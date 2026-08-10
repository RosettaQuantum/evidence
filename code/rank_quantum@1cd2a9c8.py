#!/usr/bin/env python3
"""Ranker cuantico CIEGO: matriz de conectividad N x N + top-5 sitios por blanco.

Produce los entregables 1 y 2 del challenge Cleveland (la matriz y el hit list) a
partir de los caches ciegos (cache_blind/, construidos SIN abrir las holo).

EL METRICO, PRE-REGISTRADO
--------------------------
Conectividad cuantica C(i,j) = promedio temporal a tiempo infinito de la probabilidad
de transicion de la caminata cuantica continua (CTQW) con H = W:

    C(i,j) = lim_{T->inf} (1/T) int_0^T |<i| e^{-iHt} |j>|^2 dt
           = sum_{lambda} |<i| P_lambda |j>|^2

donde P_lambda proyecta sobre el autoespacio de cada autovalor distinto de H (la
"mixing matrix" estandar de CTQW). W es la adyacencia pesada gaussiana sobre la red
de contactos CA (mismo kernel y cutoff que el motor sellado y que el corredor).

Por que ESTE metrico y no otro — la justificacion que pide el entregable 3:

1.  SIN PARAMETROS LIBRES. No hay ventana de tiempo, ni grilla, ni r de Trotter que
    elegir. Ya nos paso: una grilla con tope en t=20 inflo un q/c de 5x a 19x. Un
    metrico sin perillas no se puede sobreajustar ni atacar por la eleccion de
    perillas.

2.  LA DIFUSION CLASICA, EN EL MISMO PROMEDIO, NO CONTIENE INFORMACION. El analogo
    clasico exacto (exp(-Lt) promediado a tiempo largo) converge al reparto uniforme
    1/n: una matriz de rango 1 que rankea a todos los residuos igual. La CTQW, por
    interferencia, retiene estructura a tiempo infinito. La comparacion clasica no es
    un rival debil elegido a proposito: es la MISMA operacion, y da exactamente nada.
    Cualquier senal del ranking es, por construccion, senal cuantica.

3.  ES FISICA DEL TRANSPORTE, no una feature ad-hoc: C(i,src) mide cuanta amplitud
    de la fuente termina, en promedio, en cada residuo — la nocion literal de
    "conectividad dinamica al sitio activo" que pide el statement.

SCORE Y SITIOS
--------------
score(i) = promedio sobre s in src de C(i, s), restringido a residuos distales
(mask, >6 A de la fuente — convencion sellada del motor). Los sitios se arman por
clustering espacial aglomerativo de los top 10% distales con enlace simple a 8 A
(la convencion de cluster_sites del motor), rankeados por su mejor residuo, top-5.

CIEGO: este script no abre, no lee y no conoce las estructuras holo. El scoring
contra los bolsillos validados es una etapa POSTERIOR y separada, que se corre
recien cuando las predicciones ya estan comprometidas (commiteadas y ancladas).
El orden en git lo prueba: el commit de este archivo precede al de las predicciones.

Uso:
    python3 rank_quantum.py            # los 4 blancos -> predictions_blind/
"""
import glob, hashlib, json, os
import numpy as np

import build_cache as BC

HERE = os.path.dirname(os.path.abspath(__file__))
BLIND = os.path.join(HERE, "cache_blind")
OUT = os.path.join(HERE, "predictions_blind")
SIGMA = 6.0          # kernel gaussiano del peso de arista — el del motor y el corredor
TOP_FRAC = 0.10      # top 10% distal entra al clustering (convencion cluster_sites)
LINK_A = 8.0         # enlace simple a 8 A (convencion cluster_sites)
N_SITES = 5          # el hit list que pide el challenge


def mixing_matrix(W):
    """C(i,j) = sum sobre autovalores distintos de |<i|P_l|j>|^2, via eigh."""
    vals, vecs = np.linalg.eigh(W)
    C = np.zeros_like(W)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and abs(vals[j + 1] - vals[i]) < 1e-9:
            j += 1
        P = vecs[:, i:j + 1] @ vecs[:, i:j + 1].T      # proyector del autoespacio
        C += P ** 2
        i = j + 1
    return C


