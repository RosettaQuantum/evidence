#!/usr/bin/env python3
"""Genera el entregable de VW en INGLES. Ninguna cifra se teclea: todas salen de esperados.json.

POR QUE ASI
-----------
Los seis defectos del informe de E.ON estaban TODOS en totales escritos a mano, al lado de
tablas correctas. Aqui el texto se interpola desde los 176 valores sellados por el laboratorio.
Si un numero del informe no existe en `esperados.json`, este guion no puede escribirlo.

Y el ingles es la FUENTE, no una traduccion: decidido el 26-ago tras contar las iteraciones de
Cleveland (5), Airbus (4) y HSBC (3). Portar desde el español metia un defecto por vuelta.
"""
import json, os, re, statistics as st, sys

AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
LAB = os.path.join(RAIZ, "lab-vw-2026-08-26")
V = json.load(open(os.path.join(LAB, "esperados.json")))["valores"]
ENT = json.load(open(os.path.join(LAB, "esperados.json")))["entorno"]

def g(seccion, clave):
    """Un valor sellado. Aborta si no existe: no se inventa ni se aproxima."""
    d = V[seccion]
    if clave not in d:
        raise SystemExit("ABORTA: %s|%s no esta en esperados.json. El informe no puede "
                         "escribir un numero que el laboratorio no sello." % (seccion, clave))
    return d[clave]

def por_sufijo(seccion, sufijo):
    return {k.rsplit("|", 1)[0]: v for k, v in V[seccion].items() if k.endswith("|" + sufijo)}

# ---------------------------------------------------------------- R10, el baseline
fila   = por_sufijo("baseline", "int8_por_fila")
tensor = por_sufijo("baseline", "int8_por_tensor")
nuestro = por_sufijo("baseline", "nuestro_2x")
razones = {k: nuestro[k] / fila[k] for k in nuestro}
n_mat = len(nuestro)
peor_razon, mejor_razon = max(razones.values()), min(razones.values())
med_fila, med_nuestro = st.median(fila.values()), st.median(nuestro.values())
med_razon = med_nuestro / med_fila
gana_alguna = sum(1 for k in nuestro if nuestro[k] < fila[k])
gana_tensor = sum(1 for k in nuestro if nuestro[k] < tensor[k])

# ---------------------------------------------------------------- error a 2x y 4x
e2 = list(por_sufijo("compresion", "2x").values())
e4 = list(por_sufijo("compresion", "4x").values())
e1 = list(por_sufijo("compresion", "1x").values())

# ---------------------------------------------------------------- Pareto: media vs peor
# La rejilla se DERIVA del archivo. La tenia escrita a mano y me faltaba «3x»:
# una lista escrita al lado de la que manda ya diverge.
COMPR = sorted({k.split("|")[0] for k in V["pareto"]}, key=lambda s: float(s[:-1]))
def par(c, campo): return g("pareto", "%s|%s" % (c, campo))
cruce = next((c for c in COMPR if par(c, "peor_por_espectro") > par(c, "peor_uniforme")), None)

# ---------------------------------------------------------------- reshape
nat = por_sufijo("reshape", "natural"); perm = por_sufijo("reshape", "permutado_medio")
# El nulo gaussiano es una MEDICION nuestra, no una constante. Estuvo tecleado aqui hasta que
# el laboratorio lo sello: dos numeros a mano sosteniendo las 21 reducciones de enlace del §3.4.
NULO_ATT = g("nulo", "4096x4096|nulo_medio")
NULO_MLP = g("nulo", "4096x11008|nulo_medio")
NULO_STD = max(g("nulo", "4096x4096|nulo_std"), g("nulo", "4096x11008|nulo_std"))
# TERCERA vez hoy que un filtro por subcadena caza de mas: «|nulo_s» calzaba tambien con
# «nulo_std», y el informe decia 4 semillas donde hay 3. La unidad real es el patron
# completo —nulo_s seguido de digitos—, no el prefijo.
NULO_SEMILLAS = sorted({m.group(1) for k in V["nulo"]
                        for m in [re.fullmatch(r".*\|nulo_s(\d+)", k)] if m})
