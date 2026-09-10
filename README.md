# Cryptocurrency Investigation with Agentic AI — Companion Code

Companion labs for **Victor Fang**’s Wiley book *Cryptocurrency Investigation with Agentic AI* (2026).

**Author:** [VictorFang.com](https://www.VictorFang.com) · [LinkedIn](https://www.linkedin.com/in/drvictorfang/) · [X](http://x.com/vicfcs)  
**Repo:** https://github.com/victorfang/wiley-ciaa  
**License:** [Apache License 2.0](LICENSE)

Each `chN/` folder is a **standalone system**: chapter README, `.env.example` (when needed), Python code, and data artifacts. Open that folder’s README for setup, keys, and how to run.

```bash
git clone https://github.com/victorfang/wiley-ciaa.git
cd wiley-ciaa
```

**Shared requirements:** Python 3.10+. Install dependencies and configure secrets only inside the chapter you are running. Copy `.env.example` → `.env` locally; never commit `.env`.

## Design for education and simplicity

This codebase is built for **education and simplicity**. It prefers **open-source tooling and publicly accessible data/APIs** over commercial investigation platforms (for example AnChain.ai and similar products).

- **AI models.** Most examples call hosted models such as OpenAI, Anthropic, or DeepSeek for simplicity. You can swap in other providers, including **self-hosted open-weight models on your own GPU**. Hosted APIs may require a small usage fee to run the labs.
- **Data APIs.** Labs use openly accessible endpoints (for example blockchain explorers / public Bitcoin APIs, Etherscan, and similar). Free tiers often have **rate limits and quotas**; paid tiers raise those limits if you need heavier use.

## Who this is for

- Students, researchers, and engineers learning and looking to build **agentic AI systems** using real-world, high-impact data
- Cryptocurrency investigators, AML / financial-crime analysts, and cybersecurity / digital-forensics practitioners
- Compliance, risk, and fraud teams who need reproducible on-chain and off-chain investigation workflows
- Security and AI engineers prototyping investigation agents, triage pipelines, and evidence-bounded reporting
- Educators and training programs teaching applied blockchain forensics and agentic AI

**Basic Python** is enough to run and adapt the labs; deep ML or blockchain engineering experience is not required.

## Chapters

| Folder | Topic | Status |
|--------|--------|--------|
| [`ch1/`](ch1/) | First AI agent — WannaCry Bitcoin ransomware screen | ✅ |
| [`ch2/`](ch2/) | Bitcoin one-hop tracing — Twitter hack case | ✅ |
| [`ch3/`](ch3/) | Ethereum one-hop tracing — multi-layer value edges | ✅ |
| [`ch4/`](ch4/) | Compliance, off-ramps, and legal reality | |
| [`ch5/`](ch5/) | ML triage + LangGraph agent — PowerShell / Bitcoin IOCs | ✅ |
| [`ch6/`](ch6/) | Reliable LLMs for evidence-based investigations | |

## Example: run Chapter 1

Screens the WannaCry Bitcoin ransom address with an OpenAI agent (web search). Full notes: [`ch1/README.md`](ch1/README.md).

```bash
cd ch1
cp .env.example .env          # set OPENAI_API_KEY or OPENAI_API_KEY_VF
pip install -r requirements.txt
python3 ch1_ai_agent_bitcoin_ransomware.py
```

Optional: pass another address as an argument. Default model is `gpt-4.1-mini` (`OPENAI_MODEL` to override).

## Shared investigative rules

- An address is not a person; graph distance is not ownership.
- Heuristic labels and explorer tags are screening hypotheses, not attribution.
- Keep findings evidence-bounded; verify primary sources before relying on any automated summary.

## Citation

> Victor Fang. *Cryptocurrency Investigation with Agentic AI*. Wiley, 2026. Companion code: https://github.com/victorfang/wiley-ciaa

Labs are for education and reproducible practice — not legal advice or production enforcement tooling.
