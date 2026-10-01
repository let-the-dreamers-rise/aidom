#!/usr/bin/env python3
"""
Rank scanner findings by exploit value.

A bug only pays if the contract holds / controls value. We can't read
on-chain balances (API blocked), so we approximate value with corpus
signals:

  inbound  - how many OTHER contracts reference this contract's principal
             (widely integrated => likely real TVL / many callers)
  named    - deployer owns a BNS name (names.txt) => more likely a real project
  sip      - contract is in sip10.txt / sip9.txt (recognized token)
  kw       - contract name contains a fund-holding keyword

Class weights: OWNER (takeover) and MINT (infinite mint) are rarer and
higher-signal than CUSTODY (noisy: every AMM/claim looks custodial).
"""
import json, os, re, sys
from collections import defaultdict, Counter

BASE = "/home/claude/boomcrypto/clarity-deployed-contracts"
CONTRACTS = os.path.join(BASE, "contracts")
SCAN = sys.argv[1] if len(sys.argv) > 1 else "scan_all.json"

findings = json.load(open(SCAN))

# ---- load corpus signals ----
named_deployers = set()
try:
    for line in open(os.path.join(BASE, "names.txt")):
        parts = line.strip().split()
        if parts:
            named_deployers.add(parts[0].split('.')[0])
except FileNotFoundError:
    pass

sip_contracts = set()
for fn in ("sip10.txt", "sip9.txt"):
    try:
        for line in open(os.path.join(BASE, fn)):
            sip_contracts.add(line.strip())
    except FileNotFoundError:
        pass

KW = re.compile(r'(pool|vault|stak|lend|borrow|bridge|treasury|grant|airdrop|claim|reward|farm|launch|sale|ico|ido|vest|lock|escrow|swap|dex|yield|deposit|withdraw|distributor|payout|fund)', re.I)

CLASS_W = {'OWNER': 100, 'MINT': 40, 'CUSTODY': 8}

def contract_id(relpath):
    # relpath like SPxxx/contract-name.clar
    d, f = os.path.split(relpath)
    return f"{d}.{f[:-5]}"  # SPxxx.contract-name

# We'll need inbound reference counts only for flagged contracts (cheaper).
flagged_ids = {}
for x in findings:
    cid = contract_id(x['file'])
    flagged_ids[cid] = x

# Build inbound-ref counts by one pass over the corpus, counting mentions of
# each flagged contract-name token ".<name>" (cheap approximation: match the
# contract short-name as a trait/contract reference).
# To keep it fast we grep for ".<shortname>" occurrences across all files.
shortnames = defaultdict(list)  # shortname -> list of cids using it
for cid in flagged_ids:
    short = cid.split('.', 1)[1]
    shortnames[short].append(cid)

inbound = Counter()
# single walk; for each file, find all ".token" references and bump matching shortnames
REF = re.compile(r'\.([a-zA-Z0-9\-\_]+)')
# limit: only count references to shortnames we care about
care = set(shortnames.keys())
for dirpath, _, files in os.walk(CONTRACTS):
    for fn in files:
        if not fn.endswith('.clar'):
            continue
        p = os.path.join(dirpath, fn)
        try:
            txt = open(p, errors='replace').read()
        except Exception:
            continue
        seen_here = set()
        for m in REF.finditer(txt):
            s = m.group(1)
            if s in care:
                seen_here.add(s)
        for s in seen_here:
            inbound[s] += 1

rows = []
for cid, x in flagged_ids.items():
    deployer = cid.split('.', 1)[0]
    short = cid.split('.', 1)[1]
    classes = set()
    fns = []
    for f in x['findings']:
        classes.update(f['classes'])
        fns.append(f['fn'] + '/' + ','.join(f['classes']))
    score = 0
    for c in classes:
        score += CLASS_W.get(c, 0)
    inb = inbound.get(short, 0) - 1  # subtract self-reference
    inb = max(inb, 0)
    score += min(inb, 50) * 3
    named = deployer in named_deployers
    if named:
        score += 20
    sip = cid in sip_contracts
    if sip:
        score += 30
    if KW.search(short):
        score += 10
    rows.append({
        'cid': cid, 'score': score, 'classes': sorted(classes),
        'inbound': inb, 'named': named, 'sip': sip,
        'kw': bool(KW.search(short)), 'fns': fns,
    })

rows.sort(key=lambda r: (-r['score'], -r['inbound']))
json.dump(rows, open('ranked.json', 'w'), indent=0)
print(f"ranked {len(rows)} flagged contracts")
print("\nTop 40 by score:")
for r in rows[:40]:
    print(f"{r['score']:5d} inb={r['inbound']:3d} {'N' if r['named'] else '.'}{'S' if r['sip'] else '.'}{'K' if r['kw'] else '.'} {r['cid']}  {r['fns'][:3]}")
