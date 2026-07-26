"""
Entregables exigidos que faltaban: (a) la matriz N x N de conectividad cuantica y
(b) la visualizacion 3D interpretable. Ambas se generan del MISMO objeto: el
propagador cuantico sobre la red de contactos, en la configuracion central de la
rejilla congelada.

La matriz de conectividad cuantica se define como C_ij = suma_t |<i|e^{-iAt}|j>|^2
sobre la ventana temporal: la probabilidad integrada de transferencia entre cada par
de residuos. Es simetrica, N x N, y es literalmente lo que el reto pide.

La visualizacion es un HTML autocontenido: no descarga nada al abrirse.
"""
import json, sys, numpy as np
sys.path.insert(0, "/home/claude/rosettaq")
from allo_challenge import *

CUT, WIN = 8.5, (0.5, 8.0)
TARGETS = [("KRAS_G12C", "4OBE", "A", "challenge_results_part1.json", "KRAS G12C (4OBE)"),
           ("BCR_ABL1", "1OPL", "A", "challenge_results_part1.json", "BCR-ABL1 (1OPL)"),
           ("CARDIAC_MYOSIN", "5TBY", "A", "challenge_results_part2.json", "Miosina cardiaca (5TBY)"),
           ("c_MYC", "1NKP", None, "challenge_results_part2.json", "c-Myc / Max (1NKP)")]


def qmatrix(A, t_lo, t_hi, n_times=NTIMES):
    """C_ij = sum_t |U(t)_ij|^2 — matriz de conectividad cuantica N x N."""
    w, V = np.linalg.eigh(A)
    C = np.zeros(A.shape)
    for t in np.linspace(t_lo, t_hi, n_times):
        U = (V * np.exp(-1j * w * t)) @ V.T
        C += np.abs(U) ** 2
    return C / n_times


payload = {}
for name, pdb, chain, srcfile, label in TARGETS:
    T = json.load(open("/home/claude/rosettaq/" + srcfile))[name]
    apo = load(pdb)
    sel = ("protein and name CA and chain %s" % chain) if chain else \
          "protein and name CA and (chain A or chain B)"
    A, ids, coords, seq, D = ca_network(apo, sel, CUT)
    src = idx_of(ids, [tuple(x) for x in T["source_residues"]])
    allo = idx_of(ids, [tuple(x) for x in T["gt_residues"]]) if T["gt_residues"] else []
    mask = D[:, src].min(axis=1) > DISTAL_A

    C = qmatrix(A, *WIN)
    q = props(A, src, *WIN)[0]["ctqw"][0]
    d = props(A, src, *WIN)[0]["diffusion"][0]
    sites = cluster_sites(q, mask, coords, ids, n_sites=5)

    np.save("/home/claude/rosettaq/qmatrix_%s.npy" % name, C)
    payload[name] = {
        "label": label, "pdb": pdb, "n": len(ids),
        "coords": [[round(float(x), 2) for x in c] for c in coords],
        "resnum": [int(r) for _, r in ids],
        "chain": [c for c, _ in ids],
        "ctqw": [round(float(x), 6) for x in q],
        "diff": [round(float(x), 6) for x in d],
        "src": [int(i) for i in src],
        "allo": [int(i) for i in allo],
        "distal": [bool(m) for m in mask],
        "sites": sites,
        "qmatrix_file": "qmatrix_%s.npy" % name,
        "qmatrix_shape": list(C.shape),
        "qmatrix_checksum_trace": round(float(np.trace(C)), 6),
    }
    print("%-16s n=%4d  matriz %dx%d  sitios=%d  |  traza=%.4f"
          % (name, len(ids), C.shape[0], C.shape[1], len(sites), np.trace(C)))

json.dump(payload, open("/home/claude/rosettaq/viz_payload.json", "w"),
          separators=(",", ":"))
print("\nviz_payload.json y matrices N x N guardadas")
