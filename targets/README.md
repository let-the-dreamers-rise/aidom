# Targets

`targets.json` holds real programs from the September 2026 research.
`rank.py` scores them for fit and prints them best-first.

## The ranking, in one line

The score is not "biggest pool wins." It rewards **fresh code, low
competition, and zero upfront capital** over headline pool size, because the
operation's edge is reading recently-changed code before many others do — not
out-grinding a thousand researchers on a marquee $5M program.

```
python3 rank.py          # human-readable table
python3 rank.py --json   # for the machine to consume
```

## Keeping it real

Every figure here goes stale within days. `days_since_scope_change` and
`competition` in particular are operator estimates that must be refreshed from
the live scope page before a target is started. Pool sizes and even whether a
program is still live change weekly (Code4rena was the category leader and shut
down in May 2026).

## Workflow per target

1. Refresh the target's row from its live scope page.
2. Clone the in-scope source into a local, gitignored working directory.
3. Audit per `../playbook/methodology.md`.
4. Take every candidate through `../playbook/self-refutation.md`.
5. Draft survivors with the matching `../templates/` file.
6. Log the pass in `../findings/log.md` — including passes that found nothing.
   A clean "nothing found" is a real result, not a failure.
