#!/usr/bin/env python3
"""
Read-only, wallet-free verification of the `ststxbtc-tracking-v2` reward-freeze
griefing finding against Stacks mainnet. python3 + curl only; public read-only
API calls, no mainnet transaction, no funds.

For each deactivated stSTXbtc position it reads the frozen checkpoint
`deactivated-cumm-reward` (D) and the current global `cumm-reward` (G). The
UNGATED `save-pending-rewards` resets a griefed holder's checkpoint to G (via
`update-holder-position`); a later `get-pending-rewards` on the deactivated
position then computes `(- D G)` with D < G -> uint underflow -> aborts
`claim-pending-rewards`, permanently freezing that holder's rewards. Anyone can
trigger it for any holder in one transaction.
"""
import json, subprocess

DEP  = "SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG"
API  = "https://api.hiro.so"
DATA = "ststxbtc-tracking-data-v2"
POSITIONS = ["position-zest-v3","position-zest-v4","position-zest-v5","position-zest-v6"]
C32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

def c32decode(a):
    # Stacks c32check: version is the first char after 'S'; the remainder
    # base32-decodes to hash160(20) + checksum(4).
    version=C32.index(a[1])
    acc=0
    for ch in a[2:]: acc=acc*32+C32.index(ch)
    raw=acc.to_bytes((acc.bit_length()+7)//8,"big").rjust(24,b"\x00")[-24:]
    return version, raw[:20]

def principal_cv(addr,name):
    ver,h=c32decode(addr); nb=name.encode()
    return "06"+f"{ver:02x}"+h.hex()+f"{len(nb):02x}"+nb.hex()

def call_read(contract,fn,args):
    out=subprocess.run(["curl","-sS","--max-time","40","-X","POST",
        f"{API}/v2/contracts/call-read/{DEP}/{contract}/{fn}",
        "-H","content-type: application/json",
        "-d",json.dumps({"sender":DEP,"arguments":args})],capture_output=True,text=True).stdout
    return json.loads(out)

class P:
    def __init__(s,h): s.h=h; s.i=0
    def rb(s,n): v=s.h[s.i:s.i+n*2]; s.i+=n*2; return v
    def b1(s): return int(s.rb(1),16)
    def val(s):
        t=s.b1()
        if t==0x01: return int(s.rb(16),16)        # uint
        if t==0x00: return -int(s.rb(16),16)       # int
        if t==0x03: return True                    # bool true
        if t==0x04: return False                   # bool false
        if t==0x05: s.rb(21); return "principal"   # standard principal
        if t==0x06:                                 # contract principal
            s.rb(21); ln=s.b1(); s.rb(ln); return "contract"
        if t==0x0a: return s.val()                 # optional some
        if t==0x09: return None                    # optional none
        if t==0x0c:                                 # tuple
            n=int(s.rb(4),16); d={}
            for _ in range(n):
                ln=s.b1(); name=bytes.fromhex(s.rb(ln)).decode(); d[name]=s.val()
            return d
        raise ValueError(f"unhandled type 0x{t:02x} at {s.i}")

def unwrap(res):
    h=res[2:] if res.startswith("0x") else res
    p=P(h); t=p.b1()
    if t==0x07: return p.val()   # (ok ...)
    p.i=0; return p.val()

G=unwrap(call_read(DATA,"get-cumm-reward",[])["result"])
print(f"global cumm-reward  G = {G:,}\n")
hdr=f"{'position':18}{'active':9}{'D (deactivated)':18}{'G > D ?':10}underflow-reachable"
print(hdr); print("-"*len(hdr))
for name in POSITIONS:
    r=call_read(DATA,"get-supported-positions",["0x"+principal_cv(DEP,name)])
    tup=unwrap(r["result"])
    active=tup.get("active"); D=tup.get("deactivated-cumm-reward")
    reach = (not active) and isinstance(D,int) and D>0 and G>D
    print(f"{name:18}{str(active):9}{str(D):18}{str(isinstance(D,int) and G>D):10}{'YES' if reach else 'no (active/empty)'}")
print("\nAny 'YES' row: an unclaimed holder of that deactivated position can be")
print("permanently frozen by anyone calling save-pending-rewards(holder,position).")
