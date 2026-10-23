Concise one-hop investigative report for bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh

Scope and completeness

- Network and window: bitcoin-mainnet, epoch 1594771200–1594944000.
- history_complete: true.
- Transactions retrieved: 1117.
- All statements below use only the supplied JSON; no external clustering or identity inference is applied.

Observed facts (on-chain evidence only)
Inbound to the target address

- The target received many P2WPKH outputs within the window (examples below). Inputs jointly fund outputs (per allocation_warning), so source-to-output attribution within those funding transactions is not encoded.
- Example large inbound:
  - 27,344,675 sats to outpoint ea844aa0356e254a9386ab429109924fe29d67e84a392cc33f9be84b7b43117d:1 (TX ea844aa0356e254a9386ab429109924fe29d67e84a392cc33f9be84b7b43117d; block_time 1594852690). This transaction drew 71 inputs, all from bc1qwr30ddc04zqp878c0evdrqfx564mmf0dy2w39l, with a 383,682-sat fee; classification flagged possible_consolidation: true (not attribution).
- Numerous smaller inbound UTXOs were also received across many TXIDs (e.g., 10,868,939 sats in 293f8e88360944740152efc8c4993b7375cd66de6be17d39b3e6ed1b766c1335:107; 10,853,639 sats in cd6799b2edb856addc12489796ed9d94dd42f51174ad04e8da2c32ea9147fcd9:1; 10,700,000+ sats in multiple other upstream events). Many tiny “dust-like” values (e.g., 1,337 sats) are also present.

Outbound spends of target-controlled UTXOs (one-hop)

- The 27,344,675-sat UTXO from ea844aa03…:1 was spent in d3ed76029bdf9cbfec9ae9634850fcf770cfa968a8423c24bd12f7fde8377bcb (block_time 1594861903). Inputs included that UTXO plus another 21,730,800-sat UTXO (ff0ce894…:0). Outputs: bc1q6l86kvwg4kr75w5ac9j30dn8363kcr8rde35dn (54,343,906 sats) and bc1qn4vysu0e8jp0tama9xphtehznxla8jlrk7zwjj (18,712,851 sats). Classification: possible_consolidation: false, possible_peel: false. No input-to-output mapping is asserted.
- Multiple other one-hop spending transactions consume many target UTXOs in large batches and produce two outputs, often one large P2PKH and one P2WPKH. Examples (classification consistently flags possible_consolidation: true and not coinjoin):
  - 14e1176296633cf3feab2df4d832c1c906ff6278e6444f61c5aa827bdfde34c3 (block_time 1594858790): 36 inputs (several target UTXOs), outputs 1NWJd7BfJLJrEcfGiGfFqbhyaiusWwaZS1 (54,407,176 sats) and bc1qrvslwdamxxllsysqml9p5tsw9rq5actt7hwqpe (5,947,151 sats).
  - a5ad498d6ab8641af23f74a1a6f6c82b89c8a00cbe465a8ac8febbc8a9478f25 (block_time 1594862313): spent 456,036,318 sats from 63015d329f…:0 to two P2WPKH outputs (429,921,760 sats; 76,081,469 sats); possible_peel: true.
  - 0f084b75a380f08e5f6e43cf6023b26cc90768ef9a7e520bc00554fd1d0d9cbb (block_time 1594848595): four large inputs (sum includes 10,870,000; 27,932,474; 47,390,000; 37,838,048 sats) to P2WPKH 24,003,300 sats and P2PKH 1Ai52Uw6usjhpcDrwSmkUvjuqLpcznUuyF 100,000,000 sats.
  - d056bf2052da7a262d73882e94f70f5d938e6af6b39d13ad12ffee1e7cc52916 (block_time 1594848595): two large inputs (100,000,000; 50,000,000 sats) to P2WPKH 49,983,464 sats and P2PKH 1Ai52Uw6usjhpcDrwSmkUvjuqLpcznUuyF 100,000,000 sats.
  - 4070a1984cc7fa4e7e02ed94fa8a060bf3798a19659131a09ef7020ac995b3dc (block_time 1594844487): 54 inputs to P2WPKH 4,552,437 sats and P2PKH 1Ai52Uw6usjhpcDrwSmkUvjuqLpcznUuyF 100,000,000 sats.
- Several other one-hop spend TXIDs consolidate many of the target’s UTXOs and send large amounts to P2PKH 1Ai52Uw6usjhpcDrwSmkUvjuqLpcznUuyF (e.g., 0f084b75…, d056bf20…, 4070a198…), while also creating a second P2WPKH output. No assignment of specific target inputs to specific outputs is made.

Patterns and structure (heuristic observations only; not attribution)

- Consolidation behavior: Many inbound UTXOs (including recurring tiny values like 1,337 sats and multiple mid-size deposits) are frequently combined into two-output transactions flagged as possible_consolidation: true by the classifier (e.g., 14e11762…, 4637df85…, 053fe442…, 4070a198…).
- Recurring recipient pattern: The P2PKH address 1Ai52Uw6usjhpcDrwSmkUvjuqLpcznUuyF appears as a high-value recipient across multiple one-hop spending TXs (e.g., 0f084b75…, d056bf20…, 4070a198…). This is a transactional pattern only; it is not identity.
- Repeated funding sources: Several upstream fundings include repeated previous_address values (e.g., multiple upstream transactions list previous_address 1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s as inputs to funding TXs that created outputs to the target). This shows recurring source addresses but does not imply control or identity at the target.

Attribution, clustering, and change (explicitly not asserted)

- No person/entity attribution is made for any address.
- No input-to-output flow allocation is asserted beyond one hop; the data carries allocation_warning and the report treats CoinJoin/change detection flags as hypotheses only.
- The repeated P2PKH recipient 1Ai52… observed in multiple one-hop spends is a pattern, not an identity claim or a claim that “change” went elsewhere.

Key one-hop movements cited

- Inbound: 27,344,675 sats at ea844aa0356e254a9386ab429109924fe29d67e84a392cc33f9be84b7b43117d:1 (target received; later spent).
- Outbound: d3ed76029bdf9cbfec9ae9634850fcf770cfa968a8423c24bd12f7fde8377bcb (spent the above UTXO with other inputs; two P2WPKH outputs).
- Additional high-value one-hop outbound consolidations with two-output structure: 14e1176296633cf3feab2df4d832c1c906ff6278e6444f61c5aa827bdfde34c3; a5ad498d6ab8641af23f74a1a6f6c82b89c8a00cbe465a8ac8febbc8a9478f25; 0f084b75a380f08e5f6e43cf6023b26cc90768ef9a7e520bc00554fd1d0d9cbb; d056bf2052da7a262d73882e94f70f5d938e6af6b39d13ad12ffee1e7cc52916; 4070a1984cc7fa4e7e02ed94fa8a060bf3798a19659131a09ef7020ac995b3dc; 053fe44233d8e8a625d509f0dcf6aef672f297b4c2c7d7bd989d377027888b56; 4637df8554fb46316e9cbf3bf081d0c4b5e348697e8218525b789dfe10678744; 879a0b0fc037ef9de77a09ac1ec3128491db78563e7668cafef8c0234efde573.

Investigator notes and cautions

- Allocation and change: Do not assign a specific target input to any particular output without a fully disclosed tracing model. This report intentionally refrains from such mapping.
- CoinJoin screening: All classifier “possible_coinjoin” flags are false in the cited one-hop spends, but these are screening hypotheses only, not proofs of transaction intent or ownership.
- Address ≠ identity: The repeated presence of certain addresses (as sources or recipients) is an observable pattern, not an attribution of control or ownership.

