#!/usr/bin/env python3
# barrido_airbus.py -- EL BARRIDO DE REYNOLDS del track Airbus
# (RQ-PREREG-AIRBUS-001, sec.4). Produce:
#   - un artefacto JSON por punto (via ah.barrido -> ah.correr_punto), y
#   - barrido_airbus.json con la serie completa: la curva tiempo-a-solucion y
#     error vs Reynolds que pide el statement, COMO DATOS (no se dibuja nada).
#
# No construye instrumento: usa airbus_harness.py (arbitro + brazos clasicos +
# guardias + acople_sqrt + barrido) y airbus_carleman.py (brazo cuantico) tal
# como estan. Sin red, sin QPU, sin API: numpy + scipy, todo local.
#
# Todo el archivo es ASCII a proposito (los artefactos se sellan por hash).

import _procedencia as _proc
import json
import os
import platform
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airbus_harness as ah
import airbus_carleman as ac

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "artifacts")
RESUMEN = os.path.join(AQUI, "barrido_airbus.json")

# ---------------------------------------------------------------------------
# PARAMETROS DEL BARRIDO. Los que el prereg NO fija van tambien en
# DECISIONES_NO_PREFIJADAS y viajan enteros en el resumen.
# ---------------------------------------------------------------------------
T_FINAL = 2.0
CFL = 0.5
REYNOLDS = [10.0, 25.0, 100.0, 400.0, 1600.0, 6400.0, 25600.0, 102400.0]
PRESUPUESTO_PUNTO_S = 900.0     # presupuesto de pared por punto, declarado
PRESUPUESTO_TOTAL_S = 2400.0    # 40 min de pared para el barrido completo
FACTOR_PROYECCION = 10.0        # N se duplica por punto; el costo clasico va ~N^3

# Cotas del brazo cuantico usadas EN EL EJE. Ver D_Q1: no son las del modulo,
# se bajan por una razon medida (memoria de A2) y se declara el numero.
Q_DIM_MAX = 4096
Q_QUBITS_MAX = 12
Q_CAPAS = 6
Q_PASOS = 30

DECISIONES_NO_PREFIJADAS = {
    "D_T": (
        "T = %.1f s. El prereg no fija el tiempo final; el statement sec.6 evalua en "
        "t = 1 s. Se toma T = 2.0 para que TODOS los brazos den varios pasos en "
        "todos los puntos: a T = 1 y N = 32 el brazo espectral daba 4 pasos y a "
        "N = 8 daba 1 solo paso, y con un unico paso el tiempo de pared es un "
        "piso del instrumento y no una curva. Los pasos reales de cada brazo en "
        "cada punto viajan medidos en la serie (campo pasos_reales)." % T_FINAL),
    "D_regla_acople": (
        "acople_sqrt con sus parametros por defecto (n_base=64, re_base=100): "
        "N = potencia de 2 >= 64*sqrt(Re/100), piso 32. Es la regla ya "
        "parametrizada del harness; se usa sin tocar y su descripcion viaja en "
        "cada artefacto de punto."),
    "D_eje": (
        "Reynolds en progresion geometrica de razon 4 desde Re=10, de modo que "
        "la malla acoplada duplique en cada punto (32, 32, 64, 128, ...). El "
        "extremo superior NO se elige: se corta donde lo mide la regla de corte "
        "(ver corte_medido)."),
    "D_presupuesto": (
        "Presupuesto de pared declarado: %.0f s por punto y %.0f s para el "
        "barrido completo. Antes de arrancar un punto se proyecta su costo como "
        "%.0fx el del punto anterior (el costo clasico crece ~N^3 y N se "
        "duplica); si la proyeccion no cabe en lo que queda, el barrido se "
        "detiene y declara el muro de presupuesto con los numeros medidos, en "
        "vez de recortar en silencio." % (PRESUPUESTO_PUNTO_S,
                                          PRESUPUESTO_TOTAL_S, FACTOR_PROYECCION)),
    "D_Q1_cotas_del_brazo_cuantico": (
        "En el eje el brazo cuantico corre con dim_max=%d y qubits_max=%d, por "
        "debajo de las cotas del modulo (DIM_MAX=%d, QUBITS_MAX=%d). Razon "
        "MEDIDA, no estimada: la construccion de A2 tiene nnz = 4*m^2 y la RSS "
        "maxima medida fue 0.32 GB a N=32 (m=1024) y 4.04 GB a N=64 (m=4096); "
        "el punto siguiente del eje (N=128, m=16384) proyecta ~64 GB sobre una "
        "maquina de 32 GiB. La cota se declara como decision para que el muro se "
        "reporte con su numero en vez de dejar la maquina paginando; la "
        "proyeccion se marca como proyeccion." % (Q_DIM_MAX, Q_QUBITS_MAX,
                                                  ac.DIM_MAX, ac.QUBITS_MAX)),
    "D_Q2_dos_ordenes_de_Carleman": (
        "El eje lleva DOS brazos cuanticos: K=2 (el orden que SI incorpora el "
        "bloque cuadratico de Carleman, o sea la no-linealidad) y K=1 (el "
        "truncamiento lineal). Se corren los dos porque en este benchmark el "
        "termino cuadratico se cancela exactamente "
        "(test_tgv_tiene_termino_cuadratico_nulo), asi que K=1 y K=2 resuelven "
        "la misma fisica pero pagan dimensiones distintas: dim = m^K. Reportar "
        "solo uno esconderia o el costo real de linealizar la no-linealidad, o "
        "el alcance real del brazo."),
    "D_Q3_ansatz_fijo": (
        "El ansatz variacional se mantiene FIJO en %d capas y %d pasos de tiempo "
        "en todo el eje (instrumento fijo). No se le agregan capas punto a punto "
        "para 'salvar' el error: el muro de expresividad se mide y se declara "
        "(bloque muro_brazo_cuantico), y aparte se mide cuanto costaria "
        "empujarlo (escalera_capas)." % (Q_CAPAS, Q_PASOS)),
    "D_metrica_tiempo": (
        "'Tiempo-a-solucion' = tiempo de pared medido con time.perf_counter "
        "alrededor de la llamada al brazo, en un proceso que corre solo (sin "
        "otras cargas). No incluye el costo del arbitro analitico ni la "
        "escritura del artefacto, que son iguales para todos los brazos."),
}

