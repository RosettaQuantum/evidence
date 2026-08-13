#!/usr/bin/env python3
"""La telemetria: barre la pista entera y dice DONDE se puede ganar.

POR QUE EXISTE
--------------
La primera corrida de RQ-0019 (2026-08-13, instancia mina_9frentes_3camiones_cap50)
enseno dos cosas y ninguna era el veredicto:

  1. OR-Tools quedo a 0,001 % del optimo exacto. En esa instancia NO HAY BRECHA que
     ganar — cronometrar ahi no puede producir una mejora vendible por mas vueltas
     que se den.
  2. El brazo cuantico no cabia: 9 frentes x 3 camiones son 27 qubits contra 22 de
     simulador.

Juntas dicen la tension que ordena todo el trabajo: **el regimen donde el clasico
flaquea es donde el cuantico todavia no entra.** Correr una instancia mas no lo
resuelve; hay que MAPEAR la frontera. Eso es esto.

QUE MIDE, EXACTAMENTE
---------------------
Para cada punto de la grilla:
  brecha_clasico  = cuanto le falta a OR-Tools respecto del optimo exacto.
                    Si es ~0, ese punto no sirve como pista: no hay nada que ganar.
  cabe_cuantico   = si el reparto entra en el simulador (frentes x camiones <= tope).
  tiempo_exacto   = cuanto tarda el arbitro. Cuando crece sin control, el optimo deja
                    de conocerse y la brecha pasa a ser una cota, no una medida.

La interseccion de «hay brecha» con «cabe» es el unico lugar donde una mejora cuantica
podria existir y ademas medirse. Si esa interseccion resulta VACIA, ese es el hallazgo
—y es exactamente el «discrimination forecast» que prometimos en julio y no entregamos—:
la estimacion del regimen donde valdria la pena mirar.

ACUMULA, NO PISA
----------------
Cada corrida agrega filas a `barrido_vrp.csv`. La grilla siguiente se elige mirando la
anterior: es una maquina que aprende de sus vueltas, no una que repite la misma.

Uso:
    python3 barrido_vrp.py                       # grilla por defecto
    RQ_FRENTES=6,8,10,12 RQ_CAMIONES=2,3 python3 barrido_vrp.py
"""
import csv
import json
import os
import time

import numpy as np

import vrp_harness as V

TOPE_QUBITS = int(os.environ.get("RQ_TOPE_QUBITS", 22))
SALIDA_CSV = os.environ.get("RQ_CSV", "barrido_vrp.csv")
SALIDA_JSON = os.environ.get("RQ_JSON", "barrido_vrp.json")
PRESUPUESTO = float(os.environ.get("RQ_BUDGET", 10))
SEEDS = [int(s) for s in os.environ.get("RQ_SEEDS", "42,43,44").split(",")]
FRENTES = [int(s) for s in os.environ.get("RQ_FRENTES", "6,8,10,12,15,20").split(",")]
CAMIONES = [int(s) for s in os.environ.get("RQ_CAMIONES", "2,3,4").split(",")]

CAMPOS = ["fecha", "frentes", "camiones", "capacidad_t", "seed", "uso_flota_pct",
          "exacto", "exacto_estado", "exacto_s", "clasico", "clasico_s",
          "brecha_clasico_pct", "qubits", "cabe_cuantico", "hay_brecha"]


