# aidom — a security-bounty operation run from zero

This repository is the operating system for one job: earning money from
scratch by finding and reporting real security vulnerabilities, where a
machine does the reading and verifying and a human does only what the law
requires a person to do — pass identity checks, sign, and receive payouts.

It is not a plan document. It is the working toolkit: the audit method that
gets followed, the gate that keeps unreal findings from ever being sent, the
submission templates that meet each platform's evidentiary bar, the rules
that keep the account from getting banned, and a ranked list of real targets.

## Why security, and why standing bounties first

Every other way to earn from zero has a human bottleneck that cannot be
removed: a judge who must like a pitch, a maintainer who must review a pull
request, a grant officer who must read an application, a customer who must be
convinced. Standing bug bounties have none of that. The code is public, the
scope is authorised in writing, KYC happens only at payout, and the money is
decided by whether the bug is real and reproducible.

The edge here is not speed of submission — every platform now punishes
volume. The edge is speed of **verification**: reading a large codebase in
minutes, forming many hypotheses, then spending the hours a human would not
spend trying to refute each one before anyone sees it. In a market flooded
with unverified AI output, the submitter whose reports are always real is the
scarce thing.

## The division of labour

| Step | Owner | Notes |
|---|---|---|
| Pick and rank targets | machine | `targets/rank.py` over `targets/targets.json` |
| Read the code, form hypotheses | machine | `playbook/methodology.md` |
| Try to refute every hypothesis | machine | `playbook/self-refutation.md` — the gate |
| Write the report | machine | `templates/` |
| Read the PoC and approve the send | **human** | your legal warranty is on every report |
| Open accounts, pass KYC, receive payout | **human** | one sitting, see checklist below |
| Press submit | **human** | never automated — that is what gets accounts banned |

A report is only sent when it clears the self-refutation gate **and** a human
has read the proof of concept. Nothing is auto-submitted. Ever.

## Status

- [ ] Human account setup complete (see `playbook/rules-of-engagement.md`)
- [ ] First target selected from `targets/targets.json`
- [ ] First target source cloned and audited
- [ ] First report cleared the gate and was submitted
- [ ] First payout received

## What the human does next, once

The full list with the reasons is in `playbook/rules-of-engagement.md`. In
short: prepare a tax form and a bank/Wise account and a KYC'd crypto exchange
plus self-custody wallet, then open accounts on Immunefi, Cantina, HackerOne,
Bugcrowd, Sherlock and CodeHawks. Roughly three hours, done before anything is
earned, because prize and payout paperwork windows are short.

## What to hand the machine next

A single in-scope target to start on: either name a program from
`targets/targets.json` or paste the URL of its in-scope source repository.
The machine reads real source and reports only what it can reproduce. It will
not invent a finding to have something to show.
