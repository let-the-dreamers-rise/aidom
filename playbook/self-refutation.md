# The self-refutation gate

This is the single most important file in the repository. It is the reason
the operation earns instead of getting banned. No finding is written up, and
no report is sent, until it has passed every question here and has a proof of
concept that actually runs.

The mindset is adversarial toward your own finding. You are not trying to
confirm the bug. You are trying to kill it. If you cannot kill it, and you can
demonstrate it, only then is it real.

## Gate 1 — Is it even in scope and in-impact?

- [ ] The affected contract/asset is on the program's in-scope list.
- [ ] The impact is on the program's paid-impact list (not merely "a bug").
- [ ] It is not on the known-issues / previous-findings / out-of-scope list.
- [ ] It is not a category the program explicitly excludes (e.g. jailbreaks and
      prompt injection on most AI-product programs; centralisation risk on many
      DeFi programs; theoretical issues with no funds at risk).

If any box is unchecked, stop. It pays nothing.

## Gate 2 — Try to refute the mechanism

For every hypothesis, force yourself to answer:

- [ ] **Is the vulnerable path actually reachable** by an unprivileged
      attacker? Re-read every modifier and require on the call path. Many
      "bugs" die here because a check three frames up already blocks them.
- [ ] **Does an existing invariant already prevent it?** A later check, a
      reentrancy guard, a supply cap, a settlement step.
- [ ] **Am I misreading the code?** Re-read the exact lines. Check the compiler
      version's semantics (e.g. Solidity ≥0.8 reverts on overflow; unchecked
      blocks do not). Check inherited and overridden functions, not just the
      one in front of you.
- [ ] **Does it depend on a wrong assumption about a dependency?** How does the
      real oracle behave, the real token, the real proxy — not the idealised
      one.
- [ ] **Is the profit real after costs?** Gas, flash-loan fees, slippage,
      capital. An "attack" that nets a loss is not a finding.

A hypothesis that survives all of these is a candidate. Not yet a report.

## Gate 3 — Prove it

- [ ] A proof of concept exists and **runs** (a Foundry/Hardhat test that
      reverts on the fixed code and passes on the vulnerable code; for web, a
      reproducible request sequence with expected vs actual response).
- [ ] The PoC uses only in-scope assets and does not touch mainnet state,
      other users' funds, or anything outside the rules of engagement. Fork
      tests locally; never exploit a live deployment.
- [ ] The PoC is minimal — it demonstrates the one bug, with no unrelated
      noise.
- [ ] Numbers are shown: attacker cost in, attacker value out, net.

## Gate 4 — Human sign-off

- [ ] A human has read the PoC and the impact statement and agrees it is real.
- [ ] KYC/payout for this program is already set up so a win is not forfeited
      on a paperwork deadline.

Only after Gate 4 does anyone press submit.

## Hard rules, no exceptions

- **Never** submit a finding that has not cleared Gates 1–3. One unverified
  report can get the account permanently banned (Immunefi has done this;
  Bugcrowd bans "submission farming" permanently).
- **Never** auto-submit. A machine drafts; a human sends.
- **Never** exploit a live deployment to "prove" a bug. Local fork only.
- **Never** submit the same root cause under two accounts, or hold more than
  one account per platform. Instant ban everywhere.
- When uncertain whether something is real, it is not real yet. Downgrade, or
  drop it. The cost of a false report is the account; the cost of a dropped
  true report is one missed payout. These are not symmetric.
