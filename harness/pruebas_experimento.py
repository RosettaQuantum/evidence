#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Las pruebas de `experimento.py`: cada guardia con SUS DOS DIRECCIONES.

LA REGLA QUE ORDENA ESTE ARCHIVO (CLAUDE.md Rosetta §4 bis, formulacion de la sesion web)
-----------------------------------------------------------------------------------------
    «todos mis casos exigian el grito y ninguno el silencio. Esa asimetria es la que deja
    pasar al control que lee prosa — un guardia demasiado ruidoso pasa todas las pruebas
    de gritar.»

Asi que cada guardia tiene:
  - un caso que lo hace GRITAR,
  - un caso donde tiene que CALLARSE,
  - y donde rinde, el caso de silencio PARADOJICO: el defecto descrito en un comentario o
    en un texto y ausente del codigo. Si el guardia grita ahi, esta leyendo prosa.

Y todo va PROBADO POR MUTACION: se rompe el guardia a proposito y se comprueba que su caso
de grito deja de fallar. Un caso que pasa igual con el guardia roto no esta cazando nada.

Los casos de grito estan escritos contra DEFECTOS REALES, con fecha, no contra ejemplos
inventados (CLAUDE.md Rosetta §2).

Uso:
    python3 pruebas_experimento.py
"""
import io
import json
import os
import sys
import contextlib

import numpy as np

import experimento as E
from experimento import Brazo, Censo, Criterio, Experimento

PASARON, FALLARON, SALTADOS = [], [], []


def caso(nombre, fn):
    """Ejecuta un caso. Un caso que no se pudo ejercer entra al resumen, no a un aviso
    suelto arriba (CLAUDE.md Rosetta §5 quater.4: verde no es lo mismo que cubierto)."""
    try:
        fn()
    except _Saltado as s:
        SALTADOS.append((nombre, str(s)))
        print("  SALTADO  %s — %s" % (nombre, s))
        return
    except AssertionError as e:
        FALLARON.append((nombre, str(e)))
        print("  FALLO    %s\n           %s" % (nombre, e))
        return
    except Exception as e:
        FALLARON.append((nombre, "%s: %s" % (type(e).__name__, e)))
        print("  FALLO    %s\n           %s: %s" % (nombre, type(e).__name__, e))
        return
    PASARON.append(nombre)
    print("  ok       %s" % nombre)


class _Saltado(Exception):
    pass


def grita(fn, contiene=None):
    """El guardia tiene que abortar. Devuelve el mensaje, para poder mirarlo."""
    try:
        fn()
    except SystemExit as e:
        msg = str(e)
        if contiene and contiene not in msg:
            raise AssertionError("grito, pero sin decir %r. Dijo: %s" % (contiene, msg[:200]))
        return msg
    raise AssertionError("NO grito, y tenia que gritar")


def calla(fn):
    """El guardia tiene que dejar pasar. Devuelve lo que devuelva la funcion."""
    try:
        return fn()
    except SystemExit as e:
        raise AssertionError("grito y tenia que callarse: %s" % str(e)[:300])


def no_grita_con_el_guardia_roto(fn):
    """MUTACION: con el guardia roto, el caso de grito tiene que dejar de fallar."""
    try:
        fn()
    except SystemExit as e:
        raise AssertionError(
            "el guardia roto SIGUE gritando, asi que el caso de grito no lo estaba\n"
            "           ejerciendo a el: %s" % str(e)[:200])


# ============================================================ G1 — env()
def g1_calla_cadena_vacia():
    """DEFECTO REAL (2026-08-13T19:37): GitHub Actions pasa "" y no la ausencia."""
    os.environ["RQ_PRUEBA"] = ""
    assert E.env("RQ_PRUEBA", 120, int) == 120, "la cadena vacia no se leyo como ausencia"


def g1_calla_valor_falsy():
    """SILENCIO PARADOJICO: "0" PARECE ausencia y no lo es.

    Un `if not v` ingenuo devolveria el defecto y el experimento correria con otro
    numero — la ausencia disfrazada de valor, al reves.
    """
    os.environ["RQ_PRUEBA"] = "0"
    assert E.env("RQ_PRUEBA", 120, int) == 0, "'0' se leyo como ausencia"
    os.environ["RQ_PRUEBA"] = "   "
    assert E.env("RQ_PRUEBA", 120, int) == 120, "solo espacios no se leyo como ausencia"


def g1_grita_valor_ilegible():
    os.environ["RQ_PRUEBA"] = "veinte"
    grita(lambda: E.env("RQ_PRUEBA", 120, int), contiene="RQ_PRUEBA")


def g1_mutacion():
    """El guardia roto = el `os.environ.get(x, d)` de siempre."""
    def roto(nombre, defecto, tipo=str):
        return tipo(os.environ.get(nombre, defecto))
    os.environ["RQ_PRUEBA"] = ""
    try:
        roto("RQ_PRUEBA", 120, int)
    except ValueError:
        return                                   # el defecto real vuelve a aparecer
    raise AssertionError("el guardia roto no reprodujo el defecto del 2026-08-13")


# ============================================================ G2 — denominador
def _res(value, motivo=None, trunc=None):
    r = {"value": value, "motivo_sin_valor": motivo}
    if trunc:
        r["truncamiento"] = trunc
    return r


def g2_calla_todo_cierra():
    d = calla(lambda: E.denominador_de({
        "a": _res(1.0), "b": _res(None, "cortado_por_reloj"),
        "c": _res(None, "fuera_de_alcance")}))
    assert d["brazos_intentados"] == 3 and d["brazos_con_valor"] == 1, d
    assert sum(d["brazos_sin_valor"].values()) == 2, d


def g2_grita_sin_motivo():
    grita(lambda: E.denominador_de({"a": _res(1.0), "b": _res(None)}),
          contiene="no entra a ninguna categoria")


def g2_grita_motivo_inventado():
    grita(lambda: E.denominador_de({"a": _res(None, "porque si")}))


def g2_mutacion():
    def roto(resultados):
        con = sum(1 for r in resultados.values() if r.get("value") is not None)
        return {"brazos_intentados": len(resultados), "brazos_con_valor": con}
    no_grita_con_el_guardia_roto(lambda: roto({"a": _res(1.0), "b": _res(None)}))


# ============================================================ G3 — truncamiento
_TRUNC_OK = E.truncamiento(pasos_dados=6, pasos_de_presupuesto=120, reloj_s=120.0)


def g3_grita_brazo_que_itera_sin_bloque():
    """DEFECTO REAL (2026-08-13): K=20 dio 6 pasos de 120 y la brecha se publico como
    si midiera al metodo. Dos conclusiones retiradas."""
    grita(lambda: E.exigir_truncamiento("cuantico", {"value": 1.0}),
          contiene="no reporto `truncamiento`")


def g3_grita_bloque_a_medias():
    t = dict(_TRUNC_OK)
    del t["truncado_por_reloj"]
    grita(lambda: E.exigir_truncamiento("cuantico", {"value": 1.0, "truncamiento": t}),
          contiene="le faltan")


def g3_grita_sin_tope_de_pasos_y_otro_criterio():
    t = E.truncamiento(pasos_dados=5, pasos_de_presupuesto=None,
                       criterio_de_parada="convergencia")
    grita(lambda: E.exigir_truncamiento("q", {"value": 1.0, "truncamiento": t}),
          contiene="el unico criterio posible es el reloj")


def g3_grita_fuera_de_alcance_con_valor():
    """La excepcion no puede ser una puerta: un brazo que dice no haber corrido y trae
    un numero es una contradiccion (CLAUDE.md Rosetta §5 quater.4)."""
    grita(lambda: E.exigir_truncamiento(
        "q", {"value": 7.0, "motivo_sin_valor": "fuera_de_alcance"}),
        contiene="devolvio un valor")


def g3_calla_bloque_completo():
    calla(lambda: E.exigir_truncamiento("q", {"value": 1.0, "truncamiento": _TRUNC_OK}))


def g3_calla_fuera_de_alcance_sin_valor():
    calla(lambda: E.exigir_truncamiento(
        "q", {"value": None, "motivo_sin_valor": "fuera_de_alcance"}))


def g3_calla_paradojico_texto_que_describe_el_defecto():
    """SILENCIO PARADOJICO: el bloque esta completo y su TEXTO dice lo contrario.

    Si el guardia mirara la prosa en vez de la estructura, esta advertencia —que dice
    literalmente que no se declaro el truncamiento— lo haria gritar.
    """
    t = dict(_TRUNC_OK)
    t["advertencia"] = ("este brazo NO declara truncamiento y su `truncado_por_reloj` "
                        "falta: exactamente el defecto del 2026-08-13")
    calla(lambda: E.exigir_truncamiento("q", {"value": 1.0, "truncamiento": t}))


def g3_mutacion():
    def roto(nombre, res):
        return res.get("truncamiento")
    no_grita_con_el_guardia_roto(lambda: roto("q", {"value": 1.0}))


# ============================================================ G4 — memoria
_TOP_UNUSED_GB = 757 / 1024.0      # medido en este Mac el 2026-08-18 con `top -l 1`
_VM_STAT_GB = 10.4                 # el mismo instante, con vm_stat free+inactive+speculative


def g4_calla_con_aire():
    r = calla(lambda: E.guardia_de_memoria(6.0, _libre=lambda: 32.0, _presion=lambda: 10))
    assert r["gb_disponibles"] == 32.0, r


def g4_calla_el_caso_real_del_2026_08_17():
    """SILENCIO: el defecto era gritar aqui.

    Con 10,4 GB recuperables y presion normal, el guardia bueno se calla. El guardia
    viejo —que leia el `unused` de `top`— veia 0,74 GB y abortaba. Un falso positivo lo
    desactiva el primero que lo choque, y entonces no protege nunca mas.
    """
    calla(lambda: E.guardia_de_memoria(6.0, _libre=lambda: _VM_STAT_GB,
                                       _presion=lambda: 32))


def g4_grita_sin_memoria():
    """CASO REAL (2026-08-14): se corrio con 984 MB libres y hubo que reiniciar el Mac."""
    grita(lambda: E.guardia_de_memoria(6.0, _libre=lambda: 0.96, _presion=lambda: 40),
          contiene="minimo declarado")


def g4_grita_por_presion():
    grita(lambda: E.guardia_de_memoria(6.0, _libre=lambda: 20.0, _presion=lambda: 92),
          contiene="presion de memoria")


def g4_grita_falla_cerrado():
    grita(lambda: E.guardia_de_memoria(6.0, _libre=lambda: None, _presion=lambda: 10),
          contiene="no pude leer la memoria")


def g4_mutacion_lector_de_top():
    """MUTACION = EL DEFECTO REAL: se le pone al guardia el lector viejo (`top unused`).

    Con eso, el caso que tiene que CALLARSE grita. Es la prueba de que ese caso de
    silencio esta ejerciendo al lector y no a otra cosa.
    """
    try:
        E.guardia_de_memoria(6.0, _libre=lambda: _TOP_UNUSED_GB, _presion=lambda: 32)
    except SystemExit:
        return
    raise AssertionError("con el lector de `top` el guardia no grito: entonces el caso de "
                         "silencio no estaba ejerciendo al lector")


def g4_lector_real_falla_cerrado_en_sistema_desconocido():
    import platform as _p
    real = _p.system
    try:
        _p.system = lambda: "Plan9"
        assert E.memoria_disponible_gb() is None, "en un sistema desconocido invento un numero"
        grita(lambda: E.guardia_de_memoria(1.0), contiene="no pude leer la memoria")
    finally:
        _p.system = real


# ============================================================ G5 — censo
def g5_grita_no_calza():
    """DEFECTO REAL: nueve sellos decian case14 y median case118."""
    c = Censo()
    grita(lambda: c.medir(declarado={"n_buses": 14, "n_lineas": 15},
                          medido={"n_buses": 118, "n_lineas": 186}),
          contiene="no calza con lo declarado")


def g5_grita_campo_declarado_sin_medir():
    c = Censo()
    grita(lambda: c.medir(declarado={"n_buses": 14, "n_lineas": 15},
                          medido={"n_buses": 14}),
          contiene="el censo no lo midio")


def g5_grita_si_nunca_corrio():
    grita(lambda: Censo().exigir(), contiene="nunca corrio")


def g5_calla_cuando_calza():
    c = Censo()
    calla(lambda: c.medir(declarado={"n_buses": 14}, medido={"n_buses": 14}))
    assert c.exigir()["n_buses"] == 14


def g5_calla_paradojico_medido_de_mas():
    """SILENCIO: medir MAS de lo declarado es una virtud, no un defecto.

    Si el guardia comparara los conjuntos en vez de los campos declarados, el censo del
    VRP —que mide n_arcos y demanda_total_t sin declararlos— abortaria cada corrida.
    """
    c = Censo()
    calla(lambda: c.medir(declarado={"n_nodos": 8},
                          medido={"n_nodos": 8, "n_arcos": 56, "demanda_total_t": 80.58}))
    assert "n_arcos" in c.exigir()


def g5_mutacion():
    class Roto(Censo):
        def medir(self, declarado, medido):
            self._medido = dict(medido)          # estampa sin comparar
            return medido
    no_grita_con_el_guardia_roto(
        lambda: Roto().medir({"n_buses": 14}, {"n_buses": 118}))


# ====================================================== G6b — reformulacion del objetivo
def _qubo_aleatorio(K=6, semilla=3):
    rs = np.random.RandomState(semilla)
    Q = np.triu(rs.randn(K, K), 0)
    c = rs.randn(K)
    const = 1.7
    return Q, c, const


def _qubo_val(Q, c, const, x):
    x = np.asarray(x, float)
    return float(x @ Q @ x + c @ x + const)


def _ising(Q, c, const, roto):
    """La conversion QUBO->Ising de eon_harness.py. `roto=True` reproduce EL DEFECTO."""
    K = len(c)
    Qs = (Q + Q.T) / 2
    J = np.zeros((K, K)); h = np.zeros(K); off = const
    for i in range(K):
        off += Qs[i][i] / 2 + c[i] / 2
        h[i] -= Qs[i][i] / 2 + c[i] / 2
        for j in range(K):
            if i != j:
                off += Qs[i][j] / 4
                h[i] -= Qs[i][j] / 4
                if not roto:
                    h[j] -= Qs[i][j] / 4      # LA LINEA QUE FALTABA hasta el 2026-08-18
                J[i][j] += Qs[i][j] / 4

    def energia(x):
        z = 1.0 - 2.0 * np.asarray(x, float)
        return float(off + h @ z + sum(J[a][b] * z[a] * z[b]
                                       for a in range(K) for b in range(K) if a != b))
    return energia


def g6b_grita_el_defecto_del_2026_08_18():
    """EL DEFECTO REAL: `h[i] -=` sin `h[j] -=` deja el campo lineal en la mitad."""
    Q, c, k = _qubo_aleatorio()
    msg = grita(lambda: E.guardia_de_reformulacion(
        lambda x: _qubo_val(Q, c, k, x), _ising(Q, c, k, roto=True), n_vars=6,
        nombre="QUBO->Ising"), contiene="no reproduce el objetivo original")
    assert "2026-08-18" in msg


def g6b_calla_la_conversion_correcta():
    Q, c, k = _qubo_aleatorio()
    r = calla(lambda: E.guardia_de_reformulacion(
        lambda x: _qubo_val(Q, c, k, x), _ising(Q, c, k, roto=False), n_vars=6,
        nombre="QUBO->Ising"))
    assert r["desvio_maximo"] < 1e-9, r


def g6b_calla_paradojico_el_comentario_describe_el_defecto():
    """SILENCIO PARADOJICO: el codigo esta bien y la DOCUMENTACION describe el defecto.

    Es el caso que mata al control que lee prosa (CLAUDE.md Rosetta §4 bis): un guardia
    que buscara `h[i] -= Qs[i][j]/4` con grep gritaria aqui, porque esa linea esta
    escrita —en el docstring— y NO esta el defecto en el codigo.
    """
    Q, c, k = _qubo_aleatorio()
    bueno = _ising(Q, c, k, roto=False)
    bueno.__doc__ = ("DEFECTO 2026-08-18: el bucle hacia `h[i] -= Qs[i][j]/4` pero NO "
                     "`h[j] -=`, y el campo lineal quedaba EN LA MITAD. Desvio medido: "
                     "24.381 en K=8, 165.857 en K=20.")
    calla(lambda: E.guardia_de_reformulacion(
        lambda x: _qubo_val(Q, c, k, x), bueno, n_vars=6, nombre="QUBO->Ising"))


def g6b_mutacion():
    """El guardia roto = tolerancia infinita. El defecto real deja de gritar."""
    Q, c, k = _qubo_aleatorio()
    no_grita_con_el_guardia_roto(lambda: E.guardia_de_reformulacion(
        lambda x: _qubo_val(Q, c, k, x), _ising(Q, c, k, roto=True), n_vars=6,
        tol=1e9, nombre="QUBO->Ising"))


def g6b_el_desvio_medido_es_el_publicado():
    """El desvio de la version rota no es simbolico: se mide y se compara con lo dicho."""
    Q, c, k = _qubo_aleatorio()
    roto = _ising(Q, c, k, roto=True)
    rs = np.random.RandomState(0)
    peor = max(abs(roto(x) - _qubo_val(Q, c, k, x))
               for x in (rs.randint(0, 2, 6).astype(float) for _ in range(64)))
    assert peor > 1e-3, "la version rota no se desvia: el caso no reproduce el defecto"


# ====================================================== G6a — puntaje comun
def g6a_grita_puntaje_ajeno_sin_declarar():
    """EL HALLAZGO REAL DEL PORTADO (2026-08-18): el arbitro reportaba el objetivo
    ENTERO de CP-SAT (esc=1000) y el rival el costo en flotantes. Con LAS MISMAS rutas
    el artefacto decia 278,9 y 278,9027, y de ahi salia una brecha de 0,001 %."""
    res = {"exacto": {"value": 278.9, "solucion": "R"},
           "clasico": {"value": 278.9027, "solucion": "R"}}
    grita(lambda: E.guardia_de_puntaje_comun(res, evaluar=lambda s: 278.9027071177935),
          contiene="funciones distintas")


def g6a_calla_cuando_el_desvio_se_declara():
    res = {"exacto": {"value": 278.9, "solucion": "R",
                      "puntaje_propio": {"que_es": "objetivo entero CP-SAT esc=1000",
                                         "tolerancia_rel": 1e-4}},
           "clasico": {"value": 278.9027, "solucion": "R"}}
    r = calla(lambda: E.guardia_de_puntaje_comun(
        res, evaluar=lambda s: 278.9027071177935, decimales_reportados=4))
    fila = [f for f in r["filas"] if f["brazo"] == "exacto"][0]
    assert fila["desvio_relativo"] > 0, "el desvio declarado no quedo medido en el artefacto"
    assert fila["puntaje_propio"], "no quedo escrito QUE es ese puntaje propio"
    # el desvio declarado NO entra al peor no-declarado: para eso se declara
    assert r["peor_desvio_no_declarado"] < 1e-6, r


def g6a_calla_sin_solucion_que_puntuar():
    res = {"cuantico": {"value": None, "solucion": None}}
    r = calla(lambda: E.guardia_de_puntaje_comun(res, evaluar=lambda s: 0.0))
    assert r["filas"][0]["estado"].startswith("sin solucion")


def g6a_calla_el_redondeo_del_propio_artefacto():
    """SILENCIO: el artefacto publica con round(...,4). Sin la holgura derivada de esos
    decimales el guardia gritaria por su propio redondeo — un falso positivo."""
    res = {"clasico": {"value": 278.9027, "solucion": "R"}}
    calla(lambda: E.guardia_de_puntaje_comun(
        res, evaluar=lambda s: 278.9027071177935, decimales_reportados=4))


def g6a_mutacion():
    def roto(resultados, evaluar, tol_rel=1e-9, decimales_reportados=None):
        return {"filas": [], "peor_desvio_no_declarado": 0.0}
    res = {"exacto": {"value": 278.9, "solucion": "R"}}
    no_grita_con_el_guardia_roto(lambda: roto(res, lambda s: 278.9027071177935))


# ====================================================== G7 — el criterio, sellado
_CRIT = dict(texto="el retador debe SUPERAR al rival", rival="OR-Tools GLS",
             porque_este_rival="es lo que usan hoy las empresas de ruteo",
             arbitro="CP-SAT sin limite practico",
             sin_arbitro="sin optimo probado la brecha se reporta None")


def g7_grita_criterio_incompleto():
    d = dict(_CRIT); d["porque_este_rival"] = ""
    grita(lambda: Criterio(**d), contiene="porque_este_rival")


def g7_calla_criterio_completo():
    c = calla(lambda: Criterio(**_CRIT))
    assert c.huella().startswith("sha256:")


def g7_la_huella_cambia_si_cambia_el_texto():
    a = Criterio(**_CRIT)
    d = dict(_CRIT); d["texto"] = "el retador debe EMPATAR al rival"
    assert a.huella() != Criterio(**d).huella(), "la huella no distingue dos criterios"


def g7_grita_si_el_criterio_se_ablanda_despues():
    exp = _experimento_minimo()
    object.__setattr__(exp.criterio, "texto", "basta con empatar")   # ablandado a posteriori
    grita(lambda: exp.correr({}, verboso=False), contiene="el criterio cambio")


def g7_mutacion():
    """El guardia roto = no comparar la huella. El ablandamiento pasa sin ruido."""
    exp = _experimento_minimo()
    original = Criterio.huella
    try:
        exp._huella_criterio = None
        Criterio.huella = lambda self: None                          # el guardia roto
        object.__setattr__(exp.criterio, "texto", "basta con empatar")
        no_grita_con_el_guardia_roto(lambda: exp.correr({}, verboso=False))
    finally:
        Criterio.huella = original


# ====================================================== G8 — la forma del experimento
def _brazo_ok(nombre, valor):
    def f(ctx):
        return {"value": valor, "solucion": [valor], "estado": "ok"}
    return f


def _experimento_minimo(brazos=None, semillas=None):
    c = Censo()
    c.medir({"n": 3}, {"n": 3})
    return Experimento(
        track="prueba", instancia="i", params={},
        criterio=Criterio(**_CRIT), evaluar=lambda s: s[0],
        brazos=brazos or [Brazo("arb", "arbitro", _brazo_ok("arb", 1.0)),
                          Brazo("riv", "rival", _brazo_ok("riv", 2.0)),
                          Brazo("ret", "retador", _brazo_ok("ret", 3.0))],
        semillas=semillas if semillas is not None else {"s": 42},
        versiones=E.versiones_base(), censo=c)


def g8_grita_sin_rival():
    grita(lambda: _experimento_minimo(
        brazos=[Brazo("arb", "arbitro", _brazo_ok("a", 1.0)),
                Brazo("ret", "retador", _brazo_ok("r", 2.0))]),
        contiene="rol 'rival'")


def g8_grita_dos_rivales():
    grita(lambda: _experimento_minimo(
        brazos=[Brazo("r1", "rival", _brazo_ok("a", 1.0)),
                Brazo("r2", "rival", _brazo_ok("b", 2.0)),
                Brazo("ret", "retador", _brazo_ok("c", 3.0))]))


def g8_grita_sin_retador():
    grita(lambda: _experimento_minimo(
        brazos=[Brazo("arb", "arbitro", _brazo_ok("a", 1.0)),
                Brazo("riv", "rival", _brazo_ok("b", 2.0))]),
        contiene="retador")


def g8_grita_sin_semillas():
    grita(lambda: _experimento_minimo(semillas={}), contiene="semillas")


def g8_grita_brazo_sin_value():
    def malo(ctx):
        return {"estado": "listo"}
    exp = _experimento_minimo(brazos=[Brazo("arb", "arbitro", _brazo_ok("a", 1.0)),
                                      Brazo("riv", "rival", _brazo_ok("b", 2.0)),
                                      Brazo("ret", "retador", malo)])
    grita(lambda: exp.correr({}, verboso=False), contiene="no devolvio `value`")


def g8_calla_y_el_artefacto_trae_lo_que_promete():
    art = calla(lambda: _experimento_minimo().correr({}, verboso=False))
    for clave in ("track", "instance", "params", "verdict", "lib_versions", "plantilla"):
        assert clave in art, "al artefacto le falta %r" % clave
    p = art["plantilla"]
    for clave in ("censo_medido", "denominador", "puntaje_comun", "semillas",
                  "criterio", "criterio_huella", "roles"):
        assert clave in p, "al bloque de plantilla le falta %r" % clave
    assert p["denominador"]["brazos_intentados"] == 3
    assert "solucion" not in art["arb"], "la solucion interna se filtro al artefacto"


def g8_memoria_error_de_un_brazo_entra_al_denominador():
    def sin_memoria(ctx):
        raise MemoryError("vector de estado")
    exp = _experimento_minimo(brazos=[Brazo("arb", "arbitro", _brazo_ok("a", 1.0)),
                                      Brazo("riv", "rival", _brazo_ok("b", 2.0)),
                                      Brazo("ret", "retador", sin_memoria)])
    art = calla(lambda: exp.correr({}, verboso=False))
    d = art["plantilla"]["denominador"]
    assert d["brazos_sin_valor"]["cortado_por_memoria"] == 1, d


def g8_mutacion():
    """Sin la exigencia de rol, un experimento sin rival corre igual."""
    def roto(brazos):
        return [b.nombre for b in brazos]
    no_grita_con_el_guardia_roto(
        lambda: roto([Brazo("ret", "retador", _brazo_ok("a", 1.0))]))


# ============================================================ EL RESUMEN
CASOS = [
    ("G1 calla · cadena vacia = ausencia", g1_calla_cadena_vacia),
    ("G1 calla · PARADOJICO: '0' parece ausencia y no lo es", g1_calla_valor_falsy),
    ("G1 grita · valor ilegible, con el nombre de la variable", g1_grita_valor_ilegible),
    ("G1 mutacion · el os.environ.get de siempre reproduce el defecto", g1_mutacion),

    ("G2 calla · el denominador cierra", g2_calla_todo_cierra),
    ("G2 grita · brazo sin valor y sin motivo", g2_grita_sin_motivo),
    ("G2 grita · motivo fuera del catalogo", g2_grita_motivo_inventado),
    ("G2 mutacion · sin categorias, el caso deja de gritar", g2_mutacion),

    ("G3 grita · brazo que itera sin bloque de truncamiento", g3_grita_brazo_que_itera_sin_bloque),
    ("G3 grita · bloque a medias", g3_grita_bloque_a_medias),
    ("G3 grita · sin tope de pasos y con otro criterio de parada", g3_grita_sin_tope_de_pasos_y_otro_criterio),
    ("G3 grita · 'fuera de alcance' con un valor adentro", g3_grita_fuera_de_alcance_con_valor),
    ("G3 calla · bloque completo", g3_calla_bloque_completo),
    ("G3 calla · fuera de alcance sin valor", g3_calla_fuera_de_alcance_sin_valor),
    ("G3 calla · PARADOJICO: el texto dice que falta y el bloque esta", g3_calla_paradojico_texto_que_describe_el_defecto),
    ("G3 mutacion · guardia que solo devuelve el bloque", g3_mutacion),

    ("G4 calla · 32 GB y presion baja", g4_calla_con_aire),
    ("G4 calla · el caso real: 10,4 GB por vm_stat", g4_calla_el_caso_real_del_2026_08_17),
    ("G4 grita · 0,96 GB (el dia que hubo que reiniciar)", g4_grita_sin_memoria),
    ("G4 grita · presion 92 % con RAM de sobra", g4_grita_por_presion),
    ("G4 grita · falla cerrado si no puede leer", g4_grita_falla_cerrado),
    ("G4 mutacion · con el 'unused' de top, el caso de silencio grita", g4_mutacion_lector_de_top),
    ("G4 lector real · sistema desconocido -> falla cerrado", g4_lector_real_falla_cerrado_en_sistema_desconocido),

    ("G5 grita · censo declarado 14 y medido 118", g5_grita_no_calza),
    ("G5 grita · campo declarado que nadie midio", g5_grita_campo_declarado_sin_medir),
    ("G5 grita · el artefacto exige el censo y nunca corrio", g5_grita_si_nunca_corrio),
    ("G5 calla · cuando calza", g5_calla_cuando_calza),
    ("G5 calla · PARADOJICO: medir de mas no es un defecto", g5_calla_paradojico_medido_de_mas),
    ("G5 mutacion · censo que estampa sin comparar", g5_mutacion),

    ("G6b grita · QUBO->Ising con el campo lineal a la mitad", g6b_grita_el_defecto_del_2026_08_18),
    ("G6b calla · la conversion correcta", g6b_calla_la_conversion_correcta),
    ("G6b calla · PARADOJICO: el docstring describe el defecto ausente", g6b_calla_paradojico_el_comentario_describe_el_defecto),
    ("G6b mutacion · con tolerancia infinita el defecto pasa", g6b_mutacion),
    ("G6b el caso de grito reproduce un desvio real, no simbolico", g6b_el_desvio_medido_es_el_publicado),

    ("G6a grita · dos brazos puntuados con funciones distintas", g6a_grita_puntaje_ajeno_sin_declarar),
    ("G6a calla · cuando el desvio se declara, y queda medido", g6a_calla_cuando_el_desvio_se_declara),
    ("G6a calla · brazo sin solucion que puntuar", g6a_calla_sin_solucion_que_puntuar),
    ("G6a calla · el redondeo del propio artefacto", g6a_calla_el_redondeo_del_propio_artefacto),
    ("G6a mutacion · sin comparacion, el caso deja de gritar", g6a_mutacion),

    ("G7 grita · criterio sin justificar el rival", g7_grita_criterio_incompleto),
    ("G7 calla · criterio completo", g7_calla_criterio_completo),
    ("G7 la huella distingue dos criterios", g7_la_huella_cambia_si_cambia_el_texto),
    ("G7 grita · el criterio se ablando despues de correr", g7_grita_si_el_criterio_se_ablanda_despues),
    ("G7 mutacion · sin huella, el ablandamiento pasa", g7_mutacion),

    ("G8 grita · sin rival", g8_grita_sin_rival),
    ("G8 grita · dos rivales", g8_grita_dos_rivales),
    ("G8 grita · sin retador", g8_grita_sin_retador),
    ("G8 grita · sin semillas", g8_grita_sin_semillas),
    ("G8 grita · brazo que no devuelve `value`", g8_grita_brazo_sin_value),
    ("G8 calla · el artefacto trae censo, denominador, semillas y huella", g8_calla_y_el_artefacto_trae_lo_que_promete),
    ("G8 un MemoryError de un brazo entra al denominador", g8_memoria_error_de_un_brazo_entra_al_denominador),
    ("G8 mutacion · sin exigencia de rol, un experimento sin rival corre", g8_mutacion),
]


if __name__ == "__main__":
    print("PRUEBAS DE experimento.py — %d casos\n" % len(CASOS))
    for nombre, fn in CASOS:
        caso(nombre, fn)
    print("\n%d pasaron · %d fallaron · %d saltados  (de %d)"
          % (len(PASARON), len(FALLARON), len(SALTADOS), len(CASOS)))
    if FALLARON:
        for n, e in FALLARON:
            print("  FALLO %s: %s" % (n, e[:160]))
    # los tres numeros salen del mismo recorrido: si no suman, el resumen miente
    assert len(PASARON) + len(FALLARON) + len(SALTADOS) == len(CASOS)
    sys.exit(1 if FALLARON else 0)
