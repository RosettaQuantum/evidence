"""
Evaluacion registrada: grafo PELADO vs grafo ANOTADO (Glifo), bajo el MISMO nulo
espacial de bolsillo contiguo del run sellado EXP-0007-017. Config central de la
rejilla congelada (cut 8.5, ventana 0.5-8.0). src/allo se toman del registro sellado
(challenge_results), no se reconstruyen.

PESOS PRE-REGISTRADOS (declarados aqui, NO tuneados mirando el resultado):
  uni_binding_site=1.0, uni_active_site=1.0, clinvar_density=0.5, coordination=0.3
  aristas gaussianas. Son los mismos del smoke test; no se ajustan por diana.
"""
import json, sys, numpy as np
sys.path.insert(0, "/home/claude/rosettaq")
from allo_challenge import idx_of, props, percentile, DISTAL_A
from sigo_features import build_feature_table, annotated_hamiltonian

NPERM = 2000
RS = np.random.RandomState(20260717)   # misma semilla que spatial_null.py
CUT, WIN = 8.5, (0.5, 8.0)
WEIGHTS = {"uni_binding_site": 1.0, "uni_active_site": 1.0,
           "clinvar_density": 0.5, "coordination": 0.3}   # PRE-REGISTRADOS
TARGETS = [("KRAS_G12C", "challenge_results_part1.json"),
           ("BCR_ABL1", "challenge_results_part1.json"),
           ("CARDIAC_MYOSIN", "challenge_results_part2.json")]
MAN = json.load(open("/home/claude/rosettaq/cleveland_manifest.json"))["targets"]


def ctqw_on(M, src):
    n = M.shape[0]; TS = np.linspace(*WIN, 16)
    w, V = np.linalg.eigh(M)
    psi = np.zeros(n); psi[src] = 1/np.sqrt(len(src)); c = V.T @ psi
    q = np.zeros(n)
    for t in TS:
        q += np.abs(V @ (np.exp(-1j*w*t)*c))**2
    return q


def contiguous_null(coords, distal, k, nperm):
    C = coords[distal]; out = []
    for _ in range(nperm):
        s = RS.randint(len(distal))
        d = np.linalg.norm(C - C[s], axis=1)
        out.append(distal[np.argsort(d)[:k]])
    return out


report = {}
for name, src_json in TARGETS:
    T = json.load(open("/home/claude/rosettaq/" + src_json))[name]
    ft = build_feature_table(MAN[name], cutoff=CUT)
    A, ids, coords, feats = ft["A"], ft["ids"], ft["coords"], ft["features"]
    src = idx_of(ids, [tuple(x) for x in T["source_residues"]])
    allo = idx_of(ids, [tuple(x) for x in T["gt_residues"]])
    D = np.linalg.norm(coords[:, None, :] - coords[src][None, :, :], axis=-1)
    mask = D.min(axis=1) > DISTAL_A
    distal = np.where(mask)[0]
    allo_d = [a for a in allo if mask[a]]
    k = len(allo_d)

    H, hmeta = annotated_hamiltonian(A, coords, feats, WEIGHTS, edge_mode="gaussian")
    scores = {"ctqw_bare": ctqw_on(A, src),
              "ctqw_glifo": ctqw_on(H, src),
              "diffusion": props(A, src, *WIN)[0]["diffusion"][0]}
    pockets = contiguous_null(coords, distal, k, NPERM)
    r = {"n": len(ids), "n_distal": len(distal), "k_site": k}
    for m, v in scores.items():
        obs = percentile(v, allo_d, mask)
        null = np.array([percentile(v, list(p), mask) for p in pockets])
        r[m] = {"obs": round(obs, 2), "null_mean": round(float(null.mean()), 2),
                "p_better_than_chance": round(float((null >= obs).mean()), 4),
                "z_real_contiguous": round(float((obs-null.mean())/max(null.std(), 1e-9)), 2)}
    r["glifo_minus_bare_pct"] = round(r["ctqw_glifo"]["obs"] - r["ctqw_bare"]["obs"], 2)
    report[name] = r
    print("== %s  n=%d n_distal=%d k=%d" % (name, len(ids), len(distal), k))
    for m in scores:
        x = r[m]
        print("   %-11s obs=%5.1f  null=%5.1f  p(better)=%.3f  z_real=%+.2f"
              % (m, x["obs"], x["null_mean"], x["p_better_than_chance"], x["z_real_contiguous"]))
    print("   Δ Glifo-pelado = %+.2f pct" % r["glifo_minus_bare_pct"])

json.dump(report, open("/home/claude/rosettaq/glifo_eval.json", "w"), indent=1, ensure_ascii=False)
print("\nguardado glifo_eval.json  |  pesos:", WEIGHTS)
