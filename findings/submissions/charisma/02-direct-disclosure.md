# Charisma / Blaze — direct disclosure instructions (human-side)

This is a **Low** griefing finding. Deliver it privately, in good faith. Do **not**
disclose publicly and do **not** run the attack on mainnet — the verifier is
read-only and that is all that should ever touch the chain.

## Channel (pick one; GitHub private report preferred)

1. **GitHub private vulnerability report (preferred).** Go to
   `github.com/r0zar/charisma` → **Security** tab → **Report a vulnerability**
   (GitHub's private advisory form). If that button isn't present, the repo
   hasn't enabled private reporting — use option 2.
2. **Direct message to the author.** rozar.btc is active on X/Twitter as
   `@rozar` / `rozar.btc`. Send a short DM asking for a private channel to share
   a Low security finding in `blaze-v1`, then send the write-up.

Attach from `~/Downloads/`:
- `Charisma-blaze-uuid-griefing-report.pdf` (full write-up)
- `verify_blaze_uuid_griefing.py` (read-only verifier; python3 + curl, no wallet)

## Message body to paste

> Hi — good-faith private disclosure of a **Low** (griefing DoS, no theft) issue
> in the deployed `SP2ZNGJ85ENDY6QRHQ5P2D4FXKGZWCKTB2T0Z55KS.blaze-v1`.
>
> The replay map `submitted-uuids` is global and keyed on the UUID string alone,
> and `execute` consumes the UUID via `map-insert` before any signer-specific
> check. So any account can pre-consume a victim's UUID by calling `execute`
> directly with an intent they signed themselves that reuses that UUID; the
> victim's legitimate intent bearing the same UUID then reverts
> `ERR_UUID_SUBMITTED` on every subnet, since they share this one map. No theft
> and no permanent loss — the victim re-signs with a fresh UUID — but a griefer
> can bounce a targeted account's intents for one tx fee each, and this is the
> normal condition in a broadcast-intent/solver model where the signed UUID is
> visible before it lands on-chain.
>
> Suggested fix: key the replay map on `{ signer, uuid }` (recover the signer,
> then insert the pair) so unrelated parties can't collide on a UUID.
>
> Attached: a full write-up and a read-only Python verifier (no wallet, no
> transaction) that confirms the map key is signer-independent and global against
> mainnet. No mainnet exploitation was performed and nothing is disclosed
> publicly. Happy to walk through it.

## Honest expectation

Charisma runs no formal bounty. This is a Low with no fund loss; a reward is
unlikely. Value here is a genuine, correct disclosure on record — not income.
The two StackingDAO reports remain the findings with real upside.
