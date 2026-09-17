# Chapter 4 — Compliance, Off-Ramps, and Legal Reality

*Cryptocurrency Investigation with Agentic AI* · Victor Fang · Wiley · 2026  
**Author:** [VictorFang.com](https://www.VictorFang.com) · [LinkedIn](https://www.linkedin.com/in/drvictorfang/) · [X](http://x.com/vicfcs)

---

Drafts a **FAKE TRAINING** Suspicious Activity Report (SAR) workpaper for an AML officer — **not for filing**. The agent reads one fully synthetic exchange case (`SYNTHETIC-1`), writes an evidence-bounded draft, and requires a typed human approval before anything is saved.

Every identifier in this lab is fictional. There is no real case, no real customer, and no real address.

## The synthetic case (`SYNTHETIC-1`)

| Field | Value |
|-------|-------|
| Institution | ACME Exchange, Market Street, San Francisco (fictional) |
| Subject | John Doe, DOB 1977-07-07, account `ACME-TRAINING-0042` |
| Expected activity | Below USD 25,000 per month |
| Deposit | 77 BTC on Bitcoin mainnet, observed 2026-09-16 18:42 UTC |
| Training valuation | 77 BTC × USD 110,000 = USD 8,470,000 (illustrative only) |
| Then | 75 BTC sold 20:21 UTC; wire to a new foreign beneficiary requested and **held** 20:29 UTC |
| Red flags | New device and session IP `203.0.113.42`; source-of-funds records requested with no response by the 2026-09-17 cutoff |
| Analytics | Indirect exposure to a ransomware-tagged cluster — **a lead, not proof** |

The `source_address`, `deposit_address`, and `txid` (`deadbeef` × 8) are deliberately **invalid** — the addresses contain characters outside the bech32 alphabet, so funds can never be sent to them.

## What the agent does

1. Builds the `SYNTHETIC-1` case package and computes the illustrative USD value with `Decimal`.
2. Asks an OpenAI model (Responses API, `store=False`) to draft **Parts I–V**, **Evidence Gaps**, and a **Human Review Checklist**, with Part V written chronologically and including the full addresses and TxID.
3. Constrains the draft: cite facts as `[SYNTHETIC-1]`, leave unknowns unresolved, separate the confirmed deposit and sale from the **held** wire request, and never infer guilt, ransomware participation, sanctions status, or intent.
4. Requires the draft to end with:  
   `Filing decision: UNDECIDED - AUTHORIZED HUMAN REQUIRED`
5. Aborts without saving if the API response is not `completed` or the text is empty.
6. Prints the draft wrapped in `# FAKE TRAINING DOCUMENT - NOT FOR SAR FILING` banners, then waits for approval.

## Setup

```bash
cp .env.example .env   # set OPENAI_API_KEY and OPENAI_MODEL
pip install -r requirements.txt
```

Both variables are **required** — the script exits immediately if either is missing.

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Model id (e.g. `gpt-4.1-mini`) |

## Run

```bash
python3 ch4-sar_agent.py
```

After the draft prints, either:

- type `SAVE FAKE DRAFT` exactly and press Enter to save, or
- press Enter alone (or type anything else) to cancel — the script exits without writing

**Saving overwrites.** `FAKE_SAR_TRAINING_DRAFT.md` is written with `Path.write_text`, so an existing draft is replaced without warning. Rename or copy any draft you want to keep before re-running.

## How the code works

The script is about 90 lines and reads top to bottom in five steps.

**1. Describe the case as data, not prose.** All the facts live in one `CASE` dictionary — institution, subject, the Bitcoin deposit, the timeline of events, the analytics lead, and the records already retained. Keeping evidence in a dictionary rather than inside the prompt text means you can see exactly what the model was given.

```python
CASE = {
    "evidence_id": "SYNTHETIC-1",
    "warning": "Fictional training case; not for filing.",
    ...
}
```

**2. Do the arithmetic in Python, not in the model.** Language models are unreliable at multiplication, so the USD figure is computed with `Decimal` and handed to the model as a finished value:

```python
btc = Decimal(CASE["bitcoin"]["amount_btc"])
rate = Decimal(CASE["bitcoin"]["assumed_usd_per_btc"])
CASE["bitcoin"]["training_value_usd"] = str(btc * rate)
```

**3. Put the rules in `instructions`, the evidence in `input`.** The Responses API keeps these two separate. `INSTRUCTIONS` says what to write and what never to claim; the case JSON is the only material the model may draw on. `store=False` keeps the training case off OpenAI's servers.

```python
response = OpenAI(timeout=60, max_retries=0).responses.create(
    model=model,
    instructions=INSTRUCTIONS,
    input=json.dumps(CASE, indent=2),
    store=False,
    max_output_tokens=1800,
)
```

**4. Fail closed.** If the call is cut short or comes back empty, the script exits rather than saving a partial workpaper. A truncated SAR draft is worse than none.

```python
if response.status != "completed" or not response.output_text.strip():
    raise SystemExit("No complete draft returned; nothing saved.")
```

**5. Make the human the gate.** The draft is printed between `FAKE TRAINING` banners, and nothing touches disk until you type the exact phrase. Any other input — including a bare Enter — cancels.

```python
approval = input("Type SAVE FAKE DRAFT after review, or press Enter to cancel: ")
if approval != "SAVE FAKE DRAFT":
    raise SystemExit("Cancelled; nothing saved or filed.")
```

This is the chapter's real lesson: the agent drafts, the human decides.

## Understanding the result

A sample run is saved as [`FAKE_SAR_TRAINING_DRAFT.md`](FAKE_SAR_TRAINING_DRAFT.md). The model turns the dictionary into a structured workpaper:

| Section | What it contains |
|---------|------------------|
| Part I | Subject and account — John Doe, `ACME-TRAINING-0042`, and the stated expectation of under USD 25,000 per month |
| Part II | The transactions — 77 BTC in, both addresses, the TxID, the USD 8,470,000 illustration, the 75 BTC sale, and the held wire |
| Part III | Behavioral flags — the new device and IP, the unanswered source-of-funds request, and the ransomware-cluster lead |
| Part IV | Records retained for the file |
| Part V | The same facts as a dated narrative, which is the part a reviewer reads first |
| Evidence Gaps | What is still unknown: source of funds, beneficiary identity, and the nature of the cluster link |
| Human Review Checklist | Open items for the officer, ending in the escalation decision |

Three details are worth noticing, because they are what separate a usable draft from a risky one:

- **The suspicion is quantified, not asserted.** A deposit worth roughly USD 8.47 million against a stated expectation of under USD 25,000 a month is the finding. The draft states the mismatch and stops there.
- **Completed and incomplete actions stay distinct.** The deposit and the 75 BTC sale happened; the wire was *requested and held*. Collapsing those three into "moved USD 8.4 million offshore" would be the most damaging error the agent could make.
- **The ransomware link stays a lead.** The draft says indirect exposure with no direct evidence — it never promotes a cluster tag into a finding about the customer.

And the last line is always the same:

```
Filing decision: UNDECIDED - AUTHORIZED HUMAN REQUIRED
```

Your output will differ in wording on every run, since the model writes fresh prose each time. Facts, addresses, amounts, and that final line should not change. If they do, treat it as a prompt or model problem worth investigating — that habit of checking generated output against source evidence is the skill this lab is teaching.

## Files

| File | Purpose |
|------|---------|
| `ch4-sar_agent.py` | Lab script |
| `requirements.txt` | `openai` |
| `.env.example` | API key / model template |
| `FAKE_SAR_TRAINING_DRAFT.md` | Sample saved training draft |

## Caveats

- Output is a **training workpaper only** — not a real SAR, and not for FinCEN or any other regulator.
- ACME Exchange, John Doe, the account number, the addresses, and the TxID are all **fictional**.
- Part headings come from the model, not the official FinCEN SAR form. Do not treat them as the real filing structure.
- The agent cannot decide or submit a filing; an authorized human remains responsible.
- The USD figure is an assumed-rate illustration, not an executed trade price or a completed wire amount.
- Ransomware-cluster exposure is a screening lead. It is not attribution and not evidence of participation.

## Summary

This lab sits at the point where an investigation becomes a compliance obligation. Tracing coins is a technical problem; deciding whether an institution must report what it found is a legal one, and this chapter is about keeping those two apart.

The agent takes a synthetic exchange case — an unexplained 77 BTC deposit, a fast sale, and a wire to a new foreign beneficiary — and produces a structured SAR-style workpaper in seconds: parts, a dated narrative, evidence gaps, and a reviewer checklist. That is genuinely useful, because assembling a first draft is the slowest part of an analyst's day.

What it deliberately does **not** do matters more:

- It does not decide. Every run ends `UNDECIDED - AUTHORIZED HUMAN REQUIRED`.
- It does not file. Nothing is transmitted anywhere, and nothing is even written to disk without a typed phrase.
- It does not embellish. Facts come from a dictionary you can inspect, the arithmetic happens in Python, and a truncated response is discarded rather than saved.
- It does not promote leads into findings. A cluster tag stays exposure; a held wire stays held.

Three transferable practices come out of this:

1. **Keep evidence as structured data.** If the facts live in a dictionary rather than in prose, you can always prove what the model was given.
2. **Compute outside the model.** Anything a regulator might rely on — amounts, dates, totals — should be calculated in code and passed in.
3. **Put the human at the write step, not after it.** An approval gate that runs before the file exists is a control. One that runs after is a formality.

Used this way, an agent shortens the drafting work without taking on a decision it has no authority to make — which is the only form of automation a compliance function can defend.

---

*Companion code · [Apache License 2.0](../LICENSE)*