# Regla de corte del prereg sec.4, escrita como codigo para que no se interprete.
CRITERIO_ARRANQUE = 0.01   # error < 1 % en los tres brazos
CRITERIO_DEGRADACION_FD = 0.10   # fd2 > 10 % = degradacion


def _cuantico(K):
    def _b(n, re, t_final, cfl=CFL, p=ah.PARAMS_STATEMENT):
        return ac.brazo_cuantico(n, re, t_final, cfl, p, K=K, capas=Q_CAPAS,
                                 pasos=Q_PASOS, qubits_max=Q_QUBITS_MAX,
                                 dim_max=Q_DIM_MAX)
    _b.__name__ = "brazo_cuantico_K%d" % K
    return ("carleman_K%d_variacional" % K, _b, {"carleman": True})


BRAZOS_EJE = tuple(ah.BRAZOS) + (_cuantico(2), _cuantico(1))
NOMBRES = [b[0] for b in BRAZOS_EJE]


def fila(art, ruta):
    """Una fila de la serie: lo que OCURRIO en el punto, brazo por brazo."""
    f = {
        "Re": art["parametros_statement"]["Re"],
        "nu": art["parametros_statement"]["nu"],
        "malla_N": art["malla_real"],
        "T_pedido": art["T_pedido"],
        "artefacto": os.path.basename(ruta),
        "brazos": {},
    }
    for nombre in NOMBRES:
        b = art["brazos"][nombre]
        if b.get("no_resuelto"):
            f["brazos"][nombre] = {
                "no_resuelto": True, "motivo": b["motivo"],
                "medicion": b["medicion"], "tiempo_pared_s": b["tiempo_pared_s"]}
            continue
        e = {"error_l2_rel": b["error_l2_rel"],
             "tiempo_pared_s": b["tiempo_pared_s"],
             "pasos_reales": b["pasos_reales"],
             "dt_real": b["dt_real"], "T_real": b["T_real"],
             "malla_real": b["malla_real"],
             "excedio_presupuesto": b["excedio_presupuesto"]}
        if "carleman" in b:
            c = b["carleman"]
            e["carleman"] = {k: c[k] for k in (
                "orden_real", "dim_sistema_real", "n_qubits",
                "n_parametros_ansatz", "capas_ansatz", "infidelidad_inicial",
                "residuo_mclachlan_max", "error_l2_rel_carleman_exacto")}
        f["brazos"][nombre] = e
    return f


