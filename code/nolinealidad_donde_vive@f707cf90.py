#!/usr/bin/env python3
# nolinealidad_donde_vive.py -- TAREA 2 del cierre del track Airbus.
#
# El hallazgo ya medido y clavado en test_tgv_tiene_termino_cuadratico_nulo es
# NEGATIVO: en el vortice de Taylor-Green del statement el termino no-lineal se
# cancela EXACTAMENTE, tambien en los operadores discretos de fd2. Un hallazgo
# negativo que solo senala el problema resta. Este script lo mide POSITIVO:
# en que casos de la MISMA familia la no-linealidad SI es distinta de cero, y
# cuanto.
#
# La razon medida es exactamente la que ya usan los tests:
#
#       razon = || A2 (w kron w) ||  /  || A1 w ||
#
# con A1, A2 los MISMOS operadores de airbus_carleman.matrices_fd (no se
# re-teclea ninguna formula). Sin red, sin QPU: numpy + scipy, local.
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
SALIDA = os.path.join(AQUI, "nolinealidad_donde_vive.json")

N_TABLA = 16          # malla de la tabla principal
N_CRUZADAS = (8, 16, 32)
RE_TABLA = 100.0
RE_CRUZADAS = (10.0, 100.0, 1000.0, 10000.0)
SEMILLA = 20260819
TOL_MODO = 1e-10      # amplitud relativa a partir de la cual un modo "esta"

DECISIONES_NO_PREFIJADAS = {
    "D_normalizacion": (
        "La razon || A2 (w kron w) || / || A1 w || es LINEAL en la amplitud de w "
        "(A2 es cuadratica y A1 lineal), asi que comparar formas exige fijar la "
        "amplitud. TODOS los campos de la tabla principal se reescalan a la MISMA "
        "norma L2 que el TGV del statement en la misma malla. Sin esta decision "
        "la tabla mediria amplitudes disfrazadas de formas."),
    "D_malla_y_Re": (
        "Tabla principal a N=%d y Re=%g. La razon depende de los dos (A1 lleva "
        "nu = V0*L/Re y las derivadas llevan h), asi que ambos se declaran y "
        "ademas se barren aparte: la misma tabla en N=%s y el mismo caso en "
        "Re=%s. Si la conclusion cambiara con la malla o con Re, se veria."
        % (N_TABLA, RE_TABLA, list(N_CRUZADAS), list(RE_CRUZADAS))),
    "D_familias": (
        "Se eligieron cinco familias, declaradas: (1) el TGV del statement tal "
        "cual; (2) TGV rotado 45 grados en su version exactamente periodica; "
        "(3) TGV anisotropo sin(x/L)*sin(a*y/L); (4) superposicion de dos modos "
        "TGV de numero de onda distinto; (5) TGV perturbado por un modo ajeno "
        "con amplitud relativa creciente. Mas un control superior de campo "
        "aleatorio de banda limitada."),
    "D_capas_de_Laplaciano": (
        "El diagnostico 'capas' cuenta cuantos autovalores DISTINTOS del "
        "Laplaciano discreto de 5 puntos tocan los modos presentes en w (los de "
        "amplitud > %g de la maxima). Es el mecanismo candidato de la "
        "cancelacion y por eso se mide en cada fila, no se supone." % TOL_MODO),
    "D_control_reproducido": (
        "El control superior incluye la reproduccion EXACTA del campo del test "
        "existente (N=4, Re=10, semilla 7, norma 2). Su razon publicada es "
        "0.482: si esta corrida no la reprodujera, el instrumento de esta tabla "
        "estaria midiendo otra cosa que el de los tests."),
}


# ---------------------------------------------------------------------------
# Campos de la familia. Todos sobre la malla del harness (ah._malla), nunca
# sobre una malla re-tecleada aca.
# ---------------------------------------------------------------------------
def _xy(n, p=ah.PARAMS_STATEMENT):
    xx, yy, _, _ = ah._malla(n, p)
    return xx, yy, p["L"]


def f_tgv_statement(n):
    return ah._vorticidad_inicial(n)          # el campo del statement, reusado


def f_tgv_rotado_45(n):
    xx, yy, L = _xy(n)
    return np.sin((xx + yy) / L) * np.sin((xx - yy) / L)


def f_tgv_anisotropo(a):
    def f(n):
        xx, yy, L = _xy(n)
        return np.sin(xx / L) * np.sin(a * yy / L)
    return f


