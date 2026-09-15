# Chapter 4 — Compliance, Off-Ramps, and Legal Reality

*Cryptocurrency Investigation with Agentic AI* · Victor Fang · Wiley · 2026  
**Author:** [VictorFang.com](https://www.VictorFang.com) · [LinkedIn](https://www.linkedin.com/in/drvictorfang/) · [X](http://x.com/vicfcs)

---

Drafts a **FAKE TRAINING** SAR-style workpaper for an AML officer — **not for filing**. The agent combines a public Bitcoin fixture (`PUBLIC-1`) with a clearly labeled synthetic exchange case (`SYNTHETIC-1` / ACME / John Doe), keeps them separate, and requires a human save gate before writing any file.

## What it does

1. Builds a case package with:
   - **PUBLIC-1** — public Bitcoin output cited from a D. Mass. affidavit (reference only)
   - **SYNTHETIC-1** — fictional ACME Exchange deposit → sale → held wire scenario
2. Asks an OpenAI model to draft Parts I–V (Subject, Activity, Institution, Contact, Narrative) labeled **FAKE TRAINING**
3. Requires evidence gaps, a human checklist, and:  
   `Filing decision: UNDECIDED - AUTHORIZED HUMAN REQUIRED`
4. Prints the draft, then waits for you to type exactly `SAVE FAKE DRAFT` before writing `FAKE_SAR_TRAINING_DRAFT.md`

## Setup

```bash
cp .env.example .env   # set OPENAI_API_KEY and OPENAI_MODEL
pip install -r requirements.txt
```

Required environment variables:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model id (e.g. `gpt-4.1-mini`) |

## Run

```bash
python3 ch4-sar_agent.py
```

After the draft prints, either:

- type `SAVE FAKE DRAFT` and press Enter to save, or  
- press Enter alone to cancel (nothing is written)

If `FAKE_SAR_TRAINING_DRAFT.md` already exists, delete or rename it first — the script opens that path exclusively (`"x"` mode).

## Files

| File | Purpose |
|------|---------|
| `ch4-sar_agent.py` | Lab script |
| `requirements.txt` | `openai` |
| `.env.example` | API key / model template |
| `FAKE_SAR_TRAINING_DRAFT.md` | Sample saved training draft (if generated) |

## Caveats

- Output is a **training workpaper only** — not a real SAR and not for FinCEN or any regulator.
- ACME, John Doe, and related IDs are **fictional** and unrelated to `PUBLIC-1`.
- The agent cannot decide or submit a filing; a human remains responsible.
- Assumed BTC/USD valuation is illustrative, not an executed trade price.

---

*Companion code · [Apache License 2.0](../LICENSE)*
