# Chapter 2 — Bitcoin Trace Agent

*Cryptocurrency Investigation with Agentic AI* · Victor Fang · Wiley · 2026  
**Author:** [VictorFang.com](https://www.VictorFang.com) · [LinkedIn](https://www.linkedin.com/in/drvictorfang/) · [X](http://x.com/vicfcs)

---

One-hop Bitcoin tracing agent for the July 2020 Twitter hack case study. Pulls address history and a named transaction from Blockstream Esplora, screens for consolidation / peel / CoinJoin structure, optionally asks an OpenAI model for a constrained investigative summary, and writes everything to disk.

## What it does

1. Fetches confirmed transaction history for a Bitcoin address (default: the Twitter hack donation address).
2. Builds a **one-hop** package:
   - **Upstream** — funding transactions that paid the address
   - **Downstream** — spends that consumed the address's UTXOs
3. Inspects a fixed “running” transaction (`ea844aa0…117d`) with outspend status.
4. Labels transaction structure as hypotheses only (`possible_coinjoin`, `possible_consolidation`, `possible_peel`).
5. Optionally generates an AI narrative that must separate observed facts, heuristic inferences, and attribution.
6. Caches every Esplora JSON response so re-runs do not re-download.

**Tutorial:** see [`tutorial-bitcoin-trace-agent.md`](tutorial-bitcoin-trace-agent.md) for a function-by-function walkthrough using the saved `output/` JSON and OpenAI summary.

## Requirements

```bash
pip install -r requirements.txt
```

For `--ai`:

```bash
cp .env.example .env
export OPENAI_API_KEY=sk-...
# or
export OPENAI_API_KEY_VF=sk-...
```

Optional: `OPENAI_MODEL` (default `gpt-5`).

## Usage

```bash
# Default: Twitter address, 2020-07-15 → 2020-07-17, JSON only
python3 ch2_bitcoin_trace_agent.py

# Same run plus OpenAI investigative summary
python3 ch2_bitcoin_trace_agent.py --ai

# Custom address / window
python3 ch2_bitcoin_trace_agent.py \
  --address bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh \
  --start 2020-07-15T00:00:00Z \
  --end 2020-07-17T00:00:00Z \
  --max-pages 60 \
  --ai

# Force fresh downloads
python3 ch2_bitcoin_trace_agent.py --no-cache

# Custom output directory
python3 ch2_bitcoin_trace_agent.py --output-dir ./output --ai
```

### Flags

| Flag | Default | Meaning |
|------|---------|---------|
| `--address` | Twitter hack address | Target to trace |
| `--start` / `--end` | `2020-07-15` / `2020-07-17` UTC | Inclusive start, exclusive end (ISO-8601) |
| `--max-pages` | `60` | Esplora pagination cap (25 txs/page) |
| `--ai` | off | Call OpenAI and save the summary |
| `--no-cache` | off | Bypass `cache/esplora/` |
| `--output-dir` | `./output` | Where package + AI files are written |

## Outputs

| Path | Contents |
|------|----------|
| `cache/esplora/*.json` | Raw Esplora responses (one file per API path) |
| `output/bitcoin_trace_package_latest.json` | Full one-hop package + running tx + cache stats |
| `output/bitcoin_trace_package_<UTC>.json` | Timestamped copy of the same package |
| `output/openai_summary_latest.md` | Latest AI report (with `--ai`) |
| `output/openai_summary_<UTC>.md` | Timestamped AI report |
| `output/openai_request_latest.json` | Full OpenAI API call context (model, instructions, input, response) |
| `output/openai_request_<UTC>.json` | Timestamped copy of the same request record |

Stdout prints the package JSON, cache hit/miss counts, and (with `--ai`) the full OpenAI summary.

## Agent constraints

The package and AI prompt enforce the same rules used in the book:

- An address is not a person.
- Flow allocation (which input paid which output) is model-dependent; Bitcoin does not encode it.
- CoinJoin / change / peel labels are **screening hypotheses**, not attribution.
- If `history_complete` is false, pagination stopped early — do not treat the history as exhaustive.

## Data source

[Blockstream Esplora](https://blockstream.info/api) public API (`https://blockstream.info/api`). No API key required. Rate-limit politely; the client sleeps briefly after each network fetch and prefers the on-disk cache on subsequent runs.

---

*Companion code · [Apache License 2.0](../LICENSE)*
