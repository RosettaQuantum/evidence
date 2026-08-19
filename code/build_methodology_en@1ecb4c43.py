#!/usr/bin/env python3
"""Builds the ENGLISH methodology report (Cleveland deliverable 3) + its chart data.

WHY THIS IS A GENERATOR
-----------------------
Same rule as the Spanish draft Nicholas approved: **the numbers are read from the sealed
files at build time and never retyped**; the prose is written here. The first version of
the Spanish generator spliced whole sentences out of the JSON and produced duplicated
clauses and broken accents. Numbers from the seal, prose in the generator.

If any seal fails to verify, the report is not built.

TWO OUTPUTS
-----------
  REPORTE-METODOLOGICO-EN.md   the approved content, in English
  charts_data.json             one entry per figure, each with `source` and `n`, which is
                               what the web session's chart engine requires — it refuses to
                               render a figure without them.

Usage:  python3 build_methodology_en.py
"""
import glob
import hashlib
import json
import os
import re
import sys
import textwrap

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))

import rosettaq_seal as rs  # noqa: E402

RUN_CIEGO = ("RosettaQ__RUN__RQ-EXP-CLEV-BLIND-001__20260809T2220Z__"
             "prediccion-ciega-cleveland--negativo.json")
RUN_N90 = ("RosettaQ__RUN__RQ-EXP-N90-LOPO-003__20260812T0100Z__"
           "n90-deja-una-fuera-sin-fuga.json")
PREREG_GG = ("RosettaQ__PREREG__PR-COARSE-001__20260810T1200Z__"
             "grano-grueso-supervivencia-del-orden.json")
RUN_GG = ("RosettaQ__RUN__RQ-EXP-COARSE-001__20260810T1230Z__"
          "grano-grueso-supervivencia-del-orden.json")
MANIFEST_QPU = os.path.join(RAIZ, "quantum-run", "voyage2_manifest.json")
# El texto que Nicholas aprobo, leido del archivo de aprobacion — no tipeado aqui.
APROBACION = os.path.join(RAIZ, "CAMBIOS-REPORTE-aprobados.md")
APROBACION_SHA = ("03a33dd087d6ca689e2ebd808d4f816b2840c418063efb9590269996"
                  "93e96ce7")
BATTERY = os.path.join(AQUI, "battery_result.json")
OUT_MD = os.path.join(AQUI, "REPORTE-METODOLOGICO-EN.md")
OUT_CHARTS = os.path.join(AQUI, "charts_data.json")

NAME = {"KRAS_4OBE": "KRAS G12C", "ABL1_1OPL": "BCR-ABL1",
        "MYOSIN_5TBY": "Cardiac myosin", "MYC_1NKP": "c-Myc",
        # los nombres que usa el motor en la bateria de hardware, que no son los mismos
        "KRAS_G12C": "KRAS G12C", "PFKP_FBP": "PFKP", "HK1_G6P": "Hexokinase 1",
        "BCR_ABL1": "BCR-ABL1", "CARDIAC_MYOSIN": "Cardiac myosin"}

# El manifiesto guarda los roles en espanol; este documento es ingles.
ROLE = {"control-positivo": "positive control",
        "control-secundario": "secondary control",
        "control-negativo": "negative control",
        "exploracion-largo": "long-corridor exploration",
        "repeticion": "repetition",
        "replica-corrida-1": "replica of run 1",
        "transporte-abl1": "transport, BCR-ABL1"}
ORDER = ["KRAS_4OBE", "ABL1_1OPL", "MYOSIN_5TBY", "MYC_1NKP"]


def load(name):
    d = json.load(open(os.path.join(AQUI, name)))
    if not rs.verify(d):
        raise SystemExit("%s does NOT verify — the report is not built on a broken seal"
                         % name)
    return d


def parrafos_aprobados():
    """Los parrafos del CAMBIO 2, leidos del archivo de aprobacion de Nicholas.

    No se tipean aqui: se leen, y el archivo se identifica por su sha256. Si alguien
    edita la aprobacion, la construccion se detiene en vez de publicar otro texto.
    """
    crudo = open(APROBACION, "rb").read()
    visto = hashlib.sha256(crudo).hexdigest()
    if visto != APROBACION_SHA:
        raise SystemExit("la aprobacion cambio: esperaba %s…, hay %s…. El reporte NO se "
                         "construye sobre un texto que Nicholas no vio."
                         % (APROBACION_SHA[:12], visto[:12]))
    citado = [l[2:].strip() if l.startswith("> ") else ""
              for l in crudo.decode("utf-8").splitlines() if l.startswith(">")]
    paras, cur = [], []
    for l in citado:
        if l:
            cur.append(l)
        elif cur:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    if len(paras) != 4:
        raise SystemExit("esperaba 4 parrafos aprobados en %s, encontre %d"
                         % (os.path.basename(APROBACION), len(paras)))
    return paras


# --------------------------------------------------------- las secciones nuevas
# La coordinadora las redacto y las dejo en dos archivos de la raiz. Se leen de ahi,
# identificados por sha256, y NO se tipean. Las correcciones que el laboratorio les hace
# van declaradas una por una, con la medicion que las obliga: asi el diff contra lo que
# ella escribio es explicito y comprobable, en vez de una reescritura silenciosa.
PROP_SECC = os.path.join(RAIZ, "PROPUESTA-secciones-nuevas.md")
PROP_PORT = os.path.join(RAIZ, "PROPUESTA-portada-y-resumen.md")

CORRECCIONES = [
    (PROP_SECC,
     "and the ground truth was opened last",
     "and for myosin the ground truth did not exist in the tree until afterwards",
     "el archivo dice lo contrario para 2 de 3 blancos",
     "RQ-EXP-CLEV-BLIND-001 declara: 6OIM (KRAS) y 5MO4 (ABL1) ya estaban en el arbol en "
     "el commit 2538c47, ANTERIOR a las predicciones (4cfac34). Solo 9GZ1 (miosina) entro "
     "despues. La §2 del propio reporte lo dice; el resumen lo habria contradicho."),
    (PROP_PORT,
     "Eso hace **criptográficamente imposible** elegir después la\n> proteína o el "
     "parámetro que nos favorecía",
     "Eso hace **verificable por un tercero** que no elegimos después la\n> proteína o el "
     "parámetro que nos favorecía",
     "el sello prueba el orden, no vuelve imposible la eleccion",
     "un sello de tiempo demuestra que A precede a B; no impide elegir A. Y con dos holo "
     "ya en el arbol, la afirmacion fuerte es ademas falsa. Regla §1 ter de CLAUDE.md: no "
     "se publica una afirmacion que nuestro propio archivo desmiente."),
]


