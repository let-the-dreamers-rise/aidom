# lollms — DM reactions IDOR (SUBMITTABLE, awaiting human sign-off)

**Status:** cleared the self-refutation gate (Gates 1–3). Awaiting **Gate 4** —
a human must reproduce the PoC and press submit on huntr. Nothing auto-submitted.

- **Target:** parisneo/lollms (huntr OSV — paid, monthly Stripe payouts)
- **Bug:** Broken object-level authorization (IDOR) in
  `POST /api/dm/messages/{message_id}/reactions` → any authenticated user reads
  the content of **any** private direct message (and writes reactions to it).
- **Severity:** High (CVSS ~7.1; sibling friends IDOR CVE-2026-0562 scored 8.3).
- **Verified:** on today's HEAD `a744154` with a runnable PoC that executes the
  real endpoint function. Duplicate-checked — no CVE covers this endpoint.

## Files
- `report-dm-reaction-idor.md` — the huntr submission draft (human rewrites in
  their own words before sending; huntr rejects verbatim AI text).
- `poc_dm_reaction_idor.py` — self-contained PoC. Runs the real
  `toggle_dm_reaction` against a temp SQLite DB with the project's real ORM
  models; proves cross-user content disclosure + reaction write.

## Reproduce
```bash
cd /home/user/aidom/work
git clone --depth 1 https://github.com/parisneo/lollms.git lollms-src   # if not present
python3 -m venv venv-lollms
./venv-lollms/bin/pip install fastapi==0.129.0 sqlalchemy==2.0.43 pydantic==2.12.5 \
  "pydantic[email]==2.12.5" werkzeug==3.1.6 Pillow==12.3.0 ascii_colors==0.12.3 \
  "passlib[bcrypt]==1.7.4" "python-jose[cryptography]==3.5.0" requests python-multipart \
  aiofiles email-validator beautifulsoup4 pipmaster toml python-dotenv
cd ../findings/submissions/lollms
LOLLMS_SRC=/home/user/aidom/work/lollms-src PYTHONPATH=/home/user/aidom/work/lollms-src \
  ../../../work/venv-lollms/bin/python poc_dm_reaction_idor.py
```
Expected: `READ-IDOR … CONFIRMED` and `WRITE-IDOR … CONFIRMED`.

## Before the human submits (Gate 4 checklist)
- [ ] Re-confirm no duplicate on huntr's disclosure list + GitHub advisories.
- [ ] Optionally do a live HTTP repro on a local lollms instance (curl steps are
      in the report) for an in-context screenshot.
- [ ] Rewrite the report in the submitter's own words (huntr closes verbatim
      AI-generated text).
- [ ] Confirm lollms is still an active, paying huntr program.
