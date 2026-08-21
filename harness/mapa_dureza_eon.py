#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EL MAPA: donde el problema de E.ON empieza a ser duro DE VERDAD, como funcion de K.

POR QUE EXISTE ESTE ARCHIVO — UN ERROR NUESTRO, MEDIDO
------------------------------------------------------
Declaramos haber encontrado la «instancia dificil» de E.ON en K=10, S=250 porque SCIP no
lograba PROBAR optimalidad en 900 s. Eso NO la vuelve dificil: con K=10 y presupuesto 5 hay
C(10,5) = 252 planes de primera etapa, y enumerarlos todos toma ~18 minutos (1103,94 s,
medido, `arbitro_enumeracion_K10_S250.json`). El problema no es duro — derrota la ESTRATEGIA
DE PRUEBA de un solucionador, que es otra cosa.

Peor: SCIP no fue reproducible sobre esa misma instancia. Una corrida dio el optimo (brecha
1,93 %) y otra dio 11,11 % — y la segunda estaba a 8,8 % del optimo REAL, que la enumeracion
conoce. Con una sola corrida eso no se ve.

E.ON no pide una instancia: pide **«classically hard problem instances ... with differing
variable counts»** — una FAMILIA. Asi que esto dibuja tres curvas sobre el mismo eje
K = variables binarias de primera etapa:

  1. COSTO DE ENUMERAR   C(K,k) y el tiempo real de evaluarlos con la funcion exacta.
                         Es el techo de honestidad: por debajo de el, ningun metodo
                         sofisticado se justifica.
  2. TIEMPO DEL SOLUCIONADOR hasta DEMOSTRAR el optimo, y desde donde deja de lograrlo.
  3. ALCANCE CUANTICO    hasta que K cabe en simulacion y en hardware real.

El cruce entre 1 y 2 define donde empieza lo duro. La distancia entre eso y 3 es la brecha
real del campo.

EL CRITERIO DE «DURO», ESCRITO ANTES DE MEDIR (no se toca despues)
------------------------------------------------------------------
    duro(K)  <=>  (A) la enumeracion exacta de los C(K,k) planes NO cabe en el presupuesto
                      operativo T_OP en UN nucleo,   Y
                  (B) el solucionador NO devuelve OPTIMAL dentro de T_OP en NINGUNA de las
                      tres semillas.
Las dos condiciones. Una sola no alcanza: (B) sin (A) es exactamente el error que este
archivo existe para corregir — un solucionador derrotado sobre un problema que se enumera.

Y una tercera categoria, porque el dato de hoy la exige:
    fragil(K)  <=>  (A) y ademas el solucionador prueba en ALGUNAS semillas y en otras no.
Un punto fragil no es duro, pero tampoco es resuelto: es un punto donde la respuesta depende
de la suerte, y eso se declara en vez de promediarse.

**El arbitro se pierde exactamente donde empieza lo duro**, y no es coincidencia: es la
misma definicion leida al reves. Sin enumeracion y sin prueba de optimalidad no queda nadie
que sepa el optimo, y desde ahi todo lo que se diga son COTAS, no brechas.

LO QUE SE FIJA Y POR QUE (declarado, porque decide como leer todo lo demas)
--------------------------------------------------------------------------
S = 100 escenarios, FIJO en todo el barrido. Razon: es el S mas grande del CSV donde SCIP
    SI prueba optimalidad en K=10 (135,71 s, fila 15 de `barrido_eon_estocastico.csv`). Con
    S=250 el punto K=10 ya no prueba, y entonces la transicion que se mida al crecer K seria
    atribuible a S y no a K. El eje de este archivo es K; S es otro eje y ya esta barrido.

k = K // 2, o sea la RAZON 1/2 de la instancia original (5 de 10). Se mantiene la razon, como
    pide el encargo. Ademas es la peor razon posible para la enumeracion: C(K,k) es maximo en
    k=K/2. Si se preguntara «¿desde donde deja de poder enumerarse?», usar el maximo es la
    respuesta honesta; cualquier otra razon da una curva 1 mas barata.