def cluster_sites(score, mask, coords, ids, n_sites=N_SITES):
    """Top 10% distal -> clustering aglomerativo de enlace simple a 8 A -> sitios."""
    distal = np.where(mask)[0]
    orden = distal[np.argsort(-score[distal])]
    top = orden[:max(1, int(len(distal) * TOP_FRAC))]
    grupos = [[int(t)] for t in top]
    fusion = True
    while fusion and len(grupos) > 1:
        fusion = False
        for a in range(len(grupos)):
            for b in range(a + 1, len(grupos)):
                da = coords[grupos[a]]; db = coords[grupos[b]]
                dmin = np.linalg.norm(da[:, None, :] - db[None, :, :], axis=-1).min()
                if dmin < LINK_A:
                    grupos[a] += grupos[b]; del grupos[b]; fusion = True; break
            if fusion:
                break
    grupos.sort(key=lambda g: -max(score[i] for i in g))
    sitios = []
    for rank, g in enumerate(grupos[:n_sites], 1):
        g = sorted(g, key=lambda i: -score[i])
        sitios.append({
            "rank": rank,
            "residuos": [{"chain": ids[i][0], "resnum": int(ids[i][1]),
                          "score": round(float(score[i]), 6)} for i in g],
            "mejor_score": round(float(score[g[0]]), 6),
            "n_residuos": len(g),
        })
    return sitios, len(grupos)


def run(nombre):
    d = BC.load(nombre)
    A, coords = d["A"], d["coords"]
    D = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    W = np.exp(-(D ** 2) / (2 * SIGMA ** 2)) * (A > 0)
    np.fill_diagonal(W, 0.0)
    C = mixing_matrix(W)
    src = d["src"]
    score = C[:, src].mean(axis=1)
    sitios, n_grupos = cluster_sites(score, d["mask"], coords, d["ids"])

    os.makedirs(OUT, exist_ok=True)
    mpath = os.path.join(OUT, "%s.connectivity.npz" % d["name"])
    np.savez_compressed(mpath, C=C.astype(np.float32),
                        ids_chain=np.array([c for c, r in d["ids"]]),
                        ids_resnum=np.array([r for c, r in d["ids"]]))
    pred = {
        "target": d["name"], "pdb_id": d["pdb_id"], "chain": d["chain"],
        "pdb_sha256": d["pdb_sha256"], "n": d["n"], "n_distal": d["n_distal"],
        "metrico": "mixing matrix CTQW (promedio temporal infinito), H=W gaussiano "
                   "sigma=6 sobre contactos CA cutoff=8.5; score=media sobre src; "
                   "sitios=clustering enlace simple 8A del top 10% distal",
        "ciego": "las estructuras holo no se abrieron para nada de esto",
        "clasico_analogo": "exp(-Lt) promediado a tiempo largo = uniforme 1/n "
                           "(rango 1): el mismo promedio, sin informacion",
        # Hash del CONTENIDO, no del archivo: el .npz es un zip y su compresion cambia
        # con la version de numpy. Lo que un tercero puede recomputar son los datos.
        "matriz_conectividad": {"archivo": os.path.basename(mpath),
                                "contenido_sha256": BC.firma_npz(mpath),
                                "como_verificar": "np.load(archivo) y rehacer la firma "
                                                  "sobre los arreglos en orden de clave "
                                                  "(ver build_cache.firma)",
                                "forma": list(C.shape), "dtype": "float32"},
        "sitios_predichos_top%d" % N_SITES: sitios,
        "n_clusters_totales": n_grupos,
    }
    ppath = os.path.join(OUT, "%s.prediction.json" % d["name"])
    json.dump(pred, open(ppath, "w"), indent=1, ensure_ascii=False)
    top1 = sitios[0]["residuos"][0] if sitios else None
    print("%-14s n=%4d  sitios=%d  top-1: %s%s score=%.4f  (clusters %d)" % (
        d["name"], d["n"], len(sitios),
        top1["chain"], top1["resnum"], top1["score"], n_grupos))
    return pred


if __name__ == "__main__":
    nombres = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(BLIND, "*.npz")))
    if not nombres:
        raise SystemExit("no hay caches ciegos; corre build_cache.py primero")
    print("RANKER CUANTICO CIEGO — %d blancos" % len(nombres))
    for n in nombres:
        run(n)
    print("\nescrito predictions_blind/ — comprometer (commit+ancla) ANTES de abrir holo alguna.")
