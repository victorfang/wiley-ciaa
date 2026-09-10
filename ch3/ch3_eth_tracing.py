"""Ethereum value tracing for Chapter 3 case work.

Cryptocurrency Investigation with Agentic AI, Wiley, Victor Fang, 2026.

Two modes
---------
1. **Transaction decode** — given a tx hash + focal address, decode every
   value edge inside that one transaction (upstream/downstream relative to
   the focal). This does not discover the transaction; it parses it.

2. **Address one-hop trace** — given an address, list neighboring value
   edges from account-index APIs (native txs, internals, ERC-20 transfers).
   This is true one-hop tracing: who paid the address, where did it pay next.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Literal

import requests

CHAIN_ID = 1  # Ethereum mainnet; never infer chain from a 0x hash.
ETHERSCAN_V2 = "https://api.etherscan.io/v2/api"
BLOCKSCOUT = "https://eth.blockscout.com/api"
RPC_URLS = (
    "https://cloudflare-eth.com",
    "https://eth.llamarpc.com",
    "https://eth.blockscout.com/api/eth-rpc",
)
TRANSFER_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa"
    "952ba7f163c4a11628f55a4df523b3ef"
)

# Alleged Forsage registration on Ethereum mainnet (Chapter 3).
FORSAGE_TX = (
    "0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246"
)
FORSAGE_CONTRACT = "0x5acc84a3e955Bdd76467d3348077d003f00fFB97"

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / "cache" / "eth"


class EthClient:
    """Read-only Ethereum client with on-disk JSON caching."""

    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        use_cache: bool = True,
        api_key: str | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.use_cache = use_cache
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Wiley-Eth-Tracer/1.0"})
        self.cache_hits = 0
        self.cache_misses = 0

    def _cache_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        safe = key.replace("/", "_").replace(":", "_")[:80]
        return self.cache_dir / f"{safe}__{digest}.json"

    def _read_cache(self, key: str) -> Any | None:
        path = self._cache_path(key)
        if self.use_cache and path.exists():
            self.cache_hits += 1
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def _write_cache(self, key: str, payload: Any) -> None:
        if not self.use_cache:
            return
        self._cache_path(key).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    def rpc(self, method: str, params: list[Any]) -> dict[str, Any]:
        cache_key = f"rpc:{method}:{json.dumps(params, sort_keys=True)}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        errors: list[str] = []
        for url in RPC_URLS:
            try:
                response = self.session.post(url, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json().get("result")
                if result:
                    self.cache_misses += 1
                    self._write_cache(cache_key, result)
                    time.sleep(0.10)
                    return result
                errors.append(f"{url}: empty result")
            except Exception as exc:
                errors.append(f"{url}: {exc}")
        raise RuntimeError("RPC failed: " + "; ".join(errors))

    def explorer(self, module: str, action: str, **query: Any) -> Any:
        query.update(module=module, action=action)
        cache_key = f"explorer:{json.dumps(query, sort_keys=True)}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        if self.api_key:
            query.update(chainid=str(CHAIN_ID), apikey=self.api_key)
            url = ETHERSCAN_V2
        else:
            url = BLOCKSCOUT

        response = self.session.get(url, params=query, timeout=30)
        response.raise_for_status()
        payload = response.json()
        result = payload.get("result")
        message = str(payload.get("message") or "").lower()
        if result == [] or ("no " in message and "found" in message):
            self.cache_misses += 1
            self._write_cache(cache_key, [])
            time.sleep(0.10)
            return []
        if payload.get("status") == "0" or result is None:
            raise RuntimeError(payload)

        self.cache_misses += 1
        self._write_cache(cache_key, result)
        time.sleep(0.10)
        return result

    def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        if self.api_key:
            return self.explorer(
                "proxy",
                "eth_getTransactionByHash",
                txhash=tx_hash,
            )
        return self.rpc("eth_getTransactionByHash", [tx_hash])

    def get_receipt(self, tx_hash: str) -> dict[str, Any]:
        if self.api_key:
            return self.explorer(
                "proxy",
                "eth_getTransactionReceipt",
                txhash=tx_hash,
            )
        return self.rpc("eth_getTransactionReceipt", [tx_hash])

    def get_internals_by_tx(self, tx_hash: str) -> list[dict[str, Any]]:
        result = self.explorer("account", "txlistinternal", txhash=tx_hash)
        return result if isinstance(result, list) else []

    def list_account_activity(
        self,
        action: Literal["txlist", "txlistinternal", "tokentx"],
        address: str,
        *,
        page: int = 1,
        offset: int = 25,
        start_block: int = 0,
        end_block: int = 99_999_999,
        sort: str = "desc",
    ) -> list[dict[str, Any]]:
        """Account-index rows from Etherscan-compatible explorer APIs."""
        result = self.explorer(
            "account",
            action,
            address=address,
            startblock=start_block,
            endblock=end_block,
            page=page,
            offset=offset,
            sort=sort,
        )
        return result if isinstance(result, list) else []


def is_tx_hash(value: str) -> bool:
    return value.startswith("0x") and len(value) == 66


def is_evm_address(value: str) -> bool:
    return value.startswith("0x") and len(value) == 42


def topic_address(topic: str) -> str:
    return "0x" + topic[-40:]


def _edge(
    *,
    tx_hash: str,
    asset: str,
    sender: str | None,
    recipient: str | None,
    amount: int,
    source: str,
    block_number: int | None,
    direction: str | None = None,
) -> dict[str, Any]:
    edge = {
        "tx_hash": tx_hash,
        "asset": asset,
        "from": sender,
        "to": recipient,
        "amount_base_units": amount,
        "source": source,
        "block_number": block_number,
    }
    if direction is not None:
        edge["direction"] = direction
    return edge


def _classify_edge(
    edge: dict[str, Any],
    focal_lower: str,
    upstream: list[dict[str, Any]],
    downstream: list[dict[str, Any]],
    other: list[dict[str, Any]],
) -> None:
    recipient = (edge.get("to") or "").lower()
    sender = (edge.get("from") or "").lower()
    if recipient == focal_lower:
        edge["direction"] = "upstream"
        upstream.append(edge)
    elif sender == focal_lower:
        edge["direction"] = "downstream"
        downstream.append(edge)
    else:
        edge["direction"] = "other"
        other.append(edge)


def decode_transaction_edges(
    client: EthClient,
    tx_hash: str,
    focal: str,
) -> dict[str, Any]:
    """Decode upstream/downstream value edges inside one known transaction."""
    tx = client.get_transaction(tx_hash)
    receipt = client.get_receipt(tx_hash)
    if receipt.get("status") != "0x1":
        return {
            "mode": "transaction_decode",
            "target": {
                "network": "ethereum-mainnet",
                "chain_id": CHAIN_ID,
                "address": focal,
                "tx_hash": tx_hash,
            },
            "execution_status": "reverted",
            "upstream_events": [],
            "downstream_events": [],
            "other_edges": [],
        }

    block_number = int(tx.get("blockNumber", "0x0"), 16)
    focal_lower = focal.lower()
    upstream: list[dict[str, Any]] = []
    downstream: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []

    value_wei = int(tx["value"], 16)
    if value_wei:
        _classify_edge(
            _edge(
                tx_hash=tx_hash,
                asset="ETH",
                sender=tx["from"],
                recipient=tx["to"],
                amount=value_wei,
                source="transaction.value",
                block_number=block_number,
            ),
            focal_lower,
            upstream,
            downstream,
            other,
        )

    for call in client.get_internals_by_tx(tx_hash):
        amount = int(call["value"])
        if call.get("isError", "0") != "0" or not amount:
            continue
        _classify_edge(
            _edge(
                tx_hash=tx_hash,
                asset="ETH",
                sender=call["from"],
                recipient=call["to"],
                amount=amount,
                source="internal call",
                block_number=block_number,
            ),
            focal_lower,
            upstream,
            downstream,
            other,
        )

    for log in receipt.get("logs") or []:
        topics = log.get("topics") or []
        if len(topics) != 3 or topics[0].lower() != TRANSFER_TOPIC:
            continue
        _classify_edge(
            _edge(
                tx_hash=tx_hash,
                asset=log["address"],
                sender=topic_address(topics[1]),
                recipient=topic_address(topics[2]),
                amount=int(log["data"], 16),
                source=f"receipt log {int(log['logIndex'], 16)}",
                block_number=block_number,
            ),
            focal_lower,
            upstream,
            downstream,
            other,
        )

    return {
        "mode": "transaction_decode",
        "target": {
            "network": "ethereum-mainnet",
            "chain_id": CHAIN_ID,
            "address": focal,
            "tx_hash": tx_hash,
        },
        "execution_status": "success",
        "upstream_events": upstream,
        "downstream_events": downstream,
        "other_edges": other,
    }


def trace_address_one_hop(
    client: EthClient,
    address: str,
    *,
    max_pages: int = 1,
    page_size: int = 25,
    start_block: int = 0,
    end_block: int = 99_999_999,
) -> dict[str, Any]:
    """Trace one hop upstream/downstream from an address using account APIs."""
    focal_lower = address.lower()
    upstream: list[dict[str, Any]] = []
    downstream: list[dict[str, Any]] = []
    pages_fetched = 0
    history_complete = True

    def append_row(
        *,
        tx_hash: str,
        asset: str,
        sender: str | None,
        recipient: str | None,
        amount: int,
        source: str,
        block_number: int | None,
    ) -> None:
        if amount <= 0:
            return
        _classify_edge(
            _edge(
                tx_hash=tx_hash,
                asset=asset,
                sender=sender,
                recipient=recipient,
                amount=amount,
                source=source,
                block_number=block_number,
            ),
            focal_lower,
            upstream,
            downstream,
            [],
        )

    for action, source_label in (
        ("txlist", "account txlist"),
        ("txlistinternal", "account txlistinternal"),
        ("tokentx", "account tokentx"),
    ):
        for page in range(1, max_pages + 1):
            rows = client.list_account_activity(
                action,
                address,
                page=page,
                offset=page_size,
                start_block=start_block,
                end_block=end_block,
            )
            pages_fetched += 1
            if not rows:
                break
            for row in rows:
                tx_hash = row.get("hash") or row.get("transactionHash") or ""
                block_number = int(row.get("blockNumber", "0"))
                if action == "tokentx":
                    append_row(
                        tx_hash=tx_hash,
                        asset=row.get("contractAddress") or "ERC-20",
                        sender=row.get("from"),
                        recipient=row.get("to"),
                        amount=int(row["value"]),
                        source=source_label,
                        block_number=block_number,
                    )
                else:
                    append_row(
                        tx_hash=tx_hash,
                        asset="ETH",
                        sender=row.get("from"),
                        recipient=row.get("to"),
                        amount=int(row["value"]),
                        source=source_label,
                        block_number=block_number,
                    )
            if len(rows) < page_size:
                break
        else:
            history_complete = False

    return {
        "mode": "address_one_hop",
        "target": {
            "network": "ethereum-mainnet",
            "chain_id": CHAIN_ID,
            "address": address,
        },
        "history_complete": history_complete,
        "pages_fetched": pages_fetched,
        "page_size": page_size,
        "upstream_events": upstream,
        "downstream_events": downstream,
        "other_edges": [],
        "note": (
            "Address mode uses account-index APIs (txlist, txlistinternal, "
            "tokentx). Pagination may truncate history; increase --max-pages."
        ),
    }


# Backward-compatible alias for older scripts/tests.
build_one_hop_trace = decode_transaction_edges


def main() -> None:
    client = EthClient()
    package = decode_transaction_edges(client, FORSAGE_TX, FORSAGE_CONTRACT)
    print(json.dumps(package, indent=2))
    print(
        f"\n[cache] hits={client.cache_hits} "
        f"misses={client.cache_misses} dir={client.cache_dir}"
    )


if __name__ == "__main__":
    main()
