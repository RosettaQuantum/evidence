# Errata — the E.ON series is one grid at three stress levels, not three grids

**Dated:** 2026-07-29 · **Affects:** E.ON track, recipe `RQ-0033`, runs `EXP-0033-001…009`
**Status:** disclosed here; corrected re-seals pending from the laboratory

## What we found

An internal audit of all nine sealed runs in the E.ON grid-expansion series found that
**every one of them ran on IEEE case14**, while six of the nine are *named* after a
larger grid. The contradiction sits inside the sealed files themselves: the
machine-readable parameters and the human-written note disagree.

| Run | Filename says | `w6.como.instance_params.grid` | `w6.que.instance` | Agree |
|---|---|---|---|---|
| `EXP-0033-001` | case14 | IEEE case14 | `case14_stress3.0_K14_seed42` | yes |
| `EXP-0033-002` | case14 | IEEE case14 | `case14_stress3.0_K14_seed43` | yes |
| `EXP-0033-003` | case14 | IEEE case14 | `case14_stress3.0_K14_seed44` | yes |
| `EXP-0033-004` | case30 | **IEEE case14** | `case14_stress2.2_K16_seed42` | **no** |
| `EXP-0033-005` | case30 | **IEEE case14** | `case14_stress2.2_K16_seed43` | **no** |
| `EXP-0033-006` | case30 | **IEEE case14** | `case14_stress2.2_K16_seed44` | **no** |
| `EXP-0033-007` | case30 | **IEEE case14** | `case14_stress2.2_K16_seed45` | **no** |
| `EXP-0033-008` | case30 | **IEEE case14** | `case14_stress2.2_K16_seed46` | **no** |
| `EXP-0033-009` | case118 | **IEEE case14** | `case14_stress1.8_K16_seed42` | **no** |

`EXP-0033-009` goes further: its `meta.scope_note` reads *"ESCALA UTILITY: IEEE case118
(118 buses, 173 lineas)"* while its own `instance_params` read
`{"grid": "IEEE case14", "load_scale": 1.8, "n_candidates": 16, ...}`. No run in this
archive contains any internal indication of a 30-bus or 118-bus network: no bus count,
no line count, no candidate set of that size. The parameter block is the harness input,
so it is the authoritative record of what was computed; the prose was aspirational.

## What the sealed evidence actually supports

A **stress ladder on a single grid**: IEEE case14 at load scales 1.8, 2.2 and 3.0, with
14 or 16 candidate lines, budget K=6, across seeds 42–46, 120 s per side. That is a
legitimate and useful result — the classical solver reached the proven optimum in every
one of the nine, and the winning plan cut real AC line overload — but it is *not* a
bus-count scaling ladder.

## What must not be claimed

Until corrected runs exist, none of the following is supported by sealed evidence and
must not appear in any proposal, page or feed:

- "case30" or "case118" as executed instances
- "utility-scale, 118 buses / 173 lines"
- "case14 → case30 → case118, all sealed"
- ">100 qubits" reached

## Why the files were not edited

Because published means sealed. The six mislabeled archives keep their hashes, their
Bitcoin anchors and their contradiction exactly as published — that record is now part
of the archive's history. The correction is a **new sealed file per affected run**,
produced by the laboratory's versioned `seal()` and referencing the old one, as with any
other correction here. The notary does not seal.

Meanwhile the discrepancy is exposed rather than hidden:
[`RosettaQ-EON-sealed-runs.csv`](../RosettaQ-EON-sealed-runs.csv) — generated from the
archives by `scripts/make_eon_csv.py` — carries both `grid_per_filename` and
`grid_per_internal_params` plus a `labels_agree` column, so anyone reading the summary
sees the conflict at a glance.

## Verify this yourself

```bash
for F in runs/2026/07/*EXP-0033-*.json; do
  python3 -c "
import json,sys,re,os
d=json.load(open(sys.argv[1]))
print(os.path.basename(sys.argv[1])[:60],
      '| internal grid:', d['w6']['como']['instance_params']['grid'],
      '| instance:', d['w6']['que']['instance'])" "$F"
done
```

## Why this note exists

We found this in our own archive, before a judge did. An archive whose whole claim is
"you do not have to trust us" cannot ask for the benefit of the doubt on its own
labels — and a mislabeled file is worse than a missing one, because it looks like
evidence. The proposal gets corrected to say what was measured.
