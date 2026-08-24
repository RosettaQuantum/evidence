#!/usr/bin/env python3
# airbus_harness.py — arbitro analitico + dos brazos clasicos del track Airbus
# (RQ-PREREG-AIRBUS-001). Esta es SOLO la mitad clasica del instrumento: el
# brazo cuantico lo monta la coordinacion encima de este mismo eje.
#
# Fuente de las formulas: Airbus-Challenge-Statement-vF.pdf, §5.2 y §5.3,
# sha256 recomputado COMPLETO el 2026-08-19 desde ~/Downloads (coincide con el
# ancla del prereg "4a2e084dd25d4934..."):
STATEMENT_SHA256 = "4a2e084dd25d49343c98475091eede479513779c4306e90260f9b9cf518f77c6"
#
# Guardias del prereg §5 — todas fallan cerrado (GuardiaError) y todas se
# prueban por mutacion en test_guardias.py (sin esas pruebas, no existen):
#   1. En t=0 el campo inicial reproduce la analitica a epsilon de maquina, o
#      aborta. La IC (§5.2) y la solucion exacta (§5.3 en t=0) se implementan
#      POR SEPARADO y la guardia exige que coincidan: un arbitro mal tecleado
#      no corre nada.
#   2. El artefacto declara lo que OCURRIO, no lo que se pidio (CLAUDE.md
#      §4 sexies): malla leida del shape del arreglo, pasos leidos del
#      contador del bucle, tiempos leidos del reloj. La guardia compara el
#      artefacto contra esos objetos reales antes de escribir nada.
#   3. Un nan o un campo vacio en cualquier brazo aborta la corrida entera —
#      la ausencia no viaja como valor (CLAUDE.md §5 quater).
#   4. El orden de truncamiento de Carleman y la dimension REAL del sistema
#      linealizado viajan declarados en el artefacto, y se verifican contra la
#      malla que OCURRIO: dim tiene que ser suma_{j=1..K} (N^2)^j con N leido
#      del shape del arreglo. Un brazo que reduce el problema en silencio (o
#      que declara un orden que no corrio) no puede pasar por aca.
#   5. Si un brazo NO puede resolver un punto (memoria, dimension, no
#      convergencia), el artefacto lo declara con el motivo MEDIDO. No se emite
#      un error silencioso ni un valor por defecto, y no puede declarar a la vez
#      "no resuelto" y un error numerico. Falla cerrado en los dos sentidos.
#
# Todo el archivo es ASCII a proposito: los artefactos de este proyecto se
# sellan por hash y un caracter invisible es indistinguible de uno medido.

import hashlib
import json
import os
import platform
import time
from datetime import datetime, timezone

import numpy as np


class GuardiaError(RuntimeError):
    """Una guardia del prereg §5 que se dispara: la corrida NO continua."""


# ---------------------------------------------------------------------------
# Parametros del statement (§6, tabla). Se leen de aqui, no se recuerdan.
# ---------------------------------------------------------------------------
PARAMS_STATEMENT = {
    "L": 2.0 * np.pi,   # "Domain Length (L) = 2*pi" — ver DECISION_DOMINIO
    "V0": 1.0,
    "Uc": 1.0,
    "Vc": 0.0,
    "rho": 1.0,
    "p0": 0.0,
}

# DECISION DECLARADA (el prereg no la fija; la coordinacion debe validarla):
# la tabla del statement llama L=2*pi "Domain Length", pero las formulas usan
# sin(x/L): con L=2*pi el periodo del campo es 2*pi*L, y un dominio de lado
# 2*pi NO es periodico para ese campo. Tomamos L=2*pi literal de la tabla y el
# dominio = UN PERIODO COMPLETO, lado D = 2*pi*L. Las dos lecturas posibles
# (L=2*pi, D=4*pi^2) y (L=1, D=2*pi) son el mismo problema adimensional con
# el mismo Re; esta elige la literal y lo declara en cada artefacto.
DECISION_DOMINIO = ("dominio periodico [0, 2*pi*L)^2 = un periodo completo del campo; "
                    "L=2*pi literal de la tabla §6 (la tabla y la formula sin(x/L) son "
                    "inconsistentes entre si; misma fisica adimensional en ambas lecturas)")


