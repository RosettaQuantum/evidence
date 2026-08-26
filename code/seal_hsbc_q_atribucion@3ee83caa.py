#!/usr/bin/env python3
"""Sella las tres salidas que el §5.2 del enunciado de HSBC exige, mas la atribucion.

QUE SELLA
---------
El enunciado pide TRES artefactos —Fraud Probability en [0,1], Binary Prediction en {0,1} y
Feature Attribution— y el brazo sellado producia UNO. Esto cierra el hueco:

  a) probabilidad CALIBRADA a [0,1]. Lo que devuelve SVC.decision_function son margenes; el
     detalle esta en la errata RQ-ERRATA-EXP-HSBC-Q-001. Platt ajustado sobre filas del
     TRAIN disjuntas del soporte, nunca sobre el test.
  b) prediccion binaria en dos umbrales declarados: el elegido por F1 EN EL TRAIN, y 0,5
     sobre la probabilidad calibrada. El umbral es una decision de negocio; se dan los dos
     con su matriz en vez de elegir por el lector.
  c) atribucion LOCAL, una fila por transaccion. El enunciado pide «contribution of features
     to EACH prediction»: un ranking global responde otra pregunta. Por oclusion — cada
     variable se reemplaza por su mediana del TRAIN y se mide cuanto se mueve el score DE
     ESA FILA.
  d) ademas, importancia por permutacion sobre el AUPRC, con repeticiones e intervalo. No la
     pide el enunciado; dice si el modelo extrae senal de alguna variable.

NO ESTA PRE-REGISTRADO y se declara: es trabajo descriptivo posterior al resultado primario,
que no se toca. El veredicto vive en RQ-EXP-HSBC-Q-001 y esta errata-do aparte.

GUARDIA CENTRAL: la calibracion es monotona, asi que NO PUEDE mover el AUPRC. Si lo movio,
el ranking cambio y el artefacto no sirve como reemplazo. Aborta.

Costo US$0: local, simulacion exacta, sin QPU.
"""
import hashlib, json, os, shutil, sys, glob
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes
from sklearn.metrics import average_precision_score

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

LAB = os.path.join(RAIZ, "lab-hsbc-2026-08-20")
ART = os.path.join(LAB, "resultado_hsbc_atribucion.json")
NPZ = os.path.join(LAB, "scores_atr_atribucion.npz")
CORRER = os.path.join(LAB, "_correr_atribucion.sh")
HARNESS = os.path.join(EV, "harness", "hsbc_harness.py")
for f in (ART, NPZ, CORRER):
    if not os.path.exists(f):
        raise SystemExit("ABORTA: falta %s" % os.path.basename(f))
d = json.load(open(ART))
S52 = d["salidas_5_2"]

PRIM = glob.glob(os.path.join(EV, "runs", "2026", "08", "*HSBC-Q-001*.json"))[0]
ERRA = glob.glob(os.path.join(EV, "reports", "2026", "08", "*ERRATA-EXP-HSBC-Q-001*.json"))[0]
prim, erra = json.load(open(PRIM)), json.load(open(ERRA))
for x, n in ((prim, "primario"), (erra, "errata")):
    if not rs.verify(x): raise SystemExit("ABORTA: el %s no verifica" % n)

# ---------------- GUARDIAS
if d["harness_sha256"] != sha(HARNESS):
    raise SystemExit("ABORTA: el artefacto declara harness %s y el del arbol es %s"
                     % (d["harness_sha256"][:16], sha(HARNESS)[:16]))
AUPRC_PRIM = prim["w6"]["que"]["VEREDICTO"]["cuantico"]["AUPRC"]
if d["modelos"]["kernel_cuantico"]["AUPRC"] != AUPRC_PRIM:
    raise SystemExit("ABORTA: esta corrida da AUPRC %s y el primario sellado %s — no es el "
                     "mismo modelo" % (d["modelos"]["kernel_cuantico"]["AUPRC"], AUPRC_PRIM))
z = np.load(NPZ, allow_pickle=True)
pr, loc = z["proba"], z["atribucion_local"]
if not (pr.min() >= 0.0 and pr.max() <= 1.0):
    raise SystemExit("ABORTA: la probabilidad no esta en [0,1] y el enunciado pide «Float [0,1]»")
if round(float(average_precision_score(z["y_true"], pr)), 6) != AUPRC_PRIM:
    raise SystemExit("ABORTA: la calibracion movio el AUPRC. Una transformacion monotona no "
                     "puede: si se movio, el ranking cambio.")
n_test = int(prim["w6"]["que"]["particion"]["test"]["filas"])
if loc.shape[0] != n_test:
    raise SystemExit("ABORTA: la atribucion local tiene %d filas y el test %d. El enunciado "
                     "pide contribucion POR PREDICCION: una fila por transaccion o no cumple."
                     % (loc.shape[0], n_test))
if len(S52["feature_attribution"]["ranking_global"]) != loc.shape[1]:
    raise SystemExit("ABORTA: el ranking global no cubre todas las variables")

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
NOMBRE = ("RosettaQ__RUN__RQ-EXP-HSBC-Q-002__%s__"
          "salidas-5-2-probabilidad-calibrada-binaria-y-atribucion-local.json" % STAMP)
