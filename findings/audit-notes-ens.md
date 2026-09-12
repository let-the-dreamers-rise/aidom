# ENS audit notes — first pass, 2026-09-12

Target: ENS standing bug bounty (Immunefi), mainnet contracts.
Source: github.com/ensdomains/ens-contracts at commit 121dc23 (2026-09-11).
Scope reference: the mainnet deployments listed on the ens-contracts wiki, per
the program's in-scope assets. Testnet and the web apps were not looked at.
Fees: confirmed fee-free, KYC generally not required. The separate ENS *audit
competition* (Manager/Explorer web apps) charges a submission fee and is out.

This is a partial pass. About 15 of ~162 contracts were read closely. No
finding cleared the self-refutation gate. Recorded here so the work is not
repeated and so a continuation starts from the right place.

## Covered, nothing that clears the gate

- **ETHRegistrarController** (register/renew/commit, payment and refund path).
  Commit-reveal is standard; the commitment is deleted before external calls;
  the refund is computed per-call from `msg.value`; the attacker-controlled
  `resolver` is called via `multicallWithNodeCheck` before the NFT transfer,
  but reentering `register` fails on the already-deleted commitment and yields
  no double-refund or free registration. No profit path found.
- **BaseRegistrarImplementation** (register/renew/reclaim, expiry, grace
  period). Controller-gated; `available()` and the grace-period math check out.
- **ReverseRegistrar / DefaultReverseRegistrar / SignatureUtils.** The
  ERC-191/ERC-6492 signature path enforces an expiry window (<= 1 hour) and
  validates via SignatureChecker / the universal validator. The `authorised`
  modifier and `ownsContract` fallback are the long-standing ENS design.
- **PublicResolver / Multicallable.** `multicallWithNodeCheck` enforces the
  namehash prefix on each inner call; `isAuthorised` trusts only the configured
  ETH controller and reverse registrar plus the node owner / wrapper owner.
- **RegistrarSecurityController / RootSecurityController.** Break-glass, all
  `onlyOwner` / `onlyController`; no unguarded path.

## The one lead worth continuing

The freshest code in the repo is the CCIP-Read batch error handling, changed in
the two commits immediately before head (#574 on 2026-09-10, #575 on
2026-09-11). Freshly changed code is where the fewest eyes have been, which is
exactly the edge to press. Files:

- `contracts/ccipRead/CCIPBatcher.sol` — `_isSafeBatchGatewayError()` now
  allowlists only `Error(string)` and `HttpError`; everything else is wrapped
  in `UnsafeBatchGatewayResponse`. `_toResponseArray()` pads non-empty error
  data to `length % 32 == 4` "to prevent unverified data passing as a valid
  response".
- `contracts/universalResolver/AbstractUniversalResolver.sol` and
  `ResolverCaller.sol` — consume batch results and decide success vs. error.

Why it is only a lead, not a finding: these are all `view` resolution paths.
The plausible impact is a *resolution-correctness* bug — a malicious batch
gateway or resolver getting crafted error bytes interpreted as a valid answer,
which a wallet UI could render as a wrong address. That is potentially in
scope under "unintended alteration of what the NFT represents"-style impacts,
but its severity depends entirely on the program's rubric, and it needs a
working PoC before it is anything at all. Not claimed as a bug.

### To continue this properly

1. Model the batch gateway as fully adversarial (it is untrusted by design).
   Enumerate every byte sequence it can return for `failures[]` / `responses[]`
   and trace each through `ccipBatchCallback` -> `_toResponseArray` ->
   `resolveBatchCallback`, looking for any error value that reaches a caller as
   a non-reverting, attacker-chosen "answer".
2. Pay attention to the padding branch: an error whose length makes
   `(4 - v.length) & 31 == 0` is *not* padded. Check whether an unpadded error
   value can be `abi.decode`d downstream as a valid `bytes`/`address`.
3. Build a Foundry PoC with a mock adversarial batch gateway and a mock
   resolver. The repo is hardhat+bun; a standalone Foundry harness that imports
   only these files plus OpenZeppelin is the fastest way to a runnable PoC.
   Requires `forge` (not installed in this session) and the OZ deps.
4. If and only if a crafted error reaches a caller as a valid answer, and the
   PoC demonstrates it, run it through `playbook/self-refutation.md` and draft
   with `templates/immunefi-report.md`. Otherwise log it as checked and move to
   the next target.
