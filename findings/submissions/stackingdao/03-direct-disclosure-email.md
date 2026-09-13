# Direct responsible disclosure — cover email (send from your own address)

**To:** philip@stackingdao.com (the legal-notice contact in StackingDAO's Terms of Service and Privacy Policy; co-founder)
**Sanctioned alternative channel:** StackingDAO's own security page (docs.stackingdao.com › Audits and Security) says: "If you discover a vulnerability, please disclose it privately and give the team a reasonable window to respond before any public disclosure" and "You can also reach the team via @StackingDAO on X." So a private DM to @StackingDAO on X is an officially listed route. Send the email first; if there is no reply within 3 business days, DM @StackingDAO on X with the first paragraph and ask for a secure address for the attachment. Do not post details in Discord, Telegram or any public channel.
**Subject:** Responsible disclosure — stBTC receives 0.004% of the sBTC reward stream (live, verifiable on-chain)
**Attach:** `01-reward-split-stbtc-zero-share.md`, `verify_reward_split.py`

---

Hi Philip,

I'm an independent security researcher. I have a verified, live finding in StackingDAO's reward distribution that I'd like to disclose privately to the team. Summary:

- `rewards-pox5-v1` pays stBTC the remainder of each sBTC release after the stSTXbtc and stSTX shares. The live split parameters are 3291 / 6709 bps, which sum to exactly 10,000, so the stBTC remainder is 1 sat of floor rounding per payout.
- Over the contract's whole history, `stbtc-reserve` has received 3,186 sats of the 79,394,283 sats distributed (0.004%), while the stBTC pool holds 152.5 BTC of deposits with 150 BTC bonded into PoX-5 bond 1.
- The post-audit `reward-split-calculator-v2` (deployed 30 August) computes `ststx-bps = 10000 − ststxbtc-bps`, so unlike the audited v1 it can never assign stBTC a non-zero share. The keeper's six `refresh-split` calls in August also passed `t-stbtc = 0`.
- The stBTC bond entered its first reward cycle (143) at the time of writing; its rewards flow through the same split, so from the first bond claim onward every sat earned by stBTC depositors' own sBTC goes to the other legs.
- At today's prices the pool's TVL-proportional share is about 35%: roughly USD 21.6k short to date and about USD 14.8k per two-week release window going forward.

The full write-up with contract line references, the exact read-only calls, and a two-line fix is attached, along with a script that reproduces every number from the public Hiro API with no wallet or transaction. Nothing was tested on mainnet and nothing has been disclosed to anyone else.

Your docs ask that vulnerabilities be disclosed privately with a reasonable window before any public disclosure, and list X as an alternative to the Immunefi program; this email follows that guidance. I intended to submit through Immunefi, but the submission form requires a 50 USDC fee per report that I'm not in a position to pay. I'd be grateful if the team would either sponsor that submission so it can be tracked on Immunefi, or handle it directly and consider a reward under your program's High tier ("theft / permanent freezing of unclaimed yield", USD 1,000–20,000), or a discretionary award at your judgement. I also have a second, lower-severity finding in the stSTXbtc reward tracker (an ungated function that can brick claims on deactivated positions) that I'll send once this one is acknowledged.

Happy to answer questions, walk the team through it on a call, and confirm the fix once deployed.

Best regards,
[your name]
[your contact, and an Ethereum or Stacks address for any reward]
