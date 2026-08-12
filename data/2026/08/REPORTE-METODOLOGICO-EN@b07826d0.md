# Methodology Report — Rosetta Quantum

**Cleveland Clinic Challenge · allosteric site prediction · deliverable 3**

> Every figure in this document is read at build time from the sealed files listed
> below; none is typed by hand. The Spanish source was approved before translation.

| Sealed file | ID | content_hash |
|---|---|---|
| RUN | `RQ-EXP-CLEV-BLIND-001` | `sha256:ca916f94a138ae3b19279d045f9631be3944276b8ccb71e637b9a46963497214` |
| PREREG | `PR-COARSE-001` | `sha256:5af5af0e79dfad074ce28f47363424751d44a83a3a9794240b6402e9961a499b` |
| RUN | `RQ-EXP-COARSE-001` | `sha256:296e1c7055747017a2c1774ff7bce258f683f46616433cca3c83f7796cdd67a2` |
| RUN | `RQ-EXP-N90-LOPO-003` | `sha256:022f8e450782c06866de84d852270105b8aa717e3daf41bb8ea80f719e4244df` |

---

## 1. What was predicted, and with what

The metric is the **mixing matrix of a continuous-time quantum walk (CTQW)**: the
infinite-time average of the transition probability over the protein's CA contact
network.

```
C(i,j) = lim (1/T) ∫ |<i| e^{-iHt} |j>|² dt = Σ_λ |<i| P_λ |j>|²
```

A residue's score is the mean of C(i, s) over the active-site residues. Sites are
formed by single-linkage clustering at 8 Å of the top 10 % of distal residues.

**Why this metric and not another.** Three reasons, in order of weight:

1. **It has no free parameters.** There is no time window, no grid, no Trotter step
   count to choose. We had already been bitten by the opposite: a grid capped at
   t = 20 inflated an apparent advantage from 5× to 19×. A metric with no knobs cannot
   be overfitted, nor attacked on the choice of knobs.
2. **The exact classical analogue, under the same averaging, carries no information.**
   Classical diffusion averaged over long times converges to the uniform distribution
   1/n — a rank-1 matrix that ranks every residue identically. This is not a weak
   baseline chosen on purpose: it is the *same* operation, and it yields exactly
   nothing. It is proven in the engine's test suite, not asserted.
3. **It is transport physics**, not an ad-hoc feature: C(i, src) measures how much
   amplitude from the source ends up, on average, at each residue.

The geometric conventions are the engine's sealed ones, not invented for this
challenge: CA–CA contact at 8.5 Å, validated pocket within 4.5 Å of the ligand, distal
beyond 6.0 Å of every source residue, Gaussian kernel σ = 6.0 Å.

## 2. How the prediction was blinded, and where that blinding has a limit

The chain is in git and each link is an ancestor of the next. We did not read the log
of commit titles: ancestry was checked with `git merge-base --is-ancestor`, and all
four were checked to be contained in `origin/main`.

| # | Commit | Date (UTC) | Role |
|---|---|---|---|
| 1 | `407fa7b` | 2026-08-09T18:14:45Z | metric pre-registered, no free parameters, before predicting |
| 2 | `4cfac34` | 2026-08-09T18:15:14Z | blind predictions for the 4 targets, committed |
| 3 | `f119f42` | 2026-08-09T18:19:30Z | scorer committed **before** it was run (and 9GZ1 archived) |
| 4 | `b2a29e4` | 2026-08-09T18:20:21Z | scoring result, published exactly as it came out |

**The limit, stated because a third party should not have to discover it.** Two of the
three holo structures — 6OIM (KRAS) and 5MO4 (ABL1) — were already in the git tree at
commit `2538c47`, which precedes the predictions. Only 9GZ1, for myosin, arrived after.

So for KRAS and ABL1 the blinding is **not physical** (the file did not exist) but a
property of the code and the process. What supports it is that the predictor's inputs
are auditable and do not include the holo structures: the cache builder opens only the
apo structures declared in its target table (4OBE, 1OPL, 5TBY, 1NKP); the ranker reads
only the blind caches; and those caches do not carry the pocket key and declare
themselves blind, with a positive test case that checks it. For myosin, the physical
chain holds as well.

