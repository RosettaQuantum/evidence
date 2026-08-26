# When the protocol decides the number: an anchored pre-registration, an adversarial attack on our own result, and a quantum negative that survives its own controls

**Rosetta Quantum · HSBC track of the 2026 Global Quantum + AI Challenge**

> Every figure below is read from a sealed artefact at build time; none is typed. Each claim carries exactly one of three labels: **[measured]** (our instrument produced it and the artefact lets you recompute it), **[by construction]** (it follows from how the object is built), **[from the literature]** (a cited source holds it up). Anything without a label is not in this document.

## 1 · Summary

We built a classical fraud-detection baseline on public data, with the question and the protocol **sealed and pushed to a public repository before any of the code existed**. Then we attacked it: we repeated the measurement under the protocol the published literature uses, and under three variants designed to kill our own result, with every possible outcome written down and sealed before anything ran.

Four things came out.

**Our implementation reproduces the published numbers when it uses the published protocol** [measured]: the mean of the clean random-split series lands at 0.8545, inside the band [0.841 – 0.901] we fixed beforehand from the challenge statement's own tabulated results. That is the credential — whatever we measure differently afterwards is not an implementation error of ours.

**The choice of split moves the headline metric by 0.0713 AUPRC** [measured]. Random splits score higher than temporal ones on the same model and the same data, and the gap is the second finding.

**SMOTE, correctly applied, contributes +0.0004** [measured]. In this dataset and this implementation the split does all the work and the oversampling does none.

**Applied in the common defective order, the metric saturates at 1.0000 on every seed** [measured] — reportable perfection with any model whatsoever. That is the headline of this document, and §6 states precisely what it is and is not.

We claim no scientific novelty: the underlying phenomenon is already catalogued [from the literature: Kapoor & Narayanan, *Leakage and the reproducibility crisis in ML-based science*, Patterns 2023]. What we offer is the machine that measures it, with a verifiable pre-registration and recomputation by third parties.

## 2 · Results against what you asked for

This section exists so that you do **not** have to hunt for whether we complied. Each row
quotes the statement and says where the answer is.

The **§4.1 metrics for both arms**, with precision, recall and the full confusion matrix,
are in §6 — this section points at them rather than repeating them.

### The three outputs of §5.2

| asked for, verbatim | where it is |
|---|---|
| *«Fraud Probability — Float [0, 1]»* | package file 2, column `fraud_probability`; range [0.0293 – 1.0000] |
| *«Binary Prediction — Integer {0, 1}»* | package file 2, column `binary_prediction`; 18 positives |
| *«Feature Attribution — contribution of features to each prediction»* | package file 2, 8 `attribution_*` columns, **one row per transaction** |

### Everything else the statement asks for, and where

| asked for | § | where |
|---|---|---|
| *«encoding strategy, and circuit design choices»* | 5.2 | §8 |
| *«comparison with at least one classical baseline»* | 5.2 | §6 and §8 |
| *«discussion of any observed quantum improvement and under what conditions»* | 5.2 | §8 |
| *«handling of class imbalance should be documented»* | 5.3 | §8 |
| *«feature selection is expected for quantum approaches»* | 5.3 | §8 |
| *«qubit count and circuit depth»* | 5.3 | §8, circuit table |
| *«feature attribution or importance analysis is valued»* | 5.3 | §8, local and permutation |
| *«total number of samples used for quantum execution must be explicitly stated»* | 4.2 | §8 |
| *«subsampling must be performed using stratified sampling»* | 4.2 | §8 |
| *«benchmark against these published results»* | 4.1 | §6 |
| *«error mitigation techniques»* | 5.3 | §8 — no hardware was run, and we say what would apply |
| *«comparison of simulator vs. hardware results»* | 5.3 | not available; §8 says so plainly |

**And one thing the statement does NOT ask for that we hand you anyway**, because it is
what most helps a bank evaluating a pilot today: §9.

## 3 · The question, and when it was fixed

The question — what does a quantum or quantum-inspired model add over a tuned classical one, with the protocol fixed before anyone looks? — was sealed as `RQ-PREREG-HSBC-001` (`sha256:b04f214fae845b1c…`) and committed in `72dcbf2`, **before a single row of data had been downloaded**. That is a property of the git history, which you can check yourself; it is not a claim of ours. [by construction]

The adversarial attack was pre-registered separately as `RQ-PREREG-HSBC-002-ATAQUE` (`sha256:87c187b48627d529…`), committed in `6859ebf`, **with its three possible outcomes written before the runs, including the one that left us looking bad**. The outcome that fired is computed by the sealing harness against the pre-fixed band, not chosen afterwards by a human. [by construction]

**Sealing and anchoring, as they stand on disk right now** [measured]: all 11 pieces of this track are sealed and their content hashes verify. Of those, **11 carry an OpenTimestamps receipt** (`RQ-PREREG-HSBC-001`, `RQ-PREREG-HSBC-002-ATAQUE`, `RQ-PREREG-HSBC-003-CUANTICO`, `RQ-DATA-HSBC-ULB-001`, `RQ-EXP-HSBC-BASE-001`, `RQ-EXP-HSBC-ATAQUE-001`, `RQ-EXP-HSBC-Q-001`, `RQ-EXP-HSBC-Q-002`, `RQ-EXP-HSBC-IEEE-001`, `RQ-ERRATA-PREREG-HSBC-003`, `RQ-ERRATA-EXP-HSBC-Q-001`) and **0 do not yet** (). Anchoring is the notary's step, deliberately separate from the lab's, and we report the state rather than let you assume it. What the git history gives you for every piece is the order — the pre-registration is in the tree before any code that could have been tuned to it. What an OpenTimestamps receipt adds, for the two that have one, is a bound on *when*, from a clock neither we nor you control.

This document covers the classical phase of the track. The quantum arm is later work and nothing here is claimed about it.

## 4 · The data, and its measured limits

**Source** [measured]: the ULB *creditcard* dataset via OpenML (id 1597, version 1). The md5 we measured equals the one the source declares (`178bcf9bb1f3…`); sha256 `fdaf12730dc1fc42…`. Both were fixed in the sealed manifest `RQ-DATA-HSBC-ULB-001` **before the first training run**, so no result can pick its own dataset after the fact.

