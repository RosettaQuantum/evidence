#!/usr/bin/env python3
"""DIAGNOSTICO DE PROXIMIDAD — por que el metrico ciego dio negativo, medido.

POR QUE EXISTE ESTE ARCHIVO
---------------------------
La cifra "el score correlaciona -0,55 a -0,85 con la distancia a la fuente" circula
en encargos y en texto de la web. No estaba instrumentada en ninguna parte: ningun
script del repositorio la calcula. Repetirla dentro de un sello seria heredar un
numero (CLAUDE.md Rosetta §7). Este script la MIDE, sobre las mismas matrices que
quedaron comprometidas en git antes de abrir ninguna holo.

Lo que prueba `tests/test_engine.py` es el mecanismo en un caso donde la respuesta se
conoce de antemano (grafo camino: localizacion espectral en nodos de grado 1). Lo que
mide este script es la magnitud en las cuatro proteinas reales. Son cosas distintas y
las dos hacen falta.

QUE SE MIDE, EXACTAMENTE
------------------------
  score(i)  = media sobre s en src de C(i, s), con C la matriz de conectividad
              CTQW **leida del .npz comprometido** (commit 4cfac34), no recalculada.
  d_src(i)  = distancia euclidea minima del CA de i a los CA de la fuente.
  rho       = Spearman(score, d_src). Se reporta sobre los residuos DISTALES —que son
              el universo sobre el que el metrico compite— y sobre todos, para que no
              se pueda elegir el subconjunto que mas conviene.

NO SE ABRE NINGUNA HOLO AQUI. Este diagnostico usa exactamente los mismos insumos que
la prediccion ciega; es una lectura del predictor, no del acierto.

PROMESA QUE SE EJERCE (CLAUDE.md Rosetta §1 bis): antes de medir, se recomputa la
firma de contenido de cada .npz y se compara con la que declara el prediction.json.
Si no calza, ese blanco NO se mide y queda contado en el denominador como saltado.

REGISTRO ANTES DEL PASO (§5 ter): la bitacora se abre al empezar y se anota una linea
por blanco ANTES de medirlo. Un blanco que mate el proceso deja su intento escrito.

Uso:  python3 diagnose_proximity.py
Sale: diagnose_proximity_result.json  +  diagnose_proximity_log.jsonl
"""
import json
import os
import sys

import numpy as np
from scipy.stats import spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
QRUN = os.path.join(os.path.dirname(AQUI), "quantum-run")
sys.path.insert(0, QRUN)

import build_cache as BC  # noqa: E402

BLIND = os.path.join(QRUN, "cache_blind")
PRED = os.path.join(QRUN, "predictions_blind")
LOG = os.path.join(AQUI, "diagnose_proximity_log.jsonl")
OUT = os.path.join(AQUI, "diagnose_proximity_result.json")


def anota(evento, **kv):
    with open(LOG, "a") as f:
        f.write(json.dumps({"evento": evento, **kv}, ensure_ascii=False) + "\n")


def medir(nombre):
    d = BC.load(nombre, carpeta=BLIND)
    pred = json.load(open(os.path.join(PRED, nombre + ".prediction.json")))

    # la promesa, ejercida: recomputar la firma declarada antes de usar la matriz
    npz_path = os.path.join(PRED, pred["matriz_conectividad"]["archivo"])
    firma_real = BC.firma_npz(npz_path)
    firma_declarada = pred["matriz_conectividad"]["contenido_sha256"]
    if firma_real != firma_declarada:
        return None, {"razon": "firma de contenido no calza",
                      "declarada": firma_declarada, "recomputada": firma_real}

    C = np.load(npz_path)["C"]
    src = d["src"]
    score = C[:, src].mean(axis=1)

    coords = d["coords"]
    d_src = np.linalg.norm(coords[:, None, :] - coords[src][None, :, :], axis=-1).min(axis=1)

    distal = np.where(d["mask"])[0]
    rho_todos = spearmanr(score, d_src).correlation
    rho_distal = spearmanr(score[distal], d_src[distal]).correlation

    return {
        "blanco": nombre,
        "pdb": d["pdb_id"],
        "n_residuos": int(d["n"]),
        "n_fuente": len(src),
        "n_distal": int(len(distal)),
        "matriz_verificada": firma_real,
        "spearman_score_vs_dist_fuente_todos": round(float(rho_todos), 4),
        "spearman_score_vs_dist_fuente_distales": round(float(rho_distal), 4),
        "dist_fuente_A": {"min": round(float(d_src.min()), 2),
                          "max": round(float(d_src.max()), 2),
                          "mediana": round(float(np.median(d_src)), 2)},
    }, None


if __name__ == "__main__":
    nombres = sorted(os.path.basename(p)[:-4]
                     for p in __import__("glob").glob(os.path.join(BLIND, "*.npz")))
    open(LOG, "w").close()
    anota("inicio", n_blancos_vistos=len(nombres), blancos=nombres)

    medidos, saltados = [], []
    for n in nombres:
        anota("intento", blanco=n)                     # ANTES del paso, no despues
        r, err = medir(n)
        if r is None:
            saltados.append({"blanco": n, **err})
            anota("saltado", blanco=n, **err)
            continue
        medidos.append(r)
        anota("medido", blanco=n,
              rho_distal=r["spearman_score_vs_dist_fuente_distales"])

    rhos = [m["spearman_score_vs_dist_fuente_distales"] for m in medidos]
    res = {
        "_doc": "Diagnostico de proximidad del metrico ciego CTQW. Mide la correlacion "
                "de rango entre el score y la distancia a la fuente. No abre ninguna holo.",
        "denominador": {"blancos_vistos": len(nombres),
                        "medidos": len(medidos),
                        "saltados": len(saltados)},
        "saltados": saltados,
        "rango_spearman_distales": [round(min(rhos), 4), round(max(rhos), 4)] if rhos else None,
        "blancos": medidos,
    }
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    anota("fin", medidos=len(medidos), saltados=len(saltados))

    print("DIAGNOSTICO DE PROXIMIDAD — %d de %d blancos medidos, %d saltados"
          % (len(medidos), len(nombres), len(saltados)))
    for m in medidos:
        print("  %-14s n=%4d distal=%4d  rho(distales)=%+.4f  rho(todos)=%+.4f"
              % (m["blanco"], m["n_residuos"], m["n_distal"],
                 m["spearman_score_vs_dist_fuente_distales"],
                 m["spearman_score_vs_dist_fuente_todos"]))
    if rhos:
        print("\nrango en distales: %+.4f a %+.4f" % (min(rhos), max(rhos)))
    print("escrito %s" % os.path.basename(OUT))
