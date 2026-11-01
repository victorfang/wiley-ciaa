# Forensic report

**Evidence convention:** **OBSERVED** means returned transaction, input-decoding, runtime-log, or token-flow data. **ATTRIBUTED** means a label or public-report attribution supplied with the case index. **INFERRED** means an interpretation of those observations, not an independently verified fact. Hashes below are prefixes; log indexes refer to the relevant transaction.

## Timeline

| UTC time | Block / nonce | OBSERVED | ATTRIBUTED / INFERRED |
|---|---:|---|---|
| 2023-11-22 22:58:23 | 18630408 / 9 | Exploit transaction `0x09a3a12d…`; 932 input bytes, 355 logs. Runtime output shows two pool runs, starting at logs 71 and 190. | The case index attributes the sender to “KyberSwap Exploiter 1” and the recipient to the exploit contract. |
| 2023-11-22 22:58:35 | 18630409 / 10 | Exploit transaction `0x396a83df…`; 1,508 input bytes, 582 logs. Runtime output shows six pool runs, starting at logs 118, 232, 349, 468, 581, and an earlier run in the same sequence. | The case index describes this as the ETHx/USDC exploit transaction cited by the KyberSwap post-mortem. |
| 2023-11-22 23:57:11 | 18630701 / 12 | Text calldata sent to `0x8180…d757`; zero receipt logs. Decoded text says negotiations will start in a few hours. | The case index describes it as the first on-chain message. |
| 2023-11-28 22:10:47 | 18673017 / 13 | Text calldata sent to `0x91c9…6f5b`; zero receipt logs. The sender says a treaty statement is planned for Nov. 30 at noon UTC. | The case index labels the recipient “Kyber: DAO Multisig Wallet.” |
| 2023-11-30 12:04:23 | 18684303 / 14 | Text calldata sent to the same recipient; zero receipt logs. The message presents demands and a Dec. 10 deadline. | The case index describes this as the “treaty” demand. The stated noon release time and the observed 12:04:23 posting time are not identical. |

The exploit transactions are consecutive blocks but 12 seconds apart. The listed nonces jump from 10 to 12; this case index does not include a nonce-11 transaction.

## Decoded messages

**OBSERVED:** Three inputs decode as UTF-8 text. Their apparent first-four-byte “selectors” are text prefixes—not known function selectors: `0x44656172` (“Dear”) on the first two, and `0x546f2041` (“To A”) on the third. Each of these message transactions has zero receipt logs.

### `0x7a891258…` — 136-byte input

> Dear Kyberswap Developers, Employees, DAO members and LPs,
>
> Negotiations will start in a few hours when I am fully rested.
>
> Thank you.

### `0x5c27d8e9…` — 557-byte input

> Dear Kyberswap Executives, Employees, Token Holders and LPs,
>
> I said I was willing to negotiate. In return, I have received (mostly) threats, deadlines, and general unfriendliness from the executive team. That's ok, I don't mind.
>
> I have prepared a statement concerning our (potential) treaty. I plan to release it on Nov. 30 at Noon UTC, sharp.
>
> Under the assumption that I am treated with further hostility, we can reschedule for a later date, when we all feel more civil. You need only say the word.
>
> If not, we proceed as planned on Nov. 30.
>
> Thank you.

### `0x0479da9d…` — 2,658-byte input