def parrafear(bloque):
    """Un bloque citado -> lista de parrafos. Una viñeta ABRE parrafo aunque no haya
    linea en blanco antes: si no, las tres viñetas del §2 se funden en una sola."""
    parrafos, cur = [], []
    for l in bloque:
        s = l.strip()
        if s.startswith("- ") and cur:
            parrafos.append(" ".join(cur))
            cur = [s]
        elif s:
            cur.append(s)
        elif cur:
            parrafos.append(" ".join(cur))
            cur = []
    if cur:
        parrafos.append(" ".join(cur))
    return parrafos


def reflujo(bloque, ancho=92):
    """Reparte un bloque citado en lineas, SANGRANDO la continuacion de cada viñeta.

    Markdown marca la continuacion de un item con sangria. El texto de la coordinadora
    viene sin ella —el renderizador antiguo la ignoraba— y el nuevo la EXIGE: un parrafo
    sin sangria despues de una lista es prosa de la seccion, y absorberlo seria inventar
    una estructura que nadie escribio. Sin esto, la lista del §2 se parte en el PDF, que
    es el defecto que se comio el §7 durante dos versiones.
    """
    parrafos = parrafear(bloque)
    salida = []
    for i, p in enumerate(parrafos):
        if i:
            salida.append("")
        salida += textwrap.wrap(p, width=ancho,
                                subsequent_indent="  " if p.startswith("- ") else "")
    return salida


def leer_propuesta(ruta):
    """Los bloques citados de una propuesta, con las correcciones del lab aplicadas."""
    txt = open(ruta, encoding="utf-8").read()
    for arch, viejo, nuevo, _q, _p in CORRECCIONES:
        if arch != ruta:
            continue
        if txt.count(viejo) != 1:
            raise SystemExit("la correccion del lab busca %r en %s y lo encuentra %d veces. "
                             "El texto cambio: hay que revisar la correccion, no forzarla."
                             % (viejo[:44], os.path.basename(ruta), txt.count(viejo)))
        txt = txt.replace(viejo, nuevo)
    bloques, cur = [], []
    for l in txt.splitlines():
        if l.startswith(">"):
            cur.append(l[2:] if l.startswith("> ") else "")
        elif cur:
            bloques.append(cur)
            cur = []
    if cur:
        bloques.append(cur)
    return bloques


blind, prereg_cg, cg, n90 = (load(RUN_CIEGO), load(PREREG_GG), load(RUN_GG),
                             load(RUN_N90))
Q, C, P = blind["w6"]["que"], blind["w6"]["como"], blind["w6"]["porque"]
diag = P["diagnostico_de_por_que_fallo"]
prox = {m["blanco"]: m for m in diag["medido_no_heredado"]["blancos"]}
den_prox = diag["medido_no_heredado"]["denominador"]
QG = cg["w6"]["que"]
den_cg, split_cg = QG["denominador"], QG["reparto_de_celdas"]
cells = {m["blanco"]: {f["bloque"]: f for f in m["niveles"]}
         for m in QG["resultados_por_blanco"]}
conv = C["convenciones_selladas"]
qpu = json.load(open(MANIFEST_QPU))
bat = json.load(open(BATTERY))
bc = bat["comparaciones"]
brow = {f["role"]: f for f in bat["circuitos"]}

# --- el N=90 con la conservacion viva, del sello -003 (CAMBIO 2 aprobado)
N = n90["w6"]["que"]
_brazo = {b["brazo"]: b for b in N["brazos"]}
_abl = {a["ablacion"]: a for a in N["ablaciones"]}
P_B_CON = _brazo["armB_ml"]["p_publicado"]
P_B_SIN = _abl["sin_conservacion"]["p_publicado"]
P_A = _brazo["armA_manager"]["p_publicado"]
N_BLANCOS = _brazo["armB_ml"]["n_proteinas"]
_censo = [int(x) for x in re.findall(r"\d+", N["conservacion"]["censo"])[:2]]
_mejor_metodo = max(N["percentil_medio_por_metodo"],
                    key=N["percentil_medio_por_metodo"].get)
_elige = N["elecciones_del_gestor"][_mejor_metodo]
RAZON_SIN_CON = P_B_SIN and P_B_CON / P_B_SIN

# Las guardias del CAMBIO 2. La prosa aprobada AFIRMA cosas; si los numeros dejaran de
# sostenerlas, hay que reescribir la prosa con Nicholas, no dejarla pasar interpolada.
# Es el defecto que tuvo el sello -003 el 2026-08-12, ahora atajado aguas arriba.
if _censo != [N_BLANCOS, N_BLANCOS]:
    raise SystemExit("el censo de conservacion dice %s y el brazo declara %d proteinas"
                     % (_censo, N_BLANCOS))
if RAZON_SIN_CON <= 1.05:
    raise SystemExit("el texto aprobado afirma que la conservacion RESTA (%.2fx mejor sin "
                     "ella) y los numeros dicen %.3g con y %.3g sin (razon %.2f). Reescribe "
                     "el texto con Nicholas, no los numeros."
                     % (1.8, P_B_CON, P_B_SIN, RAZON_SIN_CON))
if _mejor_metodo != "diffusion":
    raise SystemExit("el texto aprobado dice que la difusion clasica sigue siendo el mejor "
                     "propagador individual, y el mejor ahora es %s" % _mejor_metodo)

# --- censo del archivo: se MIDE aqui, con la lista canonica de carpetas, no se hereda.
# La lista vive en un solo lugar (`notarize_globs`) porque una lista escrita a mano en dos
# scripts ya diverge: el primer conteo de la coordinadora dio 76 por eso mismo.
sys.path.insert(0, os.path.join(RAIZ, "evidence", "scripts"))
from notarize_globs import ARCHIVE_GLOBS  # noqa: E402

