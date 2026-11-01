## Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
## An OpenAI tool-calling agent that decodes hidden text in the KyberSwap exploit and cross-checks it against token flows.
import argparse, inspect, json, os, re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI
ROOT = Path(__file__).resolve().parent
for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    if "=" in line and not line.startswith("#"): os.environ.setdefault(*line.strip().split("=", 1))
ap = argparse.ArgumentParser(description="Agentic DeFi investigator over a cached Ethereum case file.")
ap.add_argument("--cache", type=Path, default=ROOT / "data/kyber_cache.json")
ap.add_argument("--question", default="Decode every hidden message in this case, reconstruct the attacker's playbook and timeline, "
                "and prove or refute that the attacker's own logs match the token flows. Note gaps in the evidence.")
ap.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-6-luna")); ap.add_argument("--max-steps", type=int, default=12)
args = ap.parse_args()
C = json.loads(args.cache.read_text())
def label(a): return f"{a} [{C['labels'][a]}]" if a in C["labels"] else a
def tx(h): return C["txs"][h.lower()]
def abi_str(b, at): o = int.from_bytes(b[at:at + 32], "big"); n = int.from_bytes(b[o:o + 32], "big"); return b[o + 32:o + 32 + n].decode(errors="replace")
DSTEST = {"0x0b2e13ff": lambda b: abi_str(b, 0),                                                    # log_string(string)
          "0x7ae74c52": lambda b: label("0x" + b[12:32].hex()),                                     # log_address(address)
          "0xb2de2fbe": lambda b: f"{abi_str(b, 0)} = {int.from_bytes(b[32:64], 'big')}",           # log_named_uint(string,uint256)
          "0x2fe63277": lambda b: f"{abi_str(b, 0)} = {int.from_bytes(b[32:64], 'big', signed=True)}"}  # log_named_int(string,int256)
def narrative(h): return [[l["log_index"], DSTEST[l["topics"][0][:10]](bytes.fromhex(l["data"][2:]))]
                          for l in tx(h)["other_logs"] if l["topics"][0][:10] in DSTEST]

