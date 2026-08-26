#!/usr/bin/env python3
"""Sella el brazo cuantico del track HSBC: kernel de fidelidad en simulacion exacta sobre ULB.

QUE SELLA
---------
Un resultado NEGATIVO, medido contra el criterio que el pre-registro fijo antes de mirar:
el intervalo del brazo cuantico queda entero por debajo del clasico sellado. El propio
pre-registro dice que «los dos desenlaces son entregables», asi que esto se publica igual.

LO QUE LA SIMULACION EXACTA NO PUEDE RESPONDER
----------------------------------------------
Nada sobre hardware con ruido — no se corrio ninguno, y el pre-registro autoriza US$0.
El numero de aqui es un TECHO: con el mismo mapa, la version ruidosa no puede superar a la
exacta. Que no haya ventaja aqui cierra el caso; que la hubiera no la probaria en hardware.

LOS CONTROLES NO ESTAN PRE-REGISTRADOS
--------------------------------------
Se decidieron despues de ver el primario y el artefacto lo dice en un campo propio. Existen
porque «el kernel cuantico pierde» y «le dimos 37 positivos en vez de 417» son conclusiones
distintas, y el numero primario solo no las separa. No modifican el resultado primario.

Costo US$0: local, sin backend de pago, sin QPU.
"""
import hashlib, json, os, shutil, sys, glob
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

LAB = os.path.join(RAIZ, "lab-hsbc-2026-08-20")
ART = os.path.join(LAB, "resultado_hsbc_cuantico.json")
HARNESS = os.path.join(EV, "harness", "hsbc_harness.py")
CORRER = os.path.join(LAB, "_correr_cuantico.sh")
SCORES = sorted(glob.glob(os.path.join(LAB, "scores_q_*.npz")))
d = json.load(open(ART))

PRE = glob.glob(os.path.join(EV, "prereg", "2026", "08", "*HSBC-003-CUANTICO*.json"))[0]
MAN = glob.glob(os.path.join(EV, "manifests", "*ULB*.json"))[0]
BASE = glob.glob(os.path.join(EV, "runs", "2026", "08", "*HSBC-BASE-001*.json"))[0]
pre, man, base = (json.load(open(x)) for x in (PRE, MAN, BASE))
for x, n in ((pre, "prereg"), (man, "manifiesto"), (base, "basal")):
    if not rs.verify(x): raise SystemExit("ABORTA: el %s no verifica" % n)

# EL BASAL SE LEE DEL SELLO, NO SE TECLEA. Nueve veces en este proyecto el defecto fue
# comparar contra un valor escrito a mano en vez de contra el que el objeto produce.
B = base["w6"]["que"]["resultado_principal_xgboost"]
B_AUPRC, B_IC = B["AUPRC"], B["AUPRC_IC95"]
Q = d["modelos"]["kernel_cuantico"]
Q_AUPRC, Q_IC = Q["AUPRC"], Q["AUPRC_IC95"]

# ------------------------------------------------------------------ GUARDIAS
if d["harness_sha256"] != sha(HARNESS):
    raise SystemExit("ABORTA: el artefacto declara harness %s y el publicado es %s"
                     % (d["harness_sha256"][:16], sha(HARNESS)[:16]))
if d["dataset"] != "ulb" or d["brazo"] != "cuantico":
    raise SystemExit("ABORTA: el artefacto no es el brazo cuantico sobre ULB: %r / %r"
                     % (d["dataset"], d["brazo"]))
if not d["particion"]["corte_temporal"]["min_test_mayor_o_igual_que_max_train"]:
    raise SystemExit("ABORTA: el corte no es temporal")
# EL MISMO TEST, COMPROBADO POR HASH — no por afirmacion. Si el brazo cuantico se hubiera
# evaluado sobre otro test, los dos intervalos no serian comparables y el veredicto no
# significaria nada. Es la condicion que Nicholas puso por escrito antes de autorizar.
if d["particion"]["test"]["sha256"] != base["w6"]["que"]["particion"]["test"]["sha256"]:
    raise SystemExit("ABORTA: el test NO es el mismo del basal (%s vs %s) — una comparacion "
                     "sobre otro test no es una comparacion"
                     % (d["particion"]["test"]["sha256"][:16],
                        base["w6"]["que"]["particion"]["test"]["sha256"][:16]))