**Census** [measured]: 284,807 rows, 492 frauds (0.173 %), 0 null values — trivially zero in both classes. No row was excluded and the features are used exactly as they arrive, with no transformation of ours [by construction].

**The limits — measured, not estimated.** Every figure in this list was computed from the ARFF whose sha256 the manifest pins, and the generator verifies that hash before reading a byte.

- **The whole window is 48.00 hours** [measured: Time ranges over 0–172,792 seconds] — two days of September 2013 [from the literature: the dataset's own documentation]. Our temporal 80/20 split leaves **7.65 hours** of test. Calling that “the future” would be more than the data supports, so we do not call it that.
- **The positive class is not spread evenly through time** [measured]: across the six 8-hour blocks the fraud rate varies by a factor of 4.9 (0.46 % in the worst block against 0.09 % in the cleanest), and the temporal test set ends up holding just 75 of the 492 frauds — 15.2 % of them.
- **V1–V28 are the components of a PCA the dataset's own authors fitted over the whole set** [by construction: it was published already transformed, so nobody can re-fit it on their training half alone]. It is unsupervised PCA — it never saw a label — and it is of a different order than an oversampling leak, but it is inherited leakage all the same and **we declare it** (annex B, L1.2-inherited).
- **Sampling frame**: card-holder transactions from one European processor over two days [from the literature]. **We do not claim it represents fraud in general.** Every finding in this document is intra-dataset and by construction, never an extrapolation.

## 5 · Method

**Split** [measured, sealed in the pre-registration]: temporal 80/20 on the `Time` column — 227,845 training rows (417 frauds) against 56,962 test rows (75 frauds). The sha256 of the test half is declared inside the artefact (`88f43ccb6ffcd6ae…`) and is **bit-identical across two different machines** [measured: the local Mac and the CI runner produced the same hash]. Exact duplicates between the halves: 0 [measured].

**The metric that decides** [sealed beforehand]: AUPRC. At a prevalence of 0.173 % the AUC-ROC is optically generous — it is easy to score high on it and learn nothing — so AUPRC rules and AUC-ROC, F1 and the confusion matrix are always reported beside it, never instead of it. [by construction]

**Baseline**: XGBoost, with its configuration declared inside artefact `@2072bc53`. **LightGBM is OPEN and stays visible**: our v1 configuration breaks it (AUPRC 0.0058, 9,624 false positives at threshold 0.5) [measured]. That is a defect in our configuration, not in the method, and it does **not** enter as a tuned baseline until it passes the declared hyperparameter search. That search is still pending; if LightGBM ends up not entering at all, this paragraph is updated with the reason rather than deleted.

**Guards, all fail-closed and all mutation-tested** [measured]: three deliberately broken artefacts — data foreign to the manifest, a harness with no provenance, a metric that does not match its own scores — make the verification battery scream with exit code 1, while the base case stays silent. A guard that has only ever been tested for screaming passes every test. What the guards enforce: the data is verified against the manifest before training; no test row takes part in training; the stratification of every subsample is measured rather than assumed; and every artefact carries the sha256 of the harness that produced it.

## 6 · Results of the classical arm

**XGBoost baseline on the temporal split** [measured, artefact `@2072bc53`, sealed as `RQ-EXP-HSBC-BASE-001`]:

| metric | value | 95 % bootstrap CI (2,000 resamples, seed 42) |
|---|---|---|
| AUPRC (the metric that decides) | **0.8008** | [0.705 – 0.883] |
| AUC-ROC | 0.9878 | [0.977 – 0.996] |
| F1 at threshold 0.5 | 0.8235 | tp=56 fp=5 fn=19 tn=56,882 |

The first two rows describe the same model on the same test set: 0.8008 AUPRC and 0.9878 AUC-ROC. Reporting only the second would not be a lie, and it would tell the reader almost nothing — which is why the pre-registration fixed AUPRC as the metric that decides, before any of these numbers existed. [by construction]

**Validation context** [from the literature: the baselines the challenge statement tabulates]: the published stacking result on this dataset reports AUC-ROC 0.9887, and ours gives 0.9878 on a temporal split. The published AUPRC is 0.871, and **our own confidence interval contains it, so we do not claim any difference against that number.** Crossing protocols *and* implementations at once is not a comparison. The honest comparison is intra-implementation, and it is in §6.

### The §4.1 metrics, for both arms

| metric | classical (XGBoost) | quantum kernel |
|---|---|---|
| **AUC-ROC** | 0.987796 | 0.743759 |
| **AUPRC** | **0.800822** [0.7054 – 0.8828] | **0.257453** [0.1546 – 0.3691] |
| **F1** | 0.8235 | 0.3226 |
| **Precision** | 0.9180 | 0.8333 |
| **Recall** | 0.7467 | 0.2000 |
| **confusion matrix** | tp=56 fp=5 fn=19 tn=56882 | tp=15 fp=3 fn=60 tn=56884 |

*The classical threshold is 0.5 on a probability. The quantum threshold was chosen **on
the training data** over the calibrated probability, never by looking at the test set; §8
explains why. Both are scored on the same test set, verified by hash.*

## 7 · Attacks on our own result

This section comes before the conclusions rather than after them, because it is what gives them the right to exist.

Four series, 65 training runs, **the same model and the same data throughout** — the only thing that changes is the protocol [measured, seal `RQ-EXP-HSBC-ATAQUE-001`, Bitcoin-anchored]:

| series | protocol | n | mean AUPRC ± sd |
|---|---|---|---|
| S1 | stratified random 80/20, no SMOTE | 20 | 0.8542 ± 0.0324 |
| S2 | random + SMOTE fitted **inside** the training half | 20 | **0.8545** ± 0.0306 |
| S3 | random + SMOTE applied **before** the split (defective on purpose) | 20 | 1.0000 ± 0.00001 |
| S4 | temporal, cut points from 70 % to 90 % | 5 | 0.7829 ± 0.0295 |

**What survived and what did not, against the outcomes sealed beforehand:**

1. **The implementation is validated** [measured]. Outcome 1 of the three fired: S2 — the literature's protocol, correctly applied — has mean 0.8545, inside the pre-fixed band [0.841 – 0.901] built from the published numbers. So our temporal-versus-random gap is not an artefact of our code. *(The sealed artefact states this outcome in Spanish, its original language; the translation is ours and the artefact remains the source of the fact.)*
2. **The split effect holds under its pre-sealed criterion, by a narrow margin, and we say the margin is narrow** [measured]. Δ = mean(S1) − mean(S4) = 0.0713. The first condition is comfortable: Welch p = 0.002451 and Mann-Whitney p = 0.001092 agree, both well under the pre-set 0.01. The second condition — Δ greater than twice the median per-run bootstrap noise, i.e. 0.0702 — **is met by 1.5 % of the threshold.** A different realisation of the noise might not have met it. The seal protects whoever audits us; this sentence protects whoever reads us, and both are needed.
3. **A hole we anticipated did not open, and it is recorded anyway** [by construction]. Before running we warned that if S2 fell below the band while S3 rose above it, the sealed outcomes would leave a region uncovered. S2 landed inside the band and the outcome fired unambiguously — but a pre-registration that anticipates its own holes is worth more than one where everything happens to fit.
4. **Sensitivity to the cut point is smooth** [measured]: temporal AUPRC runs from 0.81 at the 70 % cut down to 0.74 at the 90 % cut, so the effect does not hang on a single choice of cut. The 90 % cut leaves only 22 frauds in its test set and is the noisiest point of the five, which is why it is the low end rather than a surprise.

**The central result of the attack — and the headline of this document:**

> **Applying the oversampling before separating the test set does not inflate the metric: it destroys it.** AUPRC = 1.0000 on all 20 seeds, with a standard deviation of 0.00001 [measured]. The test half ends up 50 % synthetic positives — against 0.173 % real, because the pre-registered SMOTE ratio is 1:1 with k=5 — and it holds synthetic twins of training rows [by construction]. **Anyone evaluating this way can report perfection with any model at all**, which means a number published under that protocol carries no information about the model that produced it. No value from S3 is ever cited as performance anywhere in this document: it is arithmetic of the protocol, not quality of the model.

**And its quiet complement** [measured]: when SMOTE is applied *correctly*, it contributes +0.0004 over the plain random split (0.8545 against 0.8542) — a difference an order of magnitude smaller than its own run-to-run standard deviation (0.0306). Set that against the 0.0713 the split moves, and in this dataset and this implementation **the split does all the work.**

## 8 · The quantum arm: the negative, and why the handicap does not explain it

The quantum arm had its own pre-registration (`RQ-PREREG-HSBC-003-CUANTICO`, `sha256:e15b1808c03c29a8`), which
fixed the criterion **before the run**: AUPRC on the full test set, 95 %% bootstrap
intervals over 2,000 resamples with seed 42, and **no advantage if the interval overlaps
the classical one or falls below it**. It also stated in advance that **both outcomes are
deliverable**. The one that makes us look bad is the one we got, which is why it is here.

| arm | AUPRC | 95 %% CI |
|---|---|---|
| classical, sealed (`RQ-EXP-HSBC-BASE-001`) | **0.800822** | [0.7054 – 0.8828] |
| quantum fidelity kernel, exact simulation | **0.257453** | [0.1546 – 0.3691] |

**Quantum-advantage crossing: 0** [measured]. The quantum interval falls entirely below.
Both arms were scored on **the same test set, verified by hash** (`88f43ccb6ffcd6ae…`),
with the same resampling. A comparison drawn against a different bootstrap is not a
comparison, so the sealer **aborts** when the two hashes differ [by construction].

### The handicap is real, and we measured it instead of invoking it

The challenge statement requires **stratified** sampling. At a 0.183 % fraud rate, a
support set of 20,000 points leaves **37 positives**, against the 417 the classical arm trained
on. That is a hard, asymmetric disadvantage, and it is the first explanation anyone would
reach for — ourselves included.

**So we handed the classical arm the very same handicap** [measured]: the same 20,000-point
subsample, the same 8 variables, the same 37 frauds.

| control (not pre-registered) | AUPRC | 95 %% CI | vs. the sealed baseline |
|---|---|---|---|
| XGBoost, same sample and same variables | **0.7460** | [0.6429 – 0.8429] | overlaps |
| quantum kernel with all 417 frauds (not stratified) | 0.4887 | [0.3699 – 0.5979] | below |
| RBF, same sample and same variables | 0.1004 | [0.0673 – 0.1575] | below |

XGBoost on the crippled sample reaches **0.7460**, and its interval **overlaps the
baseline's**: stratified sampling cost the classical method something that is not even
detectable. And lifting the handicap from the quantum arm entirely — all 417 frauds —
raises it to 0.4887 and it **still falls below**. The handicap exists and it does not
explain the result.

Without that measurement, «the quantum kernel loses» and «we gave it 37 positives» are
indistinguishable, and publishing the first would be a false report even with a correct
number attached.

### We do not claim to beat the RBF kernel either

On the same data, the same variables and the same classifier, the quantum kernel scores
0.2575 and the RBF 0.1004. That looks like a win until you read the intervals: [0.1546 – 0.3691]
against [0.0673 – 0.1575] — **they touch**. By the same rule we used to deny a quantum advantage over
the baseline, we cannot claim to beat the RBF either [measured]. The rule applies to us
or it is not a rule.

### Exact simulation is what the statement proposes, not a shortfall to excuse

The statement itself says that *«full end-to-end model training or inference on quantum
hardware is not expected nor required»*, and **explicitly encourages** prototyping on
Amazon Braket's managed simulators [from the literature: official statement, §5.3].
Running in exact simulation at US$0 is the route the challenge proposes.

**And one clause deserves to have its scope stated rather than assumed.** The stratified
subsampling requirement sits nested under *«Teams using hardware are encouraged to:»*.
**We did not run on hardware**, so on a plain reading it does not bind us — and we
honoured it anyway, which cost us 37 frauds instead of 417. **We are not forcing the
reading that suits us**: we report the pre-registered arm *with* the constraint (0.2575)
and the control without it (0.4887), and **both fall below the baseline** [measured]. The
conclusion does not depend on how the rule is read.

### Encoding strategy and circuit design

§5.2 asks for a *«description of quantum approach, encoding strategy, and circuit design
choices»*. This is that description.

**From 30 columns to 8 qubits.** The statement notes that feature selection *«is expected
for quantum approaches»*, because encoding hundreds of columns into a circuit is not
practical today. We take the 8 with the largest |Pearson correlation with the label|,
**computed on the training data alone** — looking at the test set would be the very leak
the temporal split exists to prevent: V3, V7, V10, V11, V12, V14, V16, V17 [measured].

**From real number to angle.** Each variable is standardised with the training mean and
sigma, clipped at ±3σ and mapped onto `[0, π]`. The bounds come from training data, not
from the full set. One qubit per variable.

**The feature map.** `ZZFeatureMap` (Havlíček et al., *Nature* 567, 2019) with
`reps = 2` and full pairwise entanglement — the canonical map from the literature, not
one of ours. The phase convention was **not derived from memory: it was checked against
the object qiskit builds** before being used, and that check caught a real defect nothing
else could have seen (§17).

**The circuit, counted rather than described** [measured: built from the parameters the
seal declares and counted with qiskit while this document was assembled]:

| property | value |
|---|---|
| qubits | 8 |
| depth | 67 |
| total gates | 200 (112 cx, 88 u) |
| two-qubit gates | 112 |
| entangled pairs | 28 — requires **all-to-all** connectivity |
| depth transpiled to IBM (rz, sx, x, cx) | 71 |
| depth transpiled to Rigetti (rz, rx, cz) | 206 |

*Measured on the circuit decomposed **once** into elementary gates and transpiled from
there at `optimization_level=1` with a fixed seed. We state the procedure because the
depth depends on it: decomposing twice before transpiling gives a different figure, and
then the number would be a property of how we measured rather than of the circuit.*

**What that means for near-term hardware, said plainly** [by construction]: 112 two-qubit gates over 8 qubits, with **28 pairs demanding all-to-all connectivity**, is an expensive circuit for today's devices. On a limited-connectivity topology the transpiler inserts swaps and the depth grows: you can already see it going from 71 in the friendlier basis to 206 in the other.

**And this is the circuit for *every pair* (transaction, support point) in the kernel**,
not a single circuit: that is where the cost becomes prohibitive. The pre-registration
derives it from Braket's published tariff: **USD 39,018,970** for the full test set [measured],
which is why no hardware was run — under an authorised spend of US$0.

### How we handled class imbalance

§5.3 says imbalance handling *«should be documented»*. We did it four different ways, and
none of them is synthetic oversampling:

- **Loss weighting.** The classical arm uses `scale_pos_weight` = 545.39, the negative-to-positive ratio of the training set. The quantum arm uses `class_weight='balanced'`.
- **Stratified subsampling** for the quantum support set, which **preserves** the fraud
  ratio rather than correcting it: 37 frauds in 20,000 points, the same rate as training.
- **The threshold is chosen on the training data**, never on the test set, and is
  reported with its full confusion matrix rather than as a single number.
- **The headline metric is AUPRC**, which the statement itself recommends for imbalanced
  data, rather than accuracy — which at a 0.183 % fraud rate rewards always saying «no».

**What we deliberately did not do:** no SMOTE, no oversampling in the headline result.
§7 shows why — applied correctly it contributes +0.0004, and applied in the common faulty
order it **saturates the metric at 1.0000 under any seed**.

### Noise and mitigation: what would apply, and why none was needed here

§4.2 values documenting hardware considerations — noise, error mitigation, and comparison
against simulator results. We say it precisely, including the fact that **we ran no
hardware**, which is what makes this section short and honest rather than long and
speculative.

**Our simulation is exact, not noisy.** A statevector has no readout error and no
decoherence, so **there is nothing to mitigate**: applying error mitigation to an exact
simulation would improve nothing, because there is no error to correct. The statement
encourages prototyping on Braket's managed simulators (SV1, TN1, DM1) before going to
hardware; we stopped one step earlier, at local exact simulation, at US$0.

**What would apply if this ran on a device**, in order of importance *for this particular
circuit* [by construction]:

- **Readout error mitigation**, first: the fidelity kernel is estimated from the frequency
  of the `|0…0⟩` outcome, so a readout bias feeds **directly** into every matrix entry.
  It is the error that would hurt us most.
- **Zero-noise extrapolation**, second: with 112 two-qubit gates the accumulated gate error
  dominates, and ZNE is what that class of circuit calls for.
- **And the cheap step nobody should skip**: `DM1`, Braket's density-matrix simulator,
  allows noise-aware prototyping **before** spending on hardware.

**We do not have the simulator-versus-hardware comparison, and we do not imply that we
do.** It is one of the metrics the statement lists as desirable and **ours is empty**:
filling it requires execution, and the pre-registration authorises US$0. What we can say
is the direction: our figure is a **ceiling**, so the noisy version would sit below it —
and we are already below the classical arm.

### Latency and training time

The statement lists both as *good-to-have*. We have them measured [measured]:

| | quantum arm (exact simulation) | classical XGBoost |
|---|---|---|
| total end-to-end run time | 45.2 s | 63.4 s |

**What we do not report, and why.** A per-transaction inference latency: the timing of
that leg stayed in the console and **travels in no artefact**, so copying it here would be
a figure without provenance. It gets measured and sealed, or it does not get reported.

**And even if we had it, it would not be a quantum deployment's latency** [by
construction]. The statevector shortcut exists **because** this is simulated: on a real
device that object does not exist and the pairwise kernel evaluations come back. The
figure above says what it costs to obtain the model this way, not what it would cost on
hardware.

