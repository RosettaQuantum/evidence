#!/usr/bin/env python3
"""Sella la ERRATA de RQ-EXP-HSBC-Q-001. El original no se toca.

QUE CORRIGE
-----------
El artefacto del brazo cuantico trae `F1_umbral_0.5` y `confusion_0.5`. Esos campos aplican
un umbral de 0,5 a lo que devuelve `SVC.decision_function`, que son MARGENES y no
probabilidades: los nuestros van de -1,3810 a 1,0207. Un umbral de 0,5 sobre esa escala no
tiene el significado que tiene sobre una probabilidad, y NO es comparable con los mismos
campos del brazo clasico, donde el score si es probabilidad.

De ahi sale Precision 1,000 y Recall 0,040 — precision perfecta con TRES positivos predichos
de 56.962. Es el punto ultraconservador de una escala arbitraria, no una propiedad del
metodo, y en un entregable se lee como una fortaleza.

QUE NO CAMBIA: el veredicto. AUPRC y AUC son de ranking puro y ningun umbral los toca. El
brazo cuantico sigue en AUPRC 0,257453 con IC95 [0,154578 - 0,369107], por debajo del
clasico, y el «cruce = 0» se sostiene entero. Esta errata NO es una retractacion del
resultado.

LA CAUSA, que es nuestra: `evaluar()` se extrajo a UNA implementacion compartida justamente
para que los dos brazos usaran el mismo remuestreo y fueran comparables. Esa unificacion
aplica el mismo `p >= 0.5` a los dos — y para el cuantico eso no significa lo mismo.
Unificar para comparar fue lo que introdujo la incomparabilidad. El defecto solo aparece si
alguien mira la ESCALA en vez de confiar en el nombre del campo.

QUE USAR EN CAMBIO: la probabilidad calibrada a [0,1] (Platt sobre train disjunto del
soporte, nunca sobre el test) que produce el artefacto de atribucion, con su umbral elegido
en el train. Una errata que solo dice que algo estaba mal deja al lector sin nada.

GUARDIA: las cifras se recomputan desde los scores publicados antes de sellar. Si alguna
dejo de reproducir, aborta.

Lectura de artefactos y calculo local. Costo US$0.
"""
import hashlib, json, os, shutil, sys, glob
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes
from sklearn.metrics import (average_precision_score, roc_auc_score, precision_score,
                             recall_score, f1_score, confusion_matrix)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

ORIG = glob.glob(os.path.join(EV, "runs", "2026", "08", "*HSBC-Q-001*.json"))[0]
orig = json.load(open(ORIG))
if not rs.verify(orig):
    raise SystemExit("ABORTA: el artefacto original no verifica")
ART = os.path.join(EV, "code", "resultado_hsbc_cuantico@71e071ed.json")
SCORES = os.path.join(EV, "code", "scores_q_kernel_cuantico@091914f1.npz")
crudo = json.load(open(ART))
Q = crudo["modelos"]["kernel_cuantico"]

# ---------------- GUARDIA: recomputar desde lo PUBLICADO, no desde la memoria
z = np.load(SCORES)
y, s_ = z["y_true"], z["y_score"]
auprc = float(average_precision_score(y, s_)); auc = float(roc_auc_score(y, s_))
if round(auprc, 6) != Q["AUPRC"] or round(auc, 6) != Q["AUC_ROC"]:
    raise SystemExit("ABORTA: los scores publicados ya no reproducen el artefacto "
                     "(%.6f/%.6f vs %.6f/%.6f)" % (auprc, auc, Q["AUPRC"], Q["AUC_ROC"]))
yhat = (s_ >= 0.5).astype(int)
tn, fp, fn, tp = confusion_matrix(y, yhat).ravel()
if {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)} != Q["confusion_0.5"]:
    raise SystemExit("ABORTA: la confusion no reproduce")
PREC = float(precision_score(y, yhat, zero_division=0))
REC = float(recall_score(y, yhat, zero_division=0))
RANGO = [round(float(s_.min()), 4), round(float(s_.max()), 4)]
if RANGO[0] >= 0.0 and RANGO[1] <= 1.0:
    raise SystemExit("ABORTA: los scores SI estan en [0,1] — esta errata no tendria objeto")

