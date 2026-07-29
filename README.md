# Rosetta Quantum — Evidence Archive

The public, immutable record of what we measured. For each recipe (a parametrised
quantum algorithm) and problem class, this archive states whether the quantum method
beat the best available classical method, on which instance, under which budget — with
the raw evidence attached. **This is a record, not a pitch:** the results below include
the ones where quantum lost, because those are the majority and hiding them would make
the rest worthless.

**State of the archive — 2026-07-28**

| | |
|---|---|
| Sealed runs | **48** |
| Published verdicts | **1** (`V-0012`) |
| Pre-registrations | **2** (E.ON, Cleveland Clinic) |
| Problem classes | **3** — portfolio optimisation · grid expansion · molecular allostery |
| Measured quantum wins | **0** |
| Optimisation runs where the classical solver reached the proven optimum | **29 / 29** |

Every file is sealed with SHA-256, stored byte-identical in three independent places
(this repo, a Codeberg mirror, and a Cloudflare D1 database) and timestamp-anchored in
the Bitcoin blockchain, which none of the three parties controls.

---

## Verify it yourself — three commands

You do not need to trust us, and you do not need to ask us anything. Clone the repo and
run these.

**1. Every seal reproduces from the file's own content**

```bash
python3 tools/verify_seals.py 'runs/**/*.json' 'prereg/**/*.json' 'verdicts/**/*.json'
```

Expected: `0 INVALID`. The tool prints, per file, which sealing convention reproduced
its hash — `v2` (current), `v1-canonica`, or `v1-legado`. Two conventions exist under
the `rosettaq-archive/v1` tag for a documented historical reason (see
[`SPEC-SELLADO.md`](SPEC-SELLADO.md) and the manifest in `manifests/`); the earlier
series were already published and anchored when the convention was tightened, and
re-sealing them would have invalidated real timestamps. The verifier declares which one
each file used rather than hiding the difference.

**2. The three copies are byte-identical**

```bash
F=runs/2026/07/RosettaQ__RUN__EXP-0007-015__20260725T1543Z__ctqw-vs-clasicos--allosteria-miosina-cardiaca.json
diff <(curl -s "https://raw.githubusercontent.com/RosettaQuantum/evidence/main/$F") \
     <(curl -s "https://codeberg.org/RosettaQuantum/evidence/raw/branch/main/$F") && echo IDENTICAL
```

**3. The timestamp is anchored in Bitcoin**

```bash
pip install opentimestamps-client
ots info runs/2026/07/<file>.json.ots      # shows BitcoinBlockHeaderAttestation(<height>)
ots verify runs/2026/07/<file>.json.ots    # full check; needs a local Bitcoin node
```

Without a node, check the attestation against any block explorer — the Merkle root in
the proof must equal the block's:

```bash
H=959715
HASH=$(curl -s https://blockstream.info/api/block-height/$H)
curl -s https://blockstream.info/api/block/$HASH | jq -r '.merkle_root, .timestamp'
```

Block **959715** was mined 2026-07-26 15:26 UTC. The seals below existed before that
block, which is what the anchor proves — and no party to this archive can move it.

---

## Cleveland Clinic track — allosteric site prediction (recipe `RQ-0007`)

Continuous-time quantum walk (CTQW) versus classical propagation on residue-contact
networks, over the four mandated targets. The parameter grid, the null models and the
success criteria were **sealed before the runs** in the pre-registration
[`PR-CLEV-001`](prereg/2026/07/), so nothing here was chosen after seeing the results.

