import { test } from "node:test";
import assert from "node:assert/strict";
import { split, formatCents } from "../public/split.js";

test("shares add up to the total including tip", () => {
  const shares = split(10000, 3, 15);
  assert.equal(shares.reduce((a, b) => a + b, 0), 11500);
  assert.deepEqual(shares, [3834, 3833, 3833]);
});

test("rejects bad input", () => {
  assert.throws(() => split(-1, 2));
  assert.throws(() => split(100, 0));
});

test("formats cents", () => {
  assert.equal(formatCents(123456), "$1,234.56");
});
