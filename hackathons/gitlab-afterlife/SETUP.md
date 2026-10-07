# Setting Afterlife up for the hackathon (official rules, 7 Oct 2026)

Deadline: **27 Oct 2026, 13:00 UTC**. Path A projects must be **created on or
after 5 Oct 2026**, be public, MIT-licensed, and use the GitLab Duo Agent Platform.

## Ash: do these first (they gate everything else)

1. **Register on Devpost** (if not done):
   https://gitlab-transcend.devpost.com/
2. **Contributor onboarding** (about 5 minutes, then ~24 h for GitLab to
   approve). Approval provisions your hackathon group, subgroup and project:
   https://contributors.gitlab.com/transcend-hackathon
3. Tell Claude in the thread once you're approved, and paste the project URL.

## After approval (Claude can walk you through each click)

4. **Code.** Push `demo-app/` (as the repo root), `flows/`, `README.md` and
   `LICENSE` into the provisioned project as a fresh repository.
5. **Pages.** Settings → Pages: enabled. First push to `main` runs
   test → SAST/secret detection → pages → smoke.
6. **Flows.** AI → Flows → New flow, three times, pasting each YAML from
   `flows/` (`afterlife-ship`, `afterlife-guard`, `afterlife-postmortem`). Then
   Managed → Enable each in the project.
7. **Triggers.** AI → Triggers → New flow trigger:
   - `afterlife-ship`: Pipeline events → Passed
   - `afterlife-guard`: Pipeline events → Failed
   - `afterlife-postmortem`: Mention, and Work item → Status changed → Closed
8. **Labels.** `afterlife::release`, `afterlife::rollback`, `afterlife::revert`,
   `afterlife::incident`, `afterlife::postmortem`, `afterlife::follow-up`,
   `severity::2`, `breaking`.
9. **Optional Google Cloud bonus.** Create a public website bucket and a
   service account with Storage Admin; add CI/CD variables `GCS_BUCKET` and
   `GCP_SA_KEY` (type File).
10. **Run the demo** in `DEMO.md`, record it (max 3 min), upload to YouTube as
    public.
11. **Submit on Devpost:** description (from `README.md`), public GitLab repo
    URL, YouTube link, and the Google Cloud URL if you did step 9.

Note from GitLab's docs: triggers only fire on actions by a human, not bots or
other flows. That's why you merge the release, rollback and revert MRs
yourself. That's the "review final outcomes" step that makes this a
Supervised entry.
