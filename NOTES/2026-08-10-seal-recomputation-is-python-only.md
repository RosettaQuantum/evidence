# Correction note — the seal can only be recomputed in Python (today)

**Dated:** 2026-08-10 · **Affects:** every sealed file in this archive · **Severity:** the
central promise of this archive is weaker than stated
**Found by:** the session that owns the public API, while writing a copy-paste quick start
for `/api-docs` — not by an audit of the archive itself.

## What we promise

Every response from our API, and `PROTOCOL.md` itself, tells a third party: download the
sealed file and recompute `content_hash` yourself. That promise is the product. It is what
distinguishes a measurement you can check from a number you must believe.

## What is actually true

**The recomputation only reproduces our hash in Python**, or in a verifier that never
re-serialises the parsed JSON.

The seal is computed over a *text*: `json.dumps(..., sort_keys=True, ensure_ascii=False)`.
Different languages serialise the same number differently. Python writes a float `8.0` as
`8.0`; JavaScript's `JSON.stringify` writes the same value as `8`. Go, Rust and most other
runtimes agree with JavaScript, not with Python.

Concretely, inside `PR-CLEV-001`:

```
python  ..., "contact_cutoffs_A": [7.5, 8.0, 8.5, 9.0, ...
js      ..., "contact_cutoffs_A": [7.5, 8, 8.5, 9, ...
```

One character of difference is a completely different sha256. **64 of the 69 sealed files
in this archive contain at least one such literal.**

So a reviewer who parses our JSON in Go, Rust or JavaScript and re-serialises it to check
the hash gets a mismatch — and gets it **silently**, with no error, looking exactly like
evidence of tampering. That is the worst possible failure mode for an integrity check: it
accuses an honest archive.

## What we are not doing

**We are not changing a single sealed file.** They are anchored in Bitcoin and published
in three places; published is published, and corrections are new files, never edits. The
hashes in this archive remain exactly what they were.

## What a verifier must do today

Either verify in Python with the reference implementation
([`tools/verify_seals.py`](../tools/verify_seals.py)), or — in any other language — use a
JSON parser that **preserves numeric literals as written** and does not re-serialise them.
The API session implemented exactly such a parser in JavaScript to prove the point: with
literal preservation the seal of `PR-CLEV-001` reproduces; without it, it does not.

## What changes going forward

New seals should be defined over a canonicalisation that every language agrees on —
RFC 8785 (JSON Canonicalization Scheme) is the standard answer, and its number rules are
exactly ECMAScript's, so a JCS verifier in any language reproduces the same bytes. That is
a **new seal version**, not a rewrite of the old ones: both conventions will coexist and
the verifier will keep declaring which one each file used, as it already does for v1 and v2.

That decision is not taken in this note. What this note does is stop us from claiming, for
one more day, a portability the convention does not have.

## Why this note exists

Because the rule of this project is that what you promise can be checked, you check
yourself, first — and we had not. We published a verification recipe, exercised it in
Python, and concluded it worked. It did work; it just did not work *anywhere else*, and
nobody had tried anywhere else until someone wrote a quick start for people who are not us.

The defect was in the convention, not in any measurement. Every scientific result in this
archive stands. What was overstated is how many people could check it.
