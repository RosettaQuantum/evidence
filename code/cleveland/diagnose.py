"""
Diagnostico: POR QUE fallan los propagadores en el set oficial, y prueba de una
metrica correctiva cuantico-nativa.

Hipotesis H1 (estructural): los bolsillos alostericos cripticos estan SUB-conectados
  en la red de contactos de la apo (apenas existen antes de que el farmaco los abra).
  Cualquier score que premie centralidad los va a hundir sistematicamente.
Hipotesis H2 (metrica): la senal util no es la AMPLITUD de la caminata en el residuo,
  sino su SENSIBILIDAD: cuanto cambia la propagacion global al perturbar localmente
  ese residuo (eco de Loschmidt). Es cuantico-nativo y apunta a criptidad, no a grado.
"""
import json, sys, numpy as np, prody
sys.path.insert(0, "/home/claude/rosettaq")
from allo_challenge import *

CUT = 8.5
WIN = (0.5, 8.0)
EPS = 1.0


def loschmidt(A, src_idx, t_lo, t_hi, n_times=NTIMES, eps=EPS):
    """sensibilidad_i = 1 - |<psi(t)|psi_i'(t)>|^2 promediado en la ventana,
    donde psi' evoluciona bajo A + eps|i><i|."""
    n = A.shape[0]
    TS = np.linspace(t_lo, t_hi, n_times)
    psi0 = np.zeros(n); psi0[src_idx] = 1.0 / np.sqrt(len(src_idx))
    w, V = np.linalg.eigh(A)
    c = V.T @ psi0
    base = [V @ (np.exp(-1j * w * t) * c) for t in TS]
    out = np.zeros(n)
    for i in range(n):
        Ai = A.copy(); Ai[i, i] += eps
        wi, Vi = np.linalg.eigh(Ai)
        ci = Vi.T @ psi0
        acc = 0.0
        for k, t in enumerate(TS):
            psi = Vi @ (np.exp(-1j * wi * t) * ci)
            acc += 1.0 - abs(np.vdot(base[k], psi)) ** 2
        out[i] = acc / len(TS)
    return out


def classical_prs(A, src_idx, t_lo, t_hi, n_times=NTIMES, eps=EPS):
    """Control clasico exacto del mismo experimento: cuanto cambia la difusion."""
    n = A.shape[0]
    TS = np.linspace(t_lo, t_hi, n_times)
    p0 = np.zeros(n); p0[src_idx] = 1.0 / len(src_idx)
    L = np.diag(A.sum(1)) - A
    w, V = np.linalg.eigh(L)
    c = V.T @ p0
    base = [V @ (np.exp(-w * t * 0.15) * c) for t in TS]
    out = np.zeros(n)
    for i in range(n):
        Li = L.copy(); Li[i, i] += eps
        wi, Vi = np.linalg.eigh(Li)
        ci = Vi.T @ p0
        acc = 0.0
        for k, t in enumerate(TS):
            p = Vi @ (np.exp(-wi * t * 0.15) * ci)
            acc += float(np.abs(base[k] - p).sum())
        out[i] = acc / len(TS)
    return out


TARGETS = json.load(open("/home/claude/rosettaq/challenge_results_part1.json"))
report = {}
for name, T in TARGETS.items():
    apo = prody.parsePDB("/tmp/%s.pdb.gz" % T["apo"].lower())
    sel = "protein and name CA and chain %s" % T["chain"]
    A, ids, coords, seq, D = ca_network(apo, sel, CUT)
    src = idx_of(ids, [tuple(x) for x in T["source_residues"]])
    allo = idx_of(ids, [tuple(x) for x in T["gt_residues"]])
    dmin = D[:, src].min(axis=1)
    mask = dmin > DISTAL_A
    deg = A.sum(1)
    distal = np.where(mask)[0]
    allo_d = [a for a in allo if mask[a]]

    # --- H1: conectividad de los residuos verdaderos vs el resto de los distales
    h1 = {
        "grado_medio_sitio_alosterico": round(float(deg[allo_d].mean()), 2),
        "grado_medio_distales": round(float(deg[distal].mean()), 2),
        "grado_mediana_distales": round(float(np.median(deg[distal])), 2),
        "percentil_de_grado_del_sitio": round(float(
            100.0 * (deg[distal] < deg[allo_d].mean()).mean()), 1),
    }

    # --- H2: metrica de sensibilidad
    ls = loschmidt(A, src, *WIN)
    pr = classical_prs(A, src, *WIN)
    P, _, _ = props(A, src, *WIN)
    scores = {"ctqw_amplitud": P["ctqw"][0], "difusion_amplitud": P["diffusion"][0],
              "gnm": gnm_score(A, src),
              "eco_loschmidt_cuantico": ls, "respuesta_perturbacion_clasica": pr}
    h2 = {}
    for k, v in scores.items():
        h5, top5 = topk_hits(v, allo, mask, 5)
        h10, _ = topk_hits(v, allo, mask, 10)
        h2[k] = {"percentil": round(percentile(v, allo, mask), 2),
                 "top5_aciertos": h5, "top10_aciertos": h10,
                 "top5_residuos": [list(ids[i]) for i in top5]}
    report[name] = {"config": {"cutoff": CUT, "window": list(WIN), "eps": EPS,
                               "n_nodes": len(ids), "n_distal": int(mask.sum()),
                               "n_allo_distal": len(allo_d)},
                    "H1_conectividad": h1, "H2_metricas": h2}
    print("==", name, T["apo"], "->", T["holo"])
    print("   H1  grado sitio=%(grado_medio_sitio_alosterico)s  distales=%(grado_medio_distales)s"
          "  (el sitio esta en el percentil %(percentil_de_grado_del_sitio)s de grado)" % h1)
    for k, v in h2.items():
        print("   H2  %-32s pct=%6.2f  top5=%d  top10=%d" %
              (k, v["percentil"], v["top5_aciertos"], v["top10_aciertos"]))

json.dump(report, open("/home/claude/rosettaq/diagnosis.json", "w"),
          indent=1, ensure_ascii=False)
print("\nguardado diagnosis.json")
