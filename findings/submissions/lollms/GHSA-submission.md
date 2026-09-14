# lollms — GitHub Security Advisory (ready to file)

**How to file (2 minutes, your GitHub account):**
1. Go to **https://github.com/parisneo/lollms/security/advisories/new** (you must be signed in).
   - If that 404s (advisories not enabled on the repo), instead email the maintainer:
     open `SECURITY.md` in the repo for the address, or use `security@` / the maintainer's
     contact, and paste the **Description** block below.
2. Fill each field from the sections below (they map 1:1 to GitHub's advisory form).
3. Under **Credits**, add your own GitHub username.
4. Submit as a **draft advisory** (private). Do NOT open a public issue/PR.

> Rewrite is optional here — GitHub advisories aren't auto-rejected for AI text the way
> huntr is — but a couple of edits in your own words never hurt.

---

## Field: Title
Unauthenticated-adjacent IDOR: any registered user can read every private direct message via `POST /api/dm/messages/{message_id}/reactions`

## Field: Ecosystem / Package
- **Ecosystem:** pip (PyPI)
- **Package name:** `lollms`
- **Affected versions:** `<=` latest release (reproduced on `main` @ commit `a744154`, 2026-09-14; `APP_VERSION` reads `2.1.0`). The vulnerable endpoint exists in all versions that ship the direct-message feature.
- **Patched versions:** none yet.

## Field: Severity (CVSS v3.1)
- **Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N`
- **Score:** 7.1 (High)
- Rationale: confidentiality of *all* users' private messages (C:H); secondary integrity via forged reactions on any message (I:L); requires a low-privilege account (PR:L), and self-registration is enabled by default (`ALLOW_NEW_REGISTRATIONS` defaults to `True`), so in the default configuration any anonymous person can obtain that account.

## Field: Weakness (CWE)
- **CWE-639** — Authorization Bypass Through User-Controlled Key (IDOR)
- (also **CWE-284** — Improper Access Control)

## Field: Description

### Summary
`toggle_dm_reaction` in `backend/routers/social/dm.py` looks up a direct message by its
integer primary key and performs **no check** that the caller is the sender, the receiver,
or a member of the conversation. It then returns the full message object
(`DirectMessagePublic`, which includes `content`). Any authenticated user can therefore
read the plaintext of **any** private direct message on the server — 1:1 DMs and group
messages they are not part of — by enumerating the sequential `message_id`, and can
additionally write a reaction onto any message. Registration is open by default, so an
attacker only needs to self-register.

### Affected endpoint
`POST /api/dm/messages/{message_id}/reactions` → `toggle_dm_reaction`
(`backend/routers/social/dm.py`), auth dependency `get_current_active_user` (any active user).

### Steps to reproduce
Roles: **alice** and **bob** (victims, exchange a private DM); **eve** (attacker, a normal account, not a party to that DM).
1. As **eve**, register (`POST /api/auth/register`) and log in for a bearer token.
2. alice sends bob a private DM. Its `message_id` is a small sequential integer.
3. As **eve**, call:
   ```
   POST /api/dm/messages/1/reactions
   Authorization: Bearer <eve_token>
   Content-Type: application/json

   {"emoji": "🔥"}
   ```
4. **Expected:** `403 Forbidden`. **Actual:** `200 OK` with the full message body — `content`, `sender_username`, `receiver_username`, `media`, `image_references`, `reply_to_content` — and eve's id is now persisted in that message's `reactions`.

Iterating `message_id` over the integer range dumps the content of every direct message on the instance.

### Proof of concept
A self-contained PoC that runs the real `toggle_dm_reaction` against a throwaway SQLite DB
using the project's real ORM models (attacker `eve` reads `alice→bob` content and writes a
reaction) is available on request. Observed output:
```
content : 'PRIVATE: my bank OTP is 738114 and my SSN is 555-01-2029'
reactions: {'🔥': [3]}          # 3 == eve's user id
READ-IDOR CONFIRMED / WRITE-IDOR CONFIRMED
```

### The vulnerable code
```python
@dm_router.post("/messages/{message_id}/reactions", response_model=DirectMessagePublic)
async def toggle_dm_reaction(message_id: int, payload: MessageReactionRequest,
                             current_user: UserAuthDetails = Depends(get_current_active_user),
                             db: Session = Depends(get_db)):
    msg = db.query(DBDirectMessage).filter(DBDirectMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    # <-- NO check that current_user is sender / receiver / conversation member -->
    ...
    resp = _map_direct_message_public(msg, db)   # returns content, sender, media, ...
    ...
    return resp
```
For contrast, the neighbouring `bulk_delete_messages` (same file) *does* filter
`or_(sender_id == current_user.id, receiver_id == current_user.id)`, and `get_dm_attachment`
performs an explicit membership check — so the omission here is an oversight, not a design choice.

### Impact
Complete disclosure of all users' private direct-message content to any single
low-privileged account (reachable by anyone on an instance with the default open
registration), plus the ability to forge reactions on arbitrary messages.

### Remediation
Enforce object-level authorization before reading or mutating the message — mirror the
check already used by `get_dm_attachment` / `bulk_delete_messages`:
```python
msg = db.query(DBDirectMessage).filter(DBDirectMessage.id == message_id).first()
if not msg:
    raise HTTPException(status_code=404, detail="Message not found")

is_party = current_user.id in (msg.sender_id, msg.receiver_id)
if not is_party and msg.conversation_id:
    is_party = db.query(DBConversationMember).filter_by(
        conversation_id=msg.conversation_id, user_id=current_user.id).first() is not None
if not is_party:
    raise HTTPException(status_code=404, detail="Message not found")  # 404 avoids an id oracle
```
Apply the same participant check to every DM endpoint that resolves a message/conversation
by id (a repo-wide audit of `social/dm.py` is warranted — this is the second IDOR in the
social subsystem after CVE-2026-0562).

## Field: Credits
- `<your GitHub username>` — Reporter / Analysis
