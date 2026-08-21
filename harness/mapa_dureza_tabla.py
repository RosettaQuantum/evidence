#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La tabla de las tres curvas, leida de los JSON que dejo `mapa_dureza_eon.py`.

No calcula nada nuevo: solo ordena lo medido. Toda cifra que aparece aqui sale de un archivo
`punto_K??.json`, y el denominador (puntos completados / pedidos) va siempre.
"""
import glob
import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(AQUI, "mapa_dureza")


def humano(s):
    if s is None:
        return "—"
    if s < 60:
        return "%.0f s" % s
    if s < 3600:
        return "%.1f min" % (s / 60)
    if s < 86400 * 2:
        return "%.1f h" % (s / 3600)
    if s < 86400 * 730:
        return "%.0f d" % (s / 86400)
    return "%.2g años" % (s / (86400 * 365.25))


def main():
    fs = sorted(glob.glob(os.path.join(DIR, "punto_K*.json")))
    if not fs:
        raise SystemExit("ABORTA: no hay ningun punto medido en %s" % DIR)
    ds = [json.load(open(f)) for f in fs]
    ds.sort(key=lambda d: d["K"])
    p = ds[0]
    print("MAPA DE DUREZA — E.ON expansion de red bajo incertidumbre")
    print("red=%s  S=%d escenarios (fijo)  razon k/K=%.2f  T_OP=%.0f s  semillas=%s  "
          "solucionador=SCIP"
          % (p["red"], p["S"], p["razon_budget"], p["T_OP_s"], p["reglas"]["semillas"]))
    print()
    cab = ("%-4s %-4s %14s %11s %11s %10s %10s %8s %9s %11s %s"
           % ("K", "k", "C(K,k)", "enum real", "enum proy", "SCIP min", "SCIP max",
              "OPT/3", "brecha%", "arbitro", "veredicto"))
    print(cab)
    print("-" * len(cab))
    filas = []
    for d in ds:
        e, s, v = d["enumeracion"], d["solucionador"], d["veredicto"]
        real = humano(e.get("segundos_reales")) if e.get("corrio") else "no corre"
        proy = humano(e["segundos_proyectados_1_nucleo"])
        br = s["brecha_cota_max_pct"]
        brtxt = "—" if br is None else ("%.2f" % br)
        arb = ("enumeracion" if d["arbitro"]["hay"]
               else ("SCIP OPTIMAL" if s["n_OPTIMAL"] else "NINGUNO"))
        ver = "DURO" if v["duro"] else ("fragil" if v["fragil"] else "no duro")
        print("%-4d %-4d %14s %11s %11s %10s %10s %8s %9s %11s %s"
              % (d["K"], d["k_budget"], f"{d['combinaciones']:,}", real, proy,
                 humano(s["segundos_min"]), humano(s["segundos_max"]),
                 "%d/%d" % (s["n_OPTIMAL"], s["denominador"]), brtxt, arb, ver))
        filas.append(d)

    print()
    print("CURVA 3 — alcance cuantico (qubits = K) y el peaje clasico de entrada")
    cab3 = "%-4s %-9s %14s %14s %s" % ("K", "qubits", "vector estado", "evals QUBO",
                                       "armar el QUBO (cota sup.)")
    print(cab3)
    print("-" * len(cab3))
    for d in ds:
        c = d["cuantico"]
        vg = c["vector_estado_gb"]
        if vg >= 1:
            vtxt = "%.3g GB" % vg
        elif vg * 1024 >= 1:
            vtxt = "%.1f MB" % (vg * 1024)
        else:
            vtxt = "%.0f KB" % (vg * 1024 * 1024)
        print("%-4d %-9d %14s %14d %s"
              % (d["K"], c["qubits_necesarios"], vtxt, c["evaluaciones_para_armar_el_qubo"],
                 humano(c["segundos_qubo_proyectados_cota_superior"])))

    print()
    print("DISPERSION ENTRE SEMILLAS (regla dura: 3 semillas por punto)")
    cab2 = "%-4s %-24s %-24s %-14s %s" % ("K", "status por semilla", "segundos",
                                          "valor min-max", "dispersion valor %")
    print(cab2)
    print("-" * len(cab2))
    for d in ds:
        s = d["solucionador"]
        st = ",".join(c.get("status", "?")[:4] for c in s["corridas"])
        sg = ",".join("%.0f" % c["segundos"] if c.get("segundos") is not None else "—"
                      for c in s["corridas"])
        vmin, vmax = s["valor_min"], s["valor_max"]
        print("%-4d %-24s %-24s %-14s %s"
              % (d["K"], st, sg,
                 ("%.0f-%.0f" % (vmin, vmax)) if vmin is not None else "—",
                 ("%.4f" % s["dispersion_valor_pct"]) if s["dispersion_valor_pct"] is not None
                 else "0"))

    print()
    print("LA PRUEBA — enumeracion exacta vs solucionador, donde las dos existen")
    for d in ds:
        t = d["prueba_enum_vs_solucionador"]
        if t.get("pasa") is None:
            print("  K=%-3d no aplica: %s" % (d["K"], t.get("motivo")))
        else:
            print("  K=%-3d enumeracion=%.6f  SCIP=%.6f  dif rel=%.3e  -> %s"
                  % (d["K"], t["optimo_enumeracion"], t["optimo_solucionador"],
                     t["diferencia_relativa"], "PASA" if t["pasa"] else "FALLA"))

    duros = [d["K"] for d in ds if d["veredicto"]["duro"]]
    sin_arb = [d["K"] for d in ds if not d["veredicto"]["arbitro_disponible"]]
    # DENOMINADOR de verdad: los K PEDIDOS salen de mapa_dureza_eon.KS (una sola
    # definicion, importada), no de los archivos que existan. Contar los que hay y
    # llamarlo denominador es exactamente el fallo de CLAUDE.md §5 bis: un proceso que
    # declara haber recorrido lo que nunca miro.
    sys.path.insert(0, AQUI)
    import mapa_dureza_eon as M
    pedidos = list(M.KS)
    faltan = [k for k in pedidos if k not in [d["K"] for d in ds]]
    print()
    print("DENOMINADOR: %d puntos medidos de %d pedidos (medidos: %s)"
          % (len(ds), len(pedidos), ", ".join(str(d["K"]) for d in ds)))
    if faltan:
        print("  NO MEDIDOS: %s — no se corrieron; el mapa termina donde termina."
              % ", ".join(str(k) for k in faltan))
    print("DURO segun el criterio escrito antes de medir: %s"
          % (", ".join("K=%d" % k for k in duros) if duros
             else "NINGUN K de los medidos. El problema NUNCA SE VUELVE DURO dentro de lo "
                  "que se pudo medir."))
    print("ARBITRO PERDIDO en: %s"
          % (", ".join("K=%d" % k for k in sin_arb) if sin_arb
             else "ninguno — en todos los K medidos hay arbitro (enumeracion o prueba de "
                  "optimalidad)"))


if __name__ == "__main__":
    main()
