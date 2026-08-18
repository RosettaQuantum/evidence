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
import os, json, time, itertools, platform, hashlib
import numpy as np
import pandapower as pp
import pandapower.networks as nw

SEED = int(os.environ.get("RQ_SEED", 42))
# MEZCLADOR DEL QAOA. "x" = el camino de siempre (Hadamard + RX), byte-identico.
# "xy_dicke" = la variante pre-registrada en RQ-PREREG-EON-DICKE-001: estado inicial de
# Dicke |D^K_k> y mezclador XY en anillo, de modo que TODO disparo cumple la cardinalidad
# por construccion. La decision de NO quitar la penalidad esta en el pre-registro: sobre
# el subespacio de peso k vale exactamente 0, asi que QUBO y arbitros no cambian.
MIXER = os.environ.get("RQ_MIXER") or "x"
if MIXER not in ("x", "xy_dicke"):
    raise SystemExit("RQ_MIXER=%r: los mezcladores son 'x' y 'xy_dicke'" % MIXER)
LOAD_SCALE = float(os.environ.get("RQ_LOADSCALE", 2.6))   # estres para inducir congestion
K_BUDGET = int(os.environ.get("RQ_BUDGET", 5))            # lineas a construir (cardinalidad objetivo)
LAMBDA_COST = float(os.environ.get("RQ_LAMBDA", 0.02))    # peso del costo de build
# EL PRESUPUESTO DEL BRAZO CUANTICO, Y POR QUE AHORA ESCALA
# ----------------------------------------------------------
# Hasta el 2026-08-13 estos cuatro numeros eran constantes. Medido ese dia: con K=20 el
# optimizador alcanzo a dar **6 pasos de 120** antes de que el reloj lo cortara, y con
# K=16 dio 83. Su brecha (4,41 % y 2,44 %) se publico como si midiera al algoritmo, y
# mide nuestro presupuesto: un circuito casi sin optimizar.
#
# Peor todavia, en la misma direccion: las capas estaban fijas en 2 para todo tamaño, o
# sea que a K creciente se le pedia expresar un problema mas grande con la misma
# capacidad de expresion. Las dos cosas empujan la brecha hacia arriba y ninguna es una
# propiedad del metodo.
#
# Ahora los cuatro se pueden fijar por entorno, y el DEFECTO escala con el problema en
# vez de quedarse quieto. El artefacto declara los valores usados, asi que una corrida
# nunca se puede volver a leer sin saber con cuanto presupuesto corrio.
def _env(nombre, defecto, tipo=int):
    """Lee una variable de entorno tratando la CADENA VACIA como ausente.

    GitHub Actions pasa "" —no la ausencia— cuando un input opcional se deja en blanco,
    y `os.environ.get(x, 120)` devuelve "" en ese caso, no 120. Las cuatro corridas del
    2026-08-13T19:37 murieron asi, en 45 segundos y con el mensaje mas inutil posible:
    `invalid literal for int() with base 10: ''`. El defecto se arregla una vez y para
    los cuatro parametros, no solo para el que fallo — los otros tres sobrevivian por un
    valor por defecto puesto en el shell del flujo, que es una red que no se ve y que la
    proxima persona no va a saber que existe.
    """
    v = os.environ.get(nombre, "")
    return tipo(v) if str(v).strip() else defecto


TIME_BUDGET_S = _env("RQ_TIME_BUDGET", 120.0, float)
# Una capa por cada 4 variables, minimo 2: crece con el problema en vez de ignorarlo.
QAOA_LAYERS = _env("RQ_LAYERS", None)        # None = se deriva de K mas abajo
QAOA_STEPS = _env("RQ_STEPS", 120)
QAOA_SHOTS = _env("RQ_SHOTS", 2000)
rng = np.random.default_rng(SEED)

TIGHTEN = float(os.environ.get("RQ_TIGHTEN", 0.5))   # feeder sub-dimensionado: ratings apretados
_RATINGS = None   # se fija una vez desde el caso base estresado (mismo para todas las variantes)

GRID = os.environ.get("RQ_GRID", "case14")
_GRIDFN = getattr(nw, GRID)

# ---------------------------------------------------------------- EL GUARDIA
# POR QUE EXISTE, con nombre y fecha:
# Hasta el 2026-08-13 este archivo cargaba la red desde RQ_GRID y despues estampaba
# dos literales: `instance="case14_..."` y `params.grid="IEEE case14"`. Corriendo
# case118 el sello decia case14, y NADIE se enteraba porque ningun campo registraba
# el tamano real de la red. Nueve sellos salieron asi, y la propuesta de julio
# heredo la afirmacion del NOMBRE DEL ARCHIVO: "medido sobre case14 -> case30 ->
# case118, todas selladas". Las nueve eran case14.
#
# El instrumento no podia registrar lo que decia medir. Por eso el arreglo no es
# cambiar los literales por variables —eso ya seria correcto y seguiria siendo
# indemostrable— sino MEDIR la red cargada y comprobar que calza con la declarada.
_N_BUS = _N_LINE = None      # los llena el censo, y el resultado los estampa


