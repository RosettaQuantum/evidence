"""Envio a IBM Quantum de la PoC de caminata cuantica (CTQW) + medicion de ruido.
Corre el MISMO circuito en tres lugares y compara las distribuciones:
  (1) simulador IDEAL (Aer statevector)        -> la caminata "perfecta"
  (2) simulador con RUIDO (modelo depolarizante) -> preview local, sin gastar QPU
  (3) QPU REAL de IBM (si hay IBM_TOKEN)         -> la maquina de verdad
Metrica: fidelidad de Bhattacharyya entre cada distribucion y la ideal =
RESISTENCIA AL RUIDO. Entregable honesto: cuanto reproduce el hardware la caminata,
y cuanto la degrada el ruido. NO es una afirmacion de ventaja cuantica.

USO:
  # preview local (sin cuenta, no gasta nada):
  python poc_ibm_run.py KRAS_G12C --r 2
  # correr en QPU real (Nicholas, con su cuenta IBM):
  export IBM_TOKEN='<tu API key de quantum.cloud.ibm.com>'
  export IBM_CRN='<CRN de la instancia open>'   # opcional
  python poc_ibm_run.py KRAS_G12C --r 2 --hw ibm_kingston --shots 2000
"""
import os, sys, json, argparse, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poc_ibm as P

def bhattacharyya(p, q):
    p = np.asarray(p, float); q = np.asarray(q, float)
    return float(np.sum(np.sqrt(p*q))**2)

def counts_to_p1(counts, m):
    """De conteos de shots -> P(1) por qubit, restringido al subespacio de 1 excitacion."""
    p1 = np.zeros(m); tot = 0
    for bit, c in counts.items():
        b = bit.replace(" ", "")[::-1]   # qiskit: bit string little-endian
        if b.count("1") == 1:
            p1[b.index("1")] += c; tot += c
    return (p1/tot if tot else p1), tot

def noisy_preview(qc, m, p2=0.005, p1e=0.001):
    """Simulacion local con ruido depolarizante (preview antes de gastar QPU)."""
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error
    from qiskit import transpile
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(p1e, 1), ['rz','sx','x','h'])
    nm.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ['cx','cz','ecr'])
    sim = AerSimulator(noise_model=nm)
    tqc = transpile(qc, sim, basis_gates=['rz','sx','x','cx'], optimization_level=3)
    res = sim.run(tqc, shots=4000).result()
    p1, tot = counts_to_p1(res.get_counts(), m)
    return p1, tqc.depth(), tot/4000.0

def run_hw(qc, m, backend_name, shots):
    """Envia a QPU real via qiskit-ibm-runtime (SamplerV2)."""
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit import transpile
    kw = {"channel": "ibm_quantum_platform", "token": os.environ["IBM_TOKEN"]}
    if os.environ.get("IBM_CRN"): kw["instance"] = os.environ["IBM_CRN"]
    service = QiskitRuntimeService(**kw)
    backend = service.backend(backend_name) if backend_name else service.least_busy(operational=True, simulator=False)
    print("  backend:", backend.name)
    tqc = transpile(qc, backend, optimization_level=3)
    print("  2q-depth transpilado:", tqc.depth())
    sampler = SamplerV2(mode=backend)
    job = sampler.run([tqc], shots=shots)
    print("  job id:", job.job_id())
    res = job.result()[0]
    counts = res.data.c.get_counts()
    p1, tot = counts_to_p1(counts, m)
    return p1, backend.name, job.job_id(), tot/float(shots)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("protein", nargs="?", default="KRAS_G12C")
    ap.add_argument("--r", type=int, default=2)
    ap.add_argument("--hw", default=None, help="nombre del backend IBM (ej. ibm_kingston); vacio = menos ocupado")
    ap.add_argument("--shots", type=int, default=2000)
    a = ap.parse_args()
    d = P.load(a.protein); idx, W, v, roles = P.subgraph(d)
    m = len(idx); allo = set(roles["allo"]); src = [(roles["src"] or [0])[0]]
    exact = P.ctqw_exact(W, v, src, P.WIN_T)
    qc = P.build_circuit(W, v, src, P.WIN_T, r=a.r)
    ideal = P.ideal_probs(qc, m)
    out = {"protein": a.protein, "nodes": m, "trotter_r": a.r, "source": src, "pocket": sorted(allo),
           "exact_pocket_mass": float(sum(exact[a2] for a2 in allo)),
           "ideal_pocket_mass": float(sum(ideal[a2] for a2 in allo)),
           "ideal_vs_exact_fid": bhattacharyya(exact, ideal)}
    print("== PoC %s | %d qubits | Trotter r=%d ==" % (a.protein, m, a.r))
    print("  masa en bolsillo: exacto=%.3f  ideal=%.3f  (fid ideal-vs-exacto=%.3f)" %
          (out["exact_pocket_mass"], out["ideal_pocket_mass"], out["ideal_vs_exact_fid"]))
    # (2) preview con ruido
    noisy, dep, surv = noisy_preview(qc, m)
    out["noisy_pocket_mass"] = float(sum(noisy[a2] for a2 in allo))
    out["noisy_vs_ideal_fid_restringida"] = bhattacharyya(ideal, noisy)
    out["noisy_survival_1exc"] = float(surv)
    out["transpiled_depth"] = int(dep)
    print("  RUIDO (preview local, depol 0.5%%/2q, depth=%d):" % dep)
    print("     supervivencia en subespacio valido = %.2f%%  <- el daño REAL del ruido" % (surv*100))
    print("     (de los que sobreviven) masa_bolsillo=%.3f fid_vs_ideal=%.3f" %
          (out["noisy_pocket_mass"], out["noisy_vs_ideal_fid_restringida"]))
    # (3) QPU real
    if os.environ.get("IBM_TOKEN"):
        try:
            hw, bname, jid, hsurv = run_hw(qc, m, a.hw, a.shots)
            out["hw_backend"] = bname; out["hw_job_id"] = jid
            out["hw_pocket_mass"] = float(sum(hw[a2] for a2 in allo))
            out["hw_vs_ideal_fid_restringida"] = bhattacharyya(ideal, hw)
            out["hw_survival_1exc"] = float(hsurv)
            print("  QPU REAL (%s): supervivencia=%.2f%%  masa=%.3f  fid_vs_ideal=%.3f  <- RESISTENCIA AL RUIDO" %
                  (bname, hsurv*100, out["hw_pocket_mass"], out["hw_vs_ideal_fid_restringida"]))
        except Exception as e:
            print("  QPU: no se pudo correr (%s: %s)" % (type(e).__name__, str(e)[:120]))
    else:
        print("  QPU: fija IBM_TOKEN para correr en hardware real.")
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "poc_result_%s.json" % a.protein), "w"), indent=1)
    print("  guardado poc_result_%s.json" % a.protein)