def f_tgv_k(k):
    def f(n):
        xx, yy, L = _xy(n)
        return np.sin(k * xx / L) * np.sin(k * yy / L)
    return f


def f_superpos(k2, a):
    def f(n):
        xx, yy, L = _xy(n)
        return (np.sin(xx / L) * np.sin(yy / L)
                + a * np.sin(k2 * xx / L) * np.sin(k2 * yy / L))
    return f


def _delta_ajeno(n):
    """Modo perturbador: NO pertenece a la capa de autovalor del TGV."""
    xx, yy, L = _xy(n)
    return np.sin(2.0 * xx / L) * np.cos(3.0 * yy / L)


def f_perturbado(eps):
    def f(n):
        w0 = f_tgv_statement(n)
        d = _delta_ajeno(n)
        w0h = w0 / np.linalg.norm(w0)
        dh = d / np.linalg.norm(d)
        return w0h + eps * dh
    return f


def f_aleatorio_banda(kmax, semilla=SEMILLA):
    """Campo aleatorio de banda limitada: ruido gaussiano en el espacio de
    Fourier truncado a |kx|,|ky| <= kmax, hecho real y de media nula."""
    def f(n):
        rng = np.random.default_rng(semilla)
        wh = np.zeros((n, n), dtype=complex)
        k = np.fft.fftfreq(n, d=1.0 / n).astype(int)
        for i in range(n):
            for j in range(n):
                if abs(k[i]) <= kmax and abs(k[j]) <= kmax:
                    wh[i, j] = rng.normal() + 1j * rng.normal()
        w = np.real(np.fft.ifft2(wh))
        return w - w.mean()
    return f


# ---------------------------------------------------------------------------
# Diagnostico de capas: autovalores DISTINTOS del Laplaciano de 5 puntos que
# tocan los modos presentes. Los autovalores se toman de la misma formula que
# usa _brazo_fd y matrices_fd (no se re-teclean).
# ---------------------------------------------------------------------------
def capas_laplaciano(w, n, p=ah.PARAMS_STATEMENT):
    _, _, h, _ = ah._malla(n, p)
    mm = np.arange(n)
    lam1 = -(2.0 - 2.0 * np.cos(2.0 * np.pi * mm / n)) / h ** 2
    lam = lam1[:, None] + lam1[None, :]
    wh = np.fft.fft2(w)
    amp = np.abs(wh)
    mx = amp.max()
    presentes = amp > TOL_MODO * mx if mx > 0 else np.zeros_like(amp, dtype=bool)
    vals = lam[presentes]
    esc = max(1.0, float(np.max(np.abs(lam))))
    distintos = sorted({round(float(v) / esc, 12) for v in vals})
    return int(presentes.sum()), len(distintos)


# ---------------------------------------------------------------------------
# La medicion: razon = ||A2 (w kron w)|| / ||A1 w||, con normalizacion
# declarada a la norma del TGV del statement en la misma malla.
# ---------------------------------------------------------------------------
def razon(nombre, campo, n, re, normalizar=True, cache={}):
    clave = (n, re)
    if clave not in cache:
        cache[clave] = ac.matrices_fd(n, re)
    A1, A2, m = cache[clave]
    w = np.asarray(campo(n), dtype=float)
    if normalizar:
        ref = float(np.linalg.norm(f_tgv_statement(n)))
        w = w * (ref / float(np.linalg.norm(w)))
    wv = w.ravel()
    lin = float(np.linalg.norm(A1 @ wv))
    cuad = float(np.linalg.norm(A2 @ np.kron(wv, wv)))
    n_modos, n_capas = capas_laplaciano(w, n)
    return {"variante": nombre, "malla_N": n, "Re": re,
            "norma_L2_w": float(np.linalg.norm(wv)),
            "norma_A1_w": lin, "norma_A2_wxw": cuad,
            "razon": (cuad / lin) if lin > 0 else None,
            "modos_presentes": n_modos, "capas_autovalor": n_capas}


VARIANTES = [
    ("tgv_statement", f_tgv_statement,
     "el vortice de Taylor-Green del statement, tal cual"),
    ("tgv_k2", f_tgv_k(2), "TGV de numero de onda 2: sin(2x/L)*sin(2y/L)"),
    ("tgv_rotado_45", f_tgv_rotado_45,
     "TGV rotado 45 grados, version exactamente periodica: sin((x+y)/L)*sin((x-y)/L)"),
    ("tgv_anisotropo_a2", f_tgv_anisotropo(2.0), "sin(x/L)*sin(2y/L)"),
    ("tgv_anisotropo_a3", f_tgv_anisotropo(3.0), "sin(x/L)*sin(3y/L)"),
]
for _a in (0.01, 0.1, 0.5, 1.0):
    VARIANTES.append(("superpos_tgv_k1_k2_a%g" % _a, f_superpos(2, _a),
                      "TGV(k=1) + %g*TGV(k=2): dos numeros de onda a la vez" % _a))
