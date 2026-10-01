#!/usr/bin/env python3
"""
Read-only invariant checks for deployed Clarity contracts.

Calls a contract's read-only functions through a public Stacks API node and
compares the results. It never signs or sends a transaction, holds no keys and
needs only the Python standard library.

Usage:
  clarity_check.py call SP000...ADDR.contract-name get-balance "'SP000...OWNER"
  clarity_check.py check invariants.json

Argument syntax (Clarity literals):
  u100          uint
  -5, 7         int
  true, false   bool
  none          none
  'SP...        standard principal
  'SP....name   contract principal
  "text"        string-ascii

Values that come back are decoded to plain Python (ints, bools, dicts, lists,
strings); (ok x) and (some x) unwrap to x, (err x) becomes {"err": x}.
"""
import argparse
import hashlib
import json
import operator
import os
import sys
import urllib.request

API = os.environ.get("STACKS_API", "https://api.hiro.so")
C32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


# ---------------------------------------------------------------- c32 addresses

def _c32_decode(s):
    n = 0
    for ch in s.upper():
        n = n * 32 + C32.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    lead = len(s) - len(s.lstrip("0"))
    return b"\x00" * lead + raw


def _c32_encode(b):
    n = int.from_bytes(b, "big")
    out = ""
    while n:
        n, r = divmod(n, 32)
        out = C32[r] + out
    lead = len(b) - len(b.lstrip(b"\x00"))
    return "0" * lead + out


def _checksum(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]


def address_to_parts(addr):
    """'SP2ZN...' -> (version, hash160 bytes). Verifies the checksum."""
    if addr[0] != "S":
        raise ValueError(f"not a Stacks address: {addr}")
    version = C32.index(addr[1])
    body = _c32_decode(addr[2:])
    body = body[-24:].rjust(24, b"\x00")
    h160, check = body[:20], body[20:]
    if _checksum(bytes([version]) + h160) != check:
        raise ValueError(f"bad checksum: {addr}")
    return version, h160


def parts_to_address(version, h160):
    body = h160 + _checksum(bytes([version]) + h160)
    enc = _c32_encode(body)
    # c32check keeps one leading '0' per leading zero byte of hash160.
    zeros = len(h160) - len(h160.lstrip(b"\x00"))
    enc = "0" * zeros + enc.lstrip("0")
    return "S" + C32[version] + enc


# ------------------------------------------------------------ Clarity encoding

def encode_arg(text):
    t = text.strip()
    if t in ("true", "false"):
        return bytes([0x03 if t == "true" else 0x04])
    if t == "none":
        return b"\x09"
    if t.startswith("u") and t[1:].isdigit():
        return b"\x01" + int(t[1:]).to_bytes(16, "big")
    if t.lstrip("-").isdigit():
        return b"\x00" + int(t).to_bytes(16, "big", signed=True)
    if t.startswith('"') and t.endswith('"'):
        b = t[1:-1].encode("ascii")
        return b"\x0d" + len(b).to_bytes(4, "big") + b
    if t.startswith("'"):
        addr, _, name = t[1:].partition(".")
        version, h160 = address_to_parts(addr)
        if not name:
            return b"\x05" + bytes([version]) + h160
        nb = name.encode("ascii")
        return b"\x06" + bytes([version]) + h160 + bytes([len(nb)]) + nb
    raise ValueError(f"unsupported argument literal: {text}")


def decode(buf, i=0):
    """Decode one serialized Clarity value from buf at i -> (value, next_i)."""
    t = buf[i]
    i += 1
    if t == 0x00:
        return int.from_bytes(buf[i:i + 16], "big", signed=True), i + 16
    if t == 0x01:
        return int.from_bytes(buf[i:i + 16], "big"), i + 16
    if t == 0x02:
        n = int.from_bytes(buf[i:i + 4], "big")
        return "0x" + buf[i + 4:i + 4 + n].hex(), i + 4 + n
    if t in (0x03, 0x04):
        return t == 0x03, i
    if t == 0x05:
        return parts_to_address(buf[i], buf[i + 1:i + 21]), i + 21
    if t == 0x06:
        addr = parts_to_address(buf[i], buf[i + 1:i + 21])
        n = buf[i + 21]
        return addr + "." + buf[i + 22:i + 22 + n].decode("ascii"), i + 22 + n
    if t in (0x07, 0x0a):  # ok, some
        return decode(buf, i)
    if t == 0x08:  # err
        v, i = decode(buf, i)
        return {"err": v}, i
    if t == 0x09:
        return None, i
    if t == 0x0b:
        n = int.from_bytes(buf[i:i + 4], "big")
        i += 4
        out = []
        for _ in range(n):
            v, i = decode(buf, i)
            out.append(v)
        return out, i
    if t == 0x0c:
        n = int.from_bytes(buf[i:i + 4], "big")
        i += 4
        out = {}
        for _ in range(n):
            k = buf[i + 1:i + 1 + buf[i]].decode("ascii")
            i += 1 + buf[i]
            out[k], i = decode(buf, i)
        return out, i
    if t in (0x0d, 0x0e):
        n = int.from_bytes(buf[i:i + 4], "big")
        return buf[i + 4:i + 4 + n].decode("utf-8"), i + 4 + n
    raise ValueError(f"unknown Clarity type 0x{t:02x}")


# ------------------------------------------------------------------- API calls

def call_read(contract, fn, args=(), sender=None):
    addr, name = contract.split(".", 1)
    body = json.dumps({
        "sender": sender or addr,
        "arguments": ["0x" + encode_arg(a).hex() for a in args],
    }).encode()
    req = urllib.request.Request(
        f"{API}/v2/contracts/call-read/{addr}/{name}/{fn}",
        data=body, headers={"content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        res = json.load(r)
    if not res.get("okay"):
        raise RuntimeError(f"{contract}::{fn} failed: {res.get('cause')}")
    value, _ = decode(bytes.fromhex(res["result"][2:]))
    return value


def resolve(spec):
    """A spec is a number, or {"call": "ADDR.name::fn", "args": [...], "path": "a.b"}."""
    if not isinstance(spec, dict):
        return spec
    contract, fn = spec["call"].split("::")
    v = call_read(contract, fn, spec.get("args", []))
    for key in filter(None, spec.get("path", "").split(".")):
        v = v[int(key)] if isinstance(v, list) else v[key]
    return v


OPS = {"<=": operator.le, "<": operator.lt, ">=": operator.ge,
       ">": operator.gt, "==": operator.eq, "!=": operator.ne}


def check(path):
    with open(path) as f:
        cfg = json.load(f)
    failed = 0
    for inv in cfg["invariants"]:
        lhs, rhs = resolve(inv["lhs"]), resolve(inv["rhs"])
        ok = OPS[inv["op"]](lhs, rhs)
        failed += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {inv['name']}: {lhs} {inv['op']} {rhs}")
    print(f"\n{len(cfg['invariants']) - failed} passed, {failed} failed")
    return 1 if failed else 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("call", help="call one read-only function")
    c.add_argument("contract")
    c.add_argument("fn")
    c.add_argument("args", nargs="*")
    k = sub.add_parser("check", help="evaluate invariants from a JSON file")
    k.add_argument("file")
    a = p.parse_args()
    if a.cmd == "call":
        print(json.dumps(call_read(a.contract, a.fn, a.args), indent=2))
        return 0
    return check(a.file)


if __name__ == "__main__":
    sys.exit(main())
