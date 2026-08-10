#!/usr/bin/env python3
"""GRANO GRUESO — cuanto del orden de residuos sobrevive a la compresion de la red.

QUE PREGUNTA CONTESTA
---------------------
El challenge pide escalabilidad por coarse-graining como objetivo secundario. Lo que
ya estaba medido (`evidence/code/cleveland/required_deliverables.py`) es el percentil
del bolsillo y la aceleracion a cada nivel de compresion. Falta lo que de verdad
decide si la compresion sirve: **si el ORDEN de los residuos sobrevive**. Un metodo
que va 50 veces mas rapido y reordena la lista no acelera nada — resuelve otro
problema.

Este script no abre ninguna holo y no necesita verdad de terreno: compara el ranking
grueso contra el ranking fino, asi que los CUATRO blancos entran, incluido c-Myc.

CONVENCIONES — ninguna inventada aqui
-------------------------------------
  coarse_grain     agrupacion de residuos consecutivos en super-nodos de tamano b,
                   adyacencia binarizada, coordenadas = centroide. Es la receta de
                   `required_deliverables.coarse_grain`, replicada tal cual.
  kernel y metrico exp(-d^2/2*6^2) sobre la adyacencia, mixing matrix CTQW: los de
                   `rank_quantum.py`, el metrico ciego pre-registrado en 407fa7b.
  score fino       NO se recalcula: se lee del .npz COMPROMETIDO en 4cfac34, con su
                   firma de contenido recomputada antes de usarlo.
  distales         la mascara fina del cache ciego (>6 A de la fuente).
  top 10%          TOP_FRAC de `rank_quantum.cluster_sites`.

LIMITACION DECLARADA ANTES DE CORRER
------------------------------------
Dentro de un super-nodo todos los residuos reciben el MISMO score por construccion.
Eso pone un techo a Spearman que no depende del metodo sino del tamano de bloque. Es
inherente a la pregunta —queremos saber cuanto orden se pierde, y esa perdida es
parte de lo que se pierde— y queda dicho aqui para que nadie lo presente despues como
un descubrimiento ni como una excusa.

Uso:  python3 coarse_grain_test.py
"""
import glob
import hashlib
import json
import os
import sys
import time

import numpy as np
from scipy.stats import spearmanr

AQUI = os.path.dirname(os.path.abspath(__file__))
QRUN = os.path.join(os.path.dirname(AQUI), "quantum-run")
sys.path.insert(0, QRUN)

import build_cache as BC  # noqa: E402

BLIND = os.path.join(QRUN, "cache_blind")
PRED = os.path.join(QRUN, "predictions_blind")
LOG = os.path.join(AQUI, "coarse_grain_log.jsonl")
OUT = os.path.join(AQUI, "coarse_grain_result.json")
PREREG = os.path.join(AQUI, "RosettaQ__PREREG__PR-COARSE-001__20260810T1200Z__"
                            "grano-grueso-supervivencia-del-orden.json")

SIGMA = 6.0
TOP_FRAC = 0.10
BLOQUES = (2, 4, 8, 16)


def anota(evento, **kv):
    with open(LOG, "a") as f:
        f.write(json.dumps({"evento": evento, **kv}, ensure_ascii=False) + "\n")


def mi_sha():
    return "sha256:" + hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()


def mixing_matrix(W):
    """C(i,j) = suma sobre autovalores distintos de |<i|P_l|j>|^2. Copia de rank_quantum."""
    vals, vecs = np.linalg.eigh(W)
    C = np.zeros_like(W)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and abs(vals[j + 1] - vals[i]) < 1e-9:
            j += 1
        P = vecs[:, i:j + 1] @ vecs[:, i:j + 1].T
        C += P ** 2
        i = j + 1
    return C


