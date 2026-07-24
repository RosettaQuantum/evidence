"""
RosettaQ harness — track E.ON (grid expansion / network congestion relief).
Protocolo Juez v1 aplicado a la clase de problema del challenge.

Formulacion (variante binaria de line-additions, ref [4] del brief E.ON):
  - Red IEEE de distribucion, estresada hasta generar congestion real.
  - K lineas candidatas (build/no-build). x_i in {0,1}.
  - Objetivo: MINIMIZAR  congestion_remanente(S) + lambda * costo_build(S)
    donde el alivio de congestion se modela con expansion de 2do orden
    medida con FLUJO DE POTENCIA DC REAL (pandapower):
      relief(S) = sum_i r_i x_i + sum_{i<j} q_ij x_i x_j
      r_i  = alivio construyendo solo i           (medido)
      q_ij = relief(i,j) - r_i - r_j (interaccion) (medido)
  - QUBO exacto => tres contendores: optimo exacto (arbitro), CP-SAT, QAOA.
  - El set ganador se VALIDA en flujo AC completo (honestidad: el modelo es
    2do-orden DC; reportamos el error vs fisica real).
"""
import os, json, time, itertools, platform
import numpy as np
import pandapower as pp
import pandapower.networks as nw

SEED = int(os.environ.get("RQ_SEED", 42))
LOAD_SCALE = float(os.environ.get("RQ_LOADSCALE", 2.6))   # estres para inducir congestion
K_BUDGET = int(os.environ.get("RQ_BUDGET", 5))            # lineas a construir (cardinalidad objetivo)
LAMBDA_COST = float(os.environ.get("RQ_LAMBDA", 0.02))    # peso del costo de build
TIME_BUDGET_S = 120.0
QAOA_LAYERS = 2
QAOA_STEPS = 120
QAOA_SHOTS = 2000
rng = np.random.default_rng(SEED)

TIGHTEN = float(os.environ.get("RQ_TIGHTEN", 0.5))   # feeder sub-dimensionado: ratings apretados
_RATINGS = None   # se fija una vez desde el caso base estresado (mismo para todas las variantes)

def build_base():
    net = nw.case14()
    net.load["p_mw"] *= LOAD_SCALE
    net.load["q_mvar"] *= LOAD_SCALE
    global _RATINGS
    if _RATINGS is None:
        pp.rundcpp(net)
        _RATINGS = net.res_line.i_ka.values * TIGHTEN
    net.line["max_i_ka"] = _RATINGS
    return net

def total_congestion(net):
    """suma de sobrecarga (loading% por encima de 100) en todas las lineas, via DC."""
    try:
        pp.rundcpp(net)
    except Exception:
        return 1e6
    over = np.maximum(net.res_line.loading_percent.values - 100.0, 0.0)
    return float(over.sum())

# --- candidatos: refuerzos paralelos de los corredores mas cargados + algunas lineas nuevas ---
base = build_base()
pp.rundcpp(base)
load_pct = base.res_line.loading_percent.values
C0 = total_congestion(base)
# corredores mas cargados -> refuerzo paralelo (duplicar linea)
order = np.argsort(-load_pct)
cand = []  # cada candidato: ("parallel", line_idx) o ("new", from_bus, to_bus)
for li in order[:10]:
    cand.append(("parallel", int(li)))
# nuevas lineas entre buses no adyacentes (elegidas con semilla, plausibles)
buses = list(base.bus.index)
existing = set(tuple(sorted((int(r.from_bus), int(r.to_bus)))) for _, r in base.line.iterrows())
tries = 0
while len([c for c in cand if c[0]=="new"]) < 4 and tries < 200:
    a, b = rng.choice(buses, 2, replace=False)
    key = tuple(sorted((int(a), int(b))))
    if key not in existing and a != b:
        cand.append(("new", int(a), int(b))); existing.add(key)
    tries += 1
K = len(cand)

def apply_candidate(net, c):
    if c[0] == "parallel":
        li = c[1]; ln = base.line.loc[li]
        pp.create_line_from_parameters(net, int(ln.from_bus), int(ln.to_bus), length_km=float(ln.length_km or 1.0),
            r_ohm_per_km=float(ln.r_ohm_per_km), x_ohm_per_km=float(ln.x_ohm_per_km),
            c_nf_per_km=float(ln.c_nf_per_km or 0.0), max_i_ka=float(ln.max_i_ka or 1.0))
    else:
        ref = base.line.iloc[0]
        pp.create_line_from_parameters(net, c[1], c[2], length_km=2.0,
            r_ohm_per_km=float(ref.r_ohm_per_km), x_ohm_per_km=float(ref.x_ohm_per_km),
            c_nf_per_km=0.0, max_i_ka=float(ref.max_i_ka or 1.0))