def case_index():
    """List every cached transaction and contract: time, block, sender nonce, labeled from/to, input size, log count."""
    return {"chain_id": C["chain_id"], "captured_utc": C["captured_utc"], "contracts": {a: v["why"] for a, v in C["contracts"].items()},
            "txs": [{"hash": h, "why": t["why"], "time_utc": t["time_utc"], "block": t["block"], "nonce": t["nonce"], "from": label(t["from"]),
                     "to": label(t["to"]), "value_wei": t["value_wei"], "input_bytes": len(t["input"]) // 2 - 1, "logs": t["log_count"]} for h, t in C["txs"].items()]}

def decode_input(tx_hash: str):
    """Decode a transaction's input data: ABI selector lookup versus hidden UTF-8 text message."""
    raw = bytes.fromhex(tx(tx_hash)["input"][2:]); sel = "0x" + raw[:4].hex()
    text = sum(32 <= b < 127 or b in (9, 10, 13) for b in raw) / max(len(raw), 1) > 0.95
    return {"bytes": len(raw), "first4_as_selector": sel, "known_selector": C["selectors"].get(sel), "is_text": text, "text": raw.decode(errors="replace") if text else None,
            "explorer_pitfall": f"explorers may label this 'Call {sel} Method' although {raw[:4]!r} is just text" if text else None}

def runtime_logs(tx_hash: str, start: int, limit: int):
    """Decode debug events (forge-std log_string / log_named_uint / log_named_int / log_address) the attack contract emitted while running."""
    return {"total_lines": len(lines := narrative(tx_hash)), "start": start, "lines": lines[start:start + min(limit, 150)]}

def bytecode_strings(address: str):
    """Static analysis: printable strings stored as PUSH constants in deployed bytecode. A trailing '…' marks a 32-byte chunk cut mid-string."""
    code, i, out = bytes.fromhex(C["contracts"][address.lower()]["bytecode"][2:]), 0, []
    while i < len(code):
        if 0x60 <= code[i] <= 0x7f:
            n = code[i] - 0x5f; d = code[i + 1:i + 1 + n].rstrip(b"\0"); i += n
            if len(d) >= 4 and all(32 <= c < 127 for c in d) and re.search(rb"[A-Za-z]{3}", d):
                out.append(d.decode() + "…" * (len(d) == 32))
        i += 1
    return {"bytecode_bytes": len(code), "strings": list(dict.fromkeys(out))}

def token_flows(tx_hash: str, address: str):
    """Exact net ERC-20 flow (raw units) per token inside one tx, from Transfer logs only. address='*' lists every non-zero net position."""
    net = defaultdict(int)
    for t in tx(tx_hash)["transfers"]:
        net[t["to"], t["token"]] += int(t["raw"]); net[t["from"], t["token"]] -= int(t["raw"])
    return [{"address": label(a), "token": C["tokens"][k]["symbol"], "decimals": C["tokens"][k]["decimals"], "raw_net": str(v)}
            for (a, k), v in net.items() if v and address.lower() in ("*", a)]

def cross_check(tx_hash: str, amount: str):
    """Find an integer (sign ignored) within +/-1 in this tx's Transfer logs and the attacker's runtime logs; diff exposes rounding.
    amount='*' sweeps every runtime-log integer and returns only the Transfers that are off by exactly one unit."""
    if amount == "*":
        nums = {abs(int(n)) for _, s in narrative(tx_hash) for n in re.findall(r"-?\d{6,}", s)}
        return [{"runtime_value": str(v), **h} for v in sorted(nums) for h in cross_check(tx_hash, str(v)) if h.get("diff") in (-1, 1)]
    v, t = abs(int(amount)), tx(tx_hash)
    hits = [{"source": "Transfer", "log_index": x["log_index"], "token": C["tokens"][x["token"]]["symbol"], "raw": x["raw"],
             "from": label(x["from"]), "to": label(x["to"]), "diff": int(x["raw"]) - v} for x in t["transfers"] if abs(int(x["raw"]) - v) <= 1]
    return hits + [{"source": "runtime_log", "log_index": i, "line": s} for i, s in narrative(tx_hash)
                   if any(abs(abs(int(n)) - v) <= 1 for n in re.findall(r"-?\d{6,}", s))]

TOOLS = {f.__name__: f for f in (case_index, decode_input, runtime_logs, bytecode_strings, token_flows, cross_check)}
SCHEMAS = [{"type": "function", "name": n, "description": f.__doc__, "strict": True, "parameters": {"type": "object", "additionalProperties": False,
            "properties": {p: {"type": "integer" if q.annotation is int else "string"} for p, q in inspect.signature(f).parameters.items()},
            "required": list(inspect.signature(f).parameters)}} for n, f in TOOLS.items()]
# Agent loop: the model plans and picks tools; Python executes them exactly and feeds results back until the model writes its report.
out = ROOT / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); out.mkdir(parents=True)
client, history, trace = OpenAI(timeout=180), [{"role": "user", "content": args.question}], []
for step in range(args.max_steps):
    r = client.responses.create(model=args.model, instructions=(ROOT / "prompt.txt").read_text(), input=history, tools=SCHEMAS,
                                store=False, tool_choice="required" if step == 0 else "auto")
    history += [o.model_dump(mode="json", exclude_none=True) for o in r.output]
    if not (calls := [o for o in r.output if o.type == "function_call"]): break
    for c in calls:
        try: result = TOOLS[c.name](**json.loads(c.arguments))
        except Exception as e: result = {"error": f"{type(e).__name__}: {e}"}
        print(f"step {step}: {c.name}({c.arguments[:90]})")
        trace.append({"step": step, "tool": c.name, "args": json.loads(c.arguments), "result": result, "usage": r.usage.model_dump()})
        history.append({"type": "function_call_output", "call_id": c.call_id, "output": json.dumps(result)})
(out / "report.md").write_text(report := r.output_text or "(no final report: step limit reached)")
# Grounding check: every hash, address and long integer in the report must appear somewhere in the evidence the tools returned.
seen, claims = json.dumps([t["result"] for t in trace]).lower(), set(re.findall(r"0x[0-9a-f]{8,64}|\b\d{9,}\b", report.lower().replace(",", "")))
ungrounded = sorted(x for x in claims if x not in seen)
(out / "trace.json").write_text(json.dumps({"model": args.model, "question": args.question, "trace": trace, "final_usage": r.usage.model_dump(), "ungrounded": ungrounded}, indent=1))
print(report, f"\n\nGrounding: {len(claims) - len(ungrounded)}/{len(claims)} cited identifiers found in tool output; ungrounded={ungrounded}\nSaved {out}")
