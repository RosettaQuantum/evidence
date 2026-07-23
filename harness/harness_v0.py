"""
RosettaQ harness v0 — protocolo Juez v1.
Fight: QAOA (PennyLane, simulador CPU) vs CP-SAT (OR-Tools) sobre la MISMA
instancia QUBO de optimizacion de portafolio, con semilla fija y el optimo
exacto (fuerza bruta) como arbitro de calidad.

Regla Juez v1: misma instancia + mismo presupuesto de tiempo para ambos lados.
Todo queda registrado: semilla, versiones, tiempos, calidad vs optimo exacto.
"""
import json, time, itertools, platform, sys
import numpy as np

SEED = 42
N_ASSETS = 12          # 12 qubits — escala pequena, honesta, para harness v0
K_TARGET = 5           # cardinalidad objetivo del portafolio
RISK_AVERSION = 2.0
PENALTY = 4.0          # penalidad por violar cardinalidad
TIME_BUDGET_S = 120.0  # mismo presupuesto para ambos lados
QAOA_LAYERS = 2
QAOA_STEPS = 120
QAOA_SHOTS = 2000

rng = np.random.default_rng(SEED)

# ---------- 1. Instancia (generada con semilla fija) ----------
mu = rng.uniform(0.02, 0.15, N_ASSETS)                  # retornos esperados
A = rng.normal(0, 1, (N_ASSETS, N_ASSETS))
Sigma = (A @ A.T) / N_ASSETS * 0.05                     # covarianza PSD

# QUBO: min x'Qx + c'x  (riesgo - retorno + penalidad cardinalidad)
# objetivo = risk_aversion * x'Sigma x - mu'x + PENALTY*(sum x - K)^2
Q = RISK_AVERSION * Sigma + PENALTY * np.ones((N_ASSETS, N_ASSETS))
np.fill_diagonal(Q, np.diag(RISK_AVERSION * Sigma) + PENALTY * (1 - 2 * K_TARGET))
c = -mu
CONST = PENALTY * K_TARGET ** 2

def qubo_value(x):
    x = np.asarray(x, dtype=float)
    return float(x @ Q @ x + c @ x + CONST)

# ---------- 2. Optimo exacto (fuerza bruta 2^12 — el arbitro) ----------
t0 = time.time()
best_val, best_x = None, None
for bits in itertools.product([0, 1], repeat=N_ASSETS):
    v = qubo_value(bits)
    if best_val is None or v < best_val:
        best_val, best_x = v, bits
exact = {"value": best_val, "x": list(best_x), "runtime_s": round(time.time() - t0, 3)}

# ---------- 3. Lado clasico: OR-Tools CP-SAT (el campeon) ----------
from ortools.sat.python import cp_model
SCALE = 10**6
t0 = time.time()
m = cp_model.CpModel()
xs = [m.NewBoolVar(f"x{i}") for i in range(N_ASSETS)]
terms = []
for i in range(N_ASSETS):
    terms.append((int(round((Q[i][i] + c[i]) * SCALE)), xs[i]))
prod_vars = {}
for i in range(N_ASSETS):
    for j in range(i + 1, N_ASSETS):
        coef = int(round((Q[i][j] + Q[j][i]) * SCALE))
        if coef != 0:
            p = m.NewBoolVar(f"p{i}_{j}")
            m.AddMultiplicationEquality(p, [xs[i], xs[j]])
            prod_vars[(i, j)] = (coef, p)
obj = sum(co * v for co, v in terms) + sum(co * p for co, p in prod_vars.values())
m.Minimize(obj)
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = TIME_BUDGET_S
solver.parameters.random_seed = SEED
status = solver.Solve(m)
cls_x = [int(solver.Value(v)) for v in xs]
classical = {
    "solver": "OR-Tools CP-SAT",
    "status": solver.StatusName(status),
    "value": qubo_value(cls_x),
    "x": cls_x,
    "runtime_s": round(time.time() - t0, 3),
}

# ---------- 4. Lado cuantico: QAOA (PennyLane, simulador CPU) ----------
import pennylane as qml
from pennylane import numpy as pnp

# QUBO -> Ising: x_i = (1 - z_i)/2
J = np.zeros((N_ASSETS, N_ASSETS))
h = np.zeros(N_ASSETS)
offset = CONST
Qs = (Q + Q.T) / 2
for i in range(N_ASSETS):
    offset += Qs[i][i] / 2 + c[i] / 2
    h[i] -= Qs[i][i] / 2 + c[i] / 2
    for j in range(N_ASSETS):
        if i != j:
            offset += Qs[i][j] / 4
            h[i] -= Qs[i][j] / 4
            J[i][j] += Qs[i][j] / 4