## 3. The three metrics, fixed before anything was opened

1. **Hit rank.** The rank of the first site in the top-5 with at least one residue
   inside the validated pocket, plus each site's minimum distance to the pocket.
2. **Pocket percentile.** Mean percentile of its residues among the distal ones.
3. **Permutation p-value.** 2,000 random contiguous patches of the same size as the
   pocket, distal only, fixed seed.

The null is built from **contiguous patches**, not scattered residues. An allosteric
site is a spatially connected object: a residue's score strongly predicts its
neighbours', so the effective sample size is far smaller than the residue count, and
any test assuming independence inflates significance. Comparing a pocket against
confetti would inflate the result in our own favour.

## 4. The result: negative

| Target | Reference drug | Pocket (in network / holo) | First hit rank | Percentile | p |
|---|---|---|---|---|---|
| KRAS G12C | MOV (sotorasib, 6OIM) | 21 / 21 | 2 | 47.82 | 0.5212 |
| BCR-ABL1 | AY7 (asciminib, 5MO4) | 20 / 20 | none | 60.12 | 0.4153 |
| Cardiac myosin | XB2 (mavacamten, 9GZ1) | 12 / 12 | none | 60.62 | 0.4038 |

**No significance on any of the three.** The p-values range from 0.4038 to 0.5212, the pocket
percentiles sit in the middle of the distribution, and only KRAS has a top-5 site that
touches the pocket at all.

**c-Myc is excluded from scoring, and we say so.** It was predicted blind and its
prediction is committed in git, but no validated allosteric pocket has been published
for it. We do not score what cannot be scored.

**The two near-misses, which are never quoted alone.** KRAS has a rank-2 site touching
the sotorasib pocket by one residue, at p = 0.5212. Myosin has a site 3.83 Å from the
mavacamten pocket, at p = 0.4038. At those p-values they are not hits, and they are never
cited without them. If the p-value does not fit, the number does not fit either.

## 5. Why it failed — the most useful finding of the exercise

**The score is a proximity-to-source measure wearing the costume of dynamic
connectivity.** And an allosteric pocket is, by definition, distal: the metric and the
objective are in tension by construction.

| Target | n | Distal | Spearman ρ (distal) | ρ (all residues) |
|---|---|---|---|---|
| KRAS G12C | 169 | 119 | -0.6162 | -0.8293 |
| BCR-ABL1 | 451 | 391 | -0.8178 | -0.8772 |
| Cardiac myosin | 954 | 935 | -0.8501 | -0.8582 |
| c-Myc | 88 | 53 | -0.7855 | -0.8943 |

Denominator: 4 of 4 targets measured, 0 skipped. Across distal residues the range
is -0.8501 to -0.6162; across all residues, -0.8943 to -0.8293.

**The mechanism is spectral localisation.** On a path graph the mixing matrix is
**flat in the interior** and spikes at **both** ends: the far end scores the same as
the source itself. In a protein that means chain termini and surface protrusions rise
on their own, with nothing coupling them to the active site.

This is proven on a case whose answer is known in advance. The check was written
expecting decay with distance, and it screamed. It stays in the suite so that if
somebody "fixes" the metric and this changes, they find out.

**The design consequence we take away:** any future metric must report its correlation
with distance-to-source alongside its result. An allostery predictor correlating -0.8
with proximity is measuring geometry, not coupling.

## 6. Coarse-graining scalability: also negative

Question pre-registered in `PR-COARSE-001`, sealed before anything was run: when the network is
compressed into supernodes of consecutive residues, **how much of the residue ordering
survives?** What had already been measured was the pocket percentile and the speed-up.
What was missing is what decides whether compression is useful at all: a method that
runs 50× faster and reorders the list has not accelerated anything — it has solved a
different problem.

Thresholds frozen before looking: survives at ρ ≥ 0.90; partial between 0.70 and 0.90;
does not survive below 0.70.