def _censo_de_la_red(net, declarada):
    global _N_BUS, _N_LINE
    n_bus, n_line = int(len(net.bus)), int(len(net.line))
    # La referencia se CARGA, no se recuerda. La primera version de este guardia traia
    # una tabla escrita de memoria —decia que case14 tenia 20 lineas y tiene 15— y como
    # solo comparaba buses, la cifra equivocada nunca gritó. Un guardia con un numero
    # inventado adentro es el guardia del proximo defecto.
    try:
        ref = getattr(nw, declarada)()
        rb, rl = int(len(ref.bus)), int(len(ref.line))
    except AttributeError:
        print("censo: '%s' no es una red del catalogo de pandapower; se mide igual" % declarada)
        rb = rl = None
    if rb is not None and (n_bus, n_line) != (rb, rl):
        raise SystemExit(
            "ABORTA: se declaro %s —que tiene %d buses y %d lineas— pero la red cargada\n"
            "tiene %d y %d. El sello habria dicho una red y medido otra, que es exactamente\n"
            "el defecto que este guardia existe para impedir." % (declarada, rb, rl, n_bus, n_line))
    print("censo de la red: %s -> %d buses, %d lineas" % (declarada, n_bus, n_line))
    _N_BUS, _N_LINE = n_bus, n_line
    return n_bus, n_line


def build_base():
    net = _GRIDFN()
    net.load["p_mw"] *= LOAD_SCALE
    net.load["q_mvar"] *= LOAD_SCALE
    global _RATINGS
    if _RATINGS is None:
        pp.rundcpp(net)
        ik = net.res_line.i_ka.values
        # piso al rating para evitar lineas con flujo ~0 -> carga infinita
        floor = 0.15 * float(np.nanmax(ik))
        _RATINGS = np.maximum(ik, floor) * TIGHTEN
        _censo_de_la_red(net, GRID)
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
# LOS CANDIDATOS ESCALAN CON LA RED, y por que importa (2026-08-13):
# hasta hoy N_PAR=10 y N_NEW=4 eran fijos, asi que K valia 14 en case14 Y en case118.
# Cuatro corridas sobre redes de 14 a 118 buses resolvian EL MISMO problema de 14
# variables binarias: la red crecia y el problema no. Comparar sus tiempos y llamarlo
# escalamiento era medir variacion entre instancias y ponerle otro nombre.
#
# EL TECHO ES DURO Y ES EXPONENCIAL. El simulador usa un qubit por candidato:
#   14 candidatos -> 0,2 MB de vector de estado
#   26            -> 1 GB
#   28            -> 4 GB   (al limite)
#   34            -> 256 GB (imposible en CPU)
# Por eso el tope por defecto es 26: es el ultimo punto donde la curva se puede
# producir en simulacion. Subir de ahi exige hardware real, que cuesta y necesita OK.
# RQ_CAND fija el tamano del problema de decision, EXPLICITAMENTE. Es el parametro
# que faltaba: mi primer intento lo derivaba de fracciones de lineas y el piso minimo
# dominaba en redes chicas — cuatro redes de 14 a 118 buses dieron 8, 8 y 11 candidatos,
# o sea casi el mismo problema otra vez. Para que exista una curva de escalamiento, el
# numero de variables tiene que poder elegirse.
#
# EL TECHO ES EXPONENCIAL Y DOBLE: el simulador usa un qubit por candidato y la fuerza
# bruta es 2^K. 26 candidatos son 1 GB de vector de estado; y medido en CI, 26 no
# termina en 90 minutos. Por eso el tope por defecto es 22: el ultimo que cabe en
# memoria Y en reloj.
_n_lineas = len(base.line)
TOPE_CAND = int(os.environ.get("RQ_TOPE_CAND", 22))
_pedido = int(os.environ.get("RQ_CAND", 0))
if _pedido:
    K_OBJETIVO = min(_pedido, TOPE_CAND, _n_lineas + 6)
    if K_OBJETIVO < _pedido:
        print("candidatos recortados de %d a %d (tope %d, lineas %d)"
              % (_pedido, K_OBJETIVO, TOPE_CAND, _n_lineas))
