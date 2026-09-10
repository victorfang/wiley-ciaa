#!/usr/bin/env python3
# Author: Victor Fang, 2026
# Check if a Bitcoin address is ransomware-related via OpenAI API (web search).
# Usage: python ch1_ai_agent_bitcoin_ransomware.py [ADDRESS]
# Requires: OPENAI_API_KEY_VF or OPENAI_API_KEY in env or .env
# Optional: OPENAI_MODEL (default gpt-4.1-mini)
import json, os, sys
from openai import OpenAI

address = sys.argv[1] if len(sys.argv) > 1 else "12t9YDPgwueZ9NyMgw519p7AA8isjr6SMw"
api_key = os.getenv("OPENAI_API_KEY_VF") or os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
client = OpenAI(api_key=api_key)

res = client.responses.create(
    model=model,
    input=[
        {"role": "system", "content": "You are a blockchain risk analyst. Return ONLY valid JSON: address, ransomware_related, confidence, reasoning, sources. No other text."},
        {"role": "user", "content": f"Is this Bitcoin address ransomware-related? {address}"},
    ],
    tools=[{"type": "web_search_preview"}],
)
raw = res.output_text.strip()
if raw.startswith("```"): raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
try: print(json.dumps(json.loads(raw), indent=2))
except json.JSONDecodeError: print(raw)

# Example output:
"""
{
  "address": "12t9YDPgwueZ9NyMgw519p7AA8isjr6SMw",
  "ransomware_related": true,
  "confidence": 1.0,
  "reasoning": "This Bitcoin address is hardcoded into the WannaCry ransomware, which was a significant global cyberattack in 2017. The address was used by the attackers to receive ransom payments from victims. Multiple reputable sources confirm this association, including Secureworks and the Gigamon Blog. Additionally, the address has been flagged as malicious by BitInfoCharts, further corroborating its connection to ransomware activities.",
  "sources": [
    "https://www.secureworks.jp/research/wcry-ransomware-analysis",
    "https://blog.gigamon.com/2017/05/19/wannacry-key-points-of-interest/",
    "https://www.bitinfocharts.com/bitcoin/address/12t9YDPgwueZ9NyMgw519p7AA8isjr6SMw"
  ]
}
"""
