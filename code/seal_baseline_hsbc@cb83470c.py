#!/usr/bin/env python3
"""Sella el BASELINE clasico del track HSBC — el numero principal del entregable.

Se sella tarde y eso se declara: el artefacto existia desde el 20-ago y viajaba citado
por los sellos del ataque, pero sin sello propio. Lo cazo la sesion de coordinacion
leyendo el entregable contra el archivo. El artefacto no cambio: solo faltaba certificar
lo que afirma.
"""
import glob, hashlib, json, os, sys
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))
import rosettaq_seal as rs
from reloj_sello import ahora_stamp, ahora_iso

R = os.path.join(RAIZ, "evidence", "resultados_hsbc")
f = glob.glob(os.path.join(R, "hsbc_ulb_baseline_lightgbm-xgboost@*.json"))[0]
h = hashlib.sha256(open(f, "rb").read()).hexdigest()
assert h.startswith(os.path.basename(f).split("@")[1][:8]), "el @ no calza"
d = json.load(open(f))
X, L = d["modelos"]["xgboost"], d["modelos"]["lightgbm"]
P = d["particion"]

# los scores crudos recomputan las metricas: se comprueba AQUI, no se afirma
recomp = {}
for m in ("xgboost", "lightgbm"):
    z = np.load(glob.glob(os.path.join(R, "scores_%s@*.npz" % m))[0])
    y, p = z["y_true"], z["y_score"]
    recomp[m] = {"AUPRC": float(average_precision_score(y, p)),
                 "AUC_ROC": float(roc_auc_score(y, p))}
    for k in ("AUPRC", "AUC_ROC"):
        if abs(recomp[m][k] - d["modelos"][m][k]) > 5e-5:
            raise SystemExit("%s %s no recomputa: %.6f vs %.6f"
                             % (m, k, recomp[m][k], d["modelos"][m][k]))

STAMP = ahora_stamp()
FILE_ID = "RQ-EXP-HSBC-BASE-001"
NOMBRE = ("RosettaQ__RUN__%s__%s__baseline-clasico-ulb-particion-temporal.json"
          % (FILE_ID, STAMP))
doc = {"meta": {
    "file_name": NOMBRE, "file_id": FILE_ID, "type": "RUN", "is_demo": False,
    "scope_note": "Baseline clasico del track HSBC sobre ULB con particion TEMPORAL "
                  "80/20: el numero principal del entregable. Sellado por el "
                  "laboratorio; el anclaje es del notario.",
    "prereg": {"file_id": "RQ-PREREG-HSBC-001",
               "content_hash": "sha256:b04f214fae845b1c50431d225e6590b0956d8920c24b7c7f"
                               "a26ed94c58f3f2db"},
    "manifest": "RQ-DATA-HSBC-ULB-001",
    "POR_QUE_SE_SELLA_TARDE": "el artefacto se produjo el 20-ago y quedo citado dentro de "
            "los sellos del ataque, pero sin sello propio — el unico numero principal del "
            "entregable sin certificar. Lo encontro la sesion de coordinacion leyendo el "
            "documento contra el archivo. El artefacto NO cambio: su sha256 es el mismo "
            "que citan RQ-PREREG-HSBC-002-ATAQUE y RQ-EXP-HSBC-ATAQUE-001, asi que este "
            "sello certifica exactamente lo que ya circulaba.",
}, "w6": {
    "que": {
        "artefacto": {"archivo": "resultados_hsbc/" + os.path.basename(f),
                      "sha256": "sha256:" + h},
        "resultado_principal_xgboost": {
            "AUPRC": X["AUPRC"], "AUPRC_IC95": X["AUPRC_IC95"],
            "AUC_ROC": X["AUC_ROC"], "AUC_IC95": X["AUC_IC95"],
            "F1_umbral_0.5": X["F1_umbral_0.5"], "confusion_0.5": X["confusion_0.5"],
            "metrica_que_manda": "AUPRC (sellado en el prereg): con prevalencia 0,17 % el "
                                 "AUC-ROC es opticamente generoso",
        },
        "lightgbm_ABIERTO": {
            "AUPRC": L["AUPRC"], "falsos_positivos_umbral_0.5": L["confusion_0.5"]["fp"],
            "estado": "NO es un baseline afinado: la configuracion v1 del laboratorio lo "
                      "rompe. Defecto de configuracion NUESTRA, no del metodo. No entra al "
                      "entregable como baseline hasta pasar la busqueda declarada; si al "
                      "final no entra, se dice por que en vez de desaparecer.",
        },
        "particion": {"tipo": "temporal 80/20 por Time",
                      "train": P["train"], "test": P["test"],
                      "duplicados_exactos_entre_mitades": P["solape_de_contenido_duplicados_exactos"],
                      "determinismo_entre_maquinas": "el sha256 del test es identico en el "
                              "Mac local y en el runner de CI"},
        "recomputo_desde_scores_crudos": {
            "hecho_en_este_sellado": True, "tolerancia": "5e-5",
            "xgboost": {k: round(v, 6) for k, v in recomp["xgboost"].items()},
            "lightgbm": {k: round(v, 6) for k, v in recomp["lightgbm"].items()},
            "como": "los .npz publicados por hash permiten a un tercero rehacer las curvas "
                    "exactas; se ejercio antes de sellar, no se afirmo."},
        "contexto_de_validacion": "el IC95 del AUPRC contiene el 0,871 publicado, asi que "
                "NO se afirma diferencia contra ese numero; la evidencia del efecto de "
                "protocolo es el delta intra-implementacion de RQ-EXP-HSBC-ATAQUE-001.",
        "cruce_ventaja_cuantica": "0 (fase enteramente clasica)",
    },
    "como": {"modelo": "XGBoost, config declarada en el artefacto",
             "harness_sha256": d["harness_sha256"],
             "compute": "GitHub Actions (experimento-hsbc.yml)",
             "lib_versions": d.get("lib_versions")},
    "cuando": {"archived_at": ahora_iso()},
    "donde": {"compute": "CI de evidence", "verificacion": "Mac local (laboratorio)"},
    "porque": {"question": "¿que da un clasico afinado sobre ULB con particion temporal, "
                           "con el protocolo fijado antes de mirar?",
               "para_que": "es la referencia contra la que se mide todo lo demas del track "
                           "y el numero principal del entregable."},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}
rs.seal(doc, harness=("hsbc_harness.py", "1.0.0", "sha256:" + d["harness_sha256"]),
        sealed_at=ahora_iso(), schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(RAIZ, "evidence", "runs", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
assert rs.verify(json.load(open(dst)))
import shutil
h8 = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:8]
shutil.copy2(__file__, os.path.join(RAIZ, "evidence", "code",
                                    "seal_baseline_hsbc@%s.py" % h8))
print("SELLADO %s  %s" % (FILE_ID, doc["meta"]["content_hash"]))
print("  stamp del reloj: %s" % STAMP)
print("  AUPRC %.4f | AUC %.4f | F1 %.4f — recomputados desde los scores antes de sellar"
      % (X["AUPRC"], X["AUC_ROC"], X["F1_umbral_0.5"]))
print("  capa 1: code/seal_baseline_hsbc@%s.py" % h8)