### The model was not inert: it uses all eight variables and still loses

The natural objection to a negative is that the implementation was broken, or ignoring its
inputs. **We measured it.** We shuffled each variable in the test set and measured how far
AUPRC falls, with 10 repetitions per variable so the drop carries an interval rather than
resting on a single run [measured].

| variable | AUPRC drop when shuffled | AUPRC left | 95 %% CI |
|---|---|---|---|
| V17 | 0.2444 | 0.0131 | [0.2223 – 0.2527] |
| V12 | 0.2361 | 0.0213 | [0.2185 – 0.2476] |
| V14 | 0.2301 | 0.0273 | [0.2135 – 0.2460] |
| V11 | 0.2232 | 0.0343 | [0.1872 – 0.2484] |
| V10 | 0.2202 | 0.0373 | [0.1781 – 0.2383] |
| V16 | 0.1999 | 0.0576 | [0.1668 – 0.2265] |
| V3 | 0.1311 | 0.1263 | [0.0814 – 0.1828] |
| V7 | 0.1284 | 0.1290 | [0.0609 – 0.1656] |

**8 of 8 variables have a drop whose interval does not cross zero** [measured].
Shuffling any single one of them collapses AUPRC to the order of the base rate. **The
model is not inert: it extracts signal from every one of its inputs** — and using all of
it, it reaches 0.2575, while a classical model **on the same eight variables and the same
sample** reaches 0.7460.

