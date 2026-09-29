"""
Faithful port of Bitflow stableswap-stx-ststx-v-1-2 integer math.
Clarity semantics: unsigned ints, floor division, subtraction underflow ABORTS.
For stx/ststx both tokens are 6 decimals -> scaling is identity.
"""

class Abort(Exception):
    pass

def usub(a, b):
    if b > a:
        raise Abort(f"sub underflow {a}-{b}")
    return a - b

NTOK = 2
INDEX_MAX = 384

def get_D(x_bal, y_bal, ann, threshold=2):
    D = x_bal + y_bal
    converged = 0
    for _ in range(1, INDEX_MAX + 1):
        if converged != 0:
            break
        S = x_bal + y_bal
        dp = D
        # new_D_partial_x = D*dp/(2*x)
        dpx = (D * dp) // (2 * x_bal)
        dp2 = (D * dpx) // (2 * y_bal) if False else (D * dpx) // (2 * y_bal)
        num = (ann * S + NTOK * dp2) * D
        den = (ann - 1) * D + (NTOK + 1) * dp2
        newD = num // den
        if newD > D:
            if newD - D <= threshold:
                converged = newD
            D = newD
        else:
            if D - newD <= threshold:
                converged = newD
            D = newD
    return converged

def get_y(x_bal, y_bal, x_amount, ann, threshold=2):
    """Returns new y such that invariant holds. Mirrors contract get-y.
       NOTE contract computes current-D from (x_bal,y_bal) passed in, and
       x_bal_new = x_bal + x_amount."""
    x_bal_new = x_bal + x_amount
    D = get_D(x_bal, y_bal, ann, threshold)
    c0 = D
    c1 = (c0 * D) // (NTOK * x_bal_new)
    c2 = (c1 * D) // (ann * NTOK)
    b = x_bal_new + (D // ann)
    y = D
    converged = 0
    for _ in range(1, INDEX_MAX + 1):
        if converged != 0:
            break
        num = y * y + c2
        den = usub(2 * y + b, D)   # contract: (- (+ (* u2 y) b) D)
        newy = num // den
        if newy > y:
            if newy - y <= threshold:
                converged = newy
            y = newy
        else:
            if y - newy <= threshold:
                converged = newy
            y = newy
    return converged  # 0 if never converged

def swap_x_for_y(bx, by, x_amount, ann, fee_bps, threshold=2):
    """Model swap-x-for-y with identity scaling (6/6 decimals)."""
    total_fee = fee_bps
    fee = (x_amount * total_fee) // 10000
    updated_x = x_amount - fee
    updated_bx = bx + updated_x
    new_y = get_y(updated_bx, by, updated_x, ann, threshold)
    dy = usub(by, new_y)          # contract: (- current-balance-y new-y)
    return dy, updated_bx, new_y, fee

def get_D_correct(x, y, ann, threshold=2):
    return get_D(x, y, ann, threshold)

if __name__ == "__main__":
    # Realistic-ish balanced pool: 1,000,000 units each at 6 decimals
    U = 10**6
    bx = 1_000_000 * U
    by = 1_000_000 * U
    A = 100
    ann = A * NTOK
    D0 = get_D(bx, by, ann)
    print(f"Balanced pool bx={bx} by={by} A={A} ann={ann} D0={D0}")
    print(f"invariant check: D0 approx x+y = {bx+by}")

    for amt_units, label in [(1_000, "small 1k"), (100_000, "100k"),
                             (1_000_000, "1x balance"), (5_000_000, "5x"),
                             (9_999_999, "~10x")]:
        x_amount = amt_units * U
        try:
            dy, ubx, ny, fee = swap_x_for_y(bx, by, x_amount, ann, 0)  # non-admin fee=0
            D1 = get_D(ubx, ny, ann)
            print(f"\n[{label}] x_in={x_amount} fee=0")
            print(f"  dy(out)={dy}  new_y={ny}  D_before={D0} D_after={D1} dD={D1-D0}")
            if ny == 0:
                print(f"  *** get_y returned 0 -> DRAIN: dy=entire y balance ({by}) ***")
            # value check for stable pool (1:1): user paid x_amount, got dy
            print(f"  user paid {x_amount}, received {dy}, net(out-in)={dy - x_amount}")
        except Abort as e:
            print(f"\n[{label}] ABORT: {e}")