def nu_de_re(re, p=PARAMS_STATEMENT):
    # §6 del statement: nu = V0 * L / Re. Formula, no numero suelto.
    return p["V0"] * p["L"] / float(re)


def _malla(n, p=PARAMS_STATEMENT):
    d = 2.0 * np.pi * p["L"]
    h = d / n
    x = np.arange(n) * h
    xx, yy = np.meshgrid(x, x, indexing="ij")
    return xx, yy, h, d


# ---------------------------------------------------------------------------
# §5.2 — condicion inicial del statement, tecleada de la formula del PDF.
# Existe SEPARADA del arbitro a proposito: la guardia 1 compara ambas.
# ---------------------------------------------------------------------------
def ic_statement(n, p=PARAMS_STATEMENT):
    xx, yy, _, _ = _malla(n, p)
    u0 = p["Uc"] + p["V0"] * np.sin(xx / p["L"]) * np.cos(yy / p["L"])
    v0 = p["Vc"] - p["V0"] * np.cos(xx / p["L"]) * np.sin(yy / p["L"])
    return u0, v0


# ---------------------------------------------------------------------------
# §5.3 — EL ARBITRO: solucion analitica exacta, evaluable en cualquier malla
# y tiempo. Es una formula cerrada; sin arbitro aprendido ni numerico.
# ---------------------------------------------------------------------------
def arbitro_analitico(n, t, re, p=PARAMS_STATEMENT):
    xx, yy, _, _ = _malla(n, p)
    nu = nu_de_re(re, p)
    a = (xx - p["Uc"] * t) / p["L"]
    b = (yy - p["Vc"] * t) / p["L"]
    dec = np.exp(-2.0 * nu * t / p["L"] ** 2)
    u = p["Uc"] + p["V0"] * np.sin(a) * np.cos(b) * dec
    v = p["Vc"] - p["V0"] * np.cos(a) * np.sin(b) * dec
    return u, v


def _vorticidad_inicial(n, p=PARAMS_STATEMENT):
    # Curl analitico de la IC §5.2: w = dv/dx - du/dy = (2*V0/L) sin(x/L) sin(y/L).
    # Los dos brazos evolucionan vorticidad y parten de esta misma formula.
    xx, yy, _, _ = _malla(n, p)
    return (2.0 * p["V0"] / p["L"]) * np.sin(xx / p["L"]) * np.sin(yy / p["L"])


# ---------------------------------------------------------------------------
# Metrica del prereg §4: error L2 relativo del campo de velocidad completo
# (incluye el flujo medio Uc — lectura literal de "campo de velocidad").
# ---------------------------------------------------------------------------
def error_l2_rel(u, v, u_ref, v_ref):
    num = np.sqrt(np.sum((u - u_ref) ** 2 + (v - v_ref) ** 2))
    den = np.sqrt(np.sum(u_ref ** 2 + v_ref ** 2))
    return float(num / den)


# ---------------------------------------------------------------------------
# GUARDIA 1 — el campo inicial reproduce la analitica a epsilon de maquina.
# ---------------------------------------------------------------------------
def guardia_t0(u0, v0, u_arb, v_arb, tol=1e-13):
    err = error_l2_rel(u0, v0, u_arb, v_arb)
    if not (err <= tol):
        raise GuardiaError(
            "ABORTA (guardia 1): en t=0 el campo inicial difiere de la analitica "
            "en %.3e > %.0e. O la IC §5.2 o el arbitro §5.3 estan mal tecleados; "
            "no se corre nada encima de un arbitro dudoso." % (err, tol))
    return err


# ---------------------------------------------------------------------------
# GUARDIA 3 — nan o campo vacio en cualquier brazo aborta la corrida entera.
# ---------------------------------------------------------------------------
def guardia_finito(campos, brazo):
    for nombre, arr in campos.items():
        a = np.asarray(arr)
        if a.size == 0:
            raise GuardiaError(
                "ABORTA (guardia 3): el campo '%s' del brazo %s esta VACIO. "
                "La ausencia no viaja como valor." % (nombre, brazo))
        if not np.all(np.isfinite(a)):
            n_malos = int(np.sum(~np.isfinite(a)))
            raise GuardiaError(
                "ABORTA (guardia 3): %d valores no finitos en el campo '%s' del "
                "brazo %s. Un nan rio abajo se lee como un numero." % (n_malos, nombre, brazo))


