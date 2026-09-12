<!--
Immunefi / Cantina / Sherlock / CodeHawks submission template.
Web3 programs judge on funds-at-risk. A working PoC is effectively mandatory
for High/Critical. Fill every section; delete none. Do not submit until the
finding has cleared playbook/self-refutation.md and a human has read the PoC.
-->

# [Severity] Title: <one line, the impact, not the mechanism>

**Program:** <name + link to scope page>
**In-scope asset:** <exact contract/address/file from the scope list>
**Severity (self-assessed against the program rubric):** Critical / High / Medium
**Funds at risk:** <concrete amount or fraction of TVL, with the reasoning>

## Summary

Two or three sentences: what an attacker does, and what they gain. Impact
first. No preamble.

## Vulnerability details

The precise mechanism. Reference exact files and line numbers. Walk the call
path from the attacker's entry point to the damage, naming every function and
every check along the way (including the checks that do *not* stop it, and
why).

## Attack scenario / step by step

1. Attacker calls ...
2. State becomes ...
3. Attacker calls ...
4. Net result: attacker gains X, protocol/users lose Y.

State the prerequisites honestly: capital needed (assume flash-loan access),
timing, any privileged position, any required victim action.

## Proof of concept

A runnable Foundry (or Hardhat) test against a local fork. It must fail on the
fixed code and pass on the vulnerable code. Paste the test and the command to
run it, plus the relevant console output showing the balance change.

```solidity
// forge test --match-test test_exploit -vvv
```

## Impact

Map to the program's rubric. State the realistic worst case and who bears the
loss.

## Recommended fix

The minimal change that closes it, with the reasoning. A concrete fix
strengthens the report and speeds triage.
