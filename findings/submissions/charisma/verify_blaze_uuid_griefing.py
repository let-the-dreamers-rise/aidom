#!/usr/bin/env python3
"""
Read-only, wallet-free verification of the blaze-v1 UUID-griefing finding against
Stacks mainnet. python3 + curl only; public read-only API calls, no transaction,
no funds, no exploitation.

It confirms the three structural facts the finding rests on:

  1. blaze-v1 is deployed at the stated principal.
  2. Its replay map `submitted-uuids` is declared `(string-ascii 36) -> bool` —
     the key is the UUID string ALONE (no signer, no contract), so two unrelated
     intents that merely share a UUID collide in one global namespace.
  3. `execute` consumes the UUID with `map-insert` BEFORE (and independently of)
     any signer-specific check; the signer is folded into the signed HASH but not
     into the replay KEY.

It then calls the public read-only `check(uuid)` to show the map is live and
shared: a well-known all-zero UUID reads back its current state for anyone. No
UUID is consumed here — the actual griefing step (a direct `execute` call reusing
a victim's UUID) is described in the report, never executed.
"""
import json, re, subprocess

DEP = "SP2ZNGJ85ENDY6QRHQ5P2D4FXKGZWCKTB2T0Z55KS"
API = "https://api.hiro.so"
NAME = "blaze-v1"


def curl(url, data=None):
    cmd = ["curl", "-sS", "--max-time", "40", url]
    if data is not None:
        cmd += ["-X", "POST", "-H", "content-type: application/json", "-d", json.dumps(data)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def clv_string_ascii(s):
    # Clarity value hex for (string-ascii): type 0x0d, 4-byte len, ascii bytes
    b = s.encode("ascii")
    return "0x0d" + f"{len(b):08x}" + b.hex()


def main():
    src = json.loads(curl(f"{API}/v2/contracts/source/{DEP}/{NAME}")).get("source", "")
    print(f"[1] blaze-v1 deployed at {DEP}.{NAME}: {'YES' if src else 'NO'} ({len(src)} chars)\n")
    if not src:
        print("    could not fetch source; aborting."); return

    # 2. replay map keyed on the UUID alone
    m = re.search(r"\(define-map\s+submitted-uuids\s+(.+?)\s+bool\s*\)", src, re.S)
    key = " ".join(m.group(1).split()) if m else "<not found>"
    keyed_on_uuid_only = m is not None and "string-ascii 36" in key and "{" not in key
    print(f"[2] replay map key type: {key}")
    print(f"    keyed on UUID string ALONE (no signer / no contract in key): "
          f"{'YES  <-- collision surface' if keyed_on_uuid_only else 'no'}\n")

    # 3. execute inserts the uuid before/independent of signer identity
    ex = re.search(r"\(define-public\s+\(execute.*?\n\s*\(if\s+\(map-insert\s+submitted-uuids\s+uuid",
                   src, re.S)
    print(f"[3] execute consumes UUID via map-insert as its first action, "
          f"signer only inside the hash: {'YES' if ex else 'no'}")
    print(f"    => any account can insert a victim's UUID by self-signing its own "
          f"intent that reuses it.\n")

    # live proof the map is public + shared
    zero_uuid = "00000000-0000-0000-0000-000000000000"
    res = json.loads(curl(f"{API}/v2/contracts/call-read/{DEP}/{NAME}/check",
                          {"sender": DEP, "arguments": [clv_string_ascii(zero_uuid)]}))
    raw = res.get("result", "")
    consumed = raw.endswith("03")  # 0x03 = Clarity bool true
    print(f"[4] public check(\"{zero_uuid}\") -> raw {raw} "
          f"(consumed={consumed}); the map is live and readable by anyone,")
    print(f"    and the same global namespace backs every subnet built on blaze-v1.\n")

    ok = keyed_on_uuid_only and ex is not None
    print("RESULT:", "confirmed — UUID replay key is signer-independent and global; "
          "pre-consumption griefing is reachable (Low, DoS, no theft)."
          if ok else "structural facts not confirmed; re-check source.")


if __name__ == "__main__":
    main()
