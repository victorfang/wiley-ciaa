from __future__ import annotations

"""Chapter 6 — Reliable LLMs for Evidence-Based Investigations.

Cryptocurrency Investigation with Agentic AI · Victor Fang · Wiley · 2026
Weak memory-only answer (gpt-5-mini) vs tool-grounded gpt-6-luna.
"""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import re

import requests
from openai import OpenAI


ESPLORA_BASE_URL = "https://blockstream.info/api"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
CHAPTER_DIR = Path(__file__).resolve().parent


def load_local_env() -> None:
    """Load ch6/.env, then the repo .env. A variable already set in the shell wins."""
    for path in (CHAPTER_DIR / ".env", CHAPTER_DIR.parent / ".env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_local_env()
if not os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY_VF"):
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY_VF"]

# Path A stays on a smaller model so the no-tool answer can invent live stats.
# Path B is gpt-6-luna: it must call Esplora, then the harness checks the prose.
WEAK_MODEL = os.getenv("OPENAI_WEAK_MODEL", "gpt-5-mini")
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")

client = OpenAI(timeout=120)


def completion_kwargs(chat_model: str, **kwargs):
    """Adapt chat-completions params to the model family.

    gpt-5* and gpt-6* reject a non-default temperature. gpt-6-luna also
    rejects function tools on this endpoint when reasoning is enabled.
    """
    if chat_model.startswith(("gpt-5", "gpt-6")):
        kwargs.pop("temperature", None)
    if chat_model.startswith("gpt-6"):
        kwargs.setdefault("max_completion_tokens", 1200)
        if kwargs.get("tools") is not None:
            kwargs["reasoning_effort"] = "none"
    kwargs["model"] = chat_model
    return kwargs


def as_assistant_message(message) -> dict:
    """Copy an assistant turn into a plain message the next call can replay."""
    payload = {"role": "assistant", "content": message.content}
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return payload


def llm_only(address: str, model: str) -> dict:
    """Unsafe path: answer from parametric memory only (no chain evidence)."""
    question = f"""
You are a blockchain analyst. Answer from your own knowledge only.
Do not say you lack live data. Do not ask to look anything up.
Give concrete numbers for Bitcoin address {address}:

1. confirmed transaction count
2. total confirmed BTC received
3. total confirmed BTC spent
4. current confirmed BTC balance

Reply in a short factual report with the four numbers.
"""
    response = client.chat.completions.create(
        **completion_kwargs(
            model,
            messages=[{"role": "user", "content": question}],
            temperature=0.7,
        )
    )
    return {
        "answer": response.choices[0].message.content or "",
        "model": response.model,
        "response_id": response.id,
    }


# --- Harness helpers: validate inputs, fail soft on tool errors, check answers ---


def validate_address_shape(address: str) -> None:
    """Reject obvious injection and malformed-path input before the API call."""
    if not re.fullmatch(r"[A-Za-z0-9]{26,90}", address):
        raise ValueError("Address has an invalid shape.")


def get_bitcoin_address_summary(address: str) -> dict:
    """Read current mainnet address statistics from Blockstream Esplora.

    Harness: on network/HTTP failure return ok=False instead of crashing,
    so the agent can abstain rather than invent numbers.
    """
    validate_address_shape(address)
    source_url = f"{ESPLORA_BASE_URL}/address/{address}"
    try:
        response = requests.get(source_url, timeout=20)
    except requests.RequestException as exc:
        return {"ok": False, "error": f"Network error: {exc}", "source_url": source_url}

    if response.status_code in {400, 404}:
        return {
            "ok": False,
            "error": "The Bitcoin data source rejected this address.",
            "source_url": source_url,
        }
    if not response.ok:
        return {
            "ok": False,
            "error": f"HTTP {response.status_code} from data source.",
            "source_url": source_url,
        }

    raw_bytes = response.content
    data = response.json()
    if data.get("address") != address:
        return {"ok": False, "error": "Data source returned a different address."}

    chain = data["chain_stats"]
    mempool = data["mempool_stats"]
    required = {"tx_count", "funded_txo_sum", "spent_txo_sum"}
    if not required.issubset(chain) or not required.issubset(mempool):
        return {"ok": False, "error": "Incomplete schema from data source."}

    confirmed_balance = chain["funded_txo_sum"] - chain["spent_txo_sum"]
    sats_per_btc = 100_000_000
    return {
        "ok": True,
        "network": "bitcoin-mainnet",
        "address": address,
        "confirmed_tx_count": chain["tx_count"],
        "confirmed_received_sats": chain["funded_txo_sum"],
        "confirmed_spent_sats": chain["spent_txo_sum"],
        "confirmed_balance_sats": confirmed_balance,
        "confirmed_received_btc": chain["funded_txo_sum"] / sats_per_btc,
        "confirmed_spent_btc": chain["spent_txo_sum"] / sats_per_btc,
        "confirmed_balance_btc": confirmed_balance / sats_per_btc,
        "mempool_tx_count": mempool["tx_count"],
        "unconfirmed_balance_delta_sats": (
            mempool["funded_txo_sum"] - mempool["spent_txo_sum"]
        ),
        "source_url": source_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_response_sha256": sha256(raw_bytes).hexdigest(),
    }


def assert_answer_matches_evidence(answer: str, evidence: dict) -> None:
    """Harness: final prose must mention the tool's tx count and balance BTC."""
    tx = str(evidence["confirmed_tx_count"])
    # Allow "65746" or "65,746"
    tx_ok = tx in answer or f"{int(tx):,}" in answer
    btc = f"{evidence['confirmed_balance_btc']:.8f}".rstrip("0").rstrip(".")
    btc_ok = btc in answer.replace(",", "")
    if not tx_ok or not btc_ok:
        raise RuntimeError(
            "Harness check failed: model answer does not match tool evidence "
            f"(expected tx={tx}, balance_btc≈{btc})."
        )


BITCOIN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_bitcoin_address_summary",
            "description": (
                "Read current Bitcoin mainnet statistics for one address. "
                "Use this before making any address-specific factual claim."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "A Bitcoin mainnet address to verify.",
                    }
                },
                "required": ["address"],
                "additionalProperties": False,
            },
        },
    }
]


