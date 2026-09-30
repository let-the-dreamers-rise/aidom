# Afterlife: your code's life after merge, run by agents

Entry prep for GitLab's **Life After Code** hackathon (Devpost, 5–27 Oct 2026,
$45k). Official rules and challenge paths publish on 5 Oct; this is built so it
can be adapted to them in a day.

**Pitch:** A developer's job ends at "merge". Afterlife takes it from there:
versioning, changelog, release, deploy verification, incident response,
rollback, culprit revert, and a blameless postmortem with follow-up issues.
Three custom flows on the GitLab Duo Agent Platform, wired to GitLab's own
pipeline, merge-request and work-item triggers. One human click (merging the
release MR) is the only required step; everything else is hands-off.

## Stages covered

| Stage | Who does it | How |
|---|---|---|
| Decide if main is releasable | `afterlife-ship` gate agent | Pipeline **Passed** trigger |
| Semver bump from Conventional Commits + MR labels | `afterlife-ship` release writer | tags + compare API |
| Changelog + release notes + risk call-out | release writer | commits `CHANGELOG.md`, `VERSION`, opens "Release vX.Y.Z" MR |
| Tag + GitLab Release | CI (`prepare_release`, `publish_release`) | on merge of the release MR |
| Deploy | CI (`pages`) | GitLab Pages = production |
| Verify production | CI (`smoke`) | checks the *live* site: version, config, core logic |
| Triage failures | `afterlife-guard` triage agent | Pipeline **Failed** trigger → production / regression / flaky / ignore |
| Incident + rollback | guard `rollback` agent | incident issue with timeline, rollback MR to last good tag, pings suspect MR |
| Culprit revert | guard `revert_culprit` agent | bisects last-green..failed, revert MR, tells the author |
| Blameless postmortem + follow-ups | `afterlife-postmortem` | Mention or work-item **closed**; commits `docs/postmortems/*.md`, files follow-up issues |

## Layout

- `flows/afterlife-ship.yml`, `flows/afterlife-guard.yml`,
  `flows/afterlife-postmortem.yml` — the custom flows (flow registry v1).
- `demo-app/` — Splitly, a tiny bill-splitter that plays "production":
  unit tests, GitLab Pages deploy, live smoke test, tag-and-release jobs.
- `tools/validate_flows.py` — validates the flows with **GitLab's own**
  `FlowValidator` from the Duo Workflow Service (the code behind
  `ValidateFlowConfig`), plus the extra custom-flow restrictions from the docs
  and a check that every tool name exists in the real tools registry.

## Validation status (30 Sep 2026)

All three flows pass GitLab's validator (component build, routing, tool names,
tool options, prompt-variable checks). A deliberately broken copy (misspelled
tool, wrong prompt variable) fails with both errors, so the check is live.
The demo app's unit tests pass, and the smoke test passes against a local copy
of the site and fails on two injected production bugs (invalid currency in
`config.json`; `split()` dropping cents).

Not yet done, because it needs a GitLab account with Duo Agent Platform access:
running the flows end to end on gitlab.com, and recording the demo.

```bash
# from a checkout of gitlab-org/modelops/applied-ml/code-suggestions/ai-assist
# with `poetry install --only main` done (Python 3.12)
PYTHONPATH=. .venv/bin/python /path/to/tools/validate_flows.py /path/to/flows/*.yml
```

See `SETUP.md` for the gitlab.com steps and `DEMO.md` for the video script.