def un_punto(frentes, camiones, seed, presupuesto):
    """Una instancia: el arbitro y el rival. El cuantico se mide aparte y solo si cabe."""
    V.NODOS = frentes + 1
    V.CAMIONES = camiones
    V.SEED = seed
    V.rng = np.random.default_rng(seed)

    # capacidad con holgura del 25%: una faena no opera al 100% de su flota, y una
    # instancia infactible se leeria como «los tres fallaron» en vez de «no habia problema»
    coords, demanda, D = V.construir_instancia()
    V.CAPACIDAD = float(np.ceil(demanda.sum() / camiones * 1.25))
    total = float(demanda.sum())
    flota = camiones * V.CAPACIDAD

    ex = V.brazo_exacto(D, demanda, presupuesto)
    cl = V.brazo_ortools(D, demanda, presupuesto)
    qubits = frentes * camiones

    brecha = None
    if ex.get("value") and cl.get("value"):
        brecha = round(100 * (cl["value"] - ex["value"]) / ex["value"], 4)

    return {
        "fecha": time.strftime("%Y-%m-%d"),
        "frentes": frentes, "camiones": camiones, "capacidad_t": V.CAPACIDAD, "seed": seed,
        "uso_flota_pct": round(100 * total / flota, 1),
        "exacto": ex.get("value"), "exacto_estado": ex.get("estado"), "exacto_s": ex.get("runtime_s"),
        "clasico": cl.get("value"), "clasico_s": cl.get("runtime_s"),
        "brecha_clasico_pct": brecha,
        "qubits": qubits, "cabe_cuantico": qubits <= TOPE_QUBITS,
        # «hay brecha» con criterio explicito: 0,5 % es el minimo que un cliente notaria
        # en una faena. Por debajo de eso, ganar no se distingue de ruido de heuristica.
        "hay_brecha": (brecha is not None and brecha >= 0.5),
    }


if __name__ == "__main__":
    filas = []
    if os.path.exists(SALIDA_CSV):                 # acumula, no pisa
        with open(SALIDA_CSV) as f:
            filas = list(csv.DictReader(f))
        print("barrido previo: %d filas — se agregan a estas" % len(filas))

    nuevas = []
    for fr in FRENTES:
        for ca in CAMIONES:
            for se in SEEDS:
                if fr < ca * 2:                    # instancias degeneradas: sin sentido
                    continue
                r = un_punto(fr, ca, se, PRESUPUESTO)
                nuevas.append(r)
                print("  %2d frentes × %d camiones seed %d → brecha %-8s qubits %-3d %s%s"
                      % (fr, ca, se, r["brecha_clasico_pct"], r["qubits"],
                         "CABE" if r["cabe_cuantico"] else "no cabe",
                         "  ← PISTA" if (r["hay_brecha"] and r["cabe_cuantico"]) else ""),
                      flush=True)

    with open(SALIDA_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        for r in filas + nuevas:
            w.writerow({k: r.get(k) for k in CAMPOS})

    # ------------------------------------------------------------ la lectura
    con_brecha = [r for r in nuevas if r["hay_brecha"]]
    caben = [r for r in nuevas if r["cabe_cuantico"]]
    pista = [r for r in nuevas if r["hay_brecha"] and r["cabe_cuantico"]]

    lectura = {
        "puntos_medidos": len(nuevas),
        "con_brecha_clasica": len(con_brecha),
        "donde_cabe_el_cuantico": len(caben),
        "PISTA_donde_ambas_cosas": len(pista),
        "criterio_de_brecha": "el clasico deja >= 0,5 % respecto del optimo exacto",
        "tope_de_qubits": TOPE_QUBITS,
    }
    if pista:
        lectura["donde_apuntar"] = sorted(
            [{"frentes": r["frentes"], "camiones": r["camiones"], "seed": r["seed"],
              "brecha_pct": r["brecha_clasico_pct"], "qubits": r["qubits"]} for r in pista],
            key=lambda x: -x["brecha_pct"])[:8]
    else:
        lectura["hallazgo"] = (
            "NO hay ningun punto donde el clasico deje brecha Y el cuantico quepa. "
            "Ese vacio es el resultado, no un fallo del barrido: dice que con este "
            "encoding y este tope de qubits no existe pista donde competir. Cambiar "
            "una de las dos cosas —encoding mas compacto o mas qubits— es la unica via.")
    if con_brecha:
        lectura["brecha_maxima_vista"] = max(r["brecha_clasico_pct"] for r in con_brecha)
        lectura["qubits_en_esa_brecha"] = [
            r["qubits"] for r in con_brecha
            if r["brecha_clasico_pct"] == lectura["brecha_maxima_vista"]][0]

    json.dump({"lectura": lectura, "puntos": nuevas}, open(SALIDA_JSON, "w"), indent=1)
    print("\n" + json.dumps(lectura, indent=1, ensure_ascii=False))