That **closes off the easiest exit for a sceptical reader** and makes the negative
stronger, not weaker. It also agrees with the local attribution, which is a separate
measurement: per-transaction contributions are near-uniform across variables. None
dominates; all of them contribute.

### The three outputs the statement requires

§5.2 of the statement asks for three artefacts and the sealed arm produced one. They are
in `RQ-EXP-HSBC-Q-002` [measured]:

| output required | what we deliver |
|---|---|
| *Fraud Probability*, `Float [0,1]` | calibrated probability, range [0.0293 – 1.0000] |
| *Binary Prediction*, `Integer {0,1}` | threshold chosen on **train**: 18 positives, precision 0.833, recall 0.200, F1 0.323 |
| *Feature Attribution*, contribution **per prediction** | a 56,962 × 8 matrix: one contribution vector for every transaction in the test set |

**And the count the statement requires verbatim** — *«the total number of samples used for
quantum execution must be explicitly stated in the submission»* — stated in those terms:
stratified support set **20,000** (37 frauds), calibration **20,000**, test **56,962**, **total 96,962
samples** under quantum execution, on **8 qubits** [measured].

> **The calibrated probability is not cosmetic, and we found this ourselves before
> submitting.** Checking whether we met the `Float [0,1]` the statement asks for, we saw
> that our scores were decision-function **margins**, running from -1.3810 to 1.0207. AUPRC and
> AUC do not notice — they are rank-based — but the original artefact's «0.5 threshold»
> applied 0.5 to that scale, and out of it came a precision of 1.000 on **3** predicted
> positives out of 56,962: the ultra-conservative point of an arbitrary scale, not a property
> of the method. It is corrected in erratum `RQ-ERRATA-EXP-HSBC-Q-001`, which **does not rewrite the**
> **original** and leaves the verdict intact. At the threshold chosen on train, precision
> 0.833 and recall 0.200.