def congestion_with(sel):
    net = build_base()
    for i in sel: apply_candidate(net, cand[i])
    return total_congestion(net)

# medir r_i (alivio individual) y q_ij (interaccion) con DC real
t_measure = time.time()
relief_i = np.zeros(K)
for i in range(K):
    relief_i[i] = C0 - congestion_with([i])
q_ij = {}
for i in range(K):
    for j in range(i+1, K):
        rij = C0 - congestion_with([i, j])
        q_ij[(i, j)] = rij - relief_i[i] - relief_i[j]
measure_s = round(time.time() - t_measure, 2)

# costo de build (parallel mas barato que new; con ruido por semilla)
cost = np.array([1.0 if c[0]=="parallel" else 1.8 for c in cand]) * rng.uniform(0.9, 1.1, K)

# QUBO: minimizar  -sum r_i x_i - sum q_ij x_i x_j + lambda sum cost_i x_i + penalty*(sum x - K_BUDGET)^2
PEN = max(1.0, relief_i.max()) * 3.0
Q = np.zeros((K, K)); c_lin = np.zeros(K)
for i in range(K):
    c_lin[i] += -relief_i[i] + LAMBDA_COST*cost[i] + PEN*(1 - 2*K_BUDGET)
    Q[i][i] += PEN
    for j in range(i+1, K):
        Q[i][j] += -q_ij[(i,j)] + 2*PEN
CONST = PEN * K_BUDGET**2

def qubo_val(x):
    x = np.asarray(x, float); return float(x @ Q @ x + c_lin @ x + CONST)

# --- 1. optimo exacto (arbitro) ---
t0 = time.time(); best=None; bx=None
for bits in itertools.product([0,1], repeat=K):
    v = qubo_val(bits)
    if best is None or v < best: best, bx = v, bits
exact = {"value": best, "x": list(bx), "runtime_s": round(time.time()-t0,3), "n_selected": int(sum(bx))}

# --- 2. clasico CP-SAT ---
from ortools.sat.python import cp_model
SC = 10**6; t0 = time.time()
m = cp_model.CpModel(); xs=[m.NewBoolVar(f"x{i}") for i in range(K)]
obj=[int(round((Q[i][i]+c_lin[i])*SC))*xs[i] for i in range(K)]
for i in range(K):
    for j in range(i+1,K):
        co=int(round(Q[i][j]*SC))
        if co: p=m.NewBoolVar(f"p{i}_{j}"); m.AddMultiplicationEquality(p,[xs[i],xs[j]]); obj.append(co*p)
m.Minimize(sum(obj)); solver=cp_model.CpSolver()
solver.parameters.max_time_in_seconds=TIME_BUDGET_S; solver.parameters.random_seed=SEED
st=solver.Solve(m); cx=[int(solver.Value(v)) for v in xs]
classical={"solver":"OR-Tools CP-SAT","status":solver.StatusName(st),"value":qubo_val(cx),"x":cx,"runtime_s":round(time.time()-t0,3),"n_selected":int(sum(cx))}

# --- 3. cuantico QAOA ---
import pennylane as qml
from pennylane import numpy as pnp
Qs=(Q+Q.T)/2; J=np.zeros((K,K)); h=np.zeros(K); off=CONST
for i in range(K):
    off+=Qs[i][i]/2+c_lin[i]/2; h[i]-=Qs[i][i]/2+c_lin[i]/2
    for j in range(K):
        if i!=j:
            off+=Qs[i][j]/4; h[i]-=Qs[i][j]/4; J[i][j]+=Qs[i][j]/4
co=[];op=[]
for i in range(K):
    if abs(h[i])>1e-12: co.append(h[i]);op.append(qml.PauliZ(i))
for i in range(K):
    for j in range(i+1,K):
        cij=J[i][j]+J[j][i]
        if abs(cij)>1e-12: co.append(cij);op.append(qml.PauliZ(i)@qml.PauliZ(j))