EPSILONES = (1e-4, 1e-3, 1e-2, 3e-2, 0.1, 0.3, 1.0)
for _e in EPSILONES:
    VARIANTES.append(("tgv_perturbado_eps%g" % _e, f_perturbado(_e),
                      "TGV + %g * modo ajeno sin(2x/L)cos(3y/L) (amplitud relativa)" % _e))
for _k in (2, 4):
    VARIANTES.append(("aleatorio_banda_kmax%d" % _k, f_aleatorio_banda(_k),
                      "control superior: campo aleatorio de banda limitada |k|<=%d, "
                      "semilla %d" % (_k, SEMILLA)))


def control_del_test():
    """Reproduce EXACTAMENTE el campo de test_carleman_converge_al_subir_el_orden_K
    (N=4, Re=10, semilla 7, norma 2) para comprobar que esta tabla mide lo mismo
    que los tests que ya existen. Valor publicado: 0.482."""
    n, re = 4, 10.0
    A1, A2, m = ac.matrices_fd(n, re)
    rng = np.random.default_rng(7)
    base = rng.normal(size=m)
    base -= base.mean()
    base /= np.linalg.norm(base)
    w0 = 2.0 * base
    lin = float(np.linalg.norm(A1 @ w0))
    cuad = float(np.linalg.norm(A2 @ np.kron(w0, w0)))
    return {"variante": "control_reproducido_del_test", "malla_N": n, "Re": re,
            "norma_L2_w": 2.0, "norma_A1_w": lin, "norma_A2_wxw": cuad,
            "razon": cuad / lin,
            "valor_publicado_en_el_encargo": 0.482,
            "sin_normalizar": True,
            "nota": ("NO se reescala: se reproduce el campo del test tal cual, "
                     "porque el punto es comprobar el numero contra el terreno.")}


