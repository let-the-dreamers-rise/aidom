// Splitly core: split a bill between people, rounding to cents so the shares
// always add back up to the exact total.
export function split(totalCents, people, tipPercent = 0) {
  if (!Number.isInteger(totalCents) || totalCents < 0) throw new Error("totalCents must be a non-negative integer");
  if (!Number.isInteger(people) || people < 1) throw new Error("people must be a positive integer");
  const withTip = Math.round(totalCents * (1 + tipPercent / 100));
  const base = Math.floor(withTip / people);
  const remainder = withTip - base * people;
  return Array.from({ length: people }, (_, i) => base + (i < remainder ? 1 : 0));
}

export function formatCents(cents, currency = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(cents / 100);
}
