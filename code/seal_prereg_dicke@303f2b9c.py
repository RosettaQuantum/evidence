#!/usr/bin/env python3
"""Sella el PRE-REGISTRO de la variante Dicke+XY, ANTES de correr nada."""
import json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))
import rosettaq_seal as rs

NOMBRE = ("RosettaQ__PREREG__RQ-PREREG-EON-DICKE-001__20260819T1400Z__"
          "disparos-factibles-por-construccion.json")
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-PREREG-EON-DICKE-001", "type": "PREREG",
    "is_demo": False,
    "scope_note": "Pre-registro de la demo prometida en el §8 del informe de E.ON: un "
                  "circuito donde CADA disparo es un plan factible por construccion. "
                  "Escrito y sellado ANTES de implementar o correr. Encargo aprobado por "
                  "Nicholas (decision C del 18-ago via Norte).",
}, "w6": {
    "que": {
        "variante": {
            "estado_inicial": "Dicke |D^K_5>: superposicion uniforme de las C(K,5) cadenas "
                              "de peso 5, preparada por StatePrep del vector exacto "
                              "(esta fase es simulacion; la preparacion por circuito es "
                              "problema de la fase de hardware, si la hay).",
            "mezclador": "XY en ANILLO: pares (i, i+1 mod K), exp(-i*beta*(XX+YY)) via "
                         "IsingXX+IsingYY con el mismo angulo. Preserva el peso de "
                         "Hamming; se elige anillo (K pares) y no grafo completo "
                         "(K(K-1)/2) por costo, y la eleccion queda declarada aqui, antes.",
            "serie": "K=8/12/16, 400 pasos, reloj 2400 s, capas 2/3/4, seed 42 — los "
                     "mismos parametros del lote D para comparacion limpia. K=20 NO: el "
                     "reloj ya demostro que ahi se mide el presupuesto.",
        },
        "DECISION_penalidad_de_cardinalidad": {
            "decision": "NO SE QUITA. El QUBO, el arbitro exacto y CP-SAT quedan "
                        "identicos al lote D.",
            "por_que_es_seguro": "sobre cualquier cadena de peso k la penalidad "
                    "PEN*(sum x - k)^2 vale exactamente 0. El subespacio de peso k es el "
                    "unico que la dinamica Dicke+XY habita, y alli la penalidad es una "
                    "constante nula: no altera el ranking ni la evolucion (fase global). "
                    "Quitarla crearia una segunda funcion objetivo que habria que "
                    "declarar y auditar; mantenerla preserva la comparabilidad bit a bit.",
            "guardia_asociada": "toda muestra debe ser de peso 5 (guardia b); sobre esas "
                    "muestras ambas funciones coinciden por identidad, no por tolerancia.",
        },
        "expectativas_ANTES_de_correr": {
            "fraccion_valida": "100 % por construccion, verificada sobre el vector de "
                               "estado y sobre cada muestra — no asumida del circuito.",
            "subespacio": {"K=8": 56, "K=12": 792, "K=16": 4368},
            "K=8": "gap 0.0000 % (empate). ADVERTENCIA pre-escrita: con 35,7 disparos por "
                   "estado factible, el empate NO demuestra el metodo — un muestreador "
                   "uniforme del subespacio daria lo mismo. Misma clase que el empate del "
                   "K=8 del lote B.",
            "K=12": "gap 0.0000 % esperado: uniforme puro sobre 792 estados tocaria el "
                    "optimo con prob ~92 % en 2000 disparos; el sesgo del QAOA sube eso.",
            "K=16": "gap MENOR que el 1.3062 % del X-mixer, probablemente < 0.5 %; sin "
                    "garantia de 0 (uniforme puro: ~37 %). ESTE es el punto que informa: "
                    "los otros dos casi no pueden fallar.",
            "costo_de_pared": "mismo orden que el lote D (domina 2^K del simulador); el "
                              "mezclador XY cuesta mas por capa — hasta ~3x por paso.",
            "falsable": "si el gap Dicke en K=16 sale PEOR que el del X-mixer, se publica "
                        "igual y la promesa del §8 se corrige en vez de defenderse.",
        },
        "guardias_que_fallan_cerrado": [
            "(a) el estado FINAL analitico (tras las p capas, no solo la preparacion) "
            "tiene soporte SOLO en cadenas de peso 5: masa fuera < 1e-9 o aborta. Probar "
            "el estado final prueba preparacion Y mezclador a la vez.",
            "(b) cada muestra de peso 5; UNA sola que no lo sea aborta — en simulacion "
            "exacta debe ser el 100 %.",
            "(c) el guardia Ising<->QUBO existente sigue activo, y harness_sha256 sigue "
            "en el artefacto.",
        ],
        "no_se_rompe_el_camino_viejo": "la variante entra por RQ_MIXER (default 'x' = "
                "camino actual, byte-identico en comportamiento); artefactos con '_dicke' "
                "en el nombre; y una corrida X de regresion (K=8) debe reproducir los "
                "verdictos del lote D al decimal.",
        "qpu": "NADA de QPU en esta fase. Simulacion en CI solamente (CLAUDE.md §8).",
    },
    "como": {"harness_base": "eon_harness.py @ commit e6778c5 (sha 50cd5d6f...)",
             "compute": "GitHub Actions, experimento-eon.yml con input nuevo 'mezclador'"},
    "cuando": {"archived_at": "2026-08-19T14:00:00Z"},
    "donde": {"compute": "CI de evidence"},
    "porque": {"question": "¿cuanto del gap del X-mixer era desperdicio de disparos "
                           "infactibles, y cuanto es del metodo?",
               "promesa_que_cumple": "informe E.ON §8: «a circuit where every shot is a "
                                     "feasible plan by construction»."},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}
import hashlib
_mi_sha = "sha256:" + hashlib.sha256(open(__file__, "rb").read()).hexdigest()
rs.seal(doc, harness=("seal_prereg_dicke.py", "1.0.0", _mi_sha),
        sealed_at="2026-08-19T14:00:00+00:00", schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(RAIZ, "evidence", "prereg", "2026", "08", NOMBRE)
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
assert rs.verify(json.load(open(dst)))
print("PREREG sellado y depositado:", doc["meta"]["content_hash"])
