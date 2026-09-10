## Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
"""Run ch3_eth_tracing live examples, assert shapes, save results."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ch3_eth_tracing import (
    CHAIN_ID,
    FORSAGE_CONTRACT,
    FORSAGE_TX,
    EthClient,
    decode_transaction_edges,
    trace_address_one_hop,
)

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

USDT_TX = "0x73ee5f2594e154c73590ba8339e69a553b14ccce29b5a976b2725885cf86e185"
USDT_SENDER = "0x28C6c06298d514Db089934071355E5743bf21d60"
USDT = "0xdac17f958d2ee523a2206206994597c13d831ec7"


def save_results(payload: dict) -> tuple[Path, Path]:
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = RESULTS / f"ch3_eth_tracing_{stamp}.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    latest = RESULTS / "latest.json"
    latest.write_text(json.dumps(payload, indent=2) + "\n")
    return json_path, latest


def assert_forsage_decode(trace: dict) -> None:
    assert trace["mode"] == "transaction_decode"
    upstream = trace["upstream_events"]
    downstream = trace["downstream_events"]
    assert len(upstream) == 1
    assert upstream[0]["asset"] == "ETH"
    assert upstream[0]["amount_base_units"] == 50_000_000_000_000_000
    assert len(downstream) == 2
    assert sorted(row["amount_base_units"] for row in downstream) == [
        25_000_000_000_000_000,
        25_000_000_000_000_000,
    ]


def assert_usdt_decode(trace: dict) -> None:
    assert trace["upstream_events"] == []
    assert len(trace["downstream_events"]) == 1
    edge = trace["downstream_events"][0]
    assert edge["asset"].lower() == USDT
    assert edge["amount_base_units"] == 337_095_759


def assert_forsage_address(trace: dict) -> None:
    assert trace["mode"] == "address_one_hop"
    assert trace["upstream_events"] or trace["downstream_events"]


def main() -> None:
    client = EthClient()
    forsage_decode = decode_transaction_edges(client, FORSAGE_TX, FORSAGE_CONTRACT)
    usdt_decode = decode_transaction_edges(client, USDT_TX, USDT_SENDER)
    forsage_address = trace_address_one_hop(
        client,
        FORSAGE_CONTRACT,
        max_pages=1,
        page_size=5,
    )
    assert_forsage_decode(forsage_decode)
    assert_usdt_decode(usdt_decode)
    assert_forsage_address(forsage_address)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "chain_id": CHAIN_ID,
        "examples": [
            {"id": "forsage_decode", "trace": forsage_decode},
            {"id": "usdt_decode", "trace": usdt_decode},
            {"id": "forsage_address", "trace": forsage_address},
        ],
    }
    json_path, latest = save_results(payload)
    print("Assertions passed.")
    print(f"Saved JSON: {json_path}")
    print(f"Latest:     {latest}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