> To ALL relevant and/or interested parties,
>
> I thank you for your attention and patience during this uncertain time for Kyber (the protocol/DAO) as well as Kyber (the company). Below I have delineated a treaty for us to agree to.
>
> My demands are as follows:
>
> * Complete executive control over Kyber (the company)
> * Temporary full authority and ownership over the governance mechanism (KyberDAO) in order to enact legislative changes. My current wallet address is fine for this.
> * All documents and information related to company / protocol formation, structure, operation, revenues, profits, expenses, assets, liabilities, investors, salaries, etc.
> * Surrender of all Kyber (the company) assets. This is both On-chain and Off-chain assets. It includes but is not limited to: shares, equity, tokens (KNC and non-KNC), partnerships, blogs, websites, servers, passwords, code, social channels, any and all creative and intellectual property of Kyber.
>
> Once my demands have been met, I will provide the following:
>
> * Executives, you will be bought out of the company at a fair valuation. You will be wished well in your future endeavors. You haven't done anything wrong. A small error was made, rounding in the wrong direction, it could have been made by anyone. Simply bad luck.
> * Employees, under the new regime your salary will be doubled. It is understandable that many current employees will want to leave regardless. The employees who don't want to stay will be given a 12-month severance with full benefits and assistance in finding a new career, no questions asked.
> * Token Holders and Investors, under this treaty, your tokens will no longer be worthless. Is this not sweet enough? I'll go further still. Under my management, Kyber will undergo a complete makeover. It will no longer be the 7th most popular DEX, but rather, an entirely new cryptographic project.
> * LPs, you will be gifted a rebate on your recent market-making activity. The rebate will be for 50% of the losses you have incurred. I know this is probably less than what you wanted. However, it is also more than you deserve.
>
> This is my best offer. This is my only offer.
> I require my demands to be met by December 10, otherwise, the treaty falls through.
>
> Additionally, should I be contacted by agents from any of the 206 sovereignties, concerning the trades I placed on Kyber, the treaty falls through. In this case, rebates will total to exactly 0.
>
> Kyber is one of the original and longest-running DeFi protocols. No one wants to see it go under.
>
> To assist with this transition of leadership, I may be contacted on telegram: @Kyber_Director
>
> Thank you.
>
> - Kyber Director

**OBSERVED:** The two exploit-call inputs do **not** decode as text. Both begin with unrecognized selector `0x38f39e5c` (`0x09a3a12d…`: 932 bytes; `0x396a83df…`: 1,508 bytes). That does not establish what their calldata encodes; it only means these tools did not identify them as text or a known selector.

## Attacker playbook

**OBSERVED:** The exploit contract emits a repeated, staged sequence in its own runtime logs:

1. **Start a pool run and enter a flash callback.** For example, `0x09a3a12d…` emits “Inside flash callback” and “Raping Now” at logs 77–79; `0x396a83df…` does so at logs 123–125.
2. **Print a requested swap and calculate liquidity.** The first transaction’s run at logs 71–137 prints swap amounts, balances, liquidity values, and a “Glitch Liquidity” value. It prints `Glitch Liquidity = 203741196903450477362` at log 112 and `exactLiqNeeded = 202861333915261012721` at log 120.
3. **Mint and burn around the liquidity adjustment.** That first run emits “MINTED” at log 129 and “BURNED” at log 136. In the second transaction’s first run, the corresponding stages are visible at logs 153–184, with “MINTED” at log 176 and “BURNED” at log 183.
4. **Execute a step the contract calls the “doubling move,” then report repayment and balances.** The first run prints `delA = 1056056735638220800000` at log 139 and “Loan Paid off” at log 160. Another run in `0x09a3a12d…` prints `amoutn = 2000000000000000000000` and `fee = 1000000000000000000` at logs 276–279.

The pattern recurs across pool runs: `0x09a3a12d…` starts runs at logs 71 and 190; `0x396a83df…` contains repeated runs beginning at logs 118, 232, 349, 468, and 581, in addition to the initial run. The second transaction’s run at logs 617–699 again prints “building up fake liquidity,” “pulling off the doubling move,” and “Loan Paid off” (for example, logs 617–648, 649–671).

**INFERRED:** The logs support a playbook involving repeated pool operations, liquidity manipulation/adjustment, swaps, and repayment—rather than a single isolated swap. The labels “fake liquidity,” “Glitch Liquidity,” and “doubling move” are the contract’s own debug wording. These logs alone do **not** prove the precise vulnerable code path or the mechanism’s correctness. Nor do “Loan Paid off” and the printed amount/fee independently establish which lender supplied funds or the full loan accounting.

## Log-vs-flow verification

**OBSERVED:** `token_flows` reports net ERC-20 positions from Transfer logs. The attacker’s runtime lines are the exploit contract’s self-emitted “My token balances” entries; they are not, by themselves, independent balance proofs. The comparisons below were checked with `cross_check` before being relied on.

