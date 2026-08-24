#!/usr/bin/env python3
# airbus_carleman.py — BRAZO CUANTICO del track Airbus (RQ-PREREG-AIRBUS-001).
#
# Prereg §4, tercer brazo, literal: "linealizacion de Carleman (orden declarado
# en cada artefacto) + evolucion del sistema lineal por metodo variacional en
# statevector. Sin QPU en esta fase". Esto es exactamente lo que hay aca: no
# hay red, no hay hardware, no hay API. numpy + scipy y nada mas.
#
# Se monta ENCIMA de airbus_harness.py: mismo arbitro analitico (§5.3), misma
# metrica L2 relativa, mismas guardias 1/2/3, mismo formato de artefacto. La
# comparacion contra los brazos clasicos es limpia o no vale.
#
# Todo el archivo es ASCII a proposito (los artefactos se sellan por hash).
#
# ---------------------------------------------------------------------------
# DE DONDE SALE CADA BLOQUE DE LA MATRIZ
# ---------------------------------------------------------------------------
# El semi-discreto de fd2 sobre la vorticidad w (vector de m = n*n) es
# EXACTAMENTE cuadratico:
#
#     dw/dt = A1 w + A2 (w kron w)
#
#   A1 = -Uc*Dx - Vc*Dy + nu*Lap
#        (adveccion por el flujo MEDIO del statement §5.2, que es constante y
#         por lo tanto lineal en w, + difusion viscosa: los dos terminos
#         lineales del operador de fd2)
#   A2 = la auto-adveccion -(u'[w] . grad) w, cuadratica porque u'[w] es
#        lineal en w (Poisson discreta) y grad w tambien:
#           A2[i, a*m+b] = -( Bu[i,a]*Dx[i,b] + Bv[i,a]*Dy[i,b] )
#        con Bu = Dy @ P, Bv = -Dx @ P y P la inversa EXACTA del Laplaciano
#        discreto de 5 puntos (la misma que usa _brazo_fd, por eso el test
#        test_carleman_reproduce_fd2 exige igualdad a epsilon de maquina).
#
# Carleman: se define el estado extendido y = (w, w^{kron 2}, ..., w^{kron K}).
# Derivando w^{kron j} por la regla del producto sobre las j ranuras:
#
#     d(w^{kron j})/dt = A1^{(j)} w^{kron j} + A2^{(j)} w^{kron (j+1)}
#     A1^{(j)} = suma_{s=1..j} I^{kron(s-1)} kron A1 kron I^{kron(j-s)}
#     A2^{(j)} = suma_{s=1..j} I^{kron(s-1)} kron A2 kron I^{kron(j-s)}
#
# (A2 come DOS ranuras y devuelve UNA, por eso A2^{(j)}: m^{j+1} -> m^{j};
#  w^{kron(j+1)} es simetrico bajo permutacion de ranuras, asi que poner las
#  dos ranuras contraidas en las posiciones s,s+1 no pierde generalidad.)
#
# La matriz C queda BLOQUE-BIDIAGONAL POR BLOQUES:
#
#        [ A1^{(1)}  A2^{(1)}     0        0     ]
#   C =  [    0      A1^{(2)}  A2^{(2)}    0     ]
#        [    0         0      A1^{(3)}  A2^{(3)}]
#        [    0         0         0      A1^{(K)}]   <-- TRUNCAMIENTO: el
#                                                        bloque A2^{(K)} que
#                                                        acoplaria al orden
#                                                        K+1 se DESCARTA.
# Ese descarte es el orden de truncamiento K, y es lo unico que se aproxima
# en la parte de Carleman: para K -> infinito la solucion de C reproduce la
# solucion exacta del sistema cuadratico (= la de fd2 con dt -> 0).
#
# Dimension real del sistema linealizado: dim = suma_{j=1..K} m^j. Crece como
# m^K. Ese es el muro y se MIDE, no se estima.
#
# ---------------------------------------------------------------------------
# EVOLUCION VARIACIONAL EN STATEVECTOR (McLachlan)
# ---------------------------------------------------------------------------
# El estado de Carleman y(t) (real, dim -> 2^nq con relleno de ceros) se
# escribe y(t) = r(t) * psi(theta(t)) con ||psi||=1 y psi el statevector de un
# ansatz real (RY + CNOT en anillo). El principio variacional de McLachlan
# minimiza || d/dt (r psi) - C (r psi) ||, y como <psi|d_k psi> = 0 para un
# ansatz real normalizado, el sistema se desacopla:
#
#     r_punto = r * <psi|C|psi>
#     suma_k M_jk theta_punto_k = V_j
#         M_jk = <d_j psi | d_k psi>
#         V_j  = <d_j psi | (C - <psi|C|psi>) | psi>
#
# M es la metrica de Fubini-Study real (Gram de las derivadas). Se resuelve
# regularizada (Tikhonov, lambda declarado) porque M es singular cuando el
# ansatz tiene parametros redundantes. Se integra con RK4 en t.
#
# El RESIDUO DE McLACHLAN --- la fraccion de la dinamica que el espacio
# tangente del ansatz NO puede representar --- se mide en cada paso y viaja en
# el artefacto. Es la medida honesta de "hasta donde alcanza el ansatz", y es
# lo que separa el error de truncamiento (Carleman) del error de expresividad
# (variacional).

