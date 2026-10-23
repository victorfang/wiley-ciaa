# Chapter 6 — Reliable LLMs for Evidence-Based Investigations

*Cryptocurrency Investigation with Agentic AI* · Victor Fang · Wiley · 2026  
**Author:** [VictorFang.com](https://www.VictorFang.com) · [LinkedIn](https://www.linkedin.com/in/drvictorfang/) · [X](http://x.com/vicfcs)

---

## What this lab demonstrates

Same Bitcoin address, two answer paths, two models:

1. **Weak LLM only (`gpt-5-mini`)** — answers from training memory (can invent plausible but wrong numbers).
2. **Tool-grounded `gpt-6-luna` + thin harness** — must call Blockstream Esplora; harness checks tool health and answer-vs-evidence match.

This chapter introduces **three stages of agentic AI engineering** (prompt, context, harness). Document retrieval (RAG) is deferred to a later chapter.

| Discipline | Primary question | In this lab |
|------------|------------------|-------------|
| **Prompt engineering** | Did we express the task clearly? | Path A vs Path B instructions and output shape |
| **Context engineering** | Did the model receive the right information at the right time? | Esplora tool JSON injected before the final answer |
| **Harness engineering** | Can the model complete the whole task reliably under real constraints? | Force tool use, validate address, fail soft on tool errors, check answer matches evidence, save run logs |

## Why models hallucinate here (demo intuition)

Large language models do **not** query the Bitcoin network by default. When asked for live address statistics, they often:

- Reuse a **memorable but incomplete** story from training data (e.g. “genesis coinbase = 50 BTC, one transaction”).
- Sound confident while the chain has moved on for years.
- Fill gaps instead of saying “I don’t have live data” — especially when the prompt asks for concrete numbers.

That is **hallucination**: fluent text that is not grounded in current evidence.

This demo uses the well-known genesis-block reward address:

`1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`

People have sent dust and donations to it for years, so the real balance and transaction count are far from the “50 BTC / 1 tx” folklore.

### Harness engineering in this lab (beginner view)

Prompts alone are not enough. A thin **harness** wraps the model so the investigation fails closed instead of sounding fluent and wrong:

| Harness check | What it prevents |
|---------------|------------------|
| `tool_choice="required"` then `"none"` | Skipping the explorer / calling tools again after answering |
| Address shape + “must not change address” | Injection / swapped target |
| Tool returns `ok: false` on network/HTTP errors | Inventing numbers when Esplora is down |
| Abstain if tool failed (no second LLM invent step) | Unsupported conclusions after silent tool failure |
| `assert_answer_matches_evidence` | Prose that drifts from tool BTC / tx count |
| Saved `{weak}_vs_{model}_{address6}_{time}` artifacts | Missing audit trail (both models, address, timestamp, evidence) |

This is educational and intentionally short — not a full production agent platform.

---

## Technical causes of LLM hallucination

### What “hallucination” means in NLG / LLMs

In natural language generation research, hallucination usually means generating content that is **nonsensical or unfaithful** to a provided source (Maynez et al., 2020; Ji et al., 2023). For open-ended LLMs the notion broadens: the model may diverge from the user input, contradict its own earlier context, or conflict with verifiable world knowledge (Zhang et al., 2023/2025; Huang et al., 2025).

Mechanically, an autoregressive LLM samples the next token from a conditional distribution \(P(x_t \mid x_{<t})\). It does **not** maintain a separate “truth database” or live blockchain client. Truthfulness is an emergent side-effect of statistics in training data, post-training alignment, and (optionally) tools at inference. When those pressures favor fluent guessing over abstention, the model emits confident falsehoods.

### Different types / taxonomies

Researchers use overlapping but useful taxonomies:

#### 1. Intrinsic vs extrinsic (source-grounded NLG)

From summarization and related NLG work (Maynez et al., 2020; Ji et al., 2023):

| Type | Definition | Crypto-investigation example |
|------|------------|------------------------------|
| **Intrinsic** | Output **contradicts** the source / context you gave | Tool returns 57.43 BTC; model says balance is 50 BTC |
| **Extrinsic** | Output adds content **not supported** by the source | Model invents an exchange attribution or owner name not in the case file |

#### 2. Factuality vs faithfulness (LLM-oriented)

Huang et al. (2025) (survey, ACM TOIS / arXiv:2311.05232) split LLM hallucinations into:

| Type | Definition | Subtypes / notes |
|------|------------|------------------|
| **Factuality hallucination** | Divergence from **verifiable real-world facts** | **Factual inconsistency** (wrong fact) vs **factual fabrication** (invented fact) |
| **Faithfulness hallucination** | Divergence from **user instruction**, **provided context**, or **self-consistency** | Instruction inconsistency; context inconsistency; logical inconsistency |

Our Path A “50 BTC / 1 tx” answer is primarily a **factuality** failure (wrong live-world state). If the model had been given Esplora JSON and still said 50 BTC, that would also be a **faithfulness / intrinsic** failure.

#### 3. Input- / context- / fact-conflicting

Zhang et al. (2023; CL 2025, “Siren’s Song…”) use a three-way split:

| Type | Definition |
|------|------------|
| **Input-conflicting** | Conflicts with the user’s source input / instructions |
| **Context-conflicting** | Contradicts earlier model-generated context (self-inconsistency) |
| **Fact-conflicting** | Conflicts with established world knowledge / is unverifiable |

Path A in this demo is **fact-conflicting** (and outdated relative to current chain state). Path B is designed to reduce that class by forcing retrieval before claims.

### Root causes (data → training → inference)

Huang et al. (2025) organize causes across the model lifecycle:

#### A. Data-related causes

1. **Flawed / biased corpora** — misinformation, duplicated myths, social biases, and “imitative falsehoods” (models learn frequently repeated wrong statements as if they were facts).
2. **Knowledge boundary** — the pretraining cutoff and sparse coverage of rare or **time-varying** facts. Live Bitcoin balances are a canonical boundary case: even a “correct” training snapshot becomes stale.
3. **Inferior knowledge utilization** — the model may have seen relevant tokens but fail to **recall / bind** them correctly at generation time (knowledge exists in weights but is not retrieved into the answer).

In this demo, “genesis reward = 50 BTC” is a **high-frequency training pattern**. Later deposits to the same address are lower-salience, time-varying facts → the model defaults to the myth.

#### B. Training-related causes

1. **Pretraining objective** — next-token cross-entropy rewards local fluency and pattern completion, not calibrated truth. Arbitrary one-off facts are hard to predict from context alone; grammar is easy. Kalai et al. (2025/2026) argue pretraining hallucinations are statistically natural classification-like errors under next-token learning.
2. **Alignment / post-training** — RLHF and instruction tuning can improve helpfulness but do not fully erase guessing. If users reward confident complete answers, models learn to **sound sure**.
3. **Capability gaps** — limited long-context binding, weak multi-hop reasoning, or poor tool-use discipline can produce contradictions even when evidence is available.

#### C. Inference-related causes

1. **Decoding stochasticity** — sampling (temperature, top-\(p\)) can surface lower-probability but fluent fabrications.
2. **Exposure bias / error compounding** — early wrong tokens condition later ones; a fabricated “50 BTC” makes “1 transaction” more likely as a coherent story.
3. **Prompt pressure** — instructions like “give concrete numbers; do not say you lack data” (used deliberately in Path A) suppress abstention and **induce** fabrication.

#### D. Evaluation incentives (why hallucinations persist)

OpenAI’s analysis (Kalai, Nachum, Vempala & Zhang; arXiv:2509.04664; Nature 2026; OpenAI blog *Why language models hallucinate*) argues:

- Pretraining creates pressure to guess when a fact is not reliably distinguishable from alternatives.
- Many **benchmarks score accuracy** and give little credit for “I don’t know,” so guessing when uncertain raises leaderboard scores.
- Mitigation is partly **socio-technical**: change scoring / rubrics to reward calibrated abstention, not only add more hallucination tests.

That framing matters for investigators: a model optimized as a good test-taker may prefer a confident wrong balance over a careful abstention.

### Mapping causes → this Bitcoin experiment

| Mechanism | What happened in Path A |
|-----------|-------------------------|
| High-frequency myth in pretraining | “Coinbase = 50 BTC” |
| Knowledge boundary / stale facts | No live Esplora; post-2009 deposits ignored |
| Prompt that forbids abstention | Model must emit numbers |
| No tool grounding | Nothing constrains tokens to current chain state |
| Coherent story completion | “1 tx / 50 BTC / 0 spent” forms a fluent package |

| Mechanism | What Path B changes |
|-----------|---------------------|
| Tool call before claims | Evidence JSON enters the context |
| Answer constrained to tool fields | Prefers `confirmed_*_btc` from Esplora |
| Provenance | Source URL, retrieval time, raw SHA-256 |
| Thin harness | Fail soft on tool errors; check answer matches evidence |

Tool calling does not “cure” the model’s weights; it **changes the inference context** so the next-token distribution is conditioned on retrieved evidence. (Document retrieval / RAG is a related idea for a later chapter.)

### Mitigations (brief)

| Approach | Idea |
|----------|------|
| **Abstention / uncertainty** | Prefer “unverifiable” when evidence is missing; open-rubric evals that penalize wrong guesses (Kalai et al.) |
| **Tool grounding** | Call explorers / APIs (this demo) |
| **Harness checks** | Validate I/O, abstain on tool failure, match answer to evidence (this demo) |
| **Faithfulness checks** | Entailment / citation checks against source (Maynez et al.; later LLM judges) |
| **Self-consistency / verification** | Sample multiple answers; abstain on disagreement (used in related evaluation work) |

For crypto investigations, treat LLM prose as a **draft** until each numeric/attributive claim cites a tool result or explorer export.

---

## Side-by-side results (recorded run)

Captured **2026-10-23T03:47:50Z**. Path A is **`gpt-5-mini`** with no tool. Path B is **`gpt-6-luna`** with Esplora and the harness. Full artifacts:

- [`results/gpt-5-mini_vs_gpt-6-luna_1A1zP1_20261023T034802Z.json`](results/gpt-5-mini_vs_gpt-6-luna_1A1zP1_20261023T034802Z.json)
- [`results/gpt-5-mini_vs_gpt-6-luna_1A1zP1_20261023T034802Z.txt`](results/gpt-5-mini_vs_gpt-6-luna_1A1zP1_20261023T034802Z.txt)

| Metric | A. `gpt-5-mini` only (hallucinated) | B. `gpt-6-luna` + Esplora |
|--------|--------------------------------------|---------------------------|
| Confirmed tx count | **1** | **67,099** |
| Confirmed received | **50 BTC** | **57.6863958 BTC** |
| Confirmed spent | **0 BTC** | **0 BTC** |
| Confirmed balance | **50 BTC** | **57.6863958 BTC** |
| Evidence | none | Blockstream API + SHA-256 of raw JSON |
| Harness | — | tool ok, answer matched evidence |

`gpt-5-mini` recycled the coinbase myth. `gpt-6-luna` beat that answer by calling the chain tool; the harness accepted the prose only because the transaction count and balance were copied from the tool JSON.

**Taxonomy label for Path A:** factuality / fact-conflicting hallucination (outdated parametric “fact”), induced by a no-tool, no-abstention prompt.

### Earlier memory-only runs (kept)

These files stay under the model id they were run with. They are the same address and the same Path A prompt, on earlier dates. The Esplora row is the tool result saved in that same run, not today’s balance.

| Model (Path A) | Confirmed txs | Received / balance | Still wrong? | Artifact |
|----------------|---------------|--------------------|--------------|----------|
| `gpt-4o-mini` | 1 | 50 BTC | yes (classic myth) | [`gpt-4o-mini_1A1zP1_…`](results/gpt-4o-mini_1A1zP1_20260910T202204Z.json) |
| `gpt-5-mini` | 1 | 50 BTC | yes (same myth) | [`gpt-5-mini_1A1zP1_…`](results/gpt-5-mini_1A1zP1_20260910T210304Z.json) |
| `gpt-5` | 3,769 | 68.561 BTC | yes (different fabrication) | [`gpt-5_1A1zP1_…`](results/gpt-5_1A1zP1_20260910T210246Z.json) |
| `gpt-4.1-mini` | 305 | 68,012.5 received / 12.51 balance | yes | [`gpt-4.1-mini_1A1zP1_…`](results/gpt-4.1-mini_1A1zP1_20260915T041617Z.json) |
| Esplora on 2026-09-10 | **65,746** | **57.43423379 BTC** | — | the `gpt-4o-mini` / `gpt-5` / `gpt-5-mini` runs |
| Esplora on 2026-09-15 | **65,793** | **57.46952256 BTC** | — | the `gpt-4.1-mini` run |

`gpt-5-mini` remains the weak-model example: with no tool, it still reports 1 transaction and 50 BTC. On 2026-09-10, `gpt-5` with no tool invented a different wrong balance. The 2026-10-23 win is `gpt-6-luna` with the tool and the harness.

### A. Hallucinated answer (`gpt-5-mini`, verbatim)

```text
1. Confirmed transaction count: 1
2. Total confirmed BTC received: 50.00000000 BTC
3. Total confirmed BTC spent: 0.00000000 BTC
4. Current confirmed BTC balance: 50.00000000 BTC
```

### B. Tool-grounded answer (`gpt-6-luna`, verbatim)

```text
- Confirmed transaction count: 67099
- Confirmed received: 57.6863958 BTC
- Confirmed spent: 0.0 BTC
- Confirmed balance: 57.6863958 BTC

Source: https://blockstream.info/api/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Retrieved: 2026-10-23T03:48:00.101769+00:00 (UTC)
Raw-response SHA-256: 3c1aa0e0f9234012165f719851b27ccfb679f5c86b81dff8fb35550b98acbf9c
```

## How the two prompts differ

### Path A — unsafe (memory only)

The model is told to answer from its own knowledge and to give concrete numbers. It has **no** blockchain tool and **no** retrieved document. That is the failure mode this chapter illustrates.

```text
You are a blockchain analyst. Answer from your own knowledge only.
Do not say you lack live data. Do not ask to look anything up.
Give concrete numbers for Bitcoin address <address>:
  confirmed tx count / received / spent / balance
```

### Path B — safer (tool grounding + thin harness)

The model **must** call `get_bitcoin_address_summary` (Blockstream Esplora) before stating facts. The final answer is constrained to that tool JSON (including precomputed BTC fields, source URL, retrieval time, and response hash). The harness then checks that the prose still matches those numbers.

| Pattern in this lab | What grounds / enforces the answer |
|---------------------|------------------------------------|
| Prompt engineering | Clear role, required fields, no attribution |
| Context engineering | Live tool JSON in the message history |
| Harness engineering | Force tool → validate → abstain on failure → check answer |

(Document retrieval / RAG is intentionally out of scope here.)

Path A is pinned to `gpt-5-mini` so the lab still shows a fluent wrong answer. Path B is `gpt-6-luna`. Override with `OPENAI_WEAK_MODEL` and `OPENAI_MODEL` if your API project uses other ids.

## Run the demo

```bash
cp .env.example .env   # set OPENAI_API_KEY (or OPENAI_API_KEY_VF)
pip install -r requirements.txt

# optional: Path A weak model (default gpt-5-mini), Path B (default gpt-6-luna)
# export OPENAI_WEAK_MODEL=gpt-5-mini
# export OPENAI_MODEL=gpt-6-luna

python3 ch6-hallucination-demo.py
```

Each run writes a new pair under `results/`. The name includes both model ids, so a later run does not overwrite an earlier one:

`{weak-model}_vs_{model}_{address6}_{YYYYMMDDTHHMMSSZ}`

- `*.json` — both models, address, timestamp, both answers, evidence
- `*.txt` — same content in a readable report

Example: `gpt-5-mini_vs_gpt-6-luna_1A1zP1_20261023T034802Z.json`

Older single-model files (`gpt-4o-mini_…`, `gpt-5-mini_…`, `gpt-5_…`, `gpt-4.1-mini_…`) stay in `results/` under the model that produced them.

Live chain stats change over time; re-run to refresh Path B. Path A may still hallucinate the same outdated genesis story.

## Files

| File | Purpose |
|------|---------|
| `ch6-hallucination-demo.py` | Side-by-side LLM-only vs tool-grounded demo |
| `requirements.txt` | `requests`, `openai` |
| `.env.example` | API key / model template |
| `results/` | Saved comparison artifacts (JSON + text) |

## Takeaway for investigators

Do not trust an LLM for **current** balances, tx counts, or attribution unless the answer is tied to a **cited tool result or explorer export**, and ideally checked by a harness. Fluency is not evidence.

---

## References

1. Maynez, J., Narayan, S., Bohnet, B., & McDonald, R. (2020). *On Faithfulness and Factuality in Abstractive Summarization*. ACL 2020. https://aclanthology.org/2020.acl-main.173/ · https://arxiv.org/abs/2005.00661

2. Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y., Madotto, A., & Fung, P. (2023). *Survey of Hallucination in Natural Language Generation*. ACM Computing Surveys. https://arxiv.org/abs/2202.03629

3. Zhang, Y., Li, Y., Cui, L., Cai, D., Liu, L., Fu, T., Huang, X., Zhao, E., Zhang, Y., Chen, Y., Wang, L., Luu, A. T., Bi, W., Shi, F., & Shi, S. (2023/2025). *Siren’s Song in the AI Ocean: A Survey on Hallucination in Large Language Models*. Computational Linguistics 51(4). https://arxiv.org/abs/2309.01219 · https://aclanthology.org/2025.cl-4.9/

4. Huang, L., Yu, W., Ma, W., Zhong, W., Feng, Z., Wang, H., Chen, Q., Peng, W., Feng, X., Qin, B., & Liu, T. (2025). *A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions*. ACM Transactions on Information Systems. https://doi.org/10.1145/3703155 · https://arxiv.org/abs/2311.05232

5. Kalai, A. T., Nachum, O., Vempala, S. S., & Zhang, E. (2025). *Why Language Models Hallucinate*. arXiv:2509.04664. https://arxiv.org/abs/2509.04664  
   Journal version: Kalai et al. (2026). *Evaluating large language models for accuracy incentivizes hallucinations*. *Nature*. https://doi.org/10.1038/s41586-026-10549-w  
   OpenAI summary: https://openai.com/index/why-language-models-hallucinate/

---

*Companion code · [Apache License 2.0](../LICENSE)*