_semilla_basal = base["w6"].get("como", {}).get("semilla")
if _semilla_basal is not None and d["seed"] != _semilla_basal:
    raise SystemExit("ABORTA: el basal uso semilla %r y este brazo %r — con remuestreos "
                     "distintos los intervalos no son comparables"
                     % (_semilla_basal, d["seed"]))
if d["simulacion"]["gasto_usd"] != 0.0 or pre["w6"]["que"]["GASTO_AUTORIZADO_USD"] != 0:
    raise SystemExit("ABORTA: el pre-registro autoriza US$0 y el artefacto declara %r"
                     % d["simulacion"]["gasto_usd"])
# La guardia del mapa viaja MEDIDA adentro: sin ella, «kernel cuantico» seria una etiqueta.
if not (d["simulacion"]["max_dif_statevector"] < 1e-10
        and d["simulacion"]["max_dif_kernel"] < 1e-12):
    raise SystemExit("ABORTA: el statevector no coincide con el ZZFeatureMap de la libreria")
if d["controles_exploratorios"]["PRE_REGISTRADOS"] is not False:
    raise SystemExit("ABORTA: los controles se decidieron despues de ver el primario y el "
                     "artefacto tiene que decirlo")
if not SCORES:
    raise SystemExit("ABORTA: faltan los scores crudos del test")

# EL VEREDICTO SE CALCULA, NO SE ESCRIBE.
def contra_basal(ic):
    if ic[0] > B_IC[1]: return "POR ENCIMA"
    if ic[1] < B_IC[0]: return "POR DEBAJO"
    return "SOLAPA"
VEREDICTO = contra_basal(Q_IC)
CRUCE = 1 if VEREDICTO == "POR ENCIMA" else 0
if CRUCE:
    raise SystemExit("ABORTA: el sellador esta escrito para un negativo y midio un cruce. "
                     "Un resultado positivo pasa por revision antes de sellarse.")

ctrl = d["controles_exploratorios"]["resultados"]
A1 = ctrl["A1_rbf_mismo_dato_mismas_features"]
A2 = ctrl["A2_xgboost_mismo_dato_mismas_features"]
CB = ctrl["B_cuantico_con_los_417_fraudes"]
# ¿le gana siquiera al RBF? Con NUESTRA regla, aplicada contra nosotros mismos.
GANA_AL_RBF = Q_IC[0] > A1["AUPRC_IC95"][1]

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
NOMBRE = ("RosettaQ__RUN__RQ-EXP-HSBC-Q-001__%s__"
          "brazo-cuantico-kernel-fidelidad-simulacion-exacta--sin-ventaja.json" % STAMP)

doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-EXP-HSBC-Q-001", "type": "RUN", "is_demo": False,
    "scope_note": "Brazo cuantico del track HSBC: kernel de fidelidad en simulacion exacta "
                  "sobre ULB, contra el clasico sellado, mismo test y mismo bootstrap. "
                  "RESULTADO NEGATIVO: no hay ventaja. Se publica porque el pre-registro "
                  "declaro de antemano que los dos desenlaces son entregables.",
    "prereg": {"file_id": pre["meta"]["file_id"], "content_hash": pre["meta"]["content_hash"]},
    "manifest": {"file_id": man["meta"]["file_id"], "content_hash": man["meta"]["content_hash"]},
    "compara_contra": {"file_id": base["meta"]["file_id"],
                       "content_hash": base["meta"]["content_hash"]},
}, "w6": {
    "que": {
        "artefacto": {"archivo": os.path.basename(ART), "sha256": "sha256:" + sha(ART),
                      "publicado_como": "code/resultado_hsbc_cuantico@%s.json" % sha(ART)[:8]},
        "VEREDICTO": {
            "cruce_ventaja_cuantica": CRUCE,
            "lectura": "el intervalo del brazo cuantico queda %s del clasico sellado. Por el "
                       "criterio pre-registrado —AUPRC sobre el test completo, IC95 por "
                       "bootstrap de 2.000 remuestreos con semilla 42, sin solape— NO hay "
                       "ventaja." % VEREDICTO.lower(),
            "cuantico": {"AUPRC": Q_AUPRC, "IC95": Q_IC, "AUC_ROC": Q["AUC_ROC"]},
            "clasico_sellado": {"AUPRC": B_AUPRC, "IC95": B_IC,
                                "leido_de": base["meta"]["file_id"]},
            "mismo_test_comprobado_por_hash": d["particion"]["test"]["sha256"],
        },
        "LO_QUE_LA_SIMULACION_EXACTA_NO_RESPONDE": d["simulacion"]["lo_que_NO_responde"],
        "decisiones_declaradas_antes_de_mirar_el_test": d["decisiones_declaradas_antes"],
        "EL_HANDICAP_Y_POR_QUE_NO_EXPLICA_EL_RESULTADO": {
            "el_handicap": "el statement exige muestreo estratificado. Al 0,183 %% de fraude, "
                "un soporte de %d puntos deja %d positivos, contra los %d con que se entreno "
                "el clasico. Es una desventaja real y del protocolo, no del metodo."
                % (d["decisiones_declaradas_antes"]["D4_soporte"]["n"],
                   d["decisiones_declaradas_antes"]["D4_soporte"]["fraudes"],
                   int(d["particion"]["train"]["fraudes"])),
            "por_que_no_explica_el_resultado": "porque se midio. Con LA MISMA muestra "
                "mutilada y LAS MISMAS 8 features, un xgboost llega a %.4f %s, cuyo "
                "intervalo se solapa con el del basal: el muestreo estratificado le costo al "
                "metodo clasico algo que ni siquiera es detectable. Y quitandole el handicap "
                "por completo al brazo cuantico —los %d fraudes, soporte no estratificado— "
                "sube a %.4f %s y sigue por debajo del basal."
                % (A2["AUPRC"], A2["AUPRC_IC95"], int(d["particion"]["train"]["fraudes"]),
                   CB["AUPRC"], CB["AUPRC_IC95"]),
            "por_que_esto_esta_aqui": "sin esta medicion, «el kernel cuantico pierde» y «le "
                "dimos 37 positivos» son indistinguibles, y publicar el primero seria un "
                "reporte falso aunque el numero fuera correcto.",
        },
        "TAMPOCO_LE_GANA_AL_RBF": {
            "cuantico_IC95": Q_IC, "rbf_IC95": A1["AUPRC_IC95"],
            "gana": GANA_AL_RBF,
            "lectura": "con el mismo dato, las mismas features y el mismo clasificador, el "
                "kernel cuantico da %.4f y el RBF %.4f. Los intervalos SE TOCAN, asi que por "
                "la misma regla que usamos para negar la ventaja cuantica frente al basal, "
                "tampoco podemos afirmar que le gane al RBF. La regla se aplica contra "
                "nosotros mismos o no es una regla."
                % (Q_AUPRC, A1["AUPRC"]) if not GANA_AL_RBF else
                "los intervalos no se tocan: supera al RBF en igualdad de condiciones.",
            "ninguno_de_los_dos_fue_afinado": "ni el kernel cuantico ni el RBF llevan busqueda "
                "de hiperparametros. C=1 y gamma='scale' son los valores por defecto.",
        },
        "controles_exploratorios": d["controles_exploratorios"],
        "particion": d["particion"],
        "cruce_ventaja_cuantica": CRUCE,
    },
    "como": {
        "harness": {"archivo": "hsbc_harness.py", "sha256": "sha256:" + sha(HARNESS),
                    "publicado_como": "code/hsbc_harness@%s.py" % sha(HARNESS)[:8]},
        "comando": {"archivo": os.path.basename(CORRER), "sha256": "sha256:" + sha(CORRER),
                    "publicado_como": "code/_correr_cuantico@%s.sh" % sha(CORRER)[:8]},
        "scores_crudos": [{"archivo": os.path.basename(p), "sha256": "sha256:" + sha(p),
                           "publicado_como": "code/%s@%s.npz"
                                             % (os.path.basename(p)[:-4], sha(p)[:8])}
                          for p in SCORES],
        "el_ejecutor_del_mapa": {
            "que_es": "statevector propio en numpy — Walsh-Hadamard rapida mas dos "
                      "diagonales de fase.",
            "verificado_contra": d["simulacion"]["verificado_contra"],
            "max_dif_statevector": d["simulacion"]["max_dif_statevector"],
            "max_dif_kernel": d["simulacion"]["max_dif_kernel"],
            "LO_QUE_LA_GUARDIA_ENCONTRO": "la primera version daba max|dK|=3e-15 y "
                "max|dpsi|=4,1e-01: el kernel coincidia y el estado no. Yo habia escrito la "
                "fase como exp(+i phi Z); qiskit la implementa con puertas P(2phi), que es "
                "exp(-i phi Z) salvo fase global — mi estado era el CONJUGADO del suyo. Como "
                "|<conj a|conj b>|^2 = |<a|b>|^2, el numero que iba al resultado era correcto "
                "por accidente mientras el objeto era otro. Una guardia que solo comparara el "
                "kernel habria dejado pasar esto entero.",
        },
        "DESVIACIONES_DEL_PRE_REGISTRO": [
            {"declarado": "PennyLane/statevector",
             "ejecutado": "statevector propio en numpy, verificado contra el ZZFeatureMap de "
                          "qiskit a 2,8e-15 en el estado y 3,3e-15 en el kernel",
             "por_que": "por velocidad. No se agrego ademas una verificacion contra "
                        "PennyLane porque habria que transcribir el mapa a mano, y comparar "
                        "mi numpy contra mi transcripcion es comparar mi codigo con mi "
                        "codigo: la comprobacion contra el objeto que construye la libreria "
                        "desde su propia definicion es estrictamente mas fuerte.",
             "afecta_al_veredicto": False},
            {"declarado": "CI de evidence",
             "ejecutado": "Mac local (laboratorio)",
             "por_que": "no se ejecuto el paso de CI. El basal sellado corrio en CI con "
                        "verificacion local, asi que los dos brazos NO corrieron en el mismo "
                        "entorno.",
             "afecta_al_veredicto": False,
             "por_que_no_afecta": "el test es el mismo, comprobado por hash, y el bootstrap "
                 "usa la misma semilla sobre ese mismo test. La diferencia de entorno mueve "
                 "el clasico del orden de 0,002 (local 0,798951 vs CI 0,800822) frente a una "
                 "brecha de 0,54 entre los dos brazos. Queda pendiente reproducirlo en CI.",
             "pendiente": "reproducir el brazo cuantico en CI de evidence"},
        ],
        "reproducibilidad": "la corrida se repitio entera y dio el primario identico "
            "—AUPRC %.4f, mismo IC, mismos 945 vectores de soporte." % Q_AUPRC,
        "entorno": d["lib_versions"], "semilla": d["seed"],
        "bootstrap": "2.000 remuestreos, semilla 42, sobre el MISMO test que el basal; una "
                     "sola implementacion compartida por los dos brazos, para que los "
                     "intervalos sean comparables.",
    },
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "Mac local (laboratorio). Ningun backend de pago, ninguna QPU.",
              "gasto_usd": 0.0},
    "porque": {"question": pre["w6"]["porque"]["question"]},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario; el "
                  "texto publico pasa por el OK de Nicholas."},
}}
_yo = os.path.basename(__file__); _mi = sha(__file__)
copias = [(ART, os.path.join(EV, "code", "resultado_hsbc_cuantico@%s.json" % sha(ART)[:8])),
          (HARNESS, os.path.join(EV, "code", "hsbc_harness@%s.py" % sha(HARNESS)[:8])),
          (CORRER, os.path.join(EV, "code", "_correr_cuantico@%s.sh" % sha(CORRER)[:8])),
          (__file__, os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8])))]
copias += [(p, os.path.join(EV, "code", "%s@%s.npz" % (os.path.basename(p)[:-4], sha(p)[:8])))
           for p in SCORES]
exigir_procedencia(doc, extra=tuple(p for p, _ in copias))
rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(EV, "runs", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
for _, d_ in copias: assert not os.path.exists(d_), d_
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
for s_, d_ in copias: shutil.copy2(s_, d_); assert sha(s_) == sha(d_)
assert rs.verify(json.load(open(dst)))
print("SELLADO:", doc["meta"]["content_hash"])
print("  veredicto: %s  (cruce=%d)" % (VEREDICTO, CRUCE))
print("  cuantico  %.6f %s" % (Q_AUPRC, Q_IC))
print("  clasico   %.6f %s   (leido de %s)" % (B_AUPRC, B_IC, base["meta"]["file_id"]))
print("  mismo test: %s" % d["particion"]["test"]["sha256"][:16])
print("  le gana al RBF:", GANA_AL_RBF)
for _, d_ in copias: print("  publicado:", os.path.relpath(d_, EV))
