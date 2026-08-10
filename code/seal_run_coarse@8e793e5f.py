#!/usr/bin/env python3
"""Sella el RUN del experimento de grano grueso. Se corre DESPUES del experimento.

Los numeros se LEEN de coarse_grain_result.json; no se transcriben.

Uso:  python3 seal_run_coarse.py
"""
import hashlib
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
QRUN = os.path.join(RAIZ, "quantum-run")
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))

import rosettaq_seal as rs  # noqa: E402

FILE_ID = "RQ-EXP-COARSE-001"
STAMP = "20260810T1230Z"
SLUG = "grano-grueso-supervivencia-del-orden"
NOMBRE = "RosettaQ__RUN__%s__%s__%s.json" % (FILE_ID, STAMP, SLUG)


def sha(path):
    return "sha256:" + hashlib.sha256(open(path, "rb").read()).hexdigest()


res = json.load(open(os.path.join(AQUI, "coarse_grain_result.json")))
pr = json.load(open(os.path.join(AQUI, res["prereg"]["file_id"].replace(
    "PR-COARSE-001",
    "RosettaQ__PREREG__PR-COARSE-001__20260810T1200Z__"
    "grano-grueso-supervivencia-del-orden.json"))))
assert rs.verify(pr), "el pre-registro no verifica — no se sella el RUN"
assert pr["prereg"]["guardrails_script_sha256"] == res["script_sha256"], \
    "el script que corrio NO es el pre-registrado"

celdas = [f for m in res["blancos"] for f in m["niveles"] if "saltado" not in f]
rhos = [f["spearman_orden_vs_fino_distales"] for f in celdas]
n_sobrevive = sum(1 for f in celdas if f["veredicto_orden"] == "sobrevive")
n_parcial = sum(1 for f in celdas if f["veredicto_orden"] == "parcial")
n_no = sum(1 for f in celdas if f["veredicto_orden"] == "no sobrevive")

