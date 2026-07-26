"""
Los tres entregables que el reto EXIGE y que la propuesta actual no tiene:
  (1) resiliencia al ruido, (2) escalabilidad por coarse-graining, (3) costo de
  circuito real (qubits y profundidad), medido — no citado de una cota asintotica.

(3) se mide asi: la caminata se descompone en clases de aristas disjuntas mediante
coloreo voraz de aristas. Cada clase es un emparejamiento (matching), y el
exponencial de un emparejamiento es EXACTO y cerrado: bloques 2x2 de cos/-i sin.
Se construye el producto de Trotter de primer orden y se mide cuantos pasos r hacen
falta para que el RANKING converja (Spearman >= 0.99 contra el propagador exacto),
que es una exigencia mucho mas debil que converger el estado. Esa es la profundidad
que el reto realmente necesita, y es la respuesta a "los circuitos profundos sin
optimizar seran penalizados".
"""
import json, sys, math, time, numpy as np
sys.path.insert(0, "/home/claude/rosettaq")
from allo_challenge import *
from scipy.stats import spearmanr

CUT, WIN = 8.5, (0.5, 8.0)
RS = np.random.RandomState(7)

TARGETS = [("KRAS_G12C", "4OBE", "A", "challenge_results_part1.json"),
           ("BCR_ABL1", "1OPL", "A", "challenge_results_part1.json"),
           ("CARDIAC_MYOSIN", "5TBY", "A", "challenge_results_part2.json")]


# ------------------------------------------------------------------ circuito
def edge_coloring(A):
    """Coloreo voraz de aristas: cada color es un emparejamiento (1-disperso).
    Vizing garantiza <= Delta+1 colores; se reporta lo que realmente sale."""
    n = A.shape[0]
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if A[i, j]]
    used = [set() for _ in range(n)]
    colors = {}
    for (i, j) in edges:
        c = 0
        while c in used[i] or c in used[j]:
            c += 1
        colors[(i, j)] = c
        used[i].add(c); used[j].add(c)
    ncol = max(colors.values()) + 1 if colors else 0
    classes = [[] for _ in range(ncol)]
    for (i, j), c in colors.items():
        classes[c].append((i, j))
    return classes, len(edges)


def apply_matching(psi, I, J, c, s):
    """exp(-i*M*dt) aplicado en sitio para un emparejamiento M: bloques 2x2 exactos.
    Sin matrices densas — es lo que hace que la simulacion de Trotter escale."""
    a, b = psi[I], psi[J]
    psi[I] = c * a - 1j * s * b
    psi[J] = c * b - 1j * s * a
    return psi


def trotter_walk(classes, n, src_idx, t_lo, t_hi, r, n_times=NTIMES):
    """Caminata bajo el producto de Trotter de primer orden, r pasos por muestra."""
    TS = np.linspace(t_lo, t_hi, n_times)
    idx = [(np.array([p[0] for p in cl]), np.array([p[1] for p in cl]))
           for cl in classes]
    psi0 = np.zeros(n, dtype=complex); psi0[src_idx] = 1.0 / np.sqrt(len(src_idx))
    acc = np.zeros(n)
    for t in TS:
        dt = t / r
        c, s = math.cos(dt), math.sin(dt)
        psi = psi0.copy()
        for _ in range(r):
            for (I, J) in idx:
                psi = apply_matching(psi, I, J, c, s)
        acc += np.abs(psi) ** 2
    return acc


