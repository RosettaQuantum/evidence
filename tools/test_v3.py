#!/usr/bin/env python3
"""Pruebas de la propuesta v3 — la regresion importa mas que la novedad.

Lo que hay que probar de un bump de convencion no es que la nueva funcione: es que **la
vieja siga funcionando exactamente igual**. Los 43 archivos anclados son hechos publicos;
si esta propuesta le cambia el veredicto a uno solo, la propuesta esta mal y no entra.

    python3 test_v3.py
    python3 test_v3.py --self-test
"""
import copy
import glob
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.dirname(AQUI)
RAIZ = os.path.dirname(STAGING)
BASE = os.path.dirname(AQUI) if os.path.basename(AQUI) == "tools" else AQUI
sys.path.insert(0, os.path.join(BASE, "harness"))
sys.path.insert(0, os.path.join(BASE, "tools"))

import jcs                                     # noqa: E402
import rosettaq_seal as rs                     # noqa: E402
import verify_seals as vs                      # noqa: E402

SELF = "--self-test" in sys.argv
pasaron, fallaron = 0, 0


def ok(n):
    global pasaron
    pasaron += 1
    print("  ok    %s" % n)


def mal(n, d):
    global fallaron
    fallaron += 1
    print("  FALLO %s\n        %s" % (n, d))


def comprobar(n, cond, detalle=""):
    ok(n) if cond else mal(n, detalle)


# ------------------------------------------------------- regresion sobre lo anclado
# EL punto entero de la propuesta: nada de lo publicado cambia de veredicto.
print("REGRESION — los sellos ya publicados no cambian de veredicto")
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))
sys.path.insert(0, os.path.join(RAIZ, "evidence", "tools"))
import importlib.util                          # noqa: E402


def _cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


vs_viejo = _cargar("vs_viejo", os.path.join(RAIZ, "evidence", "tools", "verify_seals.py"))

# DEFECTO CORREGIDO (2026-08-10): esta lista era un glob de cuatro carpetas escritas a
# mano —runs, prereg, recipes, manifests— y por eso la primera corrida cubrio 67 de 69 y
# lo reporto como si fueran todos. Faltaban `verdicts/` (un v1-legada anclado) y
# `predictions/`. Es el mismo defecto que perseguimos en el motor: alcance declarado mayor
# que el real, en verde. Ahora se RECORRE el repo y un sello es lo que tiene
# `meta.content_hash`, no lo que este en una carpeta que alguien se acordo de listar.
def sellos_del_archivo(base):
    out = []
    for raiz, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in (".git", ".wrangler", "node_modules")]
        for f in files:
            if not f.endswith(".json"):
                continue
            p = os.path.join(raiz, f)
            try:
                d = json.load(open(p))
            except Exception:
                continue
            if isinstance(d, dict) and isinstance(d.get("meta"), dict) \
                    and "content_hash" in d["meta"]:
                out.append((p, d))
    return sorted(out)


archivos = sellos_del_archivo(os.path.join(RAIZ, "evidence"))
distintos = []
for p, d in archivos:
    antes = vs_viejo.identify(d)
    despues = vs.identify(d)
    if antes != despues:
        distintos.append((os.path.basename(p), antes[0], despues[0]))
vistos = len(archivos)
comprobar("los %d sellos del archivo dan el MISMO veredicto antes y despues" % vistos,
          not distintos and vistos > 0,
          "cambiaron %d: %s" % (len(distintos), distintos[:5]) if distintos
          else "no se leyo ningun archivo — el denominador es cero y eso no prueba nada")
comprobar("y el denominador se recorre, no se lista a mano (>= 69 sellos)",
          vistos >= 69,
          "solo %d: si el archivo crecio, esta prueba tiene que verlo sola" % vistos)

# ------------------------------------------------------------------ ida y vuelta v3
print("\nv3 — ida y vuelta")
doc = {"meta": {"file_id": "PRUEBA-001", "type": "RUN"},
       "w6": {"que": {"distal_A": 6.0, "n": 90, "p": 0.4038}}}