# ---------------------------------------------------------------------------
# GUARDIA 2 — el artefacto declara lo que ocurrio. Se comparan los valores del
# artefacto contra los medidos de los objetos reales (shapes, contadores,
# relojes) por ruta punteada; una clave ausente es el mismo fallo que una
# distinta: declarar de menos tambien es declarar otra cosa.
# ---------------------------------------------------------------------------
def guardia_declaracion(artefacto, ocurrido):
    for ruta, medido in ocurrido.items():
        nodo = artefacto
        for k in ruta.split("."):
            if not isinstance(nodo, dict) or k not in nodo:
                raise GuardiaError(
                    "ABORTA (guardia 2): el artefacto no declara '%s' (medido: %r). "
                    "Lo que ocurrio y no se declara, no ocurrio para el lector." % (ruta, medido))
            nodo = nodo[k]
        if nodo != medido:
            raise GuardiaError(
                "ABORTA (guardia 2): el artefacto declara %s=%r pero lo medido es %r. "
                "Se declara lo que OCURRIO, no lo que se pidio." % (ruta, nodo, medido))


# ---------------------------------------------------------------------------
# GUARDIA 5 — una ausencia no viaja como valor, en LOS DOS SENTIDOS. Un brazo
# que no resolvio tiene que declararlo con motivo y mediciones que lo
# respalden; uno que si resolvio tiene que traer un error finito. Nadie puede
# quedar en el medio, y nadie puede declarar las dos cosas a la vez.
# ---------------------------------------------------------------------------
def guardia_ausencia_declarada(nombre, entrada):
    no_res = bool(entrada.get("no_resuelto", False))
    err = entrada.get("error_l2_rel", None)
    if no_res:
        motivo = entrada.get("motivo")
        if not isinstance(motivo, str) or not motivo.strip():
            raise GuardiaError(
                "ABORTA (guardia 5): el brazo %s declara que no resolvio pero sin "
                "MOTIVO. Un fallo sin causa medida es un fallo silencioso." % nombre)
        med = entrada.get("medicion")
        if not isinstance(med, dict) or len(med) == 0:
            raise GuardiaError(
                "ABORTA (guardia 5): el brazo %s declara que no resolvio con motivo "
                "%r pero sin ninguna MEDICION que lo respalde. El motivo se mide, "
                "no se narra." % (nombre, motivo))
        if err is not None:
            raise GuardiaError(
                "ABORTA (guardia 5): el brazo %s declara que no resolvio Y a la vez "
                "error_l2_rel=%r. La ausencia no viaja como valor." % (nombre, err))
    else:
        if err is None:
            raise GuardiaError(
                "ABORTA (guardia 5): el brazo %s no declara que fallara, pero su "
                "error_l2_rel esta AUSENTE. O resolvio y trae numero, o declara "
                "por que no." % nombre)
        if not np.isfinite(err):
            raise GuardiaError(
                "ABORTA (guardia 5): el brazo %s presenta error_l2_rel=%r como si "
                "fuera un resultado. Un no-finito no es una medicion." % (nombre, err))