import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.optimize import minimize

import airbus_harness as ah


# ---------------------------------------------------------------------------
# DECISIONES QUE EL PREREG NO FIJA (APRENDIZAJES §11: se declaran, no se
# deciden en silencio). Viajan enteras en cada artefacto del brazo cuantico.
# ---------------------------------------------------------------------------
DECISIONES_NO_PREFIJADAS = {
    "D1_discretizacion_base_de_Carleman":
        "Carleman se construye sobre la MISMA discretizacion de fd2 (diferencias "
        "centradas 2.o orden + Laplaciano 5 puntos + Poisson exacta del operador "
        "discreto), no sobre la espectral. Motivo: asi el limite K->infinito del "
        "brazo cuantico es exactamente el brazo fd2, y la convergencia en K es "
        "verificable contra un objeto que ya existe y ya esta probado.",
    "D2_ansatz":
        "Ansatz real hardware-efficient: (capas+1) capas de RY en cada qubit "
        "separadas por CNOT en anillo. Real porque el estado de Carleman es real; "
        "un ansatz complejo gastaria la mitad de los parametros en una fase que "
        "no existe. n_parametros = n_qubits * (capas+1).",
    "D3_orden_de_los_qubits":
        "El estado de Carleman se rellena con ceros hasta 2^n_qubits. El relleno "
        "es ceros exactos, no ruido: un relleno con basura seria un valor que no "
        "se midio viajando dentro del statevector.",
    "D4_regularizacion":
        "M (metrica de Fubini-Study real) se invierte con Tikhonov lambda=1e-6 "
        "sobre la diagonal. M es singular por construccion cuando el ansatz tiene "
        "parametros redundantes; sin regularizacion el paso variacional explota.",
    "D5_estado_inicial":
        "theta inicial se ajusta maximizando <psi(theta)|y0/||y0||> con L-BFGS-B "
        "desde una semilla PRNG fija (seed declarada). La infidelidad que quede "
        "es error del ansatz y viaja medida en el artefacto; no se disimula.",
    "D6_muro":
        "Muro declarado por dos cotas duras y una medida: n_qubits > QUBITS_MAX o "
        "dim > DIM_MAX abortan ANTES de construir (motivo con el numero medido); "
        "MemoryError durante la construccion, no-finitud durante la evolucion y "
        "crecimiento de norma > FACTOR_DIVERGENCIA abortan con el paso medido.",
    "D7_diagnostico_separado":
        "El artefacto trae DOS errores del brazo cuantico: el error de punta a "
        "punta (el que se compara con los clasicos) y el error del mismo sistema "
        "de Carleman resuelto EXACTO (expm_multiply). La diferencia entre ambos "
        "es el costo del ansatz variacional; sin ese par no se puede saber cual "
        "de las dos capas fallo.",
}

# Cotas duras del muro (parametros, no constantes escondidas).
QUBITS_MAX = 14           # 2^14 = 16384 amplitudes reales
DIM_MAX = 1 << 14
FACTOR_DIVERGENCIA = 1e3  # ||y(t)|| / ||y(0)|| por encima de esto = no convergio

# Defaults del brazo cuando se registra en BRAZOS (declarados, no escondidos).
CARLEMAN_ORDEN = 2
ANSATZ_CAPAS = 6
PASOS_TIEMPO = 40
SEMILLA = 20260819
LAMBDA_TIKHONOV = 1e-6