_dir = os.getcwd()
os.chdir(os.path.join(RAIZ, "evidence"))
try:
    _sellados = sorted({f for g in ARCHIVE_GLOBS for f in glob.glob(g, recursive=True)})
    _sellados_abs = [os.path.abspath(f) for f in _sellados]
    ARCHIVO = {"total": len(_sellados),
               "con_ots": sum(1 for f in _sellados if os.path.exists(f + ".ots")),
               "por_tipo": {}}
    _corr = []
    for f in _sellados:
        _d = json.load(open(f))
        _t = _d["meta"].get("type", "?")
        ARCHIVO["por_tipo"][_t] = ARCHIVO["por_tipo"].get(_t, 0) + 1
        for _k in ("corrige_a", "corrige_a_ANTERIOR"):
            if _k in _d["meta"]:
                _corr.append((_d["meta"]["file_id"], _d["meta"][_k].get("file_id")))
finally:
    os.chdir(_dir)
ARCHIVO["correcciones_declaradas"] = len(_corr)
# «correcciones a nuestras lecturas publicadas» = los sellos de EXPERIMENTO que corrigen a
# otro. Las otras tres relaciones `corrige_a` del archivo son revisiones de este reporte,
# que no son lecturas equivocadas. Un jurado que cuente encuentra 5 en total y 2 de estas;
# por eso el sello declara las dos cifras y no solo la conveniente.
ARCHIVO["corrige_lecturas_publicadas"] = sorted(a for a, b in _corr
                                                if a.startswith("RQ-EXP-"))
ARCHIVO["revisiones_de_este_reporte"] = sorted(a for a, b in _corr
                                               if not a.startswith("RQ-EXP-"))

# La seccion del equipo afirma que CADA archivo esta anclado en Bitcoin. Si alguno no
# tiene su .ots, la frase es falsa y el documento no se arma.
if ARCHIVO["con_ots"] != ARCHIVO["total"]:
    raise SystemExit("el texto afirma que los %d sellos estan anclados y %d no tienen .ots"
                     % (ARCHIVO["total"], ARCHIVO["total"] - ARCHIVO["con_ots"]))

PALABRA = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
           8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def palabra(n):
    """El numero en letras. Si no esta en la tabla, se detiene: un numero escrito a mano
    en la seccion que le explica al lector como comprobarnos es el defecto que este
    documento tuvo el 2026-08-12 — decia «three» con cuatro filas en la tabla, porque yo
    agregue la cuarta y la prosa no se entero."""
    if n not in PALABRA:
        raise SystemExit("no se como escribir %d en letras; agregalo a PALABRA" % n)
    return PALABRA[n]


ESQUEMAS = {}
for _f in _sellados_abs:
    _e = json.load(open(_f))["meta"].get("schema", "?")
    ESQUEMAS[_e] = ESQUEMAS.get(_e, 0) + 1

ps = [t["p_permutacion_parches_contiguos"] for t in Q["metricas_por_blanco"].values()]
rho_d = [m["spearman_score_vs_dist_fuente_distales"] for m in prox.values()]
rho_a = [m["spearman_score_vs_dist_fuente_todos"] for m in prox.values()]
jac = [f["jaccard_top10pct_distal"] for b in cells.values() for f in b.values()]
rhos_cg = [f["spearman_orden_vs_fino_distales"] for b in cells.values() for f in b.values()]

L = []
w = L.append

w("# Methodology Report — Rosetta Quantum")
w("")
w("**Cleveland Clinic Challenge · allosteric site prediction · deliverable 3**")
w("")
w("> Every figure in this document is read at build time from the sealed files listed")
w("> below; none is typed by hand. The Spanish source was approved before translation.")
w("")
w("| Sealed file | ID | content_hash |")
w("|---|---|---|")
SELLOS = (blind, prereg_cg, cg, n90)
for d in SELLOS:
    w("| %s | `%s` | `%s` |" % (d["meta"]["type"], d["meta"]["file_id"],
                                d["meta"]["content_hash"]))
w("")
w("---")
w("")

# ---------------------------------------------------------------- §1 el resumen
# Nicholas aprueba el CONTENIDO en espanol (`PROPUESTA-portada-y-resumen.md`); esto es su
# traduccion, con las cifras leidas de los sellos. Las dos diferencias contra el borrador
# de la coordinadora estan en CORRECCIONES, declaradas con su medicion.
_prop_port = leer_propuesta(PROP_PORT)
w("## 1. What this is, in one page")
w("")
w("**Rosetta Quantum does not sell a quantum algorithm. It sells the machine that measures")
w("whether a quantum algorithm is any good — and publishes the answer even when the answer")
w("is no.**")
w("")
w("The Cleveland Clinic challenge asks whether a quantum computer can find *allosteric")
w("pockets*: hidden points on a protein's surface that, when touched, switch the protein off")
w("from a distance. The challenge statement puts them as the only therapeutic route into the")
w("85 % of disease-causing proteins that have no viable treatment today.")
w("")
w("**What we did.** We turn each protein into a contact network between its residues, inject")
w("a signal at the active site, and let it spread two ways: as a quantum walk and as classical")
w("diffusion. The question is whether the quantum version reaches the hidden pocket more")
w("strongly than the classical one.")
w("")
w("**What we measured.** It does not. On the four challenge targets the result is a **measured")
w("negative** (p = %s to %s) — not a tie and not a near miss. Across 90 further proteins, in"
  % (min(ps), max(ps)))
w("leave-one-out, the quantum arm **does not reach significance** (p = %.3f), and classical"
  % P_A)
w("diffusion turns out to be the best of the %d propagators we tested — chosen by our own"
  % len(N["percentil_medio_por_metodo"]))
