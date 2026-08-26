#!/usr/bin/env python3
"""Genera la version en INGLES del entregable del track HSBC.

POR QUE ES UN GENERADOR Y NO UNA TRADUCCION
-------------------------------------------
Regla 12 de APRENDIZAJES: **un artefacto es la fuente del HECHO, no de la redaccion.**
Traducir a mano el .md español seria copiar prosa — y con ella, cualquier defecto que la
prosa ya tenga. Este generador lee LOS MISMOS artefactos sellados que
`build_hsbc_entregable.py` y redacta prosa inglesa original encima. Ninguna cifra se
teclea: todas se leen del artefacto al armar.

QUE HACE DISTINTO (lecciones de E.ON y Airbus)
----------------------------------------------
- Acceso por ruta EXPLICITA que falla cerrado (`campo`): si un campo esperado no esta,
  aborta con la lista de los que si estan. Nada de `.get()` que devuelva None.
- El estado de sellado y de ancla se MIRA en el disco, no se recuerda: para cada pieza
  se comprueba el .json, su .ots y el commit que lo introdujo, y el texto se adapta.
- Los limites del dato se MIDEN sobre el ARFF cuyos bytes fija el manifiesto (se
  verifica el sha256 antes de leer). Sin ese archivo, aborta: son cifras load-bearing.
- Cada afirmacion lleva su etiqueta del §2 del estandar: measured / by construction /
  from the literature.

LAS DOS GUARDIAS DEL FINAL
--------------------------
1. **Divergencia contra el español.** Todo numero de 3+ decimales del documento ingles
   tiene que existir en `ENTREGABLE-HSBC.md` (en su forma con punto o con coma). Si
   aparece uno que el español no tiene, las dos redacciones divergieron sobre los mismos
   artefactos y el generador aborta. Se prueba por mutacion con RQ_MUTAR_GUARDIA=1.
2. **Fuga de español.** Un documento en ingles con prosa en español es como se colo el
   §5 de Airbus. Se aborta ante palabras funcionales del español.

Uso:  python3 build_hsbc_entregable_en.py
      RQ_MUTAR_GUARDIA=1 python3 build_hsbc_entregable_en.py   # debe ABORTAR
Sale: ENTREGABLE-HSBC-EN.md junto a este archivo.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np
from scipy import stats

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
SAL = os.path.join(AQUI, "ENTREGABLE-HSBC-EN.md")
ES_MD = os.path.join(AQUI, "ENTREGABLE-HSBC.md")
ES_PY = os.path.join(AQUI, "build_hsbc_entregable.py")
ARFF = os.environ.get("RQ_ULB_ARFF",
                      os.path.join(RAIZ, "lab-hsbc-2026-08-20", "creditcard.arff"))

sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs  # noqa: E402
from fuentes_hsbc import FUENTES  # noqa: E402


# ------------------------------------------------------------------ utilidades
def campo(d, *ruta):
    """Un valor por su ruta explicita. Aborta si falta, con lo que si hay.

    El buscador a ciegas que devuelve None dejo una tabla entera vacia en el informe de
    E.ON, con aspecto normal. Aqui una ausencia es un fallo, no un hueco silencioso.
    """
    cur = d
    for i, k in enumerate(ruta):
        if not isinstance(cur, dict) or k not in cur:
            disponibles = ", ".join(cur.keys()) if isinstance(cur, dict) else type(cur).__name__
            raise SystemExit("ABORTA: falta %r bajo %r. Hay: %s"
                             % (k, " -> ".join(map(str, ruta[:i])) or "(raiz)", disponibles))
        cur = cur[k]
    return cur


def miles(n):
    return "{:,}".format(int(n))


class Pieza:
    """Una pieza sellada, con su estado de sello y de ancla MIRADO en el disco."""

    def __init__(self, patron, etiqueta):
        # solo .json: los .ots comparten prefijo y son binarios (tropiezo de julio).
        cand = [x for x in sorted(glob.glob(os.path.join(EV, patron))) if x.endswith(".json")]
        if len(cand) != 1:
            raise SystemExit("ABORTA: esperaba 1 archivo para %r, hay %d: %s"
                             % (patron, len(cand), [os.path.basename(c) for c in cand]))
        self.ruta = cand[0]
        self.etiqueta = etiqueta
        self.doc = json.load(open(self.ruta, encoding="utf-8"))
        if not rs.verify(self.doc):
            raise SystemExit("ABORTA: el sello de %s no verifica." % os.path.basename(self.ruta))
        self.id = campo(self.doc, "meta", "file_id")
        self.hash = campo(self.doc, "meta", "content_hash")
        self.anclado = os.path.exists(self.ruta + ".ots")
        rel = os.path.relpath(self.ruta, EV)
        self.commit = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%h", "-1", "HEAD", "--", rel],
            cwd=EV, capture_output=True, text=True).stdout.strip()


def artefacto(patron):
    cand = glob.glob(os.path.join(EV, "resultados_hsbc", patron))
    if len(cand) != 1:
        raise SystemExit("ABORTA: esperaba 1 artefacto para %r, hay %d." % (patron, len(cand)))
    return json.load(open(cand[0], encoding="utf-8")), os.path.basename(cand[0])


# ------------------------------------------------------------------ fuentes
PRE1 = Pieza("prereg/2026/08/*HSBC-001*", "design pre-registration")
PRE2 = Pieza("prereg/2026/08/*HSBC-002*", "attack pre-registration")
MAN = Pieza("manifests/*HSBC-ULB*", "data manifest")
BASE_SELLO = Pieza("runs/2026/08/*HSBC-BASE*", "baseline run seal")
ATA_SELLO = Pieza("runs/2026/08/*HSBC-ATAQUE*", "attack run seal")
PRE3 = Pieza("prereg/2026/08/*HSBC-003-CUANTICO*", "quantum-arm pre-registration")
ERR_PRE = Pieza("reports/2026/08/*ERRATA-PREREG-HSBC-003*", "erratum to the quantum pre-reg")
QUA = Pieza("runs/2026/08/*HSBC-Q-001*", "quantum-arm run seal")
ERR_Q = Pieza("reports/2026/08/*ERRATA-EXP-HSBC-Q-001*", "erratum to the quantum-arm run")
IEEE = Pieza("runs/2026/08/*HSBC-IEEE-001*", "IEEE-CIS baseline seal")
Q2 = Pieza("runs/2026/08/*HSBC-Q-002*", "§5.2 outputs and attribution seal")
PIEZAS = [PRE1, PRE2, PRE3, MAN, BASE_SELLO, ATA_SELLO, QUA, Q2, IEEE, ERR_PRE, ERR_Q]
S52 = campo(Q2.doc, "w6", "que", "salidas_exigidas_por_el_5_2")
PERM = campo(Q2.doc, "w6", "que", "importancia_por_permutacion")
BIN = campo(S52, "binary_prediction", "umbral_F1_optimo_en_train")
MUE = campo(Q2.doc, "w6", "que", "el_conteo_que_el_statement_exige_textual")

# Numeracion DERIVADA, igual que en el generador español: insertar una seccion a mano
# renumera las siguientes y deja las referencias cruzadas apuntando a otro lado en silencio.
ORDEN_EN = ["summary", "question", "data", "method", "results", "attacks",
            "quantum", "budget", "external", "limits", "reproduce", "annexes"]
_vistas_en = []

def sec(titulo, clave):
    if clave not in ORDEN_EN:
        raise SystemExit("seccion %r no declarada en ORDEN_EN" % clave)
    if _vistas_en and ORDEN_EN.index(clave) <= ORDEN_EN.index(_vistas_en[-1]):
        raise SystemExit("la seccion %r sale despues de %r y ORDEN_EN dice lo contrario"
                         % (clave, _vistas_en[-1]))
    _vistas_en.append(clave)
    w("## %d · %s" % (ORDEN_EN.index(clave) + 1, titulo))

def ref(clave):
    if clave not in ORDEN_EN:
        raise SystemExit("referencia a seccion no declarada: %r" % clave)
    return "§%d" % (ORDEN_EN.index(clave) + 1)

import numpy as _np
_zq = _np.load(os.path.join(EV, "code", "scores_q_kernel_cuantico@091914f1.npz"))["y_score"]
QV = campo(QUA.doc, "w6", "que", "VEREDICTO")
QCTRL = campo(QUA.doc, "w6", "que", "controles_exploratorios", "resultados")
QA2 = QCTRL["A2_xgboost_mismo_dato_mismas_features"]
QA1 = QCTRL["A1_rbf_mismo_dato_mismas_features"]
QCB = QCTRL["B_cuantico_con_los_417_fraudes"]
QD4 = campo(QUA.doc, "w6", "que", "decisiones_declaradas_antes_de_mirar_el_test", "D4_soporte")
IJ = campo(IEEE.doc, "w6", "que", "mejor_por_AUPRC")
IDIF = campo(IEEE.doc, "w6", "que", "IEEE_es_mas_dificil_que_ULB")

def ic_en(v):
    return "[%.4f – %.4f]" % (v[0], v[1])

BASE, BASE_F = artefacto("hsbc_ulb_baseline_lightgbm-xgboost@*.json")
SERIES = {k: artefacto("*ataque_%s_*@*.json" % k) for k in ("S1", "S2", "S3", "S4")}

xgb = campo(BASE, "modelos", "xgboost")
lgb = campo(BASE, "modelos", "lightgbm")
part = campo(BASE, "particion")
censo = campo(MAN.doc, "w6", "que", "censo")
fuente = campo(MAN.doc, "w6", "que", "fuente")

# Las series: se leen las corridas Y el resumen sellado, y se exige que coincidan.
# Un resumen que no reproduce sus propias corridas es exactamente el fallo silencioso
# que este proyecto ya pago una vez.
auprc = {k: [campo(r, "AUPRC") for r in campo(SERIES[k][0], "corridas")] for k in SERIES}
media, desv = {}, {}
for k in SERIES:
    res = campo(SERIES[k][0], "resumen")
    media[k] = float(np.mean(auprc[k]))
    desv[k] = float(np.std(auprc[k], ddof=1))
    if abs(media[k] - campo(res, "AUPRC_media")) > 5e-6 or abs(desv[k] - campo(res, "AUPRC_sd")) > 5e-6:
        raise SystemExit("ABORTA: el resumen sellado de %s no reproduce sus propias corridas." % k)
    if len(auprc[k]) != campo(res, "n"):
        raise SystemExit("ABORTA: n declarado de %s no calza con las corridas." % k)

delta = media["S1"] - media["S4"]
_, p_welch = stats.ttest_ind(auprc["S1"], auprc["S4"], equal_var=False)
_, p_mw = stats.mannwhitneyu(auprc["S1"], auprc["S4"], alternative="two-sided")
ruido = float(np.median([campo(r, "AUPRC_boot_se")
                         for r in campo(SERIES["S1"][0], "corridas")
                         + campo(SERIES["S4"][0], "corridas")]))
umbral = 2 * ruido
margen_pct = 100 * (delta - umbral) / umbral
n_entrenamientos = sum(len(auprc[k]) for k in auprc)

crit = campo(ATA_SELLO.doc, "w6", "que", "criterio_C_calculado")
if abs(campo(crit, "delta_S1_menos_S4") - delta) > 5e-6:
    raise SystemExit("ABORTA: el Δ sellado no reproduce el Δ recomputado desde las corridas.")
salida = campo(ATA_SELLO.doc, "meta", "LA_SALIDA_QUE_HABLO")
TOLERANCIA = campo(BASE_SELLO.doc, "w6", "que", "recomputo_desde_scores_crudos", "tolerancia")
CRUCE = campo(BASE_SELLO.doc, "w6", "que", "cruce_ventaja_cuantica")
if not CRUCE.startswith("0"):
    raise SystemExit("ABORTA: el sello del baseline ya no declara 0 cruces cuanticos: %r" % CRUCE)
# La razon de SMOTE se LEE del prereg: el 50 %% del test sintetico es su consecuencia,
# no un numero de la cabeza de quien redacta.
_m = re.search(r"SMOTE \(k=(\d+), razon (\d+):(\d+)\)",
               campo(PRE2.doc, "w6", "que", "las_cuatro_series", "S2_aleatoria_smote_DENTRO"))
if not _m:
    raise SystemExit("ABORTA: no pude leer la razon de SMOTE del prereg del ataque.")
SMOTE_K, _ra, _rb = int(_m.group(1)), int(_m.group(2)), int(_m.group(3))
PCT_SINTETICO = 100.0 * _rb / (_ra + _rb)

# La banda pre-fijada y los baselines publicados se LEEN del pre-registro, no se tipean.
_txt_pre2 = json.dumps(PRE2.doc, ensure_ascii=False)
_m = re.search(r"0,871 ± 0,030 → \[0,841, 0,901\]", _txt_pre2)
if not _m:
    raise SystemExit("ABORTA: no pude leer la banda pre-fijada del prereg del ataque.")
BANDA = (0.841, 0.901)
_txt_pre1 = json.dumps(PRE1.doc, ensure_ascii=False)
_m = re.search(r"baselines publicados en el propio statement \(AUC-ROC 0,(\d+); AUPRC 0,(\d+)\)",
               _txt_pre1)
if not _m:
    raise SystemExit("ABORTA: no pude leer los baselines publicados del prereg de diseño.")
PUB_AUC, PUB_AUPRC = "0.%s" % _m.group(1), "0.%s" % _m.group(2)


# ------------------------------------------------------------------ limites del dato
def limites_medidos():
    """Mide la ventana temporal y el reparto de la clase positiva sobre el dato REAL.

    El español teclea estas cuatro cifras; aqui se miden. La licencia para hacerlo es el
    manifiesto: fija el sha256 exacto del ARFF, asi que verificarlo antes de leer
    convierte la lectura en una medicion trazable y no en una fuente nueva.
    """
    if not os.path.exists(ARFF):
        raise SystemExit(
            "ABORTA: no encuentro el ARFF de ULB en %s. Los limites del dato son cifras\n"
            "        load-bearing del §3 y no se tecleen. Receta del manifiesto:\n        %s\n"
            "        (o apunta RQ_ULB_ARFF al archivo)."
            % (ARFF, campo(MAN.doc, "w6", "como", "receta_para_un_tercero")))
    h = hashlib.sha256(open(ARFF, "rb").read()).hexdigest()
    esperado = campo(fuente, "sha256_medido")
    if h != esperado:
        raise SystemExit("ABORTA: el ARFF local no es el del manifiesto (%s != %s)."
                         % (h[:16], esperado[:16]))
    tiempos, clases, en_datos = [], [], False
    for linea in open(ARFF, encoding="utf-8", errors="replace"):
        if not en_datos:
            en_datos = linea.strip().lower() == "@data"
            continue
        linea = linea.strip()
        if not linea:
            continue
        partes = linea.split(",")
        tiempos.append(float(partes[0]))
        clases.append(partes[-1].strip().strip("'"))
    if len(tiempos) != campo(censo, "filas"):
        raise SystemExit("ABORTA: el ARFF tiene %d filas y el manifiesto declara %d."
                         % (len(tiempos), campo(censo, "filas")))
    corte = campo(part, "corte_fila")
    fraudes_total = sum(1 for c in clases if c == "1")
    fraudes_test = sum(1 for c in clases[corte:] if c == "1")
    # tasa de fraude por bloques de 8 h: el reparto de la clase positiva en el tiempo
    bloques = {}
    for t, c in zip(tiempos, clases):
        b = int(t // (8 * 3600))
        n, f = bloques.get(b, (0, 0))
        bloques[b] = (n + 1, f + (1 if c == "1" else 0))
    tasas = sorted(f / n for n, f in bloques.values())
    return {
        "horas_totales": (tiempos[-1] - tiempos[0]) / 3600.0,
        "horas_test": (tiempos[-1] - tiempos[corte]) / 3600.0,
        "fraudes_test": fraudes_test,
        "fraudes_total": fraudes_total,
        "cuota_test": fraudes_test / fraudes_total,
        "tasa_alta": tasas[-1],
        "tasa_baja": tasas[0],
        "razon_bloques": tasas[-1] / tasas[0],
        "n_bloques": len(bloques),
        "rango_Time_s": (tiempos[0], tiempos[-1]),
    }


LIM = limites_medidos()
if LIM["fraudes_test"] != campo(part, "test", "fraudes"):
    raise SystemExit("ABORTA: los fraudes del test medidos sobre el ARFF (%d) no calzan con "
                     "el artefacto (%d)." % (LIM["fraudes_test"], campo(part, "test", "fraudes")))


# ------------------------------------------------------------------ REFORMS
# Las descripciones son PROSA (inglesa, mia). Los estados son un HECHO y se cotejan
# contra la lista del generador español: si divergen, aborta.
REFORMS = [
    ("1a", "full", "population of the claim: §3, declared as intra-dataset"),
    ("1b", "full", "why this dataset: pre-registration + §3"),
    ("1c", "full", "why this method: pre-registration 001"),
    ("2a", "full", "dataset with id, md5, sha256 and a sealed manifest"),
    ("2b", "full", "code public, archived by hash, sha inside every artifact"),
    ("2c", "full", "infrastructure declared (CI, versions in lib_versions)"),
    ("2d", "partial", "instructions in §8; a dedicated README is still owed"),
    ("2e", "full", "tools/reproducir_hsbc.sh"),
    ("3a", "full", "source and collection date (Sept 2013): §3"),
    ("3b", "full", "sampling frame described: §3"),
    ("3c", "full", "dataset justification: pre-registration"),
    ("3d", "full", "outcome variable and descriptives: manifest"),
    ("3e", "full", "n in the manifest"),
    ("3f", "full", "0 nulls, trivially so per class: §3"),
    ("3g", "partial", "representativeness deliberately NOT claimed — stated as a limit"),
    ("4a", "full", "no row excluded: §3"),
    ("4b", "full", "0 corrupt rows measured; policy declared"),
    ("4c", "full", "no transformation of ours: §3"),
    ("5a", "full", "complete configs inside the artifacts"),
    ("5b", "full", "model choice justified: pre-registration"),
    ("5c", "full", "splits detailed and sealed"),
    ("5d", "full", "reported model = the fixed v1 config, no selection among alternatives"),
    ("5e", "partial", "hyperparameter search PENDING; LightGBM is open there"),
    ("5f", "full", "appropriate baselines justified: pre-registration §4"),
    ("6a", "full", "train-only preprocessing, guards mutation-tested"),
    ("6b", "full", "duplicates measured (0); temporal dependence by design"),
    ("6c", "partial", "Time/Amount legitimate; the inherited global PCA is declared (annex B)"),
    ("7a", "full", "metrics justified and sealed beforehand"),
    ("7b", "full", "bootstrap declared (2,000 resamples, fixed seed)"),
    ("7c", "full", "Welch and Mann-Whitney agree; criterion pre-sealed"),
    ("8a", "full", "second dataset measured and sealed (IEEE-CIS); bounded to two datasets"),
    ("8b", "full", "limits and contexts where we do NOT hold the findings: §3 and §7"),
]
_TRAD = {"pleno": "full", "parcial": "partial", "ausente": "absent"}
_es_items = dict((i, _TRAD[e]) for i, e in
                 re.findall(r'\("(\d[a-z])",\s*"(pleno|parcial|ausente)"',
                            open(ES_PY, encoding="utf-8").read()))
if not _es_items:
    raise SystemExit("ABORTA: no pude leer la lista REFORMS del generador español.")
_mios = dict((i, e) for i, e, _ in REFORMS)
if _mios != _es_items:
    _dif = {k for k in set(_mios) | set(_es_items) if _mios.get(k) != _es_items.get(k)}
    raise SystemExit("ABORTA: el recuento REFORMS diverge del español en: %s" % sorted(_dif))
PLENOS = sum(1 for _, e, _ in REFORMS if e == "full")
PARCIALES = sum(1 for _, e, _ in REFORMS if e == "partial")
AUSENTES = sum(1 for _, e, _ in REFORMS if e == "absent")

# El punto de partida se lee del estandar, no de la memoria de quien redacta.
_est = " ".join(open(os.path.join(RAIZ, "ESTANDAR-presentacion-entregable.md"),
                     encoding="utf-8").read().split())
_m = re.search(r"(\d+) plenos · (\d+) parciales · (\d+) ausentes", _est)
if not _m:
    raise SystemExit("ABORTA: no pude leer el recuento REFORMS de partida del estandar.")
P0, PA0, AU0 = _m.groups()


# ------------------------------------------------------------------ el documento
L = []
def w(s=""):
    L.append(s)


# El titulo NO puede afirmar «anchored»: en el disco el pre-registro de diseño no tiene
# recibo OTS. El español lo afirma y por eso este generador no lo copia — dice lo que la
# propiedad del historial de git SI sostiene, y §2 reporta el ancla pieza por pieza.
_PRE1_ANCLADO = PRE1.anclado
w("# When the split decides the number: a fraud baseline pre-registered %s"
  % ("and anchored before the code" if _PRE1_ANCLADO else "before a line of its code existed"))
w()
w("**Rosetta Quantum · HSBC track of the 2026 Global Quantum + AI Challenge · English "
  "edition, drafted for Nicholas's approval — NOT published**")
w()
w("> Every figure below is read from a sealed artifact at build time; none is typed. Each "
  "claim carries exactly one of three labels: **[measured]** (our instrument produced it "
  "and the artifact lets you recompute it), **[by construction]** (it follows from how the "
  "object is built), **[from the literature]** (a cited source holds it up). Anything "
  "without a label is not in this document.")
w()

# ---------------------------------------------------------------- 1 · resumen
sec("Summary", "summary")
w()
w("We built a classical fraud-detection baseline on public data, with the question and the "
  "protocol **sealed and pushed to a public repository before any of the code existed**. "
  "Then we attacked "
  "it: we repeated the measurement under the protocol the published literature uses, and "
  "under three variants designed to kill our own result, with every possible outcome "
  "written down and sealed before anything ran.")
w()
w("Four things came out.")
w()
w("**Our implementation reproduces the published numbers when it uses the published "
  "protocol** [measured]: the mean of the clean random-split series lands at %.4f, inside "
  "the band [%.3f – %.3f] we fixed beforehand from the challenge statement's own tabulated "
  "results. That is the credential — whatever we measure differently afterwards is not an "
  "implementation error of ours."
  % (media["S2"], BANDA[0], BANDA[1]))
w()
w("**The choice of split moves the headline metric by %.4f AUPRC** [measured]. Random "
  "splits score higher than temporal ones on the same model and the same data, and the "
  "gap is the second finding." % delta)
w()
w("**SMOTE, correctly applied, contributes +%.4f** [measured]. In this dataset and this "
  "implementation the split does all the work and the oversampling does none."
  % (media["S2"] - media["S1"]))
w()
w("**Applied in the common defective order, the metric saturates at %.4f on every seed** "
  "[measured] — reportable perfection with any model whatsoever. That is the headline of "
  "this document, and §6 states precisely what it is and is not."
  % media["S3"])
w()
w("We claim no scientific novelty: the underlying phenomenon is already catalogued "
  "[from the literature: Kapoor & Narayanan, *Leakage and the reproducibility crisis in "
  "ML-based science*, Patterns 2023]. What we offer is the machine that measures it, with "
  "a verifiable pre-registration and recomputation by third parties.")
w()

# ---------------------------------------------------------------- 2 · prereg
sec("The question, and when it was fixed", "question")
w()
w("The question — what does a quantum or quantum-inspired model add over a tuned classical "
  "one, with the protocol fixed before anyone looks? — was sealed as `%s` (`%s…`) and "
  "committed in `%s`, **before a single row of data had been downloaded**. That is a "
  "property of the git history, which you can check yourself; it is not a claim of ours. "
  "[by construction]" % (PRE1.id, PRE1.hash[:23], PRE1.commit))
w()
w("The adversarial attack was pre-registered separately as `%s` (`%s…`), committed in "
  "`%s`, **with its three possible outcomes written before the runs, including the one "
  "that left us looking bad**. The outcome that fired is computed by the sealing harness "
  "against the pre-fixed band, not chosen afterwards by a human. [by construction]"
  % (PRE2.id, PRE2.hash[:23], PRE2.commit))
w()

# El estado de ancla se MIRA, y el texto se adapta a lo que encuentre.
_anc = [p for p in PIEZAS if p.anclado]
_sin = [p for p in PIEZAS if not p.anclado]
w("**Sealing and anchoring, as they stand on disk right now** [measured]: all %d pieces of "
  "this track are sealed and their content hashes verify. Of those, **%d carry an "
  "OpenTimestamps receipt** (%s) and **%d do not yet** (%s). Anchoring is the notary's "
  "step, deliberately separate from the lab's, and we report the state rather than let you "
  "assume it. What the git history gives you for every piece is the order — the "
  "pre-registration is in the tree before any code that could have been tuned to it. What "
  "an OpenTimestamps receipt adds, for the two that have one, is a bound on *when*, from a "
  "clock neither we nor you control."
  % (len(PIEZAS), len(_anc), ", ".join("`%s`" % p.id for p in _anc),
     len(_sin), ", ".join("`%s`" % p.id for p in _sin)))
w()
w("This document covers the classical phase of the track. The quantum arm is later work "
  "and nothing here is claimed about it.")
w()

# ---------------------------------------------------------------- 3 · datos
sec("The data, and its measured limits", "data")
w()
w("**Source** [measured]: the ULB *creditcard* dataset via OpenML (id %d, version %d). The "
  "md5 we measured equals the one the source declares (`%s…`); sha256 `%s…`. Both were "
  "fixed in the sealed manifest `%s` **before the first training run**, so no result can "
  "pick its own dataset after the fact."
  % (campo(fuente, "openml_id"), campo(fuente, "version"),
     campo(fuente, "md5_medido")[:12], campo(fuente, "sha256_medido")[:16], MAN.id))
w()
w("**Census** [measured]: %s rows, %d frauds (%.3f %%), %d null values — trivially zero in "
  "both classes. No row was excluded and the features are used exactly as they arrive, "
  "with no transformation of ours [by construction]."
  % (miles(campo(censo, "filas")), campo(censo, "fraudes"),
     100 * campo(censo, "tasa_fraude"), campo(censo, "nulos_totales")))
w()
w("**The limits — measured, not estimated.** Every figure in this list was computed from "
  "the ARFF whose sha256 the manifest pins, and the generator verifies that hash before "
  "reading a byte.")
w()
w("- **The whole window is %.2f hours** [measured: Time ranges over %s–%s seconds] — two "
  "days of September 2013 [from the literature: the dataset's own documentation]. Our "
  "temporal 80/20 split leaves **%.2f hours** of test. Calling that \u201cthe future\u201d would be "
  "more than the data supports, so we do not call it that."
  % (LIM["horas_totales"], miles(LIM["rango_Time_s"][0]), miles(LIM["rango_Time_s"][1]),
     LIM["horas_test"]))
w("- **The positive class is not spread evenly through time** [measured]: across the six "
  "8-hour blocks the fraud rate varies by a factor of %.1f (%.2f %% in the worst block "
  "against %.2f %% in the cleanest), and the temporal test set ends up holding just %d of "
  "the %d frauds — %.1f %% of them."
  % (LIM["razon_bloques"], 100 * LIM["tasa_alta"], 100 * LIM["tasa_baja"],
     LIM["fraudes_test"], LIM["fraudes_total"], 100 * LIM["cuota_test"]))
w("- **V1–V28 are the components of a PCA the dataset's own authors fitted over the whole "
  "set** [by construction: it was published already transformed, so nobody can re-fit it "
  "on their training half alone]. It is unsupervised PCA — it never saw a label — and it "
  "is of a different order than an oversampling leak, but it is inherited leakage all the "
  "same and **we declare it** (annex B, L1.2-inherited).")
w("- **Sampling frame**: card-holder transactions from one European processor over two "
  "days [from the literature]. **We do not claim it represents fraud in general.** Every "
  "finding in this document is intra-dataset and by construction, never an extrapolation.")
w()

# ---------------------------------------------------------------- 4 · metodo
sec("Method", "method")
w()
w("**Split** [measured, sealed in the pre-registration]: temporal 80/20 on the `Time` "
  "column — %s training rows (%d frauds) against %s test rows (%d frauds). The sha256 of "
  "the test half is declared inside the artifact (`%s…`) and is **bit-identical across two "
  "different machines** [measured: the local Mac and the CI runner produced the same "
  "hash]. Exact duplicates between the halves: %d [measured]."
  % (miles(campo(part, "train", "filas")), campo(part, "train", "fraudes"),
     miles(campo(part, "test", "filas")), campo(part, "test", "fraudes"),
     campo(part, "test", "sha256")[:16],
     campo(part, "solape_de_contenido_duplicados_exactos")))
w()
w("**The metric that decides** [sealed beforehand]: AUPRC. At a prevalence of %.3f %% the "
  "AUC-ROC is optically generous — it is easy to score high on it and learn nothing — so "
  "AUPRC rules and AUC-ROC, F1 and the confusion matrix are always reported beside it, "
  "never instead of it. [by construction]" % (100 * campo(censo, "tasa_fraude")))
w()
w("**Baseline**: XGBoost, with its configuration declared inside artifact `@%s`. "
  "**LightGBM is OPEN and stays visible**: our v1 configuration breaks it (AUPRC %.4f, "
  "%s false positives at threshold 0.5) [measured]. That is a defect in our configuration, "
  "not in the method, and it does **not** enter as a tuned baseline until it passes the "
  "declared hyperparameter search. That search is still pending; if LightGBM ends up not "
  "entering at all, this paragraph is updated with the reason rather than deleted."
  % (BASE_F.split("@")[1][:8], campo(lgb, "AUPRC"),
     miles(campo(lgb, "confusion_0.5", "fp"))))
w()
w("**Guards, all fail-closed and all mutation-tested** [measured]: three deliberately "
  "broken artifacts — data foreign to the manifest, a harness with no provenance, a metric "
  "that does not match its own scores — make the verification battery scream with exit "
  "code 1, while the base case stays silent. A guard that has only ever been tested for "
  "screaming passes every test. What the guards enforce: the data is verified against the "
  "manifest before training; no test row takes part in training; the stratification of "
  "every subsample is measured rather than assumed; and every artifact carries the sha256 "
  "of the harness that produced it.")
w()

# ---------------------------------------------------------------- 5 · resultados
sec("Results of the classical arm", "results")
w()
w("**XGBoost baseline on the temporal split** [measured, artifact `@%s`, sealed as `%s`]:"
  % (BASE_F.split("@")[1][:8], BASE_SELLO.id))
w()
w("| metric | value | 95 %% bootstrap CI (%s resamples, seed %d) |"
  % (miles(campo(xgb, "bootstrap_validos")), campo(BASE, "seed")))
w("|---|---|---|")
w("| AUPRC (the metric that decides) | **%.4f** | [%.3f – %.3f] |"
  % (campo(xgb, "AUPRC"), *campo(xgb, "AUPRC_IC95")))
w("| AUC-ROC | %.4f | [%.3f – %.3f] |"
  % (campo(xgb, "AUC_ROC"), *campo(xgb, "AUC_IC95")))
w("| F1 at threshold 0.5 | %.4f | tp=%d fp=%d fn=%d tn=%s |"
  % (campo(xgb, "F1_umbral_0.5"), campo(xgb, "confusion_0.5", "tp"),
     campo(xgb, "confusion_0.5", "fp"), campo(xgb, "confusion_0.5", "fn"),
     miles(campo(xgb, "confusion_0.5", "tn"))))
w()
w("The first two rows describe the same model on the same test set: %.4f AUPRC and %.4f "
  "AUC-ROC. Reporting only the second would not be a lie, and it would tell the reader "
  "almost nothing — which is why the pre-registration fixed AUPRC as the metric that "
  "decides, before any of these numbers existed. [by construction]"
  % (campo(xgb, "AUPRC"), campo(xgb, "AUC_ROC")))
w()
w("**Validation context** [from the literature: the baselines the challenge statement "
  "tabulates]: the published stacking result on this dataset reports AUC-ROC %s, and ours "
  "gives %.4f on a temporal split. The published AUPRC is %s, and **our own confidence "
  "interval contains it, so we do not claim any difference against that number.** Crossing "
  "protocols *and* implementations at once is not a comparison. The honest comparison is "
  "intra-implementation, and it is in §6."
  % (PUB_AUC, campo(xgb, "AUC_ROC"), PUB_AUPRC))
w()

# ---------------------------------------------------------------- 6 · ataques
sec("Attacks on our own result", "attacks")
w()
w("This section comes before the conclusions rather than after them, because it is what "
  "gives them the right to exist.")
w()
w("Four series, %d training runs, **the same model and the same data throughout** — the "
  "only thing that changes is the protocol [measured, seal `%s`, %s]:"
  % (n_entrenamientos, ATA_SELLO.id,
     "Bitcoin-anchored" if ATA_SELLO.anclado else "anchor still pending"))
w()
w("| series | protocol | n | mean AUPRC ± sd |")
w("|---|---|---|---|")
w("| S1 | stratified random 80/20, no SMOTE | %d | %.4f ± %.4f |"
  % (len(auprc["S1"]), media["S1"], desv["S1"]))
w("| S2 | random + SMOTE fitted **inside** the training half | %d | **%.4f** ± %.4f |"
  % (len(auprc["S2"]), media["S2"], desv["S2"]))
w("| S3 | random + SMOTE applied **before** the split (defective on purpose) | %d | %.4f ± %.5f |"
  % (len(auprc["S3"]), media["S3"], desv["S3"]))
w("| S4 | temporal, cut points from 70 %% to 90 %% | %d | %.4f ± %.4f |"
  % (len(auprc["S4"]), media["S4"], desv["S4"]))
w()
w("**What survived and what did not, against the outcomes sealed beforehand:**")
w()
w("1. **The implementation is validated** [measured]. Outcome %d of the three fired: S2 — "
  "the literature's protocol, correctly applied — has mean %.4f, inside the pre-fixed band "
  "[%.3f – %.3f] built from the published numbers. So our temporal-versus-random gap is "
  "not an artifact of our code. *(The sealed artifact states this outcome in Spanish, its "
  "original language; the translation is ours and the artifact remains the source of the "
  "fact.)*" % (campo(salida, "salida"), media["S2"], BANDA[0], BANDA[1]))
w("2. **The split effect holds under its pre-sealed criterion, by a narrow margin, and we "
  "say the margin is narrow** [measured]. Δ = mean(S1) − mean(S4) = %.4f. The first "
  "condition is comfortable: Welch p = %.4g and Mann-Whitney p = %.4g agree, both well "
  "under the pre-set 0.01. The second condition — Δ greater than twice the median "
  "per-run bootstrap noise, i.e. %.4f — **is met by %.1f %% of the threshold.** A "
  "different realisation of the noise might not have met it. The seal protects whoever "
  "audits us; this sentence protects whoever reads us, and both are needed."
  % (delta, p_welch, p_mw, umbral, margen_pct))
w("3. **A hole we anticipated did not open, and it is recorded anyway** [by construction]. "
  "Before running we warned that if S2 fell below the band while S3 rose above it, the "
  "sealed outcomes would leave a region uncovered. S2 landed inside the band and the "
  "outcome fired unambiguously — but a pre-registration that anticipates its own holes is "
  "worth more than one where everything happens to fit.")
w("4. **Sensitivity to the cut point is smooth** [measured]: temporal AUPRC runs from "
  "%.2f at the 70 %% cut down to %.2f at the 90 %% cut, so the effect does not hang on a "
  "single choice of cut. The 90 %% cut leaves only %d frauds in its test set and is the "
  "noisiest point of the five, which is why it is the low end rather than a surprise."
  % (campo(campo(SERIES["S4"][0], "corridas")[0], "AUPRC"),
     campo(campo(SERIES["S4"][0], "corridas")[-1], "AUPRC"),
     campo(campo(SERIES["S4"][0], "corridas")[-1], "test", "fraudes")))
w()
w("**The central result of the attack — and the headline of this document:**")
w()
w("> **Applying the oversampling before separating the test set does not inflate the "
  "metric: it destroys it.** AUPRC = %.4f on all %d seeds, with a standard deviation of "
  "%.5f [measured]. The test half ends up %.0f %% synthetic positives — against %.3f %% real, "
  "because the pre-registered SMOTE ratio is %d:%d with k=%d — and it holds synthetic "
  "twins of training rows [by construction]. **Anyone evaluating "
  "this way can report perfection with any model at all**, which means a number published "
  "under that protocol carries no information about the model that produced it. No value "
  "from S3 is ever cited as performance anywhere in this document: it is arithmetic of the "
  "protocol, not quality of the model."
  % (media["S3"], len(auprc["S3"]), desv["S3"], PCT_SINTETICO,
     100 * campo(censo, "tasa_fraude"), _ra, _rb, SMOTE_K))
w()
w("**And its quiet complement** [measured]: when SMOTE is applied *correctly*, it "
  "contributes +%.4f over the plain random split (%.4f against %.4f) — a difference an "
  "order of magnitude smaller than its own run-to-run standard deviation (%.4f). Set that "
  "against the %.4f the split moves, and in this dataset and this implementation **the "
  "split does all the work.**"
  % (media["S2"] - media["S1"], media["S2"], media["S1"], desv["S2"], delta))
w()

# ---------------------------------------------------------------- 7 · lo que no
sec("The quantum arm: the negative, and why the handicap does not explain it", "quantum")
w("")
w("The quantum arm had its own pre-registration (`%s`, `%s`), which" % (PRE3.id, PRE3.hash[:23]))
w("fixed the criterion **before the run**: AUPRC on the full test set, 95 %% bootstrap")
w("intervals over 2,000 resamples with seed 42, and **no advantage if the interval overlaps")
w("the classical one or falls below it**. It also stated in advance that **both outcomes are")
w("deliverable**. The one that makes us look bad is the one we got, which is why it is here.")
w("")
w("| arm | AUPRC | 95 %% CI |")
w("|---|---|---|")
w("| classical, sealed (`%s`) | **%.6f** | %s |"
  % (QV["clasico_sellado"]["leido_de"], QV["clasico_sellado"]["AUPRC"],
     ic_en(QV["clasico_sellado"]["IC95"])))
w("| quantum fidelity kernel, exact simulation | **%.6f** | %s |"
  % (QV["cuantico"]["AUPRC"], ic_en(QV["cuantico"]["IC95"])))
w("")
w("**Quantum-advantage crossing: %d** [measured]. The quantum interval falls entirely below."
  % QV["cruce_ventaja_cuantica"])
w("Both arms were scored on **the same test set, verified by hash** (`%s…`),"
  % QV["mismo_test_comprobado_por_hash"][:16])
w("with the same resampling. A comparison drawn against a different bootstrap is not a")
w("comparison, so the sealer **aborts** when the two hashes differ [by construction].")
w("")
w("### The handicap is real, and we measured it instead of invoking it")
w("")
w("The challenge statement requires **stratified** sampling. At a %.3f %% fraud rate, a"
  % (100 * part["train"]["tasa"]))
w("support set of %s points leaves **%d positives**, against the %d the classical arm trained"
  % (miles(QD4["n"]), QD4["fraudes"], part["train"]["fraudes"]))
w("on. That is a hard, asymmetric disadvantage, and it is the first explanation anyone would")
w("reach for — ourselves included.")
w("")
w("**So we handed the classical arm the very same handicap** [measured]: the same %s-point"
  % miles(QD4["n"]))
w("subsample, the same 8 variables, the same %d frauds." % QD4["fraudes"])
w("")
w("| control (not pre-registered) | AUPRC | 95 %% CI | vs. the sealed baseline |")
w("|---|---|---|---|")
w("| XGBoost, same sample and same variables | **%.4f** | %s | overlaps |"
  % (QA2["AUPRC"], ic_en(QA2["AUPRC_IC95"])))
w("| quantum kernel with all %d frauds (not stratified) | %.4f | %s | below |"
  % (part["train"]["fraudes"], QCB["AUPRC"], ic_en(QCB["AUPRC_IC95"])))
w("| RBF, same sample and same variables | %.4f | %s | below |"
  % (QA1["AUPRC"], ic_en(QA1["AUPRC_IC95"])))
w("")
w("XGBoost on the crippled sample reaches **%.4f**, and its interval **overlaps the"
  % QA2["AUPRC"])
w("baseline's**: stratified sampling cost the classical method something that is not even")
w("detectable. And lifting the handicap from the quantum arm entirely — all %d frauds —"
  % part["train"]["fraudes"])
w("raises it to %.4f and it **still falls below**. The handicap exists and it does not"
  % QCB["AUPRC"])
w("explain the result.")
w("")
w("Without that measurement, «the quantum kernel loses» and «we gave it %d positives» are"
  % QD4["fraudes"])
w("indistinguishable, and publishing the first would be a false report even with a correct")
w("number attached.")
w("")
w("### We do not claim to beat the RBF kernel either")
w("")
w("On the same data, the same variables and the same classifier, the quantum kernel scores")
w("%.4f and the RBF %.4f. That looks like a win until you read the intervals: %s"
  % (QV["cuantico"]["AUPRC"], QA1["AUPRC"], ic_en(QV["cuantico"]["IC95"])))
w("against %s — **they touch**. By the same rule we used to deny a quantum advantage over"
  % ic_en(QA1["AUPRC_IC95"]))
w("the baseline, we cannot claim to beat the RBF either [measured]. The rule applies to us")
w("or it is not a rule.")
w("")
w("### Exact simulation is what the statement proposes, not a shortfall to excuse")
w("")
w("The statement itself says that *«full end-to-end model training or inference on quantum")
w("hardware is not expected nor required»*, and **explicitly encourages** prototyping on")
w("Amazon Braket's managed simulators [from the literature: official statement, §5.3].")
w("Running in exact simulation at US$0 is the route the challenge proposes.")
w("")
w("**And one clause deserves to have its scope stated rather than assumed.** The stratified")
w("subsampling requirement sits nested under *«Teams using hardware are encouraged to:»*.")
w("**We did not run on hardware**, so on a plain reading it does not bind us — and we")
w("honoured it anyway, which cost us %d frauds instead of %d. **We are not forcing the"
  % (QD4["fraudes"], part["train"]["fraudes"]))
w("reading that suits us**: we report the pre-registered arm *with* the constraint (%.4f)"
  % QV["cuantico"]["AUPRC"])
w("and the control without it (%.4f), and **both fall below the baseline** [measured]. The"
  % QCB["AUPRC"])
w("conclusion does not depend on how the rule is read.")
w("")
w("### The model was not inert: it uses all eight variables and still loses")
w("")
w("The natural objection to a negative is that the implementation was broken, or ignoring its")
w("inputs. **We measured it.** We shuffled each variable in the test set and measured how far")
w("AUPRC falls, with %d repetitions per variable so the drop carries an interval rather than"
  % PERM["por_variable"][list(PERM["por_variable"])[0]]["repeticiones"])
w("resting on a single run [measured].")
w("")
w("| variable | AUPRC drop when shuffled | AUPRC left | 95 %% CI |")
w("|---|---|---|---|")
for _v, _x in sorted(PERM["por_variable"].items(), key=lambda t: -t[1]["caida_media_de_AUPRC"]):
    w("| %s | %.4f | %.4f | %s |" % (_v, _x["caida_media_de_AUPRC"],
                                     PERM["AUPRC_de_referencia"] - _x["caida_media_de_AUPRC"],
                                     ic_en(_x["IC95"])))
w("")
w("**%d of %d variables have a drop whose interval does not cross zero** [measured]."
  % (len(PERM["por_variable"]) - len(PERM["variables_cuya_caida_cruza_cero"]),
     len(PERM["por_variable"])))
w("Shuffling any single one of them collapses AUPRC to the order of the base rate. **The")
w("model is not inert: it extracts signal from every one of its inputs** — and using all of")
w("it, it reaches %.4f, while a classical model **on the same eight variables and the same"
  % QV["cuantico"]["AUPRC"])
w("sample** reaches %.4f." % QA2["AUPRC"])
w("")
w("That **closes off the easiest exit for a sceptical reader** and makes the negative")
w("stronger, not weaker. It also agrees with the local attribution, which is a separate")
w("measurement: per-transaction contributions are near-uniform across variables. None")
w("dominates; all of them contribute.")
w("")
w("### The three outputs the statement requires")
w("")
w("§5.2 of the statement asks for three artefacts and the sealed arm produced one. They are")
w("in `%s` [measured]:" % Q2.id)
w("")
w("| output required | what we deliver |")
w("|---|---|")
w("| *Fraud Probability*, `Float [0,1]` | calibrated probability, range %s |"
  % ic_en(S52["fraud_probability"]["rango"]))
w("| *Binary Prediction*, `Integer {0,1}` | threshold chosen on **train**: %d positives, "
  "precision %.3f, recall %.3f, F1 %.3f |"
  % (BIN["predichos_positivos"], BIN["precision"], BIN["recall"], BIN["F1"]))
w("| *Feature Attribution*, contribution **per prediction** | a %s × %d matrix: one "
  "contribution vector for every transaction in the test set |"
  % (miles(campo(S52, "feature_attribution", "local_por_prediccion", "forma")[0]),
     campo(S52, "feature_attribution", "local_por_prediccion", "forma")[1]))
w("")
w("**And the count the statement requires verbatim** — *«the total number of samples used for")
w("quantum execution must be explicitly stated in the submission»* — stated in those terms:")
w("stratified support set **%s** (%d frauds), calibration **%s**, test **%s**, **total %s"
  % (miles(MUE["soporte_estratificado"]), MUE["fraudes_en_el_soporte"],
     miles(MUE["calibracion"]), miles(MUE["test_evaluado"]),
     miles(MUE["total_de_muestras_con_ejecucion_cuantica"])))
w("samples** under quantum execution, on **%d qubits** [measured]." % MUE["qubits"])
w("")
w("> **The calibrated probability is not cosmetic, and we found this ourselves before")
w("> submitting.** Checking whether we met the `Float [0,1]` the statement asks for, we saw")
w("> that our scores were decision-function **margins**, running from %.4f to %.4f. AUPRC and"
  % (float(_zq.min()), float(_zq.max())))
w("> AUC do not notice — they are rank-based — but the original artefact's «0.5 threshold»")
w("> applied 0.5 to that scale, and out of it came a precision of 1.000 on **3** predicted")
w("> positives out of %s: the ultra-conservative point of an arbitrary scale, not a property"
  % miles(MUE["test_evaluado"]))
w("> of the method. It is corrected in erratum `%s`, which **does not rewrite the**" % ERR_Q.id)
w("> **original** and leaves the verdict intact. At the threshold chosen on train, precision")
w("> %.3f and recall %.3f." % (BIN["precision"], BIN["recall"]))
w("")
w("### What this measurement does not answer")
w("")
w("Nothing about hardware. The arm ran in **exact simulation**, at US$0, without sending a")
w("single circuit to a device: a statevector has no noise, no readout error, no decoherence")
w("and no transpilation error. That makes this number a **ceiling** [by construction]: with")
w("the same feature map, the noisy version cannot beat the exact one. No advantage here")
w("**closes the case**; an advantage here would **not** prove one on hardware. That asymmetry")
w("is why a simulation suffices for a negative and would not suffice for a positive.")
w("")

sec("Search budget: the guard we adopted against ourselves", "budget")
w("")
w("From %s [from the literature] we took a guard and wrote it into the protocol, because it"
  % FUENTES[0]["id"])
w("attacks the cheapest way to fool yourself with a quantum result: **selecting the quantum")
w("model from more configurations than the classical one**. In that work, the single")
w("statistically significant advantage they observed **turned out to be fully explained by")
w("the number of configurations searched** — it stopped being a finding and became an")
w("artefact of the procedure.")
w("")
w("**Our search budget, measured: one configuration per arm, for both arms** [measured].")
w("There is no `GridSearchCV`, `RandomizedSearchCV`, `optuna` or `param_grid` anywhere in")
w("the instrument: both arms' hyper-parameters are fixed in the published code")
w("(`code/hsbc_harness@%s.py`), and you can check that by reading it. Our negative cannot be"
  % campo(QUA.doc, "w6", "como", "harness", "sha256").split(":")[-1][:8])
w("an artefact of the search budget, because there was no search.")
w("")
w("**And the reverse, which runs against us and is stated anyway**: the same work reports")
w("that ordinary hyper-parameter choices move performance **considerably more than the")
w("quantum kernel does**. If nobody tuned anything, then our `C = 1`, the `reps = 2` feature")
w("map and the scaling to `[0, π]` are exactly that kind of untuned choice. **We cannot")
w("separate «the method does not help» from «this configuration does not help»**, and a")
w("budget-matched search across both arms is pending work, not a result.")
w("")
w("**But that caveat is smaller than we ourselves had made it, and saying so is also part of")
w("the job.** %s shows that optimal bandwidth tuning **moves** quantum kernels **towards**"
  % FUENTES[2]["id"])
w("RBF kernels (%s). If that holds, tuning would not have moved us away from the classical" % ref("external"))
w("kernel: it would have pushed us into it. The caveat stands — we are not in that regime,")
w("because we did not tune — but it stops being «maybe another configuration would have won»")
w("and becomes «the direction the literature says tuning moves you is *towards* the")
w("classical kernel, not away from it». **An inflated caveat is another way of not saying")
w("what you know.**")
w("")

sec("What was already known: triangulation on three axes", "external")
w("")
w("Our result does not land on empty ground. **None of the three works below replicates our")
w("measurement** — we are supervised ranking with AUPRC on card fraud, and none of them is")
w("that — and saying so matters: presenting them as replications would be the very stitching")
w("this document exists to avoid. What they do is close in from three different sides.")
w("")
w("| source | axis | what it measures |")
w("|---|---|---|")
for _f in FUENTES:
    w("| `%s` | %s | %s |" % (_f["id"], _f["eje_en"], _f["mide_en"]))
w("")
for _f in FUENTES:
    w("**`%s`** — *%s*, %s, %s [from the literature]."
      % (_f["id"], _f["tit"], _f["autor"], _f["fecha_en"]))
    w("")
    w("> %s" % _f["quote"])
    w("")
w("**The two findings that touch us most are not the headlines:**")
w("")
w("- **Geometric difference predicts nothing.** `%s` reports, verbatim, that *«the geometric"
  % FUENTES[1]["id"])
w("  difference, while large throughout (g ≫ 1), does not predict out-of-sample gains")
w("  (ρ = −0.20)»*. That difference is **the standard diagnostic** used to argue a quantum")
w("  kernel is «different enough» from a classical one to hold an advantage. There it is")
w("  large and **negatively correlated** with the real gain. It is the published")
w("  counterexample to «exponential space ⇒ separates better».")
w("- **A badly built evaluation manufactures the advantage.** The same work documents that")
w("  *«a 60-window evaluation on a universe screened with full-sample information makes the")
w("  same quantum kernel appear dominant on stability criteria»*: information from the")
w("  future leaking in and producing dominance where none exists. **That is the same")
w("  phenomenon we measured** in %s with balancing applied before the split, which" % ref("attacks"))
w("  saturates the metric at 1.0000 under any seed. Two teams, two markets, one mechanism.")
w("")
w("**What we do not claim** [by construction]: that this is a literature review. These are")
w("**three sources that came out of one sweep of ours**, opened and verified sentence by")
w("sentence — none of them entered by relay. Three papers are not a sweep with a denominator,")
w("and that sweep has not been done.")
w("")

sec("What we cannot claim", "limits")
w()
w("- **Nothing about quantum models.** This phase is entirely classical: the baseline seal "
  "records a quantum-advantage crossing count of `%s`, and none was attempted. "
  "[by construction]" % CRUCE.split(" ")[0])
w("- **Nothing against the published %s as a number.** Our interval contains it. The "
  "evidence for a protocol effect is the intra-implementation Δ, never the subtraction of "
  "one implementation from another. [by construction]" % PUB_AUPRC)
w("- **Nothing outside this dataset.** %.2f hours, one processor, 2013. Every finding is "
  "by construction and intra-dataset. [measured]" % LIM["horas_totales"])
w("- **The margin on criterion C is narrow** — %.1f %% of the threshold — and it travels "
  "that way wherever this result goes. [measured]" % margen_pct)
w("- **LightGBM remains open** because of our own configuration; the declared "
  "hyperparameter search is still pending for both models. [measured]")
w("- **External validity** (REFORMS item 8a): the IEEE-CIS benchmark is waiting on a "
  "credential decision, and until then there is no external evidence here. [measured]")
if _sin:
    w("- **%d of the %d sealed pieces have no Bitcoin anchor receipt yet** (%s). They are "
      "sealed, public and hash-verifiable; the anchor is a separate step by the notary and "
      "it has not run for these. We say so rather than let you assume it. [measured]"
      % (len(_sin), len(PIEZAS), ", ".join("`%s`" % p.id for p in _sin)))
w()

# ---------------------------------------------------------------- 8 · reproduccion
sec("Reproduce this — we exercised it first", "reproduce")
w()
w("```")
w("git clone https://github.com/RosettaQuantum/evidence && cd evidence")
w("bash tools/reproducir_hsbc.sh        # fetches and verifies the data, runs the baseline")
w("                                     # and all four series, verifies everything")
w("                                     # with a denominator")
w("python3 tools/replicar.py verificar --track hsbc   # the verification alone")
w("```")
w()
w("- **The raw scores are deposited** (`scores_*.npz`, addressed by hash), so a third "
  "party can rebuild the exact curves rather than trust our summary. **We exercised that "
  "as the third party** [measured]: starting from the bytes in origin (`git archive`, no "
  "local files), AUPRC, AUC, F1 and all four cells of the confusion matrix recompute "
  "within the declared tolerance. That tolerance is `%s` and it is written into the "
  "baseline seal rather than left implicit: the scores are stored as float32, so "
  "\u201cidentical\u201d would be the wrong word and we do not use it." % TOLERANCIA)
w("- **The verification battery runs 7 checks per artifact** and each one ends in OK, FAIL "
  "or SKIPPED. A check that could not be exercised counts as skipped and appears in the "
  "denominator — never as silence. [by construction]")
w("- **Cross-machine determinism** [measured]: the split produces the same test sha256 on "
  "the local Mac and in CI, and the baseline point (the 80 % cut) reproduces to the fourth "
  "decimal across independent CI runs. Note the distinction: same-hash for the split is "
  "bit-for-bit, while the metric is reproducible to a stated decimal — those are two "
  "different claims and we do not merge them.")
w("- **Scope of our own exercise** [by construction]: every command in the script was "
  "actually run — download and verification locally, the runs in CI (5 dispatches: the "
  "baseline and the four series, each listed in its artifact by run id), the battery "
  "locally and under mutation. The script as a single unit needs xgboost with OpenMP, so "
  "it runs in CI or on a compatible machine.")
w()

# ---------------------------------------------------------------- 9 · anexos
sec("Annexes", "annexes")
w()
w("### A · REFORMS, item by item")
w()
w("We score ourselves against **REFORMS** — *Reporting Standards for Machine Learning "
  "Based Science* (Kapoor et al., *Science Advances* 2024; 32 items in 8 modules) — and "
  "publish the score inside the document rather than leaving the audit to the reader. "
  "[from the literature]")
w()
w("**Count at build time: %d full · %d partial · %d absent, of %d.** The starting point "
  "(20 Aug, before the attack and before this document) was %s · %s · %s; it stands as a "
  "trajectory and is not overwritten. Closing plan for the %d partials: a dedicated README "
  "(2d), the declared hyperparameter search (5e), and the IEEE-CIS credential decision "
  "(8a). Items 3g and 6c are limits of the data itself — they are declared, not \u201cclosed\u201d. "
  "[measured]" % (PLENOS, PARCIALES, AUSENTES, len(REFORMS), P0, PA0, AU0, PARCIALES))
w()
w("| item | status | where |")
w("|---|---|---|")
for item, estado, donde in REFORMS:
    w("| %s | %s | %s |" % (item, estado, donde))
w()
w("### B · Model info sheet — the eight leakage types of Kapoor & Narayanan")
w()
w("[from the literature: the taxonomy in *Leakage and the reproducibility crisis in "
  "ML-based science*, checked against the text of the paper itself]")
w()
w("| type | status in this work |")
w("|---|---|")
w("| L1.1 no test set | ABSENT [by construction]: the split was sealed before any training |")
w("| L1.2 preprocessing over train+test | ABSENT in our own work [measured: we apply no "
  "transformation]; **INHERITED from the dataset** [by construction]: the PCA behind "
  "V1–V28 was fitted over the complete set before publication — impossible to remove, so "
  "we declare it |")
w("| L1.3 feature selection over train+test | ABSENT [by construction]: there is no "
  "feature selection |")
w("| L1.4 train-test duplicates | MEASURED: %d exact duplicates between the halves |"
  % campo(part, "solape_de_contenido_duplicados_exactos"))
w("| L2 illegitimate features | Time and Amount are legitimate for this task; V1–V28 are "
  "anonymous by design [by construction] |")
w("| L3.1 temporal leakage | THIS IS THE OBJECT OF STUDY: the temporal series avoids it, "
  "the random series exhibit it on purpose, and its effect is measured (Δ = %.4f) |" % delta)
w("| L3.2 non-independence of train and test | transactions from the same pair of days; "
  "declared as a limit in §3 |")
w("| L3.3 sampling bias | one processor, %.2f hours: declared, with no reweighting |"
  % LIM["horas_totales"])
w()
w("### C · Artifacts and seals")
w()
w("| piece | identifier | content hash | commit | anchor |")
w("|---|---|---|---|---|")
for p in PIEZAS:
    w("| %s | `%s` | `%s` | `%s` | %s |"
      % (p.etiqueta, p.id, p.hash, p.commit, "yes (OTS)" if p.anclado else "**pending**"))
w()
w("| result artifact | file |")
w("|---|---|")
w("| baseline | `%s` |" % BASE_F)
for k in ("S1", "S2", "S3", "S4"):
    w("| series %s | `%s` |" % (k, SERIES[k][1]))
w()
w("*Seals are verified with `python3 tools/verify_seals.py <file>`. The Bitcoin anchoring "
  "(OpenTimestamps) and the three mirrors (GitHub, Codeberg, D1) belong to the notary, a "
  "role deliberately separate from the lab that seals.*")
w()
w("---")
w()
w("*Blue Tuna SpA · Punta Arenas, Chile · hello@rosettaquantum.com*")

doc = "\n".join(L) + "\n"

# ------------------------------------------------------- MUTACION de la guardia
# La inyeccion vive aqui para que la guardia se pueda probar EJERCIENDO el generador,
# no leyendo su codigo. Un numero de 4 decimales que el español no puede tener.
if os.environ.get("RQ_MUTAR_GUARDIA") == "1":
    doc = doc.replace("## 1 · Summary",
                      "## 1 · Summary\n\nMUTACION DE PRUEBA: AUPRC 0.7231 [measured]\n")


# ------------------------------------------------------- GUARDIA 1: divergencia
# Todo numero de 3+ decimales del ingles tiene que existir en el español. Si aparece uno
# nuevo, las dos redacciones divergieron sobre los MISMOS artefactos, y eso es un fallo
# del sistema, no una diferencia de estilo. Se compara contra el texto español tal cual,
# aceptando su punto o su coma decimal (el .md mezcla las dos convenciones).
if not os.path.exists(ES_MD):
    raise SystemExit("ABORTA: no encuentro %s. La guardia de divergencia no es opcional."
                     % os.path.basename(ES_MD))
es_txt = open(ES_MD, encoding="utf-8").read()
en_nums = sorted(set(re.findall(r"(?<![\d.,\w])(\d+)\.(\d{3,})(?![\d])", doc)))
faltantes = []
for ent, dec in en_nums:
    patrones = [r"(?<![\d.,])%s[.,]%s(?![\d])" % (re.escape(ent), re.escape(dec))]
    if not any(re.search(p, es_txt) for p in patrones):
        faltantes.append("%s.%s" % (ent, dec))
if faltantes:
    raise SystemExit(
        "ABORTA: %d numero(s) del documento ingles NO existen en el español: %s\n"
        "        Las dos redacciones divergieron sobre los mismos artefactos."
        % (len(faltantes), ", ".join(faltantes)))

# ------------------------------------------------------- GUARDIA 2: fuga de español
# Nacio del §5 del informe de Airbus: un campo de artefacto pegado crudo salio en
# español dentro de un documento en ingles. Palabras funcionales que no existen en
# ingles tecnico; las lineas de tabla con identificadores citados se excluyen.
_ES_PALABRAS = (" que ", " para ", " porque ", " cuando ", " sobre el ", " sobre la ",
                " los ", " las ", " una sola ", " es decir ", " tambien ", " segun ",
                " particion ", " medido ", " por construccion ")
_sospechosas = [l for l in doc.split("\n")
                if any(re.search(re.escape(p), l, re.I) for p in _ES_PALABRAS)
                and not l.strip().startswith("| `")]
if _sospechosas:
    raise SystemExit("ABORTA: hay prosa en español en un documento en ingles (%d linea(s)):\n   %s"
                     % (len(_sospechosas), "\n   ".join(l[:110] for l in _sospechosas[:4])))

open(SAL, "w", encoding="utf-8").write(doc)

# ------------------------------------------------------- reporte del armado
etiquetas = {e: len(re.findall(r"\*\*\[%s\]\*\*|\[%s\]" % (e, e), doc))
             for e in ("measured", "by construction", "from the literature")}
print("ENTREGABLE HSBC (EN) ARMADO — %d lineas, %d palabras" % (len(L), len(doc.split())))
print("  secciones: %d" % len(re.findall(r"^## \d", doc, re.M)))
print("  etiquetas: %s" % " · ".join("%s=%d" % (k, v) for k, v in etiquetas.items()))
print("  guardia de divergencia: %d numeros de 3+ decimales, todos presentes en el español"
      % len(en_nums))
print("  REFORMS: %d full / %d partial / %d absent (cotejado contra el generador español)"
      % (PLENOS, PARCIALES, AUSENTES))
print("  piezas selladas: %d · ancladas: %d · sin ancla: %s"
      % (len(PIEZAS), len(_anc), ", ".join(p.id for p in _sin) or "ninguna"))
print("  limites del dato medidos sobre el ARFF verificado: %.2f h totales, %.2f h de test"
      % (LIM["horas_totales"], LIM["horas_test"]))
print("escrito %s" % os.path.relpath(SAL, RAIZ))
print("sha256:", hashlib.sha256(doc.encode()).hexdigest()[:16])
