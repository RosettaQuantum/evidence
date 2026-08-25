#!/usr/bin/env python3
"""Sella las dos mediciones nuevas del track Airbus, ANTES de regenerar el informe.

EL ORDEN IMPORTA Y ES LA LECCION DE LA v1
------------------------------------------
El §7 del informe declara las corridas selladas del track, derivandolo del archivo. Si se
sella el informe ANTES que estas dos, queda diciendo que hay dos corridas cuando hay
cuatro — que es exactamente como murio la v1, que se sello declarando que no estaba
sellada. Primero las mediciones, despues se regenera el informe, despues se sella.

QUE SE SELLA
------------
  RQ-EXP-AIRBUS-DETECCION-001  cuanto puede DETECTAR el caso del enunciado: un solver que
                               ignora el termino no lineal se equivoca 2,11e-15 sobre el
                               vortice —cero de maquina— y hasta 3,53 sobre la familia
                               reparada. 5 de 18 casos son ciegos, y son exactamente los
                               de una sola capa.
  RQ-EXP-AIRBUS-RANGO-001      que ve una red tensorial: la dimension de enlace se queda
                               en 2 mientras la no-linealidad recorre un factor de 3.400.
                               Incluye el control que MATA la hipotesis que traiamos.

Simulacion local. Costo US$0.
"""
import hashlib, json, os, shutil, sys, glob
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence"); AIR = os.path.join(AQUI, "airbus")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

DET = os.path.join(AIR, "umbral_de_deteccion.json")
RAN = os.path.join(AIR, "rango_vs_nolinealidad.json")
det, ran = json.load(open(DET)), json.load(open(RAN))
PRE = glob.glob(os.path.join(EV, "prereg", "2026", "08", "*AIRBUS*.json"))[0]
pre = json.load(open(PRE)); assert rs.verify(pre)
NOLIN = [p for p in glob.glob(os.path.join(EV, "runs", "**", "*.json"), recursive=True)
         if "AIRBUS-NOLIN" in p][0]
nolin = json.load(open(NOLIN)); assert rs.verify(nolin)

# ------------------------------------------------------------------ GUARDIAS
tgv = [f for f in det["tabla"] if f["variante"] == "tgv_statement"][0]
if tgv["detecta"]:
    raise SystemExit("ABORTA: el TGV detecta — la tesis del entregable no se sostiene")
if not det["resumen"]["todas_de_una_capa"]:
    raise SystemExit("ABORTA: la caracterizacion por capas no se sostiene")
if not ran["LA_IDENTIFICACION_SE_ROMPE"]:
    raise SystemExit("ABORTA: el control ya no rompe la identificacion — el artefacto "
                     "diria que publicamos un limite que no medimos")
for art, d in ((DET, det), (RAN, ran)):
    for n, h in d["producido_por_sha256"].items():
        p = os.path.join(AIR, n)
        if not os.path.isfile(p) or "sha256:" + sha(p) != h:
            raise SystemExit("ABORTA: %s declara %s con un hash que no calza" % (art, n))

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
COMUN = {"prereg": {"file_id": pre["meta"]["file_id"], "content_hash": pre["meta"]["content_hash"]},
         "continua": {"file_id": nolin["meta"]["file_id"],
                      "content_hash": nolin["meta"]["content_hash"],
                      "que_aporta": "aquel sello midio DONDE se anula la no-linealidad; "
                                    "estos dos miden que CUESTA que se anule."}}
CODIGO = [os.path.join(AIR, n) for n in ("airbus_harness.py", "airbus_carleman.py",
          "nolinealidad_donde_vive.py", "_procedencia.py", "umbral_de_deteccion.py",
          "rango_vs_nolinealidad.py")]

def bloque(p, d):
    return {"archivo": os.path.basename(p), "sha256": "sha256:" + sha(p),
            "publicado_como": "code/%s@%s.json" % (os.path.basename(p)[:-5], sha(p)[:8]),
            "contenido_determinista": {"valor": d["contenido_sha256"],
                                       "no_es_el_hash_de_un_archivo": True},
            "campos_no_reproducibles": d["campos_no_reproducibles"]}

docs = []
N1 = ("RosettaQ__RUN__RQ-EXP-AIRBUS-DETECCION-001__%s__"
      "que-puede-detectar-el-benchmark-del-enunciado.json" % STAMP)
docs.append((N1, {"meta": {
    "file_name": N1, "file_id": "RQ-EXP-AIRBUS-DETECCION-001", "type": "RUN",
    "is_demo": False,
    "scope_note": "Cuanto puede detectar el caso de prueba del enunciado, medido por "
                  "solucion manufacturada. Es una MEDICION SOBRE SU BENCHMARK, no una "
                  "opinion sobre el.", **COMUN}, "w6": {
    "que": {"artefacto": bloque(DET, det), "RESULTADO": det["RESULTADO"],
            "metodo": det["metodo"], "el_precio_declarado": det["el_precio_declarado"],
            "tabla": det["tabla"], "resumen": det["resumen"],
            "caracterizacion_de_la_clase_degenerada": det["caracterizacion_de_la_clase_degenerada"],
            "por_que_importa": "un caso de prueba sirve si separa un solver correcto de "
                "uno equivocado. Sobre el vortice del enunciado, un solver que ignora POR "
                "COMPLETO el termino no lineal da la respuesta exacta: el caso no puede "
                "distinguirlo. La virtud que lo hace un buen benchmark —tener solucion "
                "analitica exacta— y su punto ciego son el MISMO hecho.",
            "cruce_ventaja_cuantica": 0},
    "como": {"codigo": {os.path.basename(p): {"sha256": "sha256:" + sha(p)} for p in CODIGO}},
    "cuando": {"archived_at": ISO}, "donde": {"compute": "Mac local, sin red ni QPU"},
    "porque": {"question": "un solver que omita el termino no lineal, ¿da una respuesta "
                           "distinta sobre el caso del enunciado?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."}}}))

