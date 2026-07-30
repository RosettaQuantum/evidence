"""
RosettaQ — suite del track Cleveland Clinic sobre el CONJUNTO DE VALIDACION OFICIAL.

Protocolo (Juez-v2, extension del juez-v1 pre-registrado en PR-CLEV-001):
  ENTRADA  = estructura apo (sin farmaco). Solo topologia: red de contactos Ca.
  FUENTE   = sitio activo, leido GEOMETRICAMENTE del ligando natural de la apo
             (GDP+Mg en KRAS; inhibidor de sitio ATP en ABL; motivo Walker-A en
             miosina; contactos con el ADN en c-Myc). Nunca numeros memorizados.
  ARBITRO  = residuos <4.5 A del farmaco en la estructura holo, mapeados a la apo
             por numero de residuo (verificado por identidad de secuencia).
  RIVALES  = difusion clasica, GNM, ANM, betweenness, closeness, nulo aleatorio.
             Los tres del medio son las lineas base REALES del campo, no inventadas.
  METRICA  = percentil medio del sitio verdadero entre residuos distales (>6 A de
             la fuente) + enriquecimiento en top-5 / top-10 + sitios agrupados.

Rejilla de parametros: la ya sellada en PR-CLEV-001 (cutoffs 7.5..10.0, ventanas
0.5-4 / 0.5-8 / 0.5-14). No se ajusta nada por proteina. Se reporta cada celda.
"""
import os, json, time, itertools, platform, datetime
import numpy as np
import prody
prody.confProDy(verbosity='none')