# ===========================================================================
# 1 · OPERADORES DISCRETOS: A1 (m x m) y A2 (m x m^2)
# ===========================================================================
def _idx(n):
    i, j = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    return i.ravel(), j.ravel()


def _shift_matrix(n, di, dj):
    """Matriz de permutacion S tal que (S w)[i,j] = w[i+di, j+dj] (periodico),
    con w aplanado en orden C: idx = i*n + j (mismo orden que .ravel() de la
    malla de airbus_harness)."""
    m = n * n
    i, j = _idx(n)
    filas = i * n + j
    cols = ((i + di) % n) * n + ((j + dj) % n)
    return sp.csr_matrix((np.ones(m), (filas, cols)), shape=(m, m))


def matrices_fd(n, re, p=ah.PARAMS_STATEMENT):
    """A1, A2 del semi-discreto de fd2. Ver cabecera para el origen de cada
    bloque. Devuelve (A1 csr m x m, A2 csr m x m^2, m)."""
    _, _, h, _ = ah._malla(n, p)
    nu = ah.nu_de_re(re, p)
    m = n * n

    Dx = (_shift_matrix(n, +1, 0) - _shift_matrix(n, -1, 0)) / (2.0 * h)
    Dy = (_shift_matrix(n, 0, +1) - _shift_matrix(n, 0, -1)) / (2.0 * h)
    Lap = (_shift_matrix(n, +1, 0) + _shift_matrix(n, -1, 0)
           + _shift_matrix(n, 0, +1) + _shift_matrix(n, 0, -1)
           - 4.0 * sp.identity(m, format="csr")) / h ** 2

    # P: inversa EXACTA del Laplaciano discreto de 5 puntos con media nula,
    # construida por la misma diagonalizacion de Fourier que usa _brazo_fd
    # (se aplica a la base canonica: densa, pero m es chico donde el brazo
    # cuantico llega, y asi P es literalmente el mismo operador).
    mm = np.arange(n)
    lam1 = -(2.0 - 2.0 * np.cos(2.0 * np.pi * mm / n)) / h ** 2
    lam = lam1[:, None] + lam1[None, :]
    lam_inv = 1.0 / np.where(lam == 0.0, 1.0, lam)

    P = np.empty((m, m))
    e = np.zeros((n, n))
    for k in range(m):
        e.flat[k] = 1.0
        wh = np.fft.fft2(e)
        psih = -wh * lam_inv
        psih[0, 0] = 0.0
        P[:, k] = np.real(np.fft.ifft2(psih)).ravel()
        e.flat[k] = 0.0

    Bu = Dy @ P          # u' = d(psi)/dy
    Bv = -(Dx @ P)       # v' = -d(psi)/dx

    A1 = (-p["Uc"] * Dx - p["Vc"] * Dy + nu * Lap).tocsr()

    # A2[i, a*m + b] = -( Bu[i,a]*Dx[i,b] + Bv[i,a]*Dy[i,b] ).
    # Dx y Dy tienen 2 no-nulos por fila: se recorre el COO de cada uno y se
    # cruza vectorizado con la fila densa de Bu/Bv.
    filas, cols, vals = [], [], []
    ar = np.arange(m)
    for D, B in ((Dx.tocoo(), Bu), (Dy.tocoo(), Bv)):
        for i_, b_, v_ in zip(D.row, D.col, D.data):
            filas.append(np.full(m, i_))
            cols.append(ar * m + b_)
            vals.append(-B[i_, :] * v_)
    A2 = sp.csr_matrix((np.concatenate(vals),
                        (np.concatenate(filas), np.concatenate(cols))),
                       shape=(m, m * m))
    return A1, A2, m


def rhs_cuadratico(A1, A2, w):
    """dw/dt = A1 w + A2 (w kron w). Escrito aparte para poder probarlo contra
    _brazo_fd sin pasar por Carleman."""
    return A1 @ w + A2 @ np.kron(w, w)


# ===========================================================================
# 2 · MATRIZ DE CARLEMAN C (bloque-bidiagonal, truncada en K)
# ===========================================================================
def dimension_carleman(m, K):
    """dim REAL del sistema linealizado = suma_{j=1..K} m^j. Se calcula con
    enteros de Python (sin overflow) porque su valor es justamente lo que se
    compara contra el muro."""
    return sum(m ** j for j in range(1, K + 1))