# ---------------------------------------------------------------------------
# GUARDIA 4 — el orden de truncamiento de Carleman viaja declarado junto a la
# dimension REAL del sistema linealizado, y ambos se verifican contra la malla
# que OCURRIO (leida del shape del arreglo). La aritmetica dim = suma_{j=1..K}
# m^j con m = N^2 ata las tres cosas: si el brazo corrio otro orden, otra
# dimension o en otra malla que la declarada, no cierran.
# ---------------------------------------------------------------------------
def guardia_carleman_declarado(nombre, entrada, malla_real):
    c = entrada.get("carleman")
    if not isinstance(c, dict):
        raise GuardiaError(
            "ABORTA (guardia 4): el brazo %s esta registrado como brazo de Carleman "
            "pero su entrada NO declara el bloque 'carleman' (orden de truncamiento "
            "y dimension real). Lo que no se declara, no ocurrio para el lector."
            % nombre)
    for clave in ("orden_real", "dim_sistema_real", "n_qubits"):
        if clave not in c:
            raise GuardiaError(
                "ABORTA (guardia 4): el brazo %s no declara 'carleman.%s'. El orden "
                "de truncamiento y la dimension del sistema son parte de lo que "
                "OCURRIO." % (nombre, clave))
    k = c["orden_real"]
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise GuardiaError(
            "ABORTA (guardia 4): el brazo %s declara un orden de Carleman invalido "
            "(%r). El orden es un entero >= 1 leido de los bloques construidos."
            % (nombre, k))
    m = int(malla_real) ** 2
    dim_esperada = sum(m ** j for j in range(1, k + 1))
    if c["dim_sistema_real"] != dim_esperada:
        raise GuardiaError(
            "ABORTA (guardia 4): el brazo %s declara orden K=%d sobre malla N=%d "
            "(m=%d celdas), lo que da dim = suma m^j = %d, pero declara "
            "dim_sistema_real=%r. O el orden, o la dimension, o la malla no son "
            "los que corrieron." % (nombre, k, int(malla_real), m, dim_esperada,
                                    c["dim_sistema_real"]))
    nq_esperado = 1 if dim_esperada <= 1 else int(np.ceil(np.log2(dim_esperada)))
    if c["n_qubits"] != nq_esperado:
        raise GuardiaError(
            "ABORTA (guardia 4): el brazo %s declara n_qubits=%r para un sistema de "
            "dimension %d, que necesita %d qubits. El tamano del statevector es una "
            "consecuencia de la dimension, no una eleccion."
            % (nombre, c["n_qubits"], dim_esperada, nq_esperado))


# ---------------------------------------------------------------------------
# BRAZO ESPECTRAL (calidad referencia): pseudo-espectral, vorticidad-funcion
# de corriente, dealiasing 2/3, RK4 con factor integrante viscoso exacto
# (el termino viscoso es lineal y diagonal en Fourier: integrarlo exacto
# elimina la rigidez sin cambiar el metodo).
# ---------------------------------------------------------------------------
def _brazo_espectral(n, re, t_final, cfl=0.5, p=PARAMS_STATEMENT):
    _, _, h, _ = _malla(n, p)
    nu = nu_de_re(re, p)
    w = _vorticidad_inicial(n, p)

    k1 = 2.0 * np.pi * np.fft.fftfreq(n, d=h)
    kx, ky = np.meshgrid(k1, k1, indexing="ij")
    k2 = kx ** 2 + ky ** 2
    k2_inv = 1.0 / np.where(k2 == 0.0, 1.0, k2)
    corte = (2.0 / 3.0) * np.max(np.abs(k1))
    dealias = (np.abs(kx) <= corte) & (np.abs(ky) <= corte)

    def velocidad(wh):
        psih = wh * k2_inv
        psih[0, 0] = 0.0  # el modo medio de la velocidad es (Uc, Vc), no sale de psi
        u = p["Uc"] + np.real(np.fft.ifft2(1j * ky * psih))
        v = p["Vc"] - np.real(np.fft.ifft2(1j * kx * psih))
        return u, v

    def no_lineal(wh):
        u, v = velocidad(wh)
        wx = np.real(np.fft.ifft2(1j * kx * wh))
        wy = np.real(np.fft.ifft2(1j * ky * wh))
        return -np.fft.fft2(u * wx + v * wy) * dealias

    # dt por CFL con cota dura de |u| (|Uc|+V0, |Vc|+V0): la analitica acota la
    # velocidad, no hace falta estimarla del campo. El ultimo paso cae exacto
    # en t_final reescalando dt, para no comparar contra otro tiempo.
    umax = max(abs(p["Uc"]) + p["V0"], abs(p["Vc"]) + p["V0"])
    pasos_plan = max(1, int(np.ceil(t_final * umax / (cfl * h))))
    dt = t_final / pasos_plan

    e_full = np.exp(-nu * k2 * dt)
    e_half = np.exp(-nu * k2 * dt / 2.0)
    wh = np.fft.fft2(w)
    pasos = 0  # contador del bucle: lo que la guardia 2 declara como ocurrido
    for _ in range(pasos_plan):
        n1 = no_lineal(wh)
        n2 = no_lineal(e_half * (wh + 0.5 * dt * n1))
        n3 = no_lineal(e_half * wh + 0.5 * dt * n2)
        n4 = no_lineal(e_full * wh + dt * e_half * n3)
        wh = e_full * wh + (dt / 6.0) * (e_full * n1 + 2.0 * e_half * (n2 + n3) + n4)
        pasos += 1

    u, v = velocidad(wh)
    w_fin = np.real(np.fft.ifft2(wh))
    return {"u": u, "v": v, "w": w_fin, "dt": dt, "pasos": pasos,
            "esquema": "pseudo-espectral Fourier, dealiasing 2/3, "
                       "RK4 con factor integrante viscoso exacto"}


