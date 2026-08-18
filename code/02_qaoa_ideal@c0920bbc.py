"""QAOA para el QUBO de E.ON (K=10). Optimiza gamma/beta en simulador EXACTO (gratis).

Dos implementaciones independientes que tienen que coincidir:
  (a) simulador numpy que aplica exp(-i*gamma*E(x)) usando el ESPECTRO CRUDO del QUBO,
  (b) el circuito de Qiskit construido desde la conversion Ising (h, J) con RZ/RZZ/RX.
Si (a) y (b) coinciden, la conversion Ising esta bien. Si no, no se envia nada.
"""
import json, os, itertools
import numpy as np
from scipy.optimize import minimize

BASE = os.path.abspath("lab-eon-qpu-2026-08-17")
d = json.load(open(os.path.join(BASE, "01_qubo_eon_case118_K10.json")))
K = d["problema"]["K"]; KB = d["problema"]["k_budget"]
Q = np.array(d["qubo"]["Q_upper"]); c_lin = np.array(d["qubo"]["c_lin"]); CONST = d["qubo"]["CONST"]
OPT = d["optimo_exacto"]["valor"]

# ---- energias en el ORDEN DE QISKIT (qubit j = bit j, LSB) -----------------------
N = 2 ** K
bits = ((np.arange(N)[:, None] >> np.arange(K)[None, :]) & 1).astype(float)   # bits[n, j] = x_j
E = np.einsum("nj,jk,nk->n", bits, Q, bits) + bits @ c_lin + CONST
card = bits.sum(1).astype(int)

# control cruzado contra el espectro guardado (que esta en orden big-endian x0..x9)
esp = np.array(d["espectro_crudo"]["valores"])
idx_be = (bits @ (2 ** np.arange(K)[::-1])).astype(int)   # indice big-endian: x_0 es el MSB
assert np.allclose(E, esp[idx_be], atol=1e-6), "el espectro recomputado no calza con el guardado"
assert abs(E.min() - OPT) < 1e-6

# ---- conversion Ising: E = const + sum h_i z_i + sum_{i<j} J_ij z_i z_j ----------
lin = np.diag(Q) + c_lin                      # x_i^2 = x_i
h = np.zeros(K); J = np.zeros((K, K))
const = CONST + lin.sum() / 2.0
for i in range(K):
    h[i] -= lin[i] / 2.0
    for j in range(i + 1, K):
        const += Q[i, j] / 4.0
        h[i] -= Q[i, j] / 4.0
        h[j] -= Q[i, j] / 4.0
        J[i, j] = Q[i, j] / 4.0
z = 1.0 - 2.0 * bits                          # z_j = 1-2x_j
E_ising = const + z @ h + np.einsum("ni,ij,nj->n", z, J, z)
assert np.allclose(E, E_ising, atol=1e-6), "la conversion Ising no reproduce el QUBO"
assert abs(const - E.mean()) < 1e-6           # el termino constante es la media del espectro
Ec = E - const                                # lo que el circuito implementa (fase global aparte)

# ---- (a) simulador numpy ---------------------------------------------------------
def sim_np(params, p):
    g = params[:p]; b = params[p:]
    psi = np.full(N, 1.0 / np.sqrt(N), dtype=complex)
    for l in range(p):
        psi = psi * np.exp(-1j * g[l] * Ec)
        cb, sb = np.cos(b[l]), -1j * np.sin(b[l])          # RX(2b) = exp(-i b X)
        for q in range(K):
            psi = psi.reshape(-1, 2, 2 ** q)
            a0, a1 = psi[:, 0, :].copy(), psi[:, 1, :].copy()
            psi[:, 0, :] = cb * a0 + sb * a1
            psi[:, 1, :] = sb * a0 + cb * a1
            psi = psi.reshape(-1)
    return psi

def valor_esperado(params, p):
    pr = np.abs(sim_np(params, p)) ** 2
    return float(pr @ E)

# ---- optimizacion multi-arranque determinista ------------------------------------
rng = np.random.default_rng(42)
res = {}
for p in (1, 2):
    mejor = None
    for _ in range(60):
        g0 = rng.uniform(-1, 1, p) * 10 ** rng.uniform(-4, -2.3, p)
        b0 = rng.uniform(0, np.pi, p)
        x0 = np.concatenate([g0, b0])
        r = minimize(valor_esperado, x0, args=(p,), method="Nelder-Mead",
                     options={"maxiter": 4000, "xatol": 1e-10, "fatol": 1e-8})
        if mejor is None or r.fun < mejor.fun:
            mejor = r
    pr = np.abs(sim_np(mejor.x, p)) ** 2
    val = pr[card == KB].sum()
    i_best_valid = int(np.argmax(np.where(card == KB, pr, 0)))
    res[p] = {"params": mejor.x.tolist(), "gamma": mejor.x[:p].tolist(), "beta": mejor.x[p:].tolist(),
              "valor_esperado": float(pr @ E), "frac_valida_ideal": float(val),
              "p_optimo_exacto": float(pr[int(np.argmin(E))]),
              "top_valida_ideal": {"indice": i_best_valid, "prob": float(pr[i_best_valid])},
              "probs": pr}
    print("p=%d  <C>=%.3f  frac_valida_ideal=%.4f  P(optimo)=%.5f  gamma=%s beta=%s"
          % (p, pr @ E, val, pr[int(np.argmin(E))],
             np.round(mejor.x[:p], 6).tolist(), np.round(mejor.x[p:], 4).tolist()))

print("referencia: muestreo uniforme -> frac_valida = %.4f, <C> = %.1f" % ((card == KB).mean(), E.mean()))

# ---- (b) circuito de Qiskit y control cruzado -------------------------------------
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

def circuito(params, p, con_medicion=True):
    g = params[:p]; b = params[p:]
    qc = QuantumCircuit(K, K)
    qc.h(range(K))
    for l in range(p):
        for i in range(K):
            if abs(h[i]) > 1e-12:
                qc.rz(2 * g[l] * h[i], i)
        for i in range(K):
            for j in range(i + 1, K):
                if abs(J[i, j]) > 1e-12:
                    qc.rzz(2 * g[l] * J[i, j], i, j)
        for i in range(K):
            qc.rx(2 * b[l], i)
    if con_medicion:
        qc.measure(range(K), range(K))
    return qc

for p in (1, 2):
    qc = circuito(res[p]["params"], p, con_medicion=False)
    pr_qk = np.abs(np.asarray(Statevector(qc).data)) ** 2
    tvd = 0.5 * np.abs(pr_qk - res[p]["probs"]).sum()
    print("p=%d  TVD(numpy, qiskit) = %.3e   compuertas 2q logicas = %d"
          % (p, tvd, sum(1 for inst in circuito(res[p]['params'], p).data if inst.operation.name == 'rzz')))
    assert tvd < 1e-9, "las dos implementaciones NO coinciden: no se envia nada"
    res[p]["tvd_numpy_vs_qiskit"] = float(tvd)

salida = {"ising": {"h": h.tolist(), "J": J.tolist(), "const": float(const)},
          "optimo_exacto": OPT, "k_budget": KB,
          "frac_valida_uniforme": float((card == KB).mean()),
          "resultados": {str(p): {k: v for k, v in res[p].items() if k != "probs"} for p in res}}
for p in res:
    np.save(os.path.join(BASE, "02_probs_ideal_p%d.npy" % p), res[p]["probs"])
json.dump(salida, open(os.path.join(BASE, "02_qaoa_ideal.json"), "w"), indent=1)
print("escrito 02_qaoa_ideal.json + probs ideales por p")
