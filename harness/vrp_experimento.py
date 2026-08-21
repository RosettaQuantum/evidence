#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RQ-0019 — Ruteo de flota minera, PORTADO a `experimento.py`.

QUE ES ESTE ARCHIVO
-------------------
El mismo experimento que `vrp_harness.py`, escrito DECLARANDO en vez de reimplementando.
Se conserva el original tal cual para poder comparar los dos artefactos campo por campo:
si un numero cambia, la plantilla cambio el experimento y no sirve.

LO QUE SE QUEDA AQUI (es el experimento, y solo el experimento)
---------------------------------------------------------------
  - La instancia: una faena con deposito, frentes, tonelajes y capacidad de camion.
  - Los tres brazos: CP-SAT exacto (arbitro), OR-Tools routing (RIVAL), QAOA (retador).
  - Como se evalua una solucion: `costo(rutas, D)` — UNA funcion, la misma para todos.
  - La incertidumbre: escenarios perturbados sobre el plan ya elegido.
  - El criterio, escrito antes de ver un numero.

LO QUE YA NO SE ESCRIBE AQUI (lo pone la plantilla)
---------------------------------------------------
  lectura de entorno · denominador · truncamiento del optimizador · guardia de memoria ·
  censo medido de la instancia · puntaje comun entre brazos · huella del criterio ·
  forma del artefacto con semillas y versiones.

QUE ENCONTRO LA PLANTILLA AL PORTAR ESTE ARCHIVO (2026-08-18)
-------------------------------------------------------------
El guardia de puntaje comun (G6a) grito en la primera corrida, y tenia razon:
`brazo_exacto` reportaba `ObjectiveValue()/1000` —el objetivo ENTERO escalado de
CP-SAT— mientras `brazo_ortools` reportaba `costo(rutas, D)` sobre la matriz de
flotantes. Con LAS MISMAS rutas (278,9027071177935 las dos) el artefacto decia
optimo 278,9 y rival 278,9027, y de ahi salia `brecha_clasico_pct = 0,001 %`.
Esa brecha no es una brecha: es el redondeo a la grilla de enteros.
`barrido_vrp.py` la cita en su encabezado como hallazgo medido.

NO se corrigio aqui, a proposito: corregirla cambiaria los numeros y la comparacion
contra el artefacto de hoy dejaria de significar nada. Se DECLARA con `puntaje_propio`,
el desvio medido entra al artefacto, y la correccion queda como decision aparte.

Uso:
    python3 vrp_experimento.py
    RQ_NODOS=8 RQ_CAMIONES=2 RQ_CAPACIDAD=60 python3 vrp_experimento.py
"""
import time

import numpy as np

from experimento import (Brazo, Censo, Criterio, Experimento, env, truncamiento,
                         versiones_base)

# ---------------------------------------------------------------- LO DECLARADO
NODOS = env("RQ_NODOS", 10, int)              # frentes + deposito
CAMIONES = env("RQ_CAMIONES", 3, int)
CAPACIDAD = env("RQ_CAPACIDAD", 40.0, float)
SEED = env("RQ_SEED", 42, int)
PRESUPUESTO_S = env("RQ_BUDGET", 20.0, float)
N_ESCENARIOS = env("RQ_ESCENARIOS", 200, int)
SIGMA = env("RQ_SIGMA", 0.10, float)
SALIDA = env("RQ_OUT", "resultado_vrp_portado.json", str)
MIN_RAM_GB = env("RQ_MIN_RAM_GB", 1.0, float)
TOPE_QUBITS = env("RQ_TOPE_QUBITS", 22, int)

rng = np.random.default_rng(SEED)
censo = Censo()


# ---------------------------------------------------------------- LA INSTANCIA
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


# ---------------------------------------------------------------- LA EVALUACION
def costo(rutas, D):
    """LA funcion. Todos los brazos se puntuan con esta, y la plantilla lo comprueba."""
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


# ---------------------------------------------------------------- LOS BRAZOS
def brazo_exacto(ctx):
    """EL ARBITRO: CP-SAT sin limite practico. Da el optimo real cuando el tamano lo permite."""
    from ortools.sat.python import cp_model
    D, demanda, segundos = ctx["D"], ctx["demanda"], ctx["segundos"]
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
                "estado": "sin solucion en el presupuesto",
                "motivo_sin_valor": "cortado_por_reloj", "solucion": None}
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
            "rutas": rutas,
            "solucion": rutas,
            # DECLARADO, no corregido: ver el encabezado. El valor que reporta este brazo
            # NO sale de `costo(rutas, D)` sino del objetivo entero de CP-SAT con esc=1000,
            # asi que difiere del puntaje comun por el redondeo de la grilla.
            "puntaje_propio": {
                "que_es": "objetivo entero de CP-SAT con escala esc=1000 (no costo(rutas,D))",
                "tolerancia_rel": 1e-4,
                "por_que": ("cada arco se redondea a milesimas; sobre esta instancia el "
                            "desvio es de ~3e-5 relativo y se publica medido mas abajo, en "
                            "vez de viajar escondido dentro de brecha_clasico_pct")}}


def brazo_ortools(ctx):
    """EL RIVAL A SUPERAR. Si esto no se supera, no hay valor que vender."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    D, demanda, segundos = ctx["D"], ctx["demanda"], ctx["segundos"]
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
        return {"value": None, "runtime_s": round(time.time() - t0, 3),
                "estado": "sin solucion", "motivo_sin_valor": "cortado_por_reloj",
                "solucion": None}
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
            "estado": "heuristica GLS", "rutas": rutas, "solucion": rutas}