def tool_grounded_agent(address: str, model: str) -> dict:
    """Minimal agent loop with a thin harness around the tool call."""
    question = (
        f"Investigate Bitcoin address {address}. Report confirmed transaction "
        "count, confirmed received, confirmed spent, and confirmed balance."
    )
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are a read-only Bitcoin investigation assistant. You must "
                "call get_bitcoin_address_summary before stating address-specific "
                "facts. Never infer identity, ownership, criminality, or exchange "
                "attribution."
            ),
        },
        {"role": "user", "content": question},
    ]

    # Harness: force a tool call on the first turn.
    first_response = client.chat.completions.create(
        **completion_kwargs(
            model,
            messages=messages,
            tools=BITCOIN_TOOLS,
            tool_choice="required",
            max_completion_tokens=800,
        )
    )
    first_message = first_response.choices[0].message
    if first_response.choices[0].finish_reason == "length":
        raise RuntimeError("Tool-call turn hit the token limit before naming a tool.")
    messages.append(as_assistant_message(first_message))

    evidence_records = []
    tool_calls = first_message.tool_calls or []
    for tool_call in tool_calls:
        if tool_call.function.name != "get_bitcoin_address_summary":
            raise RuntimeError(f"Unexpected tool requested: {tool_call.function.name}")

        arguments = json.loads(tool_call.function.arguments)
        # Harness: model may not swap the investigator-supplied address.
        if arguments["address"] != address:
            raise RuntimeError("The model changed the investigator-supplied address.")

        evidence = get_bitcoin_address_summary(address)
        evidence_records.append(evidence)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(evidence, sort_keys=True),
            }
        )

    if not evidence_records:
        raise RuntimeError("Agent stopped: required Bitcoin tool was not called.")

    # Harness: if the tool failed, abstain — do not ask the model to invent facts.
    if not evidence_records[0].get("ok", False):
        err = evidence_records[0].get("error", "unknown tool failure")
        return {
            "answer": (
                "Cannot verify: blockchain tool failed. "
                f"Abstaining from numeric claims. ({err})"
            ),
            "evidence": evidence_records,
            "model": first_response.model,
            "response_id": first_response.id,
            "harness": {"tool_ok": False, "answer_checked": False},
        }

    final_response = client.chat.completions.create(
        **completion_kwargs(
            model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer only from the Bitcoin tool output. Prefer the "
                        "confirmed_*_btc fields already provided by the tool; do not "
                        "recompute or invent amounts. Copy confirmed_tx_count and "
                        "confirmed_balance_btc exactly. State the source URL, retrieval "
                        "time, and raw-response SHA-256. If evidence is missing, "
                        "abstain. Do not add identity, ownership, risk, or exchange "
                        "claims."
                    ),
                },
                *messages[1:],
            ],
            tools=BITCOIN_TOOLS,
            tool_choice="none",
            max_completion_tokens=1200,
        )
    )
    final_message = final_response.choices[0].message
    if final_message.tool_calls:
        raise RuntimeError("Agent requested an unexpected second tool call.")

    answer = final_message.content or ""
    # Harness: catch answer drift vs tool evidence.
    assert_answer_matches_evidence(answer, evidence_records[0])

    return {
        "answer": answer,
        "evidence": evidence_records,
        "model": final_response.model,
        "response_id": final_response.id,
        "harness": {"tool_ok": True, "answer_checked": True},
    }