# ------------------------------------------------------------------ ruido
def dephasing_walk(A, src_idx, t_lo, t_hi, gamma, n_traj=24, n_times=NTIMES, ksub=8):
    """Desfase de hardware por desdoblamiento estocastico. El ruido de fase se
    INTERCALA con la evolucion (ksub subintervalos): aplicado solo al final no
    tendria efecto sobre las poblaciones, que es lo que se mide. Promedio sobre
    trayectorias = canal de defasaje. Es el canal dominante en hardware real."""
    n = A.shape[0]
    TS = np.linspace(t_lo, t_hi, n_times)
    w, V = np.linalg.eigh(A)
    psi0 = np.zeros(n, dtype=complex); psi0[src_idx] = 1.0 / np.sqrt(len(src_idx))
    acc = np.zeros(n)
    rs = np.random.RandomState(11)
    for _ in range(n_traj):
        for t in TS:
            dt = t / ksub
            phase = np.exp(-1j * w * dt)
            psi = psi0.copy()
            for _k in range(ksub):
                psi = V @ (phase * (V.T @ psi))
                if gamma > 0:
                    psi = psi * np.exp(1j * rs.normal(0, math.sqrt(gamma * dt), n))
            acc += np.abs(psi) ** 2
    return acc / n_traj


def coordinate_noise(coords, sigma, rs):
    return coords + rs.normal(0, sigma, coords.shape)


def edge_dropout(A, p, rs):
    B = A.copy()
    idx = np.transpose(np.nonzero(np.triu(B)))
    kill = idx[rs.rand(len(idx)) < p]
    for i, j in kill:
        B[i, j] = B[j, i] = 0.0
    return B