# ---------------------------------------------------------------------------
# BRAZO DIFERENCIAS FINITAS de 2.o orden (el metodo "de ingenieria"):
# adveccion centrada, Laplaciano de 5 puntos, RK4 explicito. La Poisson del
# operador DISCRETO de 5 puntos se invierte exacta por diagonalizacion de
# Fourier: el solver es algebra lineal rapida, la discretizacion sigue siendo
# de 2.o orden — asi el tiempo de pared mide el metodo y no un Gauss-Seidel
# nuestro mal escrito.
# ---------------------------------------------------------------------------
def _brazo_fd(n, re, t_final, cfl=0.5, seg_visc=0.2, p=PARAMS_STATEMENT):
    _, _, h, _ = _malla(n, p)
    nu = nu_de_re(re, p)
    w = _vorticidad_inicial(n, p)

    m = np.arange(n)
    lam1 = -(2.0 - 2.0 * np.cos(2.0 * np.pi * m / n)) / h ** 2  # autovalores del 5 puntos
    lam = lam1[:, None] + lam1[None, :]
    lam_inv = 1.0 / np.where(lam == 0.0, 1.0, lam)

    def velocidad(w_):
        wh = np.fft.fft2(w_)
        psih = -wh * lam_inv  # lap_5p(psi) = -w, exacto para el operador discreto
        psih[0, 0] = 0.0
        psi = np.real(np.fft.ifft2(psih))
        u = p["Uc"] + (np.roll(psi, -1, axis=1) - np.roll(psi, 1, axis=1)) / (2.0 * h)
        v = p["Vc"] - (np.roll(psi, -1, axis=0) - np.roll(psi, 1, axis=0)) / (2.0 * h)
        return u, v

    def rhs(w_):
        u, v = velocidad(w_)
        wx = (np.roll(w_, -1, axis=0) - np.roll(w_, 1, axis=0)) / (2.0 * h)
        wy = (np.roll(w_, -1, axis=1) - np.roll(w_, 1, axis=1)) / (2.0 * h)
        lap = (np.roll(w_, -1, 0) + np.roll(w_, 1, 0) + np.roll(w_, -1, 1)
               + np.roll(w_, 1, 1) - 4.0 * w_) / h ** 2
        return -(u * wx + v * wy) + nu * lap

    # dt: el menor entre el limite advectivo (CFL) y el difusivo explicito;
    # ambos declarados via cfl/seg_visc, ninguno fijo a mano adentro del bucle.
    umax = max(abs(p["Uc"]) + p["V0"], abs(p["Vc"]) + p["V0"])
    dt0 = min(cfl * h / umax, seg_visc * h ** 2 / nu)
    pasos_plan = max(1, int(np.ceil(t_final / dt0)))
    dt = t_final / pasos_plan

    pasos = 0
    for _ in range(pasos_plan):
        k1_ = rhs(w)
        k2_ = rhs(w + 0.5 * dt * k1_)
        k3_ = rhs(w + 0.5 * dt * k2_)
        k4_ = rhs(w + dt * k3_)
        w = w + (dt / 6.0) * (k1_ + 2.0 * k2_ + 2.0 * k3_ + k4_)
        pasos += 1

    u, v = velocidad(w)
    return {"u": u, "v": v, "w": w, "dt": dt, "pasos": pasos,
            "esquema": "diferencias finitas centradas 2.o orden, Laplaciano 5 puntos, "
                       "Poisson exacta del operador discreto, RK4 explicito"}