CUTOFFS = [7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
WINDOWS = [(0.5, 4.0), (0.5, 8.0), (0.5, 14.0)]
NTIMES = 16
DISTAL_A = 6.0
GT_RADIUS = 4.5

PDBDIR = "/tmp"


def load(pdb):
    return prody.parsePDB(os.path.join(PDBDIR, pdb.lower() + ".pdb.gz"))


def ca_network(atoms, sel, cutoff):
    ca = atoms.select(sel)
    coords = ca.getCoords()
    ids = [(c, int(r)) for c, r in zip(ca.getChids(), ca.getResnums())]
    seq = ca.getSequence()
    d = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    A = ((d < cutoff) & (d > 0)).astype(float)
    return A, ids, coords, seq, d


def contacts(atoms, ligsel, protsel, radius=GT_RADIUS):
    """Residuos (chain,resnum) de protsel con algun atomo a <radius del ligando."""
    q = atoms.select("(%s) and same residue as (within %g of (%s))"
                     % (protsel, radius, ligsel))
    if q is None:
        return []
    return sorted(set((c, int(r)) for c, r in zip(q.getChids(), q.getResnums())))


def idx_of(ids, targets):
    s = set(targets)
    return [i for i, k in enumerate(ids) if k in s]


# ---------------------------------------------------------------- propagadores
def props(A, src_idx, t_lo, t_hi, n_times=NTIMES):
    """Todos los propagadores sobre el MISMO grafo y la MISMA fuente."""
    n = A.shape[0]
    TS = np.linspace(t_lo, t_hi, n_times)
    deg = A.sum(1)
    L = np.diag(deg) - A

    psi0 = np.zeros(n); psi0[src_idx] = 1.0 / np.sqrt(len(src_idx))
    p0 = np.zeros(n);   p0[src_idx] = 1.0 / len(src_idx)

    out = {}

    t0 = time.time()
    wA, VA = np.linalg.eigh(A)
    cA = VA.T @ psi0
    q = np.zeros(n)
    for t in TS:
        q += np.abs(VA @ (np.exp(-1j * wA * t) * cA)) ** 2
    out["ctqw"] = (q, round(time.time() - t0, 3))

    t0 = time.time()
    wL, VL = np.linalg.eigh(L)
    cL = VL.T @ p0
    c = np.zeros(n)
    for t in TS:
        c += VL @ (np.exp(-wL * t * 0.15) * cL)
    out["diffusion"] = (c, round(time.time() - t0, 3))
    return out, (wL, VL), (wA, VA)


def gnm_score(A, src_idx, n_modes=20):
    """GNM: acoplamiento fuente-residuo por covarianza de modos lentos (Bahar).
    Linea base estandar del campo para comunicacion alosterica."""
    deg = A.sum(1)
    K = np.diag(deg) - A
    w, V = np.linalg.eigh(K)
    keep = np.where(w > 1e-9)[0][:n_modes]
    Cov = (V[:, keep] / w[keep]) @ V[:, keep].T
    return np.abs(Cov[:, src_idx]).mean(axis=1)


def anm_score(coords, src_idx, cutoff=15.0, n_modes=20):
    """ANM / perturbation-response: respuesta media al empujar la fuente."""
    n = len(coords)
    H = np.zeros((3 * n, 3 * n))
    d = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    for i in range(n):
        for j in range(i + 1, n):
            if d[i, j] < cutoff and d[i, j] > 0:
                dv = (coords[j] - coords[i]).reshape(3, 1)
                sup = (dv @ dv.T) / d[i, j] ** 2
                H[3*i:3*i+3, 3*j:3*j+3] = -sup
                H[3*j:3*j+3, 3*i:3*i+3] = -sup
                H[3*i:3*i+3, 3*i:3*i+3] += sup
                H[3*j:3*j+3, 3*j:3*j+3] += sup
    w, V = np.linalg.eigh(H)
    keep = np.where(w > 1e-9)[0][:n_modes]
    Cov = (V[:, keep] / w[keep]) @ V[:, keep].T
    # respuesta media |cov 3x3| entre cada residuo y la fuente
    sc = np.zeros(n)
    for i in range(n):
        acc = 0.0
        for s in src_idx:
            acc += np.linalg.norm(Cov[3*i:3*i+3, 3*s:3*s+3])
        sc[i] = acc / len(src_idx)
    return sc


def betweenness_closeness(A, src_idx):
    """Centralidad en el grafo de contactos (BFS sin pesos)."""
    n = A.shape[0]
    adj = [np.nonzero(A[i])[0] for i in range(n)]
    INF = 10 ** 9
    # closeness respecto de la fuente = 1/dist_geodesica
    dist = np.full(n, INF)
    frontier = list(src_idx)
    for s in src_idx:
        dist[s] = 0
    dd = 0
    while frontier:
        dd += 1
        nxt = []
        for u in frontier:
            for v in adj[u]:
                if dist[v] == INF:
                    dist[v] = dd
                    nxt.append(v)
        frontier = nxt
    close = 1.0 / np.maximum(dist, 1)
    # betweenness (Brandes, sin pesos) — caro; se muestrea si n grande
    btw = np.zeros(n)
    sources = range(n) if n <= 700 else np.random.RandomState(0).choice(n, 700, False)
    for s in sources:
        S = []; P = [[] for _ in range(n)]
        sigma = np.zeros(n); sigma[s] = 1
        dist2 = np.full(n, -1); dist2[s] = 0
        Q = [s]
        while Q:
            v = Q.pop(0); S.append(v)
            for w_ in adj[v]:
                if dist2[w_] < 0:
                    dist2[w_] = dist2[v] + 1; Q.append(w_)
                if dist2[w_] == dist2[v] + 1:
                    sigma[w_] += sigma[v]; P[w_].append(v)
        delta = np.zeros(n)
        while S:
            w_ = S.pop()
            for v in P[w_]:
                delta[v] += sigma[v] / sigma[w_] * (1 + delta[w_])
            if w_ != s:
                btw[w_] += delta[w_]
    return btw, close


# ---------------------------------------------------------------- puntuacion
def percentile(prop, allo_idx, mask):
    distal = np.where(mask)[0]
    if len(distal) < 2:
        return 0.0
    order = distal[np.argsort(-prop[distal])]
    pos = {idx: k for k, idx in enumerate(order)}
    pcts = [100.0 * (1 - pos[a] / (len(order) - 1)) for a in allo_idx if a in pos]
    return float(np.mean(pcts)) if pcts else 0.0


def topk_hits(prop, allo_idx, mask, k):
    distal = np.where(mask)[0]
    order = distal[np.argsort(-prop[distal])][:k]
    return int(len(set(order) & set(allo_idx))), [int(i) for i in order]


def cluster_sites(prop, mask, coords, ids, n_sites=5, top_frac=0.10, link=8.0):
    """Agrupa los residuos mejor rankeados en sitios espaciales; devuelve top-N."""
    distal = np.where(mask)[0]
    if len(distal) == 0:
        return []
    k = max(5, int(len(distal) * top_frac))
    top = distal[np.argsort(-prop[distal])][:k]
    unassigned = list(top)
    clusters = []
    while unassigned:
        seed = unassigned.pop(0)
        comp = [seed]; frontier = [seed]
        while frontier:
            u = frontier.pop()
            rest = []
            for v in unassigned:
                if np.linalg.norm(coords[u] - coords[v]) < link:
                    comp.append(v); frontier.append(v)
                else:
                    rest.append(v)
            unassigned = rest
        clusters.append(comp)
    scored = sorted(clusters, key=lambda c: -float(np.mean(prop[c])))[:n_sites]
    out = []
    for c in scored:
        out.append({
            "score": round(float(np.mean(prop[c])), 8),
            "n_residues": len(c),
            "residues": [list(ids[i]) for i in sorted(c, key=lambda i: -prop[i])][:12],
            "centroid": [round(float(x), 2) for x in coords[c].mean(axis=0)],
        })
    return out