PERM = S52["importancia_por_permutacion"]
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-EXP-HSBC-Q-002", "type": "RUN", "is_demo": False,
    "scope_note": "Las tres salidas que el §5.2 del enunciado de HSBC exige, producidas "
                  "sobre el MISMO modelo del brazo cuantico ya sellado. Trabajo "
                  "descriptivo posterior: NO esta pre-registrado y no modifica el "
                  "veredicto, que vive en RQ-EXP-HSBC-Q-001.",
    "extiende": {"file_id": prim["meta"]["file_id"],
                 "content_hash": prim["meta"]["content_hash"]},
    "errata_relacionada": {"file_id": erra["meta"]["file_id"],
                           "content_hash": erra["meta"]["content_hash"]},
}, "w6": {
    "que": {
        "artefacto": {"archivo": os.path.basename(ART), "sha256": "sha256:" + sha(ART),
                      "publicado_como": "code/resultado_hsbc_atribucion@%s.json" % sha(ART)[:8]},
        "NO_PRE_REGISTRADO": {
            "es": True,
            "por_que_esta_bien": "no afirma ninguna hipotesis ni cambia un criterio: produce "
                "las salidas que el enunciado pide sobre un modelo ya fijado y sellado. El "
                "resultado que SI estaba pre-registrado —hay ventaja o no— no se toca.",
        },
        "salidas_exigidas_por_el_5_2": S52,
        "importancia_por_permutacion": PERM,
        "el_conteo_que_el_statement_exige_textual": S52["muestras_de_la_ejecucion_cuantica"],
        "el_veredicto_sigue_siendo": {
            "AUPRC": AUPRC_PRIM,
            "IC95": prim["w6"]["que"]["VEREDICTO"]["cuantico"]["IC95"],
            "cruce_ventaja_cuantica": prim["w6"]["que"]["VEREDICTO"]["cruce_ventaja_cuantica"],
            "leido_de": prim["meta"]["file_id"],
        },
        "cruce_ventaja_cuantica": 0,
    },
    "como": {
        "harness": {"archivo": "hsbc_harness.py", "sha256": "sha256:" + sha(HARNESS),
                    "publicado_como": "code/hsbc_harness@%s.py" % sha(HARNESS)[:8]},
        "comando": {"archivo": os.path.basename(CORRER), "sha256": "sha256:" + sha(CORRER),
                    "publicado_como": "code/_correr_atribucion@%s.sh" % sha(CORRER)[:8]},
        "salidas_crudas": {"archivo": os.path.basename(NPZ), "sha256": "sha256:" + sha(NPZ),
                           "publicado_como": "code/scores_atr_atribucion@%s.npz" % sha(NPZ)[:8],
                           "contiene": "y_true, proba (calibrada en [0,1]), binaria, "
                                       "atribucion_local (%d x %d) y los nombres de las "
                                       "variables" % (loc.shape[0], loc.shape[1])},
        "guardias": "aborta si el harness no es el que produjo el dato, si el AUPRC difiere "
                    "del primario sellado, si la probabilidad no esta en [0,1], si la "
                    "calibracion movio el AUPRC, o si la atribucion local no trae una fila "
                    "por transaccion del test.",
        "semilla": d["seed"],
    },
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "Mac local (laboratorio). Simulacion exacta, sin QPU.",
              "gasto_usd": 0.0},
    "porque": {"question": "¿que aporta cada variable a cada prediccion del brazo cuantico, "
                           "y se mueve la metrica si alguna deja de informar?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}
_yo = os.path.basename(__file__); _mi = sha(__file__)
copias = [(ART, os.path.join(EV, "code", "resultado_hsbc_atribucion@%s.json" % sha(ART)[:8])),
          (NPZ, os.path.join(EV, "code", "scores_atr_atribucion@%s.npz" % sha(NPZ)[:8])),
          (CORRER, os.path.join(EV, "code", "_correr_atribucion@%s.sh" % sha(CORRER)[:8])),
          (HARNESS, os.path.join(EV, "code", "hsbc_harness@%s.py" % sha(HARNESS)[:8])),
          (__file__, os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8])))]
copias = [(a, b) for a, b in copias if not os.path.exists(b)] + \
         [(a, b) for a, b in copias if os.path.exists(b) and sha(a) == sha(b)]
vistos = set(); copias = [(a, b) for a, b in copias if not (b in vistos or vistos.add(b))]
exigir_procedencia(doc, extra=tuple(p for p, _ in copias))
rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(EV, "runs", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
for s_, d_ in copias:
    if not os.path.exists(d_): shutil.copy2(s_, d_)
    assert sha(s_) == sha(d_)
assert rs.verify(json.load(open(dst)))
print("SELLADO:", doc["meta"]["content_hash"])
print("  probabilidad calibrada en [0,1]: %s   AUPRC intacto: %.6f"
      % (S52["fraud_probability"]["en_0_1"], AUPRC_PRIM))
b = S52["binary_prediction"]["umbral_F1_optimo_en_train"]
print("  binaria (umbral del train): P=%.3f R=%.3f F1=%.3f, %d positivos"
      % (b["precision"], b["recall"], b["F1"], b["predichos_positivos"]))
print("  atribucion local: %d x %d" % (loc.shape[0], loc.shape[1]))
print("  permutacion:", PERM["LECTURA"][:110])
for _, d_ in copias: print("  publicado:", os.path.relpath(d_, EV))
