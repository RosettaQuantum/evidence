#!/usr/bin/env python3
"""El banco de ensayo: mide DONDE SE ACABA ESTA MAQUINA, creciendo hasta que se rompe.

QUE ES Y POR QUE EXISTE
-----------------------
El muro de 22 variables que publicamos NO es una constante de la fisica: es lo que cupo
en el corredor de CI —16 GB, 4 nucleos— medido el 2026-08-13. Este archivo mide el muro
de la maquina en la que corre, sea cual sea.

Importa porque el muro define el producto. Es el punto donde un cliente deja de pagar
computo normal y empieza a pagar hardware cuantico, y ese punto es distinto en cada
maquina. Publicar «22» sin decir sobre que maquina es la clase de cifra sin metodo que
esta casa persigue (CLAUDE.md Rosetta §1 quater).

QUE MIDE Y QUE NO
-----------------
Mide el brazo cuantico SOLO: construir el circuito QAOA sobre K qubits y dar unos pocos
pasos de optimizador. No corre CP-SAT, ni el flujo AC, ni la fuerza bruta. Es a proposito:
el muro que buscamos es el del simulador, y mezclarlo con el resto mediria otra cosa.

**Lo que produce NO se sella.** Las versiones de librerias de un Mac no son las del
entorno declarado de CI, asi que un numero de aqui sirve para decidir donde medir, no
para archivar. Un ensayo no es evidencia.

Uso:
    python3 banco_de_ensayo.py                 # crece de 18 hasta que se rompe
    python3 banco_de_ensayo.py 20 22 24 26     # solo estos tamaños
"""
import json
import os
import resource
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "banco_de_ensayo.csv")
PASOS = 3          # pocos: buscamos el muro de memoria, no la convergencia
TOPE_S = 180       # si un tamaño no termina en 3 min, ya no sirve para iterar rapido
MIN_LIBRE_GB = 6.0 # por debajo de esto NO se corre. Ver el comentario de abajo.


def ram_disponible_gb():
    """Memoria REALMENTE disponible, no la que `top` llama «unused».

    DEFECTO DE MI PRIMERA VERSION, encontrado el 2026-08-17 por el agente de MPS:
    leia `PhysMem: ... N unused` de `top`. En macOS ese numero es casi cero **siempre**,
    porque el sistema usa toda la RAM libre como cache de disco y la libera cuando hace
    falta. Con 10 GB disponibles y presion de kernel normal, mi guardia abortaba.

    Un guardia que grita sin razon no protege: **lo desactiva el primero que lo choque**,
    y entonces no protege nunca mas. Un falso positivo cuesta mas caro que la ausencia
    del control, porque ademas se lleva la confianza en el resto.

    Lo correcto en macOS es sumar las paginas libres MAS las inactivas y las
    especulativas —que el sistema puede recuperar de inmediato— y mirar aparte la
    presion de memoria, que es la senal real de ahogo.
    """
    import re as _re
    out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    m = _re.search(r"page size of (\d+) bytes", out)
    pag = int(m.group(1)) if m else 4096
    def paginas(nombre):
        mm = _re.search(r"Pages %s:\s+(\d+)" % nombre, out)
        return int(mm.group(1)) if mm else 0
    libres = paginas("free") + paginas("inactive") + paginas("speculative")
    return libres * pag / (1024 ** 3)


def presion_de_memoria_pct():
    """Cuanta presion declara el propio sistema. None si no se puede leer."""
    import re as _re
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    m = _re.search(r"System-wide memory free percentage:\s*(\d+)%", out)
    return (100 - int(m.group(1))) if m else None


def guardia_de_memoria():
    """Se niega a correr si la maquina no tiene aire. NO es prudencia: es un caso real.

    El 2026-08-14 corri este banco con 984 MB libres, habiendolo MEDIDO un minuto antes.
    El pico de K=18 fue de 4,34 GB, el sistema se quedo sin memoria de aplicacion y
    Nicholas tuvo que reiniciar el Mac con todo abierto.

    El dato que lo habria evitado estaba en pantalla y no lo use. Por eso el chequeo vive
    aqui y no en la cabeza del que lanza: un control que depende de acordarse no es un
    control (CLAUDE.md Rosetta §4).

    Falla cerrado: si NO se puede leer la memoria, tampoco se corre.
    """
    libre = ram_disponible_gb()
    presion = presion_de_memoria_pct()
    if not libre:
        raise SystemExit("ABORTA: no pude leer la memoria disponible. Sin ese dato no se "
                         "corre — este banco puede pedir varios GB y tumbar la maquina.")
    # Dos condiciones, y ninguna sola basta: memoria disponible Y presion no critica.
    # La primera version miraba una sola cifra, y la equivocada.
    if presion is not None and presion >= 85:
        raise SystemExit("ABORTA: el sistema declara %d%% de presion de memoria. Hay "
                         "%.1f GB recuperables, pero el kernel ya esta apretando: correr "
                         "ahora es como corrio la vez que hubo que reiniciar." % (presion, libre))
    if libre < MIN_LIBRE_GB:
        raise SystemExit(
            "ABORTA: %.1f GB libres, y el minimo es %.1f.\n"
            "  K=18 pico en 4,34 GB de RAM con un vector de estado de solo 4 MB: lo que\n"
            "  crece no es el vector, es la cinta de derivadas de PennyLane.\n"
            "  Cierra aplicaciones y vuelve a intentar. Correr asi ya tumbo esta maquina\n"
            "  una vez." % (libre, MIN_LIBRE_GB))
    return libre


