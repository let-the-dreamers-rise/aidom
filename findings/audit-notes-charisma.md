# Charisma / Blaze audit notes — 2026-09-14 (deep dive)

Deployer: SP2ZNGJ85ENDY6QRHQ5P2D4FXKGZWCKTB2T0Z55KS. Repo: github.com/r0zar/charisma
(packages/clarity/contracts). Blaze = intent-signature execution layer (SIP-018
secp256k1 verifier + uuid replay-guard) underpinning "subnet" tokens and an
intent DEX. Deployed-vs-repo cross-checked via Hiro.

## Deployment status (critical)
DEPLOYED under the deployer: `blaze-v1`, `multihop`, `charisma-token`, `energy`,
`hooter-farm-x10`. NOT deployed (404): `x-pool`, `x-vault`, `x-charisma-token`,
`x-welshcorgicoin-token`, `x-multihop`. So the repo's intent-DEX / subnet-token
code is dev/unshipped; only blaze-v1 + non-signature multihop are live.

## blaze-v1 (deployed) — sound verifier, one Low
`execute(sig,intent,opcode,amount,target,uuid)` hashes {contract=contract-caller,
intent,opcode,amount,target,uuid} (SIP-018), recovers the signer, and consumes
the uuid via `map-insert` (err rolls back the insert). Correct: cross-subnet and
cross-function replay are blocked (contract + intent are in the hash), uuid is
single-use, a failed sig doesn't burn the uuid.
- LOW (griefing DoS, deployed): the uuid map is GLOBAL and execute doesn't care
  WHO signed. An attacker can call execute with a self-signed intent using a
  victim's uuid U, consuming U first; the victim's legitimate intent then reverts
  ERR_UUID_SUBMITTED. No theft (victim re-signs with a new uuid); costs the
  griefer gas. Likely considered inherent to nonce/uuid intents.

## Repo x-* intent DEX (NOT deployed) — pre-deployment warning
`x-pool.x-swap-a-to-b(amount,signature,uuid,recipient)`: the signed intent it
consumes (`x-charisma-token.x-transfer sig amount uuid CONTRACT`) authorizes only
"move `amount` of the signer's token A to the pool CONTRACT" — the swap OUTPUT
`recipient` is a separate, UNBOUND parameter, and x-pool never learns the signer.
Any observer of the signed intent (normal in a solver/intent model, or via
mempool front-run) could call x-swap with recipient=attacker, spending the
victim's input and taking the output. THEFT — but the contract is not deployed,
so this is a warning to fix before shipping (bind the output recipient, or return
the signer from x-transfer and assert recipient==signer), not a live finding.
Subnet token transfer fns themselves are sound: x-transfer binds exact
amount+target; x-transfer-lte has `(asserts! (<= actual bound))`; x-redeem is
intentional bearer (target=none).

## Verdict
No live, high-confidence, payable finding. One deployed Low (uuid griefing) and
one serious pre-deployment warning (x-pool recipient binding). Good-faith
disclosure to Charisma (r0zar) is worthwhile; unlikely to be a cash bounty.