### What this measurement does not answer

Nothing about hardware. The arm ran in **exact simulation**, at US$0, without sending a
single circuit to a device: a statevector has no noise, no readout error, no decoherence
and no transpilation error. That makes this number a **ceiling** [by construction]: with
the same feature map, the noisy version cannot beat the exact one. No advantage here
**closes the case**; an advantage here would **not** prove one on hardware. That asymmetry
is why a simulation suffices for a negative and would not suffice for a positive.

## 9 · What nobody will tell you: the recommended dataset cannot answer the question the statement asks

Nobody asked us for this. We hand it over because it is what most helps a bank evaluating
a pilot today, and because we have it **measured and sealed**, not opined.

**ULB, the dataset the statement recommends, holds 48 hours of data in total.** Our
temporal split — the one the pre-registration fixes — leaves **7.7 hours of test set** [measured: `ventana_de_test_dias` = 0.32 in `RQ-EXP-HSBC-Q-001`].

A model evaluated there is fitted to **a snapshot of two days in September 2013**. There
is no way to know whether it generalises to the following week, because **there is no
following week in the data**. That is not a fault of whoever chose the dataset: it is a
property of the dataset.

**And we have something to compare it against.** The track's other benchmark, IEEE-CIS,
we measured with the same rule and sealed in `RQ-EXP-HSBC-IEEE-001`:

| | ULB | IEEE-CIS |
|---|---|---|
| test window | **7.7 h** | **41.88 days** |
| ratio between them | — | **130.9×** more real future |
| fraud rate | 0.183 % | 3.514 % (**19× more frequent**) |
| best AUPRC | 0.800822 | 0.543791 |

**Read those last two rows together.** In IEEE-CIS fraud is **19 times more frequent** — so the problem ought to be easier — **and it is still predicted worse**: 0.5438 against 0.8008 [measured]. A more abundant minority class producing a worse result is exactly what you would expect if ULB's high figure comes from **the short window** rather than from the problem being easy.

**What it means for you, in one sentence:** the number your team reports on ULB **is not
measuring temporal robustness**, because ULB does not contain enough time to measure it.
A benchmark with months of holdout will give you a worse figure — and one closer to what
happens in production, where fraud changes shape between one quarter and the next.

**What we do not claim** [by construction]: that ULB is useless, or that the statement
was wrong to recommend it. It is fine for comparing implementations against each other —
which is what §7 does — and for that the short window does not matter. What it cannot do
is answer «does this survive the passage of time?», and that is the question a deployment
asks. **Two datasets are not a population**: we do not extrapolate beyond these two.

## 10 · Search budget: the guard we adopted against ourselves

From arXiv:2608.15718 [from the literature] we took a guard and wrote it into the protocol, because it
attacks the cheapest way to fool yourself with a quantum result: **selecting the quantum
model from more configurations than the classical one**. In that work, the single
statistically significant advantage they observed **turned out to be fully explained by
the number of configurations searched** — it stopped being a finding and became an
artefact of the procedure.

**Our search budget, measured: one configuration per arm, for both arms** [measured].
There is no `GridSearchCV`, `RandomizedSearchCV`, `optuna` or `param_grid` anywhere in
the instrument: both arms' hyper-parameters are fixed in the published code
(`code/hsbc_harness@a27348cb.py`), and you can check that by reading it. Our negative cannot be
an artefact of the search budget, because there was no search.

**And the reverse, which runs against us and is stated anyway**: the same work reports
that ordinary hyper-parameter choices move performance **considerably more than the
quantum kernel does**. If nobody tuned anything, then our `C = 1`, the `reps = 2` feature
map and the scaling to `[0, π]` are exactly that kind of untuned choice. **We cannot
separate «the method does not help» from «this configuration does not help»**, and a
budget-matched search across both arms is pending work, not a result.

