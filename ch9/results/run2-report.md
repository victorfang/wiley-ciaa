# Forensic report

## Timeline

**OBSERVED — transaction index.** The case index records two exploit transactions followed by three zero-value messages. The timestamps, blocks, and nonces below are from that index; sender and recipient descriptions are labels, not independent proof of identity.

| UTC time | Block / nonce | Transaction | Observed |
|---|---:|---|---|
| 2023-11-22 22:58:23 | 18630408 / 9 | `0x09a3a12d…` | Exploit-contract call, 932 input bytes; runtime logs show repeated pool operations. |
| 2023-11-22 22:58:35 | 18630409 / 10 | `0x396a83df…` | Exploit-contract call, 1,508 input bytes; runtime logs show further pool operations. |
| 2023-11-22 23:57:11 | 18630701 / 12 | `0x7a891258…` | Plain-text message sent to the address labeled KyberSwap Deployer. |
| 2023-11-28 22:10:47 | 18673017 / 13 | `0x5c27d8e9…` | Plain-text message sent to the address labeled Kyber DAO Multisig Wallet. |
| 2023-11-30 12:04:23 | 18684303 / 14 | `0x0479da9d…` | Plain-text “treaty” message sent to the address labeled Kyber DAO Multisig Wallet. |

**ATTRIBUTED — labels in the case index.** The index labels the sender as “KyberSwap Exploiter 1” and the exploit contract as the SharkTeam-reported exploit contract. It labels the latter two message recipients as Kyber DAO addresses. These are supplied labels; this report does not independently establish identities behind addresses.

## Decoded messages

**OBSERVED — decoded calldata.** The three later transactions contain readable UTF-8 text, not ABI calls. The decoder notes that explorers might misleadingly label the `Dear` and `To A` prefixes as method selectors. Their first four bytes are text (`0x44656172` and `0x546f2041`), not recognized selectors.

### `0x7a891258…` — Nov. 22

> Dear Kyberswap Developers, Employees, DAO members and LPs,
>
> Negotiations will start in a few hours when I am fully rested.
>
> Thank you.

### `0x5c27d8e9…` — Nov. 28

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

### `0x0479da9d…` — Nov. 30

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

**OBSERVED — exploit-call inputs.** The two exploit-call inputs are not decoded as UTF-8 text: `0x09a3a12d…` is 932 bytes and `0x396a83df…` is 1,508 bytes, both beginning with selector-like `0x38f39e5c`, which the decoder does not recognize. Thus the supplied evidence reveals no additional plaintext hidden messages in those inputs. The attack contract’s printable bytecode strings include operational/debug phrases such as “Glitch Liquidity” and “Step 4, pulling off the doubling move,” not further decoded messages.

## Attacker playbook

**OBSERVED — contract runtime logs.** In `0x09a3a12d…`, the contract logs enter a flash callback and proceed through “Step 2, finding liquidity required,” “Step 3, building up fake liquidity,” and “Step 4, pulling off the doubling move.” For example, the log reports “Glitch Liquidity” at log index **112**, “exactLiqNeeded” at **120**, then `delA` at **139** and later **258**. It also logs “Loan Paid off” at **160**. A subsequent pool sequence begins at log **190**; another begins at **308**.

In `0x396a83df…`, the same general sequence appears: flash callback at log **123**, “Glitch Liquidity” at **158**, `delA` at **186**, and “Loan Paid off” at **205**. Further pool sequences are visible later in the log stream, including one beginning at **232** and another at **581**. The runtime log contains pool and token addresses and successive balance/state reports.

**INFERRED — playbook.** The logs are consistent with repeatedly manipulating pool liquidity/accounting, executing large trades, and settling flash-borrowed amounts before proceeding to other pools. The code’s own “fake liquidity” and “doubling move” wording supports this interpretation, but the precise exploit mechanics cannot be independently reconstructed from debug strings and Transfer events alone.

**OBSERVED — post-exploit communications.** The sender first announced delayed negotiations, then described alleged hostile responses and a planned statement, then issued demands including executive control, temporary governance authority, company assets and information, and a 50% LP-loss rebate. The messages also set a Dec. 10 deadline and stated that contact by government agents would void the proposed rebate. Those are the message’s claims and demands; the evidence here does not establish that any party accepted them.

## Log-vs-flow verification

**OBSERVED — cross-check results.** The cross-check tool compared runtime-log integers with Transfer events and found these near-matches. In each case, the logged integer is **one raw unit greater** than the Transfer amount:

| Tx prefix | Runtime log index and logged amount | Transfer log index and amount | Result |
|---|---|---|---|
| `0x09a3a12d…` | 241: `7749224925102600392` | 243: `7749224925102600391` KNC | Transfer is 1 lower |
| `0x09a3a12d…` | 139: `1056056735638220800000` | 145: `1056056735638220799999` wstETH | Transfer is 1 lower |
| `0x09a3a12d…` | 258: `15230520795938600000` | 264: `15230520795938599999` WETH | Transfer is 1 lower |
| `0x09a3a12d…` | 376: `16126032558195200000` | 382: `16126032558195199999` WETH | Transfer is 1 lower |
| `0x396a83df…` | 186: `244080034447360000000` | 192: `244080034447359999999` ETHx | Transfer is 1 lower |
| `0x396a83df…` | 417: `2245012960051200000` | 423: `2245012960051199999` wstETH | Transfer is 1 lower |
| `0x396a83df…` | 299: `618828702402872400000` | 305: `618828702402872399999` WETH | Transfer is 1 lower |
| `0x396a83df…` | 535: `933596593953177600000` | 541: `933596593953177599999` FRAX | Transfer is 1 lower |
| `0x396a83df…` | 650: `100369700267622400000` | 656: `100369700267622399999` WETH | Transfer is 1 lower |

**INFERRED — rounding.** These nine paired values are close but do **not** match exactly. Their uniform one-unit difference is consistent with a rounding/truncation boundary, but the evidence does not establish the implementation-level cause. The cross-check is specifically a search for equal values or values off by one; it is not proof that every runtime integer has been matched to every relevant Transfer.

**OBSERVED — selected balance reconciliations.** Some logged balances reconcile exactly with net Transfer flows reported for the address the case data labels `0xc9b826…`:

- In `0x09a3a12d…`, runtime log **185** reports `4829465542309999342`, matching the reported wstETH net flow of `4829465542309999342`. Runtime log **423** reports `640340747342134581728590`, matching the reported KNC net flow of `640340747342134581728590`.
- In `0x396a83df…`, runtime log **229** reports `2548804968791375657`, matching the reported ETHx net flow of `2548804968791375657`; log **697** reports `9801937450941582`, matching the reported HAY net flow of `9801937450941582`.
- FRAX in `0x396a83df…` provides an arithmetic reconciliation: the logged balance at **564**, `6255995712288710961401`, plus the reported FRAX net flow `19184859751108358586988` equals the later logged balance at **578**, `25440855463397069548389`.

**INFERRED — reconciliation scope.** These exact matches and the FRAX prior-balance-plus-inflow calculation support correspondence between selected runtime balance reports and Transfer-derived net movements. They do not prove that every reported token balance or every asset across both transactions reconciles. The token-flow tool returns per-address net totals rather than individual event indexes, so those aggregate figures cannot themselves be cited to particular Transfer log indexes here.

**Conclusion.** The logs and Transfer flows are **partially corroborated, not an exact universal match**. Selected balances reconcile exactly, and the nine checked logged trade amounts are each one raw unit above their corresponding Transfer. That refutes literal exact equality for those nine pairs, while supporting a close match consistent with rounding.

## Gaps

- The two exploit-call inputs are not decoded beyond their selector-like prefix; the supplied tools do not expose a full call trace or explain the selector.
- Debug logs show the contract’s own emitted values and sequence, not an independent validation of the underlying pool-state calculations.
- Net token flows do not provide per-transfer log indexes or a complete per-asset accounting ledger in the returned results.
- The flow output includes a labeled “second address” (`0xc9b826…`). The relationship between that address and the exploit-contract logs is attributed by the case data; matching amounts alone do not prove control or ownership.
- The index and decoder provide messages and addresses, but do not establish whether the demands were accepted, whether funds were recovered, or whether off-chain communications occurred.

## Next steps

1. Obtain full transaction traces and token Transfer event listings for both exploit transactions; reconcile each asset and address by event index.
2. Compare pre- and post-transaction balances for the pools and addresses involved, accounting for any starting balances rather than relying only on net flow.
3. Independently inspect the exploit-contract bytecode and the relevant pool implementations to test the logged liquidity and rounding behavior.
4. Treat public-report and explorer labels as attribution, and verify address relationships from transaction-level evidence before making identity claims.
5. Review subsequent on-chain transactions for responses, fund movements, or attempted settlements; the five indexed transactions do not establish those outcomes.