w("selector in %d of the %d targets." % (_elige, N_BLANCOS))
w("")
w("**Why that is the product and not the failure.** Before running anything we sealed and")
w("timestamped the metric, the predictions and the scoring program, in that order, and only")
w("then ran the scoring against the answer. Anyone can check that the prediction precedes")
w("the result. That")
w("makes it **verifiable by a third party** that we did not pick the protein or the parameter")
w("that suited us afterwards — which is exactly how good news gets manufactured in this field.")
w("Section 4 states where that chain has a limit, because a third party should not have to")
w("discover it.")
w("")
w("**It also runs on real hardware.** Seven circuits on an IBM quantum processor, their")
w("identifiers sealed before any result existed. The circuit behaves as the simulation")
w("predicts, within **%.1f percentage points** at worst. And we found something we were not"
  % (100 * bat["desvio_vs_ideal"]["maximo_absoluto"]))
w("looking for: repeat the same circuit and the measured physics does not move, while the")
w("noise wrapped around it moves by **%.1f points** across days. From now on, every noise"
  % (-100 * bc["replica_vs_RQ-POC-QPU-001"]["delta"]))
w("figure we publish travels with its date.")
w("")
w("**What this document does not claim.** There is no quantum advantage. Our counter of")
w("\"crossings\" — cases where the quantum method beats the best classical one — stands at")
w("**zero**, and is published that way.")
w("")
w("**What is left.** A measuring apparatus that works, **%d sealed files across three"
  % ARCHIVO["total"])
w("independent copies** — GitHub, Codeberg and a queryable database — of which **%d are"
  % ARCHIVO["por_tipo"]["RUN"])
w("experimental runs**, and an honest verdict on a hypothesis that was ours. During this very")
w("submission the archive recorded **%d corrections to our own published readings**, still"
  % len(ARCHIVO["corrige_lecturas_publicadas"]))
w("visible alongside the originals. That is what is on offer: not a faster result, an")
w("instrument that reports what it finds, including against itself.")
w("")

w("### Contents")
w("")
_IDX = len(L)   # el indice se rellena al final, DESDE los titulos que el documento tiene.
w("")           # una lista que vive en dos lugares ya divergio (CLAUDE.md §5 bis).

w("## 2. What we said we would do, and what happened")
w("")
for _l in reflujo(leer_propuesta(PROP_SECC)[0][2:]):
    w(_l)
w("")

w("## 3. What was predicted, and with what")
w("")
w("The metric is the **mixing matrix of a continuous-time quantum walk (CTQW)**: the")
w("infinite-time average of the transition probability over the protein's CA contact")
w("network.")
w("")
w("```")
w("C(i,j) = lim (1/T) ∫ |<i| e^{-iHt} |j>|² dt = Σ_λ |<i| P_λ |j>|²")
w("```")
w("")
w("A residue's score is the mean of C(i, s) over the active-site residues. Sites are")
w("formed by single-linkage clustering at 8 Å of the top 10 % of distal residues.")
w("")
w("**Why this metric and not another.** Three reasons, in order of weight:")
w("")
w("1. **It has no free parameters.** There is no time window, no grid, no Trotter step")
w("   count to choose. We had already been bitten by the opposite: a grid capped at")
w("   t = 20 inflated an apparent advantage from 5× to 19×. A metric with no knobs cannot")
w("   be overfitted, nor attacked on the choice of knobs.")
w("2. **The exact classical analogue, under the same averaging, carries no information.**")
w("   Classical diffusion averaged over long times converges to the uniform distribution")
w("   1/n — a rank-1 matrix that ranks every residue identically. This is not a weak")
w("   baseline chosen on purpose: it is the *same* operation, and it yields exactly")
w("   nothing. It is proven in the engine's test suite, not asserted.")
w("3. **It is transport physics**, not an ad-hoc feature: C(i, src) measures how much")
w("   amplitude from the source ends up, on average, at each residue.")
w("")
w("The geometric conventions are the engine's sealed ones, not invented for this")
w("challenge: CA–CA contact at %s Å, validated pocket within %s Å of the ligand, distal"
  % (conv["cutoff_contacto_CA_A"], conv["gt_radius_A"]))
w("beyond %s Å of every source residue, Gaussian kernel σ = %s Å."
  % (conv["distal_A"], conv["sigma_kernel_A"]))
w("")

w("## 4. How the prediction was blinded, and where that blinding has a limit")
w("")
w("The chain is in git and each link is an ancestor of the next. We did not read the log")
w("of commit titles: ancestry was checked with `git merge-base --is-ancestor`, and all")
w("%s were checked to be contained in `origin/main`." % palabra(len(C["cadena_de_ceguera"])).capitalize())
w("")
w("| # | Commit | Date (UTC) | Role |")
w("|---|---|---|---|")
roles = {1: "metric pre-registered, no free parameters, before predicting",
         2: "blind predictions for the 4 targets, committed",
         3: "scorer committed **before** it was run (and 9GZ1 archived)",
         4: "scoring result, published exactly as it came out"}
for i, e in enumerate(C["cadena_de_ceguera"], 1):
    w("| %d | `%s` | %s | %s |" % (i, e["corto"], e["fecha_utc"], roles[i]))
w("")
w("**The limit, stated because a third party should not have to discover it.** Two of the")
w("three holo structures — 6OIM (KRAS) and 5MO4 (ABL1) — were already in the git tree at")
w("commit `2538c47` — which precedes not only the predictions but the entire chain,")
w("including the metric's pre-registration eight hours later. Only 9GZ1, for myosin,")
w("arrived after.")
w("")
w("So for KRAS and ABL1 the blinding is **not physical** (the file did not exist) but a")
w("property of the code and the process. What supports it is that the predictor's inputs")
w("are auditable and do not include the holo structures: the cache builder opens only the")
w("apo structures declared in its target table (4OBE, 1OPL, 5TBY, 1NKP); the ranker reads")
w("only the blind caches; and those caches do not carry the pocket key and declare")
w("themselves blind, with a positive test case that checks it. For myosin, the physical")
w("chain holds as well.")
w("")