# ------------------------------------------------------------ coarse-graining
def coarse_grain(A, coords, ids, allo_idx, src_idx, block):
    """Agrupa residuos consecutivos en super-nodos de tamano `block` (modelo de
    grano grueso estandar). Un super-nodo es alosterico si contiene un residuo
    alosterico; la fuente hereda igual."""
    n = A.shape[0]
    grp = np.arange(n) // block
    m = grp.max() + 1
    T = np.zeros((n, m)); T[np.arange(n), grp] = 1.0
    Ac = T.T @ A @ T
    np.fill_diagonal(Ac, 0.0)
    Ac = (Ac > 0).astype(float)
    cc = (T.T @ coords) / T.sum(0)[:, None]
    allo_c = sorted(set(grp[a] for a in allo_idx))
    src_c = sorted(set(grp[s] for s in src_idx))
    return Ac, cc, allo_c, src_c, m


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
    n = len(ids)

    t0 = time.time()
    base = props(A, src, *WIN)[0]["ctqw"][0]
    t_exact = time.time() - t0
    base_pct = percentile(base, allo, mask)
    R = {"n_nodes": n, "cutoff": CUT, "window": list(WIN),
         "percentil_base": round(base_pct, 2), "t_exacto_s": round(t_exact, 3)}

    # ---- (1a) ruido de coordenadas
    R["ruido_coordenadas"] = []
    for sig in (0.25, 0.5, 1.0):
        rs = np.random.RandomState(3)
        sp, pc = [], []
        for _ in range(10):
            cn = coordinate_noise(coords, sig, rs)
            d = np.linalg.norm(cn[:, None] - cn[None], axis=-1)
            An = ((d < CUT) & (d > 0)).astype(float)
            v = props(An, src, *WIN)[0]["ctqw"][0]
            sp.append(spearmanr(v[distal], base[distal]).correlation)
            pc.append(percentile(v, allo, mask))
        R["ruido_coordenadas"].append(
            {"sigma_A": sig, "spearman_medio": round(float(np.mean(sp)), 4),
             "percentil_medio": round(float(np.mean(pc)), 2),
             "percentil_sd": round(float(np.std(pc)), 2)})

    # ---- (1b) perdida de aristas (error del mapa de contactos)
    R["perdida_aristas"] = []
    for p in (0.01, 0.05, 0.10):
        rs = np.random.RandomState(5)
        sp, pc = [], []
        for _ in range(10):
            An = edge_dropout(A, p, rs)
            v = props(An, src, *WIN)[0]["ctqw"][0]
            sp.append(spearmanr(v[distal], base[distal]).correlation)
            pc.append(percentile(v, allo, mask))
        R["perdida_aristas"].append(
            {"p": p, "spearman_medio": round(float(np.mean(sp)), 4),
             "percentil_medio": round(float(np.mean(pc)), 2),
             "percentil_sd": round(float(np.std(pc)), 2)})

    # ---- (1c) desfase de hardware
    R["desfase_hardware"] = []
    for g in (0.0, 0.01, 0.05, 0.2, 1.0):
        v = dephasing_walk(A, src, *WIN, gamma=g)
        R["desfase_hardware"].append(
            {"gamma": g, "spearman_vs_ideal": round(float(spearmanr(v[distal], base[distal]).correlation), 4),
             "percentil": round(percentile(v, allo, mask), 2)})

    # ---- (2) coarse-graining
    R["coarse_graining"] = []
    for b in (1, 2, 4, 8):
        Ac, cc, allo_c, src_c, m = coarse_grain(A, coords, ids, allo, src, b)
        dd = np.linalg.norm(cc[:, None] - cc[None], axis=-1)
        maskc = dd[:, src_c].min(axis=1) > DISTAL_A
        t0 = time.time()
        v = props(Ac, src_c, *WIN)[0]["ctqw"][0]
        dt = time.time() - t0
        R["coarse_graining"].append(
            {"bloque": b, "n_supernodos": m,
             "percentil": round(percentile(v, allo_c, maskc), 2),
             "t_s": round(dt, 4),
             "aceleracion": round(t_exact / max(dt, 1e-6), 1)})

    # ---- (3) costo de circuito
    classes, nedges = edge_coloring(A)
    nq = int(math.ceil(math.log2(n)))
    conv = None
    trot = []
    for r in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512):
        v = trotter_walk(classes, n, src, *WIN, r=r)
        sc = float(spearmanr(v[distal], base[distal]).correlation)
        trot.append({"r": r, "spearman_vs_exacto": round(sc, 4),
                     "percentil": round(percentile(v, allo, mask), 2)})
        if conv is None and sc >= 0.99:
            conv = r
            break
    R["circuito"] = {
        "qubits_codificacion_binaria": nq,
        "aristas": nedges,
        "grado_maximo": int(A.sum(1).max()),
        "clases_de_color": len(classes),
        "trotter": trot,
        "r_para_spearman_099": conv,
        "profundidad_por_paso_2q": len(classes),
        "profundidad_total_2q": (len(classes) * conv) if conv else None,
        "nota": "cada clase de color es un emparejamiento: en codificacion binaria se "
                "implementa como una permutacion + una rotacion controlada, profundidad "
                "O(qubits) en 2-qubit gates. La profundidad total reportada esta en "
                "unidades de clases de color por paso de Trotter."}
    report[name] = R
    print("==", name, "n=%d  pct_base=%.2f" % (n, base_pct))
    print("   ruido coord:", [(x["sigma_A"], x["spearman_medio"], x["percentil_medio"]) for x in R["ruido_coordenadas"]])
    print("   perdida aristas:", [(x["p"], x["spearman_medio"], x["percentil_medio"]) for x in R["perdida_aristas"]])
    print("   desfase:", [(x["gamma"], x["spearman_vs_ideal"], x["percentil"]) for x in R["desfase_hardware"]])
    print("   coarse:", [(x["bloque"], x["n_supernodos"], x["percentil"], x["aceleracion"]) for x in R["coarse_graining"]])
    print("   circuito: qubits=%d aristas=%d colores=%d r99=%s" % (nq, nedges, len(classes), conv))
    if trot:
        print("   trotter:", [(x["r"], x["spearman_vs_exacto"]) for x in trot])

json.dump(report, open("/home/claude/rosettaq/required_deliverables.json", "w"),
          indent=1, ensure_ascii=False, default=lambda o: int(o) if isinstance(o, np.integer) else float(o))
print("\nguardado required_deliverables.json")