| Transaction / token | Net flow or log value | Verification result |
|---|---|---|
| `0x09a3a12d…`, wstETH | Net to labeled second address `0xc9b8…b50c6`: `4829465542309999342`; runtime log 185 prints the same number. | **Exact match:** `cross_check` finds Transfer log 176 (exploit contract → `0xc9b8…b50c6`) and runtime log 185; diff 0. |
| `0x09a3a12d…`, WETH | Net to `0xc9b8…b50c6`: `3285225174739883007634`; runtime log 187 prints `3006096242517832264121` (repeated at runtime log 287). | **Not an exact match.** `cross_check` finds no occurrence of the net-flow amount in Transfer logs or runtime logs. The logged amount and recipient’s net flow are different quantities in the evidence; the tools do not establish why. |
| `0x09a3a12d…`, KNC | Net to `0xc9b8…b50c6`: `640340747342134581728590`; runtime log 423 prints the same value. | **Numerical match** between net flow and runtime log 423. `cross_check` finds the runtime line, but no single exact Transfer for that amount; it does not prove how the net was composed. |
| `0x396a83df…`, ETHx | Net to `0xc9b8…b50c6`: `2548804968791375657`; runtime log 229 prints the same value. | **Exact match:** Transfer log 219 and runtime log 229; diff 0. |
| `0x396a83df…`, ELK | Net to `0xc9b8…b50c6`: `192194354498504288901718`; runtime log 346 prints the same value. | **Exact match:** Transfer log 336 and runtime log 346; diff 0. |
| `0x396a83df…`, HAY | Net to `0xc9b8…b50c6`: `9801937450941582`; runtime log 697 prints the same value. | **Exact match:** Transfer log 687 and runtime log 697; diff 0. |
| `0x396a83df…`, USDC | Net to `0xc9b8…b50c6`: `68171723014`; runtime log 465 prints `72978534070`. | **Not an exact match.** `cross_check` finds log 465 for the logged figure but finds no Transfer or runtime occurrence of the net-flow figure. Their arithmetic difference is `4806811056`, also printed at runtime log 213; that numerical coincidence does **not** prove the reason for the mismatch. |
| `0x396a83df…`, wstETH | Net to `0xc9b8…b50c6`: `287919243156368393`. | `cross_check` locates a Transfer at log 454, but no matching runtime line. |
| `0x396a83df…`, frxETH and FRAX | Net to `0xc9b8…b50c6`: frxETH `2054685392857451919`; FRAX `19184859751108358586988`. | `cross_check` locates Transfers at logs 567 and 568, respectively, but no matching runtime lines. |

**Conclusion:** The evidence **refutes a blanket claim** that the attacker’s runtime balance logs all match the token flows. It also **confirms exact, checked matches** for wstETH in `0x09a3a12d…`, and ETHx, ELK, and HAY in `0x396a83df…`. KNC is numerically equal as a net flow and runtime value, but `cross_check` does not find one Transfer of that exact amount. For WETH and USDC, the recipient net flows do not match the cited runtime amounts. Other net-flow values have Transfers but no matching runtime line. These comparisons do not show that every runtime balance snapshot should equal a recipient’s net flow; the available data do not explain the mismatches.

## Gaps

- **Calldata:** The exploit inputs’ selector `0x38f39e5c` is unresolved here. The input decoder does not expose their parameters or a full ABI interpretation.
- **Runtime logs:** They are emitted by the attack contract. They describe its execution path but are not independent traces of pool state, balances, or successful accounting.
- **Flow accounting:** `token_flows` provides net ERC-20 positions, while `cross_check` searches individual Transfer logs and runtime lines for a given amount. A net amount need not appear as one Transfer; the available results do not break every net into its constituent transfers.
- **Pool mechanics:** The logs show pool addresses and token addresses, but this evidence set does not include source-level analysis, full call traces, storage diffs, or independently reproduced pool math. The specific vulnerability mechanism remains an inference.
- **Attribution:** “KyberSwap Exploiter 1,” the second-address label, contract identification, and named recipient labels are supplied by the case index/public-report references. They are not identities established by the decoded transaction data. The messages’ claimed affiliations and Telegram contact are likewise claims in calldata, not verified identities.
- **Scope:** ERC-20 Transfer logs do not establish the full native-asset, loan, or profit accounting. This report does not calculate USD value or total loss.

## Next steps

1. Resolve `0x38f39e5c` against verified contract source/ABI or decode its parameters from the transaction trace.
2. Obtain execution traces and pool storage/state diffs for both exploit transactions, then test the logged liquidity calculations and “doubling move” against actual pool transitions.
3. Reconcile each recipient’s net token position against **all** same-transaction Transfer events, with amounts and endpoints grouped by token; distinguish exploit-contract balance snapshots from recipient transfers.
4. Independently verify the token and pool addresses, and establish the lending/repayment path from call traces rather than debug labels.
5. Treat address and actor labels as attribution leads only; do not infer a real-world identity from the on-chain messages or labels.