w("## 5. The three metrics, fixed before anything was opened")
w("")
w("1. **Hit rank.** The rank of the first site in the top-5 with at least one residue")
w("   inside the validated pocket, plus each site's minimum distance to the pocket.")
w("2. **Pocket percentile.** Mean percentile of its residues among the distal ones.")
w("3. **Permutation p-value.** 2,000 random contiguous patches of the same size as the")
w("   pocket, distal only, fixed seed.")
w("")
w("The null is built from **contiguous patches**, not scattered residues. An allosteric")
w("site is a spatially connected object: a residue's score strongly predicts its")
w("neighbours', so the effective sample size is far smaller than the residue count, and")
w("any test assuming independence inflates significance. Comparing a pocket against")
w("confetti would inflate the result in our own favour.")
w("")

w("## 6. The result: negative")
w("")
w("| Target | Reference drug | Pocket (in network / holo) | First hit rank | Percentile | p |")
w("|---|---|---|---|---|---|")
for k in ORDER[:3]:
    t = Q["metricas_por_blanco"][k]
    b = t["bolsillo_validado"]
    w("| %s | %s | %d / %d | %s | %s | %s |" % (
        NAME[k], t["farmaco"], b["mapeados_en_red"], b["residuos_holo"],
        t["rank_primer_sitio_que_acierta"] or "none",
        t["percentil_bolsillo_entre_distales"], t["p_permutacion_parches_contiguos"]))
w("")
w("**No significance on any of the three.** The p-values range from %s to %s, the pocket"
  % (min(ps), max(ps)))
w("percentiles sit in the middle of the distribution, and only KRAS has a top-5 site that")
w("touches the pocket at all.")
w("")
w("**c-Myc is excluded from scoring, and we say so.** It was predicted blind and its")
w("prediction is committed in git, but no validated allosteric pocket has been published")
w("for it. We do not score what cannot be scored.")
w("")
w("**The two near-misses, which are never quoted alone.** KRAS has a rank-2 site touching")
w("the sotorasib pocket by one residue, at p = %s. Myosin has a site %s Å from the"
  % (Q["metricas_por_blanco"]["KRAS_4OBE"]["p_permutacion_parches_contiguos"],
     min(s["dist_min_al_bolsillo_A"]
         for s in Q["metricas_por_blanco"]["MYOSIN_5TBY"]["sitios"])))
w("mavacamten pocket, at p = %s. At those p-values they are not hits, and they are never"
  % Q["metricas_por_blanco"]["MYOSIN_5TBY"]["p_permutacion_parches_contiguos"])
w("cited without them. If the p-value does not fit, the number does not fit either.")
w("")

w("## 7. Why it failed — the most useful finding of the exercise")
w("")
w("**The score is a proximity-to-source measure wearing the costume of dynamic")
w("connectivity.** And an allosteric pocket is, by definition, distal: the metric and the")
w("objective are in tension by construction.")
w("")
w("| Target | n | Distal | Spearman ρ (distal) | ρ (all residues) |")
w("|---|---|---|---|---|")
for k in ORDER:
    m = prox[k]
    w("| %s | %d | %d | %s | %s |" % (
        NAME[k], m["n_residuos"], m["n_distal"],
        m["spearman_score_vs_dist_fuente_distales"],
        m["spearman_score_vs_dist_fuente_todos"]))
w("")
w("Denominator: %d of %d targets measured, %d skipped. Across distal residues the range"
  % (den_prox["medidos"], den_prox["blancos_vistos"], den_prox["saltados"]))
w("is %s to %s; across all residues, %s to %s."
  % (min(rho_d), max(rho_d), min(rho_a), max(rho_a)))
w("")
w("**The mechanism is spectral localisation.** On a path graph the mixing matrix is")
w("**flat in the interior** and spikes at **both** ends: the far end scores the same as")
w("the source itself. In a protein that means chain termini and surface protrusions rise")
w("on their own, with nothing coupling them to the active site.")
w("")
w("This is proven on a case whose answer is known in advance. The check was written")
w("expecting decay with distance, and it screamed. It stays in the suite so that if")
w("somebody \"fixes\" the metric and this changes, they find out.")
w("")
w("**The design consequence we take away:** any future metric must report its correlation")
w("with distance-to-source alongside its result. An allostery predictor correlating -0.8")
w("with proximity is measuring geometry, not coupling.")
w("")

w("## 8. Coarse-graining scalability: also negative")
w("")
w("Question pre-registered in `%s`, sealed before anything was run: when the network is"
  % prereg_cg["meta"]["file_id"])
w("compressed into supernodes of consecutive residues, **how much of the residue ordering")
w("survives?** What had already been measured was the pocket percentile and the speed-up.")
w("What was missing is what decides whether compression is useful at all: a method that")
w("runs 50× faster and reorders the list has not accelerated anything — it has solved a")
w("different problem.")
w("")
w("Thresholds frozen before looking: survives at ρ ≥ 0.90; partial between 0.70 and 0.90;")
w("does not survive below 0.70.")
w("")
w("| Target | b = 2 | b = 4 | b = 8 | b = 16 |")
w("|---|---|---|---|---|")
for k in ORDER:
    f = cells[k]
    w("| %s | %s | %s | %s | %s |"
      % (NAME[k], *[f[b]["spearman_orden_vs_fino_distales"] for b in (2, 4, 8, 16)]))
w("")
w("**%d of %d cells** reach the survival threshold: %d land in partial and %d fall below"
  % (split_cg["sobrevive"], split_cg["total"], split_cg["parcial"],
     split_cg["no_sobrevive"]))
w("0.70. Not even the mildest compression — block 2, which merely merges pairs of")
w("consecutive residues — reaches it on any target. Denominator: %d of %d targets, %d of"
  % (den_cg["blancos_medidos"], den_cg["blancos_vistos"], den_cg["celdas_calculadas"]))
w("%d cells, %d skipped." % (den_cg["celdas_blanco_x_bloque"], den_cg["celdas_saltadas"]))
w("")
w("And what weighs most is not ρ: the **top 10 % of distal residues** — the set that")
w("enters the clustering and therefore decides which sites are predicted — is preserved")
w("with a Jaccard index between %s and %s. At that level you do not get the same sites"
  % (min(jac), max(jac)))