# Registro de brazos a nivel de modulo: correr_punto los toma de aqui, lo que
# permite a test_guardias.py inyectar un brazo roto (mutacion) sin tocar nada.
BRAZOS = (("espectral", _brazo_espectral), ("fd2", _brazo_fd))


def _desempacar_brazo(entrada):
    """Una entrada de BRAZOS es (nombre, fn) o (nombre, fn, opciones). Las
    OPCIONES viven en el REGISTRO, no en lo que el brazo devuelve: asi una
    mutacion adentro del brazo no puede apagarse a si misma la guardia 4."""
    if len(entrada) == 2:
        return entrada[0], entrada[1], {}
    return entrada[0], entrada[1], dict(entrada[2])


# ---------------------------------------------------------------------------
# Regla de acople malla-Reynolds POR DEFECTO. Es un parametro del barrido, no
# una constante interna: el statement exige "grid resolution must increase
# with Reynolds number" y el prereg exige que la regla viaje en el artefacto.
# ---------------------------------------------------------------------------
def acople_sqrt(re, n_base=64, re_base=100.0):
    n = int(np.ceil(n_base * np.sqrt(float(re) / re_base)))
    n = max(32, n)
    return 1 << (n - 1).bit_length()  # potencia de 2: mallas comparables y FFT pareja


acople_sqrt.descripcion = ("N = potencia de 2 >= 64*sqrt(Re/100), piso 32 "
                           "(resolucion crece con Re como exige el statement §4.1)")


