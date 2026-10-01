#!/usr/bin/env python3
"""
Static scanner for deployed Clarity contracts.

Goal: find PUBLIC functions that reach a value-moving sink
(token/NFT mint, custodial as-contract transfer, or owner/admin
reassignment) with NO authorization guard on the function or on any
private helper it transitively calls.

This is a heuristic triage tool, not a prover. It is tuned for high
recall on the three bug classes below and then relies on human review
of the (small) survivor set. False positives are expected and fine;
the point is to cut 121k contracts down to a hand-auditable list.

Bug classes:
  MINT   - public fn calls (ft-mint? / nft-mint?) unguarded  -> infinite mint
  CUSTODY- public fn does (as-contract ... transfer ...) unguarded -> drain
  OWNER  - public fn does (var-set <*owner*/*admin*> ...) unguarded -> takeover
"""
import os, re, sys, json

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/boomcrypto/clarity-deployed-contracts/contracts"

# ---- tokenizer-ish helpers over Clarity s-expressions -----------------------

def strip_comments_and_strings(src):
    """Remove ;; comments and string/buff literals so parens balance cleanly."""
    out = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == ';' and i+1 < n and src[i+1] == ';':
            # line comment
            while i < n and src[i] != '\n':
                i += 1
            continue
        if c == '"':
            out.append(' ')
            i += 1
            while i < n and src[i] != '"':
                if src[i] == '\\':
                    i += 1
                i += 1
            i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)

def top_level_forms(src):
    """Yield (start,end) spans of each top-level (...) form at depth 0."""
    depth = 0
    start = None
    for i, c in enumerate(src):
        if c == '(':
            if depth == 0:
                start = i
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0 and start is not None:
                yield (start, i+1)
                start = None

DEF_RE = re.compile(r'^\(\s*(define-public|define-private|define-read-only)\s+\(\s*([a-zA-Z0-9\-\_\?\!]+)')

def parse_functions(src):
    """Return dict name -> {'kind','body'} for all defined functions."""
    funcs = {}
    for (s, e) in top_level_forms(src):
        form = src[s:e]
        m = DEF_RE.match(form)
        if m:
            kind = m.group(1)
            name = m.group(2)
            funcs[name] = {'kind': kind, 'body': form}
    return funcs

# ---- sinks and guards -------------------------------------------------------

MINT_RE    = re.compile(r'\b(ft-mint\?|nft-mint\?)\b')
TRANSFER_RE= re.compile(r'\b(ft-transfer\?|nft-transfer\?|stx-transfer\?|stx-transfer-memo\?|transfer-fixed|transfer\b)')
ASCONTRACT_RE = re.compile(r'\bas-contract\b')
VARSET_RE  = re.compile(r'\(\s*var-set\s+([a-zA-Z0-9\-\_\?\!]+)')

# guard signals: presence of any of these in reachable body => considered guarded
GUARD_TOKENS = [
    r'\bis-eq\s+tx-sender\b',
    r'\bis-eq\s+contract-caller\b',
    r'\btx-sender\b[^)]*\bcontract-owner\b',
    r'\bcontract-owner\b',
    r'\bis-owner\b', r'\bonly-owner\b', r'\bassert-owner\b',
    r'\bis-dao\b', r'\bis-extension\b', r'\bis-dao-or-extension\b',
    r'\bis-admin\b', r'\bis-authoriz', r'\bcheck-is-', r'\bcheck-caller',
    r'\bcheck-owner\b', r'\bis-contract-owner\b', r'\bverify-',
    r'\bhas-role\b', r'\bis-approved\b', r'\bis-whitelisted\b',
    r'\bassert-is-', r'\bonly-',
]
GUARD_RE = re.compile('|'.join(GUARD_TOKENS))

# names that look like local calls we should follow for guards/sinks
CALL_RE = re.compile(r'\(\s*([a-zA-Z][a-zA-Z0-9\-\_\?\!]*)')

def reachable_text(fname, funcs, seen=None, depth=0):
    """Concatenate body of fname plus bodies of locally-defined functions it calls (transitive)."""
    if seen is None:
        seen = set()
    if fname in seen or depth > 6:
        return ''
    seen.add(fname)
    f = funcs.get(fname)
    if not f:
        return ''
    text = f['body']
    acc = [text]
    for m in CALL_RE.finditer(text):
        callee = m.group(1)
        if callee in funcs and callee != fname and callee not in seen:
            acc.append(reachable_text(callee, funcs, seen, depth+1))
    return '\n'.join(acc)

def analyze_file(path):
    try:
        raw = open(path, 'r', errors='replace').read()
    except Exception:
        return []
    src = strip_comments_and_strings(raw)
    funcs = parse_functions(src)
    findings = []
    for name, f in funcs.items():
        if f['kind'] != 'define-public':
            continue
        body = f['body']
        # own-body sink detection (sinks must appear in the public fn itself or helpers)
        rtext = reachable_text(name, funcs)
        guarded = bool(GUARD_RE.search(rtext))
        classes = []
        # MINT: mint primitive in reachable text
        if MINT_RE.search(rtext):
            classes.append('MINT')
        # CUSTODY: as-contract AND a transfer in the same reachable text
        if ASCONTRACT_RE.search(rtext) and TRANSFER_RE.search(rtext):
            classes.append('CUSTODY')
        # OWNER: var-set to an owner/admin-ish var in reachable text
        for mm in VARSET_RE.finditer(rtext):
            vn = mm.group(1).lower()
            if 'owner' in vn or 'admin' in vn:
                classes.append('OWNER')
                break
        if classes and not guarded:
            findings.append({'fn': name, 'classes': classes})
    return findings

def main():
    out = []
    nfiles = 0
    for dirpath, _, files in os.walk(ROOT):
        for fn in files:
            if not fn.endswith('.clar'):
                continue
            nfiles += 1
            p = os.path.join(dirpath, fn)
            fs = analyze_file(p)
            if fs:
                rel = os.path.relpath(p, ROOT)
                out.append({'file': rel, 'findings': fs})
    sys.stderr.write(f"scanned {nfiles} files; {len(out)} flagged\n")
    json.dump(out, sys.stdout)

if __name__ == '__main__':
    main()