d3 = rs.seal(copy.deepcopy(doc), harness=("t.py", "1.0.0", "sha256:x"),
             schema=rs.SCHEMA_V3)
comprobar("un sello v3 se declara v3", d3["meta"]["schema"] == rs.SCHEMA_V3)
comprobar("un sello v3 verifica", rs.verify(d3))
comprobar("el verificador lo identifica como v3", vs.identify(d3)[0] == vs.V3)
comprobar("la convencion escrita en el sello nombra JCS y RFC 8785",
          "JCS" in d3["meta"]["sealed_by"]["convention"]
          and "8785" in d3["meta"]["sealed_by"]["convention"])

d2 = rs.seal(copy.deepcopy(doc), harness=("t.py", "1.0.0", "sha256:x"))
comprobar("el defecto de seal() sigue siendo v2 (el cambio de defecto es otra decision)",
          d2["meta"]["schema"] == rs.SCHEMA_V2)
comprobar("un sello v2 sigue verificando", rs.verify(d2))
comprobar("v2 y v3 del MISMO documento dan hashes distintos",
          d2["meta"]["content_hash"] != d3["meta"]["content_hash"],
          "dan igual: entonces la convencion no cambio nada y el bump sobra")

# ----------------------------------------------- la trampa que el bump podria abrir
print("\nLA TRAMPA — una etiqueta equivocada no puede pasar como exito")
falso = copy.deepcopy(d3)
falso["meta"]["schema"] = rs.SCHEMA_V2          # dice v2, esta sellado en v3
comprobar("un v3 etiquetado v2 NO verifica (verify usa lo que el documento declara)",
          not rs.verify(falso),
          "verifico igual: la etiqueta dejo de importar y eso es peor que el problema")
comprobar("pero el verificador SI lo reconoce y dice cual convencion reprodujo",
          vs.identify(falso)[0] == vs.V3)
comprobar("y lo reporta como etiqueta equivocada, no como valido a secas",
          vs.identify(falso)[0] != falso["meta"]["schema"].rsplit("/", 1)[-1])

# ------------------------------------------------- lo que JCS no puede escribir
print("\nFALLA CERRADO")
try:
    rs.seal({"meta": {"file_id": "X"}, "w6": {"x": float("inf")}}, schema=rs.SCHEMA_V3)
    mal("un valor no canonizable aborta el sellado v3", "NO lanzo")
except jcs.NoCanonizable:
    ok("un valor no canonizable aborta el sellado v3")
try:
    rs.seal({"meta": {"file_id": "X"}, "w6": {}}, schema="rosettaq-archive/v9")
    mal("una convencion desconocida aborta", "NO lanzo")
except ValueError:
    ok("una convencion desconocida aborta")

# ------------------------------------------------------------------ self-test
if SELF:
    print("\nSELF-TEST — cada guardia se obliga a gritar")
    antes = fallaron
    comprobar("[self] v2 y v3 dan el mismo hash",
              d2["meta"]["content_hash"] == d3["meta"]["content_hash"])
    comprobar("[self] un v3 mal etiquetado verifica igual", rs.verify(falso))
    def _infinito_pasa():
        # tiene que DEVOLVER False, no lanzar: un self-test que revienta no prueba que el
        # guardia grito, prueba que el self-test estaba mal escrito.
        try:
            jcs.numero(float("inf"))
            return True
        except jcs.NoCanonizable:
            return False
    comprobar("[self] el infinito se canoniza sin quejarse", _infinito_pasa())
    esperados = 3
    reales = fallaron - antes
    print("  self-test: %d de %d guardias gritaron" % (reales, esperados))
    if reales != esperados:
        print("  ERROR: un guardia no grito cuando debia")
        sys.exit(2)
    fallaron = antes
    pasaron += esperados

print("\n%d pasaron, %d fallaron" % (pasaron, fallaron))
sys.exit(1 if fallaron else 0)
