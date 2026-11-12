# Python Lab: Reasoning Through a Cross-Chain Bridge Match

Victor Fang, 2026 · *Cryptocurrency Investigation with Agentic AI* · Chapter 10

## Goal and Impact

**Goal.** This lab builds a reasoning agent and tests it on one real bridge trace: a Wormhole transfer of 550 USDT from Ethereum to BNB Smart Chain. The same case runs on a stronger pair of models and a weaker pair, each at low and high reasoning effort. Model names will change. The way an investigator grades an agent should not.

The agent must pick one destination from three candidates. Two rows are planted. A neighboring message can share the recipient, the amount, and a closer clock. The join is the VAA id: emitter chain, emitter address, and sequence. A tidy match of the other fields can put the wrong transaction in the case file.

Students leave able to:

1. Score an agent on two lines: the destination, and the proof sentence.
2. Tell a correct trace from a correct hash carrying a false evidence label.
3. Decide when raising reasoning effort helps, and when it only makes a wrong label more certain.

## Experiment Setup

The input is one source transfer and three destination candidates, all on 11 December 2024. The source sequence is 426560. Candidate 1 carries that sequence. Candidates 2 and 3 are planted neighbors, 426559 and 426561. The JSON does not label them as planted. Candidate 2 copies the recipient and the amount and lands eight minutes sooner, so a clock-and-amount ranking prefers it.

The expectation is fixed before any model runs. Retain only the matching sequence. Reject another sequence even when the amount matches. A fully correct answer also says the file contains no signed VAA, so the match compares records. Guardian signatures were not checked. Table 10.20 is that assessment.

**Table 10.20.** Expected assessment of the source transfer and the three destination candidates.

| Record | Chain | VAA sequence | Time (UTC) | Amount | Assessment |
|---|---|---:|---|---|---|
| Source | Ethereum | 426560 | 19:27:11 | 550 USDT | Source transfer to trace |
| Candidate 1 | BSC | 426560 | 19:41:28 | 550 USDT | Retain: matching sequence and amount; verify VAA payload and successful execution |
| Candidate 2 | BSC | 426559 | 19:35:10 | 550 USDT | Reject: references a different source message |
| Candidate 3 | BSC | 426561 | 19:42:01 | 549.8 USDT | Reject: different sequence and recipient |

## Files and Quick Start

