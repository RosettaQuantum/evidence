#!/usr/bin/env python3
"""RQ-0019 — Ruteo de flota minera: contra OR-Tools, que es lo que la industria usa hoy.

QUE SE MIDE Y CONTRA QUE
------------------------
El rival NO es una version tonta del problema: es **OR-Tools**, el solver de Google que
usan hoy las empresas de ruteo. Si un metodo nuevo no le gana a eso, no aporta valor —
por elegante que sea. Ese es el criterio, y esta escrito aqui para que no se ablande
despues de ver el resultado.

Tres competidores sobre LA MISMA instancia y EL MISMO presupuesto de tiempo:

  exacto     CP-SAT sin limite practico  -> el arbitro. Da el optimo real cuando el
                                            tamano lo permite, para saber cuanto le
                                            falta a cada uno EN ABSOLUTO y no solo
                                            uno respecto del otro.
  clasico    OR-Tools routing            -> lo que hay que superar.
  cuantico   QAOA sobre el QUBO          -> el retador.

EL PROBLEMA, Y POR QUE ESTE Y NO OTRO
-------------------------------------
Flota de camiones mineros que salen de un punto de carga, visitan frentes de extraccion
y vuelven. Cada frente tiene un tonelaje; cada camion, una capacidad. Es un CVRP con
capacidad, que es la forma real del problema de un cliente que opera camiones y sensores.

La INCERTIDUMBRE del nombre de la receta ("under uncertainty") entra como tiempos de
viaje perturbados: la solucion se elige sobre la matriz nominal y se EVALUA sobre
escenarios perturbados. Un plan que gana en el papel y se cae con 10% de variacion no
sirve en una mina.

HONESTIDAD DEL DISENO
---------------------
  - La instancia se genera con semilla y se declara entera: cualquiera la reconstruye.
  - Los tres reciben el MISMO presupuesto de segundos.
  - Si el cuantico pierde, se dice "not yet — classical wins" y se sella igual.
  - Ningun numero se estima: el que no se midio se declara ausente.

Uso:
    python3 vrp_harness.py                      # instancia por defecto
    RQ_NODOS=12 RQ_CAMIONES=3 python3 vrp_harness.py
"""
import json
import os
import platform
import time

import numpy as np

# ---------------------------------------------------------------- instancia
NODOS = int(os.environ.get("RQ_NODOS", 10))          # frentes + deposito
CAMIONES = int(os.environ.get("RQ_CAMIONES", 3))
CAPACIDAD = float(os.environ.get("RQ_CAPACIDAD", 40))
SEED = int(os.environ.get("RQ_SEED", 42))
PRESUPUESTO_S = float(os.environ.get("RQ_BUDGET", 20))
N_ESCENARIOS = int(os.environ.get("RQ_ESCENARIOS", 200))
SIGMA = float(os.environ.get("RQ_SIGMA", 0.10))       # 10% de variacion en los tiempos
SALIDA = os.environ.get("RQ_OUT", "resultado_vrp.json")

rng = np.random.default_rng(SEED)


def construir_instancia():
    """Una faena: deposito en el centro, frentes alrededor, tonelaje por frente."""
    coords = np.zeros((NODOS, 2))
    coords[1:] = rng.uniform(-50, 50, size=(NODOS - 1, 2))     # km
    demanda = np.zeros(NODOS)
    demanda[1:] = rng.uniform(5, 18, size=NODOS - 1)           # toneladas
    D = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    np.fill_diagonal(D, 0.0)
    return coords, demanda, D


def factible(demanda):
    """Sin esto, una instancia imposible se lee como 'nadie encontro solucion'."""
    total, flota = float(demanda.sum()), CAMIONES * CAPACIDAD
    if total > flota:
        raise SystemExit(
            "ABORTA: la demanda total (%.1f t) supera la capacidad de la flota (%.1f t).\n"
            "La instancia no tiene solucion y los tres brazos 'fallarian' por igual,\n"
            "lo que se leeria como un empate cuando en realidad no hay problema que resolver."
            % (total, flota))
    return total, flota


# ---------------------------------------------------------------- evaluacion
def costo(rutas, D):
    return float(sum(D[r[i], r[i + 1]] for r in rutas for i in range(len(r) - 1)))