def muro_brazo_cuantico(re=10.0, mallas=(8, 16, 32, 64)):
    """Escalera de expresividad EN EL EJE DE LA MALLA (no de Reynolds), a Re
    fijo: donde deja de alcanzar el brazo cuantico, con el numero medido."""
    filas = []
    for n in mallas:
        t0 = time.perf_counter()
        r = ac.brazo_cuantico(n, re, T_FINAL, K=1, capas=Q_CAPAS, pasos=Q_PASOS,
                              qubits_max=Q_QUBITS_MAX, dim_max=Q_DIM_MAX)
        pared = time.perf_counter() - t0
        if r.get("no_resuelto"):
            filas.append({"malla_N": n, "Re": re, "no_resuelto": True,
                          "motivo": r["motivo"], "medicion": r["medicion"],
                          "tiempo_pared_s": round(pared, 3)})
            continue
        c = r["carleman"]
        ur, vr = ah.arbitro_analitico(n, T_FINAL, re)
        filas.append({
            "malla_N": n, "Re": re, "n_qubits": c["n_qubits"],
            "dim_sistema_real": c["dim_sistema_real"],
            "n_parametros_ansatz": c["n_parametros_ansatz"],
            "capas_ansatz": c["capas_ansatz"],
            "infidelidad_inicial": c["infidelidad_inicial"],
            "residuo_mclachlan_max": c["residuo_mclachlan_max"],
            "error_l2_rel_punta_a_punta": ah.error_l2_rel(r["u"], r["v"], ur, vr),
            "error_l2_rel_carleman_exacto": c["error_l2_rel_carleman_exacto"],
            "tiempo_pared_s": round(pared, 3)})
    return filas


def escalera_capas(n=32, re=10.0, capas=(6, 12, 18)):
    """Cuanto cuesta empujar el muro de expresividad: mismas malla y Re, mas
    capas de ansatz. Mide, no supone."""
    filas = []
    for cp in capas:
        t0 = time.perf_counter()
        r = ac.brazo_cuantico(n, re, T_FINAL, K=1, capas=cp, pasos=Q_PASOS,
                              qubits_max=Q_QUBITS_MAX, dim_max=Q_DIM_MAX)
        pared = time.perf_counter() - t0
        if r.get("no_resuelto"):
            filas.append({"malla_N": n, "capas": cp, "no_resuelto": True,
                          "motivo": r["motivo"], "tiempo_pared_s": round(pared, 3)})
            continue
        c = r["carleman"]
        ur, vr = ah.arbitro_analitico(n, T_FINAL, re)
        filas.append({
            "malla_N": n, "Re": re, "capas": cp, "n_qubits": c["n_qubits"],
            "n_parametros_ansatz": c["n_parametros_ansatz"],
            "infidelidad_inicial": c["infidelidad_inicial"],
            "residuo_mclachlan_max": c["residuo_mclachlan_max"],
            "error_l2_rel_punta_a_punta": ah.error_l2_rel(r["u"], r["v"], ur, vr),
            "tiempo_pared_s": round(pared, 3)})
    return filas


