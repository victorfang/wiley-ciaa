# Chapter 10 bridge lab (reasoning comparison)

Victor Fang, 2026 · *Cryptocurrency Investigation with Agentic AI* · Chapter 10

Minimal lab: one Wormhole case, eight OpenAI runs (`low` / `high` × four models).

| File | Role |
|---|---|
| `ch10_reason_simple.py` | Run the comparison |
| `ch10_wiley_reason_simple.md` | Book section |
| `ch10_wiley_reason_simple_instructor.md` | Instructor guide |
| `simple_results/` | Saved answers (`<model>_<effort>.txt`) |
| `.env` | `OPENAI_API_KEY` (from `.env.example`) |

```bash
python3 -m venv .venv
.venv/bin/python -m pip install openai python-dotenv
cp .env.example .env
.venv/bin/python ch10_reason_simple.py
```

Older agent scripts, pinned data, and prior experiment outputs are under `old/`.
