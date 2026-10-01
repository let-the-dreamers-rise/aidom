# ExecutorDAO-style treasury — missing authorization on `*-transfer-many`

**Date:** 2026-10-01
**Found by:** automated corpus scan (`tools/clarity-scanner`) → OWNER/CUSTODY
strict residue → human confirmation.
**Class:** missing authorization check (access control) → unauthorized fund
transfer / treasury drain.
**Severity (code-level):** Critical *if* a given treasury holds assets.

## The bug

The treasury extension (`ede006-treasury` / `bde006-treasury` /
`bme006-0-treasury`) guards **every** transfer entry point with
`(try! (is-dao-or-extension))` — so only the DAO core or a registered
extension can move funds — **except two**:

```clarity
(define-public (sip009-transfer-many (data (list 200 {token-id: uint, recipient: principal})) (asset <sip009-transferable>))
	(begin
		(as-contract (fold sip009-transfer-many-iter data asset))   ;; <-- no (try! (is-dao-or-extension))
		(ok true)))

(define-public (sip010-transfer-many (data (list 200 {amount: uint, recipient: principal, memo: (optional (buff 34))})) (asset <sip010-transferable>))
	(begin
		(as-contract (fold sip010-transfer-many-iter data asset))   ;; <-- no (try! (is-dao-or-extension))
		(ok true)))
```

Both are `define-public` with **no authorization assertion at all**. The
single-item siblings (`sip009-transfer`, `sip010-transfer`, `stx-transfer`,
`stx-transfer-many`, all `sip013-*`) each begin with
`(try! (is-dao-or-extension))`. Only the SIP-009/SIP-010 `-many` variants
omit it. Classic "added the batch variant later, forgot the guard."

## Why it drains

The iterators run inside `(as-contract …)`, so `tx-sender` becomes the
treasury principal:

```clarity
(define-private (sip010-transfer-many-iter (data {...}) (asset <sip010-transferable>))
	(begin
		(unwrap-panic (contract-call? asset transfer (get amount data) tx-sender (get recipient data) (get memo data)))
		asset))
```

A standard SIP-010 `transfer` asserts `(is-eq tx-sender sender)`. Here the
`sender` argument **is** `tx-sender` (the treasury, under `as-contract`), so
the check passes and the token moves the treasury's own balance.

**Exploit:** anyone calls
`sip010-transfer-many(data=[{amount: <treasury balance of T>, recipient: <attacker>, memo: none}], asset=T)`
for each SIP-010 token `T` the treasury holds (and the SIP-009 variant for
NFTs). No DAO proposal, no vote, no admin. Post-conditions are set by the
attacker, so they don't protect the contract. Drains everything.

Refutation attempts (all fail to save it):
- Other guard elsewhere? No — the whole body is `(begin (as-contract (fold …)) (ok true))`.
- `as-contract` doesn't own the tokens? It transfers whatever the treasury
  holds; attacker reads the balance and sets `amount` to it.
- Trait must match? Attacker passes the real token contract as `asset`.
- Fold return ignored? Yes — result discarded, `(ok true)` returned; transfers
  already happened as side effects.

## Scope / blast radius (deployed, from the mirror)

9 deployed treasuries carry the identical code:

- `SP167Z6WFHMV0FZKFCRNWZ33WTB0DFBCW9QRVJ627.ede006-treasury` — Marvin
  Janssen-style **ecosystem-dao** reference deployment (executor-dao,
  ede004/006/007-v2/008-v2).
- `SP3JP0N1ZXGASRJ0F7QAHWFPGTVK9T2XNXDB908Z.ede006-treasury` and `.bde006-treasury`
- `bme006-0-treasury` under 6 deployers: `SP3HAHEV768GAMP34MTEC83PJ4PG6ZSGBX52CR6XQ`,
  `SP1SCD8ERMTFYE6CK9S0MHWQCP6SY4NAVFJ538A27`, `SP22NW0RYCW4GFZRPE8VGJRCKGQMRMMX4903A2TRG`,
  `SP3Y12HJYP2NMNAFHWBPM2CMYDHYXME1F45GASVBG`, `SP22SW60674C0V6B5E234C7ZD2YR8WXKXXVC48GZR`,
  `SP2TQ069HEM31JMBNSMBP7MQDKDTB56F6M2B632JJ`.

The `bme*` deployers also ship `bme032-0-scalar-strategy-hedge`,
`bme010-0-liquidity-contribution`, `bme030-0-reputation-token`,
`bdp000-bootstrap` — a real-looking structured-product DAO family that
plausibly routes user liquidity into its treasury.

## Novelty

- The **canonical** `github.com/MarvinJanssen/executor-dao` repo contains only
  `ede000`–`ede005`; it has **no treasury extension and no `transfer-many`**
  (grep: 0 matches). So this treasury + its batch functions are a custom
  add-on in these deployments, not the audited canonical framework.
- No public disclosure of this found via web search.

## OPEN — blocks live-impact claim

**Do any of these 9 treasuries currently hold SIP-010 / SIP-009 tokens?**
On-chain balance reads are blocked from this sandbox (Hiro/Stacks API 403 at
the egress proxy). This must be checked on an explorer
(explorer.hiro.so/address/<treasury-principal>) before asserting live loss.
If empty, the finding is code-correct but zero-impact. If any hold assets,
it is a live, anyone-can-call critical drain.

## Next steps (NOTHING submitted/disclosed without Ash's go-ahead)

1. Check token balances of the 9 principals on an explorer.
2. If funded: identify the operating DAO/owner and whether it runs a bounty;
   responsible private disclosure (the funds are at immediate risk, so speed
   matters) — do NOT post the exploit publicly.
3. Run through `playbook/self-refutation.md` and package a PoC + read-only
   balance verifier before any contact.
