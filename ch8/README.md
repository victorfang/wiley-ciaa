# Chapter 8 — Smart Contracts Lab

Cryptocurrency Investigation with Agentic AI · Victor Fang · Wiley · 2026

Companion code: <https://github.com/victorfang/wiley-ciaa/tree/main/ch8>

A hands-on Python lab for smart contract investigation. You compile a small token contract with a freeze list, separate the three layers of evidence (Solidity source, ABI function names, runtime bytecode), scan the bytecode for function entry points, and write a reproducible JSON report. An optional step has GPT draft a plain-language summary of that report under strict rules.

The lab runs offline: no wallet, no live blockchain, no real case data. See `tutorial.md` for the full walkthrough (`tutorial-wiley.md` is the print edition).

## What you will learn

- Read Solidity as an investigator: who controls the contract and what rules, such as a freeze list, it claims to enforce.
- Produce evidence yourself with the official compiler instead of relying on an explorer.
- Examine bytecode with Python to confirm which functions a contract exposes.
- Write a report with file hashes that another analyst can rerun and verify.
- Use AI safely: give it only your evidence, and check every claim in its draft.

## Files

| Path | Role |
|---|---|
| `BlacklistToken.sol` | The specimen: a small teaching token with an owner-controlled freeze list |
| `IERC20.sol` | Comparison file: standard ERC-20 function names, no working code |
| `stablecoin_case_lab.py` | Compiles both files, scans the token bytecode, writes the JSON report |
| `investigate_bytecode.py` | Helper that finds function entry points in bytecode |
| `explain_case_report.py` | Optional: asks GPT to summarize the report (instructions in `PROMPT`) |
| `requirements.txt` / `.env_example` | Dependencies and settings for the optional GPT step |
| `data/stablecoin-case-report.json` | Sample report |
| `data/unverified-ai-explanation.json` | Sample GPT summary |
| `tutorial.md` / `tutorial-wiley.md` | Walkthrough / print edition |
| `old/` | Earlier specimens and scripts, not used by the lab |

`BlacklistToken.sol` is synthetic teaching code, not the contract of any real stablecoin or issuer.

## Setup

**Python 3.11 or later.** The main lab uses only the standard library.

**Solidity compiler (`solc`), version 0.7.0 up to but not including 0.9.0**, matching `pragma solidity >=0.7.0 <0.9.0;` in the `.sol` files. Any of these works:

```bash
brew install solidity                          # macOS
pip install solc-select && solc-select install 0.8.26 && solc-select use 0.8.26
```

Or download a binary from the [Solidity releases page](https://github.com/ethereum/solidity/releases). The lab looks for `solc` on your `PATH`; to use a specific binary, set `export SOLC=/path/to/solc`.

**Optional GPT step:**

```bash
pip install -r requirements.txt
cp .env_example .env      # then set OPENAI_API_KEY
```

The default model is `gpt-6-luna`; set `OPENAI_MODEL` in `.env` to use another. This step calls the OpenAI API and may incur a small usage fee. Never commit `.env`.

## Run

```bash
cd ch8
python3 stablecoin_case_lab.py
python3 explain_case_report.py data/stablecoin-case-report.json \
  --out data/unverified-ai-explanation.json      # optional
```

`stablecoin_case_lab.py` defaults to the chapter files. To analyze other files, pass `--interface`, `--token`, and `--out`.

## Output

The console prints three labeled sections for each contract (source, ABI, runtime bytecode). Expected results:

- **IERC20:** six ABI names, **zero** bytes of runtime code. Names alone are not behavior.
- **BlacklistToken:** about 2,500 bytes of runtime code (the exact count varies by compiler version) and six function entry points, each matching an ABI name.

`data/stablecoin-case-report.json` records the compiler version, SHA-256 hashes of the inputs and bytecode, the ABI names, the entry points found (`candidate_selectors`), the limits of the analysis, and a `next_check` for live follow-up.

`data/unverified-ai-explanation.json` stores the GPT draft with the model name, a response ID, and SHA-256 hashes of the report and instructions it was given. It stays an unverified draft until a human reviews it.

## Investigative limits

- A function entry point in bytecode shows the function exists. It does not prove the freeze check inside it runs, and it is never a list of frozen wallets.
- The freeze list in this lab is empty: no address is blacklisted, and no real watchlist is loaded.
- On a live case, obtain the chain ID, contract address, and bytecode at a specific block before stating who can freeze, charge fees, or control a token.

Labs are for education and reproducible practice, not legal advice or production enforcement tooling.