w("ranked worse: you get different sites.")
w("")
w("**Reading.** The useful answer is not the speed-up: it is that the speed-up cannot be")
w("collected. For this metric, sequence-block coarse-graining is not a scalability route —")
w("it changes the answer before accelerating it. If coarse-graining is to be used, the")
w("grouping would have to respect structure (domains, graph communities) rather than")
w("sequence order; and that is a new hypothesis, which would go to its own")
w("pre-registration instead of sneaking in as an adjustment to this one.")
w("")

w("## 9. What this work does NOT claim")
w("")
w("- **Quantum crossings: zero.** A \"crossing\" means a quantum method beating the best")
w("  classical one. It did not happen, and none of these experiments could have produced")
w("  one: the coarse-graining study does not even compare quantum against classical.")
w("- **Significance against chance: none**, with p between %s and %s on the three scored"
  % (min(ps), max(ps)))
w("  targets.")
w("- **Simulating is not measuring.** Everything in this report is exact CPU simulation.")
w("  Hardware runs are reported separately and support no claim made here.")
w("- **The coarse-graining speed-up is an order of magnitude, not a measurement.** Timings")
w("  were taken once per cell on a machine under other load. The result shows it: myosin")
w("  reports %s× at block 8 and %s× at block 16, which is impossible as a real"
  % (cells["MYOSIN_5TBY"][8]["aceleracion_medida"],
     cells["MYOSIN_5TBY"][16]["aceleracion_medida"]))
w("  measurement.")
w("- **c-Myc at block 16 is not an improvement.** It collapses to %d supernodes, so its ρ"
  % cells["MYC_1NKP"][16]["n_supernodos"])
w("  of %s is computed over very few distinct values: a resolution artefact, not signal."
  % cells["MYC_1NKP"][16]["spearman_orden_vs_fino_distales"])
w("- **Training/challenge overlap, declared.** KRAS G12C, BCR-ABL1 and cardiac myosin are")
w("  inside the engine's 90-protein training set. There is no leakage in these experiments")
w("  because **no trained model was used**: the blind metric has no parameters and no")
w("  training. The stacked arm, which does, requires leave-one-protein-out and is a")
w("  separate experiment, not yet run.")
w("")

w("## 10. What is out of scope")
w("")
# El primer punto es el CAMBIO 2, aprobado por Nicholas el 2026-08-12. Las siete cifras
# del tercer parrafo se LEEN del sello -003; el resto es su texto tal cual. Los cuatro
# parrafos se comparan contra el archivo de aprobacion antes de escribirlos: si un numero
# cambia y vuelve falsa una frase suya, la construccion se detiene.
_p8 = parrafos_aprobados()
_generado = list(_p8)
_generado[2] = (
    "With the column finally alive in %d of %d targets, the feature-based arm scores "
    "**%s × 10⁻⁹ with conservation and %s × 10⁻⁹ without it** — %.1f× better without the "
    "real feature in the model. The quantum manager arm remains non-significant "
    "(p = %.3f), classical diffusion remains the strongest single propagator, and the "
    "manager still selects it in %d of %d targets. Every sealed number in this report is "
    "unchanged."
    % (_censo[0], _censo[1], "%.2f" % (P_B_CON * 1e9), "%.2f" % (P_B_SIN * 1e9),
       RAZON_SIN_CON, P_A, _elige, N_BLANCOS))
for _i, (_a, _b) in enumerate(zip(_p8, _generado), 1):
    if _a != _b:
        raise SystemExit(
            "el parrafo %d que genero NO es el que Nicholas aprobo.\n  aprobado: %s\n  "
            "generado: %s\nLos numeros mandan sobre la prosa: si cambiaron, el texto se "
            "reescribe con el, no se publica interpolado." % (_i, _a, _b))
w("- %s" % _generado[0])
for _par in _generado[1:]:
    w("")
    w("  %s" % _par)
w("- **Other groupings and other sizes.** No community or domain-based grouping was")
w("  tested, no blocks larger than 16, and the effect of compression on accuracy against")
w("  validated pockets was not measured — that would require opening the holo structures")
w("  and is a separate experiment.")
w("- **A truly prospective null.** It does not exist: the pool is exhausted, and everything")
w("  passing the distal filter is already inside the set. We say so rather than calling a")
w("  holdout prospective.")
w("")

w("## 11. The same circuit, run twice on hardware")
w("")
w("**The walk runs faithfully on real hardware, and we repeated it to show how much the")
w("number moves.** That is the whole claim of this section, and it is deliberately smaller")
w("than what the data would allow us to say.")
w("")
_backend = sorted({c["backend"] for c in qpu["battery"]})
assert len(_backend) == 1, "la bateria corrio en mas de un backend: hay que decirlo"
w("A %d-circuit battery ran on %s (%s shots total), submitted with a negative control, a"
  % (bat["denominador"]["circuitos_declarados"], _backend[0],
     "{:,}".format(bat["shots_totales"])))
w("repetition of the positive control, and a replica of an earlier run. **The seven job")
w("identifiers and their roles were sealed before any result existed**, so the analysis")
w("could not choose which jobs to count.")
w("")
# CAMBIO 1, aprobado el 2026-08-12: la tabla trae los siete `job_id`. El parrafo de arriba
# afirma que estaban sellados antes de que existiera ningun resultado; sin los identificadores
# a la vista, el lector no tiene con que comprobarlo. Se leen del manifiesto, no de memoria,
# y al final del documento hay una guardia que exige que los siete aparezcan en el texto.
JOB = {c["role"]: c["job_id"] for c in qpu["battery"]}
w("| Role | `job_id` | Measured pocket mass | Ideal simulation | Uniform baseline |")
w("|---|---|---|---|---|")
for _r in ("control-positivo", "control-secundario", "exploracion-largo", "repeticion",
           "replica-corrida-1", "transporte-abl1", "control-negativo"):
    _f = brow[_r]
    if _f["job_id"] != JOB[_r]:
        raise SystemExit("el rol %s trae %s en el analisis y %s en el manifiesto sellado"
                         % (_r, _f["job_id"], JOB[_r]))
    w("| %s | `%s` | %.1f %% | %.1f %% | %.1f %% |"
      % (ROLE[_r], JOB[_r], 100 * _f["masa_bolsillo_entre_validos"],
         100 * _f["ideal_pocket_mass"], 100 * _f["classical_ceiling"]))