| Target | b = 2 | b = 4 | b = 8 | b = 16 |
|---|---|---|---|---|
| KRAS G12C | 0.5422 | 0.4784 | 0.2018 | 0.0838 |
| BCR-ABL1 | 0.8356 | 0.7898 | 0.7315 | 0.7354 |
| Cardiac myosin | 0.8859 | 0.8301 | 0.8001 | 0.7846 |
| c-Myc | 0.5118 | 0.5822 | 0.4169 | 0.7882 |

**0 of 16 cells** reach the survival threshold: 9 land in partial and 7 fall below
0.70. Not even the mildest compression — block 2, which merely merges pairs of
consecutive residues — reaches it on any target. Denominator: 4 of 4 targets, 16 of
16 cells, 0 skipped.

And what weighs most is not ρ: the **top 10 % of distal residues** — the set that
enters the clustering and therefore decides which sites are predicted — is preserved
with a Jaccard index between 0.0 and 0.6596. At that level you do not get the same sites
ranked worse: you get different sites.

**Reading.** The useful answer is not the speed-up: it is that the speed-up cannot be
collected. For this metric, sequence-block coarse-graining is not a scalability route —
it changes the answer before accelerating it. If coarse-graining is to be used, the
grouping would have to respect structure (domains, graph communities) rather than
sequence order; and that is a new hypothesis, which would go to its own
pre-registration instead of sneaking in as an adjustment to this one.

## 7. What this work does NOT claim

- **Quantum crossings: zero.** A "crossing" means a quantum method beating the best
  classical one. It did not happen, and none of these experiments could have produced
  one: the coarse-graining study does not even compare quantum against classical.
- **Significance against chance: none**, with p between 0.4038 and 0.5212 on the three scored
  targets.
- **Simulating is not measuring.** Everything in this report is exact CPU simulation.
  Hardware runs are reported separately and support no claim made here.
- **The coarse-graining speed-up is an order of magnitude, not a measurement.** Timings
  were taken once per cell on a machine under other load. The result shows it: myosin
  reports 131.9× at block 8 and 21.3× at block 16, which is impossible as a real
  measurement.
- **c-Myc at block 16 is not an improvement.** It collapses to 6 supernodes, so its ρ
  of 0.7882 is computed over very few distinct values: a resolution artefact, not signal.
- **Training/challenge overlap, declared.** KRAS G12C, BCR-ABL1 and cardiac myosin are
  inside the engine's 90-protein training set. There is no leakage in these experiments
  because **no trained model was used**: the blind metric has no parameters and no
  training. The stacked arm, which does, requires leave-one-protein-out and is a
  separate experiment, not yet run.

## 8. What is out of scope

- **The leakage-free stacked arm — and why the reason we gave was wrong.** We reported this arm as blocked by the environment: the conservation module requires Biopython ≥ 1.80 and the laboratory machine had 1.79, so the conservation feature would silently become a column of zeros. That was true of the machine. It was not the whole truth about the experiment.

  When we moved the run to CI and measured it, we found that the conservation feature had been a column of zeros **in every N=90 run already sealed** — for a second, independent reason: the cache was written to one directory and read from another. A guard written for exactly this failure existed, was tested, and was never called from the engine. It is now wired in and fails closed, and the column census is printed on every run whether or not anything is wrong.

  With the column finally alive in 90 of 90 targets, the feature-based arm scores **8.33 × 10⁻⁹ with conservation and 4.57 × 10⁻⁹ without it** — 1.8× better without the real feature in the model. The quantum manager arm remains non-significant (p = 0.104), classical diffusion remains the strongest single propagator, and the manager still selects it in 50 of 90 targets. Every sealed number in this report is unchanged.

  So the stacked arm was not held back by a missing signal. It was held back by a broken environment, and by a claim about that environment that we could not check until we built the check. Three seals record the sequence — the wrong reading, the retraction, and the measurement — and all three are public.
- **Other groupings and other sizes.** No community or domain-based grouping was
  tested, no blocks larger than 16, and the effect of compression on accuracy against
  validated pockets was not measured — that would require opening the holo structures
  and is a separate experiment.
- **A truly prospective null.** It does not exist: the pool is exhausted, and everything
  passing the distal filter is already inside the set. We say so rather than calling a
  holdout prospective.

## 9. The same circuit, run twice on hardware