def coarse_grain(A, coords, src_idx, block):
    """Receta de required_deliverables.coarse_grain, replicada sin cambios."""
    n = A.shape[0]
    grp = np.arange(n) // block
    m = int(grp.max()) + 1
    T = np.zeros((n, m))
    T[np.arange(n), grp] = 1.0
    Ac = T.T @ A @ T
    np.fill_diagonal(Ac, 0.0)
    Ac = (Ac > 0).astype(float)
    cc = (T.T @ coords) / T.sum(0)[:, None]
    src_c = sorted(set(int(grp[s]) for s in src_idx))
    return Ac, cc, src_c, grp, m


def score_de(A_bin, coords, src):
    """El metrico ciego, aplicado a la red que se le pase. Devuelve (score, segundos)."""
    D = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    W = np.exp(-(D ** 2) / (2 * SIGMA ** 2)) * (A_bin > 0)
    np.fill_diagonal(W, 0.0)
    t0 = time.time()
    C = mixing_matrix(W)
    dt = time.time() - t0
    return C[:, src].mean(axis=1), dt


def top_set(score, indices):
    """Top 10% de `indices` por score — la convencion de cluster_sites."""
    orden = indices[np.argsort(-score[indices])]
    return set(int(i) for i in orden[:max(1, int(len(indices) * TOP_FRAC))])


def medir(nombre):
    d = BC.load(nombre, carpeta=BLIND)
    pred = json.load(open(os.path.join(PRED, nombre + ".prediction.json")))

    npz_path = os.path.join(PRED, pred["matriz_conectividad"]["archivo"])
    firma_real = BC.firma_npz(npz_path)
    if firma_real != pred["matriz_conectividad"]["contenido_sha256"]:
        return None, {"razon": "firma de contenido de la matriz comprometida no calza",
                      "declarada": pred["matriz_conectividad"]["contenido_sha256"],
                      "recomputada": firma_real}

    C_fino = np.load(npz_path)["C"]
    src = d["src"]
    score_fino = C_fino[:, src].mean(axis=1)

    A, coords = d["A"], d["coords"]
    distal = np.where(d["mask"])[0]
    top_fino = top_set(score_fino, distal)

    # el tiempo fino se MIDE aqui con el mismo reloj que el grueso; el .npz no lo trae
    _, t_fino = score_de(A, coords, src)

    # residuos del sitio rank-1 de la prediccion comprometida
    resnum2idx = {rn: i for i, (c, rn) in enumerate(d["ids"])}
    sitios = pred["sitios_predichos_top5"]
    rank1 = [resnum2idx[r["resnum"]] for r in sitios[0]["residuos"]
             if r["resnum"] in resnum2idx] if sitios else []

    filas = []
    for b in BLOQUES:
        Ac, cc, src_c, grp, m = coarse_grain(A, coords, src, b)
        if not src_c:
            filas.append({"bloque": b, "saltado": "la fuente no sobrevive a la compresion"})
            continue
        score_c, t_c = score_de(Ac, cc, src_c)
        score_grueso = score_c[grp]                       # devuelto a nivel de residuo

        rho = spearmanr(score_grueso[distal], score_fino[distal]).correlation
        top_grueso = top_set(score_grueso, distal)
        inter = len(top_fino & top_grueso)
        union = len(top_fino | top_grueso)
        rank1_sobrevive = (len([i for i in rank1 if i in top_grueso]) / len(rank1)) if rank1 else None

        filas.append({
            "bloque": b,
            "n_supernodos": m,
            "compresion": round(d["n"] / m, 2),
            "spearman_orden_vs_fino_distales": round(float(rho), 4),
            "veredicto_orden": ("sobrevive" if rho >= 0.90 else
                                "parcial" if rho >= 0.70 else "no sobrevive"),
            "jaccard_top10pct_distal": round(inter / union, 4) if union else None,
            "frac_residuos_del_sitio_rank1_en_top10pct_grueso":
                round(rank1_sobrevive, 4) if rank1_sobrevive is not None else None,
            "t_fino_s": round(t_fino, 4),
            "t_grueso_s": round(t_c, 4),
            "aceleracion_medida": round(t_fino / max(t_c, 1e-9), 1),
        })

    return {"blanco": nombre, "pdb": d["pdb_id"], "n_residuos": int(d["n"]),
            "n_distal": int(len(distal)), "n_fuente": len(src),
            "matriz_verificada": firma_real,
            "n_residuos_sitio_rank1": len(rank1),
            "niveles": filas}, None