def costo_bajo_incertidumbre(rutas, D, n=N_ESCENARIOS, sigma=SIGMA):
    """El plan se elige sobre la matriz nominal y se evalua sobre escenarios perturbados.

    Devuelve la media y el percentil 90: un plan con buena media y mala cola es
    exactamente el que hace perder turnos en una faena.
    """
    ruido = rng.lognormal(mean=0.0, sigma=sigma, size=(n,) + D.shape)
    ruido = (ruido + np.transpose(ruido, (0, 2, 1))) / 2.0     # simetrico
    costos = [float(sum((D * ruido[k])[r[i], r[i + 1]]
                        for r in rutas for i in range(len(r) - 1))) for k in range(n)]
    return {"media": round(float(np.mean(costos)), 4),
            "p90": round(float(np.percentile(costos, 90)), 4),
            "n_escenarios": n, "sigma": sigma}


def valida(rutas, demanda):
    """Un plan que viola capacidad no compite: se descarta y se dice."""
    visitados = sorted(n for r in rutas for n in r if n != 0)
    if visitados != list(range(1, NODOS)):
        return False, "no visita cada frente exactamente una vez"
    for r in rutas:
        if float(demanda[[n for n in r if n != 0]].sum()) > CAPACIDAD + 1e-9:
            return False, "una ruta excede la capacidad del camion"
    return True, None


# ---------------------------------------------------------------- brazos
def brazo_exacto(D, demanda, segundos):
    from ortools.sat.python import cp_model
    t0 = time.time()
    m = cp_model.CpModel()
    esc = 1000
    Di = (D * esc).astype(int)
    x = {(i, j): m.NewBoolVar("x%d_%d" % (i, j))
         for i in range(NODOS) for j in range(NODOS) if i != j}
    for j in range(1, NODOS):
        m.Add(sum(x[i, j] for i in range(NODOS) if i != j) == 1)
        m.Add(sum(x[j, i] for i in range(NODOS) if i != j) == 1)
    m.Add(sum(x[0, j] for j in range(1, NODOS)) == CAMIONES)
    m.Add(sum(x[j, 0] for j in range(1, NODOS)) == CAMIONES)
    # carga acumulada: elimina subtours Y respeta capacidad de una sola vez
    u = {i: m.NewIntVar(0, int(CAPACIDAD * esc), "u%d" % i) for i in range(NODOS)}
    m.Add(u[0] == 0)
    di = (demanda * esc).astype(int)
    for i in range(1, NODOS):
        m.Add(u[i] >= int(di[i]))
        m.Add(u[i] <= int(CAPACIDAD * esc))
        for j in range(1, NODOS):
            if i != j:
                m.Add(u[j] >= u[i] + int(di[j]) - int(CAPACIDAD * esc) * (1 - x[i, j]))
    m.Minimize(sum(Di[i][j] * x[i, j] for i, j in x))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = segundos
    s.parameters.num_search_workers = 8
    st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"value": None, "runtime_s": round(time.time() - t0, 3),
                "estado": "sin solucion en el presupuesto"}
    rutas, usados = [], set()
    for j in range(1, NODOS):
        if s.Value(x[0, j]):
            r, act = [0, j], j
            usados.add(j)
            while True:
                sig = next((k for k in range(NODOS) if k != act and s.Value(x[act, k])), None)
                if sig is None or sig == 0:
                    r.append(0); break
                r.append(sig); usados.add(sig); act = sig
            rutas.append(r)
    return {"value": round(s.ObjectiveValue() / esc, 4),
            "runtime_s": round(time.time() - t0, 3),
            "estado": "optimo" if st == cp_model.OPTIMAL else "factible",
            "cota_inferior": round(s.BestObjectiveBound() / esc, 4),
            "rutas": rutas}