**But that caveat is smaller than we ourselves had made it, and saying so is also part of
the job.** arXiv:2503.05602 shows that optimal bandwidth tuning **moves** quantum kernels **towards**
RBF kernels (§11). If that holds, tuning would not have moved us away from the classical
kernel: it would have pushed us into it. The caveat stands — we are not in that regime,
because we did not tune — but it stops being «maybe another configuration would have won»
and becomes «the direction the literature says tuning moves you is *towards* the
classical kernel, not away from it». **An inflated caveat is another way of not saying
what you know.**

## 11 · What was already known: triangulation on three axes

Our result does not land on empty ground. **None of the three works below replicates our
measurement** — we are supervised ranking with AUPRC on card fraud, and none of them is
that — and saying so matters: presenting them as replications would be the very stitching
this document exists to avoid. What they do is close in from three different sides.

| source | axis | what it measures |
|---|---|---|
| `arXiv:2608.15718` | shares **the domain** (card fraud), changes the task | **unsupervised** clustering, ARI |
| `arXiv:2607.20168` | shares **the shape of the task** (supervised ranking), changes the domain | Chinese A-share returns, Information Coefficient |
| `arXiv:2503.05602` | compares nothing head-to-head: it explains **the cause** | mechanism; reports no effect size |

**`arXiv:2608.15718`** — *Quantum Kernel k-Means for Credit-Card Fraud Detection: A Controlled Benchmark on Real Transaction Data*, M. Faryad, 16 August 2026 [from the literature].

> We find no robust quantum advantage: the sign of the difference depends on register size, all effect sizes are below 0.013 ARI, and the single significant advantage we observe is fully explained by the number of configurations searched.

**`arXiv:2607.20168`** — *Quantum Kernels and the Cross-Section of Stock Returns: Anatomy of a Vanishing Advantage*, J. Shen, 22 July 2026 [from the literature].

> the fidelity kernel is indistinguishable from its RBF control (ΔIC = +0.005, p = 0.42)

**`arXiv:2503.05602`** — *On the similarity of bandwidth-tuned quantum kernels and classical kernels*, R. Flórez-Ablan, M. Roth y J. Schnabel, v3, 28 July 2025 [from the literature].

> optimal bandwidth tuning results in QKs that closely resemble radial basis function (RBF) kernels, leading to a lack of quantum advantage over classical methods

**The two findings that touch us most are not the headlines:**

- **Geometric difference predicts nothing.** `arXiv:2607.20168` reports, verbatim, that *«the geometric
  difference, while large throughout (g ≫ 1), does not predict out-of-sample gains
  (ρ = −0.20)»*. That difference is **the standard diagnostic** used to argue a quantum
  kernel is «different enough» from a classical one to hold an advantage. There it is
  large and **negatively correlated** with the real gain. It is the published
  counterexample to «exponential space ⇒ separates better».
- **A badly built evaluation manufactures the advantage.** The same work documents that
  *«a 60-window evaluation on a universe screened with full-sample information makes the
  same quantum kernel appear dominant on stability criteria»*: information from the
  future leaking in and producing dominance where none exists. **That is the same
  phenomenon we measured** in §7 with balancing applied before the split, which
  saturates the metric at 1.0000 under any seed. Two teams, two markets, one mechanism.

**What we do not claim** [by construction]: that this is a literature review. These are
**three sources that came out of one sweep of ours**, opened and verified sentence by
sentence — none of them entered by relay. Three papers are not a sweep with a denominator,
and that sweep has not been done.

## 12 · What we cannot claim

- **Nothing about quantum models.** This phase is entirely classical: the baseline seal records a quantum-advantage crossing count of `0`, and none was attempted. [by construction]
- **Nothing against the published 0.871 as a number.** Our interval contains it. The evidence for a protocol effect is the intra-implementation Δ, never the subtraction of one implementation from another. [by construction]
- **Nothing outside this dataset.** 48.00 hours, one processor, 2013. Every finding is by construction and intra-dataset. [measured]
- **The margin on criterion C is narrow** — 1.5 % of the threshold — and it travels that way wherever this result goes. [measured]
- **LightGBM remains open** because of our own configuration; the declared hyperparameter search is still pending for both models. [measured]
- **External validity** (REFORMS item 8a): the IEEE-CIS benchmark is waiting on a credential decision, and until then there is no external evidence here. [measured]

## 13 · Feasibility and resources

**Everything already done ran at US$0**, on a laptop, in under a minute per arm [measured:
45.2 s quantum, 63.4 s classical]. There is no hidden infrastructure behind these numbers:
the instrument is a Python file shipped with this package that you can run.

**What taking it to hardware would cost, derived from the published tariff rather than guessed** [measured, in the sealed pre-registration]: **USD 39,018,970** for the full test set, and **USD 3,425** for a bounded 200×50 demonstration on the cheapest backend.

The bulk of that is the **fixed per-task fee**: in a kernel every pair (transaction,
support point) is a separate circuit and repeating shots does not amortise it. Practical
consequence: **cutting shots barely moves the cost; only cutting pairs does** — and
cutting pairs breaks comparability with the sealed test set. Erratum `RQ-ERRATA-PREREG-HSBC-003` bounds that
statement: on expensive-shot backends the share inverts.

**What a next phase would need**, ordered by how much it would change the result:

1. **A hyper-parameter search with matched budgets** across both arms. Today it is one
   configuration per arm (§10) and it is the tightest limit we carry.
2. **A benchmark with months of holdout**, for the reason §9 sets out. IEEE-CIS is
   already measured and sealed; extending it is work, not research.
3. **A bounded hardware demonstration**, only if the goal is characterising noise — not
   improving the result, which in exact simulation is already a ceiling (§8).

## 14 · Expected impact

**Let us be precise about what this improves and what it does not.** The quantum arm does
not deliver performance: it lost, and §8 explains why that is not an artefact of the
setup. A bank adopting this kernel as-is would **detect less fraud**, not more.

**What does change is the quality of the decision about whether to invest:**

