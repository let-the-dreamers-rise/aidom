#!/usr/bin/env python3
"""Rank bounty targets by fit for a verification-first operation.

The score deliberately does NOT chase the biggest headline pool. A $5M cap
that a thousand researchers already comb is worth less to us than a $200k cap
on freshly changed code that few have looked at. So the score rewards:

  - a meaningful (but not necessarily maximal) payout ceiling,
  - freshly changed code (fewer eyes, more undiscovered surface),
  - lower competition,
  - zero upfront capital.

Usage:
    python3 rank.py                # ranks targets/targets.json
    python3 rank.py --json         # machine-readable output
    python3 rank.py path/to.json   # rank a different file
"""
import argparse
import json
import math
import sys
from pathlib import Path

COMPETITION_SCORE = {"low": 1.0, "medium": 0.6, "high": 0.3}

# Weights. Payout matters, but recency and low competition are what convert an
# AI's code-reading speed into an actual paid finding, so they carry real weight.
W_PAYOUT = 0.35
W_RECENCY = 0.30
W_COMPETITION = 0.25
W_CAPITAL = 0.10


def payout_component(usd: float) -> float:
    # Log-scaled and capped: going from $20k to $200k matters a lot; from $2M
    # to $5M barely moves the needle, because we are not going to out-grind the
    # crowd on the marquee programs anyway.
    if usd <= 0:
        return 0.0
    return min(1.0, math.log10(usd) / math.log10(500_000))


def recency_component(days: float) -> float:
    # Fresh code (<= 14 days) scores near 1; code untouched for a year scores
    # near 0. Fewer eyes on recently changed code is the core edge.
    if days is None:
        return 0.5
    return max(0.0, 1.0 - (days / 365.0))


def score_target(t: dict) -> float:
    payout = payout_component(t.get("max_payout_usd", 0))
    recency = recency_component(t.get("days_since_scope_change"))
    competition = COMPETITION_SCORE.get(t.get("competition", "medium"), 0.6)
    capital = 1.0 if not t.get("capital_required_usd") else 0.5
    return round(
        100
        * (
            W_PAYOUT * payout
            + W_RECENCY * recency
            + W_COMPETITION * competition
            + W_CAPITAL * capital
        ),
        1,
    )


def load(path: Path) -> list:
    data = json.loads(path.read_text())
    return data.get("targets", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=str(Path(__file__).with_name("targets.json")))
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"no such file: {path}", file=sys.stderr)
        return 1

    targets = load(path)
    ranked = sorted(targets, key=score_target, reverse=True)

    if args.json:
        print(json.dumps([{**t, "score": score_target(t)} for t in ranked], indent=2))
        return 0

    print(f"{'#':>2}  {'score':>5}  {'kind':<14} {'cap $':>10}  {'fresh':>5}  {'comp':<6} name")
    print("-" * 92)
    for i, t in enumerate(ranked, 1):
        days = t.get("days_since_scope_change")
        fresh = f"{days}d" if days is not None else "?"
        print(
            f"{i:>2}  {score_target(t):>5}  {t.get('kind',''):<14} "
            f"{t.get('max_payout_usd',0):>10,}  {fresh:>5}  "
            f"{t.get('competition',''):<6} {t.get('name','')}"
        )
    print()
    print("Score rewards fresh code + low competition + zero capital over headline pool size.")
    print("Re-verify every figure on the live scope page before starting a target.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