T_OP = 900 s. Es ELECCION NUESTRA — el presupuesto operativo que declaramos que un
    planificador tolera — y es el mismo 900 s de la medicion anterior, para que las dos sean
    comparables. Se aplica IGUAL a la enumeracion y al solucionador: un metodo no puede
    tener mas presupuesto que el otro.

SEMILLAS = tres, distintas, por punto. Regla dura del encargo y nacio del dato de hoy: una
    corrida optima y dos a 11 %. La reproducibilidad se MIDE.

EL GUARDIA DE MEMORIA, Y LA DECISION QUE HUBO QUE TOMAR (declarada, no escondida)
--------------------------------------------------------------------------------
`banco_de_ensayo.guardia_de_memoria()` exige >= 6 GB y lee «unused» de `top`. Al arrancar
este trabajo esa cifra era **1,16 GB** y habria abortado la sesion entera. Pero `top`
«unused» cuenta SOLO paginas libres: `vm_stat` en la misma maquina y el mismo minuto daba
**8,99 GB** entre libres + inactivas + especulativas + purgables, que es lo que un proceso
nuevo puede tomar de verdad, y `memory_pressure` reportaba 50 % libre.

Asi que este archivo usa el guardia EQUIVALENTE que el encargo permite, con la definicion
declarada, y **ademas dos cosas que el original no tiene**:
  - los DOS numeros se registran en cada punto (`ram_top_unused_gb`, `ram_recuperable_gb`),
    para que nadie tenga que creerle a la definicion elegida;
  - un TOPE DURO por proceso hijo: el padre vigila el RSS del hijo y lo mata pasando
    `TOPE_RSS_GB`. Eso protege contra el fallo real —una maquina que se cae— mejor que un
    umbral de RAM libre, porque actua sobre el proceso que crece y no sobre el que arranca.
Falla cerrado en los dos sentidos: si NO se puede leer la memoria por cualquiera de las dos
vias, no se corre.

QUE NO HACE ESTE ARCHIVO
------------------------
No toca `eon_harness.py` (otro actor depende de su hash): el tope de 22 candidatos se sube
por entorno con `RQ_TOPE_CAND`, que el propio harness ya lee. No corre CP-SAT: el criterio
declarado del encargo anterior lo incluia, pero CP-SAT discretiza la segunda etapa continua
y una frontera producida por el redondeo mediria nuestra discretizacion. Queda fuera de
alcance y se dice.

Uso:
    python3 mapa_dureza_eon.py                 # el barrido completo, un proceso por K
    python3 mapa_dureza_eon.py --punto K       # UN tamaño (es lo que lanza el padre)
    python3 mapa_dureza_eon.py --ks 10 14 18   # solo estos tamaños
