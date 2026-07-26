"""
La prueba que responde LA pregunta del reto: en el mismo grafo, con la misma fuente
y la misma ventana, la caminata cuantica, comparada CONTRA la difusion clasica,
ranquea mejor el bolsillo verdadero?

Se prueba la DIFERENCIA pareada (cuantico - clasico) contra el null de bolsillos
contiguos. La diferencia pareada tiene mucha menos varianza que cada percentil por
separado, porque ambos propagadores comparten grafo, fuente y ventana; es la prueba
mas potente disponible, y por eso es la que hay que reportar aunque salga negativa.

Se corre sobre la REJILLA COMPLETA congelada en PR-CLEV-001 (18 configuraciones por
diana), no sobre una configuracion elegida. Se reporta cada celda.
"""
import json, sys, numpy as np
sys.path.insert(0, "/home/claude/rosettaq")
from allo_challenge import *

NPERM = 5000
SEED = 20260717

TARGETS = [("KRAS_G12C", "4OBE", "A", "challenge_results_part1.json"),
           ("BCR_ABL1", "1OPL", "A", "challenge_results_part1.json"),
           ("CARDIAC_MYOSIN", "5TBY", "A", "challenge_results_part2.json")]


def pct_vector(prop, distal):
    """Percentil de cada residuo distal dentro del conjunto distal (100 = el mejor)."""
    order = distal[np.argsort(-prop[distal])]
    pv = np.zeros(prop.shape[0])
    m = len(order) - 1
    for k, idx in enumerate(order):
        pv[idx] = 100.0 * (1 - k / m)
    return pv


report = {}
for name, apo_pdb, chain, src_json in TARGETS:
    T = json.load(open("/home/claude/rosettaq/" + src_json))[name]
    apo = load(apo_pdb)
    sel = "protein and name CA and chain %s" % chain
    rows = []
    for cutoff in CUTOFFS:
        A, ids, coords, seq, D = ca_network(apo, sel, cutoff)
        src = idx_of(ids, [tuple(x) for x in T["source_residues"]])
        allo = idx_of(ids, [tuple(x) for x in T["gt_residues"]])
        mask = D[:, src].min(axis=1) > DISTAL_A
        distal = np.where(mask)[0]
        allo_d = np.array([a for a in allo if mask[a]])
        k = len(allo_d)

        # bolsillos contiguos aleatorios: identicos para todas las ventanas
        rs = np.random.RandomState(SEED)
        C = coords[distal]
        pockets = np.empty((NPERM, k), dtype=int)
        for p in range(NPERM):
            s = rs.randint(len(distal))
            d = np.linalg.norm(C - C[s], axis=1)
            pockets[p] = distal[np.argsort(d)[:k]]

        for (tlo, thi) in WINDOWS:
            P, _, _ = props(A, src, tlo, thi)
            pq = pct_vector(P["ctqw"][0], distal)
            pc = pct_vector(P["diffusion"][0], distal)
            dv = pq - pc
            obs = float(dv[allo_d].mean())
            null = dv[pockets].mean(axis=1)
            rows.append({
                "cutoff": cutoff, "window": [tlo, thi], "k_site": k,
                "n_distal": int(len(distal)),
                "pct_ctqw": round(float(pq[allo_d].mean()), 2),
                "pct_diffusion": round(float(pc[allo_d].mean()), 2),
                "delta_obs": round(obs, 2),
                "null_media": round(float(null.mean()), 2),
                "null_sd": round(float(null.std()), 2),
                "z": round(float((obs - null.mean()) / max(null.std(), 1e-9)), 2),
                "p_cuantico_mejor": round(float((null >= obs).mean()), 4),
                "p_cuantico_peor": round(float((null <= obs).mean()), 4)})

    z = np.array([r["z"] for r in rows])
    dl = np.array([r["delta_obs"] for r in rows])
    pmej = np.array([r["p_cuantico_mejor"] for r in rows])
    report[name] = {
        "nperm": NPERM, "n_configs": len(rows),
        "delta_medio": round(float(dl.mean()), 2),
        "configs_delta_positivo": int((dl > 0).sum()),
        "z_medio": round(float(z.mean()), 2),
        "z_min": round(float(z.min()), 2), "z_max": round(float(z.max()), 2),
        "configs_p_menor_005": int((pmej < 0.05).sum()),
        "p_mediano": round(float(np.median(pmej)), 4),
        "rows": rows}
    print("== %-15s delta medio=%+6.2f  (%d/%d configs con delta>0)  z medio=%+5.2f "
          "[%+5.2f,%+5.2f]  p mediano=%.3f  configs p<0.05: %d"
          % (name, dl.mean(), (dl > 0).sum(), len(rows), z.mean(), z.min(), z.max(),
             np.median(pmej), (pmej < 0.05).sum()))

json.dump(report, open("/home/claude/rosettaq/paired_null.json", "w"),
          indent=1, ensure_ascii=False)
print("\nguardado paired_null.json")
