# Rosetta Quantum — Evidence Archive

The public, immutable record of Rosetta's verdicts. For each recipe (a
parametrized quantum algorithm) and problem class, this archive states whether
quantum beat the best classical solver, at what size, with reproducible
evidence. **The thesis is "show, don't claim"** — so this repo shows the raw
evidence instead of asking anyone to trust a number.

> Status (jul 2026): the protocol is live; entries are marked `is_demo: true`
> until the first real verdict replaces them. Nothing here is a measured result yet.

## How to verify anything here yourself

Every archive file is sealed with a SHA-256 hash and stored **byte-identical in
three places** — this repo (GitHub), a Codeberg mirror, and Rosetta's own
database — plus an external timestamp anchor nobody controls. To check that a
verdict hasn't been altered:

```bash
# 1. Recompute the hash of a file's content (over meta + w6, with content_hash null)
python3 - <<'PY'
import json, hashlib
doc = json.load(open("runs/2026/07/<file>.json"))
meta = dict(doc["meta"]); meta["content_hash"] = None
payload = {"meta": meta, "w6": doc["w6"]}
h = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",",":")).encode()).hexdigest()
print("recomputed:", h)
print("sealed    :", doc["meta"]["content_hash"])
print("MATCH" if h == doc["meta"]["content_hash"] else "TAMPERED")
PY
```

```bash
# 2. Confirm the Codeberg mirror is identical
diff <(curl -s <github raw_url>) <(curl -s <codeberg raw_url>)   # no output = identical
```

If the recomputed hash matches, the three copies agree, and the OpenTimestamps
proof (`.ots`) verifies, the verdict is exactly as first published. If any check
fails, that copy is invalid — and because the files are immutable (corrections
are new, chained files, never edits), git history exposes any change.

## What each file contains

Each archive answers six questions — **what** ran, **how** (seeds, versions,
protocol), **when**, **where** it computed, **why** (the hypothesis under test),
and **who**. Naming: `RosettaQ__<TYPE>__<ID>__<DATE-UTC>__<context>.json`. Layout:
`runs/<year>/<month>/`, `verdicts/<year>/`, `recipes/`.

## Honesty rules (non-negotiable)

- `is_demo: true` on every file until a real run exists — no illustrative result
  is ever presented as measured.
- Immutable: published = sealed. Corrections are new files that reference the old
  one, never edits.
- The classical champion is always the strongest available solver (a weak
  baseline invalidates the whole archive).
- Negative results get published. "Quantum doesn't beat classical here yet" is
  the product, not a failure.

## Reading & reuse

Evidence data is licensed **CC BY 4.0** (see `LICENSE-evidence.md`) — reuse it
freely, just attribute Rosetta Quantum. This repo is read-only for the world:
open an issue if you find an error (that's the free-QA loop we want), but the
verdicts themselves are sealed.

Full protocol: see the archive spec. Live ledger: https://rosettaquantum.com/ledger.html
