# Demo run and 3-minute video script

## Scenario (do once before recording, then record a clean run)

1. **Ship.** Merge two small MRs to `main`:
   `feat: show per-person share with currency symbol` and
   `fix: reject tip below zero`. Pipeline passes → **afterlife-ship** opens
   "Release v0.2.0" with changelog and a risk line. Merge it → CI tags v0.2.0,
   publishes the release, deploys, smoke passes.
2. **Break production.** Merge an MR that passes unit tests but breaks the live
   site: `chore: switch display currency` changing `public/config.json` to
   `{ "currency": "DOLLARS" }`. Deploy succeeds, **smoke fails** →
   **afterlife-guard** triages "production", opens an incident with a timeline
   and the failing assertion, opens "Rollback to v0.2.0", and pings the MR.
   Merge the rollback → smoke goes green.
3. **Break a test.** Merge an MR that changes rounding in `public/split.js`
   (drop the remainder). Tests fail on main → guard triages "regression",
   finds the commit, opens a revert MR and tells the author.
4. **Learn.** Close the incident (or comment
   `@ai-afterlife-postmortem-<group> write it up`) → **afterlife-postmortem**
   opens `docs/postmortems/<date>-<slug>.md` in an MR and files follow-up
   issues (for example "validate config.json in CI").

## Video (under 3:00)

| Time | Show | Say |
|---|---|---|
| 0:00–0:15 | The merge button | "Every developer's work ends here. Afterlife is what happens next, run by agents on GitLab." |
| 0:15–0:45 | Pipeline passes → Release MR appears | "Main went green, so Afterlife cut a release: semver from the commits, changelog, and a risk call-out. I merge it; CI tags and deploys." |
| 0:45–1:30 | Bad config MR → smoke fails → incident + rollback MR | "This change passed every unit test but broke the live site. The smoke test caught it, and Afterlife opened an incident with a timeline, a rollback to the last good release, and told the author." |
| 1:30–2:00 | Rounding MR → tests fail → revert MR | "When a regression lands on main, it finds the culprit commit and opens a revert." |
| 2:00–2:35 | Postmortem MR + follow-up issues | "When the incident closes, it writes a blameless postmortem and files the fixes that would have prevented it." |
| 2:35–3:00 | The three YAML files + stages table | "Three custom flows, GitLab's own triggers, ten lifecycle stages, one human click." |