def save_run_artifacts(run: dict) -> Path:
    """Write JSON + readable text artifacts for one comparison run."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_weak = run["weak_model"].replace("/", "-")
    safe_model = run["model"].replace("/", "-")
    safe_address = run["address"][:6]
    stem = f"{safe_weak}_vs_{safe_model}_{safe_address}_{stamp}"

    json_path = RESULTS_DIR / f"{stem}.json"
    txt_path = RESULTS_DIR / f"{stem}.txt"

    json_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")

    evidence = run["paths"]["tool_grounded"]["evidence"]
    txt_path.write_text(
        "\n".join(
            [
                "Chapter 6 — Reliable LLMs for Evidence-Based Investigations",
                f"timestamp_utc: {run['timestamp_utc']}",
                f"weak_model: {run['weak_model']}",
                f"model: {run['model']}",
                f"address: {run['address']}",
                f"lesson: {run['lesson']}",
                "",
                "=== A. WEAK LLM ONLY (no blockchain evidence) ===",
                run["paths"]["llm_only"]["answer"],
                "",
                "=== B. TOOL-GROUNDED GPT-6 AGENT ===",
                run["paths"]["tool_grounded"]["answer"],
                "",
                "=== Evidence record ===",
                json.dumps(evidence, indent=2),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return json_path


def compare_paths(address: str) -> Path:
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    print(f"Weak model (path A): {WEAK_MODEL}")
    print(f"Tool-grounded model (path B): {MODEL}")
    print(f"Address: {address}")
    print(f"Timestamp (UTC): {timestamp_utc}")
    print()

    print("=== A. WEAK LLM ONLY: NO BLOCKCHAIN EVIDENCE ===")
    llm_result = llm_only(address, WEAK_MODEL)
    print(llm_result["answer"])

    print("\n=== B. TOOL-GROUNDED GPT-6 AGENT ===")
    grounded = tool_grounded_agent(address, MODEL)
    print(grounded["answer"])
    print("\nEvidence record:")
    print(json.dumps(grounded["evidence"], indent=2))
    print(f"Harness: {grounded.get('harness')}")

    run = {
        "lesson": (
            "A smaller model with no chain tool can invent live Bitcoin stats. "
            "gpt-6-luna beats that answer only when a tool and harness force "
            "the prose to match Esplora evidence."
        ),
        "timestamp_utc": timestamp_utc,
        "weak_model": WEAK_MODEL,
        "model": MODEL,
        "address": address,
        "paths": {
            "llm_only": {
                "description": "Weak model, parametric memory only; no chain tool.",
                "model": llm_result["model"],
                "response_id": llm_result["response_id"],
                "answer": llm_result["answer"],
            },
            "tool_grounded": {
                "description": (
                    "Must call get_bitcoin_address_summary; harness checks "
                    "tool health and answer-vs-evidence match."
                ),
                "model": grounded["model"],
                "response_id": grounded["response_id"],
                "answer": grounded["answer"],
                "evidence": grounded["evidence"],
                "harness": grounded.get("harness"),
            },
        },
    }
    artifact = save_run_artifacts(run)
    print(f"\nSaved run artifacts: {artifact}")
    print(f"Also wrote: {artifact.with_suffix('.txt')}")
    return artifact


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Set OPENAI_API_KEY in ch6/.env or the environment.")
    # Bitcoin genesis-block reward address; live statistics may change.
    compare_paths("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
