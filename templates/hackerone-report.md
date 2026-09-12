<!--
HackerOne / Bugcrowd / Anthropic template for web and application findings.
These programs require human-validated, reproducible reports. Duplicates and
out-of-scope reports dominate their queues, so scope and reproducibility are
everything. Do not submit until cleared by playbook/self-refutation.md and a
human has reproduced the steps.
-->

# Title: <impact> via <mechanism> in <component>

**Program / asset:** <name + exact in-scope asset>
**Weakness:** <CWE or class, e.g. IDOR / SSRF / broken access control>
**Severity (CVSS or program scale):** <vector + score, or the program's tier>

## Summary

What the attacker achieves and why it matters, in two or three sentences.

## Steps to reproduce

Exact, ordered, copy-pasteable. Include the account roles used (e.g. "as a
low-privilege user A, against user B's object"), the full requests, and the
expected-versus-actual response. A triager should reproduce it without
guessing.

```
1.
2.
3.
```

## Proof of concept

Requests/responses, screenshots, or a short script. Show the exact response
that proves the impact (the other user's data returned, the privileged action
succeeding, the exfiltrated value).

## Impact

Concrete consequence for the business and its users. Tie it to the program's
paid-impact list. If the program excludes this class (many exclude jailbreaks,
prompt injection, self-XSS, missing best-practice headers), do not submit.

## Remediation

The specific fix (an ownership check on the object, an allowlist on the URL, a
server-side authorization check), not a generic "validate input".
