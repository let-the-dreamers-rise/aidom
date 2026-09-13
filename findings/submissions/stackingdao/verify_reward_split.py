#!/usr/bin/env python3
"""
Reproduces the finding read-only against Stacks mainnet (no wallet, no funds,
no local toolchain). Requires only python3 and curl.

  python3 verify_reward_split.py

It (1) reads the live split parameters from rewards-pox5-v1 and shows the
stBTC remainder is zero, (2) replays process-rewards' integer arithmetic on
the release amounts observed on-chain, and (3) sums every sBTC transfer the
reward contract has ever made, by destination, from the public Hiro API.
"""
import json, subprocess, collections

DEPLOYER = "SP4SZE494VC2YC5JYG7AYFQ44F5Q4PYV7DVMDPBG"
API = "https://api.hiro.so"

def call_read(contract, fn):
    out = subprocess.run(
        ["curl", "-sS", "--max-time", "40", "-X", "POST",
         f"{API}/v2/contracts/call-read/{DEPLOYER}/{contract}/{fn}",
         "-H", "content-type: application/json",
         "-d", json.dumps({"sender": DEPLOYER, "arguments": []})],
        capture_output=True, text=True).stdout
    h = json.loads(out)["result"][2:]
    if h.startswith("07"): h = h[2:]          # unwrap (ok ...)
    assert h.startswith("01"), h              # uint
    return int(h[2:], 16)

DENOM = 10_000
btc_bps = call_read("rewards-pox5-v1", "get-ststxbtc-bps")
stx_bps = call_read("rewards-pox5-v1", "get-ststx-bps")
print("== 1. live split parameters (rewards-pox5-v1) ==")
print(f"ststxbtc-bps = {btc_bps}\nststx-bps    = {stx_bps}\nsum          = {btc_bps + stx_bps}")
print(f"stBTC share  = {DENOM - (btc_bps + stx_bps)} bps  (process-rewards routes the remainder to stbtc-reserve)\n")

print("== 2. process-rewards arithmetic on release amounts seen in recent events ==")
for rel in (26335, 53380, 78894, 105996, 133320, 160596):
    a = rel * btc_bps // DENOM
    b = rel * stx_bps // DENOM
    print(f"release {rel:>7} sats -> ststxbtc {a:>7}, ststx {b:>7}, stBTC remainder {rel - (a + b)}")
print()

print("== 3. lifetime sBTC flows of rewards-pox5-v1 (Hiro API) ==")
inflow, outflow, n, off = collections.Counter(), collections.Counter(), 0, 0
while True:
    out = subprocess.run(
        ["curl", "-sS", "--max-time", "60",
         f"{API}/extended/v1/address/{DEPLOYER}.rewards-pox5-v1/transactions_with_transfers?limit=50&offset={off}"],
        capture_output=True, text=True).stdout
    res = json.loads(out).get("results", [])
    if not res: break
    for t in res:
        n += 1
        for ft in t.get("ft_transfers", []):
            s, r, amt = ft.get("sender") or "", ft.get("recipient") or "", int(ft["amount"])
            k = lambda p: p.split(".")[-1] if "." in p else p
            if "rewards-pox5-v1" in r: inflow[k(s)] += amt
            elif "rewards-pox5-v1" in s: outflow[k(r)] += amt
    off += 50
tot_out = sum(outflow.values())
print(f"transactions scanned: {n}")
print("inflow (reward sources):")
for k, v in inflow.most_common(): print(f"  {k:<36} {v:>13,} sats")
print("outflow (distribution):")
for k, v in outflow.most_common():
    print(f"  {k:<36} {v:>13,} sats  {100*v/tot_out:6.3f}%")
print(f"\nstBTC pool: supply {call_read('stbtc-token','get-total-supply'):,} sats, "
      f"bonded in PoX-5 {call_read('stbtc-reserve','get-sbtc-staking'):,} sats")
