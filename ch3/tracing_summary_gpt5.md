Upstream edges: 1 | Downstream edges: 2
Key edges (tx 0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246):
- Upstream: 0xa9cb54745839e3d59c4c7c7d9efc1c86c7984c6c → focal 0x5acc84a3e955Bdd76467d3348077d003f00fFB97: 0.05 ETH (source: transaction.value)
- Downstream: focal → 0x77b6d298f1b0a8cba9943a7d284179f73e65ab0c: 0.025 ETH (source: internal call, same parent tx)
- Downstream: focal → 0xd43e8a8d607ad8085d82a174d6d563619e31b879: 0.025 ETH (source: internal call, same parent tx)

1) Tracing scope
- Mode: transaction_decode
- Focal address: 0x5acc84a3e955Bdd76467d3348077d003f00fFB97
- Transaction hash: 0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246

2) Upstream summary — who paid the focal address
- 0xa9cb54745839e3d59c4c7c7d9efc1c86c7984c6c sent 0.05 ETH to the focal address in the top-level transaction value (source: transaction.value; tx 0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246).

3) Downstream summary — where the focal address paid
- 0.025 ETH from the focal address to 0x77b6d298f1b0a8cba9943a7d284179f73e65ab0c (source: internal call; tx 0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246).
- 0.025 ETH from the focal address to 0xd43e8a8d607ad8085d82a174d6d563619e31b879 (source: internal call; tx 0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246).

4) Observed facts (from JSON only)
- Execution status: success (status 0x1); block 9,985,902; gas used: 336,008; log count: 4.
- The upstream value (0.05 ETH) equals the sum of internal payouts (0.025 + 0.025 ETH) in this transaction; note states this equality is not guaranteed for all contract calls.
- Input selector: 0x797eee24.
- referrer_in_calldata: 0xd43e8a8d607ad8085d82a174d6d563619e31b879.
- Legal status note: alleged Forsage activity; not convicted.
- Internal ETH transfers share the parent transaction hash (both downstream transfers share tx 0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246).

5) Heuristic inferences (inference)
- The referrer_in_calldata equals one of the downstream recipients (0xd43e8a8d…b879), suggesting the downstream split may reflect a referral-style payout structure in this specific call.
- The equal split (0.025/0.025) may indicate deterministic distribution logic for a 0.05 ETH input in this method; however, distribution rules could vary for other calls.

6) Limits of this trace
- Single-transaction decode only; not a full address history. Additional upstream/downstream activity outside tx 0x55089ea1dbba218f7c144da3b49f1ed01c23ba455a86dd1f90a4043ba3bc9246 is not covered.
- Address labels are not identities; no person-level attribution is made.
- Any Forsage-related characterization is alleged, not convicted.
