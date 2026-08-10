#!/usr/bin/env python3
"""Genera las cifras de SPEC-SELLADO.md desde el archivo, en vez de escribirlas a mano.

POR QUE EXISTE
--------------
`SPEC-SELLADO.md` cita numeros sobre el propio archivo: cuantos sellos hay de cada
convencion, cuantos literales cambian bajo v3, cuantos numeros tiene el payload. Escritos
a mano quedan viejos el dia que se sella algo nuevo — y quedan viejos EN SILENCIO, que es
peor, porque el documento sigue viendose bien. La tabla dice "v3: 0 archivos" y deja de
ser cierta con el primer sello v3.

Este script los MIDE y emite el fragmento en markdown listo para pegar. Es el mismo
patron que ya usa el frente web con su catalogo: documento derivado del archivo, no
escrito a mano.

LA LISTA DE QUE MIRAR ES PARTE DEL PROGRAMA, Y SE EQUIVOCA IGUAL
----------------------------------------------------------------
Este script NO tiene su propia lista de carpetas. Recorre el repositorio y un sello es
lo que tiene `meta.content_hash`. La razon es un defecto real y repetido del 2026-08-10:
tres programas distintos —una regresion, un conteo y el propio `verify_seals.py`— tenian
cada uno su lista escrita a mano y los tres cubrian menos de lo que declaraban (67 de 69,
y 63 de 69 el verificador de referencia). El que recorre no se olvida de una carpeta
nueva; el que lista, si.

Uso:  python3 scripts/build_spec_stats.py            # imprime el fragmento
      python3 scripts/build_spec_stats.py --json     # los numeros crudos
"""
import collections
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "tools"))
sys.path.insert(0, os.path.join(RAIZ, "harness"))

import jcs                     # noqa: E402
import verify_seals as vs      # noqa: E402

NOMBRE = {"v3": "`v3`", "v2": "`v2`", "v1-canonica": "`v1-canónica`",
          "v1-legada": "`v1-legada`"}
ORDEN = ["v1-legada", "v2", "v1-canonica", "v3"]


def sellos(base):
    """Todo JSON con meta.content_hash, recorriendo. Sin lista de carpetas."""
    out = []
    for raiz, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in (".git", ".wrangler", "node_modules")]
        for f in sorted(files):
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
    return out


def payload(d):
    meta = {k: v for k, v in d["meta"].items() if k not in ("content_hash", "schema")}
    cuerpo = {k: v for k, v in d.items() if k not in ("meta", "storage")}
    return {"meta": meta, **cuerpo}


def cuenta_numeros(o, cambian):
    """Numeros del objeto, y cuantos se escriben distinto en Python y en JCS."""
    if isinstance(o, dict):
        return sum(cuenta_numeros(v, cambian) for v in o.values())
    if isinstance(o, list):
        return sum(cuenta_numeros(x, cambian) for x in o)
    if isinstance(o, bool):
        return 0
    if isinstance(o, (int, float)):
        try:
            if json.dumps(o) != jcs.numero(o):
                cambian.append(o)
        except jcs.NoCanonizable:
            cambian.append(o)
        return 1
    return 0


def medir():
    todos = sellos(RAIZ)
    conv = collections.Counter()
    n_payload = 0
    cambian = []
    n_archivo = 0
    n_storage = 0
    con_storage = 0
    for _, d in todos:
        conv[vs.identify(d)[0] or "INVALID"] += 1
        n_payload += cuenta_numeros(payload(d), cambian)
        n_archivo += cuenta_numeros(d, [])
        if "storage" in d:
            con_storage += 1
            n_storage += cuenta_numeros(d["storage"], [])
    return {
        "sellos": len(todos),
        "por_convencion": dict(conv),
        "numeros_payload": n_payload,
        "numeros_archivo": n_archivo,
        "numeros_en_storage": n_storage,
        "archivos_con_storage": con_storage,
        "literales_que_cambian": len(cambian),
        "porcentaje": round(100.0 * len(cambian) / n_payload, 1) if n_payload else 0.0,
    }


def mil(x):
    """Separador de miles con punto, como el resto del documento."""
    return "{:,}".format(x).replace(",", ".")


def fragmento(m):
    n = m["sellos"]
    L = ["Cuántos archivos usa cada una, contados sobre el repositorio y no de memoria",
         "(**%d sellos**):" % n, "",
         "| Convención | Archivos | Del total |", "|---|---|---|"]
    for c in ORDEN:
        k = m["por_convencion"].get(c, 0)
        L.append("| %s | %d | %s |" % (NOMBRE[c], k,
                                       ("%.0f %%" % (100.0 * k / n)) if k else "—"))
    inval = m["por_convencion"].get("INVALID", 0)
    if inval:
        L.append("| **INVALID** | %d | — |" % inval)
    L += ["", "Y sobre los números: **%s literales de %s — el %s %% — cambian de forma** "
              "entre un lenguaje y otro." % (mil(m["literales_que_cambian"]),
                                             mil(m["numeros_payload"]),
                                             ("%.1f" % m["porcentaje"]).replace(".", ",")),
          "", "El denominador son los números **del payload**, no los del archivo entero. "
              "El archivo tiene %s, pero %s viven en el bloque `storage` (en %d de los %d "
              "archivos), que el sello excluye."
              % (mil(m["numeros_archivo"]), mil(m["numeros_en_storage"]),
                 m["archivos_con_storage"], n)]
    return "\n".join(L)


if __name__ == "__main__":
    m = medir()
    if "--json" in sys.argv:
        print(json.dumps(m, indent=1, ensure_ascii=False))
    else:
        print(fragmento(m))
    if m["por_convencion"].get("INVALID"):
        sys.exit(1)          # falla cerrado: un INVALID no se reporta en un pie de pagina