"""
import argparse
import json
import math
import os
import random
import re
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "mapa_dureza")

# ------------------------------------------------------------------ PARAMETROS DECLARADOS
S_FIJO = int(os.environ.get("RQ_MAPA_S", 100))
T_OP = float(os.environ.get("RQ_MAPA_TOP", 900))       # presupuesto operativo, s
RAZON_BUDGET = 0.5                                      # k = round(RAZON * K) -> K//2
SEMILLAS = [42, 1337, 2718]
KS = [10, 14, 18, 22, 26, 30, 34, 40]
MUESTRA_PLANES = 25          # planes al azar para medir el costo por plan cuando no se enumera
MIN_LIBRE_GB = 6.0
TOPE_RSS_GB = 5.0            # el padre mata al hijo que pase de aqui
TOPE_HIJO_S = 3.0 * T_OP + 3600.0   # reloj de pared del hijo entero, con holgura


def k_budget_de(K):
    return int(round(RAZON_BUDGET * K))


# ------------------------------------------------------------------- EL GUARDIA DE MEMORIA
def ram_top_unused_gb():
    """«unused» de top: SOLO paginas libres. Es la definicion de banco_de_ensayo.py."""
    o = subprocess.run(["top", "-l", "1", "-n", "0"], capture_output=True, text=True).stdout
    m = re.search(r"PhysMem: .*?(\d+)([GM]) unused", o)
    if not m:
        return None
    return int(m.group(1)) * (1.0 if m.group(2) == "G" else 1 / 1024.0)


def ram_recuperable_gb():
    """Lo que un proceso nuevo puede tomar: libres + inactivas + especulativas + purgables."""
    o = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    m = re.search(r"page size of (\d+)", o)
    if not m:
        return None
    pg = int(m.group(1))
    d = {}
    for ln in o.splitlines()[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            try:
                d[k.strip()] = int(v.strip().rstrip("."))
            except ValueError:
                pass
    faltan = [k for k in ("Pages free", "Pages inactive", "Pages speculative") if k not in d]
    if faltan:
        return None
    tot = (d["Pages free"] + d["Pages inactive"] + d["Pages speculative"]
           + d.get("Pages purgeable", 0))
    return tot * pg / 2 ** 30


def guardia_de_memoria():
    """Falla cerrado. Lee LAS DOS definiciones y exige que la recuperable llegue al minimo.

    Se registra tambien la de `top` para que la eleccion quede a la vista y no haya que
    creerle a este archivo (CLAUDE.md Rosetta §1 quater: toda cifra viaja con su metodo).
    """
    top_u = ram_top_unused_gb()
    rec = ram_recuperable_gb()
    if rec is None or top_u is None:
        raise SystemExit(
            "ABORTA: no pude leer la memoria por %s. Sin ese dato no se corre."
            % (("vm_stat" if rec is None else "") + ("/top" if top_u is None else "")))
    if rec < MIN_LIBRE_GB:
        raise SystemExit(
            "ABORTA: %.2f GB recuperables y el minimo es %.1f (top unused: %.2f GB).\n"
            "  Cierra aplicaciones y vuelve a intentar." % (rec, MIN_LIBRE_GB, top_u))
    return {"ram_top_unused_gb": round(top_u, 2), "ram_recuperable_gb": round(rec, 2),
            "minimo_exigido_gb": MIN_LIBRE_GB}


# ==========================================================================================
# EL HIJO: UN SOLO K, EN SU PROPIO PROCESO
# ==========================================================================================
def medir_punto(K):
    k = k_budget_de(K)
    # El entorno se fija ANTES de importar eon_estocastico: su K_BUDGET se lee al importar,
    # y RQ_TOPE_CAND lo lee el propio eon_harness.py al ejecutarse (por eso el tope de 22
    # sube sin tocar ese archivo, que tiene otro dueño).
    os.environ["RQ_BUDGET"] = str(k)
    os.environ["RQ_TOPE_CAND"] = str(max(64, K))
    os.environ["RQ_RELOJ"] = str(T_OP)
    sys.path.insert(0, AQUI)
    import numpy as np
    import eon_estocastico as eon

    if eon.K_BUDGET != k:
        raise SystemExit("ABORTA: K_BUDGET quedo en %d y se pidio %d." % (eon.K_BUDGET, k))

    mem = guardia_de_memoria()
    out = {"K": K, "k_budget": k, "razon_budget": RAZON_BUDGET, "S": S_FIJO,
           "T_OP_s": T_OP, "red": eon.GRID, "combinaciones": math.comb(K, k),
           "memoria": mem, "reglas": {"semillas": SEMILLAS, "solucionador": "SCIP (MILP)"},
           "t_inicio": time.strftime("%Y-%m-%dT%H:%M:%S")}
    print("=== K=%d  k=%d  C(K,k)=%s  S=%d  T_OP=%.0fs ==="
          % (K, k, f"{math.comb(K, k):,}", S_FIJO, T_OP), flush=True)
    print("    memoria: %.2f GB recuperables (top unused %.2f GB)"
          % (mem["ram_recuperable_gb"], mem["ram_top_unused_gb"]), flush=True)

    # ------------------------------------------------------------------ la instancia
    t0 = time.time()
    H = eon.cargar_harness(K, tope_fuerza_bruta=0)
    red = eon.extraer_red(H, K)
    costo = list(np.asarray(H["cost"], float))
    escen = eon.generar_escenarios(red, S_FIJO)
    out["armado_instancia_s"] = round(time.time() - t0, 2)
    out["K_real_del_harness"] = int(H["K"])
    if int(H["K"]) != K:
        raise SystemExit("ABORTA: el harness produjo K=%d y se pidieron %d. El tope de "
                         "candidatos no subio." % (H["K"], K))
    out["n_lineas"] = red["n_lineas"]
    out["n_trafos"] = red["n_trafos"]

    # ---------------------------------------------------- CURVA 1: el costo de enumerar
    # Primero el costo POR PLAN, medido sobre una muestra al azar de planes de cardinalidad
    # k. Sirve para dos cosas: proyectar la enumeracion cuando ya no cabe (y decir «ya no se
    # enumera» con un numero detras en vez de con una impresion), y decidir si conviene
    # correrla entera. La muestra se sortea con semilla fija para que sea repetible.
    cache = {}
    rng = random.Random(20260817 + K)
    universo = math.comb(K, k)
    n_muestra = min(MUESTRA_PLANES, universo)
    muestra = set()
    while len(muestra) < n_muestra:
        muestra.add(tuple(sorted(rng.sample(range(K), k))))
    t0 = time.time()
    for sel in muestra:
        eon.evaluar_plan_exacto(red, escen, costo, list(sel), cache)
    t_muestra = time.time() - t0
    t_plan = t_muestra / n_muestra
    proy_s = t_plan * universo
    out["enumeracion"] = {
        "planes_muestreados": n_muestra, "denominador": universo,
        "segundos_muestra": round(t_muestra, 2), "segundos_por_plan": round(t_plan, 4),
        "segundos_proyectados_1_nucleo": round(proy_s, 1),
        "cabe_en_T_OP_proyectado": bool(proy_s <= T_OP)}
    print("    costo por plan: %.3f s (%d planes de muestra) -> enumerar los %s = %.0f s "
          "proyectados en 1 nucleo" % (t_plan, n_muestra, f"{universo:,}", proy_s), flush=True)

    if proy_s <= T_OP:
        t0 = time.time()
        r = eon.enumerar_exacto(red, escen, costo, K, k, cache=cache, verboso=True)
        seg = time.time() - t0
        if r["combinaciones"] != r["esperadas"]:
            raise SystemExit("ABORTA: se evaluaron %d planes y C(%d,%d)=%d. Un arbitro que "
                             "no recorrio todo el conjunto no es un arbitro."
                             % (r["combinaciones"], K, k, r["esperadas"]))
        out["enumeracion"].update({
            "corrio": True, "segundos_reales": round(seg, 2),
            "planes_evaluados": r["combinaciones"], "esperados": r["esperadas"],
            "optimo_real": r["valor"], "plan_optimo": r["plan"],
            "peor_valor": r["peor_valor"],
            "cabe_en_T_OP_medido": bool(seg <= T_OP),
            "top10": r["top10"]})
        out["arbitro"] = {"hay": True, "fuente": "enumeracion exacta",
                          "optimo": r["valor"], "plan": r["plan"]}
        print("    ENUMERACION COMPLETA: optimo real = %.4f  plan %s  (%d/%d planes, %.1fs)"
              % (r["valor"], r["plan"], r["combinaciones"], r["esperadas"], seg), flush=True)
    else:
        out["enumeracion"].update({
            "corrio": False,
            "motivo": "ya no se enumera: %s planes x %.3f s/plan = %.0f s proyectados, "
                      "%.1fx el presupuesto operativo de %.0f s"
                      % (f"{universo:,}", t_plan, proy_s, proy_s / T_OP, T_OP),
            "planes_evaluados": n_muestra, "esperados": universo})
        out["arbitro"] = {"hay": False, "fuente": None, "optimo": None, "plan": None}
        print("    YA NO SE ENUMERA: %s" % out["enumeracion"]["motivo"], flush=True)

    # ------------------------------------------ CURVA 2: el solucionador, 3 semillas
    corridas = []
    for sem in SEMILLAS:
        t0 = time.time()
        m, x = eon.modelo_milp(red, escen, costo, solver_id="SCIP")
        armado = time.time() - t0
        # FALLA CERRADO: si el solucionador no acepta la semilla, la dispersion que se mida
        # no seria entre semillas y decirlo asi seria mentira. Se comprueba que el setter
        # rechaza un nombre invalido (lo hace: devuelve False), asi que un True significa
        # que el parametro entro.
        ok = m.SetSolverSpecificParametersAsString(
            "randomization/randomseedshift = %d\n"
            "randomization/permutationseed = %d\n"
            "randomization/lpseed = %d" % (sem, sem, sem))
        if not ok:
            raise SystemExit("ABORTA: SCIP no acepto la semilla %d. Sin semilla efectiva la "
                             "dispersion medida no seria entre semillas." % sem)
        try:
            r = eon.resolver_milp(m, x, T_OP, red)
        except MemoryError:
            corridas.append({"semilla": sem, "status": "MEMORIA", "segundos": None})
            print("    semilla %-5d MEMORIA" % sem, flush=True)
            continue
        r["semilla"] = sem
        r["armado_s"] = round(armado, 2)
        r["brecha_vs_cota_pct"] = eon.brecha_pct(r["valor"], r["cota"])
        if out["arbitro"]["hay"]:
            opt = out["arbitro"]["optimo"]
            r["brecha_vs_optimo_real_pct"] = round(100.0 * (r["valor"] - opt) / abs(opt), 4)
            r["plan_es_el_optimo"] = bool(
                sorted(i for i, b in enumerate(r["x"]) if b) == sorted(out["arbitro"]["plan"]))
        else:
            r["brecha_vs_optimo_real_pct"] = None
            r["plan_es_el_optimo"] = None
        corridas.append(r)
        print("    semilla %-5d %-9s %7.1fs  valor=%-16s cota=%-16s brecha_cota=%-8s "
              "brecha_optimo=%s"
              % (sem, r["status"], r["segundos"], r["valor"], r["cota"],
                 r["brecha_vs_cota_pct"], r["brecha_vs_optimo_real_pct"]), flush=True)

    probaron = [c for c in corridas if c.get("status") == "OPTIMAL"]
    tiempos = [c["segundos"] for c in corridas if c.get("segundos") is not None]
    brechas = [c.get("brecha_vs_cota_pct") for c in corridas
               if c.get("brecha_vs_cota_pct") is not None]
    valores = [c.get("valor") for c in corridas if c.get("valor") is not None]
    out["solucionador"] = {
        "motor": "SCIP (via ortools pywraplp)", "corridas": corridas,
        "semillas_corridas": len(corridas), "semillas_pedidas": len(SEMILLAS),
        "n_OPTIMAL": len(probaron), "denominador": len(SEMILLAS),
        "prueba_siempre": len(probaron) == len(SEMILLAS),
        "prueba_nunca": len(probaron) == 0,
        "segundos_min": min(tiempos) if tiempos else None,
        "segundos_max": max(tiempos) if tiempos else None,
        "brecha_cota_min_pct": min(brechas) if brechas else None,
        "brecha_cota_max_pct": max(brechas) if brechas else None,
        "valor_min": min(valores) if valores else None,
        "valor_max": max(valores) if valores else None,
        "dispersion_valor_pct": (round(100.0 * (max(valores) - min(valores)) / abs(min(valores)), 4)
                                 if len(valores) > 1 and min(valores) else None),
        "n_variables": corridas[0].get("n_variables") if corridas else None,
        "n_restricciones": corridas[0].get("n_restricciones") if corridas else None}

    # ---------------------------------------------------- LA PRUEBA: enumeracion == SCIP
    # En el K mas chico donde todavia se enumera, el optimo de la enumeracion y el del
    # solucionador tienen que ser EL MISMO numero. Si no calzan, el modelo esta mal y el
    # mapa no vale. Se reportan los dos, siempre.
    if out["arbitro"]["hay"] and probaron:
        opt_enum = out["arbitro"]["optimo"]
        opt_scip = min(c["valor"] for c in probaron)
        rel = abs(opt_enum - opt_scip) / max(1e-9, abs(opt_enum))
        out["prueba_enum_vs_solucionador"] = {
            "optimo_enumeracion": opt_enum, "optimo_solucionador": opt_scip,
            "diferencia_relativa": rel, "pasa": bool(rel < 1e-6),
            "semillas_OPTIMAL": [c["semilla"] for c in probaron]}
        print("    PRUEBA enumeracion=%.6f  SCIP=%.6f  dif rel=%.3e  ->  %s"
              % (opt_enum, opt_scip, rel, "PASA" if rel < 1e-6 else "FALLA"), flush=True)
    else:
        out["prueba_enum_vs_solucionador"] = {
            "pasa": None, "motivo": ("sin enumeracion" if not out["arbitro"]["hay"]
                                     else "ninguna semilla probo optimalidad")}

    # ------------------------------------------------- CURVA 3: el alcance cuantico
    # El circuito necesita K qubits (uno por candidata de primera etapa). Lo que NO es
    # gratis y casi nunca se dice es el precio de entrada: armar el QUBO cuesta
    # 1 + K + K(K-1)/2 evaluaciones EXACTAS, o sea el mismo LP por escenario que usa la
    # enumeracion. Se proyecta con el costo por plan MEDIDO arriba, y es una COTA SUPERIOR:
    # los planes del QUBO tienen cardinalidad 0, 1 y 2, y son mas baratos que los de
    # cardinalidad k que se midieron.
    n_eval_qubo = 1 + K + K * (K - 1) // 2
    out["cuantico"] = {
        "qubits_necesarios": K,
        "vector_estado_gb": round(16 * 2 ** K / 2 ** 30, 6),
        "evaluaciones_para_armar_el_qubo": n_eval_qubo,
        "segundos_qubo_proyectados_cota_superior": round(n_eval_qubo * t_plan, 1),
        "nota": "proyeccion con el costo por plan medido en este mismo punto; cota superior "
                "porque los planes del QUBO son de cardinalidad 0,1,2 y cuestan menos que "
                "los de cardinalidad k."}

    # ------------------------------------------------------------------- el veredicto
    A = not out["enumeracion"].get("cabe_en_T_OP_medido",
                                   out["enumeracion"]["cabe_en_T_OP_proyectado"])
    B = out["solucionador"]["prueba_nunca"]
    fragil = A and (0 < out["solucionador"]["n_OPTIMAL"] < len(SEMILLAS))
    out["veredicto"] = {
        "A_no_se_enumera_en_T_OP": bool(A),
        "B_no_se_demuestra_en_T_OP_en_ninguna_semilla": bool(B),
        "duro": bool(A and B), "fragil": bool(fragil),
        "arbitro_disponible": bool(out["arbitro"]["hay"] or len(probaron) > 0),
        "criterio": "duro = A y B (las dos). fragil = A y el solucionador prueba en algunas "
                    "semillas y en otras no."}
    out["t_fin"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    print("    VEREDICTO K=%d: A=%s B=%s -> %s%s"
          % (K, A, B, "DURO" if (A and B) else "no duro",
             " (FRAGIL)" if fragil else ""), flush=True)
    return out


# ==========================================================================================
# EL PADRE: UN PROCESO POR TAMAÑO, CON TOPE DE RSS
# ==========================================================================================
def rss_gb(pid):
    o = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True)
    try:
        return int(o.stdout.strip()) / 1048576.0
    except ValueError:
        return None


def correr_hijo(K):
    """Un tamaño, en un proceso aparte, vigilado. Si crece de mas, se lo mata y se declara."""
    destino = os.path.join(SALIDA, "punto_K%02d.json" % K)
    log = os.path.join(SALIDA, "punto_K%02d.log" % K)
    with open(log, "w") as fl:
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--punto", str(K)],
                             stdout=fl, stderr=subprocess.STDOUT)
        t0 = time.time()
        pico = 0.0
        while p.poll() is None:
            time.sleep(2.0)
            r = rss_gb(p.pid)
            if r is not None:
                pico = max(pico, r)
                if r > TOPE_RSS_GB:
                    p.kill()
                    return {"K": K, "estado": "MEMORIA",
                            "motivo": "el hijo paso de %.1f GB de RSS (pico %.2f) y se lo "
                                      "mato" % (TOPE_RSS_GB, r), "pico_rss_gb": round(pico, 2)}
            if time.time() - t0 > TOPE_HIJO_S:
                p.kill()
                return {"K": K, "estado": "RELOJ",
                        "motivo": "el hijo paso de %.0f s de pared" % TOPE_HIJO_S,
                        "pico_rss_gb": round(pico, 2)}
    if p.returncode != 0 or not os.path.exists(destino):
        cola = open(log).read().strip().splitlines()[-6:]
        return {"K": K, "estado": "MURIO", "codigo": p.returncode,
                "motivo": " | ".join(cola)[-400:], "pico_rss_gb": round(pico, 2)}
    d = json.load(open(destino))
    d["pico_rss_gb"] = round(pico, 2)
    d["estado"] = "ok"
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--punto", type=int, default=None)
    ap.add_argument("--ks", type=int, nargs="*", default=None)
    a = ap.parse_args()
    os.makedirs(SALIDA, exist_ok=True)

    if a.punto is not None:
        d = medir_punto(a.punto)
        with open(os.path.join(SALIDA, "punto_K%02d.json" % a.punto), "w") as f:
            json.dump(d, f, indent=1, default=float)
        return

    ks = a.ks or KS
    mem = guardia_de_memoria()
    print("MAPA DE DUREZA — S=%d  T_OP=%.0fs  razon k/K=%.2f  semillas=%s"
          % (S_FIJO, T_OP, RAZON_BUDGET, SEMILLAS))
    print("memoria al arrancar: %.2f GB recuperables (top unused %.2f GB), minimo %.1f\n"
          % (mem["ram_recuperable_gb"], mem["ram_top_unused_gb"], MIN_LIBRE_GB))
    filas = []
    for K in ks:
        t0 = time.time()
        d = correr_hijo(K)
        d["pared_s"] = round(time.time() - t0, 1)
        filas.append(d)
        with open(os.path.join(SALIDA, "MAPA.json"), "w") as f:
            json.dump({"parametros": {"S": S_FIJO, "T_OP_s": T_OP,
                                      "razon_budget": RAZON_BUDGET, "semillas": SEMILLAS,
                                      "ks_pedidos": ks},
                       "puntos": filas, "denominador": len(ks),
                       "completados": sum(1 for x in filas if x.get("estado") == "ok")},
                      f, indent=1, default=float)
        print("K=%-3d %-8s  %.0fs de pared  (pico RSS %.2f GB)"
              % (K, d.get("estado"), d["pared_s"], d.get("pico_rss_gb", 0)), flush=True)
    print("\nescrito en %s" % SALIDA)


if __name__ == "__main__":
    main()