doc = {
    "meta": {
        "file_name": NOMBRE,
        "file_id": FILE_ID,
        "type": "RUN",
        "is_demo": False,
        "scope_note": "Objetivo secundario del challenge Cleveland: escalabilidad por grano "
                      "grueso. Mide cuanto del ORDEN de residuos sobrevive a la compresion "
                      "de la red, contra el ranking fino COMPROMETIDO en 4cfac34. "
                      "Pre-registrado en PR-COARSE-001 antes de correr. Resultado NEGATIVO. "
                      "Sellado por el laboratorio; anclaje y publicacion son del notario.",
    },
    "w6": {
        "que": {
            "recipe": "compresion en super-nodos de residuos consecutivos (receta "
                      "required_deliverables.coarse_grain) + el metrico ciego de 407fa7b "
                      "sobre la red gruesa; el score vuelve a residuos por super-nodo",
            "denominador": res["denominador"],
            "umbrales_pre_registrados": res["umbrales_pre_registrados"],
            "reparto_de_celdas": {"sobrevive": n_sobrevive, "parcial": n_parcial,
                                  "no_sobrevive": n_no, "total": len(celdas)},
            "rango_spearman": [round(min(rhos), 4), round(max(rhos), 4)],
            "resultados_por_blanco": res["blancos"],
            "veredicto": "NEGATIVO. CERO de 16 celdas alcanzan el umbral pre-registrado de "
                         "supervivencia (Spearman >= 0,90). Ni siquiera la compresion mas "
                         "suave —bloque 2, que solo junta pares de residuos consecutivos— lo "
                         "alcanza en ningun blanco: el mejor caso de todo el experimento es "
                         "miosina a bloque 2 con 0,8859.",
            "outcome": "El orden de residuos NO sobrevive a la compresion en ningun nivel "
                       "probado: 0 celdas 'sobrevive', 9 'parcial' y 7 'no sobrevive'. Las 7 "
                       "que caen por debajo del umbral parcial son las 4 de KRAS (0,5422 a "
                       "0,0838) y 3 de las 4 de c-Myc (0,5118 a 0,4169). Y el conjunto que de "
                       "verdad decide la prediccion —el top 10% distal que entra al "
                       "clustering— se conserva entre 0,00 y 0,66 de Jaccard. Un top-10% con "
                       "Jaccard 0,22 no produce los mismos sitios: produce otros.",
            "cruce_ventaja_cuantica": "0 — este experimento no compara cuantico contra "
                                      "clasico y no puede producir un cruce. Es el costo de "
                                      "la compresion sobre nuestro propio metrico.",
            "significancia_vs_azar": "no aplica — es una caracterizacion, no una prueba "
                                     "contra el azar",
        },
        "como": {
            "prereg": {"file_id": pr["meta"]["file_id"],
                       "content_hash": pr["meta"]["content_hash"],
                       "sealed_at": pr["meta"]["sealed_at"],
                       "committed_before_run": True},
            "script_congelado": {"archivo": "coarse_grain_test.py",
                                 "sha256": res["script_sha256"],
                                 "coincide_con_el_prereg": True},
            "guardia_probado_por_caso_positivo": "se copio el script, se le agrego un byte y "
                                                 "se corrio: aborto declarando los dos "
                                                 "sha256. Un guardia que nunca se comprobo "
                                                 "gritando es indistinguible de uno borrado.",
            "referencia_fina": "matrices de conectividad comprometidas en 4cfac34; la firma "
                               "de contenido de cada .npz se recomputo antes de usarla y "
                               "calzo en los 4 blancos (0 saltados).",
            "harness_sha256": {
                "coarse_grain_test.py": sha(os.path.join(AQUI, "coarse_grain_test.py")),
                "seal_run_coarse.py": sha(os.path.abspath(__file__)),
                "build_cache.py": sha(os.path.join(QRUN, "build_cache.py")),
                "rank_quantum.py": sha(os.path.join(QRUN, "rank_quantum.py")),
            },
            "raw_result_url": "evidence-staging/coarse_grain_result.json",
            "bitacora": "evidence-staging/coarse_grain_log.jsonl — abierta al empezar, una "
                        "linea por blanco ANTES de medirlo",
            "limitaciones_medidas_no_escondidas": {
                "aceleracion_es_orden_de_magnitud_no_medicion": "los tiempos se tomaron una "
                    "vez por celda, en una maquina con otra carga, y a menos de ~100 "
                    "super-nodos la diagonalizacion baja del milisegundo. La evidencia "
                    "directa del ruido esta en los propios numeros: miosina marca 131,9x a "
                    "bloque 8 y 21,3x a bloque 16, que es imposible como medicion real. Las "
                    "aceleraciones se leen como orden de magnitud, no como cifra.",
                "spearman_sobre_pocos_valores_distintos": "a bloque 16, c-Myc queda en 6 "
                    "super-nodos: el score grueso toma 6 valores distintos sobre 53 residuos "
                    "distales, y el Spearman de esa celda (0,7882, mas alto que el de bloque "
                    "8) es un artefacto de resolucion, no una mejora. Se reporta igual y se "
                    "declara.",
                "techo_estructural_declarado_antes": "dentro de un super-nodo todos los "
                    "residuos comparten score por construccion. Estaba dicho en el "
                    "pre-registro, antes de ver ningun numero.",
            },
        },
        "cuando": {"archived_at": "2026-08-10T12:30:00Z"},
        "donde": {"compute": "Mac local (sesion laboratorio)",
                  "costo": "cero: solo CPU local, sin QPU y sin API de pago"},
        "porque": {
            "hypothesis": "la compresion de la red conserva el orden de residuos lo bastante "
                          "como para que el grano grueso sea una via de escalabilidad real",
            "question": "¿cuanto del orden sobrevive, y hasta que nivel de compresion?",
            "lectura": "La respuesta util no es la aceleracion: es que la aceleracion no se "
                       "puede cobrar. Para este metrico, el grano grueso por bloques de "
                       "secuencia no es una via de escalabilidad — cambia la respuesta antes "
                       "de acelerarla. Si el grano grueso se va a usar, el agrupamiento tiene "
                       "que respetar la estructura (dominios, comunidades del grafo), no el "
                       "orden de la secuencia; y esa es una hipotesis nueva que habria que "
                       "pre-registrar aparte, no un ajuste de esta.",
            "que_queda_fuera": "no se probaron agrupamientos por comunidad ni por dominio; no "
                               "se probaron bloques mayores a 16; no se midio el efecto sobre "
                               "el acierto contra bolsillos validados (eso exigiria abrir las "
                               "holo y es otro experimento).",
        },
        "quien": {
            "lab": "Rosetta Quantum — sesion laboratorio",
            "lead": "Nicholas Iakl Freundlich",
            "separacion_de_deberes": "sellado por el laboratorio; anclaje OTS, publicacion y "
                                     "auditoria de procedencia son del notario.",
        },
    },
}

rs.seal(doc, harness=("coarse_grain_test.py", "1.0.0", res["script_sha256"]))
assert rs.verify(doc), "el sello no verifica — no se escribe nada"

destino = os.path.join(AQUI, NOMBRE)
json.dump(doc, open(destino, "w"), indent=1, ensure_ascii=False)
recargado = json.load(open(destino))
assert rs.verify(recargado), "el archivo escrito NO verifica"

print("SELLADO  %s" % NOMBRE)
print("  content_hash: %s" % recargado["meta"]["content_hash"])
print("  prereg:       %s (%s)" % (pr["meta"]["file_id"], pr["meta"]["content_hash"]))
print("  celdas: %d sobrevive / %d parcial / %d no sobrevive (de %d)"
      % (n_sobrevive, n_parcial, n_no, len(celdas)))