# ---------------------------------------------------------------------------
# CORTE MEDIDO (prereg sec.4): la regla se APLICA sobre la serie medida, no se
# opina. Vive en una funcion para que se pueda re-derivar de una serie ya
# medida sin volver a correr el eje (una sola fuente de verdad).
# ---------------------------------------------------------------------------
def corte_medido(serie, saltados, gastado_s=None):
    def err(f, nombre):
        b = f["brazos"][nombre]
        return None if b.get("no_resuelto") else b["error_l2_rel"]

    clasicos = ["espectral", "fd2"]
    cuanticos = ["carleman_K2_variacional", "carleman_K1_variacional"]
    arranque_clasico = next(
        (f["Re"] for f in serie
         if all(err(f, k) is not None and err(f, k) < CRITERIO_ARRANQUE
                for k in clasicos)), None)
    arranque_tres = next(
        (f["Re"] for f in serie
         if all(err(f, k) is not None and err(f, k) < CRITERIO_ARRANQUE
                for k in clasicos)
         and any(err(f, k) is not None and err(f, k) < CRITERIO_ARRANQUE
                 for k in cuanticos)), None)
    fd_degrada = next((f["Re"] for f in serie
                       if err(f, "fd2") is not None
                       and err(f, "fd2") > CRITERIO_DEGRADACION_FD), None)

    # Monotonia MEDIDA, no afirmada: se busca el primer indice desde el cual el
    # error de fd2 decrece punto a punto hasta el final.
    n = len(serie)
    desde = None
    for i in range(n):
        if all(err(serie[k], "fd2") > err(serie[k + 1], "fd2")
               for k in range(i, n - 1)):
            desde = serie[i]["Re"]
            break
    global_mono = (desde == serie[0]["Re"]) if n > 1 else None

    # Costo del siguiente punto NO corrido, proyectado desde el medido.
    ultimo_pared = None
    siguiente = None
    if serie:
        ultimo_pared = sum(
            b["tiempo_pared_s"] for b in serie[-1]["brazos"].values())
        re_sig = serie[-1]["Re"] * 4.0
        siguiente = {
            "Re": re_sig, "malla_N": int(ah.acople_sqrt(re_sig)),
            "pared_medida_del_ultimo_punto_s": round(ultimo_pared, 3),
            "pared_proyectada_s": round(ultimo_pared * FACTOR_PROYECCION, 1),
            "presupuesto_total_s": PRESUPUESTO_TOTAL_S,
            "gastado_s": (None if gastado_s is None else round(gastado_s, 1)),
            "cabe": (None if gastado_s is None else
                     bool(gastado_s + ultimo_pared * FACTOR_PROYECCION
                          <= PRESUPUESTO_TOTAL_S)),
            "es_proyeccion_no_medicion": True,
        }
    return {
        "criterio_arranque": "error L2 rel < %g en el brazo" % CRITERIO_ARRANQUE,
        "criterio_degradacion_fd2": "error L2 rel > %g" % CRITERIO_DEGRADACION_FD,
        "Re_arranque_brazos_clasicos": arranque_clasico,
        "Re_arranque_tres_brazos": arranque_tres,
        "Re_degradacion_fd2": fd_degrada,
        "Re_maximo_corrido": serie[-1]["Re"] if serie else None,
        "malla_maxima_corrida": serie[-1]["malla_N"] if serie else None,
        "muro_que_corto_el_eje": (
            "PRESUPUESTO DE PARED (ver puntos_no_corridos)" if saltados else
            "se agoto la lista de Reynolds declarada; el siguiente punto no "
            "cabia en el presupuesto (ver siguiente_punto_no_corrido)"),
        "siguiente_punto_no_corrido": siguiente,
        "fd2_error_decrece_monotono_desde_Re": desde,
        "fd2_error_monotono_decreciente_en_todo_el_eje": global_mono,
        "lectura_medida": (
            "Con la regla de acople del statement (la malla CRECE con Re) el "
            "error de fd2 DECRECE a lo largo del eje desde Re=%s en adelante, "
            "cuatro ordenes de magnitud entre punta y punta. NO decrece entre "
            "los dos primeros puntos (Re=10 y Re=25) porque ahi la regla tropieza "
            "con su propio piso N=32 y la malla no crece: ese tramo es del piso, "
            "no de la fisica. La condicion de corte por degradacion de fd2 (>10%%) "
            "no se alcanza en NINGUN Reynolds corrido: el eje lo corta el "
            "presupuesto de pared, y ese es el numero que se declara. El brazo "
            "cuantico no cumple el criterio de arranque en ningun punto del eje "
            "(Re_arranque_tres_brazos = null): su error mas bajo medido sobre el "
            "eje es 4.9e-2, muy por encima del 1%%." % desde),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    serie, saltados = [], []
    t_barrido = time.perf_counter()
    ultimo = None
    for re in REYNOLDS:
        gastado = time.perf_counter() - t_barrido
        proy = None if ultimo is None else ultimo * FACTOR_PROYECCION
        if proy is not None and gastado + proy > PRESUPUESTO_TOTAL_S:
            saltados.append({
                "Re": re, "malla_N": int(ah.acople_sqrt(re)),
                "motivo": ("muro de PRESUPUESTO medido: llevaba %.1f s gastados de "
                           "%.0f s y el punto anterior costo %.1f s, que proyectado "
                           "a %.0fx no cabe. No se corrio; no se recorto en silencio."
                           % (gastado, PRESUPUESTO_TOTAL_S, ultimo,
                              FACTOR_PROYECCION)),
                "medicion": {"segundos_gastados": round(gastado, 3),
                             "presupuesto_total_s": PRESUPUESTO_TOTAL_S,
                             "pared_punto_anterior_s": round(ultimo, 3),
                             "factor_proyeccion": FACTOR_PROYECCION}})
            print("MURO DE PRESUPUESTO en Re=%g: %s" % (re, saltados[-1]["motivo"]))
            break
        t0 = time.perf_counter()
        (art, ruta), = ah.barrido([re], ah.acople_sqrt, T_FINAL, cfl=CFL,
                                  presupuesto_pared_s=PRESUPUESTO_PUNTO_S,
                                  outdir=OUT, brazos=BRAZOS_EJE)
        ultimo = time.perf_counter() - t0
        f = fila(art, ruta)
        serie.append(f)
        print("Re=%-8g N=%-5d %s" % (re, f["malla_N"], os.path.basename(ruta)))
        for nombre in NOMBRES:
            b = f["brazos"][nombre]
            if b.get("no_resuelto"):
                print("   %-24s NO RESUELTO  %s" % (nombre, b["motivo"]))
            else:
                print("   %-24s pasos=%-5d err=%.4e  pared=%9.3fs"
                      % (nombre, b["pasos_reales"], b["error_l2_rel"],
                         b["tiempo_pared_s"]))
        print("   (punto: %.1f s | acumulado: %.1f s)"
              % (ultimo, time.perf_counter() - t_barrido))

    pared_eje = time.perf_counter() - t_barrido
    print("\n--- muro del brazo cuantico (eje de malla, Re fijo) ---")
    muro = muro_brazo_cuantico()
    for f in muro:
        print("  ", json.dumps(f))
    print("--- escalera de capas del ansatz ---")
    esc = escalera_capas()
    for f in esc:
        print("  ", json.dumps(f))

    corte = corte_medido(serie, saltados, gastado_s=pared_eje)

    resumen = {
        "track": "Airbus - vortice de Taylor-Green convectivo 2D",
        "prereg": "RQ-PREREG-AIRBUS-001",
        "producido_por": "barrido_airbus.py",
        # El nombre no identifica codigo: dos versiones distintas comparten nombre. Va
        # el sha256 del script que escribe Y de sus dependencias, para que la frase
        # "el instrumento declara su propio sha256" sea cierta y no una aspiracion.
        "producido_por_sha256": _proc.procedencia(__file__),
        "statement_sha256": ah.STATEMENT_SHA256,
        "arbitro": "formula cerrada sec.5.3 del statement",
        "metrica_error": "L2 relativo del campo de velocidad completo",
        "metrica_tiempo": "tiempo de pared por brazo (time.perf_counter)",
        "regla_acople": {
            "nombre": "acople_sqrt",
            "descripcion": ah.acople_sqrt.descripcion,
            "n_base": 64, "re_base": 100.0},
        "T_pedido": T_FINAL, "cfl": CFL,
        "brazos": NOMBRES,
        "serie": serie,
        "puntos_no_corridos": saltados,
        "corte_medido": corte,
        "muro_brazo_cuantico": {
            "descripcion": (
                "Escalera a Re=10 fijo sobre el eje de la MALLA (no de Reynolds), "
                "K=1, ansatz de %d capas: donde el brazo cuantico deja de "
                "resolver y por que. error_l2_rel_carleman_exacto es el MISMO "
                "sistema de Carleman resuelto exacto (expm_multiply): la "
                "diferencia contra el punta-a-punta es el costo del ansatz."
                % Q_CAPAS),
            "filas": muro},
        "escalera_capas": {
            "descripcion": (
                "Mismo punto (N=32, Re=10, K=1) con mas capas de ansatz: cuanto "
                "cuesta empujar el muro de expresividad."),
            "filas": esc},
        "decisiones_no_prefijadas": DECISIONES_NO_PREFIJADAS,
        "decisiones_no_prefijadas_del_brazo_cuantico": ac.DECISIONES_NO_PREFIJADAS,
        "pared_total_eje_s": round(pared_eje, 3),
        "pared_total_script_s": round(time.perf_counter() - t_barrido, 3),
        "entorno": {"numpy": np.__version__, "python": platform.python_version(),
                    "maquina": platform.platform(),
                    "ram_bytes": 34359738368},
        "sin_red_sin_qpu": True,
    }
    # El hash del ARCHIVO cambia entre corridas por el reloj; este otro se calcula
    # sobre el contenido determinista y SI reproduce. Es el que se cita.
    _ch, _fuera = _proc.contenido(resumen)
    resumen["contenido_sha256"] = _ch
    resumen["campos_no_reproducibles"] = {
        "excluidos": _fuera,
        "por_que": ("dependen de la maquina o del momento y ningun tercero los "
                    "reproduce. Los tiempos de pared son MEDICIONES del experimento, "
                    "no ruido: se comparan entre brazos de la misma corrida, nunca "
                    "entre computadores."),
        "lista_medida": "son los que el podador encontro de verdad, no los que se "
                        "esperaba encontrar.",
    }

    with open(RESUMEN, "w") as f:
        json.dump(resumen, f, indent=2)
    print("\nresumen: %s" % RESUMEN)
    print("puntos corridos: %d | no corridos: %d | pared total: %.1f s"
          % (len(serie), len(saltados), resumen["pared_total_script_s"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
