# Chapter 3 — Ethereum One-Hop Tracing

*Cryptocurrency Investigation with Agentic AI* · Victor Fang · Wiley · 2026  
**Author:** [VictorFang.com](https://www.VictorFang.com) · [LinkedIn](https://www.linkedin.com/in/drvictorfang/) · [X](http://x.com/vicfcs)

---

This folder contains a minimal, read-only Python example of **Ethereum one-hop tracing**. You pick a **seed address** and a **single transaction hash**, then list every value edge in that transaction that touches the seed — once upstream, once downstream. Value edges are taken from three layers: native ETH (`transaction.value`), internal calls, and ERC-20 `Transfer` logs.

**Do not send funds to any address listed here.** The Forsage example is from a pending U.S. criminal matter; every Forsage statement in this lab is **alleged**, not convicted.

## What you will learn

| Concept | Meaning on Ethereum |
|---------|---------------------|
| **Upstream** | Value that **arrived at** the seed in this transaction (who paid it). |
| **Downstream** | Value that **left** the seed in this transaction (where it went). |
| **One hop** | One transaction boundary — not proof of a new person or wallet. |
| **Three evidence layers** | Native ETH (`transaction.value`), nested ETH (internal calls), ERC-20 (`Transfer` logs). |

Bitcoin stores every movement in inputs and outputs. Ethereum splits the story across three places. A tool that reads only `value` will miss internal ETH and all token transfers.

## Files

| File | Purpose |
|------|---------|
| `ch3_eth_tracing.py` | Core lab: fetch one transaction, extract edges, print upstream/downstream |
| `ch3_eth_trace_agent.py` | Package builder + optional OpenAI investigative summary |
| `test_ch3_eth_tracing.py` | Runs both examples live, asserts expected counts/amounts, saves results |
| `requirements.txt` | `requests`, `openai` (latter for `--ai`) |
| `tracing_summary_latest.md` | Sample AI / tracing artifact |
| `.env.example` | Optional API key template |
| `results/` | Saved JSON and text reports when tests are run (`latest.json`, `latest.txt`, timestamped copies) |

## Setup

```bash
cp .env.example .env   # optional ETHERSCAN_API_KEY; OPENAI_* only for --ai
pip install -r requirements.txt
```

**Dependency:** Python 3.10+. Core tracing needs `requests`; `openai` is needed only for `ch3_eth_trace_agent.py --ai`.

## Quick start

```bash
cd ch3
python3 ch3_eth_tracing.py
```

Optional — run tests and save output:

```bash
python3 test_ch3_eth_tracing.py
```

Optional — package builder / AI summary:

```bash
python3 ch3_eth_trace_agent.py
python3 ch3_eth_trace_agent.py --ai
```

Optional — use Etherscan instead of public RPC + Blockscout:

```bash
export ETHERSCAN_API_KEY=your_key_here
python3 ch3_eth_tracing.py
```

Without a key, the script uses public JSON-RPC for the transaction header and receipt, and Blockscout's Etherscan-compatible API for internal calls.

## The forensic question

Given:

- a **transaction hash** (the hop), and  
- a **focal address** (the seed),

ask two directional questions inside that one transaction:

1. **Upstream:** Did anyone pay the seed? From whom, how much, in what asset?
2. **Downstream:** Did the seed pay anyone? To whom, how much, in what asset?

This lab does **not** crawl an address history. It does not follow the graph to the next transaction. It teaches the Ethereum-specific step that must happen **before** multi-hop tracing: reading all three value layers inside a single hash.

## How Ethereum stores value (why three layers matter)

```
┌─────────────────────────────────────────────────────────────┐
│  Transaction header                                         │
│  from, to, value  ← top-level native ETH only               │
└─────────────────────────────────────────────────────────────┘
         │
         ▼ contract executes
┌─────────────────────────────────────────────────────────────┐
│  Internal calls (trace / txlistinternal)                    │
│  nested ETH moved by CALL / DELEGATECALL                    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼ token contract emits
┌─────────────────────────────────────────────────────────────┐
│  Receipt logs                                               │
│  ERC-20 Transfer(from, to, amount)                          │
└─────────────────────────────────────────────────────────────┘
```

The script implements this in `trace_one_hop()`:

1. Load the transaction and receipt. Skip reverted receipts (`status != 0x1`).
2. If `transaction.value > 0`, record a native ETH edge.
3. Fetch internal transactions for the hash; record each successful non-zero internal ETH transfer.
4. Scan receipt logs for the ERC-20 `Transfer` topic; decode indexed `from` / `to` and log data as amount.

Direction is assigned relative to the **focal address**:

- `to == focal` → **upstream**
- `from == focal` → **downstream**
- otherwise → **other edge in seed transaction** (same tx, but not the seed's hop)

Chain ID is hard-coded as `"1"` (Ethereum mainnet). A `0x` hash does not tell you the chain — the same address string can name unrelated contracts on BNB Smart Chain (chain ID 56) and Ethereum (chain ID 1).

## Walk through the code

### Data sources

```python
CHAIN_ID = "1"  # never infer from a 0x hash
API_KEY = os.environ.get("ETHERSCAN_API_KEY")
```

- **With `ETHERSCAN_API_KEY`:** Etherscan API V2 for transaction, receipt, and internals.
- **Without a key:** public RPC (`cloudflare-eth.com`, `eth.llamarpc.com`, Blockscout RPC) for tx/receipt; Blockscout explorer API for internals.

### ERC-20 `Transfer` topic

```python
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
```

This is `keccak256("Transfer(address,address,uint256)")`. Indexed addresses sit in `topics[1]` and `topics[2]` as 32-byte words; the script takes the last 20 bytes:

```python
def topic_address(topic):
    return "0x" + topic[-40:]
```

### Core function signature

```python
def trace_one_hop(tx_hash, focal):
    """Return native and ERC-20 edges created by one successful transaction."""
```

Each returned edge is a dict:

```json
{
  "asset": "ETH",
  "from": "0x...",
  "to": "0x...",
  "amount_base_units": 50000000000000000,
  "source": "transaction.value",
  "direction": "upstream"
}
```

Amounts are stored in **base units** (wei for ETH, 6-decimal micro-units for USDT) so JSON stays exact.

## Example 1 — Native ETH both ways (alleged Forsage registration)

**Transaction:** [`0x55089ea1...9246`](https://etherscan.io/tx/0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246)  
**Seed (focal):** Forsage registration contract `0x5acc84a3e955Bdd76467d3348077d003f00fFB97`  
**Block:** 9,985,902 — 2020-05-02 UTC (pre-Merge Ethereum)

An EOA called `registrationExt(address)` and attached **0.05 ETH**. The contract then paid **0.025 ETH** to two different addresses via internal calls. All three movements share **one transaction hash**.

### Live output

```
Example 1 — native ETH, one hop each way (alleged Forsage registration)
  chain ID 1   seed 0x5acc84a3e955Bdd76467d3348077d003f00fFB97
  tx       0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246

  One hop UPSTREAM (who paid the seed)
    0.05 ETH                0xa9cb5474...4c6c  ->  0x5acc84a3...fb97  [transaction.value]

  One hop DOWNSTREAM (where the seed paid)
    0.025 ETH               0x5acc84a3...fb97  ->  0x77b6d298...ab0c  [internal call]
    0.025 ETH               0x5acc84a3...fb97  ->  0xd43e8a8d...b879  [internal call]
```

### How to read it

| Direction | Amount | From → To | Source field |
|-----------|--------|-----------|--------------|
| Upstream | 0.05 ETH | EOA → Forsage contract | `transaction.value` |
| Downstream | 0.025 ETH | Forsage contract → `0x77b6…` | `internal call` |
| Downstream | 0.025 ETH | Forsage contract → `0xd43e…` (referrer in calldata) | `internal call` |

**Teaching points:**

- Top-level `value` (0.05 ETH) equals the sum of internals (0.025 + 0.025) here — but that equality is a property of *this* call, not a law of Ethereum.
- Internal transfers are **not** separate transactions. You need a trace or an explorer internal-tx view.
- One downstream "hop" can fan out to **multiple recipients** inside the same hash.
- The referrer address appears in the transaction calldata; one internal payout targets it. That is worth recording — it is not the same as proving who benefited.

### Saved JSON (base units)

```json
"upstream": [{ "amount_base_units": 50000000000000000, "source": "transaction.value" }],
"downstream": [
  { "amount_base_units": 25000000000000000, "source": "internal call" },
  { "amount_base_units": 25000000000000000, "source": "internal call" }
]
```

## Example 2 — ERC-20 only (USDT, native value zero)

**Transaction:** [`0x73ee5f25...e185`](https://etherscan.io/tx/0x73ee5f2594e154c73590ba8339e69a553b14ccce29b5a976b2725885cf86e185)  
**Seed (focal):** Binance hot wallet `0x28C6c06298d514Db089934071355E5743bf21d60`  
**Token contract:** USDT `0xdAC17F958D2ee523a2206206994597C13D831ec7`

The transaction header shows **`value: 0 wei`**. The entire economic event lives in one receipt log.

### Live output

```
Example 2 — ERC-20 only: native value is 0 wei (USDT Transfer log)
  chain ID 1   seed 0x28C6c06298d514Db089934071355E5743bf21d60
  tx       0x73ee5f2594e154c73590ba8339e69a553b14ccce29b5a976b2725885cf86e185

  One hop UPSTREAM (who paid the seed)
    (none in this transaction)

  One hop DOWNSTREAM (where the seed paid)
    337.095759 USDT         0x28c6c062...1d60  ->  0x7e7bdf8b...4e90  [receipt log 52]
```

### How to read it

| Field | Value |
|-------|-------|
| Native ETH moved | 0 wei |
| Token moved | 337.095759 USDT |
| Base units | `337095759` (USDT uses 6 decimals) |
| Log index | 52 (hex `0x34` in the receipt) |
| Direction | Downstream only — the seed is the sender |

**Teaching points:**

- An agent that reports only `transaction.value` would say this transaction moved **nothing**.
- `"USDT"` is not enough for identity — you need **chain ID 1** and contract `0xdAC…831ec7`.
- Explorer name tags (e.g. "Binance 14") are **leads**, not findings. This script records addresses only.

## Running the test script and saving results

`test_ch3_eth_tracing.py` imports `trace_one_hop`, runs both examples against live APIs, and checks:

| Example | Assertions |
|---------|------------|
| Forsage | 1 upstream edge at 50,000,000,000,000,000 wei; 2 downstream edges at 25,000,000,000,000,000 wei each |
| USDT | 0 upstream; 1 downstream edge at 337,095,759 base units from the USDT contract |

On success it writes:

```
results/
  latest.json          ← most recent structured run
  latest.txt           ← most recent human-readable report
  ch3_eth_tracing_<timestamp>.json
  ch3_eth_tracing_<timestamp>.txt
```

The JSON payload includes `generated_at_utc`, `chain_id`, `data_source`, and per-example `edges` plus grouped `directions`. Use it as an exhibit template or as input to a later agentic report step.

Example metadata from a saved run:

```json
{
  "generated_at_utc": "2026-08-25T21:40:02+00:00",
  "chain_id": "1",
  "data_source": "public_rpc_blockscout"
}
```

## Common mistakes this lab is designed to prevent

1. **Reading only `value`** — misses internal ETH and all ERC-20 movement (Example 2).
2. **Treating internals as new transactions** — they share the parent hash (Example 1).
3. **Inferring chain from address shape** — `0x5acc…fFB97` exists on Ethereum *and* BNB Smart Chain as unrelated contracts.
4. **Confusing direction** — upstream asks who paid the seed; downstream asks where the seed paid. They are not interchangeable.
5. **Upgrading graph distance to ownership** — a hop is a transaction boundary, not proof of common control.
6. **Ignoring reverts** — the script returns no edges when `receipt.status != 0x1` because no value finalized.

## Try it yourself

1. **Change the focal address** in `main()` to the EOA `0xa9cb54745839e3d59c4c7c7d9efc1c86c7984c6c` on the Forsage transaction. You should see one **downstream** edge (0.05 ETH out) and two **upstream** internal edges (0.025 ETH in each) — the mirror of the contract view.
2. **Add a third example** from your case file: any ERC-20 transfer where `value` is zero. Confirm the hop appears only under receipt logs.
3. **Run the optional agent** with `python3 ch3_eth_trace_agent.py --ai` to produce a constrained summary from the same three-layer evidence package.

## Relationship to Chapter 2 and later chapters

Chapter 2 taught one-hop tracing on Bitcoin UTXOs. This lab is the Ethereum equivalent at transaction scope: three layers, two directions, one hash.

For multi-hop graph search, bounded BFS, and agentic reporting, see later chapters. The prerequisite skill taught here is: **before you walk the graph, read every value layer in the seed transaction.**

## References

- Forsage DOJ indictment (Feb. 22, 2023) — alleged activity; case pending as of lab publication.
- [Etherscan — Forsage tx `0x55089ea1...`](https://etherscan.io/tx/0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246)
- [Etherscan — USDT tx `0x73ee5f25...`](https://etherscan.io/tx/0x73ee5f2594e154c73590ba8339e69a553b14ccce29b5a976b2725885cf86e185)
- ERC-20 `Transfer` event — `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`

---

*Companion code · [Apache License 2.0](../LICENSE) · Read-only. No broadcast.*