- **A quantum fraud-detection pilot already has negative prior evidence**, and until now
  it sat scattered across three works measuring different things (§11). Pooling it with an
  independent measurement of our own saves discovering it yourself.
- **The figure reported on ULB today does not measure temporal robustness** (§9), and that
  affects any team comparing models on that benchmark, quantum or not.
- **The protocol is the most transferable part of all this**: pre-registration anchored
  before the code, an adversarial attack on our own result, matched search budgets, and
  every figure recomputable by a third party. Applied to a bank's internal evaluations, it
  separates a real improvement from a procedural one — which is the error §11 documents in
  the literature and that we measured in our own experiment (§7).

## 15 · Team

**Team:** Rosetta Quantum — **Blue Tuna SpA**, Punta Arenas, Chile (solo
founder-operator). **Lead:** Nicholas Iakl Freundlich · hello@rosettaquantum.com

**Background:** founder & CEO of Sumeria (AI conversation analytics, 9+ years) and founder
of Yu-Track (collections software for financial services). Commercial Engineer and MSc.

**What we bring is not the sell-the-qubit side: it is the consume-the-verdict side** —
shipping systems whose output someone has to trust in order to act. That is why this
document is written so that you **do not have to take our word for any part of it**.

**This is our fourth quantum submission**; Cleveland, E.ON and Airbus went out before it.

**Why this can execute a next phase:** the verification infrastructure it would need **is
not a plan, it is running**. The archive holds **190 sealed artefacts** [measured: counted
at commit `afd6f6920b4e` of the evidence repository, so that you count exactly the same thing —
the archive grows, so a count without a commit cannot be checked], broken down as:

| type | count |
|---|---|
| RUN | 149 |
| PREREG | 17 |
| REPORT | 12 |
| MANIFEST | 4 |
| RECIPE | 4 |
| ERRATA | 3 |
| VERDICT | 1 |

*We say «sealed artefacts» and not «runs» deliberately: **149 are runs** and the rest are
reports, pre-registrations, manifests and errata. A total carrying the wrong label is a
correct figure the reader cannot verify — and if the first one does not reconcile, they
stop checking the rest.*

Each carries its own recomputable hash and an OpenTimestamps receipt, mirrored on two
independent hosts. **This deliverable is 11 of them**, and §17 tells you how to check every
one without asking us for anything.

## 16 · What we are asking for

**Three things, and none of them is a cheque before a conversation.**

1. **An hour with whoever owns the benchmark.** The finding in §9 — that ULB leaves **7.7 hours** of real future and therefore cannot measure temporal robustness — is either useful to you or it is wrong, and both are worth an hour. If it is useful, the comparison against IEEE-CIS is already done and sealed, and it is yours with or without us.
2. **One case you actually care about.** Everything here runs on the datasets your
   statement points to. We would rather **measure** whether your real cases have the
   short-window problem than speculate about it.
3. **A next phase scoped to the measurement, not to a promise.** The same method as this
   one: pre-registered before the instrument exists, sealed, timestamped, and published
   whether it works or not. **This report is what a negative result looks like when it is
   delivered on purpose.**

## 17 · Reproduce this — we exercised it first

```
git clone https://github.com/RosettaQuantum/evidence && cd evidence
bash tools/reproducir_hsbc.sh        # fetches and verifies the data, runs the baseline
                                     # and all four series, verifies everything
                                     # with a denominator
python3 tools/replicar.py verificar --track hsbc   # the verification alone
```

- **The raw scores are deposited** (`scores_*.npz`, addressed by hash), so a third party can rebuild the exact curves rather than trust our summary. **We exercised that as the third party** [measured]: starting from the bytes in origin (`git archive`, no local files), AUPRC, AUC, F1 and all four cells of the confusion matrix recompute within the declared tolerance. That tolerance is `5e-5` and it is written into the baseline seal rather than left implicit: the scores are stored as float32, so “identical” would be the wrong word and we do not use it.
- **The verification battery runs 7 checks per artefact** and each one ends in OK, FAIL or SKIPPED. A check that could not be exercised counts as skipped and appears in the denominator — never as silence. [by construction]
- **Cross-machine determinism** [measured]: the split produces the same test sha256 on the local Mac and in CI, and the baseline point (the 80 % cut) reproduces to the fourth decimal across independent CI runs. Note the distinction: same-hash for the split is bit-for-bit, while the metric is reproducible to a stated decimal — those are two different claims and we do not merge them.
- **Scope of our own exercise** [by construction]: every command in the script was actually run — download and verification locally, the runs in CI (5 dispatches: the baseline and the four series, each listed in its artefact by run id), the battery locally and under mutation. The script as a single unit needs xgboost with OpenMP, so it runs in CI or on a compatible machine.

## 18 · Annexes

### A · REFORMS, item by item

We score ourselves against **REFORMS** — *Reporting Standards for Machine Learning Based Science* (Kapoor et al., *Science Advances* 2024; 32 items in 8 modules) — and publish the score inside the document rather than leaving the audit to the reader. [from the literature]

**Count at build time: 28 full · 4 partial · 0 absent, of 32.** The starting point (20 Aug, before the attack and before this document) was 15 · 8 · 9; it stands as a trajectory and is not overwritten. Closing plan for the 4 partials: a dedicated README (2d), the declared hyperparameter search (5e), and the IEEE-CIS credential decision (8a). Items 3g and 6c are limits of the data itself — they are declared, not “closed”. [measured]

