"""
Victor Fang, 2026
Cryptocurrency Investigation with Agentic AI — Chapter 10
Bridge reasoning lab: compare models and reasoning_effort on one Wormhole case.
"""

from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")
client = OpenAI()

# Cross-chain bridge data snapshot provided by AnChain.AI
cross_chain_payload = """
{
  "case_name": "AnChain.AI Wormhole Ethereum-to-BSC example",
  "source": {
    "chain": "Ethereum",
    "wormhole_chain_id": 2,
    "timestamp": "2024-12-11T19:27:11Z",
    "tx_hash": "0xd5edc47aa6401ab6ed4d9c8c1d640103e81ab0176a28dd5471f62b9987156d40",
    "sender": "0x48df9e8deaefec5e7438dc5ed8b8f22c3ea79299",
    "application_router": "0x4db1683d60e0a933a9a477a19fa32f472bb9d06e",
    "wormhole_token_bridge": "0x3ee18b2214aff97000d974cf647e7c347e8fa585",
    "token_symbol": "USDT",
    "token_address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "amount": "550",
    "raw_amount": "550000000",
    "decimals": 6
  },
  "message": {
    "protocol": "Wormhole",
    "vaa_id": "2/0000000000000000000000003ee18b2214aff97000d974cf647e7c347e8fa585/426560",
    "emitter_chain": 2,
    "emitter_address": "0000000000000000000000003ee18b2214aff97000d974cf647e7c347e8fa585",
    "sequence": "426560",
    "guardian_set_index": 4,
    "signature_count": 13,
    "nonce": 14,
    "consistency_level": 1,
    "payload_type": 3,
    "target_chain": 4,
    "target_application": "0xf352dc165783538a26e38a536e76dcef227d90f2",
    "application_payload_recipient": "0x48df9e8deaefec5e7438dc5ed8b8f22c3ea79299"
  },
  "destination_candidates": [
    {
      "chain": "BSC",
      "wormhole_chain_id": 4,
      "timestamp": "2024-12-11T19:41:28Z",
      "tx_hash": "0x2d30d5cbb03e38fdadddfabc5af9cbcabf29531873ebf2ff461f76eba6a33693",
      "vaa_id": "2/0000000000000000000000003ee18b2214aff97000d974cf647e7c347e8fa585/426560",
      "recipient": "0x48df9e8deaefec5e7438dc5ed8b8f22c3ea79299",
      "token_symbol": "USDT",
      "amount": "550",
      "status": "completed"
    },
    {
      "chain": "BSC",
      "wormhole_chain_id": 4,
      "timestamp": "2024-12-11T19:35:10Z",
      "tx_hash": "0x1111111111111111111111111111111111111111111111111111111111111111",
      "vaa_id": "2/0000000000000000000000003ee18b2214aff97000d974cf647e7c347e8fa585/426559",
      "recipient": "0x48df9e8deaefec5e7438dc5ed8b8f22c3ea79299",
      "token_symbol": "USDT",
      "amount": "550",
      "status": "completed"
    },
    {
      "chain": "BSC",
      "wormhole_chain_id": 4,
      "timestamp": "2024-12-11T19:42:01Z",
      "tx_hash": "0x2222222222222222222222222222222222222222222222222222222222222222",
      "vaa_id": "2/0000000000000000000000003ee18b2214aff97000d974cf647e7c347e8fa585/426561",
      "recipient": "0x9999999999999999999999999999999999999999",
      "token_symbol": "USDT",
      "amount": "549.8",
      "status": "completed"
    }
  ]
}
"""

# high is the hard setting. low is the light one. Same question every time.
RUNS = [
    ("gpt-6-luna", "high"), ("gpt-6-luna", "low"),
    ("gpt-6-astra", "high"), ("gpt-6-astra", "low"),
    ("gpt-5-nano", "high"), ("gpt-5-nano", "low"),
    ("gpt-5-mini", "high"), ("gpt-5-mini", "low"),
]
OUT = Path(__file__).resolve().parent / "simple_results"
OUT.mkdir(exist_ok=True)

if __name__ == "__main__":
  for model, effort in RUNS:
    print(f"\n===== {model} effort={effort} =====", flush=True)
    try:
        response = client.chat.completions.create(
            model=model,
            reasoning_effort=effort,
            messages=[
                {"role": "system", "content": "You are a Blockchain Intelligence Analyst specializing in cross-chain bridge attribution."},
                {"role": "user", "content": f"Analyze the following JSON block tracing an Ethereum-to-BSC Wormhole transaction. Perform a logical matching analysis among the destination candidates. You must verify and explicitly match the cryptographic identifier (VAA ID), timing sequences, and asset flows to definitively isolate the true destination. Expose why the distractors are incorrect.\n\n{cross_chain_payload}"},
            ],
        )
        details = response.usage.completion_tokens_details if response.usage else None
        tokens = details.reasoning_tokens if details else None
        text = response.choices[0].message.content
    except Exception as exc:
        tokens, text = None, f"{type(exc).__name__}: {exc}"
    print(f"reasoning_tokens={tokens}")
    print(text)
    (OUT / f"{model}_{effort}.txt").write_text(f"model: {model}\nreasoning_effort: {effort}\nreasoning_tokens: {tokens}\n\n{text}\n")
