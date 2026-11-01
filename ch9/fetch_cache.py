## Cryptocurrency Investigation with Agentic AI, Victor Fang, 2026
## Rebuilds data/kyber_cache.json from raw Ethereum JSON-RPC. The agent never needs the network.
import json, os, urllib.request
from datetime import datetime, timezone
from pathlib import Path

RPC = os.getenv("ETH_RPC_URL", "https://eth.drpc.org")  # needs historical receipts; pruned nodes return null
OUT = Path(__file__).resolve().parent / "data" / "kyber_cache.json"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TXS = {  # hash -> why it is in the case file (sources in README)
    "0x09a3a12d58b0bb80e33e3fb8e282728551dc430c65d1e520fe0009ec519d75e8": "Exploit tx cited by SharkTeam (wstETH/WETH pool)",
    "0x396a83df7361519416a6dc960d394e689dd0f158095cbc6a6c387640716f5475": "Exploit tx cited by KyberSwap post-mortem s2.3 (ETHx/USDC pool)",
    "0x7a8912583520304ce2364fa165dafe94461a91ab2dcf45dab942e296594dc40a": "Reported first on-chain message from Exploiter 1",
    "0x5c27d8e9248608f36b028a945f3d6ff31244ab45eb89e1d1a631f608a36454a1": "Reported second on-chain message from Exploiter 1",
    "0x0479da9d6a3a29b294d6337630ea0a482e7ec7223f3b6e6d72442f6c450264d4": "Reported Nov-30 'treaty' demand from Exploiter 1",
}
CONTRACTS = {"0xaf2acf3d4ab78e4c702256d214a3189a874cdc13": "Attack contract (SharkTeam, AuditOne)"}
LABELS = {  # public attributions, not proofs of control
    "0x50275e0b7261559ce1644014d4b78d4aa63be836": "KyberSwap Exploiter 1 (KyberSwap post-mortem, Etherscan label)",
    "0xaf2acf3d4ab78e4c702256d214a3189a874cdc13": "Exploit contract (SharkTeam report)",
    "0x91c9d4373b077ef8082f468c7c97f2c499e36f5b": "Kyber: DAO Multisig Wallet (Etherscan label)",
    "0xc9b826bad20872eb29f9b1d8af4befe8460b50c6": "KyberSwap Exploiter 1, second address (KyberSwap post-mortem)",
    "0x8180a5ca4e3b94045e05a9313777955f7518d757": "KyberSwap Deployer (post-mortem on-chain message link)",
    "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2": "Aave v3 Pool (Aave docs)",
}
SELECTORS = {  # tiny offline 4byte directory for the calls in this case
    "0xa9059cbb": "transfer(address,uint256)", "0x095ea7b3": "approve(address,uint256)",
    "0x23b872dd": "transferFrom(address,address,uint256)", "0x490e6cbc": "flash(address,uint256,uint256,bytes)",
    "0x5cffe9de": "flashLoan(address,address,uint256,bytes)", "0xab9c4b5d": "flashLoan(address,address[],uint256[],uint256[],address,bytes,uint16)",
}

def rpc(method, *params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": list(params)}).encode()
    req = urllib.request.Request(RPC, body, {"content-type": "application/json", "user-agent": "ch9-opus"})
    return json.load(urllib.request.urlopen(req, timeout=60))["result"]

def token_meta(addr):
    def call(sig):
        try: return bytes.fromhex(rpc("eth_call", {"to": addr, "data": sig}, "latest")[2:])
        except Exception: return b""
    s, d = call("0x95d89b41"), call("0x313ce567")
    sym = s[64:64 + int.from_bytes(s[32:64], "big")] if len(s) > 64 else s.rstrip(b"\0")
    return {"symbol": sym.decode(errors="replace") or "?", "decimals": int.from_bytes(d, "big") if d else None}

cache = {"chain_id": int(rpc("eth_chainId"), 16), "rpc": RPC.split("?")[0], "labels": LABELS, "selectors": SELECTORS,
         "captured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "txs": {}, "contracts": {}, "tokens": {}}
for h, why in TXS.items():
    tx, rc = rpc("eth_getTransactionByHash", h), rpc("eth_getTransactionReceipt", h)
    block = rpc("eth_getBlockByNumber", tx["blockNumber"], False)
    transfers = [{"log_index": int(l["logIndex"], 16), "token": l["address"].lower(), "from": "0x" + l["topics"][1][-40:],
                  "to": "0x" + l["topics"][2][-40:], "raw": str(int(l["data"], 16))}
                 for l in rc["logs"] if len(l["topics"]) == 3 and l["topics"][0] == TRANSFER and len(l["data"]) == 66]
    cache["txs"][h] = {"why": why, "block": int(tx["blockNumber"], 16), "status": int(rc["status"], 16),
                       "time_utc": datetime.fromtimestamp(int(block["timestamp"], 16), timezone.utc).isoformat(),
                       "from": tx["from"].lower(), "to": (tx["to"] or "").lower(), "value_wei": str(int(tx["value"], 16)),
                       "nonce": int(tx["nonce"], 16), "input": tx["input"], "log_count": len(rc["logs"]), "transfers": transfers,
                       "other_logs": [{"log_index": int(l["logIndex"], 16), "address": l["address"].lower(), "topics": l["topics"],
                                       "data": l["data"]} for l in rc["logs"] if l["topics"][:1] != [TRANSFER]]}
    for t in transfers:
        cache["tokens"].setdefault(t["token"], None)
    print("tx", h[:12], len(transfers), "transfers")
for t in cache["tokens"]:
    cache["tokens"][t] = token_meta(t)
for a, why in CONTRACTS.items():
    cache["contracts"][a] = {"why": why, "bytecode": rpc("eth_getCode", a, "latest")}
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(cache, indent=1))
print("wrote", OUT, f"{OUT.stat().st_size // 1024} KB")
