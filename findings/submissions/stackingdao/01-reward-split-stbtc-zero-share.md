# [High] stBTC receives none of the protocol's sBTC reward stream: the live split leaves it a zero remainder, and the post-audit split calculator can never assign it one

**Program:** StackingDAO — https://immunefi.com/bug-bounty/stackingdao/scope/
**In-scope assets:**
- `SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG.rewards-pox5-v1` (listed asset; the distribution happens here)
- `SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG.reward-split-calculator-v2` and `.reward-split-ops-v2` (deployed 2026-08-30 after the scope snapshot; covered under the program's Primacy of Impact for High severity)
- `SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG.stbtc-reserve`, `.stbtc-token` (listed; the affected pool)

**Severity (self-assessed against the program rubric):** High — "theft / permanent loss of unclaimed yield". A stricter reading is Low ("contract fails to deliver promised returns"); the reasoning for High is in the Impact section.
**Funds affected:** the entire stBTC pool, 15,249,795,699 sats of stBTC (152.50 BTC) backed by 15,267,691,227 sats of sBTC, of which 15,000,000,000 sats (150 BTC) is bonded into PoX-5. Every sat of the shared sBTC reward stream that should reach this pool is instead paid to the stSTX recipient, the stSTXbtc tracker, the pool owner and the commission contract.

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

The current window has 54.9M sats queued; at the observed rate of roughly 26,000 sats per burn block, about 0.55 BTC is distributed per 2,100-block window, none of it to stBTC.

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
