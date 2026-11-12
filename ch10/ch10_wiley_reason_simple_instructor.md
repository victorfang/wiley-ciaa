# Instructor Guide: Reasoning Through a Cross-Chain Bridge Match

Victor Fang, 2026 · *Cryptocurrency Investigation with Agentic AI* · Chapter 10

## Lab overview

In this lab you build a minimal reasoning agent and test it on one real Wormhole bridge trace: a transfer of 550 USDT from Ethereum to BNB Smart Chain. You run the same case eight times, varying only the model and the reasoning-effort setting. Your job is not to memorize a hash. Your job is to grade how the agent reasons: which row it keeps, what it calls proof, and whether that language belongs in a case file.

By the end you should be able to:

1. Score an agent on two lines: the destination it names, and the proof sentence it writes.
2. Distinguish a correct hash from a correct investigation.
3. Decide when raising reasoning effort improves an answer, and when it only makes a wrong label more certain.

Model IDs will change. The grading method should not.

## Investigation scenario

You are given one source transfer and three destination candidates, all timestamped 11 December 2024. The source Wormhole message uses sequence **426560**. Candidate 1 repeats that sequence. Candidates 2 and 3 are planted neighbors (**426559** and **426561**). The JSON does not mark them as planted.

Candidate 2 is the trap most desks fall into: same recipient, same amount, and a timestamp **eight minutes sooner** than the true redemption. An agent that ranks by clock and amount will prefer the wrong row.

Before you run any model, fix the expected assessment. Retain only the row whose sequence equals the source. Reject a different sequence even when amount and recipient match. A complete answer also states that the file has no signed VAA, so the link is a record comparison and guardian signatures were not verified. Table 10.20 records that rubric.

**Table 10.20.** Expected assessment of the source transfer and the three destination candidates.

| Record | Chain | VAA sequence | Time (UTC) | Amount | Assessment |
|---|---|---:|---|---|---|
| Source | Ethereum | 426560 | 19:27:11 | 550 USDT | Source transfer to trace |
| Candidate 1 | BSC | 426560 | 19:41:28 | 550 USDT | Retain: matching sequence and amount; verify VAA payload and successful execution |
| Candidate 2 | BSC | 426559 | 19:35:10 | 550 USDT | Reject: references a different source message |
| Candidate 3 | BSC | 426561 | 19:42:01 | 549.8 USDT | Reject: different sequence and recipient |

## Lab files and setup

| File | Purpose |
|---|---|
| `ch10_reason_simple.py` | Sends one question; loops models and `reasoning_effort` |
| `.env` | Stores `OPENAI_API_KEY` |
| `simple_results/` | One text file per run: `<model>_<effort>.txt` |

