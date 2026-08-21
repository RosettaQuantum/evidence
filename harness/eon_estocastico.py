#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E.ON bajo incertidumbre: DONDE el clasico deja de poder PROBAR que su respuesta es optima.

POR QUE EXISTE ESTE ARCHIVO
---------------------------
`eon_harness.py` mide el problema DETERMINISTA: una red, K lineas candidatas, un solo
escenario de demanda. Medido el 2026-08-13: CP-SAT devuelve OPTIMAL en todos los tamanos
probados (hasta K=20, en 9,3 s). En ese problema NO HAY NADA QUE GANAR: el clasico no sufre.

Pero un planificador de red no resuelve un problema determinista. Resuelve el mismo
problema bajo muchos escenarios de demanda y de disponibilidad de generacion. Ahi hay una
asimetria que este archivo existe para MEDIR, no para suponer:

  - El problema CLASICO crece con los escenarios: hay que modelar la operacion de la red
    bajo cada uno, asi que las variables de segunda etapa se multiplican por S.
  - El problema CUANTICO no crece con los escenarios: la primera etapa son K binarias
    haya 10 escenarios o 10.000.

Si la asimetria es real y medible, es la primera razon fisica por la que lo cuantico
podria importar aqui. Si no lo es, hay que saberlo hoy. Las dos respuestas valen.

EL CRITERIO, ESCRITO ANTES DE VER UN SOLO NUMERO
------------------------------------------------
**La frontera es el par (K, S) mas chico donde el solucionador NO prueba optimalidad
dentro de 900 segundos.** Los 900 s son ELECCION NUESTRA —el presupuesto operativo que un
planificador tolera—, no una constante natural. Queda declarado aqui y en cada fila del CSV.

Se registra por corrida el `status` EXACTO, el tiempo real, el valor de la mejor solucion y
la COTA, para poder calcular la brecha de optimalidad cuando NO haya prueba. Un FEASIBLE
sin cota no dice nada; con cota dice cuanto le faltaba.

LOS DOS SOLUCIONADORES, Y POR QUE SON DOS
-----------------------------------------
El encargo fija CP-SAT, que es lo que usa el harness determinista. Pero alli CP-SAT resuelve
un QUBO —puras binarias, su terreno—, y aqui la segunda etapa es un despacho CONTINUO:
angulos, flujos, deslastre. **CP-SAT no tiene variables continuas.** Meterlo igual obliga a
discretizar, y una frontera producida por el redondeo mediria nuestra discretizacion y no
el problema — la sexta variante de CLAUDE.md §5 quater: un numero correcto respondiendo otra
pregunta.

Por eso se miden LOS DOS en cada punto:
  - `cpsat`  : la version entera discretizada (el criterio declarado).
  - `milp`   : el mismo modelo con recurso continuo, en SCIP (y HiGHS de contraste).
Si CP-SAT se cae donde el MILP prueba, la frontera es de la herramienta y se dice asi.

QUE MODELO ES (declarado, porque decide como leer el resultado)
--------------------------------------------------------------
Segunda etapa = **flujo DC con angulos**, o sea CON la ley de voltajes de Kirchhoff:
  f_l = B_l (theta_u - theta_v),  balance nodal,  |f_l| <= cap_l + sobrecarga_l
con redespacho de generacion y deslastre de carga como recurso.

La primera version de este archivo uso el modelo de TRANSPORTE (solo balance nodal, sin
KVL). Es la relajacion estandar en la literatura de expansion de transmision y su version
entera es exacta — muy comodo. Y estaba MAL para lo que hay que medir: su plan optimo,
evaluado con el flujo DC del propio harness, bajaba la congestion de 7174,8 a 7095,9
(un 1,1%) mientras el plan del determinista la bajaba a 6017,4 (un 16%). Sin KVL, la
potencia se "rutea" a gusto y construir una linea vale lo mismo en cualquier parte. El
numero era correcto y respondia otra pregunta. Queda escrito porque el defecto costo una
vuelta entera y se detecto SOLO porque la prueba 1 lo cruzo contra el harness.

EL BRAZO CUANTICO (2026-08-17)
------------------------------
Hasta esa fecha aqui solo corria el lado clasico: la frontera esta medida y el brazo cuantico
nunca se cableo. Ahora esta, y la pregunta que contesta es una sola: **¿el plan de primera
etapa que produce el brazo cuantico es mejor que el que SCIP alcanza sin poder demostrarlo,
en el mismo presupuesto de tiempo?** El bloque grande de mas abajo explica el diseño; lo que
importa desde aqui es que los dos planes se evaluan con LA MISMA funcion de costo exacta.

Uso:
    python3 eon_estocastico.py --pruebas          # las cuatro pruebas de aceptacion (clasico)
    python3 eon_estocastico.py --barrido          # el barrido (acumula en el CSV)
    python3 eon_estocastico.py --informe K S      # un solo punto, modo informe
    python3 eon_estocastico.py --ensayo           # corrida de ensayo chica, antes de gastar
    python3 eon_estocastico.py --pruebas-q        # pruebas Q1 (el QUBO) y Q3 (los escenarios)
    python3 eon_estocastico.py --cuantico K S     # la corrida: cuantico vs SCIP (+ prueba Q2)
    python3 eon_estocastico.py --arbitro K S      # el optimo REAL, por enumeracion de C(K,k)
