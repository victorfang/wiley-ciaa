# Chapter 1 — Jump Start Your First AI Agent (WannaCry)

*Cryptocurrency Investigation with Agentic AI* · Victor Fang · Wiley · 2026  
**Author:** [VictorFang.com](https://www.VictorFang.com) · [LinkedIn](https://www.linkedin.com/in/drvictorfang/) · [X](http://x.com/vicfcs)

---

Minimal OpenAI agent that screens a Bitcoin address for ransomware association using the Responses API with web search. Default target is the WannaCry ransom address `12t9YDPgwueZ9NyMgw519p7AA8isjr6SMw`.

## Setup

```bash
cp .env.example .env   # set OPENAI_API_KEY_VF (or OPENAI_API_KEY)
pip install -r requirements.txt
```

Optional: `OPENAI_MODEL` (default `gpt-4.1-mini`).

## Run

```bash
python3 ch1_ai_agent_bitcoin_ransomware.py
python3 ch1_ai_agent_bitcoin_ransomware.py <BITCOIN_ADDRESS>
```

The script prints JSON: `address`, `ransomware_related`, `confidence`, `reasoning`, `sources`.

## Files

| File | Purpose |
|------|---------|
| `ch1_ai_agent_bitcoin_ransomware.py` | Lab script |
| `requirements.txt` | `openai` |
| `.env.example` | API key template |

## Caveats

OSINT and model outputs are leads, not findings. Confirm primary sources before any attribution or operational use.

---

*Companion code · [Apache License 2.0](../LICENSE)*