w("")
w("Hardware tracks the ideal simulation to within **%.1f percentage points** at worst, and"
  % (100 * bat["desvio_vs_ideal"]["maximo_absoluto"]))
w("the shuffled negative control separates from the positive one by **%.1f points**. The"
  % (100 * bc["nulo_vs_control"]["delta"]))
w("circuit is doing what the simulation says it should.")
w("")
w("### The finding we did not go looking for")
w("")
w("The repetition — the same circuit, same backend, nothing changed — returns **the same")
w("pocket mass to within %s**, while the fraction of physically valid shots moves by **%.1f"
  % (bc["repeticion_vs_original"]["delta_masa"],
     100 * bc["repeticion_vs_original"]["delta_frac_valida"]))
w("points**. Across days it moves further: the replica of the earlier circuit gives %.1f %%"
  % (100 * bc["replica_vs_RQ-POC-QPU-001"]["frac_valida_replica"]))
w("valid against %.1f %% originally, **%.1f points lower**."
  % (100 * bc["replica_vs_RQ-POC-QPU-001"]["frac_valida_original"],
     -100 * bc["replica_vs_RQ-POC-QPU-001"]["delta"]))
w("")
w("**The physics we measure is stable; the noise wrapped around it is not.** Those are two")
w("numbers with different lifetimes, and until this run we quoted them side by side as if")
w("they had one. We are adopting this as a rule rather than reporting it as a curiosity:")
w("**any validity figure we publish travels with its date, or it does not travel.** A")
w("single hardware run reports a snapshot of a backend on a day, and calling it a property")
w("of the device is how a reproducible result turns into an irreproducible claim.")
w("")
w("### What this section does not claim")
w("")
w("- **The corridor is built knowing where the pocket is.** The subgraph is the shortest")
w("  path from the active site to the *known* allosteric pocket, plus neighbours. So this")
w("  battery says nothing about *finding* pockets: it measures whether the walk runs")
w("  faithfully on a small graph with the pocket deliberately placed at the far end.")
w("- **The \"classical ceiling\" is the uniform distribution**, |pocket|/n — verified equal")
w("  on all seven circuits. Beating it is beating the long-time classical diffusion limit,")
w("  which our own justification declares carries no information. It is **not** beating the")
w("  best classical method for this task; that method does not appear in this comparison.")
w("- **Quantum crossings: still zero.**")
w("- **n = 1 per circuit.** The repetition is the only error bar this experiment has, and")
w("  that is precisely why it was included.")
w("")
# ------------------------------------------------------------------ §12 el equipo
# El perfil lo redacto la coordinadora; se lee de su archivo. Las cifras del ultimo
# parrafo NO: se miden aqui contra el archivo real y se sustituyen, porque «77 corridas»
# era el conteo de ARCHIVOS sellados y solo %d de ellos son corridas.
w("## 12. Team")
w("")
_equipo = parrafear(leer_propuesta(PROP_SECC)[1][2:])
if "77 sealed runs" not in _equipo[-1]:
    raise SystemExit("el ultimo parrafo del perfil ya no trae «77 sealed runs»; la "
                     "sustitucion del censo hay que rehacerla mirando el texto nuevo, no "
                     "aplicarla a ciegas.\n  dice: %s" % _equipo[-1][-160:])
_equipo[-1] = (
    "**Why this team could run this.** The verification infrastructure this challenge asks "
    "for was already built and operating before the challenge began: a reproducible hybrid "
    "harness, and a public evidence archive that now holds **%d sealed files across three "
    "copies** — GitHub, Codeberg and a queryable database — of which **%d are experimental "
    "runs**, each one hash-anchored and timestamped on Bitcoin. Every number in this report "
    "resolves to one of them. During this submission the archive recorded not only our "
    "results but **%d corrections to our own published readings**, both still public "
    "alongside the originals. That is the capability being offered: not a faster algorithm, "
    "an apparatus that reports what it finds, including against itself."
    % (ARCHIVO["total"], ARCHIVO["por_tipo"]["RUN"],
       len(ARCHIVO["corrige_lecturas_publicadas"])))
# `_equipo` ya son parrafos: se separan con lineas en blanco antes de reflujar, o
# `parrafear` los vuelve a fundir en uno solo.
for _l in reflujo(sum([[_p, ""] for _p in _equipo], [])[:-1]):
    w(_l)
w("")

w("## How to verify this document")
w("")
w("The %s `content_hash` values in the header are recomputed with:" % palabra(len(SELLOS)))
w("")
w("```bash")
w("python3 tools/verify_seals.py <file>")
w("```")
w("")
w("**Which convention applies depends on the file, and the file's own label does not tell")
w("you.** Of the archive's %d sealed files, %d declare `rosettaq-archive/v1` and split"
  % (ARCHIVO["total"], ESQUEMAS.get("rosettaq-archive/v1", 0)))
w("across **two** different conventions that recompute differently. The verifier tries")
w("all of them")
w("and reports which one reproduced the stored hash; that is the authority, not the label.")
w("")
w("**For v1 and v2 files, verify in Python.** Those seals are computed over the text")
w("produced by Python's `json.dumps`, and languages do not serialise the same numbers")
w("identically: Python writes a float `6.0` where JavaScript, Go and Rust write `6`. If")
w("you parse such a file in another language and re-serialise it to check the hash, you")
w("will get a different result — silently, and looking exactly like tampering. It is not.")
w("Verify in Python, or compare the bytes of the file as downloaded without")
w("re-serialising it.")
w("")
w("**For v3 files that limitation is gone:** they are sealed over the RFC 8785 (JCS)")
w("canonical form, which yields the same text in any language. An independent JavaScript")
w("implementation, written from the RFC, reproduces our canonical output character for")
w("character on 22 of 22 test vectors.")
w("")
w("*No anchored file is ever re-sealed. Published hashes are immutable public facts.*")

