"""Ethereum trace agent for Chapter 3 Forsage case work.

Cryptocurrency Investigation with Agentic AI, Wiley, Victor Fang, 2026.

Supports two input modes:
  * --tx-hash + --focal  → decode value edges inside one transaction
  * --address            → one-hop upstream/downstream via account APIs
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ch3_eth_tracing import (
    FORSAGE_CONTRACT,
    FORSAGE_TX,
    EthClient,
    decode_transaction_edges,
    trace_address_one_hop,
)

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


def ensure_openai_key() -> None:
    if os.getenv("OPENAI_API_KEY"):
        return
    fallback = os.getenv("OPENAI_API_KEY_VF")
    if fallback:
        os.environ["OPENAI_API_KEY"] = fallback


def inspect_forsage_transaction(client: EthClient, tx_hash: str) -> dict[str, Any]:
    """Deep-dive the Chapter 3 Forsage registration transaction."""
    tx = client.get_transaction(tx_hash)
    receipt = client.get_receipt(tx_hash)
    internals = client.get_internals_by_tx(tx_hash)
    calldata = tx.get("input") or "0x"
    referrer = None
    if len(calldata) >= 74:
        referrer = "0x" + calldata[34:74]

    return {
        "tx_hash": tx_hash,
        "block_number": int(tx.get("blockNumber", "0x0"), 16),
        "from": tx["from"],
        "to": tx["to"],
        "value_wei": int(tx["value"], 16),
        "input_selector": calldata[:10],
        "referrer_in_calldata": referrer,
        "status": receipt.get("status"),
        "gas_used": int(receipt.get("gasUsed", "0x0"), 16),
        "log_count": len(receipt.get("logs") or []),
        "internal_transfers": [
            {
                "from": row["from"],
                "to": row["to"],
                "value_wei": int(row["value"]),
            }
            for row in internals
            if row.get("isError", "0") == "0" and int(row["value"]) > 0
        ],
        "legal_status": "alleged Forsage activity; not convicted",
        "case_note": (
            "Top-level value (0.05 ETH) equals the sum of internal payouts "
            "in this transaction, but that equality is not guaranteed on "
            "every Ethereum contract call."
        ),
    }


def build_openai_request(package: dict[str, Any]) -> dict[str, Any]:
    trace = package["trace"]
    mode = trace["mode"]
    upstream_n = len(trace.get("upstream_events") or [])
    downstream_n = len(trace.get("downstream_events") or [])

    if mode == "transaction_decode":
        task = (
            "Summarize the Ethereum tracing results in the supplied JSON.\n"
            "Mode: transaction_decode — one known transaction parsed relative "
            "to the focal address.\n"
            f"Counts: {upstream_n} upstream edge(s), {downstream_n} downstream edge(s).\n"
            "Write a concise tracing summary with these sections:\n"
            "1. Tracing scope (mode, focal address, tx hash if present)\n"
            "2. Upstream summary — who paid the focal address, amounts, sources\n"
            "3. Downstream summary — where the focal address paid, amounts, sources\n"
            "4. Observed facts (JSON only)\n"
            "5. Heuristic inferences (label clearly as inference)\n"
            "6. Limits of this trace (single tx vs full history)\n"
        )
    else:
        complete = trace.get("history_complete")
        task = (
            "Summarize the Ethereum tracing results in the supplied JSON.\n"
            "Mode: address_one_hop — neighboring value edges from account-index APIs.\n"
            f"Counts: {upstream_n} upstream edge(s), {downstream_n} downstream edge(s).\n"
            f"History complete: {complete}\n"
            "Write a concise tracing summary with these sections:\n"
            "1. Tracing scope (mode, focal address, pagination note)\n"
            "2. Upstream summary — inbound edges by asset and source API\n"
            "3. Downstream summary — outbound edges by asset and source API\n"
            "4. Observed facts (JSON only)\n"
            "5. Heuristic inferences (label clearly as inference)\n"
            "6. Limits of this trace (pagination, incomplete history if any)\n"
        )

    return {
        "model": os.getenv("OPENAI_MODEL", "gpt-5"),
        "reasoning": {"effort": "low"},
        "instructions": (
            "You are an Ethereum forensic analyst writing a tracing results "
            "summary for an investigator. Use only the supplied JSON. Lead "
            "with upstream and downstream counts, then the most important "
            "edges. Separate observed facts from heuristic inferences. Cite "
            "full transaction hashes. Never equate an address with a person. "
            "Forsage references are alleged, not convicted. Note that internal "
            "ETH transfers share the parent transaction hash."
        ),
        "input": task + "\n\n" + json.dumps(package, indent=2),
    }


def summarize_with_ai(
    package: dict[str, Any],
    request_path: Path | None = None,
) -> tuple[str, dict[str, Any]]:
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
            "total": len(request["instructions"]) + len(request["input"]),
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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Ethereum trace agent: decode one transaction or trace one hop "
            "from an address. Cryptocurrency Investigation with Agentic AI, "
            "Wiley, Victor Fang, 2026."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--tx-hash",
        help="Decode upstream/downstream edges inside this transaction.",
    )
    mode.add_argument(
        "--address",
        help="Trace one hop upstream/downstream from this address.",
    )
    parser.add_argument(
        "--focal",
        default=FORSAGE_CONTRACT,
        help="Focal address for transaction decode mode (ignored with --address).",
    )
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    package_path = output_dir / f"eth_trace_package_{stamp}.json"
    package_latest = output_dir / "eth_trace_package_latest.json"
    summary_path = output_dir / f"tracing_summary_{stamp}.md"
    summary_latest = output_dir / "tracing_summary_latest.md"
    request_path = output_dir / f"openai_request_{stamp}.json"
    request_latest = output_dir / "openai_request_latest.json"

    eth = EthClient(use_cache=not args.no_cache)
    if args.address:
        trace = trace_address_one_hop(
            eth,
            args.address,
            max_pages=args.max_pages,
            page_size=args.page_size,
        )
        tx_detail = None
    else:
        tx_hash = args.tx_hash or FORSAGE_TX
        focal = args.focal
        trace = decode_transaction_edges(eth, tx_hash, focal)
        tx_detail = (
            inspect_forsage_transaction(eth, tx_hash)
            if tx_hash.lower() == FORSAGE_TX.lower()
            else None
        )

    package = {
        "trace": trace,
        "transaction_detail": tx_detail,
        "agent_constraints": {
            "address_is_not_identity": True,
            "forsage_is_alleged_not_convicted": True,
            "transaction_decode_is_not_address_history": True,
            "internal_transfers_share_parent_tx_hash": True,
            "read_three_value_layers": [
                "transaction.value",
                "internal calls",
                "receipt logs",
            ],
        },
        "cache_stats": {
            "hits": eth.cache_hits,
            "misses": eth.cache_misses,
            "cache_dir": str(eth.cache_dir),
            "use_cache": eth.use_cache,
        },
    }

    write_json(package_path, package)
    write_json(package_latest, package)

    print(json.dumps(package, indent=2))
    print(
        f"\n[cache] hits={eth.cache_hits} "
        f"misses={eth.cache_misses} dir={eth.cache_dir}"
    )
    print(f"[saved] package -> {package_path}")
    print(f"[saved] package -> {package_latest}")

    if args.ai:
        print("\n--- AI TRACING SUMMARY ---\n")
        summary, request_record = summarize_with_ai(
            package,
            request_path=request_path,
        )
        write_json(request_latest, request_record)
        write_text(summary_path, summary)
        write_text(summary_latest, summary)
        print(summary)
        print(f"\n[saved] openai request -> {request_path}")
        print(f"[saved] openai request -> {request_latest}")
        print(f"[saved] tracing summary -> {summary_path}")
        print(f"[saved] tracing summary -> {summary_latest}")
        chars = request_record["request_chars"]
        print(
            f"[openai] input chars={chars['input']:,} "
            f"instructions={chars['instructions']:,} "
            f"total={chars['total']:,}"
        )


if __name__ == "__main__":
    main()
