#!/usr/bin/env python3
"""Análisis de la batería del Viaje 2 en ibm_kingston — 7 circuitos, hardware real.

QUÉ SE MIDE, Y POR QUÉ NO SE INVENTA NADA AQUÍ
-----------------------------------------------
Las dos convenciones vienen de la corrida original (`RQ-POC-QPU-001`, julio), no de este
script:

  válido      el circuito codifica la posición de una excitación como ONE-HOT: un shot es
              físicamente válido si tiene EXACTAMENTE un 1. La corrida original reportó
              1.228 de 2.000 = 61,4 %.
  orden       `format(k, "0Nb")[::-1]` — qubit i = bit i. Es la línea de `poc_ibm.py:94`,
              archivada en `evidence/code/poc_ibm@db044b45.py`.
  masa        fracción de los shots VÁLIDOS que caen en los nodos del bolsillo. Los nodos
              del bolsillo salen de `voyage2_manifest.json`, comprometido ANTES de enviar.

EL DISEÑO YA ESTABA COMPROMETIDO
--------------------------------
Los 7 `job_id` y sus roles quedaron sellados dentro de `RQ-REPORT-CLEV-METHOD-001` antes
de que existiera ningún resultado. Este script no elige qué trabajos contar: los lee del
manifiesto y los recorre todos, reportando su denominador.

Uso:  python3 analyze_battery.py
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
QRUN = os.path.join(os.path.dirname(AQUI), "quantum-run")
RES = os.path.join(QRUN, "resultados")
OUT = os.path.join(AQUI, "battery_result.json")
LOG = os.path.join(AQUI, "battery_log.jsonl")

ORIGINAL = {"job_id": "d9mu2bmij12s73ft86t0", "validos": 1228, "shots": 2000,
            "frac_valida": 0.614,
            "fuente": "RQ-POC-QPU-001 / resultados/RESUMEN-QPU.md"}


def anota(evento, **kv):
    with open(LOG, "a") as f:
        f.write(json.dumps({"evento": evento, **kv}, ensure_ascii=False) + "\n")


def counts_de(job):
    d = json.load(open(os.path.join(RES, "poc_job_%s.json" % job)))
    bloque = d["resultado_crudo"][0]["data"]["c"]
    return bloque["counts"], bloque["num_shots"], bloque["num_bits"]


def medir(counts, nbits, pocket):
    """one-hot y masa en el bolsillo, con la convención de la corrida original."""
    total = sum(counts.values())
    validos = 0
    en_bolsillo = 0
    por_nodo = [0] * nbits
    for bits, c in counts.items():
        s = bits.zfill(nbits)[::-1]          # qubit i = bit i
        unos = [i for i, ch in enumerate(s) if ch == "1"]
        if len(unos) != 1:
            continue
        validos += c
        n = unos[0]
        por_nodo[n] += c
        if n in pocket:
            en_bolsillo += c
    return {
        "shots": total,
        "validos": validos,
        "frac_valida": round(validos / total, 4) if total else None,
        "masa_bolsillo_entre_validos": round(en_bolsillo / validos, 4) if validos else None,
        "n_nodos": nbits,
        "distribucion_por_nodo": por_nodo,
    }


if __name__ == "__main__":
    man = json.load(open(os.path.join(QRUN, "voyage2_manifest.json")))
    bateria = man["battery"]
    open(LOG, "w").close()
    anota("inicio", n_circuitos_declarados=len(bateria),
          job_ids=[x["job_id"] for x in bateria])

    filas, faltan = [], []
    for c in bateria:
        anota("intento", job_id=c["job_id"], role=c["role"])   # ANTES del paso
        p = os.path.join(RES, "poc_job_%s.json" % c["job_id"])
        if not os.path.exists(p):
            faltan.append(c["job_id"])
            anota("saltado", job_id=c["job_id"], razon="sin archivo de resultado")
            continue
        counts, shots, nbits = counts_de(c["job_id"])
        m = medir(counts, nbits, set(c["pocket_nodes"]))
        if shots != c["shots"]:
            anota("aviso", job_id=c["job_id"], declarados=c["shots"], recibidos=shots)
        filas.append({
            "job_id": c["job_id"], "role": c["role"], "protein": c["protein"],
            "shots_declarados": c["shots"], "shots_recibidos": shots,
            "calzan_los_shots": shots == c["shots"],
            "pocket_nodes": c["pocket_nodes"],
            "ideal_pocket_mass": c.get("ideal_pocket_mass"),
            "classical_ceiling": c.get("classical_ceiling"),
            "techo_es_la_uniforme": abs(c["classical_ceiling"]
                                        - len(c["pocket_nodes"]) / c["nq"]) < 5e-5,
            "supera_el_techo_MEDIDO": (m["masa_bolsillo_entre_validos"]
                                       > c["classical_ceiling"]),
            "supera_el_techo_PREDICHO": c.get("quantum_beats_ceiling"),
            "la_prediccion_se_cumplio": ((m["masa_bolsillo_entre_validos"]
                                          > c["classical_ceiling"])
                                         == c.get("quantum_beats_ceiling")),
            "desvio_vs_ideal": round(m["masa_bolsillo_entre_validos"]
                                     - c["ideal_pocket_mass"], 4),
            **m,
        })
        anota("medido", job_id=c["job_id"], frac_valida=m["frac_valida"],
              masa=m["masa_bolsillo_entre_validos"])

    por_rol = {f["role"]: f for f in filas}
    fv = [f["frac_valida"] for f in filas]

    # --- las tres comparaciones que pedía el diseño sellado
    comp = {}

    pos, neg = por_rol.get("control-positivo"), por_rol.get("control-negativo")
    if pos and neg:
        comp["nulo_vs_control"] = {
            "que_compara": "control NEGATIVO (barajado) contra el control POSITIVO, misma "
                           "proteina y mismos disparos",
            "masa_control_positivo": pos["masa_bolsillo_entre_validos"],
            "masa_control_negativo": neg["masa_bolsillo_entre_validos"],
            "delta": round(pos["masa_bolsillo_entre_validos"]
                           - neg["masa_bolsillo_entre_validos"], 4),
            "lectura": "si el barajado da una masa parecida, el circuito no esta midiendo "
                       "la estructura de la red sino algo que sobrevive a destruirla",
        }

    rep = por_rol.get("repeticion")
    if pos and rep:
        comp["repeticion_vs_original"] = {
            "que_compara": "el MISMO circuito corrido dos veces en el mismo backend",
            "masa_primera": pos["masa_bolsillo_entre_validos"],
            "masa_repeticion": rep["masa_bolsillo_entre_validos"],
            "delta_masa": round(abs(pos["masa_bolsillo_entre_validos"]
                                    - rep["masa_bolsillo_entre_validos"]), 4),
            "frac_valida_primera": pos["frac_valida"],
            "frac_valida_repeticion": rep["frac_valida"],
            "delta_frac_valida": round(abs(pos["frac_valida"] - rep["frac_valida"]), 4),
            "lectura": "es la barra de error que no teniamos: cuanto se mueve el numero "
                       "sin que cambie nada del experimento",
        }

    replica = por_rol.get("replica-corrida-1")
    if replica:
        comp["replica_vs_RQ-POC-QPU-001"] = {
            "que_compara": "la replica del circuito de julio contra la corrida original",
            "frac_valida_replica": replica["frac_valida"],
            "frac_valida_original": ORIGINAL["frac_valida"],
            "delta": round(replica["frac_valida"] - ORIGINAL["frac_valida"], 4),
            "original": ORIGINAL,
            "lectura": "la reproducibilidad entre dias en el mismo hardware. Una diferencia "
                       "grande dice que el 61,4 % de julio era una foto, no una constante",
        }

    aciertos = sum(1 for f in filas if f["la_prediccion_se_cumplio"])
    desvios = [abs(f["desvio_vs_ideal"]) for f in filas]

    res = {
        "LO_QUE_ESTO_NO_DICE": {
            "el_corredor_se_construye_SABIENDO_donde_esta_el_bolsillo":
                "`poc_corridor.corridor_subgraph` traza el camino mas corto de la fuente al "
                "bolsillo ALOSTERICO CONOCIDO (`d['allo']`) y se queda con esos nodos mas "
                "vecinos. El sub-grafo de 8 a 12 nodos esta construido desde la respuesta. "
                "Por eso esta bateria NO dice nada sobre encontrar bolsillos: mide si la "
                "caminata corre fiel en hardware sobre un grafo chico, con el bolsillo "
                "puesto a proposito en el otro extremo del camino.",
            "el_techo_clasico_es_la_uniforme":
                "`classical_ceiling` es |bolsillo|/nq, es decir el limite de la difusion "
                "clasica a tiempo largo — comprobado igual en los 7 salvo redondeo. "
                "Superarlo NO es un cruce: es ganarle al reparto uniforme, que es "
                "exactamente el rival que la justificacion del metrico declara SIN "
                "informacion. El mejor clasico para esta tarea (GNM, betweenness, "
                "closeness, difusion a tiempo finito) no participa en esta comparacion.",
            "cruce_ventaja_cuantica": "0",
            "n_por_circuito": "1. La unica barra de error del experimento es la repeticion.",
        },
        "_doc": "Bateria del Viaje 2 en ibm_kingston. Convenciones (one-hot valido, orden "
                "de bits, masa condicionada a validos) heredadas de la corrida original, no "
                "inventadas aqui. Los job_id y los roles estaban sellados antes de existir "
                "los resultados.",
        "denominador": {"circuitos_declarados": len(bateria), "medidos": len(filas),
                        "sin_archivo": len(faltan), "cuales_faltan": faltan},
        "shots_totales": sum(f["shots_recibidos"] for f in filas),
        "todos_los_shots_calzan": all(f["calzan_los_shots"] for f in filas),
        "rango_frac_valida": [min(fv), max(fv)] if fv else None,
        "predicciones_pre-declaradas_que_se_cumplieron": "%d de %d" % (aciertos, len(filas)),
        "desvio_vs_ideal": {"maximo_absoluto": round(max(desvios), 4),
                            "mediano": round(sorted(desvios)[len(desvios) // 2], 4)},
        "circuitos": filas,
        "comparaciones": comp,
    }
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    anota("fin", medidos=len(filas), sin_archivo=len(faltan))

    print("BATERIA — %d de %d circuitos medidos, %d sin archivo"
          % (len(filas), len(bateria), len(faltan)))
    print("%-22s %-9s %6s %8s %8s" % ("rol", "proteina", "shots", "valida", "masa"))
    for f in filas:
        print("%-22s %-9s %6d %7.1f%% %7.1f%%"
              % (f["role"], f["protein"][:9], f["shots_recibidos"],
                 100 * f["frac_valida"], 100 * f["masa_bolsillo_entre_validos"]))
    print("\n%-22s %8s %8s %8s %7s" % ("rol", "medida", "ideal", "techo", "predicho?"))
    for f in filas:
        print("%-22s %7.1f%% %7.1f%% %7.1f%% %7s"
              % (f["role"], 100 * f["masa_bolsillo_entre_validos"],
                 100 * f["ideal_pocket_mass"], 100 * f["classical_ceiling"],
                 "SI" if f["la_prediccion_se_cumplio"] else "NO"))
    print("\npredicciones pre-declaradas cumplidas: %d de %d" % (aciertos, len(filas)))
    print("desvio maximo contra la simulacion ideal: %.1f puntos" % (100 * max(desvios)))
    print("\nrango de fraccion valida: %.1f%% a %.1f%%" % (100 * min(fv), 100 * max(fv)))
    print("disparos totales: %d · todos calzan con lo declarado: %s"
          % (res["shots_totales"], res["todos_los_shots_calzan"]))
    for k, v in comp.items():
        print("\n%s" % k)
        for kk, vv in v.items():
            if kk not in ("lectura", "que_compara", "original"):
                print("   %-28s %s" % (kk, vv))