else:
    K_OBJETIVO = min(TOPE_CAND, max(8, int(round(0.20 * _n_lineas))))
N_NEW = max(2, K_OBJETIVO // 4)                  # 1 de cada 4 es linea nueva
N_PAR = min(K_OBJETIVO - N_NEW, _n_lineas)       # el resto refuerza lo mas cargado

# Las capas del circuito, AHORA derivadas del tamaño del problema. Fijas en 2 producian
# un ansatz con la misma capacidad de expresion para 8 y para 20 variables.
if QAOA_LAYERS is None:
    QAOA_LAYERS = max(2, K_OBJETIVO // 4)
print("[qaoa] capas=%d · pasos=%d · reloj=%.0fs · disparos=%d"
      % (QAOA_LAYERS, QAOA_STEPS, TIME_BUDGET_S, QAOA_SHOTS))
print("candidatos: %d paralelos + %d nuevos = %d sobre una red de %d lineas"
      % (N_PAR, N_NEW, N_PAR + N_NEW, _n_lineas))
order = np.argsort(-load_pct)
cand = []  # cada candidato: ("parallel", line_idx) o ("new", from_bus, to_bus)
for li in order[:N_PAR]:
    cand.append(("parallel", int(li)))
# nuevas lineas entre buses no adyacentes (elegidas con semilla, plausibles)
buses = list(base.bus.index)
existing = set(tuple(sorted((int(r.from_bus), int(r.to_bus)))) for _, r in base.line.iterrows())
tries = 0
while len([c for c in cand if c[0]=="new"]) < N_NEW and tries < 400:
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
# La fuerza bruta es 2^K y muere al mismo tiempo que el simulador. Se conserva como
# CONTROL CRUZADO mientras quepa, y por encima del tope el arbitro pasa a ser el
# `status: OPTIMAL` de CP-SAT — que NO es una heuristica: es una prueba de optimalidad.
# En las cuatro corridas de hoy coincidieron hasta el ultimo decimal, y esa coincidencia
# es la que autoriza a jubilar la fuerza bruta sin perder rigor.
TOPE_FUERZA_BRUTA = int(os.environ.get("RQ_TOPE_FB", 22))
t0 = time.time()
if K <= TOPE_FUERZA_BRUTA:
    best=None; bx=None
    for bits in itertools.product([0,1], repeat=K):
        v = qubo_val(bits)
        if best is None or v < best: best, bx = v, bits
    exact = {"value": best, "x": list(bx), "runtime_s": round(time.time()-t0,3),
             "n_selected": int(sum(bx)), "arbitro": "fuerza bruta 2^%d" % K}
else:
    exact = {"value": None, "x": None, "runtime_s": 0.0, "n_selected": None,
             "arbitro": "no corrida: 2^%d no cabe (tope %d). El arbitro es el OPTIMAL de CP-SAT."
                        % (K, TOPE_FUERZA_BRUTA)}

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
# CONVERSION QUBO -> ISING. Corregida el 2026-08-18; antes perdia un termino.
#
# EL DEFECTO, y lo que costo: el bucle hacia `h[i] -= Qs[i][j]/4` pero NO `h[j] -=`.
# Como recorre los pares ordenados (i,j) y (j,i), el acoplamiento J salia bien —cada
# par lo recibe dos veces— pero el campo lineal `h` quedaba EN LA MITAD: x_j aparece en
# los dos terminos del par y solo se le descontaba uno.
#
# Consecuencia: el brazo cuantico optimizaba una funcion DISTINTA de la que resolvian
# CP-SAT y la fuerza bruta. Los tres brazos deben competir sobre el mismo problema; el
# cuantico competia sobre uno deformado, y eso inflaba `quantum_gap_pct` por una razon
# que no es del metodo. Desvio medido: 24.381 en K=8, 165.857 en K=20.
#
# Comprobado sobre las 64 asignaciones de un QUBO aleatorio de 6 variables: la version
# vieja se desvia hasta 1,303; esta da 0,000000 exacto. El guardia de abajo lo exige en
# cada corrida, sobre la instancia real, para que no vuelva a pasar sin que nadie mire.
#
# Lo encontro el agente que medía redes tensoriales — no era su tarea, y lo declaro.
for i in range(K):
    off+=Qs[i][i]/2+c_lin[i]/2; h[i]-=Qs[i][i]/2+c_lin[i]/2
    for j in range(K):
        if i!=j:
            off+=Qs[i][j]/4; h[i]-=Qs[i][j]/4; h[j]-=Qs[i][j]/4; J[i][j]+=Qs[i][j]/4
# EL GUARDIA DE LA CONVERSION, y se prueba contra el defecto real de arriba.
# Comprueba sobre ESTA instancia que la energia Ising reproduce el QUBO exacto. Es
# barato —unas pocas asignaciones al azar— y habria gritado el primer dia.
_rs = np.random.RandomState(SEED)
_peor = 0.0
for _ in range(24):
    _x = _rs.randint(0, 2, K).astype(float)
    _z = 1.0 - 2.0 * _x
    _E = off + float(h @ _z) + sum(J[a][b] * _z[a] * _z[b]
                                   for a in range(K) for b in range(K) if a != b)
    _peor = max(_peor, abs(_E - qubo_val(_x)))
if _peor > 1e-6:
    raise SystemExit(
        "ABORTA: la conversion QUBO->Ising no reproduce el QUBO (desvio %.6f).\n"
        "  El brazo cuantico estaria optimizando una funcion DISTINTA de la que resuelven\n"
        "  CP-SAT y la fuerza bruta, y su brecha se inflaria por una razon que no es del\n"
        "  metodo. Exactamente el defecto del 2026-08-18." % _peor)
print("[ising] la conversion reproduce el QUBO (desvio maximo %.2e sobre 24 asignaciones)" % _peor)

co=[];op=[]
for i in range(K):
    if abs(h[i])>1e-12: co.append(h[i]);op.append(qml.PauliZ(i))
for i in range(K):
    for j in range(i+1,K):
        cij=J[i][j]+J[j][i]
        if abs(cij)>1e-12: co.append(cij);op.append(qml.PauliZ(i)@qml.PauliZ(j))
H=qml.Hamiltonian(co,op); dev=qml.device("default.qubit",wires=K)
if MIXER == "xy_dicke":
    # El vector de Dicke exacto: uniforme sobre las C(K,k) cadenas de peso k. La fase de
    # esta demo es simulacion; preparar Dicke por circuito es problema de hardware.
    _pesok = [i for i in range(2**K) if bin(i).count("1") == K_BUDGET]
    _dicke = np.zeros(2**K); _dicke[_pesok] = 1.0/np.sqrt(len(_pesok))

def circ(p):
    if MIXER == "xy_dicke":
        qml.StatePrep(_dicke, wires=range(K))
    else:
        for w in range(K): qml.Hadamard(wires=w)
    for l in range(QAOA_LAYERS):
        qml.templates.ApproxTimeEvolution(H,p[0][l],1)
        if MIXER == "xy_dicke":
            # XY en anillo: exp(-i*beta*(XX+YY)) por par (XX y YY del mismo par conmutan).
            # Conserva el peso de Hamming: la dinamica nunca sale del subespacio factible.
            for w in range(K):
                a2, b2 = w, (w+1) % K
                qml.IsingXX(2*p[1][l], wires=[a2, b2])
                qml.IsingYY(2*p[1][l], wires=[a2, b2])
        else:
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

_fv_construccion = None
if MIXER == "xy_dicke":
    # GUARDIA (a) — sobre el vector de estado FINAL, no sobre la intencion del circuito:
    # tras las p capas optimizadas, la masa fuera del subespacio de peso k debe ser ~0.
    # Probar el estado final prueba la preparacion Y el mezclador a la vez.
    _deva = qml.device("default.qubit", wires=K)
    @qml.qnode(_deva)
    def _estado(p):
        circ(p); return qml.state()
    _vec = np.asarray(_estado(params))
    _masa_fuera = float(sum(abs(_vec[i])**2 for i in range(2**K)
                            if bin(i).count("1") != K_BUDGET))
    if _masa_fuera > 1e-9:
        raise SystemExit("ABORTA (guardia a): el estado final tiene masa %.3e fuera del "
                         "subespacio de peso %d. El mezclador NO conserva la cardinalidad "
                         "o la preparacion esta contaminada." % (_masa_fuera, K_BUDGET))
    # GUARDIA (b) — cada muestra de peso k; en simulacion exacta debe ser el 100 %.
    _malas = [i for i, fila in enumerate(S) if int(sum(fila)) != K_BUDGET]
    if _malas:
        raise SystemExit("ABORTA (guardia b): %d de %d muestras NO tienen peso %d (primera: "
                         "fila %d). Un solo disparo infactible desmiente la construccion."
                         % (len(_malas), len(S), K_BUDGET, _malas[0]))
    _fv_construccion = 1.0
    print("[dicke] guardia a: masa fuera del subespacio %.2e | guardia b: %d/%d muestras "
          "de peso %d" % (_masa_fuera, len(S), len(S), K_BUDGET))
# El artefacto declara si el optimizador AGOTO su presupuesto o lo corto el reloj. Sin
# este campo, una brecha grande por falta de tiempo se lee como una brecha grande del
# metodo — que fue exactamente lo que paso con K=16 y K=20 el 2026-08-13.
quantum={"framework":"PennyLane","backend":"default.qubit (CPU sim)","layers":QAOA_LAYERS,
    "mixer":MIXER,
    **({"estado_inicial":"dicke |D^%d_%d>"%(K,K_BUDGET),
        "subespacio_factible":len(_pesok),
        "fraccion_valida_por_construccion":_fv_construccion,
        "prereg":"RQ-PREREG-EON-DICKE-001"} if MIXER=="xy_dicke" else {}),
    "optimizer":f"Adam, {steps} steps","shots":QAOA_SHOTS,
    "pasos_dados":steps,"pasos_de_presupuesto":QAOA_STEPS,
    "reloj_s":TIME_BUDGET_S,
    "truncado_por_reloj":bool(steps < QAOA_STEPS),
    "advertencia":(None if steps >= QAOA_STEPS else
        f"el optimizador dio {steps} de {QAOA_STEPS} pasos: el reloj lo corto. Esta "
        f"brecha mide el presupuesto, no el metodo."),"value":qubo_val(qx),"x":qx,
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

_ref_cpsat = classical["value"] if str(classical.get("status","")).upper().startswith("OPTIMAL") else None

def gap(v):
    ref = exact["value"] if exact["value"] is not None else _ref_cpsat
    if ref is None or v is None:
        return None                    # sin arbitro no hay brecha, y se dice
    d = abs(ref) if abs(ref) > 1e-9 else 1.0
    return round(100*(v-ref)/d, 4)
verdict={"protocol":"juez-v1: misma instancia + mismo presupuesto ambos lados; optimo exacto DC como arbitro; modelo de congestion 2do-orden DC validado en AC",
    "exact_optimum":exact["value"],"arbitro":exact.get("arbitro"),"arbitro_efectivo":("fuerza bruta" if exact["value"] is not None else ("CP-SAT OPTIMAL" if _ref_cpsat is not None else "NINGUNO — la brecha no se puede medir")),"classical_gap_pct":gap(classical["value"]),"quantum_gap_pct":gap(quantum["value"]),
    "outcome":"not yet — classical wins" if quantum["value"]>classical["value"] else ("quantum win (this instance)" if quantum["value"]<classical["value"] else "tie")}

if _N_BUS is None:
    raise SystemExit("ABORTA: el censo de la red nunca corrio, asi que el sello no\n"
                     "puede declarar cuantos buses tenia. Un campo ausente es mejor que\n"
                     "uno inventado, pero un sello a medias no se publica.")

result={"track":"E.ON grid-expansion","instance":f"{GRID}_stress{LOAD_SCALE}_K{K}_seed{SEED}",
    "params":{"grid":f"IEEE {GRID}","n_buses":_N_BUS,"n_lines":_N_LINE,"load_scale":LOAD_SCALE,"n_candidates":K,"k_budget":K_BUDGET,"lambda_cost":LAMBDA_COST,"seed":SEED,"time_budget_s":TIME_BUDGET_S},
    "grid_physics":{"base_congestion_dc":round(C0,3),"congestion_model":"2nd-order DC superposition (measured r_i, q_ij via pandapower rundcpp)","measure_runtime_s":measure_s,
        "candidates":[{"type":c[0],"detail":c[1:] } for c in cand],
        "ac_validation":{"base":ac_base,"classical_build":ac_built,"built_lines":sel_c}},
    "exact":exact,"classical":classical,"quantum":quantum,"verdict":verdict,
    "lib_versions":{"pennylane":qml.__version__,"numpy":np.__version__,"python":platform.python_version(),"pandapower":pp.__version__,
        # El hash del harness que PRODUJO este artefacto, leido del archivo en
        # disco al correr — el que un tercero recomputa con sha256sum. Sin esto,
        # el artefacto no puede probar que codigo lo genero (defecto de julio).
        "harness_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest()}}
out=os.environ.get("RQ_OUT","result_eon.json")
json.dump(result,open(out,"w"),indent=2)
print(json.dumps(verdict,indent=1))
print("C0(DC)=",round(C0,2),"| K=",K,"| arbitro:",verdict.get("arbitro_efectivo"),"| exact sel=",exact["n_selected"],"| classical=",classical["value"],classical["runtime_s"],"s | quantum=",round(quantum["value"],4),quantum["runtime_s"],"s")
print("AC base overload=",ac_base.get("ac_total_overload"),"-> built=",ac_built.get("ac_total_overload"),"(max load% ",ac_built.get("max_loading_pct"),")")