def brazo_cuantico(ctx):
    """QAOA sobre el QUBO de asignacion frente->camion, y orden optimo dentro de cada uno.

    Se declara lo que ES: el cuantico decide el REPARTO, no el orden. Con los qubits de
    hoy, codificar el orden completo de un CVRP no cabe. Decirlo es parte del resultado.
    """
    import pennylane as qml
    from pennylane import numpy as pnp
    D, demanda, segundos = ctx["D"], ctx["demanda"], ctx["segundos"]
    t0 = time.time()
    frentes = list(range(1, NODOS))
    n_q = len(frentes) * CAMIONES
    if n_q > TOPE_QUBITS:
        # No corrio: no hay optimizador que truncar, y el motivo se declara.
        return {"value": None, "runtime_s": 0.0,
                "estado": "no cabe: %d qubits para %d frentes x %d camiones"
                          % (n_q, len(frentes), CAMIONES),
                "alcance": "el cuantico decide el reparto, no el orden",
                "motivo_sin_valor": "fuera_de_alcance", "solucion": None}

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
    pasos = 0
    while time.time() - t0 < segundos * 0.8:
        p = opt.step(circuito, p)
        pasos += 1

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
            "rutas": rutas if ok else None,
            "solucion": rutas if ok else None,
            "motivo_sin_valor": None if ok else "sin_solucion_valida",
            # El bucle de arriba NO tiene tope de pasos: se detiene por reloj y punto.
            # Declararlo asi es lo que impide leer una brecha del presupuesto como una
            # brecha del metodo (el defecto del 2026-08-13 en E.ON).
            "truncamiento": truncamiento(pasos_dados=pasos, pasos_de_presupuesto=None,
                                         reloj_s=round(segundos * 0.8, 3),
                                         criterio_de_parada="reloj")}


# ---------------------------------------------------------------- EL CRITERIO
CRITERIO = Criterio(
    texto=("el retador debe SUPERAR a OR-Tools sobre la misma instancia y el mismo "
           "presupuesto. Empatar no es ganar."),
    rival="OR-Tools routing con GUIDED_LOCAL_SEARCH",
    porque_este_rival=("es el solucionador de ruteo que usan hoy las empresas de flota; "
                       "si un metodo nuevo no le gana a esto, no aporta valor por elegante "
                       "que sea"),
    arbitro="CP-SAT sin limite practico: da el optimo real cuando el tamano lo permite",
    sin_arbitro=("si el arbitro no prueba el optimo, no hay brecha absoluta y se reporta "
                 "None; los brazos solo se pueden comparar entre si"),
)