| item | status | where |
|---|---|---|
| 1a | full | population of the claim: §3, declared as intra-dataset |
| 1b | full | why this dataset: pre-registration + §3 |
| 1c | full | why this method: pre-registration 001 |
| 2a | full | dataset with id, md5, sha256 and a sealed manifest |
| 2b | full | code public, archived by hash, sha inside every artefact |
| 2c | full | infrastructure declared (CI, versions in lib_versions) |
| 2d | partial | instructions in §8; a dedicated README is still owed |
| 2e | full | tools/reproducir_hsbc.sh |
| 3a | full | source and collection date (Sept 2013): §3 |
| 3b | full | sampling frame described: §3 |
| 3c | full | dataset justification: pre-registration |
| 3d | full | outcome variable and descriptives: manifest |
| 3e | full | n in the manifest |
| 3f | full | 0 nulls, trivially so per class: §3 |
| 3g | partial | representativeness deliberately NOT claimed — stated as a limit |
| 4a | full | no row excluded: §3 |
| 4b | full | 0 corrupt rows measured; policy declared |
| 4c | full | no transformation of ours: §3 |
| 5a | full | complete configs inside the artefacts |
| 5b | full | model choice justified: pre-registration |
| 5c | full | splits detailed and sealed |
| 5d | full | reported model = the fixed v1 config, no selection among alternatives |
| 5e | partial | hyperparameter search PENDING; LightGBM is open there |
| 5f | full | appropriate baselines justified: pre-registration §4 |
| 6a | full | train-only preprocessing, guards mutation-tested |
| 6b | full | duplicates measured (0); temporal dependence by design |
| 6c | partial | Time/Amount legitimate; the inherited global PCA is declared (annex B) |
| 7a | full | metrics justified and sealed beforehand |
| 7b | full | bootstrap declared (2,000 resamples, fixed seed) |
| 7c | full | Welch and Mann-Whitney agree; criterion pre-sealed |
| 8a | full | second dataset measured and sealed (IEEE-CIS); bounded to two datasets |
| 8b | full | limits and contexts where we do NOT hold the findings: §3 and §7 |

### B · Model info sheet — the eight leakage types of Kapoor & Narayanan

[from the literature: the taxonomy in *Leakage and the reproducibility crisis in ML-based science*, checked against the text of the paper itself]

| type | status in this work |
|---|---|
| L1.1 no test set | ABSENT [by construction]: the split was sealed before any training |
| L1.2 preprocessing over train+test | ABSENT in our own work [measured: we apply no transformation]; **INHERITED from the dataset** [by construction]: the PCA behind V1–V28 was fitted over the complete set before publication — impossible to remove, so we declare it |
| L1.3 feature selection over train+test | ABSENT [by construction]: there is no feature selection |
| L1.4 train-test duplicates | MEASURED: 0 exact duplicates between the halves |
| L2 illegitimate features | Time and Amount are legitimate for this task; V1–V28 are anonymous by design [by construction] |
| L3.1 temporal leakage | THIS IS THE OBJECT OF STUDY: the temporal series avoids it, the random series exhibit it on purpose, and its effect is measured (Δ = 0.0713) |
| L3.2 non-independence of train and test | transactions from the same pair of days; declared as a limit in §3 |
| L3.3 sampling bias | one processor, 48.00 hours: declared, with no reweighting |

### C · Artifacts and seals

| piece | identifier | content hash | commit | anchor |
|---|---|---|---|---|
| design pre-registration | `RQ-PREREG-HSBC-001` | `sha256:b04f214fae845b1c50431d225e6590b0956d8920c24b7c7fa26ed94c58f3f2db` | `72dcbf2` | yes (OTS) |
| attack pre-registration | `RQ-PREREG-HSBC-002-ATAQUE` | `sha256:87c187b48627d52958728365c1e31b08c71a656bfbad14b8f632f89b9fdcf8c4` | `6859ebf` | yes (OTS) |
| quantum-arm pre-registration | `RQ-PREREG-HSBC-003-CUANTICO` | `sha256:e15b1808c03c29a8623eb687c3790c0a00e29cb5ae3ff6848f83d94269c5abb8` | `16ae0b8` | yes (OTS) |
| data manifest | `RQ-DATA-HSBC-ULB-001` | `sha256:71010a1afbf85a0d831bfdc4dcca75754a439125af7fb680132ba3cf71e4503f` | `94cc048` | yes (OTS) |
| baseline run seal | `RQ-EXP-HSBC-BASE-001` | `sha256:2cc73ac7c845a57e575669d8426667ea9cc887de3ccf700a1343db1a6a492e9c` | `a33f723` | yes (OTS) |
| attack run seal | `RQ-EXP-HSBC-ATAQUE-001` | `sha256:12f18492764f1f7108f14d451f8e9620da7918564c158c13302d77ef4d7b3115` | `241c8e5` | yes (OTS) |
| quantum-arm run seal | `RQ-EXP-HSBC-Q-001` | `sha256:436334b41baf7403d474ae820b6492a211873f02f9ff03214ea679307332075f` | `9512fb1` | yes (OTS) |
| §5.2 outputs and attribution seal | `RQ-EXP-HSBC-Q-002` | `sha256:2c52b228bb8b03e5e434d671e7de4439e84adc1daf8d810e66feb54c3a67906f` | `21ec28e` | yes (OTS) |
| IEEE-CIS baseline seal | `RQ-EXP-HSBC-IEEE-001` | `sha256:e6e208d7c4433c0296e82c717a8faaa0646f4e863cefbd5ce889dd37cc07b70d` | `31c699c` | yes (OTS) |
| erratum to the quantum pre-reg | `RQ-ERRATA-PREREG-HSBC-003` | `sha256:3b46354aaf213c160dce99bbb128e8e73597c42c4ab29319bc6ed3a22c53764f` | `e178b48` | yes (OTS) |
| erratum to the quantum-arm run | `RQ-ERRATA-EXP-HSBC-Q-001` | `sha256:db1e783fa69d4e73225bde1dc42b1938284bd0e9d650cd47b9c424c4decb18de` | `707f905` | yes (OTS) |

| result artefact | file |
|---|---|
| baseline | `hsbc_ulb_baseline_lightgbm-xgboost@2072bc53.json` |
| series S1 | `hsbc_ulb_baseline_ataque_S1_n20@ffcf8721.json` |
| series S2 | `hsbc_ulb_baseline_ataque_S2_n20@664575b5.json` |
| series S3 | `hsbc_ulb_baseline_ataque_S3_n20@bf62f223.json` |
| series S4 | `hsbc_ulb_baseline_ataque_S4_n5@25c008b1.json` |

*Seals are verified with `python3 tools/verify_seals.py <file>`. The Bitcoin anchoring (OpenTimestamps) and the three mirrors (GitHub, Codeberg, D1) belong to the notary, a role deliberately separate from the lab that seals.*

---

*Blue Tuna SpA · Punta Arenas, Chile · hello@rosettaquantum.com*
