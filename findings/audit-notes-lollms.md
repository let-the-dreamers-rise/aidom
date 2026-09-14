# lollms (parisneo/lollms) — audit notes

**Date:** 2026-09-14
**Source:** `parisneo/lollms` @ HEAD `a744154` (2026-09-14; current `main`, contains
the CVE-2026-10595 `ui.py` fix, so the `APP_VERSION=2.1.0` string is just unbumped)
**Auditor pass:** IDOR / path-traversal / SSRF siblings of the 2026 huntr CVEs.
**Outcome:** **1 submittable High finding** (DM reactions IDOR) — cleared Gates 1–3,
awaiting human sign-off. See `submissions/lollms/`.

## Why lollms

Duplicate-check-first recon (the Feast lesson) showed lollms is a **fresh, funded,
fast-moving** target: a rewritten FastAPI social app (`backend/routers/`) that keeps
earning 2026 huntr bounties — CVE-2026-10595 (ui.py path traversal), CVE-2026-0560
(files.py SSRF), CVE-2026-0562 (friends.py IDOR), CVE-2026-12228 (prompts stored XSS).
The maintainer's pattern is to patch the one reported endpoint and leave siblings —
ideal for a sibling hunt. Lower hardening bar than the corporate repos (mlflow,
transformers, ray) that this operation already found hardened.

## Finding (submittable): DM reactions IDOR

`POST /api/dm/messages/{message_id}/reactions` → `toggle_dm_reaction`
(`backend/routers/social/dm.py`) fetches a `DirectMessage` by integer PK with **no
participant check**, then returns `DirectMessagePublic` (includes `content`). Any
authenticated user reads the plaintext of **every** private DM by enumerating the
sequential id, and writes reactions onto arbitrary messages. Registration is open by
default (`allow_new_registrations=True`).

- **Verified** by running the real `toggle_dm_reaction` against a temp SQLite DB with
  the real ORM models: attacker `eve` read `alice→bob` content and wrote her reaction.
- **Severity:** High, CVSS ~7.1 (`C:H/I:L`). Sibling friends IDOR (CVE-2026-0562) = 8.3.
- **Duplicate-checked:** no CVE/advisory covers this endpoint or DM read-IDOR.
  CVE-2026-12228 is a *write* XSS into DM content — different mechanism.
- **Contrast that proves oversight:** `bulk_delete_messages` (same file) applies
  `or_(sender==me, receiver==me)`; `get_dm_attachment` does a membership check. This
  endpoint does neither.

## What was checked and found hardened / safe

- **File-read path traversal** (the classic lollms class): `notebooks/assets.py`,
  `image_studio.py` (get_image_file), `files.py` (fun-facts) all use
  `secure_filename` + `.resolve()`/`is_relative_to` containment. `ui.py` has the
  CVE-2026-10595 fix. `social/dm.py get_dm_attachment` is fully guarded (secure_filename
  + containment + object-level authz). The file-read class looks largely closed now.
- **memories.py**: `_MemoryRecord` queries run inside a per-user memory manager
  (`get_user_memory_manager(username)`), so id lookups are naturally user-scoped — not
  an IDOR.
- **bulk_delete_messages / clean_conversation_history**: correct owner/member filters.

## Second sweep (done same session) — rest of the surface is hardened

Chased the obvious siblings for a second finding; the DM reactions IDOR is the lone gap:

- **Rest of `social/dm.py` is guarded.** `get_conversation_messages` enforces the
  member check even on the attacker-controlled `is_group=True` path and scopes the 1:1
  path by sender/receiver; `bulk_delete_messages`, `clean_conversation_history`,
  `delete_direct_message`, `mark_conversation_as_read`, `get_dm_attachment`,
  `add_member_to_group` all check membership/ownership. Only `toggle_dm_reaction` was
  missed — an isolated oversight, which strengthens the finding.
- **Classic resource routers scoped correctly:** `api_keys.py`, `notes.py`,
  `prompts.py`, `groups.py`, `discussion_groups.py` all filter get/put/delete-by-id by
  `owner_user_id == current_user.id` (or group owner/member). No IDOR.
- **SSRF class centralized + hardened:** `validate_url` + `safe_requests_get` in
  `backend.security`. `link-preview` (re-validates og:image too), `files.py
  _download_image_to_temp` (the CVE-2026-0560 fn, now `_validate_url`-gated), and
  `notebook ingestion pdf_url` all validate. `llm.py` street-view uses a hardcoded
  Google host (query param only, not SSRF). No SSRF sibling found.
- **File-read/social-media serving hardened everywhere:** `secure_filename` +
  `.resolve()`/`is_relative_to` containment; `social /media` adds visibility-based authz.

Not yet audited (lower probability, larger/awkward to PoC): `stores.py` [117 KB, RAG
datastore sharing], `image_studio.py`/`voices_studio.py` full endpoint set, `scim.py`,
`sso.py`, admin routers. Report any additional findings as **separate, individually-
verified** reports — never bundle or submission-farm.

## Environment
- `work/lollms-src` — clone (gitignored). `work/venv-lollms` — lean deps (no
  lollms-client/torch; that dep is stubbed in the PoC because the DM path never uses it).
- Run: `LOLLMS_SRC=… PYTHONPATH=… ./venv-lollms/bin/python poc_dm_reaction_idor.py`.

## Verdict
`drafting` → **awaiting_human_signoff**. First submittable finding since StackingDAO.