def _eye(k):
    return sp.identity(k, format="csr")


def matriz_carleman(A1, A2, m, K):
    """C de dimension dim x dim, con dim = suma m^j. Bloque (j,j) = A1^{(j)},
    bloque (j,j+1) = A2^{(j)} salvo j=K (truncado)."""
    if K < 1:
        raise ValueError("orden de Carleman K debe ser >= 1")
    offs = [0]
    for j in range(1, K + 1):
        offs.append(offs[-1] + m ** j)
    dim = offs[-1]

    bloques = [[None] * K for _ in range(K)]
    for j in range(1, K + 1):
        # A1^{(j)} = suma_s I kron A1 kron I
        acc = None
        for s in range(1, j + 1):
            t = sp.kron(_eye(m ** (s - 1)), sp.kron(A1, _eye(m ** (j - s)),
                                                    format="csr"), format="csr")
            acc = t if acc is None else (acc + t)
        bloques[j - 1][j - 1] = acc
        if j < K:
            acc2 = None
            for s in range(1, j + 1):
                t = sp.kron(_eye(m ** (s - 1)), sp.kron(A2, _eye(m ** (j - s)),
                                                        format="csr"), format="csr")
                acc2 = t if acc2 is None else (acc2 + t)
            bloques[j - 1][j] = acc2
    C = sp.bmat(bloques, format="csr")
    assert C.shape == (dim, dim)
    return C, offs


def estado_carleman_inicial(w0, K):
    """y0 = (w0, w0 kron w0, ..., w0^{kron K})."""
    partes, cur = [], w0
    for _ in range(K):
        partes.append(cur)
        cur = np.kron(cur, w0)
    return np.concatenate(partes)


# ===========================================================================
# 3 · SIMULADOR DE STATEVECTOR REAL (sin librerias cuanticas: no hay ninguna
#     instalada, se comprobo; y el ansatz es real, asi que basta numpy)
# ===========================================================================
def _ry(v, q, nq, th):
    a = v.reshape(1 << q, 2, 1 << (nq - q - 1))
    c, s = np.cos(th / 2.0), np.sin(th / 2.0)
    v0, v1 = a[:, 0, :], a[:, 1, :]
    out = np.empty_like(a)
    out[:, 0, :] = c * v0 - s * v1
    out[:, 1, :] = s * v0 + c * v1
    return out.reshape(-1)


def _dry(v, q, nq):
    """Generador -i*Y/2 = [[0,-1/2],[1/2,0]] (real). dU/dtheta = G U."""
    a = v.reshape(1 << q, 2, 1 << (nq - q - 1))
    out = np.empty_like(a)
    out[:, 0, :] = -0.5 * a[:, 1, :]
    out[:, 1, :] = 0.5 * a[:, 0, :]
    return out.reshape(-1)


def _perm_cnot(nq, c, t):
    idx = np.arange(1 << nq)
    bit_c = (idx >> (nq - 1 - c)) & 1
    return np.where(bit_c == 1, idx ^ (1 << (nq - 1 - t)), idx)


def construir_circuito(nq, capas):
    """ops: lista de ('ry', qubit, i_param) y ('cnot', perm). n_param = nq*(capas+1)."""
    ops, ip = [], 0
    for l in range(capas + 1):
        for q in range(nq):
            ops.append(("ry", q, ip))
            ip += 1
        if l < capas:
            for q in range(nq):
                ops.append(("cnot", (q + 1) % nq, _perm_cnot(nq, q, (q + 1) % nq)))
    return ops, ip


def _forward(theta, nq, ops):
    v = np.zeros(1 << nq)
    v[0] = 1.0
    for op in ops:
        v = _ry(v, op[1], nq, theta[op[2]]) if op[0] == "ry" else v[op[2]]
    return v


def _psi_y_derivadas(theta, nq, ops, nparam):
    """Devuelve psi y la matriz (nparam x 2^nq) de derivadas d_j psi.
    d_j psi = U_{>j} G_q U_j ... U_1 |0>, con G el generador real de arriba."""
    v = np.zeros(1 << nq)
    v[0] = 1.0
    marcas = []
    for oi, op in enumerate(ops):
        if op[0] == "ry":
            v = _ry(v, op[1], nq, theta[op[2]])
            marcas.append((oi, op[1], op[2], v.copy()))
        else:
            v = v[op[2]]
    psi = v
    D = np.empty((nparam, 1 << nq))
    for oi, q, ip, st in marcas:
        d = _dry(st, q, nq)
        for op in ops[oi + 1:]:
            d = _ry(d, op[1], nq, theta[op[2]]) if op[0] == "ry" else d[op[2]]
        D[ip] = d
    return psi, D


