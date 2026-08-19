#!/usr/bin/env python3
"""Sella el PRE-REGISTRO del track HSBC (deteccion de fraude), ANTES de toda corrida."""
import hashlib, json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))
import rosettaq_seal as rs

STMT = "/Users/nicholasiakl/Downloads/HSBC-Challenge-Statement-vF-1.pdf"
stmt_sha = "sha256:" + hashlib.sha256(open(STMT, "rb").read()).hexdigest()

NOMBRE = ("RosettaQ__PREREG__RQ-PREREG-HSBC-001__20260820T1500Z__"
          "fraude-tarjetas-diseno-y-protocolo.json")
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-PREREG-HSBC-001", "type": "PREREG",
    "is_demo": False,
    "scope_note": "Pre-registro del track HSBC del 2026 Global Quantum + AI Challenge "
                  "(deteccion de fraude en tarjetas). Sellado ANTES de descargar datos, "
                  "entrenar modelos o correr nada. Arranque aprobado por Nicholas via "
                  "Norte el 19-ago (HSBC + Airbus en paralelo). Todas las citas del "
                  "statement se leyeron del PDF oficial, no de relevos.",
    "statement_oficial": {"archivo": "HSBC-Challenge-Statement-vF-1.pdf",
                          "sha256": stmt_sha, "paginas": 18},
}, "w6": {
    "que": {
        "objetivo_del_challenge_textual": "«Develop a quantum or quantum-inspired fraud "
                "detection model and evaluate it against established classical baselines "
                "on the provided datasets.» (§4.1). Las metricas primarias que lista: "
                "AUC-ROC, AUPRC («Recommended for imbalanced datasets»), F1, matriz de "
                "confusion.",
        "DECISION_datasets": {
            "primario": "European Cardholder (ULB) — Open Database License segun la tabla "
                        "§6.1 del statement. Es el que lleva el VEREDICTO publicable de "
                        "punta a punta: licencia abierta (sin zona gris comercial), "
                        "desbalance extremo (fraude 0,172 %) que es donde AUPRC importa, "
                        "y baselines publicados en el propio statement (AUC-ROC 0,9887; "
                        "AUPRC 0,871).",
            "benchmark": "IEEE-CIS — designado por el organizador (tabla §6.1: «Kaggle "
                         "(requires account), Competition license»). Se usa SOLO como "
                         "benchmark dentro del challenge, al amparo de esa designacion: "
                         "sus reglas Kaggle (§7.A non-commercial only; §7.B prohibe "
                         "redistribuir) implican que NINGUN dato de IEEE-CIS entra al "
                         "repo publico — referencia por sha256, dato descargado por cada "
                         "verificador con su propia cuenta.",
            "descartado": "Sparkov (sintetico): el statement recomienda «Focus on one or "
                          "two datasets rather than all three».",
        },
        "DECISION_metrica_que_manda": {
            "veredicto_cuantico_vs_clasico": "AUPRC sobre el test set completo de ULB — "
                    "la recomendada por el organizador para desbalance, y con fraude al "
                    "0,172 % el AUC-ROC es opticamente generoso. AUC-ROC, F1 y matriz se "
                    "reportan al lado, siempre.",
            "ancla_contra_el_estado_del_arte": "AUC-ROC en IEEE-CIS contra el 0,9459 — "
                    "que el statement tabula como «Established Baselines for Reference» "
                    "(1er lugar, ensamble XGBoost+CatBoost+LightGBM). NO es una vara "
                    "declarada por el cliente para aprobar/reprobar: es la referencia "
                    "publicada, y el statement pide «benchmark against these published "
                    "results and clearly report comparison methodology». La metodologia "
                    "de comparacion es exactamente este pre-registro.",
        },
        "PROTOCOLO_de_comparacion": [
            "1. Particion TEMPORAL 80/20 por la columna de tiempo de cada dataset (ULB "
            "'Time', IEEE-CIS 'TransactionDT'): el test es el futuro del train. Nada de "
            "barajar transacciones en el tiempo — el fraude es un proceso temporal y una "
            "particion aleatoria filtra el futuro al pasado.",
            "2. AMBOS brazos se evaluan sobre EXACTAMENTE el mismo test set completo, "
            "identificado por sha256 de la particion. Un brazo cuantico que entrena sobre "
            "submuestra igual se evalua sobre el test completo.",
            "3. Submuestreo de ENTRENAMIENTO del brazo cuantico: permitido y declarado — "
            "el statement lo autoriza textual: «Subsampling must be performed using "
            "stratified sampling to preserve the fraud/non-fraud ratio ... and the total "
            "number of samples used for quantum execution must be explicitly stated». La "
            "estratificacion se MIDE en el artefacto, no se asume.",
            "4. El baseline clasico es NUESTRO, afinado (XGBoost/LightGBM con busqueda "
            "declarada): el rival es lo que el cliente usa hoy, no un espantapajaros. Los "
            "numeros publicados (0,9459 / 0,9887 / 0,871) se citan como referencia y "
            "JAMAS se heredan como medicion propia.",
            "5. CRUCE VALIDO = el brazo cuantico o hibrido supera al nuestro clasico en "
            "la metrica que manda, sobre el mismo test completo, con intervalo bootstrap "
            "del 95 % que no se solape (2.000 remuestreos, semilla 42). Sin eso, es ruido.",
            "6. Toda corrida publica sus conteos crudos (TP/FP/TN/FN por umbral, curvas "
            "completas), no solo el area: el dato crudo viaja, la cifra es derivada.",
        ],
        "expectativa_ANTES_de_correr": "BAJA probabilidad de cruce. El 0,9459 de "
                "IEEE-CIS es el 1er lugar de una competencia con miles de equipos, y los "
                "ejemplos cuanticos que el propio statement cita corren sobre datasets "
                "distintos y menores. Lo esperable: el clasico gana en ambos datasets, el "
                "brazo cuantico queda por debajo, y el valor esta en el veredicto medido "
                "y en caracterizar DONDE (features, encodings, tamanos) se acerca. Si "
                "cruza, se mira con mas desconfianza que entusiasmo.",
        "guardias_que_fallan_cerrado": [
            "(a) FUGA: ninguna fila del test participa en entrenamiento, ajuste o "
            "seleccion de features de ningun brazo — particion por hash con guardia que "
            "aborta si una fila cruza. Es la cadena de ceguera de este dominio.",
            "(b) MANIFIESTO ANTES DE ENTRENAR: los sha256 de los archivos exactos de "
            "datos se sellan como DATA-manifest ANTES de la primera corrida de "
            "entrenamiento; toda corrida declara contra que manifest corrio.",
            "(c) ESTRATIFICACION MEDIDA: la razon fraude/no-fraude de cada submuestra se "
            "mide y va al artefacto; desviacion > declarada aborta.",
            "(d) MISMO TEST: ambos brazos declaran el sha256 del test que puntuaron; si "
            "difieren, el comparador aborta.",
            "(e) harness_sha256 en cada artefacto, como en E.ON.",
        ],
        "hardware": "Fase de simulacion. El statement: hardware via Braket/Classiq es "
                    "opcional y «full end-to-end model training or inference on quantum "
                    "hardware is not expected nor required». NADA de QPU ni gasto de API "
                    "sin OK explicito de Nicholas (CLAUDE.md §8).",
        "ambiguedad_declarada_al_organizador": "el statement dice «Given the dataset "
                "size (~24,000 rows)» y ningun dataset designado tiene ese tamano (ULB "
                "284.807; IEEE-CIS ~590.000; Sparkov ~1,8 M). Puede ser un subconjunto "
                "sugerido o un error del brief. Se pregunta al organizador; NO se "
                "resuelve en silencio.",
    },
    "como": {"brazo_clasico": "XGBoost/LightGBM afinado (busqueda declarada en el "
                              "artefacto), CPU, CI",
             "brazo_cuantico": "kernels cuanticos y/o clasificador variacional en "
                               "PennyLane (simulacion), features reducidas por metodo "
                               "declarado ANTES de mirar el test",
             "compute": "GitHub Actions, patron de E.ON: entorno desde cero, deposito "
                        "por hash, harness archivado, harness_sha256 en el artefacto"},
    "cuando": {"archived_at": "2026-08-20T15:00:00Z",
               "fase_I_cierra": "2026-09-15"},
    "donde": {"compute": "CI de evidence"},
    "porque": {"question": "¿que aporta un modelo cuantico o cuantico-inspirado a la "
                           "deteccion de fraude, medido contra un clasico afinado, con "
                           "protocolo fijado antes de mirar?",
               "para_que": "primer caso (junto a Airbus) de la plantilla de desafio que "
                           "convierte la maquina en producto ofrecible."},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario; "
                                       "veredicto y texto publico pasan por Norte y el "
                                       "OK de Nicholas."},
}}
_mi = "sha256:" + hashlib.sha256(open(__file__, "rb").read()).hexdigest()
rs.seal(doc, harness=("seal_prereg_hsbc.py", "1.0.0", _mi),
        sealed_at="2026-08-20T15:00:00+00:00", schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(RAIZ, "evidence", "prereg", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
assert rs.verify(json.load(open(dst)))
print("PREREG sellado:", doc["meta"]["content_hash"])
print("statement anclado:", stmt_sha[:24])
