# Findings log

One row per audit pass. Log every pass, including the ones that found nothing —
a clean "nothing found" is a real result and stops the target being re-audited
blindly. Only a row that reaches `submitted` involved a human pressing send.

| Date | Target | Scope ref | Candidates | Survived gate | Status | Payout |
|---|---|---|---|---|---|---|
| _ | _ | _ | _ | _ | _ | _ |

Status values: `auditing` · `nothing_found` · `drafting` · `awaiting_human_signoff` · `submitted` · `accepted` · `paid` · `rejected` · `duplicate`

No row moves to `submitted` until it has cleared every gate in
`../playbook/self-refutation.md` and a human has read the proof of concept.
