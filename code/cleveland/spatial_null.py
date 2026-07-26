"""
El control que decide si el resultado de miosina es real o es un espejismo.

Problema: el percentil medio de un sitio alosterico NO se puede comparar contra 50
suponiendo residuos independientes. Los residuos verdaderos forman UN bolsillo
contiguo: estan correlacionados espacialmente, asi que el n efectivo es mucho menor
que el numero de residuos y cualquier prueba que suponga independencia infla la
significancia.

Null correcto: bolsillos CONTIGUOS aleatorios del mismo tamano. Se sortea un residuo
distal semilla y se toman sus k-1 vecinos distales mas cercanos (k = tamano del sitio
verdadero). Eso preserva la contiguidad, el tamano y la restriccion distal. Se repite
NPERM veces y se compara el percentil medio del sitio verdadero contra esa
distribucion. El p-valor resultante es el unico honesto.

Se aplica a TODOS los metodos, no solo al cuantico.
"""
import json, sys, numpy as np
sys.path.insert(0, "/home/claude/rosettaq")
from allo_challenge import *

NPERM = 2000
RS = np.random.RandomState(20260717)

TARGETS = [
    ("KRAS_G12C", "4OBE", "A", "challenge_results_part1.json"),
    ("BCR_ABL1", "1OPL", "A", "challenge_results_part1.json"),
    ("CARDIAC_MYOSIN", "5TBY", "A", "challenge_results_part2.json"),
]

# configuracion central de la rejilla congelada (mediana de cutoffs, ventana media)
CUT, WIN = 8.5, (0.5, 8.0)


def contiguous_null(coords, distal, k, nperm):
    """Bolsillos contiguos aleatorios: semilla distal + sus k-1 vecinos distales."""
    C = coords[distal]
    out = []
    for _ in range(nperm):
        s = RS.randint(len(distal))
        d = np.linalg.norm(C - C[s], axis=1)
        out.append(distal[np.argsort(d)[:k]])
    return out


report = {}
for name, apo_pdb, chain, src_json in TARGETS:
    T = json.load(open("/home/claude/rosettaq/" + src_json))[name]
    apo = load(apo_pdb)
    sel = "protein and name CA and chain %s" % chain
    A, ids, coords, seq, D = ca_network(apo, sel, CUT)
    src = idx_of(ids, [tuple(x) for x in T["source_residues"]])
    allo = idx_of(ids, [tuple(x) for x in T["gt_residues"]])
    mask = D[:, src].min(axis=1) > DISTAL_A
    distal = np.where(mask)[0]
    allo_d = [a for a in allo if mask[a]]
    k = len(allo_d)

    P, _, _ = props(A, src, *WIN)
    scores = {"ctqw": P["ctqw"][0], "diffusion": P["diffusion"][0],
              "gnm": gnm_score(A, src),
              "betweenness": betweenness_closeness(A, src)[0],
              "closeness": betweenness_closeness(A, src)[1]}
    if len(ids) <= 1200:
        scores["anm"] = anm_score(coords, src)

    pockets = contiguous_null(coords, distal, k, NPERM)
    r = {"config": {"cutoff": CUT, "window": list(WIN), "n_nodes": len(ids),
                    "n_distal": len(distal), "k_site": k, "nperm": NPERM}}
    for m, v in scores.items():
        obs = percentile(v, allo_d, mask)
        null = np.array([percentile(v, list(p), mask) for p in pockets])
        p_hi = float((null >= obs).mean())          # sitio mejor rankeado que el azar
        p_lo = float((null <= obs).mean())          # sitio PEOR que el azar
        r[m] = {"percentil_observado": round(obs, 2),
                "null_media": round(float(null.mean()), 2),
                "null_sd": round(float(null.std()), 2),
                "null_p05": round(float(np.percentile(null, 5)), 2),
                "null_p95": round(float(np.percentile(null, 95)), 2),
                "p_mejor_que_azar": round(p_hi, 4),
                "p_peor_que_azar": round(p_lo, 4),
                "z_aparente_si_iid": round((obs - 50.0) / (28.87 / np.sqrt(k)), 2),
                "z_real_contiguo": round(float((obs - null.mean()) / max(null.std(), 1e-9)), 2)}
    report[name] = r
    print("==", name, " k=%d  n_distal=%d" % (k, len(distal)))
    for m in scores:
        x = r[m]
        print("   %-12s obs=%5.1f  null=%5.1f+-%4.1f  z_iid=%+5.2f  z_real=%+5.2f  "
              "p(mejor)=%.3f p(peor)=%.3f"
              % (m, x["percentil_observado"], x["null_media"], x["null_sd"],
                 x["z_aparente_si_iid"], x["z_real_contiguo"],
                 x["p_mejor_que_azar"], x["p_peor_que_azar"]))

json.dump(report, open("/home/claude/rosettaq/spatial_null.json", "w"),
          indent=1, ensure_ascii=False)
print("\nguardado spatial_null.json")