def main():
    t0 = time.perf_counter()
    tabla = [dict(razon(nom, f, N_TABLA, RE_TABLA), descripcion=d)
             for nom, f, d in VARIANTES]
    for f in tabla:
        print("%-28s capas=%-3d modos=%-5d razon=%.6e"
              % (f["variante"], f["capas_autovalor"], f["modos_presentes"],
                 f["razon"]))

    cruzada_malla = [razon(nom, f, n, RE_TABLA)
                     for nom, f, _ in VARIANTES
                     if nom in ("tgv_statement", "tgv_rotado_45",
                                "tgv_anisotropo_a2", "superpos_tgv_k1_k2_a1",
                                "tgv_perturbado_eps0.1", "aleatorio_banda_kmax4")
                     for n in N_CRUZADAS]
    cruzada_re = [razon(nom, f, N_TABLA, r)
                  for nom, f, _ in VARIANTES
                  if nom in ("tgv_statement", "tgv_perturbado_eps0.1",
                             "aleatorio_banda_kmax4")
                  for r in RE_CRUZADAS]
    control = control_del_test()
    print("control del test: razon=%.6f (publicado %.3f)"
          % (control["razon"], control["valor_publicado_en_el_encargo"]))

    # -----------------------------------------------------------------------
    # LA REGLA, MEDIDA SOBRE LA TABLA (no afirmada): la razon es cero a
    # epsilon de maquina EXACTAMENTE en las filas de UNA sola capa de
    # autovalor del Laplaciano discreto, y no-nula en todas las demas.
    # Se reporta con denominador.
    # -----------------------------------------------------------------------
    umbral_cero = 1e-12
    una_capa = [f for f in tabla if f["capas_autovalor"] == 1]
    varias = [f for f in tabla if f["capas_autovalor"] > 1]
    regla_ok = (all(f["razon"] < umbral_cero for f in una_capa)
                and all(f["razon"] > umbral_cero for f in varias))

    # Ley de amplitud: para el TGV perturbado la razon deberia crecer LINEAL
    # con eps (A2 es bilineal y el termino de orden 0 es nulo). Se mide la
    # pendiente y su dispersion en vez de afirmar la linealidad.
    pares = [(e, next(f["razon"] for f in tabla
                      if f["variante"] == "tgv_perturbado_eps%g" % e))
             for e in EPSILONES]
    pend = [r / e for e, r in pares]
    ley = {
        "familia": "TGV + eps * modo ajeno sin(2x/L)cos(3y/L)",
        "epsilon": [e for e, _ in pares],
        "razon": [r for _, r in pares],
        "razon_sobre_epsilon": pend,
        "pendiente_en_eps_minimo": pend[0],
        "dispersion_relativa_de_la_pendiente_en_eps<=0.01": float(
            (max(pend[:3]) - min(pend[:3])) / pend[0]),
        "lectura": ("la razon crece LINEAL en la amplitud relativa de la "
                    "perturbacion para eps pequeno: razon ~ %.4f * eps"
                    % pend[0]),
    }

    salida = {
        "track": "Airbus - vortice de Taylor-Green convectivo 2D",
        "prereg": "RQ-PREREG-AIRBUS-001",
        "producido_por": "nolinealidad_donde_vive.py",
        # El nombre no identifica codigo: dos versiones distintas comparten nombre. Va
        # el sha256 del script que escribe Y de sus dependencias, para que la frase
        # "el instrumento declara su propio sha256" sea cierta y no una aspiracion.
        "producido_por_sha256": _proc.procedencia(__file__),
        "statement_sha256": ah.STATEMENT_SHA256,
        "pregunta": ("El termino no-lineal se cancela exactamente en el TGV del "
                     "statement. En que casos de la MISMA familia SI es distinto "
                     "de cero, y cuanto."),
        "medicion": "razon = || A2 (w kron w) || / || A1 w ||, operadores de matrices_fd",
        "malla_tabla": N_TABLA, "Re_tabla": RE_TABLA,
        "tabla": tabla,
        "cruzada_malla": cruzada_malla,
        "cruzada_reynolds": cruzada_re,
        "control_del_test": control,
        "ley_de_amplitud": ley,
        "regla_medida": {
            "enunciado": (
                "La no-linealidad discreta se anula EXACTAMENTE si y solo si la "
                "vorticidad vive en UNA sola capa de autovalor del Laplaciano "
                "discreto de 5 puntos. Mecanismo: en ese caso la funcion de "
                "corriente es psi = c*w con c constante, y el Jacobiano J(psi,w) "
                "es identicamente nulo punto a punto -- tambien en el discreto. "
                "El TGV del statement, el TGV rotado 45 grados y el TGV "
                "anisotropo son todos de una sola capa: por eso el benchmark no "
                "ejercita la no-linealidad. En cuanto el campo toca DOS capas "
                "-- una superposicion de numeros de onda distintos, o una "
                "perturbacion ajena -- la razon deja de ser cero y crece lineal "
                "con la amplitud de la componente ajena."),
            "umbral_cero": umbral_cero,
            "filas_una_capa": len(una_capa),
            "filas_varias_capas": len(varias),
            "denominador": len(tabla),
            "razon_maxima_entre_las_de_una_capa": max(f["razon"] for f in una_capa),
            "razon_minima_entre_las_de_varias_capas": min(f["razon"] for f in varias),
            "la_regla_se_cumple_en_toda_la_tabla": bool(regla_ok),
        },
        "decisiones_no_prefijadas": DECISIONES_NO_PREFIJADAS,
        "entorno": {"numpy": np.__version__, "python": platform.python_version()},
        "pared_total_s": None,
        "sin_red_sin_qpu": True,
    }
    salida["pared_total_s"] = round(time.perf_counter() - t0, 3)
    # El hash del ARCHIVO cambia entre corridas por el reloj; este otro se calcula
    # sobre el contenido determinista y SI reproduce. Es el que se cita.
    _ch, _fuera = _proc.contenido(salida)
    salida["contenido_sha256"] = _ch
    salida["campos_no_reproducibles"] = {
        "excluidos": _fuera,
        "por_que": ("dependen de la maquina o del momento y ningun tercero los "
                    "reproduce. Los tiempos de pared son MEDICIONES del experimento, "
                    "no ruido: se comparan entre brazos de la misma corrida, nunca "
                    "entre computadores."),
        "lista_medida": "son los que el podador encontro de verdad, no los que se "
                        "esperaba encontrar.",
    }

    with open(SALIDA, "w") as fh:
        json.dump(salida, fh, indent=2)
    print("\nregla se cumple en toda la tabla: %s (%d de una capa / %d de varias, "
          "denominador %d)" % (regla_ok, len(una_capa), len(varias), len(tabla)))
    print("salida: %s" % SALIDA)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