# ---------------------------------------------------------------------------
# UN PUNTO del eje: corre los dos brazos sobre la misma malla y el mismo T,
# mide contra el arbitro, pasa las tres guardias y (si outdir) emite el
# artefacto JSON. Cualquier guardia disparada mata la corrida SIN artefacto.
# ---------------------------------------------------------------------------
def correr_punto(re, n, t_final, cfl=0.5, presupuesto_pared_s=None,
                 outdir=None, regla_desc="(N pasado a mano, sin regla)",
                 brazos=None):
    """Corre TODOS los brazos registrados sobre la misma malla y el mismo T,
    mide con el MISMO arbitro y la MISMA metrica, pasa las cinco guardias y
    (si outdir) emite el artefacto JSON. Cualquier guardia disparada mata la
    corrida SIN artefacto.

    `brazos` permite pasar otro registro (por ejemplo los dos clasicos + el
    cuantico de airbus_carleman); por defecto se lee BRAZOS al momento de la
    llamada, para que un test pueda inyectar un brazo mutado."""
    # Guardia 1 primero: nada corre encima de un arbitro que no reproduce la IC.
    u_ic, v_ic = ic_statement(n)
    u_a0, v_a0 = arbitro_analitico(n, 0.0, re)
    err_t0 = guardia_t0(u_ic, v_ic, u_a0, v_a0)
    guardia_finito({"u_ic": u_ic, "v_ic": v_ic}, "condicion inicial")

    registro = BRAZOS if brazos is None else brazos
    corridas = {}
    orden_brazos = []
    for entrada in registro:
        nombre, brazo, opciones = _desempacar_brazo(entrada)
        orden_brazos.append(nombre)
        t_ini = time.perf_counter()
        res = brazo(n, re, t_final, cfl)
        pared = time.perf_counter() - t_ini
        if res.get("no_resuelto"):
            # Guardia 5 se aplica ANTES de tocar nada mas: un brazo que no
            # resolvio se declara aca o no viaja.
            corridas[nombre] = {"res": res, "pared_s": round(pared, 6),
                                "no_resuelto": True, "opciones": opciones}
            continue
        # Guardia 3 sobre CADA brazo antes de mirar el otro o escribir nada:
        # un nan en un brazo aborta la corrida entera, no solo su columna.
        guardia_finito({"u": res["u"], "v": res["v"], "w": res.get("w", res["u"])}, nombre)
        t_real = res["pasos"] * res["dt"]  # lo ocurrido: contador x dt real
        u_ref, v_ref = arbitro_analitico(n, t_real, re)
        corridas[nombre] = {
            "res": res,
            "pared_s": round(pared, 6),
            "t_real": t_real,
            "error": error_l2_rel(res["u"], res["v"], u_ref, v_ref),
            "malla_real": int(res["u"].shape[0]),
            "opciones": opciones,
        }

    resueltos = [k for k in orden_brazos if not corridas[k].get("no_resuelto")]
    if not resueltos:
        raise GuardiaError(
            "ABORTA (guardia 5): NINGUN brazo resolvio el punto Re=%g N=%d. Un "
            "artefacto sin un solo brazo resuelto no es una medicion." % (float(re), int(n)))
    malla_real_pto = int(corridas[resueltos[0]]["res"]["u"].shape[0])

    ts = datetime.now(timezone.utc)
    artefacto = {
        "track": "Airbus - vortice de Taylor-Green convectivo 2D",
        "prereg": "RQ-PREREG-AIRBUS-001",
        "timestamp_utc": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "statement_sha256": STATEMENT_SHA256,
        "parametros_statement": {
            "L": PARAMS_STATEMENT["L"], "V0": PARAMS_STATEMENT["V0"],
            "Uc": PARAMS_STATEMENT["Uc"], "Vc": PARAMS_STATEMENT["Vc"],
            "rho": PARAMS_STATEMENT["rho"], "p0": PARAMS_STATEMENT["p0"],
            "Re": float(re), "nu": nu_de_re(re),
        },
        "dominio": {"lado": 2.0 * np.pi * PARAMS_STATEMENT["L"], "decision": DECISION_DOMINIO},
        "regla_acople": {"descripcion": regla_desc, "N_resultante": int(n)},
        "malla_real": malla_real_pto,
        "T_pedido": float(t_final),
        "presupuesto_pared_s": presupuesto_pared_s,
        "arbitro": "formula cerrada §5.3 del statement, evaluada en la malla en T real",
        "metrica": "error L2 relativo del campo de velocidad completo (incluye flujo medio)",
        "brazos": {},
        "lib_versions": {
            "numpy": np.__version__,
            "python": platform.python_version(),
            # El hash del harness que PRODUJO este artefacto, leido del archivo
            # en disco al correr — el que un tercero recomputa con sha256sum
            # (patron de eon_harness.py; defecto de julio).
            "harness_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
        },
        "guardias": {"t0_error_l2_rel": err_t0, "t0_tolerancia": 1e-13},
    }
    for nombre in orden_brazos:
        c = corridas[nombre]
        if c.get("no_resuelto"):
            # Se declara lo que se MIDIO del fallo. error_l2_rel queda AUSENTE
            # a proposito: no hay valor por defecto que ponerle.
            artefacto["brazos"][nombre] = {
                "esquema": c["res"].get("esquema", "(sin esquema declarado)"),
                "no_resuelto": True,
                "motivo": c["res"].get("motivo"),
                "medicion": c["res"].get("medicion"),
                "tiempo_pared_s": c["pared_s"],
            }
            continue
        artefacto["brazos"][nombre] = {
            "esquema": c["res"]["esquema"],
            "malla_real": c["malla_real"],
            "pasos_reales": c["res"]["pasos"],
            "dt_real": c["res"]["dt"],
            "T_real": c["t_real"],
            "tiempo_pared_s": c["pared_s"],
            "excedio_presupuesto": (None if presupuesto_pared_s is None
                                    else bool(c["pared_s"] > presupuesto_pared_s)),
            "error_l2_rel": c["error"],
        }
        if "carleman" in c["res"]:
            artefacto["brazos"][nombre]["carleman"] = c["res"]["carleman"]

    # Guardia 5 sobre CADA entrada del artefacto, en los dos sentidos.
    for nombre in orden_brazos:
        guardia_ausencia_declarada(nombre, artefacto["brazos"][nombre])

    # Guardia 4: los brazos marcados como de Carleman en el REGISTRO tienen que
    # declarar orden y dimension reales, y cuadrar con la malla que ocurrio.
    for nombre in orden_brazos:
        if not corridas[nombre]["opciones"].get("carleman"):
            continue
        entrada = artefacto["brazos"][nombre]
        if entrada.get("no_resuelto"):
            continue  # no hay sistema construido que declarar; lo cubre la guardia 5
        guardia_carleman_declarado(nombre, entrada,
                                   int(corridas[nombre]["res"]["u"].shape[0]))

    # Guardia 2: lo declarado contra lo medido de los objetos reales. Se toma
    # del shape, del contador y del reloj — NUNCA de las variables de entrada.
    ocurrido = {}
    for nombre in orden_brazos:
        c = corridas[nombre]
        if c.get("no_resuelto"):
            ocurrido["brazos.%s.no_resuelto" % nombre] = True
            ocurrido["brazos.%s.tiempo_pared_s" % nombre] = c["pared_s"]
            continue
        ocurrido["brazos.%s.malla_real" % nombre] = int(c["res"]["u"].shape[0])
        ocurrido["brazos.%s.pasos_reales" % nombre] = c["res"]["pasos"]
        ocurrido["brazos.%s.tiempo_pared_s" % nombre] = c["pared_s"]
        ocurrido["brazos.%s.T_real" % nombre] = c["res"]["pasos"] * c["res"]["dt"]
    ocurrido["malla_real"] = malla_real_pto
    guardia_declaracion(artefacto, ocurrido)

    ruta = None
    if outdir is not None:
        os.makedirs(outdir, exist_ok=True)
        nombre_arch = "airbus_punto_Re%g_N%d_%s.json" % (
            float(re), int(n), ts.strftime("%Y%m%dT%H%M%SZ"))
        ruta = os.path.join(outdir, nombre_arch)
        with open(ruta, "w") as f:
            json.dump(artefacto, f, indent=2)  # ensure_ascii=True por defecto: el sello es ASCII
    return artefacto, ruta


