# Clarity corpus scanner

Automated first-pass triage over the full set of deployed Stacks Clarity
contracts, to cut ~121k contracts down to a hand-auditable survivor list.

## Why

Hand-auditing the big, well-funded protocols one by one (Bitflow, ALEX,
Faktory, Hermetica, Velar, Zest, Arkadiko, Granite, StackingDAO…) has a low
hit rate — they are heavily audited. The higher-odds play is to sweep the
*entire* corpus for the specific Clarity antipatterns that cause fund loss,
then spend human attention only on hits that also look like they hold value.

## Data source

Clone the public mirror (read-only, anonymous git is fine):

    GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 \
      https://github.com/boomcrypto/clarity-deployed-contracts \
      /home/claude/boomcrypto/clarity-deployed-contracts

`contracts/<deployer-principal>/<contract-name>.clar`, refreshed daily by the
mirror's own GitHub Action. Index files it ships: `names.txt` (deployers with a
BNS name), `sip10.txt` / `sip9.txt` (recognized tokens), `blacklist.txt`.

## Stage 1 — `clarity_scan.py`

Parses each contract into its `define-public` / `define-private` /
`define-read-only` forms, then for every public function computes the
*transitive* body (the function plus the local helpers it calls) and flags it
when it reaches a value-moving sink with **no authorization guard anywhere on
that reachable text**:

- `MINT`    — reaches `ft-mint?` / `nft-mint?`  (→ infinite mint, then dump)
- `CUSTODY` — reaches `as-contract` + a transfer (→ drain the contract's holdings)
- `OWNER`   — `var-set` of an `*owner*` / `*admin*` data-var (→ takeover)

Guard = any of `is-eq tx-sender`/`contract-caller`, `contract-owner`,
`is-dao-or-extension`/`is-extension`, `check-is-*`, `only-*`, `has-role`,
`is-approved`, etc. (see `GUARD_TOKENS`).

    python3 clarity_scan.py [CONTRACTS_DIR] > scan_all.json

It is a *recall-biased heuristic*, not a prover. `CUSTODY` is noisy
(permissionless AMMs/claims are custodial by design and safe); `OWNER` and
`MINT` are rare and high-signal.

## Stage 2 — `rank.py`

A bug only pays if the contract controls value, and on-chain balances are not
readable from the sandbox. `rank.py` approximates value with corpus signals and
sorts the flagged set:

- `inbound` — how many *other* contracts reference this one (integration ⇒ TVL)
- `named`   — deployer owns a BNS name
- `sip`     — recognized SIP-010/009 token
- `kw`      — fund-holding keyword in the contract name (pool/vault/stake/…)

Class weights: `OWNER` ≫ `MINT` ≫ `CUSTODY`.

    python3 rank.py scan_all.json   # writes ranked.json, prints top 40

Then a human reads the top of `ranked.json`, confirms the bug against the
deployed source, and only a *confirmed, value-bearing* finding goes through the
self-refutation gate (`../../playbook/self-refutation.md`) before any report.
