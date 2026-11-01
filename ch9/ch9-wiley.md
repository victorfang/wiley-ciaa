## Python Lab: An AI Agent That Reads the KyberSwap Attacker's Notes

### Goal of This Lab

On November 22, 2023, an attacker drained about $48 million from KyberSwap Elastic liquidity pools. They left behind three kinds of text on Ethereum:

- **Letters in transaction data.** Three transactions carry plain English in their `input` field, ending with a "treaty" that demands control of Kyber, signed "Kyber Director." Etherscan displays it as `Call 0x546f2041 Method`, because the first four bytes ("To A") look like a function selector.
- **A diary of the attack.** The attack contract was built with Foundry's test logging still switched on. While the exploit ran, it published about 680 debug events into the transaction logs, such as "Step 3, building up fake liquidity." and "Step 4, pulling off the doubling move."
- **Strings in the contract code.** The same phrases are stored as constants in the deployed bytecode.

**Why this problem matters.** On-chain messages from attackers are now routine in DeFi incidents: ransom notes, bounty negotiations, taunts and debug output. They are public and permanent, but they sit in raw hexadecimal across hundreds of logs, and explorers often mislabel them. Turning them into evidence means decoding calldata, event logs and bytecode, then reconciling large integers against token transfers. That is slow, error-prone work for a human.

**Why an AI agent is the right tool.** The investigation is open-ended. Which transaction to decode first, which number deserves checking, and what "fake liquidity" means cannot be scripted in advance. A language model can plan and interpret, but it is unreliable with raw bytes and 22-digit arithmetic. The agent in this lab splits the work: **the model reasons, Python computes.** The model decides what to examine, and small exact tools do the decoding and the math.

In this lab you will build a 99-line agent that decodes every hidden message in the case, reconstructs the attacker's playbook, and checks the attacker's own numbers against the transfers that actually happened.

### Source Files and Setup

- `kyber_agent.py`: the agent, with six tools, the agent loop and a grounding check.
- `prompt.txt`: the system prompt, with the rules of evidence and the report format.
- `data/kyber_cache.json`: cached Ethereum evidence, with 5 transactions, 937 logs, token metadata and the attack contract's bytecode.
- `fetch_cache.py`: optional. Rebuilds the cache from any Ethereum RPC endpoint.

The agent needs Python 3.10 or later and the `openai` package. Everything else comes from the standard library. The evidence is cached, so no blockchain API key is needed.

```bash
pip install openai
export OPENAI_API_KEY=sk-...        # or put it in a .env file; OPENAI_MODEL is optional
```

### Quick Start

```bash
python kyber_agent.py
python kyber_agent.py --question "Which pools were hit, and where did the proceeds go?"
```

A run takes one to two minutes. It prints each tool call as it happens, then the report. It saves `runs/<timestamp>/report.md` and `trace.json`, a log of every tool call with its arguments and results.

### Key Tools

- `case_index()`: lists the evidence, including times, blocks, sender nonces and labeled addresses.
- `decode_input(tx_hash)`: distinguishes a human-written message from a contract call.
- `runtime_logs(tx_hash, start, limit)`: decodes the attacker's debug events into readable lines.
- `bytecode_strings(address)`: extracts readable strings from contract bytecode.
- `token_flows(tx_hash, address)`: computes exact net token positions from ERC-20 `Transfer` logs.
- `cross_check(tx_hash, amount)`: finds a number, within ±1, in transfers and logs. `"*"` sweeps for off-by-one gaps.

### Key Concepts

**Tool calling.** The model never touches the data directly. It sees a list of tool names, descriptions and parameter types. When it needs evidence, it returns a structured request such as `cross_check(tx_hash="0x396a…", amount="*")`. Python runs the function and returns JSON.

**The agent loop.** The model calls tools, reads the results and decides what to do next, round after round, until it has enough evidence to write its report. Each round it may request several tools at once. A step limit (12 rounds by default) bounds the cost.

**Grounding.** Every claim in the report must trace back to a tool result. The code enforces part of this automatically, and the saved trace lets a human audit the rest.

### The Prompt

```text
You are a DeFi forensic investigator. Use only tool results as evidence; cite tx hash prefixes and log indexes.
Plan, call tools, verify numbers with cross_check before relying on them, and never guess identities behind addresses.
When two numbers differ, test simple arithmetic (prior balance + inflow, sums across runs) and state whether they reconcile.
Separate OBSERVED (on-chain, decoded) from ATTRIBUTED (labels, public reports) from INFERRED (your reasoning).
Final answer: a markdown report with Timeline, Decoded messages, Attacker playbook, Log-vs-flow verification, Gaps, Next steps.
```

