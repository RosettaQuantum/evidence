#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La reproducibilidad de SCIP EN EL PUNTO DONDE SE HIZO LA AFIRMACION ORIGINAL: K=10, S=250.

POR QUE ESTE PUNTO Y NO OTRO
----------------------------
El barrido de `mapa_dureza_eon.py` fija S=100 porque ese es el S mas grande donde SCIP SI
prueba optimalidad en K=10, y asi la transicion que se mida al crecer K es atribuible a K.
Pero la afirmacion que hay que corregir se hizo en K=10, S=250, y ahi el dato de hoy fue:
una corrida OPTIMA (brecha 1,93 %) y dos a 11,11 %. Eso NO se ve con una sola corrida, y es
lo unico que se puede decir con tres.

Este archivo mide ese punto exacto con TRES semillas y compara cada resultado contra el
OPTIMO REAL, que en este punto se conoce porque ya se enumero entero
(`arbitro_enumeracion_K10_S250.json`, 252 de 252 planes, 1103,94 s). El optimo se LEE de ese
archivo, no se escribe de memoria.

Y de paso deja escrita una cifra que la afirmacion original no tenia: **la enumeracion de ese
punto tomo 1103,94 s, o sea que ni siquiera ella cabe en el presupuesto operativo de 900 s.**
No se toca `mapa_dureza_eon.py`: se importa y se le pide el mismo punto, con su misma
maquinaria y su mismo guardia de memoria.
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("RQ_MAPA_S", "250")
os.environ.setdefault("RQ_MAPA_TOP", "900")
sys.path.insert(0, AQUI)

import mapa_dureza_eon as M          # noqa: E402

ARB = os.path.join(AQUI, "arbitro_enumeracion_K10_S250.json")


def main():
    if not os.path.exists(ARB):
        raise SystemExit("ABORTA: falta %s; sin el optimo REAL este punto no tiene arbitro "
                         "y la brecha seria contra una cota." % ARB)
    a = json.load(open(ARB))["arbitro_K10_S250"]
    if a["combinaciones"] != a["esperadas"]:
        raise SystemExit("ABORTA: el arbitro guardado recorrio %d de %d planes."
                         % (a["combinaciones"], a["esperadas"]))
    d = M.medir_punto(10)
    d["arbitro_previo_enumerado"] = {
        "optimo": a["valor"], "plan": a["plan"], "segundos": a["segundos"],
        "planes": a["combinaciones"], "esperados": a["esperadas"],
        "cabe_en_T_OP": bool(a["segundos"] <= M.T_OP),
        "fuente": os.path.basename(ARB)}
    opt = a["valor"]
    for c in d["solucionador"]["corridas"]:
        if c.get("valor") is not None:
            c["brecha_vs_optimo_real_pct"] = round(100.0 * (c["valor"] - opt) / abs(opt), 4)
            c["plan_es_el_optimo"] = bool(
                sorted(i for i, b in enumerate(c["x"]) if b) == sorted(a["plan"]))
    brs = [c["brecha_vs_optimo_real_pct"] for c in d["solucionador"]["corridas"]
           if c.get("brecha_vs_optimo_real_pct") is not None]
    d["reproducibilidad"] = {
        "optimo_real": opt, "plan_optimo": a["plan"],
        "brecha_vs_optimo_real_min_pct": min(brs) if brs else None,
        "brecha_vs_optimo_real_max_pct": max(brs) if brs else None,
        "semillas_que_llegaron_al_optimo": sum(
            1 for c in d["solucionador"]["corridas"] if c.get("plan_es_el_optimo")),
        "denominador": len(d["solucionador"]["corridas"])}
    salida = os.path.join(M.SALIDA, "reprod_K10_S250.json")
    with open(salida, "w") as f:
        json.dump(d, f, indent=1, default=float)
    print("\nREPRODUCIBILIDAD K=10 S=250 — optimo real %.4f (enumerado, %d/%d planes, %.0fs)"
          % (opt, a["combinaciones"], a["esperadas"], a["segundos"]))
    for c in d["solucionador"]["corridas"]:
        print("  semilla %-5s %-9s %7ss  valor=%-16s brecha vs cota=%-8s  "
              "brecha vs OPTIMO REAL=%-8s  llego al optimo=%s"
              % (c.get("semilla"), c.get("status"), c.get("segundos"), c.get("valor"),
                 c.get("brecha_vs_cota_pct"), c.get("brecha_vs_optimo_real_pct"),
                 c.get("plan_es_el_optimo")))
    print("escrito %s" % salida)


if __name__ == "__main__":
    main()