# ---------------------------------------------------------------------------
# EL EJE: barrido de Reynolds con la regla de acople como PARAMETRO. Un
# artefacto JSON por punto. Una guardia disparada en cualquier punto aborta
# el barrido entero (fallar cerrado > una curva con huecos silenciosos).
# ---------------------------------------------------------------------------
def barrido(reynolds, regla_acople, t_final, cfl=0.5,
            presupuesto_pared_s=None, outdir=None, brazos=None):
    desc = getattr(regla_acople, "descripcion", regla_acople.__name__)
    salidas = []
    for re_ in reynolds:
        n = int(regla_acople(re_))
        art, ruta = correr_punto(re_, n, t_final, cfl=cfl,
                                 presupuesto_pared_s=presupuesto_pared_s,
                                 outdir=outdir, regla_desc=desc, brazos=brazos)
        salidas.append((art, ruta))
    return salidas


# ---------------------------------------------------------------------------
# Corrida de humo: Re=100, malla por la regla por defecto, T corto.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts")
    salidas = barrido([100.0], acople_sqrt, t_final=2.0,
                      presupuesto_pared_s=60.0, outdir=outdir)
    art, ruta = salidas[0]
    e_sp = art["brazos"]["espectral"]["error_l2_rel"]
    e_fd = art["brazos"]["fd2"]["error_l2_rel"]
    print("artefacto:", ruta)
    for nombre in ("espectral", "fd2"):
        b = art["brazos"][nombre]
        print("%-10s N=%d pasos=%d dt=%.5f error_L2_rel=%.3e pared=%.4fs"
              % (nombre, b["malla_real"], b["pasos_reales"], b["dt_real"],
                 b["error_l2_rel"], b["tiempo_pared_s"]))
    # Criterio de exito de la corrida de humo, explicito y en la salida:
    ok = (e_sp < 1e-6) and (e_fd > e_sp) and np.isfinite(e_fd)
    print("humo:", "VERDE (espectral < 1e-6, FD mayor y finito)" if ok
          else "ROJO (espectral=%.3e, fd=%.3e)" % (e_sp, e_fd))
    raise SystemExit(0 if ok else 1)