# ===========================================================================
# 4 · EVOLUCION VARIACIONAL (McLachlan) DEL SISTEMA LINEAL
# ===========================================================================
class MuroCuantico(Exception):
    """El brazo cuantico no puede resolver el punto. Lleva motivo MEDIDO y las
    mediciones que lo respaldan: nunca se convierte en un valor por defecto."""

    def __init__(self, motivo, medicion):
        super().__init__(motivo)
        self.motivo = motivo
        self.medicion = medicion


def ajustar_estado_inicial(y0, nq, ops, nparam, semilla=SEMILLA):
    obj = y0 / np.linalg.norm(y0)

    def f(th):
        psi, D = _psi_y_derivadas(th, nq, ops, nparam)
        ov = float(psi @ obj)
        return -ov, -(D @ obj)

    rng = np.random.default_rng(semilla)
    th0 = rng.uniform(-0.1, 0.1, nparam)
    r = minimize(f, th0, jac=True, method="L-BFGS-B",
                 options={"maxiter": 600, "ftol": 1e-14, "gtol": 1e-12})
    theta = r.x
    psi = _forward(theta, nq, ops)
    ov = float(psi @ obj)
    if ov < 0:            # el signo global es libre: se absorbe en r
        pass
    return theta, ov


def evolucionar_variacional(C, y0, nq, ops, nparam, t_final, pasos,
                            lam=LAMBDA_TIKHONOV, semilla=SEMILLA):
    """RK4 sobre (theta, r) con el sistema de McLachlan. Devuelve
    (y_final, diagnosticos). Levanta MuroCuantico si no puede seguir."""
    theta, ov0 = ajustar_estado_inicial(y0, nq, ops, nparam, semilla)
    norma0 = float(np.linalg.norm(y0))
    r = ov0 * norma0                      # proyeccion de y0 sobre el ansatz
    dt = t_final / pasos
    res_max = 0.0

    def campo(th, rr):
        nonlocal res_max
        psi, D = _psi_y_derivadas(th, nq, ops, nparam)
        Cpsi = C @ psi
        c = float(psi @ Cpsi)
        objetivo = Cpsi - c * psi         # componente tangencial a representar
        M = D @ D.T
        V = D @ objetivo
        thd = np.linalg.solve(M + lam * np.eye(nparam), V)
        den = float(np.linalg.norm(objetivo))
        if den > 0:
            res = float(np.linalg.norm(D.T @ thd - objetivo) / den)
            res_max = max(res_max, res)
        return thd, c * rr

    pasos_hechos = 0
    for _ in range(pasos):
        k1t, k1r = campo(theta, r)
        k2t, k2r = campo(theta + 0.5 * dt * k1t, r + 0.5 * dt * k1r)
        k3t, k3r = campo(theta + 0.5 * dt * k2t, r + 0.5 * dt * k2r)
        k4t, k4r = campo(theta + dt * k3t, r + dt * k3r)
        theta = theta + (dt / 6.0) * (k1t + 2 * k2t + 2 * k3t + k4t)
        r = r + (dt / 6.0) * (k1r + 2 * k2r + 2 * k3r + k4r)
        pasos_hechos += 1
        if not np.all(np.isfinite(theta)) or not np.isfinite(r):
            raise MuroCuantico(
                "no-finitud en la evolucion variacional",
                {"paso_no_finito": pasos_hechos, "pasos_planeados": pasos,
                 "dt": dt})
        if abs(r) > FACTOR_DIVERGENCIA * norma0:
            raise MuroCuantico(
                "no convergencia: la norma del estado crecio por sobre el factor "
                "declarado",
                {"paso_divergente": pasos_hechos, "norma_actual": abs(r),
                 "norma_inicial": norma0, "factor_limite": FACTOR_DIVERGENCIA})

    psi = _forward(theta, nq, ops)
    y = r * psi
    diag = {
        "overlap_inicial": ov0,
        "infidelidad_inicial": 1.0 - abs(ov0),
        "residuo_mclachlan_max": res_max,
        "pasos_reales": pasos_hechos,
        "dt_real": dt,
    }
    return y, diag