"""
import argparse
import csv
import json
import math
import os
import platform
import time
import types
from fractions import Fraction
from itertools import combinations

import numpy as np

RUTA_HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eon_harness.py")

# --------------------------------------------------------------------------- PARAMETROS
GRID = os.environ.get("RQ_GRID", "case118")
SEMILLA = int(os.environ.get("RQ_SEED", 42))
K_BUDGET = int(os.environ.get("RQ_BUDGET", 5))     # se construyen exactamente 5, como el determinista
RELOJ_S = float(os.environ.get("RQ_RELOJ", 900))   # 900 s = 15 min: ELECCION NUESTRA
HILOS = int(os.environ.get("RQ_HILOS", 8))

# Costos del objetivo, en MW. Declarados: no salen de ningun estudio, son la ponderacion
# que elegimos y con la que hay que leer todo lo demas.
C_OV = 1.0        # por MW de sobrecarga remanente
VOLL = 20.0       # por MW de energia no servida: 20x la sobrecarga
W_BUILD = 10.0    # por unidad de `cost` del harness (cost_i ~ 1,0 paralelo / ~1,9 nueva)

# La distribucion de los escenarios, DECLARADA (no "realista" sin decir cual):
#   carga por bus:      mult ~ Normal(1, SIGMA_CARGA), recortada a [1-3s, 1+3s]
#   disponibilidad gen: 1.0 con prob (1-P_FALLA_GEN); si no, Uniform(0, FALLA_MAX)
# El recorte a 3 sigma es explicito para que ningun escenario tenga carga negativa.
SIGMA_CARGA = 0.15
P_FALLA_GEN = 0.15
FALLA_MAX = 0.5
# El escenario 0 es SIEMPRE el nominal (mult=1, avail=1): sin eso, "S=1" seria un escenario
# al azar y no seria comparable con el determinista. Cada escenario s se sortea con su
# propia semilla derivada SeedSequence([SEMILLA, s]), asi el escenario 7 es EL MISMO con
# S=20 y con S=500 — los puntos del barrido son anidados y comparables entre si.

# Cota de los angulos, en radianes. NO es decorativa: con 2.0 el modo sin-recurso salio
# INFEASIBLE, porque la solucion DC del propio harness llega a |theta| = 2,9966 rad (la red
# esta estresada a 2,6x y el desfase es grande). El guardia de abajo compara la cota contra
# el maximo MEDIDO en la corrida base y aborta si no hay holgura: una cota apretada no
# produce un resultado peor, produce un infactible que se leeria como "el modelo esta mal".
THETA_MAX = 10.0

# Discretizacion del brazo CP-SAT (el criterio declarado del encargo).
CP_DTHETA = 1e-4      # radianes por unidad entera de angulo
CP_MW = 0.1           # MW por unidad entera de potencia
CP_TOL_U = 2          # holgura, en unidades de potencia, de la ecuacion f = B*dtheta.
# POR QUE HAY HOLGURA: sobre una grilla entera, `den*f == num*dtheta` exacto impone
# divisibilidad y deja el modelo infactible o deformado. La banda +-CP_TOL_U (0,2 MW) es
# una decision declarada, y la prueba 4 comprueba que no cambia el optimo.

MARCA_DATOS = "# QUBO: minimizar"             # hasta aqui: red, censo, candidatos, costos
MARCA_EXACTO = "# --- 3. cuantico QAOA ---"   # hasta aqui: + optimo exacto y CP-SAT del QUBO

_CACHE_HARNESS = {}
_CACHE_RED = {}


# ------------------------------------------------------------------ REUSO DEL INSTRUMENTO
def cargar_harness(K, hasta=MARCA_DATOS, tope_fuerza_bruta=None):
    """Ejecuta la FUENTE de eon_harness.py hasta un marcador y devuelve su espacio de nombres.

    `eon_harness.py` es un script, no un modulo: importarlo corre la medicion de q_ij, la
    fuerza bruta y el QAOA completo. Y copiar aqui su carga de red seria una lista viviendo
    en dos lugares, que es lo mismo que decir que ya divergio (CLAUDE.md §5 bis, regla 3).
    Ejecutar su propia fuente hasta un marcador deja la carga de red, el censo
    (`_censo_de_la_red`), el estres, los ratings apretados, la generacion de candidatos y el
    flujo DC siendo LITERALMENTE los del harness — no una copia.

    Falla cerrado: si el marcador no esta, aborta. Un marcador ausente significa que el
    harness cambio de forma, y seguir seria medir sobre una suposicion.
    """
    clave = (K, hasta, tope_fuerza_bruta)
    if clave in _CACHE_HARNESS:
        return _CACHE_HARNESS[clave]
    fuente = open(RUTA_HARNESS).read()
    if hasta not in fuente:
        raise SystemExit(
            "ABORTA: el marcador %r no esta en %s. Este archivo reusa la fuente del harness\n"
            "ejecutandola hasta ese punto; sin el marcador no hay forma de saber donde\n"
            "termina la carga de red y empieza el resto." % (hasta, RUTA_HARNESS))
    prefijo = fuente.split(hasta)[0]

    viejo = dict(os.environ)
    os.environ["RQ_GRID"] = GRID
    os.environ["RQ_CAND"] = str(K)
    os.environ["RQ_SEED"] = str(SEMILLA)
    os.environ["RQ_BUDGET"] = str(K_BUDGET)
    if tope_fuerza_bruta is not None:
        os.environ["RQ_TOPE_FB"] = str(tope_fuerza_bruta)
    os.environ["RQ_TIME_BUDGET"] = "120"
    mod = types.ModuleType("eon_harness_prefijo")
    mod.__dict__["__file__"] = RUTA_HARNESS
    t0 = time.time()
    try:
        exec(compile(prefijo, RUTA_HARNESS, "exec"), mod.__dict__)
    finally:
        os.environ.clear()
        os.environ.update(viejo)
    H = mod.__dict__
    if H.get("_N_BUS") is None:
        raise SystemExit("ABORTA: el censo del harness no corrio; la red medida es desconocida.")
    if int(H["K"]) != int(K):
        raise SystemExit("ABORTA: se pidieron %d candidatos y el harness produjo %d. Un K "
                         "distinto del pedido invalida la fila del barrido." % (K, H["K"]))
    H["_carga_s"] = round(time.time() - t0, 2)
    _CACHE_HARNESS[clave] = H
    return H


# --------------------------------------------------------------------------- LA RED
def extraer_red(H, K):
    """Del harness a datos planos: susceptancias, capacidades, cargas, generacion.

    LAS SUSCEPTANCIAS, medidas y verificadas (2026-08-14, case118):
      lineas : B = vn_from^2 / x_ohm_total  -> reconstruye p_from_mw de pandapower con un
               error maximo de 2,2e-12 MW sobre flujos de hasta 1248 MW. Es exacta.
      trafos : la formula sn/vk% se desvia hasta 7% por los taps, asi que NO se usa: B se
               deriva de la propia solucion DC del harness (p_hv / dtheta), que es exacta
               por construccion. Un 7% inventado en 13 enlaces habria movido el optimo.

    LAS CAPACIDADES, y por que se derivan asi. Hay dos formas y NO dan lo mismo:
      cap_dc   = |p_from_mw| / (loading%/100)  -> el MW al que la linea llega a 100% SEGUN
                                                  LA METRICA DEL PROPIO HARNESS
      cap_form = sqrt(3) * Vn * max_i_ka       -> la formula de placa
    Medido: difieren hasta 5,70% (media 1,57%; 111 de 173 lineas sobre 0,1%), porque el
    `i_ka` que pandapower reporta en DC no es |p|/(sqrt3*Vn). Se usa **cap_dc**, para que
    "esta congestionada" signifique aqui lo mismo que en `total_congestion()` del harness.
    """
    clave = (K, GRID, SEMILLA)
    if clave in _CACHE_RED:
        return _CACHE_RED[clave]
    import pandapower as pp
    net = H["build_base"]()
    pp.rundcpp(net)
    if list(net.line.index) != list(range(len(net.line))):
        raise SystemExit("ABORTA: el indice de net.line no es 0..n-1; los candidatos del "
                         "harness son posicionales y se leerian con la etiqueta equivocada.")
    vn = net.bus.vn_kv.values
    th = np.radians(net.res_bus.va_degree.values)
    L = net.line
    fb = L.from_bus.values.astype(int)
    tb = L.to_bus.values.astype(int)
    x_ohm = L.x_ohm_per_km.values * L.length_km.values / np.maximum(L.parallel.values, 1)
    B_line = vn[fb] ** 2 / x_ohm
    err = np.abs(B_line * (th[fb] - th[tb]) - net.res_line.p_from_mw.values).max()
    if err > 1e-6:
        raise SystemExit("ABORTA: la susceptancia derivada no reproduce el flujo DC de "
                         "pandapower (error %.3g MW). Sin eso el modelo no es el del "
                         "harness." % err)

    lp = net.res_line.loading_percent.values
    if float(lp.min()) < 1e-6:
        raise SystemExit("ABORTA: hay lineas con carga ~0%%: su capacidad en MW no se puede "
                         "derivar del flujo DC y no se va a inventar.")
    cap_line = np.abs(net.res_line.p_from_mw.values) / (lp / 100.0)
    cap_form = math.sqrt(3) * vn[fb] * L.max_i_ka.values
    razon = float(np.median(cap_line / cap_form))
    dif_max = float((np.abs(cap_line - cap_form) / cap_form).max())

    aristas = []      # (u, v, B, cap_mw, tipo)
    for li in range(len(L)):
        aristas.append((int(fb[li]), int(tb[li]), float(B_line[li]), float(cap_line[li]), "linea"))
    T = net.trafo
    if len(T):
        hb = T.hv_bus.values.astype(int)
        lb = T.lv_bus.values.astype(int)
        dth = th[hb] - th[lb]
        if np.abs(dth).min() < 1e-9:
            raise SystemExit("ABORTA: un trafo con dtheta ~ 0: su B no se puede derivar "
                             "del flujo base.")
        B_tr = net.res_trafo.p_hv_mw.values / dth
        for t in range(len(T)):
            # sn_mva de los trafos de case118 es 9900 y su carga maxima medida es 32%:
            # son enlaces practicamente sin limite. Se incluyen porque SIN ELLOS la red se
            # parte en 105 buses de 118, y la energia no servida vendria de la topologia
            # inventada y no de la congestion.
            aristas.append((int(hb[t]), int(lb[t]), float(B_tr[t]), float(T.sn_mva.values[t]),
                            "trafo"))
    n_fijas = len(aristas)

    # LAS CANDIDATAS SE MIDEN, NO SE DEDUCEN (2026-08-14).
    # La primera version le ponia a cada candidata la B y la cap deducidas de formulas, y a
    # las NUEVAS una capacidad corregida por la razon MEDIANA cap_dc/cap_form. Con eso la
    # prueba de fisica fallaba por ~0,93 MW sobre ~10.000 en los planes que incluian lineas
    # nuevas: la razon mediana es UNA y la real varia linea a linea hasta 5,7%. Un numero
    # deducido de una mediana se ve igual que uno medido, y este se descubrio SOLO porque la
    # prueba lo cruzaba contra pandapower.
    # Ahora cada candidata se APLICA con el propio `apply_candidate` del harness, se corre el
    # DC y se leen su B y su capacidad de esa solucion. Son K corridas DC extra.
    mixtas = []
    for c in H["cand"]:
        net2 = H["build_base"]()
        H["apply_candidate"](net2, c)
        pp.rundcpp(net2)
        th2 = np.radians(net2.res_bus.va_degree.values)
        u = int(net2.line.from_bus.values[-1])
        v = int(net2.line.to_bus.values[-1])
        p2 = float(net2.res_line.p_from_mw.values[-1])
        lp2 = float(net2.res_line.loading_percent.values[-1])
        d2 = float(th2[u] - th2[v])
        if abs(d2) < 1e-9 or lp2 < 1e-9:
            raise SystemExit("ABORTA: la candidata %s queda con flujo ~0 al aplicarla, asi "
                             "que su B y su capacidad no se pueden medir — y no se van a "
                             "deducir de una formula." % (c,))
        tipo_c = "cand_par" if c[0] == "parallel" else "cand_new"
        aristas.append((u, v, p2 / d2, abs(p2) / (lp2 / 100.0), tipo_c))
        if tipo_c == "cand_new":
            if abs(vn[u] - vn[v]) > 1e-9:
                # HALLAZGO SOBRE EL HARNESS, no sobre este modelo (2026-08-14, K=20):
                # `apply_candidate` elige los dos extremos de una linea NUEVA al azar entre
                # todos los buses, sin mirar el nivel de tension. Con K=20 salen dos
                # candidatas entre 138 y 345 kV y entre 161 y 138 kV, que fisicamente serian
                # transformadores y no lineas. pandapower no se queja: arma la rama con la
                # tension del bus de ORIGEN. Al medir B y capacidad sobre la red YA
                # modificada, este modelo hereda exactamente ese criterio — el trabajo aqui
                # es reproducir el instrumento existente, no arreglarlo por su cuenta.
                mixtas.append((u, v, float(vn[u]), float(vn[v])))

    carga = np.zeros(len(net.bus))
    for _, r in net.load.iterrows():
        carga[int(r.bus)] += float(r.p_mw)
    gens = [(int(r.bus), float(r.max_p_mw) if not np.isnan(float(r.max_p_mw)) else float(r.p_mw))
            for _, r in net.gen.iterrows()]
    gens_set = [float(r.p_mw) for _, r in net.gen.iterrows()]
    red = {"n_bus": len(net.bus), "aristas": aristas, "n_fijas": n_fijas,
           "carga": carga, "gens": gens, "gens_setpoint": gens_set,
           "slack_bus": int(net.ext_grid.iloc[0].bus),
           # el nodo de balance puede cubrir toda la carga nominal: si no, la energia no
           # servida vendria de una falta global de generacion y no de la red.
           "cap_slack": float(carga.sum()),
           "n_lineas": int(len(L)), "n_trafos": int(len(T)),
           "carga_total_mw": float(carga.sum()), "K": K,
           "cap_dif_max_pct": round(100 * dif_max, 3), "razon_cap": razon,
           "theta_base_max": float(np.abs(th).max()),
           "cand_nuevas_entre_tensiones_distintas": len(mixtas), "detalle_mixtas": mixtas}
    if mixtas:
        print("AVISO: %d candidata(s) NUEVA(s) del harness unen buses de tension distinta "
              "%s. Se modelan como lo hace pandapower (tension del bus de origen); la "
              "prueba 1 comprueba que la reproduccion sigue siendo exacta."
              % (len(mixtas), [(m[2], m[3]) for m in mixtas]))
    if THETA_MAX <= 1.5 * red["theta_base_max"]:
        raise SystemExit(
            "ABORTA: THETA_MAX=%.2f rad no deja holgura sobre el maximo MEDIDO en la corrida\n"
            "base (%.4f rad). Con la cota apretada el modelo sale INFEASIBLE y eso se lee\n"
            "como un defecto del modelo en vez de como una cota mal puesta."
            % (THETA_MAX, red["theta_base_max"]))
    _CACHE_RED[clave] = red
    return red


# ---------------------------------------------------------------------- LOS ESCENARIOS
def generar_escenarios(red, S, extremo=None, todos_nominales=False):
    """S escenarios. El 0 es SIEMPRE el nominal. Los demas, semilla derivada por escenario."""
    n_bus, n_gen = red["n_bus"], len(red["gens"])
    escen = []
    for s in range(S):
        if s == 0 or todos_nominales:
            escen.append({"carga": red["carga"].copy(), "avail": np.ones(n_gen)})
        else:
            rng = np.random.default_rng(np.random.SeedSequence([SEMILLA, s]))
            mult = np.clip(rng.normal(1.0, SIGMA_CARGA, n_bus),
                           1 - 3 * SIGMA_CARGA, 1 + 3 * SIGMA_CARGA)
            cae = rng.random(n_gen) < P_FALLA_GEN
            escen.append({"carga": red["carga"] * mult,
                          "avail": np.where(cae, rng.uniform(0.0, FALLA_MAX, n_gen), 1.0)})
    if extremo is not None:
        bus, factor = extremo
        escen[-1]["carga"] = escen[-1]["carga"].copy()
        escen[-1]["carga"][bus] *= factor
    return escen


# ------------------------------------------------------- MODELO 1: MILP CON RECURSO CONTINUO
def modelo_milp(red, escen, costo, solver_id="SCIP", x_fijo=None, sin_recurso=False,
                libre_cardinalidad=False):
    """Dos etapas: x binaria (K) + despacho DC continuo por escenario.

    `sin_recurso=True` congela el despacho en los setpoints del harness y prohibe el
    deslastre: en ese modo la segunda etapa no decide nada y el modelo REPRODUCE el flujo
    DC de pandapower. Es el modo con el que se comprueba la fisica (prueba 1).

    `libre_cardinalidad=True` quita `sum(x) == K_BUDGET`. Se agrego el 2026-08-17 para el
    brazo cuantico: los coeficientes del QUBO se miden evaluando planes de cardinalidad 0, 1
    y 2 —E(vacio), E({i}), E({i,j})— y con la restriccion puesta esos planes son
    INFACTIBLES. Solo se usa junto con `x_fijo`, donde la restriccion seria redundante para
    los planes de cardinalidad K_BUDGET: ningun camino existente cambia de comportamiento.
    """
    from ortools.linear_solver import pywraplp
    m = pywraplp.Solver.CreateSolver(solver_id)
    if m is None:
        raise SystemExit("ABORTA: el solucionador %r no esta disponible." % solver_id)
    K, S = red["K"], len(escen)
    A, nf, nb = red["aristas"], red["n_fijas"], red["n_bus"]
    INF = m.infinity()

    x = [m.BoolVar("x%d" % i) for i in range(K)]
    if not libre_cardinalidad:
        m.Add(sum(x) == K_BUDGET)
    elif x_fijo is None:
        raise SystemExit("ABORTA: libre_cardinalidad sin x_fijo dejaria el plan sin ninguna "
                         "restriccion de cardinalidad. No es un modo previsto.")
    if x_fijo is not None:
        for i in range(K):
            m.Add(x[i] == int(x_fijo[i]))
    obj = [W_BUILD * costo[i] * S * x[i] for i in range(K)]

    for s, es in enumerate(escen):
        th = [m.NumVar(-THETA_MAX, THETA_MAX, "th%d_%d" % (s, b)) for b in range(nb)]
        m.Add(th[red["slack_bus"]] == 0)
        f, ov = [], {}
        for e, (u, v, B, cap, tipo) in enumerate(A):
            f.append(m.NumVar(-INF, INF, "f%d_%d" % (s, e)))
            if tipo == "linea":
                o = m.NumVar(0, INF, "ov%d_%d" % (s, e))
                ov[e] = o
                m.Add(f[e] <= cap + o)
                m.Add(-f[e] <= cap + o)
                m.Add(f[e] - B * (th[u] - th[v]) == 0)
            elif tipo == "trafo":
                # SIN limite de capacidad, a proposito: los 13 trafos de case118 traen
                # sn_mva=9900 y su carga maxima medida en DC es 32%, y sobre todo
                # `total_congestion()` del harness suma SOLO `res_line` — los trafos no
                # entran a su metrica de congestion. Ponerles un tope duro aqui habria
                # metido una restriccion que el modelo de referencia no tiene.
                m.Add(f[e] - B * (th[u] - th[v]) == 0)
            else:
                i = e - nf
                M = B * 2 * THETA_MAX
                m.Add(f[e] - B * (th[u] - th[v]) <= M * (1 - x[i]))
                m.Add(f[e] - B * (th[u] - th[v]) >= -M * (1 - x[i]))
                # Una candidata CONSTRUIDA puede sobrecargarse, igual que cualquier linea:
                # el harness la cuenta en `res_line` y su sobrecarga entra a la congestion.
                # La primera version la dejaba con tope DURO (|f| <= cap*x) y eso hacia
                # INFEASIBLE cualquier plan cuya linea nueva pasara de su placa — un
                # infactible que se leia como "el modelo esta mal" y era una restriccion
                # inventada. `o <= BIGOV*x` mantiene el f=0 de la no construida.
                o = m.NumVar(0, INF, "ov%d_%d" % (s, e))
                ov[e] = o
                m.Add(o <= red["carga_total_mw"] * x[i])
                m.Add(f[e] <= cap * x[i] + o)
                m.Add(-f[e] <= cap * x[i] + o)
        if sin_recurso:
            g = [red["gens_setpoint"][j] for j in range(len(red["gens"]))]
            sl = m.NumVar(-INF, INF, "sl%d" % s)          # el nodo de balance absorbe
            shed = {}
        else:
            g = [m.NumVar(0, red["gens"][j][1] * es["avail"][j], "g%d_%d" % (s, j))
                 for j in range(len(red["gens"]))]
            sl = m.NumVar(0, red["cap_slack"], "sl%d" % s)
            shed = {b: m.NumVar(0, float(es["carga"][b]), "sh%d_%d" % (s, b))
                    for b in range(nb) if es["carga"][b] > 0}
        sale = [[] for _ in range(nb)]
        entra = [[] for _ in range(nb)]
        for e, (u, v, B, cap, tipo) in enumerate(A):
            sale[u].append(f[e])
            entra[v].append(f[e])
        iny = [[] for _ in range(nb)]
        for j, (bus, _) in enumerate(red["gens"]):
            iny[bus].append(g[j])
        iny[red["slack_bus"]].append(sl)
        for b in range(nb):
            neta = sum(sale[b]) - sum(entra[b])
            carga_b = float(es["carga"][b])
            m.Add(neta - (sum(iny[b]) - (carga_b - (shed[b] if b in shed else 0))) == 0)
        obj.append(C_OV * sum(ov.values()))
        if shed:
            obj.append(VOLL * sum(shed.values()))
    m.Minimize(sum(obj))
    return m, x


def resolver_milp(m, x, reloj_s, red):
    from ortools.linear_solver import pywraplp
    m.SetTimeLimit(int(reloj_s * 1000))
    t0 = time.time()
    st = m.Solve()
    dt = time.time() - t0
    nombres = {pywraplp.Solver.OPTIMAL: "OPTIMAL", pywraplp.Solver.FEASIBLE: "FEASIBLE",
               pywraplp.Solver.INFEASIBLE: "INFEASIBLE", pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
               pywraplp.Solver.ABNORMAL: "ABNORMAL", pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED"}
    nombre = nombres.get(st, "DESCONOCIDO_%s" % st)
    # FALLA CERRADO: un status que no reconocemos no se convierte en aviso.
    if nombre.startswith("DESCONOCIDO"):
        raise SystemExit("ABORTA: el MILP devolvio un status no previsto: %r" % st)
    if nombre in ("INFEASIBLE", "UNBOUNDED"):
        raise SystemExit("ABORTA: el MILP devolvio %s. Deslastrar toda la carga siempre es "
                         "factible, asi que esto es un defecto del modelo, no un "
                         "resultado." % nombre)
    tiene = nombre in ("OPTIMAL", "FEASIBLE")
    cota = None
    if tiene:
        try:
            cota = m.Objective().BestBound()
        except Exception:
            cota = None
    return {"status": nombre,
            "valor": (round(m.Objective().Value(), 6) if tiene else None),
            "cota": (round(cota, 6) if cota is not None else None),
            "x": ([int(round(v.solution_value())) for v in x] if tiene else None),
            "segundos": round(dt, 2),
            "n_variables": m.NumVariables(), "n_restricciones": m.NumConstraints()}


# ------------------------------------------------------- MODELO 2: CP-SAT (CRITERIO DECLARADO)
def modelo_cpsat(red, escen, costo, x_fijo=None):
    """El mismo modelo, discretizado a enteros, porque CP-SAT no tiene variables continuas.

    angulos en unidades de CP_DTHETA rad; potencias en unidades de CP_MW MW. La ecuacion
    f = B*dtheta se impone como `den*f - num*dtheta` dentro de una banda +-CP_TOL_U, con
    num/den la mejor aproximacion racional de B*CP_DTHETA/CP_MW. La banda es una decision
    declarada: sobre una grilla entera, la igualdad exacta impone divisibilidad.
    """
    from ortools.sat.python import cp_model
    m = cp_model.CpModel()
    K, S = red["K"], len(escen)
    A, nf, nb = red["aristas"], red["n_fijas"], red["n_bus"]
    TH = int(round(THETA_MAX / CP_DTHETA))
    GRANDE = int(round(red["carga_total_mw"] / CP_MW))

    x = [m.NewBoolVar("x%d" % i) for i in range(K)]
    m.Add(sum(x) == K_BUDGET)
    if x_fijo is not None:
        for i in range(K):
            m.Add(x[i] == int(x_fijo[i]))
    obj = [int(round(W_BUILD * costo[i] * S / CP_MW)) * x[i] for i in range(K)]

    frac = [Fraction(a[2] * CP_DTHETA / CP_MW).limit_denominator(500) for a in A]
    for s, es in enumerate(escen):
        th = [m.NewIntVar(-TH, TH, "th%d_%d" % (s, b)) for b in range(nb)]
        m.Add(th[red["slack_bus"]] == 0)
        f, ov = [], {}
        for e, (u, v, B, cap, tipo) in enumerate(A):
            capu = int(round(cap / CP_MW))
            f.append(m.NewIntVar(-GRANDE, GRANDE, "f%d_%d" % (s, e)))
            num, den = frac[e].numerator, frac[e].denominator
            if tipo in ("linea", "trafo"):
                m.Add(den * f[e] - num * (th[u] - th[v]) <= CP_TOL_U * den)
                m.Add(den * f[e] - num * (th[u] - th[v]) >= -CP_TOL_U * den)
            else:
                i = e - nf
                M = int(num * 2 * TH) + CP_TOL_U * den
                m.Add(den * f[e] - num * (th[u] - th[v]) <= CP_TOL_U * den + M * (1 - x[i]))
                m.Add(den * f[e] - num * (th[u] - th[v]) >= -CP_TOL_U * den - M * (1 - x[i]))
            if tipo == "linea":
                o = m.NewIntVar(0, GRANDE, "ov%d_%d" % (s, e))
                ov[e] = o
                m.Add(f[e] <= capu + o)
                m.Add(-f[e] <= capu + o)
            elif tipo == "cand_par" or tipo == "cand_new":
                i = e - nf
                o = m.NewIntVar(0, GRANDE, "ov%d_%d" % (s, e))
                ov[e] = o
                m.Add(o <= GRANDE * x[i])
                m.Add(f[e] <= capu * x[i] + o)
                m.Add(-f[e] <= capu * x[i] + o)
            # los trafos van sin tope: ver la nota en modelo_milp
        g = [m.NewIntVar(0, max(0, int(red["gens"][j][1] * es["avail"][j] / CP_MW)),
                         "g%d_%d" % (s, j)) for j in range(len(red["gens"]))]
        sl = m.NewIntVar(0, int(round(red["cap_slack"] / CP_MW)), "sl%d" % s)
        shed = {b: m.NewIntVar(0, int(round(es["carga"][b] / CP_MW)), "sh%d_%d" % (s, b))
                for b in range(nb) if es["carga"][b] > 0}
        sale = [[] for _ in range(nb)]
        entra = [[] for _ in range(nb)]
        for e, (u, v, B, cap, tipo) in enumerate(A):
            sale[u].append(f[e])
            entra[v].append(f[e])
        iny = [[] for _ in range(nb)]
        for j, (bus, _) in enumerate(red["gens"]):
            iny[bus].append(g[j])
        iny[red["slack_bus"]].append(sl)
        for b in range(nb):
            cb = int(round(es["carga"][b] / CP_MW))
            m.Add(sum(sale[b]) - sum(entra[b]) - sum(iny[b]) + cb
                  - (shed[b] if b in shed else 0) == 0)
        obj.append(int(round(C_OV)) * sum(ov.values()))
        if shed:
            obj.append(int(round(VOLL)) * sum(shed.values()))
    m.Minimize(sum(obj))
    return m, x


def resolver_cpsat(m, x, reloj_s, hilos=HILOS):
    from ortools.sat.python import cp_model
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(reloj_s)
    solver.parameters.num_workers = hilos
    solver.parameters.random_seed = SEMILLA
    t0 = time.time()
    st = solver.Solve(m)
    dt = time.time() - t0
    nombre = solver.StatusName(st)
    if nombre not in ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN", "MODEL_INVALID"):
        raise SystemExit("ABORTA: CP-SAT devolvio un status no previsto: %r" % nombre)
    if nombre in ("INFEASIBLE", "MODEL_INVALID"):
        raise SystemExit("ABORTA: CP-SAT devolvio %s. Deslastrar toda la carga siempre es "
                         "factible; esto es un defecto del modelo." % nombre)
    tiene = nombre in ("OPTIMAL", "FEASIBLE")
    return {"status": nombre,
            "valor": (round(solver.ObjectiveValue() * CP_MW, 6) if tiene else None),
            "cota": (round(solver.BestObjectiveBound() * CP_MW, 6) if tiene else None),
            "x": ([int(solver.Value(v)) for v in x] if tiene else None),
            "segundos": round(dt, 2),
            "n_variables": len(m.Proto().variables),
            "n_restricciones": len(m.Proto().constraints)}


def brecha_pct(valor, cota):
    """Brecha de optimalidad contra LA PROPIA COTA del solucionador. Nunca se supone."""
    if valor is None or cota is None:
        return None
    d = abs(valor) if abs(valor) > 1e-9 else 1.0
    return round(100.0 * (valor - cota) / d, 4)


# ==========================================================================================
# EL BRAZO CUANTICO — QAOA SOBRE LA PRIMERA ETAPA (agregado 2026-08-17)
# ==========================================================================================
# POR QUE HASTA HOY NO ESTABA
# ---------------------------
# Este archivo encontro la frontera midiendo SOLO el lado clasico: K=10, S=250 es donde SCIP
# deja de PROBAR optimalidad dentro de 900 s (FEASIBLE, brecha 1,93 % — fila 18 del CSV).
# Ese punto es la ventana entera, porque la frontera cae con **10 binarias de primera
# etapa** — diez qubits, dentro de lo ya corrido en hardware real — mientras el problema
# clasico crece ~650 variables por escenario.
#
# LA TESIS, ESCRITA ANTES DE MEDIR NADA: el circuito no crece con S. Los escenarios entran en
# los COEFICIENTES del QUBO (costo esperado de operacion por linea y por par de lineas), no
# en el circuito. Si el numero de qubits creciera con S no habria asimetria y no habria nada
# que preguntar. La PRUEBA Q2 lo comprueba en vez de suponerlo.
#
# LA EVALUACION ES UNA SOLA Y ES LA EXACTA
# ----------------------------------------
# El plan que propone el brazo cuantico se evalua con `evaluar_plan_exacto` — la MISMA
# funcion de costo, sobre los MISMOS S escenarios, que evalua al plan de SCIP. Nunca la
# aproximacion de 2do orden contra la exacta del clasico: eso mediria el QUBO y no el plan,
# que es la sexta variante de CLAUDE.md §5 quater (un numero correcto respondiendo otra
# pregunta).
#
# Y LA TRAMPA QUE ESTE ARCHIVO DECLARA EN VEZ DE ESCONDER
# -------------------------------------------------------
# Con K=10 el espacio entero son 2^10 = 1024 estados. Un muestreo de 2000 disparos visita
# casi todos, asi que "el brazo cuantico encontro el optimo del QUBO" puede ser fuerza bruta
# disfrazada. Por eso cada corrida reporta (a) cuantos estados DISTINTOS vio el muestreo
# sobre 2^K, y (b) un control de AZAR UNIFORME con el mismo numero de disparos. Si el azar
# empata al circuito, el circuito no aporto nada y hay que decirlo.

_CACHE_EVAL = {}


def lp_escenario(red, es, sel, solver_id="GLOP"):
    """Costo de OPERACION exacto de UN escenario, dado el plan de primera etapa `sel`.

    Es la segunda etapa de `modelo_milp` con x fijo. Con x fijo el problema se SEPARA por
    escenario —el objetivo es una suma por escenario y no hay ninguna restriccion que los
    ate— asi que resolver S problemitas de ~650 variables da EXACTAMENTE lo mismo que
    resolver uno de 650*S. Eso no se supone: `verificar_evaluador` lo comprueba contra el
    modelo monolitico antes de usarlo, y falla cerrado si difieren.

    Una candidata NO construida se omite (en el modelo grande su big-M con x=0 mas
    `|f| <= cap*0 + o`, `o <= carga_total*0` la dejan en f=0: omitirla es lo mismo).
    """
    from ortools.linear_solver import pywraplp
    m = pywraplp.Solver.CreateSolver(solver_id)
    if m is None:
        raise SystemExit("ABORTA: el solucionador %r no esta disponible." % solver_id)
    A, nf, nb = red["aristas"], red["n_fijas"], red["n_bus"]
    INF = m.infinity()
    construidas = set(int(i) for i in sel)
    th = [m.NumVar(-THETA_MAX, THETA_MAX, "th%d" % b) for b in range(nb)]
    m.Add(th[red["slack_bus"]] == 0)
    f, ov = {}, {}
    for e, (u, v, B, cap, tipo) in enumerate(A):
        if tipo in ("cand_par", "cand_new") and (e - nf) not in construidas:
            continue
        fe = m.NumVar(-INF, INF, "f%d" % e)
        f[e] = fe
        m.Add(fe - B * (th[u] - th[v]) == 0)
        if tipo == "trafo":
            continue          # sin tope de capacidad: ver la nota larga en modelo_milp
        o = m.NumVar(0, INF, "ov%d" % e)
        ov[e] = o
        m.Add(fe <= cap + o)
        m.Add(-fe <= cap + o)
    g = [m.NumVar(0, red["gens"][j][1] * es["avail"][j], "g%d" % j)
         for j in range(len(red["gens"]))]
    sl = m.NumVar(0, red["cap_slack"], "sl")
    shed = {b: m.NumVar(0, float(es["carga"][b]), "sh%d" % b)
            for b in range(nb) if es["carga"][b] > 0}
    sale = [[] for _ in range(nb)]
    entra = [[] for _ in range(nb)]
    for e, fe in f.items():
        sale[A[e][0]].append(fe)
        entra[A[e][1]].append(fe)
    iny = [[] for _ in range(nb)]
    for j, (bus, _) in enumerate(red["gens"]):
        iny[bus].append(g[j])
    iny[red["slack_bus"]].append(sl)
    for b in range(nb):
        carga_b = float(es["carga"][b])
        m.Add(sum(sale[b]) - sum(entra[b])
              - (sum(iny[b]) - (carga_b - (shed[b] if b in shed else 0))) == 0)
    m.Minimize(C_OV * sum(ov.values()) + VOLL * sum(shed.values()))
    st = m.Solve()
    if st != pywraplp.Solver.OPTIMAL:
        raise SystemExit("ABORTA: el LP de un escenario no dio OPTIMAL (status %s) para el "
                         "plan %s. Deslastrar toda la carga siempre es factible, asi que "
                         "esto es un defecto del modelo, no un resultado." % (st, sorted(sel)))
    return float(m.Objective().Value())


def evaluar_plan_exacto(red, escen, costo, sel, cache=None):
    """LA funcion de costo. La misma para el plan del cuantico y para el de SCIP.

    valor = W_BUILD * sum(costo_i) * S  +  sum_s  costo_de_operacion_s(sel)
    Es termino por termino el objetivo de `modelo_milp` con x fijo en `sel`.
    """
    clave = tuple(sorted(int(i) for i in sel))
    if cache is not None and clave in cache:
        return cache[clave]
    S = len(escen)
    v = W_BUILD * sum(costo[i] for i in clave) * S
    for es in escen:
        v += lp_escenario(red, es, clave)
    if cache is not None:
        cache[clave] = v
    return v


def verificar_evaluador(red, escen, costo, planes, tol_rel=1e-6):
    """FALLA CERRADO: el evaluador separado por escenario == el modelo monolitico.

    Sin esto, toda la medicion del brazo cuantico se apoyaria en una suposicion ("el
    problema se separa con x fijo") que se ve razonable y que nadie resto nunca.
    """
    filas = []
    for sel in planes:
        xf = [1 if i in sel else 0 for i in range(red["K"])]
        m, x = modelo_milp(red, escen, costo, solver_id="SCIP", x_fijo=xf,
                           libre_cardinalidad=True)
        r = resolver_milp(m, x, 300, red)
        if r["status"] != "OPTIMAL":
            raise SystemExit("ABORTA: el monolitico no probo optimalidad con x fijo en %s "
                             "(%s); sin ese numero no hay contra que comparar." % (sel, r["status"]))
        mio = evaluar_plan_exacto(red, escen, costo, sel)
        rel = abs(mio - r["valor"]) / max(1e-9, abs(r["valor"]))
        filas.append({"plan": sorted(sel), "separado": round(mio, 6),
                      "monolitico": r["valor"], "dif_rel": rel})
        print("    plan %-18s separado=%16.4f  monolitico=%16.4f  dif rel=%.3e"
              % (str(sorted(sel)), mio, r["valor"], rel))
    peor = max(f["dif_rel"] for f in filas)
    if peor >= tol_rel:
        raise SystemExit(
            "ABORTA: el evaluador por escenario difiere del modelo monolitico en %.3e "
            "(tope %.0e). Toda la comparacion cuantico/clasico se apoya en que son la "
            "MISMA funcion de costo; si no lo son, no hay nada que medir." % (peor, tol_rel))
    return {"planes": filas, "peor_dif_relativa": peor, "pasa": True,
            "denominador": len(filas)}


# ------------------------------------------------------------------ EL QUBO DE PRIMERA ETAPA
def construir_qubo(red, escen, costo, cache=None, verboso=True):
    """Los S escenarios entran AQUI, en los coeficientes. El circuito no los ve.

    Mismo patron que `eon_harness.py` (expansion de 2do orden medida, no supuesta):
        r_i  = E(vacio) - E({i})              alivio esperado de construir solo i
        q_ij = (E(vacio) - E({i,j})) - r_i - r_j   interaccion esperada del par
    con E = `evaluar_plan_exacto`, o sea el costo esperado sobre los S escenarios. La
    diferencia con el harness es que alli E era una congestion DC de un escenario y aqui es
    el costo esperado de operacion bajo S escenarios: mismo esqueleto, coeficientes que
    dependen de la distribucion.

    Costo de armarlo: 1 + K + K(K-1)/2 evaluaciones exactas. Es el precio de que el circuito
    no crezca, y se mide y se declara (`segundos`), no se esconde.

    A diferencia del harness NO hay termino de costo aparte: E ya incluye W_BUILD*costo_i*S,
    asi que r_i ya trae el costo de construir con su signo.
    """
    K, S = red["K"], len(escen)
    if cache is None:
        cache = {}
    t0 = time.time()
    E0 = evaluar_plan_exacto(red, escen, costo, [], cache)
    Ei = np.zeros(K)
    for i in range(K):
        Ei[i] = evaluar_plan_exacto(red, escen, costo, [i], cache)
    r = E0 - Ei
    q = {}
    for i in range(K):
        for j in range(i + 1, K):
            Eij = evaluar_plan_exacto(red, escen, costo, [i, j], cache)
            q[(i, j)] = (E0 - Eij) - r[i] - r[j]
    n_eval = 1 + K + K * (K - 1) // 2

    # LA PENALIDAD, con su criterio escrito. Tiene que costar mas violar la cardinalidad que
    # cualquier ganancia posible de agregar o quitar una linea: PEN > max_i(|r_i| + sum_j
    # |q_ij|). El factor 3 es holgura declarada. La prueba Q1 comprueba que el argmin LIBRE
    # sobre 2^K sale con exactamente K_BUDGET unos — si la penalidad fuera chica, no saldria.
    peor_ganancia = max(abs(r[i]) + sum(abs(q[tuple(sorted((i, j)))])
                                        for j in range(K) if j != i) for i in range(K))
    PEN = 3.0 * (peor_ganancia + 1.0)

    Q = np.zeros((K, K))
    c_lin = np.zeros(K)
    for i in range(K):
        c_lin[i] += -r[i] + PEN * (1 - 2 * K_BUDGET)
        Q[i][i] += PEN
        for j in range(i + 1, K):
            Q[i][j] += -q[(i, j)] + 2 * PEN
    CONST = PEN * K_BUDGET ** 2 + E0
    # CONST lleva E0 para que `qubo_val` de un plan de cardinalidad K_BUDGET este en las
    # MISMAS unidades que `evaluar_plan_exacto` — asi la diferencia entre los dos es
    # legible como error de truncamiento de 2do orden y no como un desplazamiento.
    seg = round(time.time() - t0, 2)
    if verboso:
        print("  QUBO S=%-4d: %d evaluaciones exactas en %.1fs · E(vacio)=%.4f · "
              "r en [%.3f, %.3f] · q en [%.3f, %.3f] · PEN=%.4g"
              % (S, n_eval, seg, E0, r.min(), r.max(),
                 min(q.values()), max(q.values()), PEN), flush=True)
    return {"K": K, "S": S, "Q": Q, "c_lin": c_lin, "CONST": CONST, "PEN": PEN,
            "r": r, "q": q, "E0": E0, "evaluaciones": n_eval, "segundos": seg,
            "cache": cache}


def qubo_val(qb, x):
    x = np.asarray(x, float)
    return float(x @ qb["Q"] @ x + qb["c_lin"] @ x + qb["CONST"])


def qubo_val_sin_penalidad(qb, sel):
    """El modelo de 2do orden PURO: E0 - sum r_i - sum q_ij. Sin el termino de cardinalidad.

    Es lo que hay que comparar contra `evaluar_plan_exacto` para |sel| <= 2, donde la
    expansion es EXACTA por construccion: si ahi no calza al ultimo decimal, hay un indice o
    un signo mal puestos y todo lo demas sobra.
    """
    sel = sorted(int(i) for i in sel)
    v = qb["E0"] - sum(qb["r"][i] for i in sel)
    for a in range(len(sel)):
        for b in range(a + 1, len(sel)):
            v -= qb["q"][(sel[a], sel[b])]
    return float(v)


# ------------------------------------------------------------------------- EL CIRCUITO
def circuito_de(qb, capas=None):
    """QUBO -> Ising -> circuito QAOA. Devuelve el circuito Y SU FORMA MEDIDA.

    Existe como funcion aparte para que la PRUEBA Q2 mida el objeto CONSTRUIDO —los cables
    del dispositivo, los terminos del Hamiltoniano, las compuertas del circuito— y no se
    limite a repetir el K que le pasamos. Un chequeo que compara un parametro contra si
    mismo pasa siempre (CLAUDE.md §4: la instruccion repite el resultado, no lo calcula).

    LA NORMALIZACION DEL HAMILTONIANO, declarada. Con S=250 los coeficientes del QUBO son de
    orden 1e5: con ellos crudos, los angulos iniciales (0,01) producen fases de miles de
    radianes y el circuito arranca ya desfasado — el optimizador no mediria el metodo sino la
    escala. El Hamiltoniano se divide por `escala` (el mayor |coeficiente|) SOLO para el
    circuito; los bitstrings muestreados se evaluan con el QUBO sin escalar. Dividir por una
    constante positiva no mueve el argmin.
    """
    import pennylane as qml
    K = qb["K"]
    capas = int(capas if capas else max(2, K // 4))
    Q, c_lin, CONST = qb["Q"], qb["c_lin"], qb["CONST"]
    Qs = (Q + Q.T) / 2
    J = np.zeros((K, K))
    h = np.zeros(K)
    off = CONST
    for i in range(K):
        off += Qs[i][i] / 2 + c_lin[i] / 2
        h[i] -= Qs[i][i] / 2 + c_lin[i] / 2
        for j in range(K):
            if i != j:
                off += Qs[i][j] / 4
                h[i] -= Qs[i][j] / 4
                J[i][j] += Qs[i][j] / 4
    co, op = [], []
    for i in range(K):
        if abs(h[i]) > 1e-12:
            co.append(h[i]); op.append(qml.PauliZ(i))
    for i in range(K):
        for j in range(i + 1, K):
            cij = J[i][j] + J[j][i]
            if abs(cij) > 1e-12:
                co.append(cij); op.append(qml.PauliZ(i) @ qml.PauliZ(j))
    if not co:
        raise SystemExit("ABORTA: el Hamiltoniano quedo vacio: el QUBO no tiene estructura y "
                         "no hay nada que optimizar.")
    escala = float(max(abs(c) for c in co))
    H = qml.Hamiltonian([float(c) / escala for c in co], op)
    dev = qml.device("default.qubit", wires=K)

    def circ(p):
        for w in range(K):
            qml.Hadamard(wires=w)
        for l in range(capas):
            qml.templates.ApproxTimeEvolution(H, p[0][l], 1)
            for w in range(K):
                qml.RX(2 * p[1][l], wires=w)

    @qml.qnode(dev)
    def cost_fn(p):
        circ(p)
        return qml.expval(H)

    # LA FORMA, LEIDA DEL OBJETO. `qubits` sale de los cables del DISPOSITIVO y
    # `cables_usados` de la cinta del circuito ya trazado: si algun dia el circuito tocara un
    # cable por escenario, estos dos numeros lo dirian. `qml.specs` da el conteo real de
    # compuertas y la profundidad.
    import pennylane.numpy as pnp
    p0 = pnp.array(0.01 * np.ones((2, capas)), requires_grad=True)
    esp = qml.specs(cost_fn)(p0)
    rec = qml.workflow.construct_tape(cost_fn)(p0)
    forma = {"S": qb["S"], "capas": capas,
             "qubits": len(dev.wires),
             "cables_usados_por_el_circuito": len(rec.wires),
             "terminos_hamiltoniano": len(co),
             "terminos_2_cuerpos": sum(1 for o in op if len(o.wires) == 2),
             "compuertas": int(esp["resources"].num_gates),
             "profundidad": int(esp["resources"].depth),
             "escala_hamiltoniano": escala,
             "evaluaciones_para_armar_el_qubo": qb["evaluaciones"],
             "segundos_para_armar_el_qubo": qb["segundos"]}
    return {"H": H, "dev": dev, "circ": circ, "cost_fn": cost_fn, "capas": capas,
            "escala": escala, "n_terminos": len(co), "forma": forma}


def brazo_qaoa(qb, capas=None, pasos=None, disparos=None, reloj_s=None, semilla=SEMILLA,
               verboso=True):
    """QAOA sobre las K binarias de primera etapa. Mismo patron que `eon_harness.py`."""
    import pennylane as qml
    from pennylane import numpy as pnp
    K = qb["K"]
    pasos = int(pasos if pasos else 300)
    disparos = int(disparos if disparos else 2000)
    reloj_s = float(reloj_s if reloj_s else 600.0)
    C = circuito_de(qb, capas)
    capas, circ, cost_fn, escala, co = (C["capas"], C["circ"], C["cost_fn"],
                                        C["escala"], range(C["n_terminos"]))
    dev = C["dev"]

    t0 = time.time()
    pnp.random.seed(semilla)
    params = pnp.array(0.01 * pnp.random.rand(2, capas), requires_grad=True)
    opt = qml.AdamOptimizer(0.05)
    dados = 0
    for s in range(pasos):
        if time.time() - t0 > reloj_s * 0.8:
            break
        params = opt.step(cost_fn, params)
        dados = s + 1
    seg_opt = round(time.time() - t0, 3)

    devs = qml.device("default.qubit", wires=K, shots=disparos, seed=semilla)

    @qml.qnode(devs)
    def samp(p):
        circ(p)
        return qml.sample(wires=range(K))

    muestras = np.array(samp(params)).reshape(disparos, K)
    vals = np.array([qubo_val(qb, m) for m in muestras])
    distintos = len(set(tuple(int(b) for b in m) for m in muestras))

    # LA LECTURA DEL MUESTREO, Y POR QUE NO ES `argmin` A SECAS.
    # ---------------------------------------------------------
    # El ensayo del 2026-08-17 (K=6, S=3) lo atrapo en la primera corrida: el argmin sobre
    # los 200 disparos cayo en un bitstring de CUATRO lineas con presupuesto de cinco, y su
    # costo exacto salio 1,5 % por debajo del de SCIP. El titular habria sido "el cuantico
    # gana" y la verdad era que comparaba un plan INFACTIBLE contra uno factible: construir
    # menos lineas cuesta menos, y el plan de 4 no es una respuesta al problema que SCIP
    # resuelve. No fue la penalidad: con PEN=2073 ningun plan de 4 le gana a uno de 5 en el
    # QUBO. Fue que entre los 33 estados distintos que vio el muestreo no habia NINGUNO de
    # los 6 factibles.
    #
    # Asi que el plan que sale del brazo es el mejor disparo FACTIBLE (cardinalidad ==
    # K_BUDGET), la lectura estandar de un QUBO con penalidad, y se declara el denominador:
    # cuantos disparos fueron factibles de cuantos. Si no hubo ninguno, no hay plan y se
    # detiene — no se corrige a mano ni se compara con lo que haya.
    card = muestras.sum(axis=1)
    fact = np.where(card == K_BUDGET)[0]
    x_libre = [int(b) for b in muestras[int(np.argmin(vals))]]
    if len(fact) == 0:
        raise SystemExit(
            "ABORTA: ninguno de los %d disparos cumplio la cardinalidad %d (se vieron %d "
            "estados distintos de %d). El brazo cuantico NO produjo un plan comparable, y "
            "un plan infactible no se compara con el de SCIP." % (disparos, K_BUDGET,
                                                                  distintos, 2 ** K))
    mejor = int(fact[np.argmin(vals[fact])])
    x = [int(b) for b in muestras[mejor]]
    factibles_distintos = len(set(tuple(int(b) for b in muestras[i]) for i in fact))

    # EL CONTROL DE AZAR: mismos disparos, misma regla de lectura, sin circuito.
    # Si empata, el circuito no aporto nada sobre tirar monedas — y con K=10 el espacio son
    # 1024 estados, asi que empatar es el resultado ESPERADO. Se mide para poder decirlo.
    rng_az = np.random.default_rng(semilla)
    az = rng_az.integers(0, 2, size=(disparos, K))
    vals_az = np.array([qubo_val(qb, m) for m in az])
    fact_az = np.where(az.sum(axis=1) == K_BUDGET)[0]
    if len(fact_az) == 0:
        x_az, val_az_q, n_fact_az = None, None, 0
    else:
        ia = int(fact_az[np.argmin(vals_az[fact_az])])
        x_az = [int(b) for b in az[ia]]
        val_az_q = qubo_val(qb, x_az)
        n_fact_az = int(len(fact_az))

    out = {"framework": "PennyLane", "backend": "default.qubit (CPU sim)",
           "layers": capas, "optimizer": "Adam, %d steps" % dados, "shots": disparos,
           "pasos_dados": dados, "pasos_de_presupuesto": pasos,
           "reloj_s": reloj_s,
           "truncado_por_reloj": bool(dados < pasos),
           "advertencia": (None if dados >= pasos else
                           "el optimizador dio %d de %d pasos: el reloj lo corto. Esta "
                           "brecha mide el presupuesto, no el metodo." % (dados, pasos)),
           "qubits": K, "terminos_hamiltoniano": len(co),
           "escala_hamiltoniano": escala,
           "forma_circuito": C["forma"],
           "valor_qubo": qubo_val(qb, x), "x": x,
           "n_selected": int(sum(x)),
           "x_mejor_disparo_sin_filtrar": x_libre,
           "n_selected_sin_filtrar": int(sum(x_libre)),
           "regla_de_lectura": "mejor disparo con cardinalidad == K_BUDGET (%d)" % K_BUDGET,
           "disparos_factibles": int(len(fact)),
           "disparos_totales": disparos,
           "factibles_distintos": factibles_distintos,
           "factibles_posibles_C_K_kbudget": math.comb(K, K_BUDGET),
           "segundos_optimizador": seg_opt,
           "runtime_s": round(time.time() - t0, 3),
           "estados_distintos_muestreados": distintos,
           "espacio_total_2aK": 2 ** K,
           "cobertura_del_espacio_pct": round(100.0 * distintos / (2 ** K), 2),
           "cobertura_del_espacio_factible_pct": round(
               100.0 * factibles_distintos / max(1, math.comb(K, K_BUDGET)), 2),
           "control_azar": {"x": x_az, "valor_qubo": val_az_q,
                            "n_selected": (None if x_az is None else int(sum(x_az))),
                            "disparos": disparos, "disparos_factibles": n_fact_az,
                            "nota": "mismos disparos y la misma regla de lectura, sin "
                                    "circuito. Si empata al QAOA, el circuito no aporto "
                                    "nada sobre muestrear al azar."}}
    if verboso:
        print("  QAOA: %d qubits · %d capas · %d/%d pasos%s · %d disparos · %d estados "
              "distintos de %d (%.1f%%) · factibles %d disparos / %d distintos de C(%d,%d)=%d"
              % (K, capas, dados, pasos, " (TRUNCADO)" if dados < pasos else "",
                 disparos, distintos, 2 ** K, out["cobertura_del_espacio_pct"],
                 len(fact), factibles_distintos, K, K_BUDGET, math.comb(K, K_BUDGET)),
              flush=True)
    return out


# ------------------------------------------------------------------ EL ARBITRO POR ENUMERACION
def enumerar_exacto(red, escen, costo, K, k_budget, cache=None, verboso=True):
    """Optimo REAL de la primera etapa: las C(K, k_budget) combinaciones, evaluadas exacto.

    POR QUE ESTO SE PUEDE HACER Y POR QUE IMPORTA (medido el 2026-08-17):
    en K=10, S=250 —el punto donde SCIP NO prueba optimalidad en 900 s— la primera etapa
    tiene apenas C(10,5)=252 planes factibles, y cada uno se evalua con S LPs chicos e
    independientes. El optimo REAL se conoce en ~1.100 s. Sin este numero, "el cuantico
    empata o pierde contra SCIP" no dice si alguno de los dos llego al optimo: la brecha de
    SCIP se mide contra SU cota, que es una cota y no el optimo.

    Es el arbitro mas fuerte que hay aqui y es una enumeracion, no una heuristica.
    """
    t0 = time.time()
    mejor = None
    todas = []
    for comb in combinations(range(K), k_budget):
        v = evaluar_plan_exacto(red, escen, costo, list(comb), cache)
        todas.append((list(comb), v))
        if mejor is None or v < mejor[0]:
            mejor = (v, list(comb))
        if verboso and len(todas) % 25 == 0:
            print("    %d/%d planes (%.0fs)" % (len(todas), math.comb(K, k_budget),
                                                time.time() - t0), flush=True)
    todas.sort(key=lambda t: t[1])
    seg = round(time.time() - t0, 2)
    if verboso:
        print("  ARBITRO S=%d: optimo REAL = %.6f  plan %s  (%d de %d planes, %.0fs)"
              % (len(escen), mejor[0], mejor[1], len(todas), math.comb(K, k_budget), seg),
              flush=True)
    return {"valor": mejor[0], "plan": mejor[1], "combinaciones": len(todas),
            "esperadas": math.comb(K, k_budget), "segundos": seg,
            "peor_valor": todas[-1][1], "peor_plan": todas[-1][0],
            "top10": [{"plan": p, "valor": v} for p, v in todas[:10]],
            "todas": [{"plan": p, "valor": v} for p, v in todas]}


def corrida_arbitro(K, S):
    """El arbitro por enumeracion en un punto, como modo propio del harness."""
    print("\n=== ARBITRO POR ENUMERACION  red=%s  K=%d  S=%d  semilla=%d ==="
          % (GRID, K, S, SEMILLA))
    H = cargar_harness(K, tope_fuerza_bruta=0)
    red = extraer_red(H, K)
    costo = list(np.asarray(H["cost"], float))
    escen = generar_escenarios(red, S)
    r = enumerar_exacto(red, escen, costo, K, K_BUDGET, cache={})
    if r["combinaciones"] != r["esperadas"]:
        raise SystemExit("ABORTA: se evaluaron %d planes y C(%d,%d)=%d. Un arbitro que no "
                         "recorrio todo el conjunto no es un arbitro."
                         % (r["combinaciones"], K, K_BUDGET, r["esperadas"]))
    r.update({"red": GRID, "K": K, "S": S, "k_budget": K_BUDGET, "semilla": SEMILLA})
    return r


# ------------------------------------------------------------------------- LAS PRUEBAS Q
def prueba_q1(K_chico=8, k_budget_chico=3):
    """PRUEBA 1 — con S=1 y K chico, el optimo del QUBO == el optimo del MILP.

    Se enumeran las C(K, k) combinaciones y se comparan DOS argmin: el del QUBO y el de la
    funcion exacta. Ademas se comprueba la identidad de 2do orden para |sel| <= 2, donde la
    expansion es exacta por construccion — ese pedazo no admite interpretacion: si falla, hay
    un indice o un signo mal puestos.

    POR QUE k_budget=3 Y NO 2: con 2 la prueba seria una TAUTOLOGIA (la expansion de 2do
    orden es exacta para pares, asi que el argmin coincidiria por definicion y la prueba
    pasaria contra cualquier construccion). Con 3 el termino de 3er orden existe de verdad y
    la prueba puede fallar.
    """
    global K_BUDGET
    viejo = K_BUDGET
    K_BUDGET = int(k_budget_chico)
    try:
        H = cargar_harness(K_chico, tope_fuerza_bruta=0)
        red = extraer_red(H, K_chico)
        costo = list(np.asarray(H["cost"], float))
        esc1 = generar_escenarios(red, 1)
        cache = {}
        print("  evaluador separado vs monolitico (falla cerrado):")
        ver = verificar_evaluador(red, esc1, costo, [[], [0], [0, 1],
                                                     list(range(k_budget_chico))])
        qb = construir_qubo(red, esc1, costo, cache=cache)

        # (a) identidad exacta de 2do orden
        peor_id, peor_sel = 0.0, None
        n_id = 0
        for tam in (0, 1, 2):
            for sel in combinations(range(K_chico), tam):
                ex = evaluar_plan_exacto(red, esc1, costo, list(sel), cache)
                ap = qubo_val_sin_penalidad(qb, sel)
                d = abs(ex - ap) / max(1e-9, abs(ex))
                n_id += 1
                if d > peor_id:
                    peor_id, peor_sel = d, list(sel)
        print("  identidad 2do orden en |sel|<=2: peor dif relativa %.3e sobre %d subconjuntos"
              % (peor_id, n_id))

        # (b) los dos argmin sobre las C(K,k) combinaciones
        mejor_q, mejor_e = None, None
        combos = []
        for comb in combinations(range(K_chico), k_budget_chico):
            xv = [1 if i in comb else 0 for i in range(K_chico)]
            vq = qubo_val(qb, xv)
            ve = evaluar_plan_exacto(red, esc1, costo, list(comb), cache)
            combos.append((list(comb), vq, ve))
            if mejor_q is None or vq < mejor_q[1]:
                mejor_q = (list(comb), vq)
            if mejor_e is None or ve < mejor_e[1]:
                mejor_e = (list(comb), ve)
        e_del_plan_qubo = dict((tuple(c), e) for c, _, e in combos)[tuple(mejor_q[0])]
        arrepentimiento = (e_del_plan_qubo - mejor_e[1]) / max(1e-9, abs(mejor_e[1]))

        # (c) el argmin LIBRE sobre 2^K tiene que salir con exactamente k_budget unos
        libre = min(((list(b), qubo_val(qb, b)) for b in _bits(K_chico)), key=lambda t: t[1])
        card_ok = (sum(libre[0]) == k_budget_chico)

        igual = (mejor_q[0] == mejor_e[0])
        print("  argmin QUBO   : %s  (costo exacto %.4f)" % (mejor_q[0], e_del_plan_qubo))
        print("  argmin EXACTO : %s  (costo exacto %.4f)" % (mejor_e[0], mejor_e[1]))
        print("  penalidad: el argmin libre sobre 2^%d elige %d lineas (se piden %d): %s"
              % (K_chico, sum(libre[0]), k_budget_chico, "OK" if card_ok else "FALLA"))
        print("  -> CRITERIO Q1: mismo optimo = %s · identidad 2do orden %.3e (tope 1e-9) · "
              "arrepentimiento %.3e" % (igual, peor_id, arrepentimiento))
        return {"K": K_chico, "k_budget": k_budget_chico, "S": 1,
                "verificacion_evaluador": ver,
                "identidad_2do_orden_peor_dif_rel": peor_id,
                "identidad_2do_orden_subconjuntos": n_id,
                "identidad_2do_orden_peor_sel": peor_sel,
                "identidad_pasa": bool(peor_id < 1e-9),
                "argmin_qubo": mejor_q[0], "argmin_exacto": mejor_e[0],
                "valor_exacto_del_plan_qubo": e_del_plan_qubo,
                "valor_exacto_optimo": mejor_e[1],
                "arrepentimiento_relativo": arrepentimiento,
                "combinaciones_enumeradas": len(combos),
                "combinaciones_esperadas": math.comb(K_chico, k_budget_chico),
                "argmin_libre_cardinalidad": int(sum(libre[0])),
                "penalidad_respeta_cardinalidad": bool(card_ok),
                "pasa": bool(igual and peor_id < 1e-9 and card_ok)}
    finally:
        K_BUDGET = viejo


def _bits(n):
    from itertools import product
    return product([0, 1], repeat=n)


def prueba_q3(K=10, factor=10, buses_tope=None):
    """PRUEBA 3 — un escenario extremo tiene que MOVER los coeficientes del QUBO.

    Si no los mueve, los escenarios no estan entrando y estarias midiendo otra cosa. Se barre
    cada bus con carga y se reporta el DENOMINADOR: cuantos mueven, de cuantos probados.

    Se comparan los coeficientes LINEALES r_i (K+1 evaluaciones por bus). Para el bus de mayor
    carga se compara ademas la matriz completa q_ij, que es la parte que hace que el circuito
    tenga estructura de dos cuerpos.
    """
    H = cargar_harness(K, tope_fuerza_bruta=0)
    red = extraer_red(H, K)
    costo = list(np.asarray(H["cost"], float))
    base = generar_escenarios(red, 2, todos_nominales=True)
    qb_base = construir_qubo(red, base, costo, verboso=False)
    buses = [b for b in range(red["n_bus"]) if red["carga"][b] > 0]
    if buses_tope:
        buses = sorted(buses, key=lambda b: -red["carga"][b])[:buses_tope]
    movieron, quietos, peor_por_bus = 0, [], []
    for b in buses:
        esc = generar_escenarios(red, 2, extremo=(b, factor), todos_nominales=True)
        cache = {}
        E0 = evaluar_plan_exacto(red, esc, costo, [], cache)
        r = np.array([E0 - evaluar_plan_exacto(red, esc, costo, [i], cache) for i in range(K)])
        d = float(np.abs(r - qb_base["r"]).max())
        rel = d / max(1e-9, float(np.abs(qb_base["r"]).max()))
        peor_por_bus.append((b, float(red["carga"][b]), d, rel))
        if rel > 1e-6:
            movieron += 1
        else:
            quietos.append(b)
    b_max = max(buses, key=lambda b: red["carga"][b])
    esc_max = generar_escenarios(red, 2, extremo=(b_max, factor), todos_nominales=True)
    qb_max = construir_qubo(red, esc_max, costo, verboso=False)
    dq = max(abs(qb_max["q"][k] - qb_base["q"][k]) for k in qb_base["q"])
    dq_rel = dq / max(1e-9, max(abs(v) for v in qb_base["q"].values()))
    print("  x%d sobre 1 de 2 escenarios, probado en los %d buses con carga" % (factor, len(buses)))
    print("  buses que MUEVEN los coeficientes lineales r_i: %d de %d" % (movieron, len(buses)))
    print("  bus de mayor carga %d (%.1f MW): peor cambio en q_ij = %.4f (rel %.3e)"
          % (b_max, float(red["carga"][b_max]), dq, dq_rel))
    peor_por_bus.sort(key=lambda t: -t[3])
    for b, c, d, rel in peor_por_bus[:5]:
        print("    bus %-4d (%7.1f MW) -> max|dr| = %10.4f  (rel %.3e)" % (b, c, d, rel))
    return {"factor": factor, "buses_probados": len(buses), "buses_que_mueven": movieron,
            "buses_quietos": len(quietos), "ejemplos_quietos": quietos[:10],
            "bus_mayor_carga": int(b_max),
            "cambio_max_q_ij": dq, "cambio_max_q_ij_relativo": dq_rel,
            "top5_lineales": [{"bus": int(b), "carga_mw": round(c, 1),
                               "max_dr": round(d, 4), "rel": rel}
                              for b, c, d, rel in peor_por_bus[:5]],
            "pasa": bool(movieron > 0 and dq_rel > 1e-6)}


# ------------------------------------------------------------------------- LA CORRIDA
def corrida_cuantica(K, S, reloj_s=RELOJ_S, capas=None, pasos=None, disparos=None,
                     reloj_cuantico=None, con_scip=True, S_ref_qubits=1):
    """El brazo cuantico contra SCIP en el MISMO punto, con la MISMA funcion de costo."""
    print("\n=== CORRIDA CUANTICA  red=%s  K=%d  S=%d  semilla=%d ===" % (GRID, K, S, SEMILLA))
    H = cargar_harness(K, tope_fuerza_bruta=0)
    red = extraer_red(H, K)
    costo = list(np.asarray(H["cost"], float))
    escen = generar_escenarios(red, S)
    cache = {}

    print("  evaluador separado vs monolitico (falla cerrado), sobre %d escenarios:" % min(S, 3))
    ver = verificar_evaluador(red, generar_escenarios(red, min(S, 3)), costo,
                              [[], [0, 1], list(range(K_BUDGET))])

    qb = construir_qubo(red, escen, costo, cache=cache)
    cuantico = brazo_qaoa(qb, capas=capas, pasos=pasos, disparos=disparos,
                          reloj_s=reloj_cuantico)
    sel_q = sorted(i for i, b in enumerate(cuantico["x"]) if b)
    if not sel_q:
        raise SystemExit("ABORTA: el brazo cuantico no produjo ningun plan (todo ceros).")
    if len(sel_q) != K_BUDGET:
        raise SystemExit("ABORTA: el plan cuantico elige %d lineas y el presupuesto es %d. "
                         "Un plan fuera de presupuesto no es comparable con el de SCIP y no "
                         "se corrige a mano." % (len(sel_q), K_BUDGET))
    t0 = time.time()
    valor_q = evaluar_plan_exacto(red, escen, costo, sel_q, cache)
    seg_eval_q = round(time.time() - t0, 2)
    x_az = cuantico["control_azar"]["x"]
    sel_az = sorted(i for i, b in enumerate(x_az) if b) if x_az else None
    valor_az = (evaluar_plan_exacto(red, escen, costo, sel_az, cache)
                if sel_az is not None else None)

    # ---- EL RIVAL: SCIP con su mejor solucion al cabo de reloj_s, y su cota.
    clasico = None
    if con_scip:
        t0 = time.time()
        m, x = modelo_milp(red, escen, costo, solver_id="SCIP")
        armado = round(time.time() - t0, 2)
        clasico = resolver_milp(m, x, reloj_s, red)
        clasico["armado_s"] = armado
        clasico["brecha_pct"] = brecha_pct(clasico["valor"], clasico["cota"])
        clasico["corte"] = None if clasico["status"] == "OPTIMAL" else "reloj"
        if clasico["x"] is None:
            raise SystemExit("ABORTA: SCIP no devolvio ningun plan en %ss (status %s). Sin "
                             "rival no hay comparacion." % (reloj_s, clasico["status"]))
        sel_c = sorted(i for i, b in enumerate(clasico["x"]) if b)
        valor_c = evaluar_plan_exacto(red, escen, costo, sel_c, cache)
        # CONTROL CRUZADO: mi evaluador contra el objetivo que reporta el propio SCIP para
        # SU plan. Si no calzan, una de las dos funciones de costo no es la que creo.
        rel_cc = abs(valor_c - clasico["valor"]) / max(1e-9, abs(clasico["valor"]))
        if rel_cc >= 1e-6:
            raise SystemExit(
                "ABORTA: mi evaluador da %.6f para el plan de SCIP y SCIP reporta %.6f "
                "(dif rel %.3e). No son la misma funcion de costo y la comparacion no vale."
                % (valor_c, clasico["valor"], rel_cc))
        clasico["plan"] = sel_c
        clasico["valor_recomputado"] = valor_c
        clasico["dif_rel_recomputo"] = rel_cc
        print("  SCIP: %s en %.1fs · valor=%.4f · cota=%s · brecha=%s%% · plan=%s"
              % (clasico["status"], clasico["segundos"], clasico["valor"], clasico["cota"],
                 clasico["brecha_pct"], sel_c), flush=True)

    # ---- EL VEREDICTO, con sus numeros
    ver_dict = {"plan_cuantico": sel_q, "valor_exacto_cuantico": valor_q,
                "plan_azar": sel_az, "valor_exacto_azar": valor_az}
    if clasico:
        d = valor_q - clasico["valor"]
        ver_dict.update({
            "plan_scip": clasico["plan"], "valor_exacto_scip": clasico["valor_recomputado"],
            "scip_status": clasico["status"], "scip_cota": clasico["cota"],
            "scip_brecha_pct": clasico["brecha_pct"],
            "scip_probo_optimalidad": clasico["status"] == "OPTIMAL",
            "diferencia_cuantico_menos_scip": round(d, 6),
            "diferencia_pct": round(100.0 * d / max(1e-9, abs(clasico["valor"])), 4),
            "cuantico_gana": bool(d < -1e-6),
            "empatan": bool(abs(d) <= 1e-6),
            "cuantico_supera_la_cota_inferior": (
                None if clasico["cota"] is None else bool(valor_q < clasico["cota"] - 1e-6)),
            "mismo_plan": bool(sel_q == clasico["plan"])})
        ver_dict["veredicto"] = ("EL CUANTICO GANA" if d < -1e-6 else
                                 ("EMPATE — mismo valor" if abs(d) <= 1e-6 else
                                  "EL CUANTICO PIERDE"))
    # el presupuesto de reloj, contado entero y honesto
    t_cuantico = qb["segundos"] + cuantico["runtime_s"] + seg_eval_q
    ver_dict["reloj_cuantico_total_s"] = round(t_cuantico, 2)
    ver_dict["reloj_cuantico_desglose_s"] = {
        "armar_el_qubo": qb["segundos"], "qaoa": cuantico["runtime_s"],
        "evaluar_el_plan": seg_eval_q}
    ver_dict["reloj_clasico_s"] = (clasico["segundos"] + clasico["armado_s"]) if clasico else None
    ver_dict["mismo_presupuesto"] = (
        None if not clasico else bool(t_cuantico <= clasico["segundos"] + clasico["armado_s"]))

    salida = {"red": GRID, "K": K, "S": S, "semilla": SEMILLA, "k_budget": K_BUDGET,
              "reloj_s": reloj_s, "n_lineas": red["n_lineas"], "n_trafos": red["n_trafos"],
              "verificacion_evaluador": ver,
              "qubo": {"evaluaciones": qb["evaluaciones"], "segundos": qb["segundos"],
                       "E0": qb["E0"], "PEN": qb["PEN"],
                       "r": [float(v) for v in qb["r"]],
                       "q": {"%d_%d" % k: float(v) for k, v in qb["q"].items()}},
              "cuantico": cuantico, "clasico": clasico, "veredicto": ver_dict}
    print("  -> %s: cuantico %.4f  vs  SCIP %.4f  (%+.4f%%)  · azar %s"
          % (ver_dict.get("veredicto", "sin rival"), valor_q,
             clasico["valor"] if clasico else float("nan"),
             ver_dict.get("diferencia_pct", float("nan")),
             ("%.4f" % valor_az) if valor_az is not None else "no comparable"), flush=True)
    return salida, qb, red, costo, cache


def prueba_q2(qb_chico, qb_grande, red, escen_chico, escen_grande, costo, capas=None):
    """PRUEBA 2 — el circuito NO puede crecer con S. Es la tesis entera del encargo.

    Se CONSTRUYEN los dos circuitos y se leen sus numeros del objeto: cables del dispositivo,
    cables que toca la cinta trazada, terminos del Hamiltoniano, compuertas y profundidad.
    Y como contraste se arma el MILP clasico en los mismos dos puntos y se leen SUS variables
    y restricciones — que es donde el crecimiento con S tiene que verse. Sin ese contraste,
    "el circuito no crece" es una afirmacion sin nada al lado.
    """
    a = circuito_de(qb_chico, capas)["forma"]
    b = circuito_de(qb_grande, capas)["forma"]
    clas = {}
    for etiqueta, esc in (("chico", escen_chico), ("grande", escen_grande)):
        m, x = modelo_milp(red, esc, costo, solver_id="SCIP")
        clas[etiqueta] = {"S": len(esc), "n_variables": m.NumVariables(),
                          "n_restricciones": m.NumConstraints()}
    iguales = [k for k in ("qubits", "cables_usados_por_el_circuito",
                           "terminos_hamiltoniano", "terminos_2_cuerpos",
                           "compuertas", "profundidad") if a[k] == b[k]]
    distintos = [k for k in ("qubits", "cables_usados_por_el_circuito",
                             "terminos_hamiltoniano", "terminos_2_cuerpos",
                             "compuertas", "profundidad") if a[k] != b[k]]
    print("  circuito S=%-4d: %d qubits · %d cables trazados · %d terminos · %d compuertas · "
          "profundidad %d" % (a["S"], a["qubits"], a["cables_usados_por_el_circuito"],
                              a["terminos_hamiltoniano"], a["compuertas"], a["profundidad"]))
    print("  circuito S=%-4d: %d qubits · %d cables trazados · %d terminos · %d compuertas · "
          "profundidad %d" % (b["S"], b["qubits"], b["cables_usados_por_el_circuito"],
                              b["terminos_hamiltoniano"], b["compuertas"], b["profundidad"]))
    print("  idem en %d de %d rasgos medidos; distintos: %s"
          % (len(iguales), len(iguales) + len(distintos), distintos or "ninguno"))
    print("  contraste, el MILP clasico: S=%d -> %d variables / %d restricciones   ·   "
          "S=%d -> %d / %d  (x%.1f)"
          % (clas["chico"]["S"], clas["chico"]["n_variables"], clas["chico"]["n_restricciones"],
             clas["grande"]["S"], clas["grande"]["n_variables"], clas["grande"]["n_restricciones"],
             clas["grande"]["n_variables"] / max(1, clas["chico"]["n_variables"])))
    print("  costo de que no crezca: armar el QUBO paso de %s a %s evaluaciones exactas "
          "(%.1fs -> %.1fs)" % (a["evaluaciones_para_armar_el_qubo"],
                                b["evaluaciones_para_armar_el_qubo"],
                                a["segundos_para_armar_el_qubo"],
                                b["segundos_para_armar_el_qubo"]))
    igual = (a["qubits"] == b["qubits"])
    return {"chico": a, "grande": b, "clasico": clas,
            "rasgos_identicos": iguales, "rasgos_distintos": distintos,
            "denominador_rasgos": len(iguales) + len(distintos),
            "qubits_identicos": bool(igual),
            "clasico_crece": bool(clas["grande"]["n_variables"] > clas["chico"]["n_variables"]),
            "pasa": bool(igual and not distintos)}


# ------------------------------------------------------------------------- UN PUNTO
def un_punto(K, S, reloj_s=RELOJ_S, motores=("cpsat", "SCIP"), verboso=True):
    H = cargar_harness(K, tope_fuerza_bruta=0)   # 0 => la fuerza bruta del harness no corre
    red = extraer_red(H, K)
    costo = list(np.asarray(H["cost"], float))
    escen = generar_escenarios(red, S)
    out = {"K": K, "S": S}
    for mot in motores:
        t0 = time.time()
        try:
            if mot == "cpsat":
                m, x = modelo_cpsat(red, escen, costo)
                armado = round(time.time() - t0, 2)
                r = resolver_cpsat(m, x, reloj_s)
            else:
                m, x = modelo_milp(red, escen, costo, solver_id=mot)
                armado = round(time.time() - t0, 2)
                r = resolver_milp(m, x, reloj_s, red)
        except MemoryError:
            out[mot] = {"status": "MEMORIA", "corte": "memoria",
                        "armado_s": round(time.time() - t0, 2)}
            continue
        r["armado_s"] = armado
        r["brecha_pct"] = brecha_pct(r["valor"], r["cota"])
        r["valor_por_escenario"] = None if r["valor"] is None else round(r["valor"] / S, 6)
        r["corte"] = None if r["status"] == "OPTIMAL" else "reloj"
        out[mot] = r
        if verboso:
            print("  K=%-3d S=%-4d %-6s %-10s %8.1fs  vars=%-8d restr=%-8d valor=%-14s "
                  "cota=%-14s brecha=%s"
                  % (K, S, mot, r["status"], r["segundos"], r["n_variables"],
                     r["n_restricciones"], r["valor"], r["cota"], r["brecha_pct"]), flush=True)
    out["n_lineas"] = red["n_lineas"]
    out["n_trafos"] = red["n_trafos"]
    return out


# ------------------------------------------------------------------------- LAS PRUEBAS
def congestion_por_plan(H, sel):
    """Sobrecarga en MW y en 'loading% sobre 100' del harness, para un plan dado.

    Usa build_base + apply_candidate + rundcpp del PROPIO harness: es su flujo DC, no una
    reimplementacion. Devuelve las dos metricas para poder cruzarlas con el modelo.
    """
    import pandapower as pp
    net = H["build_base"]()
    for i in sel:
        H["apply_candidate"](net, H["cand"][i])
    pp.rundcpp(net)
    lp = net.res_line.loading_percent.values
    pf = np.abs(net.res_line.p_from_mw.values)
    # sobrecarga en MW = |f| - cap, y cap = |f|/(loading/100) => sobrecarga = |f|*(lp-100)/lp.
    # Escrito asi para no dividir por una carga nula: una linea recien construida puede
    # quedar con flujo 0, y 0/0 habria entrado a la suma como nan — que impreso en una
    # tabla se lee como un numero (CLAUDE.md §5 quater).
    sob = np.where(lp > 100.0, pf * (lp - 100.0) / np.where(lp > 0, lp, 1.0), 0.0)
    if np.isnan(sob).any():
        raise SystemExit("ABORTA: nan en la sobrecarga por plan; no se suma un nan.")
    return {"suma_loading_sobre_100": float(np.maximum(lp - 100.0, 0).sum()),
            "sobrecarga_mw": float(sob.sum())}


def prueba_fisica(K):
    """PRUEBA 1 sola, a cualquier K: el modelo SIN recurso == el flujo DC del harness.

    Es la unica comparacion que tiene sentido exigir contra `eon_harness.py`, y conviene
    decir por que. El harness NO tiene segunda etapa: evalua una respuesta fisica fija
    (generadores en su consigna, el nodo de balance absorbiendo) sobre un QUBO de 2do orden.
    Un programa de dos etapas CON recurso —redespacho y deslastre— es otro modelo, y su
    optimo no tiene por que coincidir con el suyo ni estar en las mismas unidades. Pedir
    que "S=1 reproduzca el determinista" en valor objetivo es pedir que dos funciones
    distintas den el mismo numero.
    Lo que SI tiene que coincidir, y aqui se exige plan por plan, es LA FISICA: congelando
    el despacho, la sobrecarga en MW que da este modelo tiene que ser la que da pandapower
    corriendo el DC del harness sobre la misma red con las mismas lineas construidas.
    """
    Hx = cargar_harness(K, hasta=MARCA_EXACTO)     # incluye la fuerza bruta del QUBO
    red = extraer_red(Hx, K)
    costo = list(np.asarray(Hx["cost"], float))
    det_sel = sorted(i for i, b in enumerate(list(Hx["exact"]["x"])) if b) \
        if Hx["exact"]["x"] else list(range(K_BUDGET))
    print("theta base max = %.4f rad (cota del modelo: %.1f)" % (red["theta_base_max"], THETA_MAX))
    esc1 = generar_escenarios(red, 1)
    planes = [det_sel, list(range(K_BUDGET)), list(range(K - K_BUDGET, K)),
              sorted(range(0, K, max(1, K // K_BUDGET)))[:K_BUDGET]]
    filas = []
    for sel in planes:
        xf = [1 if i in sel else 0 for i in range(K)]
        m, x = modelo_milp(red, esc1, costo, solver_id="SCIP", x_fijo=xf, sin_recurso=True)
        r = resolver_milp(m, x, 300, red)
        if r["status"] != "OPTIMAL":
            raise SystemExit("ABORTA: el modo sin-recurso no resolvio para %s (%s)."
                             % (sel, r["status"]))
        mio = (r["valor"] - W_BUILD * sum(costo[i] for i in sel)) / C_OV
        pand = congestion_por_plan(Hx, sel)
        rel = abs(mio - pand["sobrecarga_mw"]) / max(pand["sobrecarga_mw"], 1e-9)
        filas.append((sel, mio, pand["sobrecarga_mw"], pand["suma_loading_sobre_100"], rel))
        print("  plan %-24s sobrecarga modelo=%10.3f MW  pandapower=%10.3f MW  dif rel=%.3e"
              % (str(sel), mio, pand["sobrecarga_mw"], rel))
    peor = max(f[4] for f in filas)
    print("  -> CRITERIO K=%d: dif relativa maxima %.3e (tope 1e-4): %s"
          % (K, peor, "PASA" if peor < 1e-4 else "FALLA"))
    return {"K": K, "peor_dif_relativa": peor, "pasa": bool(peor < 1e-4),
            "cand_nuevas_entre_tensiones_distintas": red["cand_nuevas_entre_tensiones_distintas"],
            "planes": [{"plan": f[0], "modelo_mw": round(f[1], 4),
                        "pandapower_mw": round(f[2], 4),
                        "loading_sobre_100": round(f[3], 3), "dif_rel": f[4]} for f in filas]}


def pruebas():
    out = {}
    K = 10
    print("\n=== PRUEBA 1 — la fisica: S=1 SIN recurso == el flujo DC del harness ===")
    Hx = cargar_harness(K, hasta=MARCA_EXACTO)     # incluye la fuerza bruta del QUBO
    red = extraer_red(Hx, K)
    costo = list(np.asarray(Hx["cost"], float))
    det_x = list(Hx["exact"]["x"])
    det_sel = sorted(i for i, b in enumerate(det_x) if b)
    print("theta base max = %.4f rad (cota del modelo: %.1f)" % (red["theta_base_max"], THETA_MAX))
    esc1 = generar_escenarios(red, 1)
    planes = [det_sel, [0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [1, 3, 5, 7, 8]]
    filas = []
    for sel in planes:
        xf = [1 if i in sel else 0 for i in range(K)]
        m, x = modelo_milp(red, esc1, costo, solver_id="SCIP", x_fijo=xf, sin_recurso=True)
        r = resolver_milp(m, x, 300, red)
        if r["status"] != "OPTIMAL":
            raise SystemExit("ABORTA: el modo sin-recurso no resolvio para %s (%s)."
                             % (sel, r["status"]))
        build = W_BUILD * sum(costo[i] for i in sel)
        mio = (r["valor"] - build) / C_OV
        pand = congestion_por_plan(Hx, sel)
        rel = abs(mio - pand["sobrecarga_mw"]) / max(pand["sobrecarga_mw"], 1e-9)
        filas.append((sel, mio, pand["sobrecarga_mw"], pand["suma_loading_sobre_100"], rel))
        print("  plan %-16s sobrecarga modelo=%10.3f MW   pandapower=%10.3f MW   "
              "dif rel=%.3e   (loading>100 sumado: %.1f)" % (str(sel), mio,
              pand["sobrecarga_mw"], rel, pand["suma_loading_sobre_100"]))
    peor = max(f[4] for f in filas)
    print("  -> CRITERIO: dif relativa maxima %.3e (tope 1e-4): %s"
          % (peor, "PASA" if peor < 1e-4 else "FALLA"))
    out["prueba1_fisica"] = {"peor_dif_relativa": peor, "pasa": bool(peor < 1e-4),
                             "planes": [{"plan": f[0], "modelo_mw": round(f[1], 4),
                                         "pandapower_mw": round(f[2], 4),
                                         "loading_sobre_100": round(f[3], 3),
                                         "dif_rel": f[4]} for f in filas]}

    print("\n=== PRUEBA 1 bis — S=1 CON recurso contra un arbitro independiente ===")
    m, x = modelo_milp(red, esc1, costo, solver_id="SCIP")
    r1 = resolver_milp(m, x, 900, red)
    mi_sel = sorted(i for i, b in enumerate(r1["x"]) if b)
    print("  MILP conjunto      : valor=%.4f  set=%s  %s" % (r1["valor"], mi_sel, r1["status"]))
    t0 = time.time()
    mejor = None
    for comb in combinations(range(K), K_BUDGET):
        xf = [1 if i in comb else 0 for i in range(K)]
        mm, xx = modelo_milp(red, esc1, costo, solver_id="SCIP", x_fijo=xf)
        rr = resolver_milp(mm, xx, 120, red)
        if rr["status"] != "OPTIMAL":
            raise SystemExit("ABORTA: el arbitro no probo optimalidad en %s (%s)."
                             % (comb, rr["status"]))
        if mejor is None or rr["valor"] < mejor[0]:
            mejor = (rr["valor"], list(comb))
    igual = abs(mejor[0] - r1["valor"]) < 1e-4 * max(1.0, abs(mejor[0]))
    print("  arbitro C(%d,%d)=%d piezas (%.0fs): valor=%.4f  set=%s"
          % (K, K_BUDGET, math.comb(K, K_BUDGET), time.time() - t0, mejor[0], mejor[1]))
    print("  -> CP/MILP == arbitro: %s" % igual)
    dc_nada = congestion_por_plan(Hx, [])
    dc_det = congestion_por_plan(Hx, det_sel)
    dc_mio = congestion_por_plan(Hx, mi_sel)
    print("  congestion DC del harness (loading>100 sumado):  sin construir %.1f | plan "
          "determinista %s %.1f | plan estocastico %s %.1f"
          % (dc_nada["suma_loading_sobre_100"], det_sel, dc_det["suma_loading_sobre_100"],
             mi_sel, dc_mio["suma_loading_sobre_100"]))
    out["prueba1bis_arbitro"] = {
        "milp_valor": r1["valor"], "milp_set": mi_sel, "arbitro_valor": mejor[0],
        "arbitro_set": mejor[1], "coinciden": bool(igual),
        "determinista_set": det_sel, "determinista_valor_qubo": Hx["exact"]["value"],
        "dc_sin_construir": dc_nada["suma_loading_sobre_100"],
        "dc_plan_determinista": dc_det["suma_loading_sobre_100"],
        "dc_plan_estocastico": dc_mio["suma_loading_sobre_100"]}

    print("\n=== PRUEBA 2 — S escenarios IDENTICOS al nominal == S=1 ===")
    out["prueba2"] = {}
    for Sid in (5, 20):
        esc_id = generar_escenarios(red, Sid, todos_nominales=True)
        m2, x2 = modelo_milp(red, esc_id, costo, solver_id="SCIP")
        r2 = resolver_milp(m2, x2, 900, red)
        por = r2["valor"] / Sid
        ok = abs(por - r1["valor"]) < 1e-4 * max(1.0, abs(r1["valor"]))
        print("  S=%-3d identicos: valor=%14.4f  /S=%12.4f  vs S=1 %12.4f  ->  %s"
              % (Sid, r2["valor"], por, r1["valor"], "CALZA" if ok else "NO CALZA"))
        out["prueba2"]["S%d" % Sid] = {"valor": r2["valor"], "valor_por_escenario": por,
                                       "S1_valor": r1["valor"], "calza": bool(ok),
                                       "set": sorted(i for i, b in enumerate(r2["x"]) if b)}

    print("\n=== PRUEBA 3 — un escenario extremo tiene que MOVER la decision ===")
    # POR QUE ESTA PRUEBA BARRE TODOS LOS BUSES Y NO UNO SOLO
    # ------------------------------------------------------
    # La primera version cargaba x10 el bus de mayor demanda (el 58, 720,2 MW) y el plan
    # NO se movio. La conclusion tentadora era la del encargo —"los escenarios no entran
    # al modelo"— y habria sido falsa: los escenarios entraban (el objetivo cambiaba), pero
    # ese bus concreto no lo pueden ayudar las 10 candidatas, que refuerzan otro corredor.
    # Un solo bus no distingue "el escenario no llega a la decision" de "ese bus no tiene
    # candidata que lo sirva". Se barren TODOS los buses con carga y se reporta el
    # denominador: cuantos mueven la decision, de cuantos probados.
    factor = 10
    buses = [b for b in range(red["n_bus"]) if red["carga"][b] > 0]
    mueven, sin_efecto_obj = [], 0
    dos_nom = generar_escenarios(red, 2, todos_nominales=True)
    m0, x0 = modelo_milp(red, dos_nom, costo, solver_id="SCIP")
    r0 = resolver_milp(m0, x0, 300, red)
    base2 = r0["valor"]
    for b in buses:
        esc_ext = generar_escenarios(red, 2, extremo=(b, factor), todos_nominales=True)
        m3, x3 = modelo_milp(red, esc_ext, costo, solver_id="SCIP")
        r3 = resolver_milp(m3, x3, 300, red)
        if r3["status"] != "OPTIMAL":
            raise SystemExit("ABORTA: la prueba 3 no resolvio en el bus %d (%s)." % (b, r3["status"]))
        sel3 = sorted(i for i, v in enumerate(r3["x"]) if v)
        if abs(r3["valor"] - base2) < 1e-6:
            sin_efecto_obj += 1
        if sel3 != mi_sel:
            mueven.append({"bus": b, "carga_mw": round(float(red["carga"][b]), 1),
                           "set": sel3, "valor": r3["valor"]})
    print("  x%d sobre 1 de 2 escenarios, probado en los %d buses con carga" % (factor, len(buses)))
    print("  buses que MUEVEN el plan optimo: %d de %d" % (len(mueven), len(buses)))
    print("  buses cuyo extremo no cambia ni el objetivo: %d de %d" % (sin_efecto_obj, len(buses)))
    for d in mueven[:5]:
        print("    bus %-4d (%7.1f MW) -> %s   (nominal: %s)" % (d["bus"], d["carga_mw"],
                                                                 d["set"], mi_sel))
    movio = len(mueven) > 0
    print("  -> %s" % ("LOS ESCENARIOS LLEGAN A LA DECISION" if movio else
                       "NINGUN EXTREMO MUEVE EL PLAN — los escenarios NO entran a la decision"))
    out["prueba3"] = {"factor": factor, "buses_probados": len(buses),
                      "buses_que_mueven": len(mueven),
                      "buses_sin_efecto_en_el_objetivo": sin_efecto_obj,
                      "set_nominal": mi_sel, "ejemplos": mueven[:10],
                      "valor_dos_nominales": base2, "movio": bool(movio)}

    print("\n=== PRUEBA 4 — la discretizacion de CP-SAT no cambia el optimo ===")
    mc, xc = modelo_cpsat(red, esc1, costo)
    rc = resolver_cpsat(mc, xc, RELOJ_S)
    sel_c = sorted(i for i, b in enumerate(rc["x"]) if b) if rc["x"] else None
    rel_c = (None if rc["valor"] is None else
             abs(rc["valor"] - r1["valor"]) / max(1e-9, abs(r1["valor"])))
    print("  CP-SAT S=1: %s valor=%s set=%s   MILP: %.4f set=%s   dif rel=%s"
          % (rc["status"], rc["valor"], sel_c, r1["valor"], mi_sel, rel_c))
    out["prueba4_discretizacion"] = {"cpsat_status": rc["status"], "cpsat_valor": rc["valor"],
                                     "cpsat_set": sel_c, "milp_valor": r1["valor"],
                                     "milp_set": mi_sel, "dif_relativa": rel_c,
                                     "mismo_set": (sel_c == mi_sel),
                                     "segundos": rc["segundos"]}

    out["veredicto"] = {
        "1_fisica_reproduce_el_flujo_DC_del_harness": bool(peor < 1e-4),
        "2_promedio_bien_ponderado": all(v["calza"] for v in out["prueba2"].values()),
        "3_los_escenarios_mueven_la_decision": bool(movio),
        "4_la_discretizacion_cpsat_no_deforma": (sel_c == mi_sel),
    }
    return out


# ------------------------------------------------------------------------- EL BARRIDO
CAMPOS = ["fecha", "red", "K", "S", "semilla", "k_budget", "reloj_s", "motor", "status",
          "segundos", "valor", "valor_por_escenario", "cota", "brecha_pct", "n_variables",
          "n_restricciones", "armado_s", "corte", "x", "n_lineas", "n_trafos",
          "modelo_2a_etapa", "sigma_carga", "p_falla_gen", "voll", "c_ov", "w_build"]


def filas_de(punto, motores):
    fs = []
    for mot in motores:
        r = punto.get(mot)
        if r is None:
            continue
        fs.append({
            "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "red": GRID,
            "K": punto["K"], "S": punto["S"], "semilla": SEMILLA, "k_budget": K_BUDGET,
            "reloj_s": RELOJ_S, "motor": mot, "status": r.get("status"),
            "segundos": r.get("segundos"), "valor": r.get("valor"),
            "valor_por_escenario": r.get("valor_por_escenario"), "cota": r.get("cota"),
            "brecha_pct": r.get("brecha_pct"), "n_variables": r.get("n_variables"),
            "n_restricciones": r.get("n_restricciones"), "armado_s": r.get("armado_s"),
            "corte": r.get("corte"),
            "x": "".join(str(b) for b in r["x"]) if r.get("x") else None,
            "n_lineas": punto.get("n_lineas"), "n_trafos": punto.get("n_trafos"),
            "modelo_2a_etapa": "flujo DC con angulos (KVL) + redespacho + deslastre",
            "sigma_carga": SIGMA_CARGA, "p_falla_gen": P_FALLA_GEN, "voll": VOLL,
            "c_ov": C_OV, "w_build": W_BUILD})
    return fs


def barrido(lista_S, lista_K, csv_path, motores=("cpsat", "SCIP")):
    previas = []
    if os.path.exists(csv_path):                    # ACUMULA, NO PISA
        with open(csv_path) as f:
            previas = list(csv.DictReader(f))
        print("barrido previo: %d filas — se agregan a estas" % len(previas))

    cont = {m: {"probaron": 0, "reloj": 0, "memoria": 0} for m in motores}
    frontera = {m: None for m in motores}
    intentados = 0
    nuevas = []
    vivos = list(motores)
    for S in lista_S:
        for K in lista_K:
            if not vivos:
                break
            intentados += 1
            p = un_punto(K, S, motores=tuple(vivos))
            nuevas.extend(filas_de(p, vivos))
            for mot in list(vivos):
                r = p.get(mot, {})
                if r.get("corte") == "memoria":
                    cont[mot]["memoria"] += 1
                elif r.get("status") == "OPTIMAL":
                    cont[mot]["probaron"] += 1
                else:
                    cont[mot]["reloj"] += 1
                    if frontera[mot] is None:
                        frontera[mot] = {"K": K, "S": S, "status": r.get("status"),
                                         "segundos": r.get("segundos"), "valor": r.get("valor"),
                                         "cota": r.get("cota"),
                                         "brecha_pct": r.get("brecha_pct"),
                                         "n_variables": r.get("n_variables"),
                                         "n_restricciones": r.get("n_restricciones")}
                        print("  FRONTERA de %s: K=%d S=%d -> %s en %.1fs"
                              % (mot, K, S, r.get("status"), r.get("segundos") or -1))
                        vivos.remove(mot)   # se corta ESE motor; el otro sigue
            with open(csv_path, "w", newline="") as f:   # escribe tras CADA punto
                w = csv.DictWriter(f, fieldnames=CAMPOS)
                w.writeheader()
                for fl in previas + nuevas:
                    w.writerow({k: fl.get(k) for k in CAMPOS})
        if not vivos:
            break

    return {"frontera": frontera,
            "denominador": {"pares_intentados": intentados,
                            "grilla_completa_pares": len(lista_S) * len(lista_K),
                            "grilla_S": lista_S, "grilla_K": lista_K, "reloj_s": RELOJ_S,
                            "por_motor": cont},
            "filas_nuevas": len(nuevas)}


# ------------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pruebas", action="store_true")
    ap.add_argument("--barrido", action="store_true")
    ap.add_argument("--informe", nargs=2, type=int, metavar=("K", "S"))
    ap.add_argument("--fisica", type=int, default=None,
                    help="corre solo la prueba de fisica (prueba 1) al K indicado")
    ap.add_argument("--pruebas-q", action="store_true",
                    help="pruebas Q1 (el QUBO tiene el mismo optimo que el MILP) y Q3 (un "
                         "escenario extremo mueve los coeficientes)")
    ap.add_argument("--ensayo", action="store_true",
                    help="corrida de ensayo sobre una instancia chica ANTES de gastar")
    ap.add_argument("--cuantico", nargs=2, type=int, metavar=("K", "S"),
                    help="la corrida: brazo cuantico contra SCIP en el mismo punto")
    ap.add_argument("--arbitro", nargs=2, type=int, metavar=("K", "S"),
                    help="optimo REAL por enumeracion de las C(K,k_budget) primeras etapas")
    ap.add_argument("--cuantico-ref", type=int, default=None, metavar="S",
                    help="segundo S de referencia (donde SCIP SI prueba el optimo)")
    ap.add_argument("--q-capas", type=int, default=None)
    ap.add_argument("--q-pasos", type=int, default=None)
    ap.add_argument("--q-disparos", type=int, default=None)
    ap.add_argument("--q-reloj", type=float, default=None)
    ap.add_argument("--csv", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "barrido_eon_estocastico.csv"))
    ap.add_argument("--json", default=None)
    ap.add_argument("--S", default="1,5,20,50,100,250,500")
    ap.add_argument("--K", default="10,14,20")
    ap.add_argument("--motores", default="cpsat,SCIP")
    a = ap.parse_args()

    entorno = {"python": platform.python_version(), "numpy": np.__version__, "red": GRID,
               "semilla": SEMILLA, "k_budget": K_BUDGET, "reloj_s": RELOJ_S, "C_OV": C_OV,
               "VOLL": VOLL, "W_BUILD": W_BUILD, "sigma_carga": SIGMA_CARGA,
               "p_falla_gen": P_FALLA_GEN, "falla_max": FALLA_MAX, "theta_max": THETA_MAX,
               "cp_dtheta": CP_DTHETA, "cp_mw": CP_MW, "cp_tol_u": CP_TOL_U}
    print(json.dumps(entorno, ensure_ascii=False))
    motores = tuple(a.motores.split(","))

    salida = {"entorno": entorno}
    if a.informe:
        salida["informe"] = un_punto(a.informe[0], a.informe[1], motores=motores)
    if a.fisica:
        salida["fisica_K%d" % a.fisica] = prueba_fisica(a.fisica)
    if a.pruebas:
        salida["pruebas"] = pruebas()
        print("\n" + json.dumps(salida["pruebas"]["veredicto"], indent=1, ensure_ascii=False))
    if a.ensayo:
        # CLAUDE.md §5 ter: modo informe contra datos reales antes de gastar. Instancia
        # chica de verdad (K=6, S=3, presupuesto minusculo): si algo esta mal cableado,
        # revienta aqui en un minuto y no a los 40.
        print("\n=== ENSAYO — instancia chica, antes de gastar ===")
        salida["ensayo"] = {}
        r_ens, qb_ens, _, _, _ = corrida_cuantica(
            6, 3, reloj_s=60, capas=2, pasos=15, disparos=200, reloj_cuantico=60)
        salida["ensayo"]["corrida"] = r_ens

    if a.pruebas_q:
        print("\n=== PRUEBA Q1 — S=1, K chico: el optimo del QUBO == el optimo del MILP ===")
        salida["prueba_q1"] = prueba_q1()
        print("\n=== PRUEBA Q3 — un escenario extremo mueve los coeficientes del QUBO ===")
        salida["prueba_q3"] = prueba_q3()

    if a.arbitro:
        salida["arbitro_K%d_S%d" % tuple(a.arbitro)] = corrida_arbitro(*a.arbitro)

    if a.cuantico:
        Kq, Sq = a.cuantico
        r_grande, qb_grande, red_q, costo_q, cache_q = corrida_cuantica(
            Kq, Sq, capas=a.q_capas, pasos=a.q_pasos, disparos=a.q_disparos,
            reloj_cuantico=a.q_reloj)
        salida["cuantico_S%d" % Sq] = r_grande
        print("\n=== PRUEBA Q2 — el circuito NO crece con S ===")
        esc1 = generar_escenarios(red_q, 1)
        qb1 = construir_qubo(red_q, esc1, costo_q, verboso=True)
        salida["prueba_q2"] = prueba_q2(qb1, qb_grande, red_q, esc1,
                                        generar_escenarios(red_q, Sq), costo_q,
                                        capas=a.q_capas)
        if a.cuantico_ref:
            r_ref, _, _, _, _ = corrida_cuantica(
                Kq, a.cuantico_ref, capas=a.q_capas, pasos=a.q_pasos,
                disparos=a.q_disparos, reloj_cuantico=a.q_reloj)
            salida["cuantico_S%d" % a.cuantico_ref] = r_ref

    if a.barrido:
        salida["barrido"] = barrido([int(s) for s in a.S.split(",")],
                                    [int(k) for k in a.K.split(",")], a.csv, motores)
        print("\n" + json.dumps(salida["barrido"]["denominador"], indent=1, ensure_ascii=False))
        print(json.dumps(salida["barrido"]["frontera"], indent=1, ensure_ascii=False))
    if a.json:
        json.dump(salida, open(a.json, "w"), indent=1, ensure_ascii=False, default=str)
        print("\nescrito %s" % a.json)
