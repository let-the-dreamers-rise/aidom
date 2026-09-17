# USDT0 -- audit notes

Program: Immunefi standing bounty (https://immunefi.com/bug-bounty/usdt0/information/)
Critical min $50k, max $6M EVM / $1M non-EVM; Medium $5k flat; PoC required; KYC required
for all reporters. Live since 2025-01-30, live scope updated 2026-09-01 (fresh).

## Access note (read this before re-running this pass)

The canonical source, `Everdawn-Labs/usdt0-tether-contracts-hardhat`, is **private** to
Claude's GitHub App entirely -- confirmed via a direct `create_session` attempt sourced
from it (fails with `github_repo_access_denied`, not a session-scoping error). The sibling
`Everdawn-Labs/usdt0-audit-reports` repo IS public and was cloned directly; it contains
`DEPLOYMENTS.md` with real deployed addresses across 11 chains (Ethereum, Arbitrum,
Optimism, Ink, Berachain, Flare, Corn, Unichain, Sei, HyperLiquid, Rootstock) plus prior
OpenZeppelin/ChainSecurity/Guardian/Paladin audit reports.

Actual contract source was obtained instead from a **third-party mirror**:
`chainwayxyz/token-bridge` (public repo, a LayerZero bridge integration project) vendors
Tether's real USDT0 contracts under `src/usdt0/` verbatim (matching license/copyright
headers "Copyright Tether.to" / "Copyright USDT0 2025"). Cross-checked: a second,
unrelated public repo (`arthurka-o/2025-eth-global-prague`, a hackathon project)
independently hardcodes the exact same deployed addresses as `DEPLOYMENTS.md` for
Ethereum/Arbitrum/Optimism/Berachain/Ink/Unichain -- strong (not cryptographic)
confidence this is the real, current contract logic. **Not bytecode-verified against
Etherscan** -- this session's network egress blocks all block explorers and Sourcify, so
there was no way to diff against deployed bytecode. Treat any future finding here as
needing that verification step before submission.