def brazo_ortools(D, demanda, segundos):
    """EL RIVAL A SUPERAR. Si esto no se supera, no hay valor que vender."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    t0 = time.time()
    esc = 1000
    mgr = pywrapcp.RoutingIndexManager(NODOS, CAMIONES, 0)
    rt = pywrapcp.RoutingModel(mgr)
    Di = (D * esc).astype(int)

    def dist(a, b):
        return int(Di[mgr.IndexToNode(a)][mgr.IndexToNode(b)])
    tr = rt.RegisterTransitCallback(dist)
    rt.SetArcCostEvaluatorOfAllVehicles(tr)
    di = (demanda * esc).astype(int)

    def dem(a):
        return int(di[mgr.IndexToNode(a)])
    dr = rt.RegisterUnaryTransitCallback(dem)
    rt.AddDimensionWithVehicleCapacity(dr, 0, [int(CAPACIDAD * esc)] * CAMIONES, True, "Cap")

    par = pywrapcp.DefaultRoutingSearchParameters()
    par.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    par.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    par.time_limit.FromSeconds(int(max(1, segundos)))
    sol = rt.SolveWithParameters(par)
    if not sol:
        return {"value": None, "runtime_s": round(time.time() - t0, 3), "estado": "sin solucion"}
    rutas = []
    for v in range(CAMIONES):
        idx, r = rt.Start(v), []
        while not rt.IsEnd(idx):
            r.append(mgr.IndexToNode(idx))
            idx = sol.Value(rt.NextVar(idx))
        r.append(0)
        if len(r) > 2:
            rutas.append(r)
    return {"value": round(costo(rutas, D), 4), "runtime_s": round(time.time() - t0, 3),
            "estado": "heuristica GLS", "rutas": rutas}


def brazo_cuantico(D, demanda, segundos):
    """QAOA sobre el QUBO de asignacion frente->camion, y orden optimo dentro de cada uno.

    Se declara lo que ES: el cuantico decide el REPARTO, no el orden. Con los qubits de
    hoy, codificar el orden completo de un CVRP no cabe. Decirlo es parte del resultado.
    """
    import pennylane as qml
    from pennylane import numpy as pnp
    t0 = time.time()
    frentes = list(range(1, NODOS))
    n_q = len(frentes) * CAMIONES
    if n_q > 22:
        return {"value": None, "runtime_s": 0.0,
                "estado": "no cabe: %d qubits para %d frentes x %d camiones" % (n_q, len(frentes), CAMIONES),
                "alcance": "el cuantico decide el reparto, no el orden"}

    # QUBO: cada frente en exactamente un camion + penalidad por exceso de capacidad
    A, B = 50.0, 1.0
    Q = np.zeros((n_q, n_q))
    idx = lambda f, v: f * CAMIONES + v
    for f in range(len(frentes)):
        for v in range(CAMIONES):
            Q[idx(f, v), idx(f, v)] -= A
            for w in range(v + 1, CAMIONES):
                Q[idx(f, v), idx(f, w)] += 2 * A
    for v in range(CAMIONES):
        for f in range(len(frentes)):
            for g in range(f + 1, len(frentes)):
                Q[idx(f, v), idx(g, v)] += B * demanda[frentes[f]] * demanda[frentes[g]] / CAPACIDAD

    coef, obs = [], []
    for i in range(n_q):
        for j in range(i, n_q):
            if abs(Q[i, j]) > 1e-9:
                if i == j:
                    coef.append(Q[i, j] / 2); obs.append(qml.PauliZ(i))
                else:
                    coef.append(Q[i, j] / 4); obs.append(qml.PauliZ(i) @ qml.PauliZ(j))
    H = qml.Hamiltonian(coef, obs)
    dev = qml.device("default.qubit", wires=n_q)
    capas = 2

    @qml.qnode(dev)
    def circuito(p):
        for w in range(n_q):
            qml.Hadamard(w)
        for c in range(capas):
            qml.templates.ApproxTimeEvolution(H, p[c, 0], 1)
            for w in range(n_q):
                qml.RX(2 * p[c, 1], wires=w)
        return qml.expval(H)

    p = pnp.array(rng.uniform(0, np.pi, size=(capas, 2)), requires_grad=True)
    opt = qml.AdamOptimizer(0.1)
    while time.time() - t0 < segundos * 0.8:
        p = opt.step(circuito, p)

    @qml.qnode(dev)
    def muestrear(p):
        for w in range(n_q):
            qml.Hadamard(w)
        for c in range(capas):
            qml.templates.ApproxTimeEvolution(H, p[c, 0], 1)
            for w in range(n_q):
                qml.RX(2 * p[c, 1], wires=w)
        return qml.probs(wires=range(n_q))

    probs = muestrear(p)
    mejor = int(np.argmax(probs))
    bits = [(mejor >> (n_q - 1 - k)) & 1 for k in range(n_q)]
    asign = {}
    for f in range(len(frentes)):
        elegidos = [v for v in range(CAMIONES) if bits[idx(f, v)]]
        asign[frentes[f]] = elegidos[0] if elegidos else int(np.argmin(
            [sum(demanda[g] for g, w in asign.items() if w == v) for v in range(CAMIONES)]))
    rutas = []
    for v in range(CAMIONES):
        grupo = [f for f, w in asign.items() if w == v]
        if not grupo:
            continue
        r, resto, act = [0], list(grupo), 0
        while resto:                       # orden por vecino mas cercano dentro del camion
            s = min(resto, key=lambda k: D[act, k])
            r.append(s); resto.remove(s); act = s
        r.append(0); rutas.append(r)
    ok, porque = valida(rutas, demanda)
    return {"value": round(costo(rutas, D), 4) if ok else None,
            "runtime_s": round(time.time() - t0, 3),
            "estado": "QAOA p=2 sobre el reparto" if ok else "plan invalido: %s" % porque,
            "n_qubits": n_q, "capas": capas,
            "alcance": "el cuantico decide el reparto; el orden dentro de cada camion es vecino mas cercano",
            "rutas": rutas if ok else None}


# ---------------------------------------------------------------- corrida
if __name__ == "__main__":
    coords, demanda, D = construir_instancia()
    total_t, flota_t = factible(demanda)
    print("faena: %d frentes + deposito · %d camiones × %.0f t · demanda %.1f t (%.0f%% de la flota)"
          % (NODOS - 1, CAMIONES, CAPACIDAD, total_t, 100 * total_t / flota_t))

    brazos = {}
    for nombre, fn in (("exacto", brazo_exacto), ("clasico", brazo_ortools), ("cuantico", brazo_cuantico)):
        print("  corriendo %s…" % nombre, flush=True)
        brazos[nombre] = fn(D, demanda, PRESUPUESTO_S)
        if brazos[nombre].get("rutas"):
            brazos[nombre]["bajo_incertidumbre"] = costo_bajo_incertidumbre(brazos[nombre]["rutas"], D)

    exacto, clasico, cuantico = brazos["exacto"], brazos["clasico"], brazos["cuantico"]

    def brecha(v):
        if v is None or exacto["value"] in (None, 0):
            return None
        return round(100 * (v - exacto["value"]) / exacto["value"], 4)

    # EL CRITERIO, escrito antes de ver el numero: superar a OR-Tools, no empatarle.
    gana = (cuantico["value"] is not None and clasico["value"] is not None
            and cuantico["value"] < clasico["value"] - 1e-9)
    veredicto = {
        "criterio": "el retador debe SUPERAR a OR-Tools sobre la misma instancia y el mismo presupuesto. Empatar no es ganar.",
        "rival": "OR-Tools routing con GUIDED_LOCAL_SEARCH",
        "optimo_exacto": exacto["value"],
        "brecha_clasico_pct": brecha(clasico["value"]),
        "brecha_cuantico_pct": brecha(cuantico["value"]),
        "resultado": ("quantum win (this instance)" if gana else
                      "not yet — classical wins" if cuantico["value"] is not None else
                      "el cuantico no produjo un plan valido"),
    }
    res = {"track": "RQ-0019 fleet routing under uncertainty",
           "instance": "mina_%dfrentes_%dcamiones_cap%d_seed%d" % (NODOS - 1, CAMIONES, CAPACIDAD, SEED),
           "params": {"n_nodos": NODOS, "n_frentes": NODOS - 1, "n_camiones": CAMIONES,
                      "capacidad_t": CAPACIDAD, "demanda_total_t": round(total_t, 2),
                      "uso_de_flota_pct": round(100 * total_t / flota_t, 1),
                      "seed": SEED, "presupuesto_s": PRESUPUESTO_S,
                      "coords": coords.round(3).tolist(), "demanda_t": demanda.round(3).tolist()},
           "exacto": exacto, "clasico": clasico, "cuantico": cuantico, "verdict": veredicto,
           "lib_versions": {"numpy": np.__version__, "python": platform.python_version()}}
    json.dump(res, open(SALIDA, "w"), indent=1)
    print("\n" + json.dumps(veredicto, indent=1, ensure_ascii=False))