# ===========================================================================
# 5 · EL BRAZO: se enchufa en BRAZOS de airbus_harness con la MISMA firma
# ===========================================================================
def _velocidad_desde_w(w_plano, n, re, p=ah.PARAMS_STATEMENT):
    """Misma reconstruccion (u,v) que _brazo_fd: Poisson exacta del 5 puntos."""
    _, _, h, _ = ah._malla(n, p)
    w_ = w_plano.reshape(n, n)
    mm = np.arange(n)
    lam1 = -(2.0 - 2.0 * np.cos(2.0 * np.pi * mm / n)) / h ** 2
    lam = lam1[:, None] + lam1[None, :]
    lam_inv = 1.0 / np.where(lam == 0.0, 1.0, lam)
    wh = np.fft.fft2(w_)
    psih = -wh * lam_inv
    psih[0, 0] = 0.0
    psi = np.real(np.fft.ifft2(psih))
    u = p["Uc"] + (np.roll(psi, -1, axis=1) - np.roll(psi, 1, axis=1)) / (2.0 * h)
    v = p["Vc"] - (np.roll(psi, -1, axis=0) - np.roll(psi, 1, axis=0)) / (2.0 * h)
    return u, v


def brazo_cuantico(n, re, t_final, cfl=0.5, p=ah.PARAMS_STATEMENT,
                   K=None, capas=None, pasos=None, semilla=SEMILLA,
                   qubits_max=QUBITS_MAX, dim_max=DIM_MAX):
    """Carleman(K) + evolucion variacional en statevector.

    Devuelve el mismo dict que los brazos clasicos SI resuelve. Si NO puede,
    devuelve {"no_resuelto": True, "motivo": ..., "medicion": {...}} y NUNCA
    un campo u/v: la ausencia no viaja como valor (guardia 5)."""
    K = CARLEMAN_ORDEN if K is None else int(K)
    capas = ANSATZ_CAPAS if capas is None else int(capas)
    pasos = PASOS_TIEMPO if pasos is None else int(pasos)
    m = n * n
    esquema = ("Carleman orden K + evolucion variacional McLachlan en "
               "statevector real (ansatz RY + CNOT anillo), base fd2")

    # --- muro por dimension, ANTES de construir nada (D6) ---
    dim = dimension_carleman(m, K)
    nq = int(np.ceil(np.log2(dim))) if dim > 1 else 1
    medicion_base = {"m_celdas": m, "carleman_orden_pedido": K,
                     "dim_sistema": dim, "n_qubits_requeridos": nq,
                     "dim_max": dim_max, "qubits_max": qubits_max}
    if dim > dim_max or nq > qubits_max:
        return {"no_resuelto": True, "esquema": esquema,
                "motivo": ("dimension del sistema de Carleman por sobre la cota "
                           "declarada: dim=%d (max %d), n_qubits=%d (max %d)"
                           % (dim, dim_max, nq, qubits_max)),
                "medicion": medicion_base}

    try:
        A1, A2, _ = matrices_fd(n, re, p)
        C, offs = matriz_carleman(A1, A2, m, K)
    except MemoryError:
        return {"no_resuelto": True, "esquema": esquema,
                "motivo": "MemoryError al construir la matriz de Carleman",
                "medicion": medicion_base}

    # Orden y dimension REALES leidos del objeto construido, no de lo pedido.
    K_real = len(offs) - 1
    dim_real = int(C.shape[0])
    nq_real = int(np.ceil(np.log2(dim_real))) if dim_real > 1 else 1
    medicion_base.update({"carleman_orden_real": K_real,
                          "dim_sistema_real": dim_real,
                          "nnz_C": int(C.nnz)})

    w0 = ah._vorticidad_inicial(n, p).ravel()
    y0 = estado_carleman_inicial(w0, K_real)
    y0_pad = np.zeros(1 << nq_real)
    y0_pad[:dim_real] = y0

    Cp = sp.csr_matrix((1 << nq_real, 1 << nq_real))
    Cp = sp.bmat([[C, None], [None, sp.csr_matrix(((1 << nq_real) - dim_real,
                                                   (1 << nq_real) - dim_real))]],
                 format="csr") if (1 << nq_real) > dim_real else C.tocsr()

    ops, nparam = construir_circuito(nq_real, capas)
    try:
        y_fin, diag = evolucionar_variacional(Cp, y0_pad, nq_real, ops, nparam,
                                              t_final, pasos, semilla=semilla)
    except MuroCuantico as e:
        med = dict(medicion_base)
        med.update(e.medicion)
        med["n_parametros"] = nparam
        return {"no_resuelto": True, "esquema": esquema,
                "motivo": e.motivo, "medicion": med}
    if not np.all(np.isfinite(y_fin)):
        return {"no_resuelto": True, "esquema": esquema,
                "motivo": "estado final no finito tras la evolucion variacional",
                "medicion": dict(medicion_base,
                                 n_no_finitos=int(np.sum(~np.isfinite(y_fin))))}

    w_var = y_fin[:m]
    u, v = _velocidad_desde_w(w_var, n, re, p)

    # DIAGNOSTICO SEPARADO (D7): el MISMO sistema de Carleman resuelto exacto.
    # Sirve para saber cuanto del error es truncamiento y cuanto es el ansatz.
    y_ex = spla.expm_multiply(C * t_final, y0)
    u_ex, v_ex = _velocidad_desde_w(y_ex[:m], n, re, p)
    u_ref, v_ref = ah.arbitro_analitico(n, t_final, re, p)

    return {
        "u": u, "v": v, "w": w_var.reshape(n, n),
        "dt": t_final / pasos, "pasos": diag["pasos_reales"],
        "esquema": esquema,
        "carleman": {
            "orden_real": K_real,
            "dim_sistema_real": dim_real,
            "n_qubits": nq_real,
            "nnz_C": int(C.nnz),
            "n_parametros_ansatz": nparam,
            "capas_ansatz": capas,
            "semilla": int(semilla),
            "lambda_tikhonov": LAMBDA_TIKHONOV,
            "overlap_inicial": diag["overlap_inicial"],
            "infidelidad_inicial": diag["infidelidad_inicial"],
            "residuo_mclachlan_max": diag["residuo_mclachlan_max"],
            "error_l2_rel_carleman_exacto": ah.error_l2_rel(u_ex, v_ex, u_ref, v_ref),
            "decisiones_no_prefijadas": DECISIONES_NO_PREFIJADAS,
        },
    }


