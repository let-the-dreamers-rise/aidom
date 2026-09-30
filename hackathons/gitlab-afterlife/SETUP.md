# Setting Afterlife up on gitlab.com

Check the official rules first when they publish on 5 Oct. The last GitLab
hackathon required projects to live in a hackathon group
(`gitlab.com/gitlab-ai-hackathon`), an MIT license, and a video under 3 minutes.
Adjust steps 1 and 6 to whatever this one says.

1. **Project.** Create a public project (in the hackathon group if required),
   named `afterlife`. Push the contents of `demo-app/` to its root, plus
   `flows/`, `README.md` and a `LICENSE` (MIT).
2. **Pages.** Settings → Pages: make sure Pages is enabled and note the URL.
   The first push to `main` runs `test → pages → smoke`.
3. **Duo.** Settings → GitLab Duo: turn on the Agent Platform and custom flows
   for the project/group (hackathon access or trial if the tier needs it).
4. **Flows.** AI → Flows → New flow, three times. Paste each YAML from
   `flows/`, name them `afterlife-ship`, `afterlife-guard`,
   `afterlife-postmortem`, visibility Public. Then Managed → Enable each one in
   the project. This creates service accounts like `ai-afterlife-ship-<group>`.
5. **Triggers.** AI → Triggers → New flow trigger:
   - `afterlife-ship`: Pipeline events → Passed
   - `afterlife-guard`: Pipeline events → Failed
   - `afterlife-postmortem`: Mention, and Work item → Status changed → Closed
6. **Labels.** Create `afterlife::release`, `afterlife::rollback`,
   `afterlife::revert`, `afterlife::incident`, `afterlife::postmortem`,
   `afterlife::follow-up`, `severity::2`, `breaking`.
7. **Dry run.** Follow `DEMO.md` once before recording.

Note from GitLab's docs: triggers only fire on actions by a human, not by bots
or other flows. That is why merging the release/rollback MRs is done by you,
and it is the human checkpoint in the story.
