## Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
"""Generic LangGraph OSINT: fixture → QR/OCR → validate → optional GPT-6 summary."""
import hashlib, json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
import cv2, pytesseract
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")
ABC = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
PATTERN = re.compile(r"(?<![A-Za-z0-9])[1mn][1-9A-HJ-NP-Za-km-z]{25,34}(?![A-Za-z0-9])")
def digest(b): return hashlib.sha256(b).hexdigest()
def network(addr):
    try:
        n = 0
        for c in addr: n = n * 58 + ABC.index(c)
        raw = b"\0" * (len(addr) - len(addr.lstrip("1"))) + n.to_bytes((n.bit_length() + 7) // 8, "big")
        ok = len(raw) == 25 and raw[-4:] == hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()[:4]
        return {0: "bitcoin_mainnet", 111: "bitcoin_test_family"}.get(raw[0], "unsupported") if ok else "invalid"
    except (ValueError, IndexError): return "invalid"
def collect(s):
    fx, rg = Path(s.get("fixture") or ROOT/"data/doj-telegram-training-fixture.json"), Path(s.get("register") or ROOT/"data/review-register.json")
    raw, reg = fx.read_bytes(), rg.read_bytes()
    print(f"[1/5] collect {fx.name}", flush=True)
    return {**s, "fixture_path": str(fx), "messages": json.loads(raw)["messages"], "register": json.loads(reg),
            "audit": {"fixture_sha256": digest(raw), "register_sha256": digest(reg)}, "images": [], "rows": [], "osint_summary": "", "gpt": {}}
def extract(s):
    print("[2/5] extract", flush=True)
    reviews = s["register"].get("image_reviews") or {}
    for msg in s["messages"]:
        msg["extractions"] = [("text", msg["id"], msg.get("text") or "")]
        media = msg.get("media")
        if not media: continue
        path = (ROOT / media["path"]).resolve()
        if not path.is_relative_to(ROOT) or digest(path.read_bytes()) != media["sha256"]: raise ValueError("image integrity failure")
        pix = cv2.imread(str(path))
        if pix is None: raise ValueError(f"unreadable: {path}")
        qr, _, _ = cv2.QRCodeDetector().detectAndDecode(pix)
        ocr = pytesseract.image_to_string(pix, config="--psm 6", timeout=20)
        s["images"].append({"id": media["id"], "sha256": media["sha256"], "qr": qr, "ocr": ocr})
        msg["extractions"] += [("qr", media["id"], qr), ("ocr", media["id"], ocr)]
        if media["id"] in reviews: msg["extractions"].append(("human_source_review", media["id"], reviews[media["id"]]["address"]))
    return s
def validate(s):
    print("[3/5] validate", flush=True)
    reviews = s["register"].get("image_reviews") or {}
    for msg in s["messages"]:
        for method, art, text in msg["extractions"]:
            for addr in sorted(set(PATTERN.findall(text or ""))):
                row = {"message": msg["id"], "artifact": art, "method": method, "address": addr,
                       "network": network(addr), "attribution": "unsupported", "sources": [art]}
                rev = reviews.get(art, {})
                if row["network"] == "bitcoin_mainnet" and rev.get("address") == addr:
                    row.update(attribution="source_register_match", sources=[art, rev.get("source_id", "register")])
                s["rows"].append(row)
    return s
def llm_osint(s):
    if not s.get("llm"): print("[4/5] llm skipped", flush=True); return {**s, "mode": "offline"}
    print(f"[4/5] llm {MODEL}", flush=True)
    from openai import OpenAI
    rows = [{k: r[k] for k in ("message", "address", "network", "method", "attribution")} for r in s["rows"]]
    prompt = ("OSINT: public mentions for mainnet addresses; test-family/invalid are controls; ≤200-word summary. "
              f"No ownership/freeze claims.\nrows={json.dumps(rows)}\nregister={json.dumps(s['register'])[:4000]}")
    client = OpenAI(timeout=90, max_retries=0)
    try:
        r = client.responses.create(model=MODEL, store=False, tools=[{"type": "web_search"}], input=prompt)
        out, model, rid = (getattr(r, "output_text", None) or str(r)).strip(), getattr(r, "model", MODEL), getattr(r, "id", "")
    except Exception:
        r = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}])
        out, model, rid = (r.choices[0].message.content or "").strip(), MODEL, getattr(r, "id", "")
    return {**s, "osint_summary": out, "mode": "openai_osint", "model": model, "model_response_id": rid, "gpt": {"input": prompt, "output": out}}
def report(s):
    print("[5/5] report", flush=True)
    s.update(human_review_required=True, action_authorized=False,
             finding={"rows": s["rows"], "images": s["images"], "audit": s["audit"], "osint_summary": s.get("osint_summary") or ""})
    return s
def build():
    g, prev = StateGraph(dict), START
    for n in (collect, extract, validate, llm_osint, report):
        g.add_node(n.__name__, n); g.add_edge(prev, n.__name__); prev = n.__name__
    g.add_edge(prev, END); return g.compile()
if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]; use_llm = "--llm" in sys.argv or "--osint" in sys.argv
    if use_llm and not os.getenv("OPENAI_API_KEY"): raise SystemExit("Set OPENAI_API_KEY in ch11/.env")
    fixture = args[0] if args else str(ROOT / "data/doj-telegram-training-fixture.json")
    result = build().invoke({"llm": use_llm, "fixture": fixture})
    model = re.sub(r"[^A-Za-z0-9._-]+", "-", str(result.get("model") or ("offline" if not use_llm else MODEL)))
    out = ROOT / "output" / f"{model}-{Path(fixture).stem}-{datetime.now(timezone.utc):%Y-%m-%d}.json"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result.get("osint_summary"): print("\n=== OSINT summary ===\n" + result["osint_summary"])
    print(f"\nsaved: {out}", flush=True)