def error_carleman_exacto(n, re, t_final, K, p=ah.PARAMS_STATEMENT):
    """Solo la capa de Carleman (sin variacional): resuelve exp(C t) y0 y mide
    contra el arbitro analitico. Es la herramienta con la que se prueba la
    convergencia EN EL ORDEN K aislada del ansatz."""
    A1, A2, m = matrices_fd(n, re, p)
    C, _ = matriz_carleman(A1, A2, m, K)
    w0 = ah._vorticidad_inicial(n, p).ravel()
    y0 = estado_carleman_inicial(w0, K)
    y = spla.expm_multiply(C * t_final, y0)
    u, v = _velocidad_desde_w(y[:m], n, re, p)
    u_r, v_r = ah.arbitro_analitico(n, t_final, re, p)
    return ah.error_l2_rel(u, v, u_r, v_r), y[:m]


# La opcion {"carleman": True} vive en el REGISTRO, no en lo que el brazo
# devuelve: asi la guardia 4 la exige desde afuera y una mutacion adentro del
# brazo no puede apagarsela a si misma.
BRAZO_CUANTICO = ("carleman_variacional", brazo_cuantico, {"carleman": True})


def brazos_con_cuantico(K=None, capas=None, pasos=None, semilla=SEMILLA,
                        qubits_max=QUBITS_MAX, dim_max=DIM_MAX):
    """Los dos clasicos + el cuantico, para pasarle a correr_punto(brazos=...)."""
    def _b(n, re, t_final, cfl=0.5, p=ah.PARAMS_STATEMENT):
        return brazo_cuantico(n, re, t_final, cfl, p, K=K, capas=capas,
                              pasos=pasos, semilla=semilla,
                              qubits_max=qubits_max, dim_max=dim_max)
    _b.__name__ = "brazo_cuantico_configurado"
    return tuple(ah.BRAZOS) + (("carleman_variacional", _b, {"carleman": True}),)
