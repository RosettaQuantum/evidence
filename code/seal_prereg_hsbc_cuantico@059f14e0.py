#!/usr/bin/env python3
"""Sella el PRE-REGISTRO del BRAZO CUANTICO del track HSBC, ANTES de que exista su codigo.

Complementa a RQ-PREREG-HSBC-001 (diseno y protocolo, sellado el 20-ago). Aquel fijo el
arbitro; este fija el brazo cuantico contra ese arbitro ya sellado, y por eso no puede
tocar ni una linea de la particion, el test ni la metrica que manda.

Gasto autorizado: US$0. Nicholas rechazo el presupuesto de una corrida en hardware
(«no autorizo ese gasto es muy elevado»). El costo del hardware entra al archivo como
MEDICION derivada del diseno y de la tarifa publicada, no como plan de ejecucion, y este
sello es el que fija esa distincion antes de correr nada.
"""
import hashlib, json, os, shutil, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes

BORRADOR = os.path.join(RAIZ, "PREREG-HSBC-CUANTICO-borrador.md")
borr_sha = hashlib.sha256(open(BORRADOR, "rb").read()).hexdigest()

ARBITRO = os.path.join(RAIZ, "evidence", "prereg", "2026", "08",
                       "RosettaQ__PREREG__RQ-PREREG-HSBC-001__20260820T1500Z__"
                       "fraude-tarjetas-diseno-y-protocolo.json")
arbitro = json.load(open(ARBITRO))
assert rs.verify(arbitro), "el prereg arbitro no verifica: no se sella contra el"

STAMP, ISO = ahora_stamp(), ahora_iso()
assert coherentes(STAMP, ISO)

NOMBRE = ("RosettaQ__PREREG__RQ-PREREG-HSBC-003-CUANTICO__%s__"
          "brazo-cuantico-kernel-de-fidelidad-simulacion-pura.json" % STAMP)
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-PREREG-HSBC-003-CUANTICO", "type": "PREREG",
    "is_demo": False,
    "scope_note": "Pre-registro del BRAZO CUANTICO del track HSBC, sellado ANTES de que "
                  "exista una linea de su instrumento — el orden en el historial de git "
                  "es el activo, no esta afirmacion. El arbitro clasico ya estaba sellado "
                  "y anclado, asi que este documento no puede moverlo: particion, test y "
                  "metrica que manda se heredan de RQ-PREREG-HSBC-001 y se citan por "
                  "content_hash. Revisado por la sesion de coordinacion antes de sellar.",
    "prereg_arbitro": {"file_id": "RQ-PREREG-HSBC-001",
                       "content_hash": arbitro["meta"]["content_hash"],
                       "regla": "lo heredado no se re-decide aqui (§10 del borrador)."},
    "texto_fuente": {"archivo": "PREREG-HSBC-CUANTICO-borrador.md",
                     "sha256": "sha256:" + borr_sha,
                     "publicado_como": "data/2026/08/PREREG-HSBC-CUANTICO-borrador@%s.md"
                                       % borr_sha[:8],
                     "regla": "la procedencia se publica en el mismo acto que el sello."},
}, "w6": {
    "que": {
        "brazo": "kernel cuantico de fidelidad |<phi(a)|phi(b)>|^2, evaluado en simulacion "
                 "exacta por productos de statevector; variacional como segundo, declarado "
                 "y no ejecutado en esta fase.",
        "GASTO_AUTORIZADO_USD": 0,
        "hardware": {
            "ejecutado": False,
            "declaracion": "NINGUN circuito se ejecuta en un dispositivo real en esta "
                           "fase. Nicholas rechazo el gasto por elevado. El §4.2 del "
                           "statement dice textual que entrenar o inferir en hardware "
                           "«is not expected nor required», asi que el alcance no se "
                           "debilita: el objetivo §4.1 se cumple en simulacion exacta.",
            "lo_que_este_track_NO_afirma_sobre_hardware": "nada sobre ruido, calibracion, "
                           "fidelidad de dispositivo ni desempeno en hardware — no se "
                           "corrio. Lo unico afirmado es cuanto COSTARIA.",
            "costo_medido_no_gastado": {
                "metodo": "derivado del diseno y de la tarifa publicada por "
                          "costo_braket_hsbc.py; tarifa leida de aws.amazon.com/braket/"
                          "pricing el 2026-08-21 (per-task USD 0,30 identico en los seis "
                          "QPU; per-shot 0,000425 Rigetti Cepheus a 0,08 IonQ Forte).",
                "test_completo_x2000_soportes_USD": 39018970,
                "demo_500x100_USD": 17125, "demo_200x50_USD": 3425,
                "demo_200x50_ionq_forte_USD": 83000,
                "HALLAZGO": "el 88 % del costo es la tarifa fija POR TAREA, porque en un "
                            "kernel cada par (test, soporte) es un circuito distinto y no "
                            "se amortiza repitiendo disparos. Consecuencia medida: ni "
                            "reducir disparos ni cambiar de proveedor mueve el costo — "
                            "solo reducir pares, y reducir pares rompe la comparabilidad "
                            "con el test sellado. Esta es la respuesta al «under what "
                            "conditions» del §4.2.",
            },
        },
        "los_0_8_minutos_NO_son_velocidad_cuantica": "el atajo del statevector existe "
                 "PORQUE se simula; en una QPU ese objeto no existe y vuelven las n^2 "
                 "evaluaciones. El modelo es el mismo en las dos vias: lo que cambia es "
                 "el costo de obtenerlo, no lo que se calcula.",
        "criterio_de_cruce": "el heredado del arbitro: AUPRC sobre el test completo, "
                 "bootstrap 95 % sin solape, 2.000 remuestreos, semilla 42.",
        "los_dos_desenlaces_son_entregables": "si no cruza, el entregable es el veredicto "
                 "medido mas la caracterizacion de donde se acerca; el resultado negativo "
                 "se publica igual.",
    },
    "como": {"simulacion": "PennyLane/statevector, CPU, CI de evidence",
             "guardias": "falla-cerrado y probadas por mutacion (§9 del borrador)"},
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "CI de evidence — ningun backend de pago"},
    "porque": {"question": "¿aporta un kernel cuantico de fidelidad a la deteccion de "
                           "fraude, medido contra un clasico afinado sobre el mismo test, "
                           "con el protocolo fijado antes de mirar?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario; "
                                       "el texto publico pasa por el OK de Nicholas."},
}}
_yo = os.path.basename(__file__)
_mi = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
_pub_yo = os.path.join(RAIZ, "evidence", "code", "%s@%s.py" % (_yo[:-3], _mi[:8]))
exigir_procedencia(doc, extra=(BORRADOR, __file__))
rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)

dst = os.path.join(RAIZ, "evidence", "prereg", "2026", "08", NOMBRE)
assert not os.path.exists(dst), "publicado es publicado: no se reescribe un sello"
comp = os.path.join(RAIZ, "evidence", "data", "2026", "08",
                    "PREREG-HSBC-CUANTICO-borrador@%s.md" % borr_sha[:8])
assert not os.path.exists(comp)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
shutil.copy2(BORRADOR, comp); shutil.copy2(__file__, _pub_yo)
assert rs.verify(json.load(open(dst)))
assert hashlib.sha256(open(comp, "rb").read()).hexdigest() == borr_sha
print("PREREG sellado :", doc["meta"]["content_hash"])
print("arbitro citado :", arbitro["meta"]["content_hash"][:24])
print("fuente publicada:", os.path.basename(comp))
print("sellador public.:", os.path.basename(_pub_yo))
