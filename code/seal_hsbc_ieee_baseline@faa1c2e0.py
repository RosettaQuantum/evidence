#!/usr/bin/env python3
"""Sella el baseline clasico sobre IEEE-CIS con particion temporal.

QUE ES Y QUE NO ES
------------------
Es una MEDICION, no una comparacion. Sella lo que un clasico afinado consigue sobre el
benchmark designado, con el corte temporal que el pre-registro fija. NO sella ninguna
comparacion contra el 0,9459 publicado — esa cifra se midio sobre el test PRIVADO de
Kaggle, cuyas etiquetas no existen fuera de Kaggle, asi que no es el mismo test y la
comparacion pertenece al entregable con su metodologia declarada, no a un sello.

LO QUE HACE DISTINTO A ESTE ARTEFACTO
-------------------------------------
El corte temporal viaja MEDIDO adentro: max(train), min(test), la desigualdad resuelta, y
las dos ventanas en dias. «El test es el futuro» deja de ser una intencion del diseno y
pasa a ser una comparacion que el lector hace de un vistazo. Y el harness ABORTA si el
corte no se cumple: un solape daria cifras de aspecto normal respondiendo a otra pregunta.

NINGUN DATO DE IEEE-CIS ENTRA AL REPOSITORIO. Kaggle §7.B prohibe redistribuirlo; los seis
archivos estan declarados en PROCEDENCIA-EN-FUENTE-DE-TERCEROS.md con su receta. Lo que se
publica son los SCORES del test —y_true e y_score— que son producto nuestro y permiten
recomputar ambas curvas sin el dataset.

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

ART = os.path.join(AQUI, "ieee_baseline.json")
HARNESS = os.path.join(EV, "harness", "hsbc_harness.py")
CORRER = os.path.join(AQUI, "correr_ieee.sh")
SCORES = sorted(glob.glob(os.path.join(AQUI, "ieee_*.npz")))
d = json.load(open(ART))

PRE = glob.glob(os.path.join(EV, "prereg", "2026", "08", "*HSBC-001*.json"))[0]
MAN = glob.glob(os.path.join(EV, "manifests", "*IEEE*.json"))[0]
pre, man = json.load(open(PRE)), json.load(open(MAN))
assert rs.verify(pre) and rs.verify(man)

# ------------------------------------------------------------------ GUARDIAS
if d["harness_sha256"] != sha(HARNESS):
    raise SystemExit("ABORTA: el artefacto declara harness %s y el publicado es %s — se "
                     "sellaria un instrumento distinto del que produjo el dato"
                     % (d["harness_sha256"][:16], sha(HARNESS)[:16]))
if d["datos_sha256"] != man["w6"]["que"]["medido_por_el_laboratorio"]["inventario"][0]["sha256"].split(":")[-1] \
        and d["datos_sha256"] not in json.dumps(man, ensure_ascii=False):
    raise SystemExit("ABORTA: el sha del dato no aparece en el manifiesto sellado")
ct = d["particion"]["corte_temporal"]
if not ct["min_test_mayor_o_igual_que_max_train"]:
    raise SystemExit("ABORTA: el corte no es temporal — min(test) < max(train)")
if d["dataset"] != "ieee":
    raise SystemExit("ABORTA: el artefacto no es de IEEE-CIS sino de %r" % d["dataset"])
if not SCORES:
    raise SystemExit("ABORTA: faltan los scores crudos; sin ellos el lector no puede "
                     "recomputar las curvas sin el dataset, que no podemos publicar")

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
NOMBRE = ("RosettaQ__RUN__RQ-EXP-HSBC-IEEE-001__%s__"
          "baseline-clasico-ieee-cis-particion-temporal.json" % STAMP)
mejor = max(d["modelos"], key=lambda m: d["modelos"][m]["AUPRC"])
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-EXP-HSBC-IEEE-001", "type": "RUN", "is_demo": False,
    "scope_note": "Baseline clasico sobre el dataset de BENCHMARK del track HSBC "
                  "(IEEE-CIS), con la particion temporal que fija el pre-registro. Es una "
                  "MEDICION, no una comparacion: no sella ningun contraste contra cifras "
                  "publicadas de terceros.",
    "prereg": {"file_id": pre["meta"]["file_id"], "content_hash": pre["meta"]["content_hash"]},
    "manifest": {"file_id": man["meta"]["file_id"], "content_hash": man["meta"]["content_hash"]},
}, "w6": {
    "que": {
        "artefacto": {"archivo": "ieee_baseline.json", "sha256": "sha256:" + sha(ART),
                      "publicado_como": "code/ieee_baseline@%s.json" % sha(ART)[:8]},
        "modelos": d["modelos"],
        "mejor_por_AUPRC": {"modelo": mejor, "AUPRC": d["modelos"][mejor]["AUPRC"],
                            "IC95": d["modelos"][mejor]["AUPRC_IC95"],
                            "AUC_ROC": d["modelos"][mejor]["AUC_ROC"]},
        "particion": d["particion"],
        "EL_CORTE_ES_EL_FUTURO": {
            "max_train": ct["max_train"], "min_test": ct["min_test"],
            "se_cumple": ct["min_test_mayor_o_igual_que_max_train"],
            "ventana_de_test_dias": ct["ventana_de_test_dias"],
            "por_que_viaja_aqui": "«el test es el futuro» no es una intencion del diseno: "
                "es una desigualdad entre dos numeros. Dentro del artefacto, el lector la "
                "comprueba de un vistazo sin re-correr nada. Y el harness aborta si no se "
                "cumple: un solape daria cifras de aspecto normal respondiendo a otra "
                "pregunta, y nadie lo notaria mirando el AUPRC.",
        },
        "contraste_con_ULB_medido_con_la_misma_regla": {
            "ULB_ventana_de_test_horas": 7.65, "IEEE_ventana_de_test_dias": ct["ventana_de_test_dias"],
            "ULB_cambio_de_tasa_pct": -28.0,
            "IEEE_cambio_de_tasa_pct": ct["cambio_relativo_de_la_tasa_pct"],
            "lectura": "IEEE-CIS abre 41,88 dias de futuro real con la tasa moviendose "
                       "2,1 %; ULB abre 7,65 horas con la tasa cayendo 28 %. La misma "
                       "regla aplicada a los dos.",
        },
        "IEEE_es_mas_dificil_que_ULB": {
            "AUPRC_IEEE": d["modelos"][mejor]["AUPRC"], "AUPRC_ULB": 0.800822,
            "tasa_de_fraude_IEEE": d["particion"]["train"]["tasa"],
            "tasa_de_fraude_ULB": 0.00183,
            "lectura": "el fraude es 19 veces mas frecuente en IEEE-CIS y aun asi se "
                       "predice peor. No depende de compararse con nadie.",
        },
        "lo_que_este_sello_NO_afirma": "nada sobre el 0,9459 que el statement cita como "
            "referencia. Esa cifra es el primer lugar de la competencia de Kaggle, medida "
            "sobre SU test privado —cuyas etiquetas no existen fuera de Kaggle, hecho "
            "declarado en el manifiesto— con un ensamble de tres modelos entre 6.381 "
            "equipos. No es el mismo test que el nuestro y la comparacion pertenece al "
            "entregable, con la metodologia declarada que el propio statement exige.",
        "decisiones_no_prefijadas": {
            "codificacion_de_categoricas": d["columnas_categoricas"],
            "por_que_solo_con_el_train": "ajustarla sobre el dataset completo seria mirar "
                "el futuro, que es exactamente lo que la particion temporal impide.",
        },
        "cruce_ventaja_cuantica": 0,
    },
    "como": {
        "harness": {"archivo": "hsbc_harness.py", "sha256": "sha256:" + sha(HARNESS),
                    "publicado_como": "code/hsbc_harness@%s.py" % sha(HARNESS)[:8]},
        "comando": {"archivo": "correr_ieee.sh", "sha256": "sha256:" + sha(CORRER),
                    "publicado_como": "code/correr_ieee@%s.sh" % sha(CORRER)[:8],
                    "por_que_un_script": "las variables van DENTRO. Pasadas por linea de "
                        "comando se olvidan —paso— y macOS ademas borra las DYLD_* al "
                        "cruzar env o nohup: el arreglo funciona en la prueba y se pierde "
                        "en la corrida desatendida."},
        "scores_crudos": [{"archivo": os.path.basename(p), "sha256": "sha256:" + sha(p),
                           "publicado_como": "code/%s@%s.npz" % (os.path.basename(p)[:-4], sha(p)[:8])}
                          for p in SCORES],
        "por_que_los_scores": "el dataset NO se puede republicar (Kaggle §7.B), asi que se "
            "publican y_true e y_score del test: con ellos se recomputan AUPRC, AUC y "
            "cualquier umbral sin tener el dato.",
        "entorno": d["lib_versions"], "openmp": d["openmp"],
        "semilla": d["seed"], "bootstrap": "2.000 remuestreos, semilla 42",
    },
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "Mac local. NO pudo correr en CI: el dataset no se puede "
                         "redistribuir, asi que no puede subirse al runner."},
    "porque": {"question": "¿que consigue un clasico afinado sobre IEEE-CIS cuando el test "
                           "es futuro real y no una muestra barajada?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}
_yo = os.path.basename(__file__); _mi = sha(__file__)
copias = [(ART, os.path.join(EV, "code", "ieee_baseline@%s.json" % sha(ART)[:8])),
          (HARNESS, os.path.join(EV, "code", "hsbc_harness@%s.py" % sha(HARNESS)[:8])),
          (CORRER, os.path.join(EV, "code", "correr_ieee@%s.sh" % sha(CORRER)[:8])),
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
print("  mejor por AUPRC: %s %.4f %s" % (mejor, d["modelos"][mejor]["AUPRC"],
                                          d["modelos"][mejor]["AUPRC_IC95"]))
print("  corte: min(test) %.0f >= max(train) %.0f  -> %s"
      % (ct["min_test"], ct["max_train"], ct["min_test_mayor_o_igual_que_max_train"]))
for _, d_ in copias: print("  publicado:", os.path.relpath(d_, EV))