From the `ch10_bridge` directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install openai python-dotenv
cp .env.example .env
.venv/bin/python ch10_reason_simple.py
```

The case JSON never changes. The script varies only `model` and `reasoning_effort`. The prompt deliberately calls the VAA id a **"cryptographic identifier."** Watch whether the model treats that phrase as a finding or tests it against the file.

```python
RUNS = [
    ("gpt-6-luna", "high"), ("gpt-6-luna", "low"),
    ("gpt-6-astra", "high"), ("gpt-6-astra", "low"),
    ("gpt-5-nano", "high"), ("gpt-5-nano", "low"),
    ("gpt-5-mini", "high"), ("gpt-5-mini", "low"),
]
response = client.chat.completions.create(
    model=model,
    reasoning_effort=effort,
    messages=[
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question + cross_chain_payload},
    ],
)
```

## Configuring reasoning effort

Reasoning effort is the main tuning knob in this lab.

- On **Chat Completions** (what this script uses), set `reasoning_effort`.
- On the **Responses API**, the same idea is `reasoning.effort`.

This lab compares **`low`** and **`high`**. If you omit the parameter, most models default to `medium`. There is no API value named `hard`; use `high` for the deeper pass.

**What you get back.** Chat Completions reports `usage.completion_tokens_details.reasoning_tokens`. It does not expose the hidden chain of thought. Those tokens still occupy context and are **billed as output tokens**. Grade the visible answer; use the token count for cost awareness. List prices appear in Table 10.2 under Pricing.

**Other vendors.** Reasoning appears under different names and returns different artifacts. Table 10.4 summarizes; details drift, so check the vendor’s current docs before you deploy.

**Table 10.4.** How other reasoning APIs differ from this lab.

| API | How reasoning is set | What comes back |
|---|---|---|
| OpenAI, this lab | `reasoning_effort`, from a light pass to a hard one. This script sends `low` and `high`. | A token count. The reasoning text stays hidden. A summary is a separate opt-in on the Responses API. |
| Anthropic | Newer Claude models think adaptively. `effort` (`low` through `max`) steers how readily and how deeply. Older models take a token budget, `budget_tokens`. | A summary only if you ask for one. Many current models omit the text by default. The full thinking is billed as output either way. |
| DeepSeek | Thinking is on by default. `reasoning_effort` is `low`, `high`, or `max`. A `thinking` flag can turn it off. | The chain of thought itself, in `reasoning_content`, beside the answer. With tools, that text has to be passed back on the next turn. |
| Kimi | Thinking models take `reasoning_effort` of `low`, `high`, or `max`. The default on the current flagship is `max`. | `reasoning_content` as well. Later turns keep that text in context, and it continues to be billed. |

**Transferable habits:** reasoning tokens cost money whether you can read them or not; visible chain-of-thought is not the same as a verified signature; always grade the proof sentence in the final answer.

## Results and how to read them

Compare a stronger GPT-6 pair (`gpt-6-luna`, `gpt-6-astra`) with a weaker GPT-5 pair (`gpt-5-mini`, `gpt-5-nano`). Table 10.3 lines up high and low effort on the same case. Every run selected candidate 1 (sequence 426560) and rejected 426559 and 426561. The split is in the **verdict** column: whether the proof sentence is defensible.

**Table 10.3.** Lab verdicts on this case. Every cell retains sequence 426560.

| Model | High effort | Low effort | Verdict |
|---|---|---|---|
| `gpt-6-luna` | 401 reasoning tokens. A record match, and it says this is not an on-chain verification. | 124 reasoning tokens. Right sequence. The limit is unstated. | Correct at high. Incomplete at low. |
| `gpt-6-astra` | 512 reasoning tokens. The id identifies a message. It is not cryptographic proof. | 0 reasoning tokens. The opening still says the JSON has no signed VAA, so this is not a cryptographic verification. | Correct at both. |
| `gpt-5-mini` | 6,336 reasoning tokens. "Exact VAA ID equality is cryptographic proof." | 192 reasoning tokens. The row is "cryptographically attributable." | Wrong proof sentence at both. |
| `gpt-5-nano` | 8,000 reasoning tokens. Heads a string match "Cryptographic identifier." | 320 reasoning tokens. Calls it a "cryptographic linkage," and misreads the clock. | Wrong proof sentence at both. |

### Teaching point 1: The same match, opposite labels

`gpt-6-astra`, at low effort, with no reasoning tokens counted:

> Strictly, the VAA ID is a message identifier, not itself a cryptographic hash or signature proof. The reported guardian set index `4` and signature count `13` do not permit signature verification without the actual signed VAA.

`gpt-5-mini`, at high effort, after 6,336 reasoning tokens:

> Root-cause for decision: exact VAA ID equality is cryptographic proof.

Both models kept candidate 1. `gpt-6-astra` challenged the wording from the prompt and treated `signature_count` as an unverified field. `gpt-5-mini` elevated prompt language to the stated reason for the decision. **Lesson:** equal strings in a case file are a record match, not a guardian signature check.

### Teaching point 2: More effort can add a caveat—or harden an error

`gpt-6-luna` at high effort:

> This is a logical match from the provided records, not an independent on-chain verification of the transaction.

`gpt-6-luna` at low effort stops after field agreement and never states that limit.

**Lesson:** on this model, higher effort bought the sentence your case note needs. On `gpt-5-mini`, higher effort bought more confidence in the same false proof word.

### Teaching point 3: A model can invent a rejection reason

`gpt-5-nano` at low effort, on candidate 2:

> the timestamp precedes the expected post-emission window for this VAA

Sequence **426559** is a valid reason to reject that row. The clock is not: 19:35:10 is still after the source at 19:27:11. **Lesson:** stack real protocol checks first; treat extra narrative as unverified until you confirm it against the file.

## Grading checklist for your next agent

Use this rubric when you evaluate any investigation agent, not only bridge traces:

1. **Score the join and the proof sentence separately.** A correct hash with a false evidence label fails the investigation.
2. **Treat strong prompt words as hypotheses.** If the question says "cryptographic," did the agent verify a signature or echo the label?
3. **Raise effort against a rule you wrote first.** Run low; move to high only when low misses an explicit requirement (e.g., state that signatures were not checked). If high only strengthens a false claim, fix the prompt or the human review step.
4. **The analyst signs the label.** The agent drafts; the investigator owns what enters the case file.

## Pricing and scale

Reasoning tokens are billed as output tokens. Table 10.2 lists standard short-context rates for the four models in this lab (OpenAI pricing page, November 2026). Above 272K input tokens, the **entire request** uses long-context rates. This lab’s JSON is far below that threshold.

**Table 10.2.** Standard input and output price per 1 million tokens. OpenAI pricing page, November 2026.

| Model | Input | Output |
|---|---:|---:|
| `gpt-6-luna` | $0.10 | $0.50 |
| `gpt-6-astra` | $10 | $50 |
| `gpt-5-mini` | $0.25 | $2.00 |
| `gpt-5-nano` | $0.05 | $0.40 |

**Scale example (illustrative, not measured in this lab).** The exercise JSON is about **3 KB**. A production bridge packet with transaction, message, and logs can approach **1 MB**. At the token density of this JSON (~2.5 bytes per token), 1 MB is roughly **400,000 input tokens**, which triggers long-context pricing for `gpt-6-astra` (**$20** per million input on that tier). Input alone is then on the order of **$8 per trace**. At **1,000 traces per day**, that is roughly **$8,000 per day** of input cost before reasoning and answer tokens. Treat that figure as a floor for planning budgets, not as an invoice from this toy file.

## Instructor summary

Reasoning matters whenever the agent must **choose among plausible records**, not merely format a lookup. Investigation workflows—crypto attribution, fraud triage, sanctions screening, incident timelines—all share the same risk: the model returns a confident label that overstates what the evidence file actually proves.

On this bridge specimen, every model found the right destination at both effort levels. Quality diverged on the **proof sentence**. `gpt-6-astra` remained correct at low and high effort. `gpt-6-luna` was complete at high effort and incomplete at low. `gpt-5-mini` and `gpt-5-nano` called a string match cryptographic proof at both efforts. More reasoning helped the capable models state limits; it made the weaker models more certain of a false check.

**Takeaway for practice:** freeze one case, change one dial (model or effort), and do not accept any result until a human approves the evidence label—not just the transaction hash.