HIJO = r'''
import json, sys, time, resource
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp

K, PASOS = int(sys.argv[1]), int(sys.argv[2])
CAPAS = max(2, K // 4)
rs = np.random.RandomState(7)

# Un QUBO cualquiera del mismo porte que los de E.ON. No importa que resuelva: importa
# que el circuito tenga el mismo tamaño y la misma profundidad.
lin = rs.randn(K); cua = np.triu(rs.randn(K, K), 1)
coef, obs = [], []
for i in range(K):
    coef.append(float(lin[i])); obs.append(qml.PauliZ(i))
    for j in range(i + 1, K):
        coef.append(float(cua[i, j])); obs.append(qml.PauliZ(i) @ qml.PauliZ(j))
H = qml.Hamiltonian(coef, obs)

dev = qml.device("default.qubit", wires=K)

def circ(p):
    for w in range(K):
        qml.Hadamard(wires=w)
    for l in range(CAPAS):
        qml.templates.ApproxTimeEvolution(H, p[0][l], 1)
        for w in range(K):
            qml.RX(2 * p[1][l], wires=w)

@qml.qnode(dev)
def coste(p):
    circ(p); return qml.expval(H)

t0 = time.time()
params = pnp.array(0.01 * rs.rand(2, CAPAS), requires_grad=True)
opt = qml.AdamOptimizer(0.05)
for _ in range(PASOS):
    params = opt.step(coste, params)
dt = time.time() - t0
pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**3)  # macOS: bytes
print(json.dumps({"K": K, "capas": CAPAS, "segundos": round(dt, 2),
                  "pico_gb": round(pico, 3),
                  "vector_estado_mb": round(16 * (2 ** K) / 1048576, 2)}))
'''


def probar(py, k):
    """Corre UN tamaño en un proceso aparte, para que si muere no se lleve al padre."""
    t0 = time.time()
    try:
        r = subprocess.run([py, "-c", HIJO, str(k), str(PASOS)],
                           capture_output=True, text=True, timeout=TOPE_S)
    except subprocess.TimeoutExpired:
        return {"K": k, "estado": "reloj", "segundos": TOPE_S,
                "motivo": "no termino en %ds" % TOPE_S}
    if r.returncode != 0:
        cola = (r.stderr.strip().splitlines() or ["sin stderr"])[-1][:120]
        # Un proceso muerto por el sistema (SIGKILL = -9) casi siempre es memoria.
        motivo = ("lo mato el sistema, casi seguro memoria" if r.returncode < 0
                  else cola)
        return {"K": k, "estado": "murio", "segundos": round(time.time() - t0, 1),
                "motivo": motivo, "codigo": r.returncode}
    d = json.loads(r.stdout.strip().splitlines()[-1])
    d["estado"] = "ok"
    return d


if __name__ == "__main__":
    py = sys.executable
    libre = guardia_de_memoria()
    ks = [int(a) for a in sys.argv[1:]] or list(range(18, 33, 2))
    print("BANCO DE ENSAYO — %s" % py)
    print("memoria libre al arrancar: %.1f GB (minimo exigido %.1f)\n" % (libre, MIN_LIBRE_GB))
    print("%-4s %-8s %-10s %-11s %-12s %s" %
          ("K", "capas", "segundos", "pico RAM", "vector est.", "estado"))
    filas = []
    for k in ks:
        d = probar(py, k)
        filas.append(d)
        print("%-4d %-8s %-10s %-11s %-12s %s" % (
            d["K"], d.get("capas", "—"), d.get("segundos", "—"),
            "%.2f GB" % d["pico_gb"] if d.get("pico_gb") else "—",
            "%.0f MB" % d["vector_estado_mb"] if d.get("vector_estado_mb") else "—",
            d["estado"] + ("" if d["estado"] == "ok" else " — " + d.get("motivo", ""))))
        if d["estado"] != "ok":
            print("\nEl muro de ESTA maquina esta en K = %d: el ultimo tamaño que "
                  "termino." % (ks[ks.index(k) - 1] if ks.index(k) else 0))
            break
    else:
        print("\nNinguno se rompio. El muro esta por encima de K = %d." % ks[-1])

    nuevo = not os.path.exists(SALIDA)
    with open(SALIDA, "a") as f:
        if nuevo:
            f.write("K,capas,segundos,pico_gb,vector_estado_mb,estado,motivo\n")
        for d in filas:
            f.write("%s,%s,%s,%s,%s,%s,%s\n" % (
                d["K"], d.get("capas", ""), d.get("segundos", ""), d.get("pico_gb", ""),
                d.get("vector_estado_mb", ""), d["estado"],
                (d.get("motivo") or "").replace(",", ";")))
    print("acumulado en %s" % os.path.basename(SALIDA))