# ---------------- lo que se propone usar en su lugar, medido del mismo modo
ATR = os.path.join(RAIZ, "lab-hsbc-2026-08-20", "scores_atr_atribucion.npz")
if not os.path.exists(ATR):
    raise SystemExit("ABORTA: falta el artefacto de atribucion con la probabilidad "
                     "calibrada. Una errata que no dice que usar en cambio deja al lector "
                     "sin nada.")
za = np.load(ATR, allow_pickle=True)
pr, bi = za["proba"], za["binaria"]
if round(float(average_precision_score(y, pr)), 6) != Q["AUPRC"]:
    raise SystemExit("ABORTA: la probabilidad calibrada NO reproduce el AUPRC sellado. Una "
                     "transformacion monotona no puede moverlo; si se movio, el ranking "
                     "cambio y la calibracion no sirve como reemplazo.")
tn2, fp2, fn2, tp2 = confusion_matrix(y, bi).ravel()
CAL = {"rango": [round(float(pr.min()), 6), round(float(pr.max()), 6)],
       "en_0_1": bool(pr.min() >= 0 and pr.max() <= 1),
       "AUPRC_identico_al_sellado": True,
       "umbral_elegido_en_el_train": {
           "predichos_positivos": int(bi.sum()),
           "precision": round(float(precision_score(y, bi, zero_division=0)), 6),
           "recall": round(float(recall_score(y, bi, zero_division=0)), 6),
           "F1": round(float(f1_score(y, bi, zero_division=0)), 6),
           "confusion": {"tn": int(tn2), "fp": int(fp2), "fn": int(fn2), "tp": int(tp2)}}}

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
NOMBRE = ("RosettaQ__ERRATA__RQ-ERRATA-EXP-HSBC-Q-001__%s__"
          "el-umbral-0-5-se-aplico-a-margenes-no-a-probabilidades.json" % STAMP)
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-ERRATA-EXP-HSBC-Q-001", "type": "ERRATA",
    "is_demo": False,
    "scope_note": "Errata de RQ-EXP-HSBC-Q-001. NO modifica el original: su archivo, su "
                  "hash y su ancla quedan intactos. Corrige el ALCANCE de dos campos de "
                  "umbral; el veredicto del experimento no cambia. Emision autorizada por "
                  "Nicholas.",
    "corrige": {"file_id": orig["meta"]["file_id"],
                "content_hash": orig["meta"]["content_hash"]},
}, "w6": {
    "que": {
        "campos_afectados": ["modelos.kernel_cuantico.F1_umbral_0.5",
                             "modelos.kernel_cuantico.confusion_0.5"],
        "que_esta_mal": "esos campos aplican un umbral de 0,5 a lo que devuelve "
            "SVC.decision_function, que son MARGENES y no probabilidades. Los del brazo "
            "cuantico van de %s a %s. Un 0,5 sobre esa escala no tiene el significado que "
            "tiene sobre una probabilidad, y NO es comparable con los mismos campos del "
            "brazo clasico, donde el score si es probabilidad." % (RANGO[0], RANGO[1]),
        "la_lectura_que_invita": {
            "precision_en_ese_punto": round(PREC, 6),
            "recall_en_ese_punto": round(REC, 6),
            "predichos_positivos": int(tp + fp),
            "de_un_test_de": int(len(y)),
            "por_que_engana": "precision de %s con %d positivos predichos de %d es el punto "
                "ultraconservador de una escala arbitraria, no una propiedad del metodo. En "
                "un entregable se lee como una fortaleza." % (round(PREC, 3), int(tp + fp),
                                                              len(y)),
        },
        "EL_VEREDICTO_NO_CAMBIA": {
            "AUPRC": Q["AUPRC"], "IC95": Q["AUPRC_IC95"], "AUC_ROC": Q["AUC_ROC"],
            "cruce_ventaja_cuantica": orig["w6"]["que"]["VEREDICTO"]["cruce_ventaja_cuantica"],
            "por_que": "AUPRC y AUC son de RANKING puro: ningun umbral los toca. Recomputados "
                "desde los scores publicados al sellar esta errata dan identicos. Esta "
                "errata NO es una retractacion del resultado; el brazo cuantico sigue por "
                "debajo del clasico y el negativo se sostiene entero.",
        },
        "LA_CAUSA_ES_NUESTRA": "evaluar() se extrajo a UNA implementacion compartida "
            "precisamente para que los dos brazos usaran el mismo remuestreo y sus "
            "intervalos fueran comparables. Esa misma unificacion aplica el mismo "
            "`p >= 0.5` a los dos, y para el cuantico eso no significa lo mismo. "
            "UNIFICAR PARA COMPARAR FUE LO QUE INTRODUJO LA INCOMPARABILIDAD. El defecto "
            "solo aparece si alguien mira la ESCALA de los numeros en vez de confiar en el "
            "nombre del campo — `F1_umbral_0.5` suena a lo que uno espera que sea.",
        "QUE_USAR_EN_CAMBIO": CAL,
        "QUE_NO_SE_RETRACTA": "nada del veredicto, nada de los controles, nada de la "
            "comparacion contra el basal. Se corrige el alcance de dos campos de umbral.",
        "como_se_encontro": "revisando la escala de nuestros propios scores antes de "
            "entregar, porque el enunciado del desafio pide «Fraud Probability: Float "
            "[0,1]» y hubo que comprobar si lo cumpliamos. No lo cumpliamos.",
        "cruce_ventaja_cuantica": 0,
    },
    "como": {
        "artefacto_original": {"archivo": os.path.basename(ART),
                               "sha256": "sha256:" + sha(ART),
                               "publicado_como": "code/" + os.path.basename(ART)},
        "scores_publicados": {"archivo": os.path.basename(SCORES),
                              "sha256": "sha256:" + sha(SCORES),
                              "publicado_como": "code/" + os.path.basename(SCORES)},
        "recomputo_al_sellar": {"AUPRC": round(auprc, 6), "AUC_ROC": round(auc, 6),
                                "confusion_0.5": {"tn": int(tn), "fp": int(fp),
                                                  "fn": int(fn), "tp": int(tp)},
                                "coincide_con_el_original": True},
        "guardias": "aborta si los scores publicados dejan de reproducir el artefacto, si "
                    "los scores resultaran estar en [0,1] (la errata no tendria objeto), o "
                    "si la probabilidad calibrada moviera el AUPRC.",
    },
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "Mac local (laboratorio). Sin backend de pago.", "gasto_usd": 0.0},
    "porque": {"question": "¿los campos de umbral del brazo cuantico significan lo que su "
                           "nombre sugiere?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "autorizacion": "emision de la errata autorizada por Nicholas",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}
_yo = os.path.basename(__file__); _mi = sha(__file__)
copias = [(__file__, os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8])))]
exigir_procedencia(doc, extra=tuple(p for p, _ in copias))
rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(EV, "reports", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
for _, d_ in copias: assert not os.path.exists(d_), d_
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
for s2, d_ in copias: shutil.copy2(s2, d_); assert sha(s2) == sha(d_)
assert rs.verify(json.load(open(dst)))
print("ERRATA SELLADA:", doc["meta"]["content_hash"])
print("  corrige:", orig["meta"]["file_id"], orig["meta"]["content_hash"][:23])
print("  scores en [%s, %s] -> NO son probabilidades" % (RANGO[0], RANGO[1]))
print("  el punto que invitaba: Precision %.3f Recall %.3f con %d positivos de %d"
      % (PREC, REC, int(tp + fp), len(y)))
print("  en su lugar (calibrado, umbral del train): Precision %.3f Recall %.3f F1 %.3f"
      % (CAL["umbral_elegido_en_el_train"]["precision"],
         CAL["umbral_elegido_en_el_train"]["recall"],
         CAL["umbral_elegido_en_el_train"]["F1"]))
print("  VEREDICTO INTACTO: AUPRC %.6f, cruce %d" % (Q["AUPRC"], 0))
for _, d_ in copias: print("  publicado:", os.path.relpath(d_, EV))