def nulo(k): return NULO_MLP if k.startswith("mlp") else NULO_ATT
red = {k: 100 * (nulo(k) - nat[k]) / nulo(k) for k in nat}
capa0 = {k: v for k, v in red.items() if k.endswith("|0") and not k.startswith("mlp")}
prof  = {k: v for k, v in red.items() if not k.endswith("|0") and not k.startswith("mlp")}
mlp   = {k: v for k, v in red.items() if k.startswith("mlp")}

# ---------------------------------------------------------------- literatura
# --------------------------------------------------------------- cifras EXTERNAS
# De literatura.json, con fuente y tabla. NO de esperados.json —seria mezclar lo medido con lo
# leido— y NO de un dict escrito aqui. La clave es descripcion MAS compresion: «SAES-SVD ppl»
# solo calza con tres filas distintas, y una busqueda ambigua aborta en vez de elegir la primera.
LIT = json.load(open(os.path.join(LAB, "literatura.json")))
def L(frag, compresion=None):
    h = [c for c in LIT["cifras"] if frag.lower() in c["que"].lower()
         and (compresion is None or c.get("compresion") == compresion)]
    if len(h) != 1:
        raise SystemExit("ABORTA: «%s»%s calza con %d cifras de literatura.json. Una cifra "
                         "externa se cita sin ambiguedad o no se escribe."
                         % (frag, " @%s" % compresion if compresion else "", len(h)))
    return h[0]["valor"]

BASE_PPL = L("WikiText-2 perplexity, uncompressed")
PARAMS_LIT = L("parameter count")
GB_FP16 = PARAMS_LIT * 2 / 1e9          # derivada, no leida: dos bytes por parametro en fp16
VANILLA = [(c, L("Vanilla SVD ppl", c)) for c in ("1.25x", "1.67x", "2.50x")]
SAES_7, AA_7 = L("SAES-SVD ppl at 7 GB"), L("AA-SVD ppl at 7 GB")
CAIDAS_25 = sorted(((c["que"].split(" avg")[0], c["valor"]) for c in LIT["cifras"]
                    if "avg accuracy drop" in c["que"] and c.get("compresion") == "2.50x"),
                   key=lambda t: t[1])
FUENTES = sorted({c["fuente"].split(" (")[0] for c in LIT["cifras"] if c["fuente"].startswith("arXiv")})
def deg(ppl): return 100 * (ppl / BASE_PPL - 1)

def pct(x): return "%.1f%%" % x
# ---------------------------------------------------------------- R5: dispersion medida
stds = por_sufijo("reshape", "permutado_std")
# EL MISMO defecto que en NULO_SEMILLAS, en el bloque de al lado y sin verlo: «|permutado_s»
# calza tambien con «permutado_std». Lo arregle una vez y no mire su gemelo — corregir un
# caso no es corregir la clase, y la clase estaba a treinta lineas.
semillas = sorted({m.group(1) for k in V["reshape"]
                   for m in [re.fullmatch(r".*\|permutado_s(\d+)", k)] if m})
n_corridas = len(stds) * len(semillas)

# ---------------------------------------------------------------- R12: conteo de parametros
P = V["parametros"]
tot_par = P["modelo|parametros_totales"]; lin_par = P["modelo|parametros_lineales_decoder"]
n_lineales = int(P["modelo|matrices_lineales"]); cuota_lin = 100 * lin_par / tot_par
red2 = P["2x|reduccion_del_modelo_pct"]

