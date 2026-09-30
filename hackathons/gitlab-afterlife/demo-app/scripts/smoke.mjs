// Post-deploy smoke test: checks the LIVE site, not the repo.
// Usage: node scripts/smoke.mjs <base url> <expected version>
const [base, expected] = process.argv.slice(2);
const get = async (path) => {
  for (let attempt = 1; ; attempt++) {
    const res = await fetch(new URL(path, base), { cache: "no-store" });
    if (res.ok || attempt === 10) return res;
    await new Promise((r) => setTimeout(r, 15000)); // Pages can lag a deploy
  }
};
const fail = (msg) => { console.error(`SMOKE FAIL: ${msg}`); process.exit(1); };

let health;
for (let attempt = 1; attempt <= 10; attempt++) {
  health = await (await get("health.json")).json();
  if (health.version === expected) break;
  await new Promise((r) => setTimeout(r, 15000));
}
if (health.version !== expected) fail(`live version ${health.version}, expected ${expected}`);

const config = await (await get("config.json")).json();
try { new Intl.NumberFormat("en-US", { style: "currency", currency: config.currency }); }
catch { fail(`config.json currency "${config.currency}" is not a valid ISO 4217 code`); }

const code = await (await get("split.js")).text();
const { split } = await import("data:text/javascript;base64," + Buffer.from(code).toString("base64"));
const shares = split(10000, 3, 15);
if (shares.reduce((a, b) => a + b, 0) !== 11500) fail(`live split() lost cents: ${shares}`);

console.log(`SMOKE OK: v${health.version} live at ${base}`);