N2 = ("RosettaQ__RUN__RQ-EXP-AIRBUS-RANGO-001__%s__"
      "el-eje-de-memoria-es-ciego-al-de-no-linealidad.json" % STAMP)
docs.append((N2, {"meta": {
    "file_name": N2, "file_id": "RQ-EXP-AIRBUS-RANGO-001", "type": "RUN", "is_demo": False,
    "scope_note": "Que ve una red tensorial en la familia del enunciado. Incluye el "
                  "control construido para REFUTAR la hipotesis con la que se empezo, y "
                  "que la refuto.", **COMUN}, "w6": {
    "que": {"artefacto": bloque(RAN, ran),
            "decisiones_declaradas_antes_de_medir": ran["decisiones_declaradas_antes_de_medir"],
            "familia": ran["familia_del_enunciado"],
            "control_que_intenta_refutar": ran["control_que_intenta_refutar"],
            "LA_IDENTIFICACION_SE_ROMPE": ran["LA_IDENTIFICACION_SE_ROMPE"],
            "como_se_rompe": ran["como_se_rompe"],
            "correlacion": ran["correlacion"],
            "RESULTADO": "la dimension de enlace se queda en 2 en toda la familia "
                "perturbada mientras la no-linealidad recorre un factor de 3.400. Una red "
                "tensorial NO distingue el caso degenerado de los perturbados: le cuestan "
                "lo mismo. El eje de memoria —que el enunciado pide como entregable— es "
                "ciego al eje que dice querer probar.",
            "la_hipotesis_que_se_cayo": "se empezo con la idea de que «una sola capa» y "
                "«rango bajo» eran la misma propiedad. Se construyo el control que podia "
                "refutarla y la refuto: un producto de dos von Mises es rango 2, vive en "
                "40 capas y su no-linealidad NO es cero. Se publica porque un resultado "
                "que trae adentro el caso que lo limita es el que no se puede desarmar.",
            "un_defecto_del_propio_instrumento": "la primera version del Spearman usaba "
                "argsort(argsort(...)), que asigna rangos secuenciales a valores empatados "
                "segun el orden en que aparecen. Con chi constante devolvia +1,000: "
                "correlacion perfecta sobre una serie sin ninguna variacion, y habria "
                "confirmado la hipotesis con un numero redondo. Corregido con scipy, que "
                "promedia empates, y devolviendo None cuando no hay variacion.",
            "cruce_ventaja_cuantica": 0},
    "como": {"codigo": {os.path.basename(p): {"sha256": "sha256:" + sha(p)} for p in CODIGO}},
    "cuando": {"archived_at": ISO}, "donde": {"compute": "Mac local, sin red ni QPU"},
    "porque": {"question": "¿el rango necesario para representar el campo sube junto con "
                           "su no-linealidad?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lo_propuso": "la sesion de coordinacion; el laboratorio la objeto antes de "
                            "medirla y la medicion le dio la razon a la objecion.",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."}}}))

_yo = os.path.basename(__file__); _mi = sha(__file__)
copias = [(p, os.path.join(EV, "code", "%s@%s.py" % (os.path.basename(p)[:-3], sha(p)[:8])))
          for p in CODIGO if not os.path.exists(os.path.join(EV, "code", "%s@%s.py" % (os.path.basename(p)[:-3], sha(p)[:8])))]
copias += [(DET, os.path.join(EV, "code", "umbral_de_deteccion@%s.json" % sha(DET)[:8])),
           (RAN, os.path.join(EV, "code", "rango_vs_nolinealidad@%s.json" % sha(RAN)[:8])),
           (__file__, os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8])))]
salidas = []
for nombre, doc in docs:
    exigir_procedencia(doc, extra=tuple(p for p, _ in copias))
    rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
    assert rs.verify(doc)
    dst = os.path.join(EV, "runs", "2026", "08", nombre)
    assert not os.path.exists(dst); salidas.append((dst, doc))
for _, d_ in copias: assert not os.path.exists(d_), d_
for dst, doc in salidas:
    json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
    assert rs.verify(json.load(open(dst)))
for s_, d_ in copias: shutil.copy2(s_, d_); assert sha(s_) == sha(d_)
for dst, doc in salidas: print("SELLADO %-30s %s" % (doc["meta"]["file_id"], doc["meta"]["content_hash"]))
for _, d_ in copias: print("  publicado:", os.path.relpath(d_, EV))
