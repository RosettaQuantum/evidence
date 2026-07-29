# Rosetta Quantum — Archive Protocol

How every sealed file in this repository is produced, verified, and published. Written so
that a third party can audit the archive without trusting us — and so that a future
maintainer can reproduce the process exactly.

*(Internal operational memory — infrastructure, credentials, roadmap — is kept privately.
This document is the part that belongs in the open: the rules the evidence must satisfy.)*

---

## 1. What is in this archive

| Type | ID pattern | What it records |
|---|---|---|
| `RECIPE` | `RQ-XXXX` | A quantum algorithm harvested from the literature, framed as a problem class |
| `RUN` | `EXP-<recipe>-<nnn>` | One fight: the same instance solved by a quantum recipe and by the classical champion |
| `VERDICT` | `V-<recipe>` | A dated judgment over a series of runs |
| `PREREG` | `PR-<track>-<nnn>` | A forward commitment sealed *before* the runs exist |

File naming: `RosettaQ__<TYPE>__<ID>__<UTC-DATE>__<context>.json`, e.g.
`RosettaQ__RUN__EXP-0007-015__20260725T1543Z__ctqw-vs-clasicos--allosteria-miosina-cardiaca.json`.
(Deliberately not using an `EXP-0033-*` filename as the example: six of those are
mislabeled and the correction is pending — see `NOTES/2026-07-29-eon-scale-errata.md`.)
Each file has a sibling `.ots` timestamp proof.

## 2. The w6 structure

Every archive answers six questions under the `w6` key: **que** (what ran — recipe, class,
quantum side, classical side, exact optimum, outcome, gaps) · **como** (protocol, seed,
instance parameters, frozen library versions, harness, compute) · **cuando** (started_at /
archived_at / published_at) · **donde** (backends, region) · **porque** (hypothesis,
question, ledger goal) · **quien** (operator, agents, judge protocol version, org).

Plus `meta` (schema, file name, id, type, `is_demo`, `content_hash`) and `storage` (where
each of the three copies lives).

## 3. The seal

Schema tag: `rosettaq-archive/v1`.

**Canonical convention — use this for every new seal:**

```
content_hash = sha256( json.dumps({"meta": meta_without_content_hash, <body>},
                                  sort_keys=True, ensure_ascii=False) )
```

where `<body>` is every top-level key except `meta` and `storage`. `storage` is excluded on
purpose: it describes where a copy lives, not what it says.

**Legacy convention — historical, do not use for new seals:**

```
sha256( json.dumps({"meta": {**meta, "content_hash": None}, "w6": w6},
                   sort_keys=True, separators=(",",":")) )
```

**Why both exist, stated plainly.** The portfolio (`EXP-0012-*`) and grid (`EXP-0033-*`)
series were sealed under the legacy convention and are already published and
Bitcoin-anchored. Their hashes are immutable public facts — re-sealing them would
invalidate real anchors and break evidence third parties can already cite. So
`tools/verify_seals.py` accepts both and **declares which one each file used**
(`VALID` vs `VALID(legado)`) rather than hiding the difference. A file that verifies under
neither is not published.

> Known issue, disclosed: `v1` currently denotes two serializations. New seals should move
> to `rosettaq-archive/v2` so that an external verifier reading the canonical spec does not
> flag 30 legitimate files as invalid.

**Sealing policy.** Every seal is produced by a `seal()` function of a versioned harness
that is archived alongside the run. **Inline sealing is forbidden** — it produced one
unreproducible hash in this archive's history (`EXP-0007-001`), which was re-sealed
canonically *before any anchoring*, with a `meta.seal_correction` block inside the file
recording the old hash, the reason and the action.

## 4. Triple copy plus an external anchor

1. **GitHub** — `RosettaQuantum/evidence` (primary)
2. **Codeberg** — `RosettaQuantum/evidence` (mirror on independent non-profit Forgejo infrastructure)
3. **Cloudflare D1** — `rosettaq-ledger.run_archives` (full payload, hash, and the OTS proof)

plus an **OpenTimestamps** anchor (Bitcoin) per file.

**Why the anchor matters more than the copies.** Three identical copies prove the copies
are consistent *with each other* — not that the data is honest. Redundancy protects against
*later* tampering, not against *original* dishonesty; the truth mechanism is
reproducibility. And self-mirroring on infrastructure you control is not real independence.
That is why the timestamp is anchored on a chain we do not control.

## 5. How to verify this archive yourself

```bash
python3 tools/verify_seals.py 'runs/**/*.json' 'prereg/**/*.json'   # recompute every hash
diff <(curl -s <github raw url>) <(curl -s <codeberg raw url>)      # copies byte-identical
ots verify <file>.ots                                              # external timestamp
```

Any file whose recomputed hash differs from its stored `content_hash` is invalid — tell us
by opening an issue.

## 6. The judge protocol (`juez-v1`)

The same instance is solved twice, once per side:

- **equal budget on both sides** (wall-clock; 120 s per side in recent series)
- **exact optimum as referee** wherever tractable
- **fixed seeds**, **frozen library versions**, both recorded in the archive
- **classical champion is the strongest available solver** — OR-Tools CP-SAT, verified
  against brute force. A weak baseline would invalidate the entire archive.
- **every protocol deviation is declared inside the archive.** Example: at n=20 the
  gradient-based optimizer hit a memory wall and the protocol switched to gradient-free
  COBYLA — recorded in each affected run.
- **simulation first is a declared methodological choice, not a hidden limitation.** Real
  QPUs enter the ladder later.

## 7. Rules of the house

1. **`is_demo: true`** on every file until a real run exists. No illustrative result is
   ever presented as measured.
2. **Published = sealed.** Corrections are new files that reference the old one — never
   edits.
3. **The classical champion is always the strongest available solver.**
4. **Negative results get published.** A reproducible "not yet" is a valid outcome and the
   main product of this archive.
5. **Verify before anchoring.** If a seal does not verify, nothing gets stamped and the
   file is returned to the lab. A seal that does not verify is never anchored.
6. **The public counter never runs ahead of the evidence.** The sealed-run count on the
   website is raised only after all three copies are up and verifiable.
7. **Pre-registration.** Targets, parameters, seeds and success criteria are sealed and
   anchored *before* the runs, so they cannot be chosen after the fact.

## 8. Licensing

- **Data** (verdicts, experiment records, raw outputs, notebooks) — **CC BY 4.0**, see
  `LICENSE-evidence.md`.
- **Code** (harness, tooling) — **Apache 2.0**, see `LICENSE`.

CC0 is deliberately rejected: attribution is the point. We want the world — and the models
that cite this archive — to point back to the source.

---

*This repository is read-only for the world: open an issue if you find an error (that is
the free-QA loop we want), but the verdicts themselves are sealed.*