`ch10_reason_simple.py` asks one question. `.env` holds `OPENAI_API_KEY`. Each answer is saved as `simple_results/<model>_<effort>.txt`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install openai python-dotenv
cp .env.example .env
.venv/bin/python ch10_reason_simple.py
```

The case JSON stays fixed. The loop changes the model and `reasoning_effort`. The prompt calls the VAA id a "cryptographic identifier" on purpose. A careful agent matches the sequence and says that no signature was checked. A careless agent repeats that word as a finding.

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

## The Reasoning Dial

Reasoning effort is the control to keep. On Chat Completions the parameter is `reasoning_effort`. On the Responses API it is `reasoning.effort`. This lab sends `low` and `high`. Leave the parameter off and the usual default is `medium`. The hard setting in this script is the value `high`.

`low` is a short pass, biased toward speed and cost. `high` asks the model to think more completely before it answers. Other levels exist and depend on the model. A value the model rejects returns HTTP 400, so check the current model page before adding one.

The API returns a count of reasoning tokens, in `usage.completion_tokens_details.reasoning_tokens` on Chat Completions. It does not return the reasoning text. Those tokens are hidden, they occupy context, and they are billed as output tokens. Grade the written answer. A larger count is a larger bill. List prices are in Pricing, Table 10.2.

The same idea shows up at other APIs, with a different control and a different view of the reasoning. Table 10.4 is the comparison. Checked against the vendor docs in November 2026.

**Table 10.4.** How other reasoning APIs differ from this lab.

| API | How reasoning is set | What comes back |
|---|---|---|
| OpenAI, this lab | `reasoning_effort`, from a light pass to a hard one. This script sends `low` and `high`. | A token count. The reasoning text stays hidden. A summary is a separate opt-in on the Responses API. |
| Anthropic | Newer Claude models think adaptively. `effort` (`low` through `max`) steers how readily and how deeply. Older models take a token budget, `budget_tokens`. | A summary only if you ask for one. Many current models omit the text by default. The full thinking is billed as output either way. |
| DeepSeek | Thinking is on by default. `reasoning_effort` is `low`, `high`, or `max`. A `thinking` flag can turn it off. | The chain of thought itself, in `reasoning_content`, beside the answer. With tools, that text has to be passed back on the next turn. |
| Kimi | Thinking models take `reasoning_effort` of `low`, `high`, or `max`. The default on the current flagship is `max`. | `reasoning_content` as well. Later turns keep that text in context, and it continues to be billed. |

Two habits survive the vendor change. Reasoning tokens are part of the bill, whether or not you can read them. A readable chain of thought is still not a signature check. Grade the proof sentence on the answer. If the API returns the reasoning, read it as a draft of how the model got there.

## Results

The GPT-6 pair is `gpt-6-luna` and `gpt-6-astra`. The GPT-5 pair is `gpt-5-mini` and `gpt-5-nano`. Table 10.3 puts high effort beside low effort. The verdict is the last column.

**Table 10.3.** Lab verdicts on this case. Every cell retains sequence 426560.

| Model | High effort | Low effort | Verdict |
|---|---|---|---|
| `gpt-6-luna` | 401 reasoning tokens. A record match, and it says this is not an on-chain verification. | 124 reasoning tokens. Right sequence. The limit is unstated. | Correct at high. Incomplete at low. |
| `gpt-6-astra` | 512 reasoning tokens. The id identifies a message. It is not cryptographic proof. | 0 reasoning tokens. The opening still says the JSON has no signed VAA, so this is not a cryptographic verification. | Correct at both. |
| `gpt-5-mini` | 6,336 reasoning tokens. "Exact VAA ID equality is cryptographic proof." | 192 reasoning tokens. The row is "cryptographically attributable." | Wrong proof sentence at both. |
| `gpt-5-nano` | 8,000 reasoning tokens. Heads a string match "Cryptographic identifier." | 320 reasoning tokens. Calls it a "cryptographic linkage," and misreads the clock. | Wrong proof sentence at both. |

All eight runs keep candidate 1 and reject 426559 and 426561, the rows in Table 10.20. The sooner look-alike fooled none of them. The interesting difference is the sentence that follows the hash. Three pairs from the saved answers show it.

### The same match, opposite labels

`gpt-6-astra`, at low effort, with no reasoning tokens counted:

> Strictly, the VAA ID is a message identifier, not itself a cryptographic hash or signature proof. The reported guardian set index `4` and signature count `13` do not permit signature verification without the actual signed VAA.

`gpt-5-mini`, at high effort, after 6,336 reasoning tokens:

> Root-cause for decision: exact VAA ID equality is cryptographic proof.

Both kept candidate 1. `gpt-6-astra` refused the word the prompt had supplied, and it noticed that a reported signature count is only a field in the JSON. `gpt-5-mini` took that same word and made it the cause of the decision. Equal strings in a case file are a record match. This run checked no guardian signature.

### More effort adds a caveat, or hardens a mistake

`gpt-6-luna` at high effort closes with the sentence a case note needs:

> This is a logical match from the provided records, not an independent on-chain verification of the transaction.

`gpt-6-luna` at low effort stops once the fields line up:

> only candidate 1 matches the source message's exact VAA ID, destination chain, recipient, and asset amount.

The higher effort bought one sentence, at 401 tokens. `gpt-5-mini` moves the other direction. At low effort the row is "cryptographically attributable." At high effort that hedge becomes the root cause. More tokens, more certainty, the same false check.

### A model can invent a reason to reject

`gpt-5-nano` at low effort, rejecting candidate 2:

> the timestamp precedes the expected post-emission window for this VAA

The sequence mismatch is a real reason to reject that row. The clock is not. Candidate 2 lands at 19:35:10, eight minutes after the source at 19:27:11, the same direction as the true destination. The answer stacked a false timing failure on a true sequence failure. `gpt-5-nano` at high effort does not make that clock claim. It also never says the signatures were unchecked, and it spends 8,000 reasoning tokens to reach the same destination `gpt-6-luna` reached in 401.

## What to carry to the next agent

1. **Score the join and the proof sentence separately.** A right hash with a false evidence label is a wrong investigation. Pass the first line, and the second line is still open.
2. **Treat a strong word in the prompt as a hypothesis.** If the question says "cryptographic," mark whether the agent checked a signature or repeated the label. An echo still has to be tested against the file.
3. **Raise effort against a rule written first.** Run low. Buy high only when low missed a rule such as "state that signatures were not checked." If high only grows more certain about a false word, fix the prompt or the reviewer.
4. **The analyst signs the label.** The agent drafts. A sentence that says cryptographic proof has claimed a verification the tool never ran.

## Pricing

Reasoning tokens are billed as output tokens. Table 10.2 is the published list price for the four models in this lab, per 1 million tokens on the short-context tier. A request above 272K input tokens is priced higher for the whole request. This lab file is under that line. Confirm the current rate card before a production run. Rates move.

**Table 10.2.** Standard input and output price per 1 million tokens. OpenAI pricing page, November 2026.

| Model | Input | Output |
|---|---:|---:|
| `gpt-6-luna` | $0.10 | $0.50 |
| `gpt-6-astra` | $10 | $50 |
| `gpt-5-mini` | $0.25 | $2.00 |
| `gpt-5-nano` | $0.05 | $0.40 |

This lab's JSON is about 3 KB. A working bridge file, with the transaction, the message, and the logs, can be about 1 MB, and a desk may trace about 1,000 such cases a day. At about 2.5 bytes per token, the density of this JSON, 1 MB is about 400,000 input tokens. That is past 272K, so `gpt-6-astra` prices the whole request at the long-context rate, $20 per million input tokens. The input alone is about $8 a trace and about $8,000 a day for those 1,000 traces. Reasoning tokens are extra, billed as output at $75 per million, and this lab did not measure them on a 1 MB file. The $8,000 is the floor for that day's case load.

## Conclusion

Reasoning is what makes an agent usable once the task is a judgment, not a lookup. An investigation agent, in crypto or anywhere else, is handed records that compete: several rows can share a name, an amount, a time, or a phrase from the prompt. Matching those fields produces a confident action. Reasoning is the step that holds the competing explanations, keeps the fact that actually decides the case, rejects the plausible neighbor, and states what the file does not prove. Without that step the agent still returns an answer, and the answer can be the wrong record with a label stronger than the evidence. The same failure shows up in any agent that attributes, triages, or recommends: a sanctions screen, a fraud queue, an incident timeline. The bridge trace in this lab is one specimen. A closer clock and a copied amount stood in for the neighboring message, and a string match was labeled cryptographic proof when no signature had been checked. The sentence that states the limit is what an investigator can defend.

Every model found the correct destination: candidate 1, sequence 426560, at both low and high effort. The investigation then split. `gpt-6-astra` was correct at both efforts. `gpt-6-luna` was correct at high effort and incomplete at low effort. `gpt-5-mini` and `gpt-5-nano` were wrong at both efforts, because they called a string match cryptographic proof. Extra reasoning made the capable model's caveat appear, and it made the weaker model's false label more certain. The destination being right did not make the investigation right. Freeze one case, change one dial, and accept a result into the case file only after a person has accepted the evidence label beside it.