if __name__ == "__main__":
    # el pre-registro manda: si el script cambio despues de sellarse, no corre
    if not os.path.exists(PREREG):
        raise SystemExit("no existe el pre-registro sellado — no se corre nada")
    pr = json.load(open(PREREG))
    congelado = pr["prereg"]["guardrails_script_sha256"]
    if congelado != mi_sha():
        raise SystemExit("este script NO es el congelado en el pre-registro.\n"
                         "  pre-registrado: %s\n  actual:         %s" % (congelado, mi_sha()))

    nombres = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(BLIND, "*.npz")))
    open(LOG, "w").close()
    anota("inicio", prereg=pr["meta"]["content_hash"], script=mi_sha(),
          n_blancos_vistos=len(nombres), bloques=list(BLOQUES))

    medidos, saltados = [], []
    for n in nombres:
        anota("intento", blanco=n)                      # ANTES del paso
        r, err = medir(n)
        if r is None:
            saltados.append({"blanco": n, **err})
            anota("saltado", blanco=n, **err)
            continue
        medidos.append(r)
        anota("medido", blanco=n,
              rhos={f["bloque"]: f.get("spearman_orden_vs_fino_distales") for f in r["niveles"]})

    celdas = sum(len(m["niveles"]) for m in medidos)
    celdas_ok = sum(1 for m in medidos for f in m["niveles"] if "saltado" not in f)
    res = {
        "_doc": "Grano grueso: cuanto del orden de residuos sobrevive a la compresion de "
                "la red. Compara el ranking grueso contra el ranking fino COMPROMETIDO "
                "(4cfac34). No abre ninguna holo.",
        "prereg": {"file_id": pr["meta"]["file_id"],
                   "content_hash": pr["meta"]["content_hash"],
                   "sealed_at": pr["meta"]["sealed_at"]},
        "script_sha256": mi_sha(),
        "denominador": {"blancos_vistos": len(nombres), "blancos_medidos": len(medidos),
                        "blancos_saltados": len(saltados),
                        "celdas_blanco_x_bloque": celdas, "celdas_calculadas": celdas_ok,
                        "celdas_saltadas": celdas - celdas_ok},
        "saltados": saltados,
        "umbrales_pre_registrados": {"sobrevive": ">= 0.90", "parcial": "0.70 a 0.90",
                                     "no_sobrevive": "< 0.70"},
        "blancos": medidos,
    }
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    anota("fin", medidos=len(medidos), celdas_calculadas=celdas_ok)

    print("GRANO GRUESO — %d de %d blancos, %d de %d celdas"
          % (len(medidos), len(nombres), celdas_ok, celdas))
    for m in medidos:
        print("\n%s (n=%d, distal=%d)" % (m["blanco"], m["n_residuos"], m["n_distal"]))
        print("  %5s %6s %7s %9s %9s %8s %s" % ("bloq", "super", "compr", "spearman",
                                                "jaccard", "acel", "veredicto"))
        for f in m["niveles"]:
            if "saltado" in f:
                print("  %5d  SALTADO: %s" % (f["bloque"], f["saltado"]))
                continue
            print("  %5d %6d %7.2f %9.4f %9.4f %7.1fx %s"
                  % (f["bloque"], f["n_supernodos"], f["compresion"],
                     f["spearman_orden_vs_fino_distales"], f["jaccard_top10pct_distal"],
                     f["aceleracion_medida"], f["veredicto_orden"]))
    print("\nescrito %s" % os.path.basename(OUT))
