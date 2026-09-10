"""One-hop Bitcoin tracing agent for Chapter 2 case work.

Cryptocurrency Investigation with Agentic AI, Wiley, Victor Fang, 2026.

Core idea
---------
For one address A in a time window, walk every transaction that touches A
and emit two event lists:

  * upstream   — txs that *created* UTXOs at A (who funded A?)
  * downstream — txs that *spent* UTXOs from A (where did A send next?)

Bitcoin does not encode which input paid which output. This agent therefore
never invents a flow edge. It records co-spending inputs (the raw material
for common-input-ownership clustering), screens structure for CoinJoin /
consolidation / peel patterns, and leaves change-address choice as a
hypothesis for the analyst or AI layer — never as a hard fact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BASE_URL = "https://blockstream.info/api"
# July 2020 Twitter hack donation address (Chapter 2 case study).
TWITTER_ADDRESS = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
# Large consolidation that paid the Twitter address (~0.273 BTC).
RUNNING_TXID = (
    "ea844aa0356e254a9386ab429109924f"
    "e29d67e84a392cc33f9be84b7b43117d"
)

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache" / "esplora"
OUTPUT_DIR = ROOT / "output"


def ensure_openai_key() -> None:
    """Prefer OPENAI_API_KEY; fall back to OPENAI_API_KEY_VF."""
    if os.getenv("OPENAI_API_KEY"):
        return
    fallback = os.getenv("OPENAI_API_KEY_VF")
    if fallback:
        os.environ["OPENAI_API_KEY"] = fallback


class EsploraClient:
    """Thin Blockstream Esplora client with on-disk JSON caching.

    Caching matters for investigation: re-runs must be reproducible and
    must not hammer a public API while you iterate on heuristics.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        cache_dir: Path = CACHE_DIR,
        use_cache: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Wiley-Bitcoin-Tracer/1.0"}
        )
        self.cache_hits = 0
        self.cache_misses = 0

    def _cache_path(self, path: str) -> Path:
        digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]
        safe = path.strip("/").replace("/", "_") or "root"
        return self.cache_dir / f"{safe}__{digest}.json"

    def get_json(self, path: str) -> Any:
        cache_path = self._cache_path(path)
        if self.use_cache and cache_path.exists():
            self.cache_hits += 1
            return json.loads(cache_path.read_text(encoding="utf-8"))

        response = self.session.get(
            f"{self.base_url}{path}",
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        self.cache_misses += 1
        if self.use_cache:
            cache_path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
        time.sleep(0.10)
        return payload

    def get_transaction(self, txid: str) -> dict[str, Any]:
        return self.get_json(f"/tx/{txid}")

    def get_outspend(self, txid: str, vout: int) -> dict[str, Any]:
        # Follows one UTXO forward: spent? by which txid/vin?
        return self.get_json(f"/tx/{txid}/outspend/{vout}")

    def get_address_transactions(
        self,
        address: str,
        max_pages: int = 60,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Return confirmed and mempool transactions for an address.

        Esplora paginates at 25 txs. The Boolean is True only when we
        reached the end of history; False means max_pages cut us off and
        the one-hop view is incomplete.
        """
        transactions: list[dict[str, Any]] = []
        last_seen_txid: str | None = None

        for _ in range(max_pages):
            if last_seen_txid is None:
                path = f"/address/{address}/txs"
            else:
                path = (
                    f"/address/{address}/txs/chain/"
                    f"{last_seen_txid}"
                )

            page = self.get_json(path)
            if not page:
                return transactions, True

            known = {tx["txid"] for tx in transactions}
            transactions.extend(
                tx for tx in page if tx["txid"] not in known
            )

            confirmed = [
                tx for tx in page if tx.get("status", {}).get("confirmed")
            ]
            if not confirmed:
                break

            last_seen_txid = confirmed[-1]["txid"]
            if len(confirmed) < 25:
                return transactions, True

        return transactions, False


def in_time_window(
    transaction: dict[str, Any],
    start_epoch: int | None,
    end_epoch: int | None,
) -> bool:
    """Filter by confirmation time. Mempool txs pass only if no window."""
    block_time = transaction.get("status", {}).get("block_time")
    if block_time is None:
        return start_epoch is None and end_epoch is None
    if start_epoch is not None and block_time < start_epoch:
        return False
    if end_epoch is not None and block_time >= end_epoch:
        return False
    return True


def transaction_classification(tx: dict[str, Any]) -> dict[str, Any]:
    """Structural screening heuristics — not clustering, not attribution.

    These flags answer "what *shape* is this transaction?" so a human (or
    the AI layer) knows when common-input-ownership and change heuristics
    are unsafe. They do **not** name a wallet or a person.

    CoinJoin screen
        Many equal-valued outputs among many inputs/outputs. Classic
        Wasabi / JoinMarket style. If true, do **not** cluster inputs:
        co-spending was intentional mixing, not evidence of one owner.

    Consolidation screen
        Many inputs, one or two outputs, and not a CoinJoin. Typical of
        a wallet sweeping UTXOs together. Strong co-spend signal *if*
        CoinJoin was screened out first (see agent_constraints).

    Peel screen (change-address candidate shape)
        One or two inputs and exactly two outputs. Often a payment plus
        change returning to the sender. This agent does **not** pick
        which output is change (round-amount, script-type mismatch, and
        address-reuse tests belong to a disclosed tracing model). It
        only flags the *shape* that makes change detection tempting.

    Address ≠ identity. Labels are hypotheses until corroborated.
    """
    values = [output["value"] for output in tx.get("vout", [])]
    equal_value_counts = Counter(values)
    # Largest set of outputs that share one satoshi amount.
    largest_equal_set = max(equal_value_counts.values(), default=0)
    input_count = len(tx.get("vin", []))
    output_count = len(tx.get("vout", []))

    # CoinJoin: enough equal outputs that mixing is the plausible intent.
    # Thresholds are pedagogical defaults from Chapter 2 — tune per case.
    possible_coinjoin = (
        input_count >= 5
        and output_count >= 5
        and largest_equal_set >= 5
    )

    return {
        "input_count": input_count,
        "output_count": output_count,
        "largest_equal_output_set": largest_equal_set,
        "possible_coinjoin": possible_coinjoin,
        # Wallet sweep / merge: co-spend clustering is often applicable
        # *after* CoinJoin has been ruled out.
        "possible_consolidation": (
            input_count >= 5
            and output_count <= 2
            and not possible_coinjoin
        ),
        # Payment+change silhouette. Change detection is left to the
        # analyst; we refuse to auto-label an output as "change".
        "possible_peel": (
            input_count <= 2
            and output_count == 2
            and not possible_coinjoin
        ),
        "warning": "Screening labels are hypotheses, not attribution.",
    }


def build_one_hop_trace(
    client: EsploraClient,
    address: str,
    start_epoch: int | None = None,
    end_epoch: int | None = None,
    max_pages: int = 60,
) -> dict[str, Any]:
    """Build upstream and downstream event lists for one address.

    One hop means: stop at the neighboring transactions. We do not walk
    further into previous_address histories or into candidate_outputs'
    later spends — that is multi-hop tracing and needs explicit bounds.

    Upstream (funding → address)
        For each tx that *pays* `address`, record every input that
        participated. Those previous_address values are the co-spenders
        that jointly created the payment. Under the common-input-
        ownership heuristic (CIOH), co-spent inputs are hypothesized to
        share a controller — **except** when the tx looks like a
        CoinJoin. This function records the co-spend set; it does not
        merge addresses into a cluster graph.

    Downstream (address → next hop)
        For each tx that *spends* a UTXO from `address`, record all
        outputs as candidates. Bitcoin's ledger does not say which
        output received "our" sats. Listing every output keeps the
        evidence honest; picking one requires a disclosed model
        (e.g., peel-chain / change heuristics).

    Allocation warning
        Appears on every event. Repeating it in the package is
        deliberate: agents and reports must not invent flow edges.
    """
    transactions, complete = client.get_address_transactions(
        address,
        max_pages=max_pages,
    )

    upstream: list[dict[str, Any]] = []
    downstream: list[dict[str, Any]] = []

    for tx in transactions:
        if not in_time_window(tx, start_epoch, end_epoch):
            continue

        # --- Upstream: did this tx create UTXO(s) at the target? ------
        # Match outputs whose scriptpubkey_address is our target.
        target_outputs = [
            {
                "outpoint": f'{tx["txid"]}:{vout_index}',
                "vout": vout_index,
                "value_sats": output["value"],
                "script_type": output.get("scriptpubkey_type"),
            }
            for vout_index, output in enumerate(tx.get("vout", []))
            if output.get("scriptpubkey_address") == address
        ]

        if target_outputs:
            # Every vin is a co-spender. Preserve them all for CIOH /
            # clustering review; do not drop "unrelated" inputs.
            participating_inputs = []
            for vin_index, tx_input in enumerate(tx.get("vin", [])):
                prevout = tx_input.get("prevout") or {}
                participating_inputs.append(
                    {
                        "vin": vin_index,
                        "previous_outpoint": (
                            f'{tx_input.get("txid")}:'
                            f'{tx_input.get("vout")}'
                        ),
                        "previous_address": prevout.get(
                            "scriptpubkey_address"
                        ),
                        "previous_value_sats": prevout.get("value"),
                        "script_type": prevout.get("scriptpubkey_type"),
                    }
                )

            upstream.append(
                {
                    "funding_txid": tx["txid"],
                    "target_outputs": target_outputs,
                    "participating_inputs": participating_inputs,
                    "block_time": tx.get("status", {}).get("block_time"),
                    "allocation_warning": (
                        "Inputs jointly fund all outputs; no direct "
                        "input-to-output mapping is encoded."
                    ),
                }
            )

        # --- Downstream: did this tx spend UTXO(s) from the target? ---
        target_inputs = []
        for vin_index, tx_input in enumerate(tx.get("vin", [])):
            prevout = tx_input.get("prevout") or {}
            if prevout.get("scriptpubkey_address") == address:
                target_inputs.append(
                    {
                        "vin": vin_index,
                        "outpoint": (
                            f'{tx_input.get("txid")}:'
                            f'{tx_input.get("vout")}'
                        ),
                        "value_sats": prevout.get("value"),
                    }
                )

        if target_inputs:
            # All outputs are candidates. Change vs payment is unknown.
            candidate_outputs = [
                {
                    "vout": vout_index,
                    "address": output.get("scriptpubkey_address"),
                    "value_sats": output["value"],
                    "script_type": output.get("scriptpubkey_type"),
                }
                for vout_index, output in enumerate(tx.get("vout", []))
            ]

            downstream.append(
                {
                    "spending_txid": tx["txid"],
                    "target_inputs": target_inputs,
                    "candidate_outputs": candidate_outputs,
                    # Screen CoinJoin before any clustering inference.
                    "classification": transaction_classification(tx),
                    "block_time": tx.get("status", {}).get("block_time"),
                    "allocation_warning": (
                        "Do not assign the target input to one output "
                        "without a disclosed tracing model."
                    ),
                }
            )

    return {
        "target": {
            "network": "bitcoin-mainnet",
            "address": address,
            "start_epoch": start_epoch,
            "end_epoch": end_epoch,
        },
        "history_complete": complete,
        "transactions_retrieved": len(transactions),
        "upstream_events": upstream,
        "downstream_events": downstream,
    }


def inspect_running_transaction(
    client: EsploraClient,
    txid: str,
) -> dict[str, Any]:
    """Deep-dive one named transaction (the Chapter 2 "running" example).

    Adds signals useful for clustering review:
      * input_address_counts — address reuse across vins (same key
        controlling many inputs is a strong single-wallet clue, distinct
        from CIOH across *different* addresses).
      * per-output outspend — follows each UTXO one hop forward so the
        analyst sees whether the payment and the supposed change were
        later spent (and when).
    """
    tx = client.get_transaction(txid)
    input_total = sum(
        (tx_input.get("prevout") or {}).get("value", 0)
        for tx_input in tx.get("vin", [])
    )
    # Same address appearing on many vins ⇒ address reuse / wallet sweep,
    # not multi-party co-spend. Still not a person identity.
    input_address_counts = Counter(
        (tx_input.get("prevout") or {}).get("scriptpubkey_address")
        for tx_input in tx.get("vin", [])
    )

    outputs = []
    for index, output in enumerate(tx.get("vout", [])):
        outputs.append(
            {
                "outpoint": f"{txid}:{index}",
                "address": output.get("scriptpubkey_address"),
                "value_sats": output["value"],
                "script_type": output.get("scriptpubkey_type"),
                # Forward edge for change vs payment follow-up.
                "outspend": client.get_outspend(txid, index),
            }
        )

    return {
        "txid": txid,
        "status": tx.get("status"),
        "input_total_sats": input_total,
        "input_address_counts": dict(input_address_counts),
        "fee_sats": tx.get("fee"),
        "classification": transaction_classification(tx),
        "outputs": outputs,
    }


def build_openai_request(package: dict[str, Any]) -> dict[str, Any]:
    """Exact kwargs sent to client.responses.create(...)."""
    return {
        "model": os.getenv("OPENAI_MODEL", "gpt-5"),
        "reasoning": {"effort": "low"},
        "instructions": (
            "You are a Bitcoin forensic analyst. Use only the supplied "
            "JSON for transaction facts. Separate observed facts, "
            "heuristic inferences, and attribution. Cite full TXIDs. "
            "Never equate an address with a person. Never map a specific "
            "input to a specific output unless the package proves it. "
            "If history_complete is false, state that pagination is "
            "incomplete. Treat CoinJoin and change detection as hypotheses."
        ),
        "input": (
            "Analyze this one-hop Bitcoin trace and provide a concise "
            "investigative report:\n"
            + json.dumps(package, indent=2)
        ),
    }


def summarize_with_ai(
    package: dict[str, Any],
    request_path: Path | None = None,
) -> tuple[str, dict[str, Any]]:
    """Optional narrative layer; requires OPENAI_API_KEY.

    Returns (output_text, request_record). When request_path is set, the
    full API call context is written there before the request is sent.
    """
    ensure_openai_key()
    from openai import OpenAI

    request = build_openai_request(package)
    request_record = {
        "api": "openai.responses.create",
        "sent_at_utc": datetime.now(timezone.utc).isoformat(),
        "request": request,
        "request_chars": {
            "instructions": len(request["instructions"]),
            "input": len(request["input"]),
            "total": (
                len(request["instructions"]) + len(request["input"])
            ),
        },
    }
    if request_path is not None:
        write_json(request_path, request_record)

    client = OpenAI()
    response = client.responses.create(**request)
    request_record["response"] = {
        "id": getattr(response, "id", None),
        "model": getattr(response, "model", None),
        "output_text": response.output_text,
    }
    if request_path is not None:
        write_json(request_path, request_record)
    return response.output_text, request_record


def parse_utc(value: str) -> int:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return int(timestamp.timestamp())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "One-hop Bitcoin tracer with CoinJoin/consolidation/peel "
            "screens. Cryptocurrency Investigation with Agentic AI, "
            "Wiley, Victor Fang, 2026."
        ),
    )
    parser.add_argument("--address", default=TWITTER_ADDRESS)
    parser.add_argument("--start", default="2020-07-15T00:00:00Z")
    parser.add_argument("--end", default="2020-07-17T00:00:00Z")
    parser.add_argument("--max-pages", type=int, default=60)
    parser.add_argument("--ai", action="store_true")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass on-disk Esplora JSON cache.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory for package JSON and AI summary files.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    package_path = output_dir / f"bitcoin_trace_package_{stamp}.json"
    package_latest = output_dir / "bitcoin_trace_package_latest.json"
    ai_path = output_dir / f"openai_summary_{stamp}.md"
    ai_latest = output_dir / "openai_summary_latest.md"
    request_path = output_dir / f"openai_request_{stamp}.json"
    request_latest = output_dir / "openai_request_latest.json"

    esplora = EsploraClient(use_cache=not args.no_cache)
    package = {
        "one_hop_trace": build_one_hop_trace(
            client=esplora,
            address=args.address,
            start_epoch=parse_utc(args.start),
            end_epoch=parse_utc(args.end),
            max_pages=args.max_pages,
        ),
        "running_transaction": inspect_running_transaction(
            esplora,
            RUNNING_TXID,
        ),
        # Constraints mirrored into the AI prompt via the package JSON.
        "agent_constraints": {
            "address_is_not_identity": True,
            "flow_allocation_is_model_dependent": True,
            # Always screen CoinJoin before applying CIOH clustering.
            "coinjoin_screen_before_clustering": True,
        },
        "cache_stats": {
            "hits": esplora.cache_hits,
            "misses": esplora.cache_misses,
            "cache_dir": str(esplora.cache_dir),
            "use_cache": esplora.use_cache,
        },
    }

    write_json(package_path, package)
    write_json(package_latest, package)

    print(json.dumps(package, indent=2))
    print(
        f"\n[cache] hits={esplora.cache_hits} "
        f"misses={esplora.cache_misses} dir={esplora.cache_dir}"
    )
    print(f"[saved] package -> {package_path}")
    print(f"[saved] package -> {package_latest}")

    if args.ai:
        print("\n--- AI INVESTIGATIVE SUMMARY ---\n")
        summary, request_record = summarize_with_ai(
            package,
            request_path=request_path,
        )
        write_json(request_latest, request_record)
        write_text(ai_path, summary)
        write_text(ai_latest, summary)
        print(summary)
        print(f"\n[saved] openai request -> {request_path}")
        print(f"[saved] openai request -> {request_latest}")
        print(f"[saved] openai summary -> {ai_path}")
        print(f"[saved] openai summary -> {ai_latest}")
        chars = request_record["request_chars"]
        print(
            f"[openai] input chars={chars['input']:,} "
            f"instructions={chars['instructions']:,} "
            f"total={chars['total']:,}"
        )


if __name__ == "__main__":
    main()
