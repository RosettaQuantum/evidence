"""PoC de hardware cuántico (IBM) — caminata cuántica de tiempo continuo (CTQW)
sobre un SUB-GRAFO real de proteína (~16 residuos alrededor del bolsillo alosterico).
Mapeo estandar en el subespacio de una excitacion (modelo XY): salto en arista (i,j)
= exp(-i t w_ij (XiXj+YiYj)/2); potencial on-site v_i = exp(-i t v_i (I-Zi)/2).
Trotter r pasos. Valida la simulacion ideal contra exp(-iHt) exacto.

NO ejecuta en hardware desde aca. Genera el circuito y el script de envio listo
para IBM (Nicholas corre con su API key). El entregable honesto: correr la caminata
en QPU real y medir cuanto la degrada el ruido — capacidad, NO ventaja cuantica."""
import os, sys, glob, pickle, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qiskit import QuantumCircuit
from qiskit.circuit.library import RXXGate, RYYGate, RZGate
from scipy.linalg import expm

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
WIN_T = 6.0          # tiempo total de la caminata
NQ = 12              # nodos del sub-grafo (= qubits)

def load(name):
    return pickle.load(open(os.path.join(CACHE, "%s.pkl"%name), "rb"))

def subgraph(d, nq=NQ):
    """Sub-grafo de nq nodos: fuente (sitio activo) + bolsillo alosterico + puente
    (vecinos por camino mas corto). Devuelve indices, A pesada, potencial, roles."""
    A = d["A"]; n = d["n"]
    src = list(d["src"]); allo = [a for a in d["allo"] if d["mask"][a]]
    # BFS multi-fuente para ordenar por cercania y armar un puente src->allo
    import collections
    keep = set(src[:3]) | set(allo[:8])
    # agregar vecinos de los 'allo' y 'src' hasta llenar nq
    adj = [np.nonzero(A[i])[0] for i in range(n)]
    frontier = list(keep)
    while len(keep) < nq and frontier:
        nxt = []
        for u in frontier:
            for v in adj[u]:
                if len(keep) >= nq: break
                if v not in keep: keep.add(v); nxt.append(v)
        frontier = nxt
    idx = sorted(keep)[:nq]
    remap = {g:i for i,g in enumerate(idx)}
    m = len(idx)
    # adyacencia pesada del sub-grafo (gaussiana por distancia, como el motor)
    coords = d["coords"][idx]
    D = np.linalg.norm(coords[:,None,:]-coords[None,:,:], axis=-1)
    W = np.exp(-(D**2)/(2*6.0**2)) * (A[np.ix_(idx,idx)] > 0)
    np.fill_diagonal(W, 0.0)
    # potencial on-site: conservacion (la variable de novo mas fuerte), normalizada
    _c = d["features"].get("conservation")
    cons = (np.asarray(_c, float) if _c is not None else np.zeros(n))[idx]
    v = (cons - cons.min())/(np.ptp(cons)+1e-9)
    roles = {"src":[remap[s] for s in src if s in remap],
             "allo":[remap[a] for a in allo if a in remap]}
    return idx, W, v, roles

def ctqw_exact(W, v, src_nodes, t):
    """CTQW exacta en el subespacio de 1 excitacion: H = W (hopping) + diag(v)."""
    H = W + np.diag(v)
    psi0 = np.zeros(len(v), complex)
    for s in src_nodes: psi0[s] = 1.0
    psi0 /= np.linalg.norm(psi0)
    psit = expm(-1j*H*t) @ psi0
    return np.abs(psit)**2

def build_circuit(W, v, src_nodes, t, r=3):
    """Circuito Trotter de la CTQW (modelo XY). r pasos."""
    m = len(v); qc = QuantumCircuit(m, m)
    for s in src_nodes: qc.x(s)                     # walker en la fuente
    dt = t/r
    edges = [(i,j,float(W[i,j])) for i in range(m) for j in range(i+1,m) if W[i,j] > 1e-6]
    for _ in range(r):
        for (i,j,w) in edges:
            th = w*dt
            qc.append(RXXGate(2*th), [i,j]); qc.append(RYYGate(2*th), [i,j])
        for i in range(m):
            qc.append(RZGate(-v[i]*dt), [i])         # exp(-i v (I-Z)/2): parte Z
    qc.measure(range(m), range(m))
    return qc

def ideal_probs(qc, m):
    """Simula ideal (Aer statevector antes de medir) y devuelve P(1) por qubit en el
    subespacio de 1 excitacion (normalizado sobre outcomes de peso 1)."""
    from qiskit_aer import AerSimulator
    qc2 = qc.remove_final_measurements(inplace=False)
    from qiskit import transpile
    sim = AerSimulator(method="statevector")
    qc2.save_statevector()
    res = sim.run(transpile(qc2, sim)).result()
    sv = np.asarray(res.get_statevector())
    probs = np.abs(sv)**2
    p1 = np.zeros(m)
    for k, p in enumerate(probs):
        b = format(k, "0%db"%m)[::-1]   # qubit i = bit i
        if b.count("1") == 1:
            p1[b.index("1")] += p
    s = p1.sum()
    return p1/s if s > 0 else p1

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "KRAS_G12C"
    d = load(name); idx, W, v, roles = subgraph(d)
    m = len(idx); allo = set(roles["allo"])
    src = [(roles["src"] or [0])[0]]   # UNA sola fuente = una excitacion limpia
    print("proteina %s | sub-grafo %d nodos | fuente %s | bolsillo alo %s" % (name, m, src, sorted(allo)))
    exact = ctqw_exact(W, v, src, WIN_T)
    for r in (2, 3, 5):
        qc = build_circuit(W, v, src, WIN_T, r=r)
        p = ideal_probs(qc, m)
        fid = float(np.sum(np.sqrt(exact*p))**2)   # fidelidad de Bhattacharyya
        allo_mass = float(sum(p[a] for a in allo))
        depth = qc.decompose().depth()
        print("  Trotter r=%d: fidelidad_vs_exacto=%.3f | masa en bolsillo=%.3f | 2q-depth~%d" % (r, fid, allo_mass, depth))
    # exacto: cuanta masa cae en el bolsillo alosterico
    print("  EXACTO: masa en bolsillo alo=%.3f (de %d nodos)" % (float(sum(exact[a] for a in allo)), m))