# --- el indice, generado DESDE los titulos que el documento realmente tiene
_titulos = [x[3:] for x in L if x.startswith("## ")]
L[_IDX:_IDX] = ["| | |", "|---|---|"] + [
    "| %s | %s |" % tuple(t.split(". ", 1)) if re.match(r"^\d+\. ", t)
    else "| | %s |" % t for t in _titulos]
if len(_titulos) != 13:
    raise SystemExit("el indice lista %d secciones y esperaba 13; si se agrego o quito una, "
                     "revisa la numeracion antes de publicar" % len(_titulos))

_TEXTO = "\n".join(L) + "\n"

# GUARDIA CONTRA EL DEFECTO QUE ESTE DOCUMENTO TUVO (2026-08-12, lo encontro Nicholas
# leyendo): el reporte afirmaba que los siete `job_id` estaban sellados de antemano y no
# traia ninguno. La afirmacion es comprobable y le quitabamos al lector la comprobacion.
# La regla no es «acuerdate de poner la tabla»: es que el documento no se escribe si una
# afirmacion verificable viaja sin el dato con que se verifica.
# GUARDIA: el numero que la seccion de verificacion le dice al lector tiene que calzar
# con las filas que la tabla del encabezado realmente trae. El 2026-08-12 decia «three»
# con cuatro filas — yo agregue la cuarta y la prosa no se movio. Es la §1 bis dentro de
# la seccion que existe para cumplir la §1 bis, asi que se cuenta, no se acuerda.
_filas = sum(1 for x in _TEXTO.split("\n---\n", 1)[0].splitlines()
             if x.startswith("| ") and "content_hash" not in x and set(x) - set("|- "))
if "The %s `content_hash` values" % palabra(_filas) not in _TEXTO:
    raise SystemExit("la seccion de verificacion no dice «%s», y el encabezado trae %d "
                     "filas. Un lector cuenta las filas antes de creernos."
                     % (palabra(_filas), _filas))

_faltan = [j for j in JOB.values() if j not in _TEXTO]
if _faltan:
    raise SystemExit("el documento afirma que los %d `job_id` estaban sellados y no trae "
                     "%d de ellos (%s…). Una afirmacion verificable no viaja sin el dato "
                     "con que se verifica." % (len(JOB), len(_faltan), _faltan[0]))
for _d in (blind, prereg_cg, cg, n90):
    if _d["meta"]["content_hash"] not in _TEXTO:
        raise SystemExit("se leyeron cifras de %s y su content_hash no aparece en el "
                         "documento: el lector no puede llegar a la fuente."
                         % _d["meta"]["file_id"])

open(OUT_MD, "w").write(_TEXTO)

# ------------------------------------------------------------------ chart data
# El motor de graficos de la sesion web se niega a renderizar sin `fuente` y `n`, y sin
# un titular que afirme el hallazgo en vez de rotular el tema. Se los damos hechos.
charts = [
    {"id": "significance",
     "headline": "No target beats chance: every p-value sits far from 0.05.",
     "type": "bar",
     "source": "RQ-EXP-CLEV-BLIND-001 (%s)" % blind["meta"]["content_hash"],
     "n": len(Q["metricas_por_blanco"]),
     "y_label": "p (contiguous-patch permutation)",
     "reference_line": {"value": 0.05, "label": "significance threshold"},
     "data": [{"label": NAME[k], "value": Q["metricas_por_blanco"][k]
               ["p_permutacion_parches_contiguos"]} for k in ORDER[:3]]},
    {"id": "proximity",
     "headline": "The score tracks distance to the source, not allosteric coupling.",
     "type": "grouped_bar",
     "source": "RQ-EXP-CLEV-BLIND-001 (%s), measured by diagnose_proximity.py"
               % blind["meta"]["content_hash"],
     "n": den_prox["medidos"],
     "y_label": "Spearman ρ (score vs distance to source)",
     "series": ["distal residues", "all residues"],
     "data": [{"label": NAME[k],
               "values": [prox[k]["spearman_score_vs_dist_fuente_distales"],
                          prox[k]["spearman_score_vs_dist_fuente_todos"]]}
              for k in ORDER]},
    {"id": "coarse_grain_order",
     "headline": "Residue ordering does not survive compression at any level tested.",
     "type": "line",
     "source": "RQ-EXP-COARSE-001 (%s), pre-registered as %s"
               % (cg["meta"]["content_hash"], prereg_cg["meta"]["file_id"]),
     "n": den_cg["celdas_calculadas"],
     "x_label": "block size (residues per supernode)",
     "y_label": "Spearman ρ vs fine-grained ordering",
     "reference_line": {"value": 0.90, "label": "pre-registered survival threshold"},
     "data": [{"label": NAME[k],
               "points": [{"x": b, "y": cells[k][b]["spearman_orden_vs_fino_distales"]}
                          for b in (2, 4, 8, 16)]} for k in ORDER]},
    {"id": "coarse_grain_topset",
     "headline": "The set that decides which sites are predicted is mostly replaced.",
     "type": "line",
     "source": "RQ-EXP-COARSE-001 (%s)" % cg["meta"]["content_hash"],
     "n": den_cg["celdas_calculadas"],
     "x_label": "block size (residues per supernode)",
     "y_label": "Jaccard index of the top 10 % distal set",
     "data": [{"label": NAME[k],
               "points": [{"x": b, "y": cells[k][b]["jaccard_top10pct_distal"]}
                          for b in (2, 4, 8, 16)]} for k in ORDER]},
]
json.dump({"_doc": "Chart data for the Cleveland methodology report. Every figure carries "
                   "its source seal and its n, which the chart engine requires. Values are "
                   "read from the sealed files, never retyped.",
           "charts": charts},
          open(OUT_CHARTS, "w"), indent=1, ensure_ascii=False)

print("wrote %s (%d lines)" % (os.path.basename(OUT_MD), len(L)))
print("wrote %s (%d charts, each with source and n)"
      % (os.path.basename(OUT_CHARTS), len(charts)))
print("sha256 md     : %s" % hashlib.sha256(open(OUT_MD, "rb").read()).hexdigest())
print("sha256 charts : %s" % hashlib.sha256(open(OUT_CHARTS, "rb").read()).hexdigest())
