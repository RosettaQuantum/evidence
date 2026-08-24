#!/usr/bin/env python3
"""El costo de la corrida en hardware del brazo cuantico de HSBC, DERIVADO del diseño.

Regla de la casa (§8 de CLAUDE.md y condicion 1 del notario): el costo que se le presenta
a Nicholas sale del codigo que lo produce, no de una cifra recordada. Este script es ese
codigo: toma el diseño del prereg, aplica la tarifa publicada y devuelve el numero.

TARIFA — leida de https://aws.amazon.com/braket/pricing/ el 2026-08-21, tabla «Quantum
Computers». Se copia aqui con su fecha: si AWS la cambia, esta cifra caduca y el script
tiene que releerla antes de gastar.
"""
import json

FUENTE = {"url": "https://aws.amazon.com/braket/pricing/", "leida": "2026-08-21",
          "tabla": "Quantum Computers — per-task y per-shot"}
# per_task es identico en todos los QPU; per_shot varia por familia
TARIFA = {                       # USD
    "IQM Garnet":     {"task": 0.30, "shot": 0.00145},
    "IQM Emerald":    {"task": 0.30, "shot": 0.00160},
    "Rigetti Cepheus":{"task": 0.30, "shot": 0.000425},
    "IonQ Forte":     {"task": 0.30, "shot": 0.08000},
    "AQT IBEX-Q1":    {"task": 0.30, "shot": 0.02350},
}
MIN_SHOTS_IONQ_EM = 2500   # IonQ exige >=2500 disparos con mitigacion de error

def costo(n_test, n_soporte, shots, backend, agrupa_por_tarea=1):
    """El kernel en hardware NO tiene el atajo del statevector: cada par (x_test, x_sop)
    es un circuito distinto. Una tarea puede repetir UN circuito con muchos disparos, asi
    que el numero de tareas es el numero de PARES, no de disparos."""
    pares = n_test * n_soporte
    tareas = -(-pares // agrupa_por_tarea)      # techo
    t = TARIFA[backend]
    c_tareas = tareas * t["task"]
    c_shots = pares * shots * t["shot"]
    return {"backend": backend, "n_test": n_test, "n_soporte": n_soporte,
            "shots_por_circuito": shots, "pares_de_kernel": pares, "tareas": tareas,
            "usd_tareas": round(c_tareas, 2), "usd_disparos": round(c_shots, 2),
            "usd_total": round(c_tareas + c_shots, 2)}

if __name__ == "__main__":
    print("TARIFA leida de %s el %s\n" % (FUENTE["url"], FUENTE["leida"]))
    print("=== lo que el prereg DESCARTA por costo: puntuar el test completo ===")
    for b in ("Rigetti Cepheus", "IQM Garnet"):
        c = costo(56962, 2000, 100, b)
        print("  %-16s %.2e pares -> USD %s" % (b, c["pares_de_kernel"],
                                                "{:,.0f}".format(c["usd_total"])))
    print("\n=== la DEMOSTRACION acotada que el prereg propone ===")
    print("  %-16s %-8s %-8s %-7s %12s %12s %12s"
          % ("backend", "n_test", "n_sop", "shots", "pares", "USD tareas", "USD total"))
    for b in ("Rigetti Cepheus", "IQM Garnet", "IonQ Forte"):
        for n_test, n_sop, sh in ((200, 50, 100), (500, 100, 100)):
            c = costo(n_test, n_sop, sh, b)
            print("  %-16s %-8d %-8d %-7d %12s %12s %12s"
                  % (b, n_test, n_sop, sh, "{:,}".format(c["pares_de_kernel"]),
                     "{:,.0f}".format(c["usd_tareas"]), "{:,.0f}".format(c["usd_total"])))
    # POR QUE ESTO NO IMPRIME UNA SOLA FRASE GENERAL
    # -----------------------------------------------
    # La version anterior imprimia "EL COSTO LO DOMINAN LAS TAREAS, no los disparos" y
    # debajo UN ejemplo, el de Rigetti. Es cierto en Rigetti (87,6 %) y FALSO en IonQ
    # Forte (3,6 %), cuyo disparo cuesta 188 veces mas. Esa frase viajo tal cual al sello
    # RQ-PREREG-HSBC-003-CUANTICO, que quedo afirmando "ni reducir disparos ni cambiar de
    # proveedor mueve el costo" — desmentido por su propia tabla, dos lineas mas abajo.
    #
    # Un promedio o un ejemplo unico esconden la dispersion. Ahora se imprime la cuota POR
    # BACKEND y la conclusion se DERIVA de ellas, no se escribe de antemano.
    cuotas = {}
    for b_ in TARIFA:
        c = costo(200, 50, 100, b_)
        cuotas[b_] = 100.0 * c["usd_tareas"] / c["usd_total"]
    print("\nQUE DOMINA EL COSTO — depende del backend (demostracion 200 x 50):")
    for b_, q in sorted(cuotas.items(), key=lambda kv: -kv[1]):
        c = costo(200, 50, 100, b_)
        print("  %-16s tareas %5.1f %%  disparos %5.1f %%   total USD %10s"
              % (b_, q, 100 - q, "{:,.0f}".format(c["usd_total"])))
    lo, hi = min(cuotas.values()), max(cuotas.values())
    # FALLA CERRADO: si la cuota cruza el 50 %, NO existe una frase general verdadera y el
    # programa se niega a insinuarla. Si algun dia todos los backends caen del mismo lado,
    # esta rama deja de dispararse sola y recien ahi la generalizacion seria legitima.
    if lo < 50.0 <= hi:
        print("\n  NO hay una afirmacion general valida: las tareas dominan en %s (%.1f %%)"
              % (max(cuotas, key=cuotas.get), hi))
        print("  y NO dominan en %s (%.1f %%). Cualquier frase que diga 'el costo lo "
              "dominan las tareas'" % (min(cuotas, key=cuotas.get), lo))
        print("  sin nombrar el backend es falsa en al menos uno.")
    else:
        print("\n  las tareas dominan en TODOS los backends de la tabla (%.1f %% a %.1f %%)"
              % (lo, hi))
    totales = {b_: costo(200, 50, 100, b_)["usd_total"] for b_ in TARIFA}
    mn, mx = min(totales, key=totales.get), max(totales, key=totales.get)
    print("\n  LO INVARIANTE es la tarifa por tarea: USD %.2f, identica en los %d backends."
          % (TARIFA[mn]["task"], len(TARIFA)))
    print("  LO QUE SI SE MUEVE: el mismo trabajo cuesta USD %s en %s y USD %s en %s "
          "— factor %.1f." % ("{:,.0f}".format(totales[mn]), mn,
                              "{:,.0f}".format(totales[mx]), mx, totales[mx]/totales[mn]))