# ---------------------------------------------------------------- LA CORRIDA
if __name__ == "__main__":
    coords, demanda, D = construir_instancia()
    total_t, flota_t = factible(demanda)

    # EL CENSO: MEDIDO sobre lo construido, nunca estampado desde las variables de entorno.
    # El nombre de la instancia se arma con lo medido, que es la mitad del arreglo: en
    # E.ON el nombre venia de un literal y por eso nueve sellos dijeron case14.
    med = censo.medir(
        declarado={"n_nodos": NODOS, "n_frentes": NODOS - 1, "n_camiones": CAMIONES},
        medido={"n_nodos": int(coords.shape[0]),
                "n_frentes": int((demanda > 0).sum()),
                "n_camiones": int(CAMIONES),
                "n_arcos": int(D.shape[0] * (D.shape[0] - 1)),
                "demanda_total_t": round(float(demanda.sum()), 3)})

    print("faena: %d frentes + deposito · %d camiones × %.0f t · demanda %.1f t (%.0f%% de la flota)"
          % (med["n_frentes"], med["n_camiones"], CAPACIDAD, total_t, 100 * total_t / flota_t))

    ctx = {"D": D, "demanda": demanda, "segundos": PRESUPUESTO_S, "coords": coords}

    def despues(nombre, res, ctx):
        """El mismo paso que hacia el bucle del original, en el mismo lugar del orden."""
        if res.get("rutas"):
            res["bajo_incertidumbre"] = costo_bajo_incertidumbre(res["rutas"], ctx["D"])

    def veredicto(res, ctx):
        exacto, clasico, cuantico = res["exacto"], res["clasico"], res["cuantico"]

        def brecha(v):
            if v is None or exacto["value"] in (None, 0):
                return None
            return round(100 * (v - exacto["value"]) / exacto["value"], 4)

        gana = (cuantico["value"] is not None and clasico["value"] is not None
                and cuantico["value"] < clasico["value"] - 1e-9)
        return {
            "criterio": CRITERIO.texto,
            "rival": CRITERIO.rival,
            "optimo_exacto": exacto["value"],
            "brecha_clasico_pct": brecha(clasico["value"]),
            "brecha_cuantico_pct": brecha(cuantico["value"]),
            "resultado": ("quantum win (this instance)" if gana else
                          "not yet — classical wins" if cuantico["value"] is not None else
                          "el cuantico no produjo un plan valido"),
        }

    exp = Experimento(
        track="RQ-0019 fleet routing under uncertainty",
        instancia="mina_%dfrentes_%dcamiones_cap%d_seed%d"
                  % (med["n_frentes"], med["n_camiones"], CAPACIDAD, SEED),
        params={"n_nodos": NODOS, "n_frentes": NODOS - 1, "n_camiones": CAMIONES,
                "capacidad_t": CAPACIDAD, "demanda_total_t": round(total_t, 2),
                "uso_de_flota_pct": round(100 * total_t / flota_t, 1),
                "seed": SEED, "presupuesto_s": PRESUPUESTO_S,
                "coords": coords.round(3).tolist(), "demanda_t": demanda.round(3).tolist()},
        criterio=CRITERIO,
        evaluar=lambda rutas: costo(rutas, D),
        brazos=[Brazo("exacto", "arbitro", brazo_exacto),
                Brazo("clasico", "rival", brazo_ortools),
                Brazo("cuantico", "retador", brazo_cuantico, itera=True)],
        semillas={"instancia_y_brazos": SEED,
                  "nota": "un solo np.random.default_rng(seed) para instancia, escenarios "
                          "y parametros iniciales del QAOA, consumido en ese orden"},
        versiones=versiones_base(),
        censo=censo,
        memoria_minima_gb=MIN_RAM_GB,
        # el artefacto publica los valores con round(...,4): la holgura del guardia de
        # puntaje sale de ahi y no de un numero elegido a ojo.
        decimales_reportados=4,
        despues_de_cada_brazo=despues,
    )

    art = exp.correr(ctx, veredicto=veredicto)
    Experimento.escribir(art, SALIDA)
    import json
    print("\n" + json.dumps(art["verdict"], indent=1, ensure_ascii=False))
    print("\ndenominador: " + json.dumps(art["plantilla"]["denominador"], ensure_ascii=False))
    print("escrito %s" % SALIDA)
