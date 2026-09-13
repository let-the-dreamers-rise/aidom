# [High] stBTC receives none of the protocol's sBTC reward stream: the live split leaves it a zero remainder, and the post-audit split calculator can never assign it one

**Program:** StackingDAO — https://immunefi.com/bug-bounty/stackingdao/scope/
**In-scope assets:**
- `SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG.rewards-pox5-v1` (listed asset; the distribution happens here)
- `SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG.reward-split-calculator-v2` and `.reward-split-ops-v2` (deployed 2026-08-30 after the scope snapshot; covered under the program's Primacy of Impact for High severity)
- `SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG.stbtc-reserve`, `.stbtc-token` (listed; the affected pool)

**Severity (self-assessed against the program rubric):** High — "theft / permanent loss of unclaimed yield". A stricter reading is Low ("contract fails to deliver promised returns"); the reasoning for High is in the Impact section.
**Funds affected:** the entire stBTC pool, 15,249,795,699 sats of stBTC (152.50 BTC, about USD 11.8M at USD 77,377/BTC) backed by 15,267,691,227 sats of sBTC, of which 15,000,000,000 sats (150 BTC) is bonded into PoX-5 bond 1, where it is 65% of all bonded sBTC. Under the protocol's own TVL-weighted split the pool's share of the reward stream is about 35%; it receives 0.004%. Shortfall to date about 27.9M sats (0.279 BTC, USD 21.6k); about 19.2M sats (USD 14.8k) more in the release window currently streaming; and, from this reward cycle on, 100% of the rewards earned by the pool's own 150 BTC bond.

## Summary

`rewards-pox5-v1.process-rewards` pays stBTC the remainder of each release after the stSTXbtc and stSTX shares. The live parameters are `ststxbtc-bps = 3291` and `ststx-bps = 6709`, which sum to exactly 10,000, so the remainder is the floor-division dust of 1 sat per call. Over the contract's whole history, stbtc-reserve has received 3,186 sats out of 79,394,283 sats distributed (0.004%). The mechanism meant to keep the split correct, `reward-split-ops-v2 → reward-split-calculator-v2`, computes `ststx-bps = 10000 − ststxbtc-bps`, so it is structurally incapable of ever assigning stBTC a non-zero share. The audited `reward-split-calculator-v1` did assign one. This is a post-audit regression that has silently zeroed the yield of the protocol's newest and only BTC-denominated product.

## Vulnerability details

### 1. Distribution: stBTC is the remainder

`rewards-pox5-v1.clar`, `process-rewards` (lines 83–97):

```clarity
(ststxbtc-share (/ (* release-amount (var-get ststxbtc-bps)) DENOMINATOR_BPS))
(ststx-share    (/ (* release-amount (var-get ststx-bps))    DENOMINATOR_BPS))
(stbtc-share    (- release-amount (+ ststxbtc-share ststx-share)))
...
(try! (route-sbtc-share stbtc-share .stbtc-reserve))
```

`set-split-bps` (lines 42–51) only requires `ststxbtc-bps + ststx-bps <= 10000`. The design clearly intends a remainder for stBTC: the Clarity Alliance PoX-5 review (2026-08-13, finding L-01) describes it in exactly these terms — "rewards-v7 treats stBTC as the implied remainder" — and the protocol bonds stBTC's own sBTC into PoX-5 (`strategy-v6.perform-bond → stbtc-staker-bond-1-v2.bond-sbtc`, 150 BTC on-chain) to generate that reward stream.

### 2. Live state: the remainder is zero

Read-only on mainnet at the time of writing:

| parameter | value |
|---|---|
| `rewards-pox5-v1.get-ststxbtc-bps` | 3291 |
| `rewards-pox5-v1.get-ststx-bps` | 6709 |
| sum | 10000 |
| stBTC remainder | 0 bps |

Replaying the integer arithmetic on release amounts seen in recent `process-rewards` events:

| release (sats) | stSTXbtc | stSTX | stBTC |
|---|---|---|---|
| 26,335 | 8,666 | 17,668 | 1 |
| 78,894 | 25,964 | 52,929 | 1 |
| 105,996 | 34,883 | 71,112 | 1 |
| 160,596 | 52,852 | 107,743 | 1 |

The 1 sat is floor-division residue, not a share.

### 3. Lifetime flows confirm it

Every sBTC transfer `rewards-pox5-v1` has ever made, aggregated from the public Hiro API (1,458 transactions):

| destination | sats | share |
|---|---|---|
| stSTX reward recipient `SP19E4PBQXGKY8C3977BA828HVGW2C8YH9KK9Y8AJ` | 44,171,095 | 55.64% |
| `ststxbtc-tracking-v2` | 21,668,098 | 27.29% |
| pool-owner receiver `SP1R9J9S0R3TRQ9EWW88TEE43N0KPBKFYTFH5D9` | 10,163,479 | 12.80% |
| `commission-sbtc-v1` | 3,388,425 | 4.27% |
| **`stbtc-reserve`** | **3,186** | **0.004%** |

Inflows total 134,279,138 sats (1.343 BTC) from seven PoX-5 signer managers; 54.9M sats are still queued in the current release window and will be distributed the same way.

### 4. The corrective mechanism cannot correct it

The audited `reward-split-calculator-v1.preview` derives both shares from the boosted TVL weights and leaves stBTC the rest:

```clarity
ststxbtc-bps: (/ (* w-ststxbtc 10000) w-sum)
ststx-bps:    (/ (* w-ststx    10000) w-sum)      ;; remainder = w-stbtc / w-sum
```

`reward-split-calculator-v2.preview` (lines 55–65), deployed 2026-08-30 and now the only calculator wired to `reward-split-ops-v2.refresh-split`, replaces the second line:

```clarity
ststxbtc-bps: ststxbtc-bps-raw,
ststx-bps:    (- (to-uint DENOMINATOR_BPS) ststxbtc-bps-raw),
```

The two outputs always sum to 10,000. `w-stbtc` still enters `w-sum`, so a larger stBTC TVL or a positive boost only shrinks the stSTXbtc share — the freed weight is handed to stSTX, never to stBTC. `set-split-bps` accepts the result because the sum does not exceed 10,000. `reward-split-calculator-v2` has emitted no events on mainnet, so this has not yet been exercised; the first keeper refresh will re-assert a zero stBTC share regardless of the TVL and `r-target` inputs.

`reward-split-calculator-v1` is no longer an active protocol contract in `dao`, so there is no on-chain path that produces a non-zero stBTC share except a direct governance call to `set-split-bps`.

### 5. How the live parameters came about

`reward-split-ops-v1` emitted six `refresh-split` events between blocks 8,800,174 and 8,830,916 (20–24 August 2026, a week after the stBTC launch, with roughly 100 BTC already deposited). Every one of them carried:

```
t-stbtc u0   t-ststxbtc u26500000000000   t-ststx u54000000000000   r-current-used u1000 (= r-target, boost 0)
-> ststxbtc-bps u3291, ststx-bps u6708
```

The keeper never supplied a stBTC TVL, so even the audited v1 calculator was asked to weight stBTC at zero. The live values are 3291 / 6709 (the v1 outputs sum to 9,999; 6709 is exactly `10000 − 3291`, the v2 formula). `reward-split-calculator-v2` and `reward-split-ops-v2` have exactly one transaction each on mainnet, their deployment, and no events, so the first time the keeper refreshes through the new path the zero share is re-asserted by construction, whatever `t-stbtc` is passed.

### 6. What the pool is entitled to, and what it is losing

The calculator is a TVL-weighted split with an stBTC boost; with `r-current = r-target` (which is what the keeper has been passing) it reduces to plain TVL proportion. Using the keeper's own unit (6-decimal STX) and 13 September 2026 spot prices (Kraken / CoinGecko: BTC 77,377 USD, STX 0.2702 USD, so 286,369 STX per BTC):

| leg | TVL | in keeper units (STX) | TVL-proportional share |
|---|---|---|---|
| stBTC | 152.50 BTC (USD 11.80M) | 43,670,000,000,000 | **35.2%** |
| stSTXbtc | 26.5M STX (keeper value) | 26,500,000,000,000 | 21.3% |
| stSTX | 54.0M STX (keeper value) | 54,000,000,000,000 | 43.5% |

Applied to the measured flows:

| | sats | BTC | USD |
|---|---|---|---|
| distributed to date, all legs | 79,394,283 | 0.794 | 61,434 |
| stBTC entitled share (35.2%) | 27,947,000 | 0.279 | 21,625 |
| stBTC actually received | 3,186 | 0.00003 | 2.5 |
| queued in the current release window (`get-streaming-remaining`) | 54,415,200 | 0.544 | 42,105 |
| stBTC entitled share of that window | 19,154,000 | 0.192 | 14,821 |

A ±30% move in the BTC/STX price ratio moves the stBTC share between roughly 30% and 40%; it does not change the conclusion. A positive boost (the calculator's purpose is to tilt toward stBTC when its yield lags `r-target`) would raise the entitled share further.

**Source of the stream, stated plainly.** The 134.3M sats received so far came from seven STX-only signer managers (`signer-manager-stacking-dao-v1`, `-xverse-v1`, `-juicy-stake-v1`, `-infstones-v1`, `-hashkey-v1`, `-foundry-v1`, `-blockdaemon-v1`). One could argue those rewards were earned by STX, not by stBTC; the protocol's own design says otherwise (a pooled, TVL-weighted split is why `w-stbtc` exists at all), but the forward loss does not depend on that argument: the pool's own 150 BTC bond (`stbtc-staker-bond-1-v2`, 65% of PoX-5 bond 1's 230.17 BTC) entered its first reward cycle, cycle 143, at the time of writing. Its rewards are claimed by `signer-manager-bond-1-v2`, whose `rewards-recipient` is `rewards-pox5-v1`, and therefore go through the same split. From the first claim onward, every sat earned by stBTC depositors' own sBTC is paid to the other legs.

## Steps to reproduce

No transaction, wallet or capital is needed; the state is live.

1. Run the attached `verify_reward_split.py` (python3 + curl only). It reads the two bps values, replays the split arithmetic, and sums the reward contract's lifetime transfers by destination. Output at the time of submission is included below.
2. Optional, for the calculator regression: in a Clarinet simnet deploy `reward-split-calculator-v2` and call `preview` with any positive `t-stbtc`, e.g. `(preview u1000 u100000 u100000 u100000)`. The returned `ststxbtc-bps + ststx-bps` is 10,000 for every input. Deploy `reward-split-calculator-v1` and call `preview` with the same arguments; the sum is below 10,000 by exactly `w-stbtc / w-sum`.

```
== 1. live split parameters (rewards-pox5-v1) ==
ststxbtc-bps = 3291
ststx-bps    = 6709
sum          = 10000
stBTC share  = 0 bps
== 3. lifetime sBTC flows of rewards-pox5-v1 ==
transactions scanned: 1458
outflow (distribution):
  SP19E4PBQXGKY8C3977BA828HVGW2C8YH9KK9Y8AJ    44,171,095 sats  55.635%
  ststxbtc-tracking-v2                    21,668,098 sats  27.292%
  SP1R9J9S0R3TRQ9EWW88TEE43N0KPBKFYTFH5D9    10,163,479 sats  12.801%
  commission-sbtc-v1                       3,388,425 sats   4.268%
  stbtc-reserve                                3,186 sats   0.004%
stBTC pool: supply 15,249,795,699 sats, bonded in PoX-5 15,000,000,000 sats
```

## Impact

stBTC is marketed as a BTC-yield product ("Bitcoin Staking rewards increase the value of stBTC relative to sBTC"). Its holders have deposited 152.5 BTC; the protocol has bonded 150 BTC of it into PoX-5 signer bonds, whose rewards are claimed into `rewards-pox5-v1`. Those holders are receiving 0.004% of the stream. The yield they are owed under the protocol's own allocation design is being paid, every 30 minutes, to holders of the other two products and to the fee recipients, and once paid it cannot be recovered for stBTC holders. This maps to the program's High tier ("theft / permanent freezing of unclaimed yield", USD 1,000–20,000 by funds at risk). It requires no attacker, which is why a stricter reading is "contract fails to deliver promised returns" (Low); but the loss is concrete, ongoing, measurable on-chain, and structurally locked in by the v2 calculator rather than being a one-off parameter mistake.

The current window has 54.4M sats queued; at the observed rate of roughly 26,000 sats per burn block, about 0.54 BTC (USD 42k) is distributed per 2,100-block window, none of it to stBTC. Its entitled share is about USD 14.8k per window today and will rise once its own bond rewards join the stream.

## Recommended fix

1. **Immediate (governance):** call `rewards-pox5-v1.set-split-bps` with values whose sum leaves stBTC its intended share, until the calculator is fixed.
2. **Code:** in `reward-split-calculator-v2.preview`, restore the v1 derivation so stBTC keeps its weighted share:
   ```clarity
   ststx-bps: (if (> w-sum u0)
     (/ (* w-ststx (to-uint DENOMINATOR_BPS)) w-sum)
     (if (> total-tvl u0) (/ (* t-ststx (to-uint DENOMINATOR_BPS)) total-tvl) u0)),
   ```
   and keep the L-01 handling for the `w-sum == 0` edge.
3. **Defence in depth:** have `set-split-bps` reject a sum of exactly 10,000 while `stbtc-token` supply is non-zero, so a zero stBTC share can never be applied silently again.

## Reward

Submitted under the program's published rubric as High ("theft / permanent freezing of unclaimed yield", USD 1,000–20,000 depending on funds at risk). I would ask the team to assess it against the full stBTC pool (152.5 BTC of user deposits, 150 BTC bonded) and the size of the reward stream it is excluded from, and to consider a discretionary award if triage settles on a lower tier, given that the finding is live, ongoing and fully reproducible from public data.