**The walk runs faithfully on real hardware, and we repeated it to show how much the
number moves.** That is the whole claim of this section, and it is deliberately smaller
than what the data would allow us to say.

A 7-circuit battery ran on ibm_kingston (26,000 shots total), submitted with a negative control, a
repetition of the positive control, and a replica of an earlier run. **The seven job
identifiers and their roles were sealed before any result existed**, so the analysis
could not choose which jobs to count.

| Role | `job_id` | Measured pocket mass | Ideal simulation | Uniform baseline |
|---|---|---|---|---|
| positive control | `d9t16s7tfhrs73dtb550` | 56.8 % | 57.4 % | 37.5 % |
| secondary control | `d9t16s8pdb6s73e6jh9g` | 23.8 % | 27.2 % | 12.5 % |
| long-corridor exploration | `d9t16sgpdb6s73e6jha0` | 47.2 % | 49.2 % | 10.0 % |
| repetition | `d9t16svpemts73cu9fhg` | 56.8 % | 57.4 % | 37.5 % |
| replica of run 1 | `d9t16t7tfhrs73dtb580` | 21.8 % | 18.7 % | 66.7 % |
| transport, BCR-ABL1 | `d9t16tftfhrs73dtb58g` | 27.7 % | 27.3 % | 12.5 % |
| negative control | `d9t16tfpemts73cu9fig` | 28.4 % | 26.3 % | 37.5 % |

Hardware tracks the ideal simulation to within **3.4 percentage points** at worst, and
the shuffled negative control separates from the positive one by **28.4 points**. The
circuit is doing what the simulation says it should.

### The finding we did not go looking for

The repetition — the same circuit, same backend, nothing changed — returns **the same
pocket mass to within 0.0001**, while the fraction of physically valid shots moves by **3.6
points**. Across days it moves further: the replica of the earlier circuit gives 50.5 %
valid against 61.4 % originally, **10.8 points lower**.

**The physics we measure is stable; the noise wrapped around it is not.** Those are two
numbers with different lifetimes, and until this run we quoted them side by side as if
they had one. We are adopting this as a rule rather than reporting it as a curiosity:
**any validity figure we publish travels with its date, or it does not travel.** A
single hardware run reports a snapshot of a backend on a day, and calling it a property
of the device is how a reproducible result turns into an irreproducible claim.

### What this section does not claim

- **The corridor is built knowing where the pocket is.** The subgraph is the shortest
  path from the active site to the *known* allosteric pocket, plus neighbours. So this
  battery says nothing about *finding* pockets: it measures whether the walk runs
  faithfully on a small graph with the pocket deliberately placed at the far end.
- **The "classical ceiling" is the uniform distribution**, |pocket|/n — verified equal
  on all seven circuits. Beating it is beating the long-time classical diffusion limit,
  which our own justification declares carries no information. It is **not** beating the
  best classical method for this task; that method does not appear in this comparison.
- **Quantum crossings: still zero.**
- **n = 1 per circuit.** The repetition is the only error bar this experiment has, and
  that is precisely why it was included.

## How to verify this document

The three `content_hash` values in the header are recomputed with:

```bash
python3 tools/verify_seals.py <file>
```

**Which convention applies depends on the file, and the file's own label does not tell
you.** Of the archive's sealed files, 47 declare `rosettaq-archive/v1` and split across
**two** different conventions that recompute differently. The verifier tries all of them
and reports which one reproduced the stored hash; that is the authority, not the label.

**For v1 and v2 files, verify in Python.** Those seals are computed over the text
produced by Python's `json.dumps`, and languages do not serialise the same numbers
identically: Python writes a float `6.0` where JavaScript, Go and Rust write `6`. If
you parse such a file in another language and re-serialise it to check the hash, you
will get a different result — silently, and looking exactly like tampering. It is not.
Verify in Python, or compare the bytes of the file as downloaded without
re-serialising it.

**For v3 files that limitation is gone:** they are sealed over the RFC 8785 (JCS)
canonical form, which yields the same text in any language. An independent JavaScript
implementation, written from the RFC, reproduces our canonical output character for
character on 22 of 22 test vectors.

*No anchored file is ever re-sealed. Published hashes are immutable public facts.*