Files read (`chainwayxyz/token-bridge/src/usdt0/`):
- `Tether/TetherToken.sol` (100 lines) -- base ERC20 + blocklist + owner mint/redeem
- `Tether/TetherTokenV2.sol` (377 lines) -- adds permit + EIP-3009 gasless transfers
- `Tether/WithBlockedList.sol` (45 lines) -- the blocklist mixin
- `Tether/EIP3009.sol` (272 lines) -- Circle-derived gasless-transfer authorization
- `Wrappers/OFTExtension.sol` (89 lines) -- `TetherTokenOFTExtension`, the
  crosschainMint/crosschainBurn hook that LayerZero's OFT adapter calls on
  burn/mint-model chains (Arbitrum, Optimism, Ink, Berachain, Flare, Corn, Unichain,
  Sei, HyperLiquid, Rootstock per DEPLOYMENTS.md; Ethereum uses a lock/unlock adapter
  over the plain TetherTokenV2 instead, since it's the home chain)

NOT obtained: the actual `OUpgradeable`/`OAdapterUpgradeable` contracts (LayerZero-side
OFT adapter that calls `crosschainMint`/`crosschainBurn` and does the actual
send/lzReceive cross-chain messaging). chainwayxyz vendored only the Tether-branded
token contracts for their own bridge, not USDT0's own OFT wrapper. This is the single
biggest gap in this pass -- see below.

## Hypotheses formed and refuted

1. **Cross-chain blocklist bypass via bridging** (the main lead pursued). Hypothesis:
   can a blocked address avoid `WithBlockedList` by bridging (crosschainBurn/
   crosschainMint) instead of a normal `transfer`? REFUTED. `TetherToken
   ._beforeTokenTransfer(from, to, amount)` (`TetherToken.sol:47-53`) is OpenZeppelin's
   standard ERC20 hook, called internally by `_mint`/`_burn`/`_transfer` alike --
   `OFTExtension.sol` does not override it. It enforces
   `require(!isBlocked[from] || msg.sender == owner())`. `crosschainBurn(_from, _amount)`
   (`OFTExtension.sol:42-46`) calls `_burn(_from, _amount)`, which triggers this hook
   with `from = _from` -- a blocked address cannot bridge out, full stop. `crosschainMint`
   triggers the hook with `from = address(0)` (never blocked), so minting *to* a blocked
   destination succeeds -- but that mirrors the existing, intentional single-chain
   semantics (`transfer(to, amount)` also only ever checks `isBlocked[msg.sender]`/
   `isBlocked[from]`, never `isBlocked[to]` -- you can always *send to* a blocked address
   on mainnet USDT today, you just can't move funds *from* one). Not a gap, not novel.
2. **`onlyAuthorizedSender` / access control on `crosschainMint`/`crosschainBurn`**
   (`OFTExtension.sol:34,42`). Gated to `msg.sender == oftContract`, which is
   `onlyOwner`-settable (`OFTExtension.sol:48-51`). Correctly restrictive; no
   unprivileged path found. (Could not verify the OFT adapter's own access control on
   who can trigger it to call these -- see gap below.)
3. **EIP-3009 replay / signature forgery** (`EIP3009.sol`). Standard Circle-derived
   implementation (same lineage as USDC's, heavily audited elsewhere): per-authorizer
   nonce mapping (not sequential, so no ordering griefing), domain-separated via
   `_domainSeparatorV4()` (chainid + contract address, so no cross-chain or cross-contract
   replay), `receiveWithAuthorization` requires `to == msg.sender` (front-run guard).
   No forgery/replay path found.
4. **`destroyBlockedFunds`** (`TetherToken.sol:84-88`). `onlyOwner`, requires
   `isBlocked[_blockedUser]` already true, burns via the same `_beforeTokenTransfer`
   hook (the `msg.sender == owner()` branch lets the owner's own burn through). Correct,
   intentional admin path, no bypass by a non-owner found.
5. **EIP-712 domain separator staleness after `updateNameAndSymbol`** (minor lead, NOT
   fully chased). `OFTExtension._EIP712NameHash()` (`OFTExtension.sol:56-58`) overrides a
   dynamic name hash, but whether OZ 4.2's `EIP712Upgradeable._domainSeparatorV4()`
   actually calls that hook (vs. using a name cached at `initialize()`-time) could not be
   confirmed -- the `lib/` submodules were not checked out in this shallow clone. Flagging
   only: worst case here is legitimate signatures failing to validate post-rename
   (a DoS on permit/EIP-3009 usability), not a theft/forgery path, so it would cap at Low
   even if real. Not pursued further -- low value for the time cost.

## What this pass did NOT cover (highest-value next step if resumed)

- The actual LayerZero-side OFT adapter (`OUpgradeable`/`OAdapterUpgradeable`) --
  send()/lzReceive()/peer-trust/rate-limiter logic. This is where a cross-chain
  replay, peer-spoofing, or supply-inflation bug would actually live, and it's the one
  piece of this program's real attack surface this pass could not read. It's most likely
  LayerZero-Labs' own audited `OFTAdapter`/`OFTCore` base (already covered by dozens of
  audits across every LayerZero-based token), customized per USDT0's specific
  configuration -- but the exact customization (rate limits, peer set, any
  Tether-specific override) is unverified.
- Any of the other 10 non-Ethereum/non-Arbitrum chain deployments individually (Ink,
  Berachain, Flare, Corn, Optimism, Unichain, Sei, HyperLiquid, Rootstock) -- addresses
  are all in `DEPLOYMENTS.md`; not diffed against each other for a chain-specific
  misconfiguration (e.g. a stale ProxyAdmin owner, a peer set incorrectly on one chain).
- Bytecode verification of the vendored source against actual deployed bytecode (blocked
  by this environment's network policy -- block explorers and Sourcify are both
  unreachable). A future pass with explorer access should diff before trusting this
  source for a submission.

## Verdict

No hypothesis survived Gate 2. This is a real pass against real (high-confidence,
not-yet-bytecode-verified) source, not a blocked/skipped target. The genuinely
uncovered surface -- the LayerZero OFT adapter contracts themselves -- is the right
place to resume if this target is revisited, but requires either GitHub App access to
the private Everdawn-Labs repo or explorer/Sourcify access to pull verified deployed
source directly.
