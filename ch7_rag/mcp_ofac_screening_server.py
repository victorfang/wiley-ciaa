## Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP as MCPServer

DATA = Path(__file__).with_name("ofac-dprk-crypto-sample.json")
DB = json.loads(DATA.read_text(encoding="utf-8"))
mcp = MCPServer("OFAC Crypto Screening Demo")

EVM_CHAINS = {
    "ethereum-mainnet",
    "arbitrum-one",
    "bnb-smart-chain-mainnet",
}

def normalize(blockchain_id: str, address: str) -> str:
    address = address.strip()
    return address.lower() if blockchain_id in EVM_CHAINS else address

def exact_matches(blockchain_id: str, address: str) -> list[dict]:
    target = normalize(blockchain_id, address)
    return [
        row for row in DB["records"]
        if row["blockchain_id"] == blockchain_id
        and normalize(blockchain_id, row["address"]) == target
    ]

@mcp.tool()
def check_sanctions(blockchain_id: str, address: str) -> dict:
    """Exact-match a crypto address against the local OFAC teaching sample."""
    matches = exact_matches(blockchain_id, address)
    return {
        "match": bool(matches),
        "match_count": len(matches),
        "records": matches,
        "dataset": DB["dataset_name"],
        "warning": DB["compliance_warning"],
    }

@mcp.resource("ofac://dprk-crypto-sample", mime_type="application/json")
def sanctions_dataset() -> dict:
    """Read the small, frozen teaching dataset and its provenance."""
    return DB

@mcp.prompt()
def screen_crypto_address(blockchain_id: str, address: str) -> str:
    """Start a sanctions-address screening review."""
    return (
        f"Screen {address} on {blockchain_id} with check_sanctions. "
        "If matched, report the entity, program, source date, and source URL. "
        "If not matched, say only that it is absent from this partial sample; "
        "do not call it unsanctioned."
    )

if __name__ == "__main__":
    mcp.run()
