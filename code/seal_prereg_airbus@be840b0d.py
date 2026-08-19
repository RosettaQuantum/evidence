#!/usr/bin/env python3
"""Sella el PRE-REGISTRO del track Airbus, redactado por coordinacion, ANTES del harness."""
import hashlib, json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))
import rosettaq_seal as rs

STMT = "/Users/nicholasiakl/Downloads/Airbus-Challenge-Statement-vF.pdf"
stmt_sha = hashlib.sha256(open(STMT, "rb").read()).hexdigest()
if not stmt_sha.startswith("4a2e084dd25d4934"):
    raise SystemExit("el statement no es el que la coordinacion declaro")
BORRADOR = os.path.join(AQUI, "PREREG-AIRBUS-borrador.md")
borr_sha = hashlib.sha256(open(BORRADOR, "rb").read()).hexdigest()

NOMBRE = ("RosettaQ__PREREG__RQ-PREREG-AIRBUS-001__20260820T1900Z__"
          "cruce-tiempo-error-vs-reynolds-arbitro-analitico.json")
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-PREREG-AIRBUS-001", "type": "PREREG",
    "is_demo": False,
    "scope_note": "Pre-registro del track Airbus (solvers cuanticos de PDEs, aerodinamica) "
                  "del 2026 Global Quantum + AI Challenge. Redactado por la sesion de "
                  "coordinacion, sellado por el laboratorio ANTES de que exista una linea "
                  "del instrumento — el orden en el historial de git es el activo. "
                  "Arranque cubierto por la aprobacion de Nicholas (HSBC + Airbus en "
                  "paralelo, 19-ago).",
    "statement_oficial": {"archivo": "Airbus-Challenge-Statement-vF.pdf",
                          "sha256": "sha256:" + stmt_sha},
    "texto_fuente": {"archivo": "PREREG-AIRBUS-borrador.md",
                     "sha256": "sha256:" + borr_sha,
                     "publicado_como": "data/2026/08/PREREG-AIRBUS-borrador@%s.md"
                                       % borr_sha[:8],
                     "regla": "la procedencia se publica en el mismo acto que el sello "
                              "(leccion de eon_estocastico)."},
}, "w6": {
    "que": {
        "pregunta_pre_registrada": "sobre el vortice de Taylor-Green convectivo 2D "
                "(Navier-Stokes incompresible, el caso del statement): ¿donde, sobre el "
                "eje del numero de Reynolds, se cruzan — si se cruzan — las curvas de "
                "tiempo-y-error de un solver cuantico de PDEs y de los solvers clasicos "
                "de referencia, midiendo el error contra la solucion analitica exacta?",
        "los_DOS_desenlaces_son_entregables": {
            "si_cruza": "el cruce es incuestionable porque el arbitro es una formula "
                        "cerrada, no una estimacion.",
            "si_no_cruza": "la curva completa tiempo-y-error vs Reynolds ES el entregable "
                           "que el statement pide («a plot characterizing the obtained "
                           "(or estimated) time-to-solution and the numerical error "
                           "across a range of Reynolds»). No hay plan B: hay dos "
                           "resultados posibles y ambos se publican sellados.",
        },
        "riesgo_conocido_declarado_ANTES": "el propio brief (§3.2) admite que la fisica "
                "es no-lineal y no-unitaria y el hardware cuantico es lineal y unitario. "
                "La linealizacion de Carleman trunca, y el orden de truncamiento acota "
                "que Reynolds son honestamente alcanzables. EXPECTATIVA PRE-DECLARADA: "
                "el piloto cuantico sera competitivo, si lo es, solo en Reynolds bajos y "
                "mallas chicas; el valor del track no depende de que gane — depende de "
                "que la curva sea exacta y reproducible.",
    },
    "como": {
        "arbitro": "la solucion analitica del statement (§5.3) evaluada en la malla en "
                   "el tiempo final T; error = L2 relativo del campo de velocidad contra "
                   "la formula. Sin arbitro aprendido, sin arbitro numerico: formula.",
        "brazos_clasicos_DOS": "para no comparar contra un espantapajaros: (a) espectral "
                "(calidad de referencia en malla periodica); (b) diferencias finitas de "
                "2.o orden (el metodo de ingenieria). Presupuesto de pared identico por "
                "punto, declarado en el artefacto.",
        "brazo_cuantico_v1": "linealizacion de Carleman (orden declarado en cada "
                "artefacto) + evolucion del sistema lineal por metodo variacional en "
                "statevector. SIN QPU en esta fase: cero gasto de cuota; hardware solo "
                "con OK explicito de Nicholas.",
        "eje_y_regla_de_corte": "Reynolds creciente con la malla acoplada segun el "
                "statement («grid resolution must increase with Reynolds number»); la "
                "regla de acople se fija en el instrumento y viaja en cada artefacto. El "
                "rango NO se elige a mano: arranca donde los tres brazos resuelven con "
                "error < 1 % y sube hasta que diferencias finitas degrada (error > 10 % "
                "en el presupuesto declarado) o el brazo cuantico agota memoria — el "
                "punto de corte SE MIDE Y SE DECLARA, no se decide (la leccion del K=20).",
        "guardias_del_instrumento": [
            "1. en t=0 el campo inicial reproduce la analitica al epsilon de maquina, o "
            "aborta.",
            "2. cada artefacto declara lo que OCURRIO, no lo que se pidio: malla real, "
            "pasos reales, orden de Carleman real, harness_sha256.",
            "3. un nan o un campo vacio en cualquier brazo aborta la corrida entera — la "
            "ausencia no viaja como valor.",
            "4. la procedencia se publica en el mismo acto que el sello.",
            "todas se prueban por mutacion antes de la primera corrida real.",
        ],
    },
    "cuando": {"archived_at": "2026-08-20T19:00:00Z", "fase_I_cierra": "2026-09-15"},
    "donde": {"compute": "CI de evidence (por construir; ni una linea existe al sellar)"},
    "porque": {"question": "ver `pregunta_pre_registrada`",
               "que_NO_afirma": "ventaja cuantica salvo cruce medido con este protocolo; "
                       "nada se extrapola mas alla del ultimo Reynolds medido; no se "
                       "compara contra solvers comerciales de CFD que no corrimos."},
    "quien": {"redaccion": "sesion de coordinacion (Rosetta Q Main)",
              "sellado": "sesion laboratorio", "anclaje": "notario (Main)",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "quien redacta no sella; quien sella no ancla."},
}}
rs.seal(doc, harness=("seal_prereg_airbus.py", "1.0.0",
                      "sha256:" + hashlib.sha256(open(__file__, "rb").read()).hexdigest()),
        sealed_at="2026-08-20T19:00:00+00:00", schema=rs.SCHEMA_V3)
assert rs.verify(doc)
import shutil
dst = os.path.join(RAIZ, "evidence", "prereg", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
assert rs.verify(json.load(open(dst)))
comp = os.path.join(RAIZ, "evidence", "data", "2026", "08",
                    "PREREG-AIRBUS-borrador@%s.md" % borr_sha[:8])
assert not os.path.exists(comp)
shutil.copy2(BORRADOR, comp)
assert hashlib.sha256(open(comp, "rb").read()).hexdigest() == borr_sha
print("PREREG sellado:", doc["meta"]["content_hash"])
print("fuente publicada:", os.path.basename(comp))
