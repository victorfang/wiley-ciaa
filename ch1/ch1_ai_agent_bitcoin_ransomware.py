#!/usr/bin/env python3
# Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
"""Check whether a Bitcoin address is ransomware-related.

Loads OPENAI_API_KEY from ch1/.env and saves the reply as <address>_<model>.txt.
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).with_name(".env"))

MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")
address = sys.argv[1] if len(sys.argv) > 1 else "12t9YDPgwueZ9NyMgw519p7AA8isjr6SMw"

client = OpenAI()

response = client.responses.create(
    model=MODEL,
    input=[
        {"role": "system", "content": "You are a cryptocurrency investigator. Return ONLY valid JSON: address, ransomware_related, confidence, reasoning, sources. No other text."},
        {"role": "user", "content": f"Is this Bitcoin address ransomware related? {address}"},
    ],
    tools=[{"type": "web_search_preview"}],
)

raw = response.output_text.strip()
if raw.startswith("```"):
    raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    data = {"result": raw}
data = {"model": MODEL, **{k: v for k, v in data.items() if k != "model"}}
text = json.dumps(data, indent=2)
print(text)

out = Path(__file__).with_name(f"{address}_{MODEL}.txt")
out.write_text(text + "\n", encoding="utf-8")
print(f"\nSaved {out.name}")
