# Clarity Security Commons

Free, open-source security resources for Clarity DeFi on Stacks.

- [`CHECKLIST.md`](CHECKLIST.md): ten bug classes found while reviewing the
  deployed contracts of ten Stacks DeFi protocols, each with an unsafe and a
  safer Clarity pattern and the question to ask in review.
- [`verifier/`](verifier/): a dependency-free Python tool that calls a
  deployed contract's read-only functions through a public Stacks API node and
  checks invariants you write in JSON. It never signs or sends a transaction.

## Verifier quick start

```sh
cd verifier
python3 -m unittest test_clarity_check          # offline encoding tests
python3 clarity_check.py call SP...ADDR.contract get-total-supply
python3 clarity_check.py check example-invariants.json
```

Set `STACKS_API` to use a node other than `https://api.hiro.so`.

## Free pre-launch reviews

Building on Stacks and haven't had an audit yet? Open an issue titled
"Review request" with a link to your contracts. Findings go to you privately
first; nothing is published without your consent.

## License

MIT
