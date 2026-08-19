#!/usr/bin/env python3
"""Sella el ADDENDUM del prereg HSBC: la replicacion adversarial, ANTES de correrla."""
import hashlib, json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))
import rosettaq_seal as rs

NOMBRE = ("RosettaQ__PREREG__RQ-PREREG-HSBC-002-ATAQUE__20260821T1200Z__"
          "replicacion-adversarial-tres-salidas-declaradas.json")
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-PREREG-HSBC-002-ATAQUE", "type": "PREREG",
    "is_demo": False,
    "scope_note": "Addendum al prereg RQ-PREREG-HSBC-001: la replicacion adversarial del "
                  "baseline, disenada para MATAR el resultado si es falso. Sellado ANTES "
                  "de correr ninguna variante. Autorizado por Nicholas via Norte "
                  "(«volvamos a hacer el experimento... o busquemos una forma "
                  "alternativa, justamente para desafiarlo»).",
    "prereg_base": {"file_id": "RQ-PREREG-HSBC-001",
                    "content_hash": "sha256:b04f214fae845b1c50431d225e6590b0956d8920c2"
                                    "4b7c7fa26ed94c58f3f2db"},
    "por_que_ya_no_defiende_un_descubrimiento": "el fenomeno (la fuga y la particion "
            "temporal) ya esta publicado y taxonomizado (Kapoor & Narayanan 2023, 8 "
            "tipos; trabajo especifico de fraude en MDPI Mathematics y arXiv "
            "2412.07437). Este ataque no defiende un hallazgo nuestro: demuestra que la "
            "MAQUINA mide bien, que es el aporte real. El encuadre anterior del "
            "laboratorio («hallazgo publicable») queda retirado y consta aqui.",
}, "w6": {
    "que": {
        "modelo_unico_del_ataque": "XGBoost con la configuracion v1 del baseline "
                "(declarada en el artefacto @2072bc53), IDENTICA en todas las variantes: "
                "lo que se compara es el protocolo, no el modelo. LightGBM queda FUERA "
                "(roto por configuracion propia, abierto y declarado); la busqueda de "
                "hiperparametros es trabajo aparte y posterior.",
        "las_cuatro_series": {
            "S1_aleatoria_sin_smote": "R=20 particiones aleatorias estratificadas 80/20, "
                                      "semillas 100-119. Control: separa el efecto del "
                                      "split del efecto de SMOTE.",
            "S2_aleatoria_smote_DENTRO": "R=20, SMOTE (k=5, razon 1:1) ajustado SOLO "
                                         "sobre el train de cada split — el protocolo "
                                         "correcto de la literatura.",
            "S3_aleatoria_smote_ANTES": "R=20, SMOTE aplicado al dataset COMPLETO y "
                                        "particion despues — la practica comun DEFECTUOSA "
                                        "que filtra vecinos sinteticos del test al train. "
                                        "Se corre a proposito como diagnostico, y el "
                                        "artefacto la etiqueta como defectuosa.",
            "S4_barrido_temporal": "cortes al 70/75/80/85/90 % por Time, sin SMOTE — la "
                                   "sensibilidad del resultado v1 al punto de corte.",
        },
        "LAS_TRES_SALIDAS_DEL_ATAQUE_A_declaradas_ANTES": {
            "definicion_de_reproducir": "media de AUPRC de la serie dentro de "
                    "0,871 ± 0,030 → [0,841, 0,901]. La banda sale de los dos numeros "
                    "publicados en el statement (RF+SMOTE 0,871; XGB+SMOTE 0,867) y se "
                    "fija AQUI, antes de ver un solo resultado.",
            "salida_1": "S2 (correcto) reproduce → los numeros publicados son "
                        "alcanzables con protocolo limpio; la diferencia temporal-vs-"
                        "aleatorio se sostiene como dureza de protocolo; implementacion "
                        "validada.",
            "salida_2": "SOLO S3 (defectuoso) reproduce y S2 queda bajo 0,841 con "
                        "Welch p<0,01 contra S3 → el numero publicado es consistente con "
                        "fuga de SMOTE embebida. Afirmacion distinta, mas fuerte, y se "
                        "publica como diagnostico con sus dos series al lado.",
            "salida_3_LA_QUE_NOS_DEJA_MAL": "NINGUNA serie aleatoria alcanza 0,841 → "
                        "nuestra implementacion difiere de las publicadas y la brecha "
                        "temporal-vs-publicado NO puede atribuirse a protocolo con "
                        "nuestra evidencia. EL RESULTADO SE CAE y se publica que se "
                        "cayo. Ninguna salida se elige despues de ver los numeros: las "
                        "tres estan escritas aqui.",
        },
        "CRITERIO_DE_DECISION_DEL_ATAQUE_C": {
            "delta": "Δ = media(S1) − media(S4): mismo codigo, mismos datos, mismo "
                     "modelo; solo cambia el protocolo de particion.",
            "el_efecto_de_protocolo_EXISTE_si": "Welch entre S1 y S4 da p < 0,01 Y "
                     "Δ > 2× la mediana del error bootstrap por corrida. Las dos "
                     "condiciones, no una.",
            "el_efecto_NO_EXISTE_si": "el IC del Δ incluye 0, o Δ queda bajo el ruido "
                     "bootstrap. En ese caso la frase «la particion temporal es mas "
                     "dura» se RETIRA de todo texto nuestro.",
            "el_0871_publicado": "contexto de validacion de S2, jamas blanco del test: "
                     "cruza implementaciones y no se compara contra nuestro IC.",
        },
        "costo_declarado": "65 entrenamientos XGBoost en CI gratuito (~1-2 h en 4 "
                           "despachos paralelos). Cero QPU, cero API de pago.",
    },
    "como": {"ejecucion": "4 despachos del workflow experimento-hsbc con RQ_ATAQUE = "
                          "S1|S2|S3|S4; cada serie deposita UN artefacto con las corridas "
                          "individuales adentro (AUPRC, AUC, conteos, bootstrap por "
                          "corrida) y los scores crudos de la peor y la mejor corrida "
                          "para recomputo.",
             "verificacion": "el corredor `replicar.py` (v1, construido en este mismo "
                             "ciclo) corre la bateria post-CI SIEMPRE con denominador; "
                             "un tramo no ejercido entra al resumen como SALTADO, no "
                             "como silencio.",
             "smote": "imbalanced-learn, version declarada en lib_versions del artefacto"},
    "cuando": {"archived_at": "2026-08-21T12:00:00Z"},
    "donde": {"compute": "CI de evidence"},
    "porque": {"question": "¿mide bien la maquina? — reproducir el protocolo ajeno con "
                           "nuestra implementacion, y que las tres salidas posibles "
                           "esten escritas antes de mirar."},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario "
                                       "(bloqueado hasta la categoria de terceros de "
                                       "Main, coordinado); texto publico via Norte + OK "
                                       "de Nicholas."},
}}
rs.seal(doc, harness=("seal_addendum_ataque.py", "1.0.0",
                      "sha256:" + hashlib.sha256(open(__file__, "rb").read()).hexdigest()),
        sealed_at="2026-08-21T12:00:00+00:00", schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(RAIZ, "evidence", "prereg", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
assert rs.verify(json.load(open(dst)))
# CAPA 1, ejercida en el mismo acto: el sellador se publica junto a su sello
import shutil
h8 = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:8]
cp = os.path.join(RAIZ, "evidence", "code", "seal_addendum_ataque@%s.py" % h8)
assert not os.path.exists(cp)
shutil.copy2(__file__, cp)
print("PREREG-ADDENDUM sellado:", doc["meta"]["content_hash"])
print("capa 1: sellador publicado como code/seal_addendum_ataque@%s.py" % h8)