| Run | Target | Structures | Effector | Sealed | sha256 (first 16) | BTC block |
|---|---|---|---|---|---|---|
| [`EXP-0007-013`](runs/2026/07/RosettaQ__RUN__EXP-0007-013__20260725T1542Z__ctqw-vs-clasicos--allosteria-kras-g12c.json) | KRAS G12C | 4OBE → 6OIM | AMG 510 (MOV) | 2026-07-25 | `1dc7ccc51e031588…` | 959715 |
| [`EXP-0007-014`](runs/2026/07/RosettaQ__RUN__EXP-0007-014__20260725T1542Z__ctqw-vs-clasicos--allosteria-bcr-abl1.json) | BCR-ABL1 | 1OPL → 5MO4 | asciminib (AY7) | 2026-07-25 | `1b61568b68e5cc04…` | 959715 |
| [`EXP-0007-015`](runs/2026/07/RosettaQ__RUN__EXP-0007-015__20260725T1543Z__ctqw-vs-clasicos--allosteria-miosina-cardiaca.json) | Cardiac myosin | 5TBY → 9GZ1 | mavacamten (XB2) | 2026-07-25 | `6718eba95dba2822…` | 959715 |
| [`EXP-0007-016`](runs/2026/07/RosettaQ__RUN__EXP-0007-016__20260725T1543Z__ctqw--prediccion-ciega-c-myc.json) | c-Myc / Max | 1NKP | none — blind prediction | 2026-07-25 | `9a49ff3ae0b4d359…` | 959715 |
| [`EXP-0007-017`](runs/2026/07/RosettaQ__RUN__EXP-0007-017__20260725T1546Z__nulo-espacial-contiguo--instrumento-de-medicion.json) | all three | spatial null | — | 2026-07-25 | `ff29769b177ed8c5…` | 959715 |
| [`EXP-0007-018`](runs/2026/07/RosettaQ__RUN__EXP-0007-018__20260725T1538Z__cripticidad--dos-regimenes-de-fallo.json) | KRAS G12C, BCR-ABL1 | crypticity | — | 2026-07-25 | `5dc317c23db08f68…` | 959715 |
| [`EXP-0007-019`](runs/2026/07/RosettaQ__RUN__EXP-0007-019__20260725T1553Z__entregables-exigidos--ruido-escala-y-costo-de-circuito.json) | all three | required deliverables | — | 2026-07-25 | `a4fdb96d1415bdbd…` | 959715 |

All seven share the same anchor batch; `ots info` on each proof also lists blocks
959725 and 959747.

**What these runs found:** CTQW did not beat the classical baselines. On KRAS G12C it
ranked *below chance*; on the others it sat above chance but not significantly, and
under an honest spatial null (`EXP-0007-017`) **nothing was significant for any method
on any target** — including the classical ones. `EXP-0007-018` measures *why*, and
separates two distinct failure modes rather than assuming one. `EXP-0007-016` is a
blind prediction on a target with no co-crystallised effector: sealed and dated now, so
it can be scored later by someone else.

That is the result. We publish it because a benchmark that only reports its wins is
not a benchmark.

**Ground-truth correction:** the challenge brief lists `6C1H` for validating mavacamten
on cardiac myosin, but `6C1H` contains only ADP and Mg — no mavacamten. We used `9GZ1`
(ligand `XB2` = mavacamten). Declared, dated and independently checkable in
[`NOTES/2026-07-28-6C1H-mavacamten.md`](NOTES/2026-07-28-6C1H-mavacamten.md).

A machine-readable summary of every sealed `RQ-0007` run — including the earlier
exploratory series — is in
[`RosettaQ-Cleveland-sealed-runs.csv`](RosettaQ-Cleveland-sealed-runs.csv), generated
from the archives themselves by `scripts/make_cleveland_csv.py` so it cannot drift from
what is sealed.

---

## What is in here

| Path | Contents |
|---|---|
| `runs/<year>/<month>/` | One sealed archive per fight, plus its `.ots` timestamp proof |
| `verdicts/<year>/` | Dated judgments over a series of runs |
| `prereg/<year>/<month>/` | Forward commitments, sealed *before* the runs exist |
| `recipes/` | The algorithm cards being tested |
| `data/`, `code/` | Raw result files and the scripts that produced them, hashed inside each run |
| `harness/`, `tools/`, `scripts/` | The sealing library, the verifier, the sync utilities |
| `NOTES/` | Dated corrections and clarifications |

Each run records the six questions — what ran, how, when, where, why, who — under its
`w6` key, with frozen library versions and fixed seeds. Runs sealed under `v2` also
record the SHA-256 of the exact data file and script that produced them, and those
hashes are inside the sealed hash: you can re-run the script and compare.

## Rules this archive follows

1. **Verify before anchoring.** A seal that does not reproduce is never timestamped and
   never published. One pre-registration is being held back right now for exactly this.
2. **Published means sealed.** Corrections are new files that reference the old one —
   never edits.
3. **The classical champion is the strongest solver available.** A weak baseline would
   invalidate everything here.
4. **Negative results get published.** A reproducible "not yet" is a valid outcome and
   the main product of this archive.
5. **The public counters never run ahead of the evidence.** They move after all three
   copies are up and verifiable, not before.

Full protocol: [`PROTOCOL.md`](PROTOCOL.md) · Sealing spec: [`SPEC-SELLADO.md`](SPEC-SELLADO.md)

## Licence

Data (verdicts, run records, raw outputs) — **CC BY 4.0**, see
[`LICENSE-evidence.md`](LICENSE-evidence.md). Code (harness, tooling) — **Apache 2.0**,
see [`LICENSE`](LICENSE). Attribution is deliberate: cite the archive, and the citation
trail is the point.

---

*Found an error? Open an issue. External correction is the free QA loop this archive
wants — but the verdicts themselves stay sealed.*