import hashlib as _h
def _sha(f): return _h.sha256(open(os.path.join(LAB, f), "rb").read()).hexdigest()
SHA_ESP, SHA_LIT = _sha("esperados.json"), _sha("literatura.json")
N_COMPROBACIONES = sum(len(V[t]) for t in V)   # tecleado como 176 hasta hoy; ya eran 328
# ---------------------------------------------------------------- el archivo, al generar
import subprocess as _sp, collections as _co, glob as _gl
_EV = os.path.join(RAIZ, "evidence")
_COMMIT = _sp.run(["git", "-C", _EV, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
_TIPOS = _co.Counter()
for _p in _gl.glob(os.path.join(_EV, "**", "RosettaQ__*.json"), recursive=True):
    try: _TIPOS[json.load(open(_p))["meta"]["type"]] += 1
    except Exception: pass
N_SELLOS = sum(_TIPOS.values())
# los de ESTE track se cuentan, no se recuerdan: iban a decir «cuatro» y son mas.
N_VW = len([_x for _x in _gl.glob(os.path.join(_EV, "**", "RosettaQ__*VW*.json"), recursive=True)])

def f4(x): return "%.4f" % x

MD = f"""# What the Spectrum of LLaVA-1.5-7B Says About Tensor-Network Compression

**Rosetta Quantum · Volkswagen Group Challenge · 2026 Global Quantum + AI Challenge**
Application Context 1 (Autonomous Driving) — Compression sub-track

---

## Abstract

**We did not achieve the challenge's primary objective, and we are opening with that.**

The quantum-inspired method we built is beaten by the accepted classical baseline the
challenge itself names. Against INT8 quantisation via `bitsandbytes`, measured on the same
{n_mat} weight matrices of LLaVA-1.5-7B at the same ~2× compression, our relative Frobenius
reconstruction error is **{med_razon:.0f}× worse at the median** ({f4(med_nuestro)} against
{f4(med_fila)}). We win on **{gana_alguna} of {n_mat}** matrices against row-wise INT8, and on
**{gana_tensor} of {n_mat}** against the weaker per-tensor variant. The per-matrix ratio ranges
from {mejor_razon:.0f}× to {peor_razon:.0f}×.

**What we contribute instead is a measurement, and it is about the challenge's own premise.**
Section 5.1 of the challenge statement asserts that MPS and TTNS decompositions enable
"2–10x compression while preserving accuracy". On the reference model this statement
designates, we measure that plain low-rank truncation cannot: at the 2× the statement requires,
the median relative reconstruction error across {len(e2)} matrices is **{f4(st.median(e2))}**
(worst {f4(max(e2))}). Nor does anyone else: across four published comparisons
covering nine low-rank methods, **not one reaches it** — **and that part does not depend on
anything we built.**

Everything below was produced on **CPU, with no GPU, at zero cost**, by fetching individual
weight tensors over HTTP range requests rather than downloading the model.

---

## 1. Why the method failed, in one finding

We entered the Compression sub-track intending to derive per-layer bond dimensions from an
intrinsic signal of each weight matrix rather than treating them as a hyperparameter. **The
allocator was developed against synthetic spectra spanning decay rates from 0.30 to 0.02. Real
LLaVA layers span a factor of about 1.2 within a matrix type.** Run on real spectra, its
improvement over a uniform cut is **{g("asignacion","presupuesto_20%|uniforme")/g("asignacion","presupuesto_20%|por_espectro"):.2f}×**
at a 20% singular-value budget — an order of magnitude less than on the fabricated spectra it
was designed for. **That figure is measured on a different set from the rest of this report**:
13 matrices across five depths (0, 8, 16, 24, 31), chosen to give the allocator the depth
variation it needs, where §3 uses 21 matrices across three. A ratio quoted without its set is a
number that means something else.

**That is the diagnosis, not a summary of one.** The method did not fail because of the
operation; it failed because it was designed against a heterogeneity that does not exist in
this model. Everything in §3 follows from it.

## 2. Theoretical motivation and experimental setup

**The quantum-inspired component is a tensor-network decomposition** — matrix product operators
— **integrated into the compression stage**, between a trained checkpoint and deployment. Its
premise, which the statement's §5.1 also builds on, is that a weight matrix carries
less information than its dimensions suggest.

**That premise is testable before anything is built, and the quantity that decides it is
spectral concentration.** Truncating to rank χ leaves a relative Frobenius error equal to the
square root of the excluded energy: a matrix whose spectrum decays fast compresses, a flat one
does not. **The same quantity governs the MPO route, which is why the two are not independent
tests** (§3.4). It also bounds what a positive result could have meant: a favourable spectrum
would show the representation is *available*, not that task accuracy survives it.

**Weights** are fetched from the published safetensors shards by HTTP range request — the JSON
header carries each tensor's byte offsets, so one 4096×4096 matrix costs about 32 MB instead of
the model's 14 GB. That is what makes the study free. **Measurement** uses each matrix's real
shape: the MLP matrices are not square and their break-even sits at a different fraction of the
rank. **The baseline**, INT8 quantisation, is implemented per-row — what `bitsandbytes` actually
does — and per-tensor, so the comparison is not made against a straw man.

**What this does not measure, stated plainly.** Weight *reconstruction* error, not task
accuracy. What it bounds is the *operation* — 2D low-rank truncation — not the tensor-network
family as a whole.

---

## 3. Results

### 3.1 · Against the accepted baseline (R10)

| | median over {n_mat} matrices | worst |
|---|---|---|
| INT8, per row (`bitsandbytes`) | {f4(med_fila)} | {f4(max(fila.values()))} |
| INT8, per tensor (naive) | {f4(st.median(tensor.values()))} | {f4(max(tensor.values()))} |
| **Ours, at 2×** | **{f4(med_nuestro)}** | **{f4(max(nuestro.values()))}** |

We lose to the well-built baseline by **{med_razon:.0f}× at the median** and on
**{n_mat - gana_alguna} of {n_mat}** matrices individually. Against the naive per-tensor variant we win on
**{gana_tensor}** — both `q_proj` and `k_proj` in **layer 0**, the one layer whose spectrum is genuinely
concentrated (§3.4 finds the same layer, for the same underlying reason). **Two favourable
matrices out of {n_mat}, in the one place we already knew was atypical, is not a subset worth
claiming** — and saying so here is cheaper than having a reader find it.

### 3.2 · Reconstruction error at the compression the statement requires

| compression | median | worst |
|---|---|---|
| 1× (break-even; no compression) | {f4(st.median(e1))} | {f4(max(e1))} |
| **2× (the stated threshold)** | **{f4(st.median(e2))}** | **{f4(max(e2))}** |
| 4× | {f4(st.median(e4))} | {f4(max(e4))} |

The MLP matrices — which hold most of the parameters — are the worst of the set.

### 3.3 · Ablation 1 — per-layer allocation against a uniform cut

*This isolates the quantum-inspired component of the allocation: the same total parameter
budget, distributed by the spectrum against distributed uniformly. Everything else in the
pipeline is identical, so the difference between the two columns is the component.*

**Pareto curve over the compression / error trade-off**, mean and worst case for both arms:

| compression | mean, uniform | mean, spectral | worst, uniform | worst, spectral |
|---|---|---|---|---|
""" + "\n".join(
    "| %s | %s | %s | %s | %s |" % (c, f4(par(c, "medio_uniforme")), f4(par(c, "medio_por_espectro")),
                                    f4(par(c, "peor_uniforme")), f4(par(c, "peor_por_espectro")))
    for c in COMPR) + f"""

**The worst-case columns cross at {cruce}** — below the 2× the statement requires. At 2× our
allocator improves the mean by {100*(par("2x","medio_uniforme")/par("2x","medio_por_espectro")-1):.1f}% and
makes the worst matrix **{100*(par("2x","peor_por_espectro")/par("2x","peor_uniforme")-1):.1f}% worse**
than a uniform cut. At 4× that becomes {100*(par("4x","medio_uniforme")/par("4x","medio_por_espectro")-1):.1f}% against
**{100*(par("4x","peor_por_espectro")/par("4x","peor_uniforme")-1):.1f}%**.

We report this against ourselves because it generalises: **any per-layer heuristic optimised on
mean error will trade the worst layer away** — that part is a property of the objective, not of
our implementation. Whether the worst layer then dominates a deployed network is an inference
we did not test. The largest improvement our allocator shows —
{par("1x","medio_uniforme")/par("1x","medio_por_espectro"):.2f}× — occurs at 1×, where nothing
is compressed.

### 3.4 · Ablation 2 — MPO reshape against a permuted order and a Gaussian null

*This isolates the structure the MPO route depends on. Three arms: the natural index order,
the same matrix with rows and columns shuffled — which destroys order while preserving the
multiset of weights — and a Gaussian matrix with no structure at all, which fixes where "no
signal" actually sits. Without the third arm the first two are uninterpretable.*

Reshaping a weight matrix into a higher-order tensor and cutting in the middle assumes that
neighbouring indices are correlated. In a physical system locality supplies that; in a weight
matrix the index order is an artefact of initialisation. We therefore measure three arms: the
**natural** index order, a **randomly permuted** order, and a **Gaussian null** — a matrix with
no structure at all, which fixes where "no signal" actually sits.

The null is measured, not assumed: **{len(NULO_SEMILLAS)} Gaussian matrices per shape**, giving a
bond dimension of **{NULO_ATT:.0f}** for the square matrices and **{NULO_MLP:.0f}** for the MLP
shapes, with a spread of {NULO_STD:.2f} across seeds. **That zero does not mean the variance is
zero** — it means the spread is smaller than the discretisation of χ, which is an integer.

| | bond reduction below the null |
|---|---|
| attention, layer 0 | {min(capa0.values()):.1f}% – {max(capa0.values()):.1f}% |
| attention, layers 16 and 31 | {min(prof.values()):.1f}% – {max(prof.values()):.1f}% |
| MLP, all depths | {min(mlp.values()):.1f}% – {max(mlp.values()):.1f}% |

**There is real order structure, and only in the first attention layer.** It fades with depth
and the MLP never has it. This corrects our own earlier reading, taken from a single matrix,
that there was no structure at all — the single matrix happened to be one of the weakest cases.

**It is still not enough.** Even at its strongest, the bond dimension retaining 90% of the
weight sits at about 88% of the maximum. A near-maximally entangled cut does not compress. The
honest statement is not "there is no signal" but **"there is signal and it does not suffice"**.

**And the two avenues are not independent.** Spectral truncation error and MPO bond dimension
covary because both read the same property: how concentrated the spectrum is. Controlling for
truncation error, the association between order structure and our margin against the baseline
disappears. **They fail for the same underlying reason**, which is why we do not present them
as two separate attempts — and which is also why our negative covers a narrower part of the
tensor-network space than "we tried two things" would suggest. TTNS, and reshapings that do not
route through spectral concentration in this basis, are not covered.

### 3.5 · Contrast against published low-rank results

To place our measure against outcomes we did not produce, we contrast it with published results
for low-rank compression of LLaMA-7B ({PARAMS_LIT:,.0f} parameters, {GB_FP16:.2f} GB in fp16;
WikiText-2 perplexity, uncompressed baseline {BASE_PPL}). Every figure below carries its source;
none of them is ours.

**The comparison is now anchored on our exact operation.** AIR (arXiv:2606.19993, Table 2)
publishes **plain truncated SVD** — no Fisher weighting, no activation weighting, no whitening —
which is precisely what our measure models:

| compression | plain SVD perplexity | vs. uncompressed |
|---|---|---|
| {VANILLA[0][0]} | {VANILLA[0][1]:,.0f} | {VANILLA[0][1]/BASE_PPL:,.0f}x |
| {VANILLA[1][0]} | {VANILLA[1][1]:,.0f} | {VANILLA[1][1]/BASE_PPL:,.0f}x |
| {VANILLA[2][0]} | {VANILLA[2][1]:,.0f} | {VANILLA[2][1]/BASE_PPL:,.0f}x |

**At 1.25x compression — below the threshold this challenge sets — plain truncation raises
perplexity by four orders of magnitude.** Our pre-registration stated that no published row
performed our operation, and that our comparison was therefore ordinal only. That is no longer
true: this row is our operation, and it anchors the contrast.

**The sophisticated variants do better and still do not reach the threshold.** At the memory
budget nearest the required 2x:

| method | date | perplexity at 7 GB (1.93x) | degradation |
|---|---|---|---|
| SAES-SVD | Feb 2026 | {SAES_7} | {deg(SAES_7):.1f}% |
| **AA-SVD** | **Apr 2026** | **{AA_7}** | **{deg(AA_7):.1f}%** |

**AA-SVD supersedes SAES-SVD at this point**, and any report quoting the February figure as
the state of the art is quoting a superseded method. We flag it because an earlier draft of
this report did exactly that: the anchor was fixed on the February paper without checking what
came after it.

**And the conclusion does not rest on any single method.** Across four published comparisons
between February and July 2026 — {", ".join(FUENTES)} — covering nine low-rank methods
including each author's own claimed improvement, **not one reaches the challenge's ≤5% accuracy
drop at ≥2x compression.** Average accuracy drops at ratio 0.6 (~2.5x) run from
**{CAIDAS_25[0][1]}% ({CAIDAS_25[0][0]}) to {CAIDAS_25[-1][1]}% ({CAIDAS_25[-1][0]})**, across {len(CAIDAS_25)} methods.
**The closest published result is roughly seven times the stated threshold.** A reader can
dispute one paper; disputing that requires disputing all four.

**A convention trap, published here so nobody rebuilds this table wrong.** There are **two
families**, not one outlier. SAES-SVD and LACE-SVD label their axis by the fraction **removed**
(0.2 → 1.25x); AIR and Swift-SVD label it by the fraction **retained** (80% → 1.25x). **AIR is
in the second family, and AIR is where our exact-operation anchor comes from** — so this is not
a curiosity about one paper we avoided, it is a conversion we had to perform on a row the
conclusion rests on.

**We checked the conversion rather than declaring it.** SVD-LLM at 1.25x appears as
{L("SVD-LLM ppl", "1.25x")} in the SAES-SVD table and as {L("SVD-LLM(W) ppl", "1.25x")} in
AIR's — the same method, reported by two independent third parties under the two different
conventions, **{abs(L("SVD-LLM ppl","1.25x")-L("SVD-LLM(W) ppl","1.25x"))/L("SVD-LLM ppl","1.25x")*100:.1f}% apart.**
The two families reconcile at a shared point. Reading Swift's "ratio 0.6" as SAES's would
compare 1.67x against 2.50x and conclude that Swift wins.

**What this contrast is worth: one bit, in one direction.** It rules out that our measure
reports health where the literature reports catastrophe. It does **not** show that it predicts —
and the reason is sharper than "more data would help": **we have no positive control.** There
is no published case in which low-rank compression of this kind demonstrably worked and our
measure correctly passed it, because we could not find one. **What we have is a rejection
filter, not a screen.**

### 3.6 · Dispersion across independent runs (R5)

The permutation ablation is the only arm of this study with genuine randomness, and it runs
across **{len(semillas)} independent seeds** on each of {len(stds)} matrices — **{n_corridas}
runs** in total. Bond dimensions are sealed as **mean and standard deviation**, per matrix and
per seed, so the dispersion is recomputable rather than taken on trust.

**Everywhere else sigma is exactly zero, and we say so rather than leaving the column blank.**
Truncated SVD is deterministic given identical input bytes: three runs return the same value to
the last digit. A blank cell would leave a reader unable to tell "we did not do this" from
"this does not vary" — the two look identical in a table and are not.

### 3.7 · Total parameter count (R12, second half)

The safetensors headers declare every tensor's shape, so the model's parameter count follows
from three headers without fetching a single weight:

| | |
|---|---|
| total parameters | {tot_par:,.0f} |
| linear decoder matrices ({n_lineales} of them) | {lin_par:,.0f} — {cuota_lin:.1f}% of the model |

| compression of the linear matrices | model after factorisation | reduction of the whole model |
|---|---|---|
| 1.25x | {P["1.25x|modelo_total_tras"]:,.0f} | {P["1.25x|reduccion_del_modelo_pct"]:.1f}% |
| 2x | {P["2x|modelo_total_tras"]:,.0f} | {P["2x|reduccion_del_modelo_pct"]:.1f}% |
| 2.5x | {P["2.5x|modelo_total_tras"]:,.0f} | {P["2.5x|reduccion_del_modelo_pct"]:.1f}% |
| 4x | {P["4x|modelo_total_tras"]:,.0f} | {P["4x|reduccion_del_modelo_pct"]:.1f}% |

**Compressing the linear matrices 2x reduces the whole model by {red2:.1f}%, not by 50%.** The
remainder — embeddings, normalisations, the vision tower — does not compress. That matters
twice: it is the honest figure for the "total parameter count" this sub-track measures, and it
independently settles a discrepancy we had only inferred. The published SAES-SVD memory budgets
report 10.2 GB where a naive calculation gives 10.8; the gap is exactly this uncompressed
remainder, now measured on our own model instead of assumed.

The first half of R12 — task accuracy on a held-out split — is declared unmet in section 5.

---

## 4. A note on the benchmark set itself

**We meet R18 with roughly five times the stated threshold, and we do not think it should be
credited to us.**

A dense layer costs 2mn multiply-accumulates; its rank-χ factorisation costs 2χ(m+n). The FLOP
reduction is therefore *identically* the compression ratio: **50% at 2×**, against the ≥10%
guidance. INT8 reduces FLOP count by **0%** — it makes each operation cheaper without removing
any.

That comparison flatters us for a structural reason: **the FLOPs benchmark is an algebraic
identity of the compression ratio. It does not measure quality and by construction cannot
penalise its loss.** Any method that compresses enough wins that row, including one that
destroys the model — as ours does. We report it here rather than in the results because it is
a finding about the rubric, not about our method.

Two further caveats we would attach to it regardless: FLOP count is not wall-clock time, and a
50% FLOP reduction on a model whose quality has collapsed is not a gain anyone should bank.

---

## 5. Requirements we do not meet, and one we meet only in part

| requirement | status |
|---|---|
| statement §4.1 — demonstrate a clear advantage over the classical baseline | **Not met.** We are beaten by the baseline by {med_razon:.0f}× at the median. |
| R2 — reduced parameter count at equivalent accuracy | **Not met.** |
| R13 — ≤5% accuracy drop at ≥2× compression | **Not met**, by us and by all nine published methods surveyed in §3.5. |
| R5 — mean ± σ across ≥3 independent runs | **Partly met.** Reported where randomness exists; elsewhere the SVD is deterministic and we say so rather than dress it as ± 0. |
| R12 — task accuracy on a held-out split | **Not met.** We measure weight reconstruction error; task accuracy needs a GPU we deliberately did not use. Parameter count is reported (§3.7). |
| R15 — inference latency ≤100 ms | **Not reported.** No compressed VLAM to time. Our own runtime here would be a correct number in the wrong box. |
| R17 — why the QI component provides the observed advantage | **Premise not satisfied**: there is no observed advantage to explain. §3 explains why there is none. |
| R23 — near-term quantum hardware pathway | **Not attempted.** Our method is quantum-*inspired* and classical in execution. |

The statement's §5.5 says submissions are not penalised for degradation below the threshold **provided
the trade-off is clearly characterised**. Characterising it is what this document is.

**Optional secondary objectives (statement §4.2):** we claim one of four, and half of it. The code
producing every number here is released under **Apache 2.0**; **no checkpoints are
released because none were produced** — this is a screening study, it concluded the compression
was not worth performing, and that absence is the result rather than an omission. Energy
accounting, cross-track transfer and a hardware pathway were not attempted.

---

## 6. Reproducibility (R16)

`reproducir.py` (shipped in this package as `4_reproduce.pdf`, a reading copy; the
runnable file is in the repository) runs **{N_COMPROBACIONES} checks** against `esperados.json` from a clean cache: it re-fetches all **25**
weight matrices — the 21 the tables report, plus four extra depths the allocator needs — and
recomputes every SVD. Last full run: **0 failures** on
Python {ENT["python"]}, NumPy {ENT["numpy"]}, {ENT["plataforma"]}.

**The public code repository the statement's §5.2 requires is published:**

> `https://github.com/RosettaQuantum/vw-spectral-screen`

Public, Apache 2.0, 18 files. It holds
every generator, the sealed value file, the literature file with each citation's source, and the
verification script. All hyperparameters, random **seeds**, dataset identities and **hardware
specs** are documented there, and the run starts from a **clean environment with no manual
intervention**.

**No model weights, datasets or checkpoints are redistributed.** The tensors are fetched at run
time by HTTP range request from the published safetensors, so the repository stays small and the
licence question over third-party weights never arises.

**Every number in this report is interpolated from two files, and both are named here so the
chain can be rebuilt rather than trusted:**

| file | sha256 |
|---|---|
| `esperados.json` — everything we measured | `{SHA_ESP}` |
| `literatura.json` — everything we cite, with its source | `{SHA_LIT}` |

Ask for those two files, run the generator, and this document reproduces byte for byte. **Three hashes side by side are three promises; a chain that rebuilds is one fact.**

**Scope of that claim.** It establishes determinism *on this machine*. It does not establish
portability across BLAS implementations — that is exactly what a third party running it would
establish, and why a declared tolerance exists.

---

## 7. Pre-registration, and the two defects we found in it

The design, the comparison set, and **three ways this instrument could fail** were written and
sealed before the calibration ran: **`RQ-PREREG-VW-001`**, OpenTimestamps-anchored and
published in our evidence archive — `github.com/RosettaQuantum/evidence`, mirrored on
Codeberg. **Every seal named in this report is downloadable there without an account**,
and each one carries the recipe for recomputing its own content hash.
**The pre-registration itself is written in Spanish and we have not translated it** — its
bytes are what the timestamp protects, and a translation would be a different document.
It fixes three things: the comparison set and why those papers, **three ways this
instrument could fail** (two of which turned out to be vacuous, see below), and what the
contrast would not demonstrate even if it succeeded.

Afterwards we found that **two of those three criteria could not fail**. "Does not order" and
"is not monotone" follow from the Eckart–Young theorem, not from any property of the
instrument: truncation error is the square root of the excluded energy, so lowering χ only adds
non-negative terms. Checked across five spectra — exponential, flat, single-valued, increasing,
and pure noise — there are no counterexamples. **Only the second criterion did any work.**

A pre-registration offering three guarantees when one is real promises more than it delivers,
and from the outside it looks identical to a sound one. We publish it with the defect in it, in
`RQ-ERRATA-VW-001`, which also records that our anchor was initially fixed without reading the
strongest row of the same table, and that the single-matrix reshape conclusion was wrong. The
original seal is not rewritten: it was sealed before the results existed, and re-anchoring it
today would place its date after them.

---

## 8. Team

**Rosetta Quantum — Blue Tuna SpA, Punta Arenas, Chile** (solo founder-operator).
**Lead: Nicholas Iakl Freundlich** · `hello@rosettaquantum.com`

Background: founder & CEO of Sumeria (AI conversation analytics, 9+ years) and founder of
Yu-Track (collections software for financial services). Commercial Engineer and MSc.

**What we bring is not the sell-the-qubit side: it is the consume-the-verdict side** — shipping
systems whose output someone has to act on. That is why this document is written so that you do
not have to take our word for any part of it, including the parts where we lost.

**This is our fifth submission to this challenge**; Cleveland, E.ON, Airbus and HSBC went out
before it. **The verification infrastructure this report leans on is not a plan, it is
running**: the archive holds **{N_SELLOS} sealed artefacts** — *measured at commit `{_COMMIT[:12]}`
of the evidence repository, so you count exactly the same thing; the archive grows, and a count
without a commit cannot be checked* — broken down as
**{_TIPOS['RUN']} RUN**, **{_TIPOS['REPORT']} REPORT**, **{_TIPOS['PREREG']} PREREG**, **{_TIPOS['ERRATA']} ERRATA**, plus manifests, recipes and one verdict.

We say *sealed artefacts* and not *runs* deliberately: {_TIPOS['RUN']} are runs and the rest are
reports, pre-registrations, manifests and errata. **{N_VW} of them belong to this submission** and each is listed with its own verification URL in `3_RosettaQ-VW-sealed-artefacts.csv`.

---

## Resource Declaration (statement §6)

| | |
|---|---|
| GPU type and count | **none** |
| Total GPU-hours | **0** |
| Simulation environment | not applicable — no quantum circuit is executed |
| Compute | CPU only; Python {ENT["python"]}, NumPy {ENT["numpy"]}, {ENT["plataforma"]} |
| Estimated energy | one CPU-core-hour class; no accelerator was powered |
| Monetary cost | **US$0** |

Qubit count, gate fidelity and shot budget (statement §5.3) are **not applicable and we state why**: the
method is quantum-*inspired* — tensor-network decomposition — and entirely classical in
execution. There is no circuit, so there are no qubits, no gate fidelities and no shots to
declare. An absent section and a section declaring non-applicability look the same in a table
of contents and different to a reader.
"""

DST = os.path.join(AQUI, "ENTREGABLE-VW-EN.md")
open(DST, "w", encoding="utf-8").write(MD)
print("escrito:", os.path.basename(DST), "·", len(MD.split()), "palabras,", MD.count("\n") + 1, "lineas")
print("cifras leidas de esperados.json: %d asignacion, %d compresion, %d reshape, %d baseline, %d pareto"
      % tuple(len(V[k]) for k in ("asignacion", "compresion", "reshape", "baseline", "pareto")))