The core of the prompt is the fourth line, which sets out **three levels of evidence**:

- **OBSERVED** facts are decoded directly from the chain, such as a message's text or a transfer amount.
- **ATTRIBUTED** facts come from someone else, such as an Etherscan label saying "KyberSwap Exploiter 1."
- **INFERRED** claims are the model's own interpretation.

Keeping these apart is what makes a forensic report defensible. A label is not proof of identity, and an interpretation is not a fact.

The other lines target known AI failures:

- **"Use only tool results"** and **citations** prevent answers from memory and let a reader check every claim.
- **"Never guess identities"** stops the model from turning an address label into an accusation.
- **The arithmetic rule** was added after a test run called two numbers a mismatch when they differed only by the wallet's prior balance.

### Core Code

**Functions become tools.** Each tool's docstring is the description the model reads, and its type hints become the parameter schema. Adding a tool means writing one typed function:

```python
SCHEMAS = [{"type": "function", "name": n, "description": f.__doc__, "strict": True, "parameters": {...
            "properties": {p: {"type": "integer" if q.annotation is int else "string"}
                           for p, q in inspect.signature(f).parameters.items()},
```

**The agent loop.** Each round, the model either requests tools or writes its report. Three details make the loop safe to use on evidence:

- `tool_choice="required"` on round 0 forces a tool call, so the model cannot answer from memory.
- Tool errors go back as data, so a bad argument is corrected on the next round instead of crashing the run.
- `max_steps` (12 by default) stops the loop. `store=False` means OpenAI does not keep the conversation; the script sends the full history each round.

```python
for step in range(args.max_steps):
    r = client.responses.create(model=args.model, instructions=(ROOT / "prompt.txt").read_text(),
                                input=history, tools=SCHEMAS, store=False,
                                tool_choice="required" if step == 0 else "auto")
    history += [o.model_dump(mode="json", exclude_none=True) for o in r.output]
    if not (calls := [o for o in r.output if o.type == "function_call"]): break
    for c in calls:
        try: result = TOOLS[c.name](**json.loads(c.arguments))
        except Exception as e: result = {"error": f"{type(e).__name__}: {e}"}
        history.append({"type": "function_call_output", "call_id": c.call_id, "output": json.dumps(result)})
```

### Results

The agent decoded three messages the attacker wrote into transaction calldata. These are the striking lines. Etherscan shows the last message as a contract call, because its first four bytes look like a function selector.

**`0x7a891258…`, November 22, one hour after the exploit.** After taking about $48 million, the attacker postpones talks until they have had a nap:

> Negotiations will start in a few hours when I am fully rested.

**`0x5c27d8e9…`, November 28.** The attacker complains, then sets a public deadline:

> I have received (mostly) threats, deadlines, and general unfriendliness from the executive team. That's ok, I don't mind.
>
> I plan to release it on Nov. 30 at Noon UTC, sharp.

**`0x0479da9d…`, November 30, the "treaty."** The demands are for the company itself, not a bounty:

> * Complete executive control over Kyber (the company)
> * Surrender of all Kyber (the company) assets … servers, passwords, code, social channels, any and all creative and intellectual property of Kyber.

The attacker then explains the exploit as a rounding mistake, and offers to run the company:

> You haven't done anything wrong. A small error was made, rounding in the wrong direction, it could have been made by anyone. Simply bad luck.
>
> Employees, under the new regime your salary will be doubled.
>
> It will no longer be the 7th most popular DEX, but rather, an entirely new cryptographic project.
>
> The rebate will be for 50% of the losses you have incurred. … it is also more than you deserve.
>
> This is my best offer. This is my only offer. I require my demands to be met by December 10, otherwise, the treaty falls through.
>
> Should I be contacted by agents from any of the 206 sovereignties … the treaty falls through. In this case, rebates will total to exactly 0.
>
> I may be contacted on telegram: @Kyber_Director
>
> - Kyber Director

This lab shows how a language model becomes useful on a DeFi investigation by working as an agent. Given tools for calldata, event logs, and token flows, the model plans its own path through the KyberSwap case: which transaction to open, which number to check, and when it has enough to write. The prompt keeps that reasoning honest. Every claim must come from a tool result, and the report separates what the chain shows from labels and from the model's own interpretation. On this case, the agent reads the attacker's on-chain letters, including a demand to take over the company, and turns a few raw transactions into a cited report an investigator can check. The same agent loop is ready for the next exploit. Point it at a new case, and it can speed the first pass of the investigation.