H=qml.Hamiltonian(co,op); dev=qml.device("default.qubit",wires=K)
def circ(p):
    for w in range(K): qml.Hadamard(wires=w)
    for l in range(QAOA_LAYERS):
        qml.templates.ApproxTimeEvolution(H,p[0][l],1)
        for w in range(K): qml.RX(2*p[1][l],wires=w)
@qml.qnode(dev)
def cost_fn(p): circ(p); return qml.expval(H)
t0=time.time(); pnp.random.seed(SEED)
params=pnp.array(0.01*pnp.random.rand(2,QAOA_LAYERS),requires_grad=True)
opt=qml.AdamOptimizer(0.05); steps=0
for s in range(QAOA_STEPS):
    if time.time()-t0>TIME_BUDGET_S*0.8: break
    params=opt.step(cost_fn,params); steps=s+1
devs=qml.device("default.qubit",wires=K,shots=QAOA_SHOTS,seed=SEED)
@qml.qnode(devs)
def samp(p): circ(p); return qml.sample(wires=range(K))
S=np.array(samp(params)); vals=[qubo_val(s) for s in S]; qi=int(np.argmin(vals))
qx=[int(b) for b in S[qi]]
quantum={"framework":"PennyLane","backend":"default.qubit (CPU sim)","layers":QAOA_LAYERS,
    "optimizer":f"Adam, {steps} steps","shots":QAOA_SHOTS,"value":qubo_val(qx),"x":qx,
    "runtime_s":round(time.time()-t0,3),"n_selected":int(sum(qx))}

# --- validacion en AC real del set ganador (clasico) ---
def ac_validate(sel):
    net=build_base()
    for i in sel: apply_candidate(net, cand[i])
    try:
        pp.runpp(net); over=np.maximum(net.res_line.loading_percent.values-100,0)
        return {"converged":True,"ac_total_overload":round(float(over.sum()),3),"max_loading_pct":round(float(net.res_line.loading_percent.max()),1)}
    except Exception as e:
        return {"converged":False,"error":str(e)[:80]}
sel_c=[i for i,b in enumerate(cx) if b]
ac_base=ac_validate([]); ac_built=ac_validate(sel_c)

def gap(v):
    d=abs(exact["value"]) if abs(exact["value"])>1e-9 else 1.0
    return round(100*(v-exact["value"])/d,4)
verdict={"protocol":"juez-v1: misma instancia + mismo presupuesto ambos lados; optimo exacto DC como arbitro; modelo de congestion 2do-orden DC validado en AC",
    "exact_optimum":exact["value"],"classical_gap_pct":gap(classical["value"]),"quantum_gap_pct":gap(quantum["value"]),
    "outcome":"not yet — classical wins" if quantum["value"]>classical["value"] else ("quantum win (this instance)" if quantum["value"]<classical["value"] else "tie")}

result={"track":"E.ON grid-expansion","instance":f"case14_stress{LOAD_SCALE}_K{K}_seed{SEED}",
    "params":{"grid":"IEEE case14","load_scale":LOAD_SCALE,"n_candidates":K,"k_budget":K_BUDGET,"lambda_cost":LAMBDA_COST,"seed":SEED,"time_budget_s":TIME_BUDGET_S},
    "grid_physics":{"base_congestion_dc":round(C0,3),"congestion_model":"2nd-order DC superposition (measured r_i, q_ij via pandapower rundcpp)","measure_runtime_s":measure_s,
        "candidates":[{"type":c[0],"detail":c[1:] } for c in cand],
        "ac_validation":{"base":ac_base,"classical_build":ac_built,"built_lines":sel_c}},
    "exact":exact,"classical":classical,"quantum":quantum,"verdict":verdict,
    "lib_versions":{"pennylane":qml.__version__,"numpy":np.__version__,"python":platform.python_version(),"pandapower":pp.__version__}}
out=os.environ.get("RQ_OUT","/home/claude/rosettaq/runs/result_eon.json")
json.dump(result,open(out,"w"),indent=2)
print(json.dumps(verdict,indent=1))
print("C0(DC)=",round(C0,2),"| exact sel=",exact["n_selected"],"| classical=",classical["value"],classical["runtime_s"],"s | quantum=",round(quantum["value"],4),quantum["runtime_s"],"s")
print("AC base overload=",ac_base.get("ac_total_overload"),"-> built=",ac_built.get("ac_total_overload"),"(max load% ",ac_built.get("max_loading_pct"),")")