coeffs, ops = [], []
for i in range(N_ASSETS):
    if abs(h[i]) > 1e-12:
        coeffs.append(h[i]); ops.append(qml.PauliZ(i))
for i in range(N_ASSETS):
    for j in range(i + 1, N_ASSETS):
        cij = J[i][j] + J[j][i]
        if abs(cij) > 1e-12:
            coeffs.append(cij); ops.append(qml.PauliZ(i) @ qml.PauliZ(j))
H_cost = qml.Hamiltonian(coeffs, ops)

dev = qml.device("default.qubit", wires=N_ASSETS)

def circuit(params):
    for w in range(N_ASSETS):
        qml.Hadamard(wires=w)
    for layer in range(QAOA_LAYERS):
        qml.templates.ApproxTimeEvolution(H_cost, params[0][layer], 1)
        for w in range(N_ASSETS):
            qml.RX(2 * params[1][layer], wires=w)

@qml.qnode(dev)
def cost_fn(params):
    circuit(params)
    return qml.expval(H_cost)

@qml.qnode(dev)
def sample_fn(params):
    circuit(params)
    return qml.sample(wires=range(N_ASSETS))

t0 = time.time()
pnp.random.seed(SEED)
params = pnp.array(0.01 * pnp.random.rand(2, QAOA_LAYERS), requires_grad=True)
opt = qml.AdamOptimizer(stepsize=0.05)
steps_done = 0
for s in range(QAOA_STEPS):
    if time.time() - t0 > TIME_BUDGET_S * 0.8:
        break
    params = opt.step(cost_fn, params)
    steps_done = s + 1

# muestreo final dentro del presupuesto
dev_s = qml.device("default.qubit", wires=N_ASSETS, shots=QAOA_SHOTS, seed=SEED)
@qml.qnode(dev_s)
def sample_shots(params):
    circuit(params)
    return qml.sample(wires=range(N_ASSETS))

samples = np.array(sample_shots(params))
vals = [qubo_value(sample) for sample in samples]
qi = int(np.argmin(vals))
q_x = [int(b) for b in samples[qi]]
quantum = {
    "framework": f"PennyLane",
    "backend": "default.qubit (CPU sim)",
    "layers": QAOA_LAYERS,
    "optimizer": f"Adam, {steps_done} steps",
    "shots": QAOA_SHOTS,
    "value": qubo_value(q_x),
    "x": q_x,
    "runtime_s": round(time.time() - t0, 3),
}

# ---------- 5. Veredicto del Juez ----------
def gap(v):  # % sobre el optimo exacto (0 = optimo)
    denom = abs(exact["value"]) if abs(exact["value"]) > 1e-9 else 1.0
    return round(100.0 * (v - exact["value"]) / denom, 4)

verdict = {
    "protocol": "juez-v1: misma instancia + mismo presupuesto ambos lados; optimo exacto como arbitro",
    "exact_optimum": exact["value"],
    "classical_gap_pct": gap(classical["value"]),
    "quantum_gap_pct": gap(quantum["value"]),
    "outcome": None,
}
if quantum["value"] < classical["value"]:
    verdict["outcome"] = "quantum win (this instance/scale)"
elif quantum["value"] > classical["value"]:
    verdict["outcome"] = "not yet — classical wins"
else:
    verdict["outcome"] = "tie on quality" + (" — classical faster" if classical["runtime_s"] < quantum["runtime_s"] else " — quantum faster")

result = {
    "instance": f"portfolio_{N_ASSETS}_assets_seed{SEED}",
    "params": {"n_assets": N_ASSETS, "k_target": K_TARGET, "risk_aversion": RISK_AVERSION,
               "penalty": PENALTY, "seed": SEED, "time_budget_s": TIME_BUDGET_S},
    "exact": exact, "classical": classical, "quantum": quantum, "verdict": verdict,
    "lib_versions": {"pennylane": qml.__version__, "numpy": np.__version__,
                     "python": platform.python_version()},
}
from ortools.init.python import init as _oi
try:
    import ortools
    result["lib_versions"]["ortools"] = ortools.__version__ if hasattr(ortools, "__version__") else "9.x"
except Exception:
    pass

with open("/home/claude/rosettaq/runs/result_EXP-0012-001.json", "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result["verdict"], indent=2))
print("classical:", classical["value"], classical["runtime_s"], "s |",
      "quantum:", quantum["value"], quantum["runtime_s"], "s |",
      "exact:", exact["value"])
