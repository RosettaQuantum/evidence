#!/usr/bin/env python3
"""Sella la ERRATA de RQ-PREREG-HSBC-003-CUANTICO. El original no se toca.

QUE CORRIGE
-----------
El sello afirma «ni reducir disparos ni cambiar de proveedor mueve el costo». Su propia
tabla, dos lineas mas abajo, muestra la MISMA demostracion de 200x50 a USD 3.425 en
Rigetti Cepheus y USD 83.000 en IonQ Forte: factor 24,2. La afirmacion es cierta en el
backend mas barato y se declaro como general.

TRES DEFECTOS, NO UNO
---------------------
  A) la afirmacion generalizada, desmentida por la tabla del propio artefacto;
  B) el mismo defecto en el INSTRUMENTO — costo_braket_hsbc.py imprimia la frase general
     seguida de un solo ejemplo, el de Rigetti. Arreglado ahi, con un chequeo que falla
     cerrado: si la cuota de las tareas cruza el 50 %, se niega a insinuar una frase
     general. Ejecutar ese arreglo destapo un quinto backend (AQT IBEX-Q1, 11,3 %);
  C) «los seis QPU»: nuestro instrumento tabula CINCO. Se declara pendiente de verificar
     en la fuente en vez de repetirse.

LO QUE NO SE RETRACTA: la decision operativa. La demostracion acotada sobre Rigetti a
USD 3.425 sigue elegida y sigue siendo la respuesta al «under what conditions» del §4.2.
Se corrige el alcance de la explicacion, no la decision.

GUARDIA: antes de sellar se recomputan las cifras desde el instrumento. Si alguna dejo de
reproducir, aborta — no se sella una correccion cuyas cifras no se sostienen al sellarse.

Simulacion y lectura de artefactos. Costo US$0.
"""
import hashlib, json, os, shutil, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness")); sys.path.insert(0, AQUI)
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes
import costo_braket_hsbc as C

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
ERRATA = os.path.join(RAIZ, "ERRATA-PREREG-HSBC-003-borrador.md")
SCRIPT = os.path.join(AQUI, "costo_braket_hsbc.py")
import glob
ORIG = glob.glob(os.path.join(EV, "prereg", "2026", "08", "*HSBC-003-CUANTICO*.json"))[0]
orig = json.load(open(ORIG)); assert rs.verify(orig)

# ------------------------------------------------------------------ GUARDIA
tot = {b: C.costo(200, 50, 100, b)["usd_total"] for b in C.TARIFA}
cuota = {b: 100.0 * C.costo(200, 50, 100, b)["usd_tareas"] / tot[b] for b in C.TARIFA}
esperado = {"Rigetti Cepheus": 3425, "IQM Garnet": 4450, "IQM Emerald": 4600,
            "AQT IBEX-Q1": 26500, "IonQ Forte": 83000}
for b, v in esperado.items():
    if round(tot[b]) != v:
        raise SystemExit("ABORTA: %s recomputa USD %.0f y la errata dice %d" % (b, tot[b], v))
factor = max(tot.values()) / min(tot.values())
if abs(factor - 24.2) > 0.05:
    raise SystemExit("ABORTA: el factor entre extremos recomputa %.2f, no 24,2" % factor)
if not (min(cuota.values()) < 50.0 <= max(cuota.values())):
    raise SystemExit("ABORTA: la cuota de tareas ya no cruza el 50 % — el diagnostico de "
                     "esta errata (hay backends a cada lado) dejo de sostenerse")
if "ni reducir disparos ni cambiar de proveedor mueve el costo" not in json.dumps(orig, ensure_ascii=False):
    raise SystemExit("ABORTA: la frase que esta errata retracta no esta en el original")

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
h_err = sha(ERRATA)
NOMBRE = ("RosettaQ__ERRATA__RQ-ERRATA-PREREG-HSBC-003__%s__"
          "el-costo-si-se-mueve-al-cambiar-de-proveedor.json" % STAMP)
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-ERRATA-PREREG-HSBC-003", "type": "ERRATA",
    "is_demo": False,
    "scope_note": "Errata de RQ-PREREG-HSBC-003-CUANTICO. NO modifica el original: su "
                  "archivo, su hash y su ancla quedan intactos. Corrige una afirmacion "
                  "que la tabla del propio artefacto desmiente. Emision autorizada por "
                  "Nicholas.",
    "corrige": {"file_id": orig["meta"]["file_id"],
                "content_hash": orig["meta"]["content_hash"],
                "sealed_at": orig["meta"]["sealed_at"],
                "regla": "el sello original no se reescribe ni se re-sella."},
    "texto_fuente": {"archivo": "ERRATA-PREREG-HSBC-003.md", "sha256": "sha256:" + h_err,
                     "publicado_como": "data/2026/08/ERRATA-PREREG-HSBC-003@%s.md" % h_err[:8]},
}, "w6": {
    "que": {
        "afirmacion_retractada": "ni reducir disparos ni cambiar de proveedor mueve el "
                                 "costo — solo reducir pares",
        "por_que_es_falsa": "el mismo trabajo (demostracion 200x50, 10.000 pares x 100 "
                            "disparos) cuesta USD 3.425 en Rigetti Cepheus y USD 83.000 "
                            "en IonQ Forte. Factor 24,2. El per-shot va de 0,000425 a "
                            "0,08: factor 188.",
        "tabla_recomputada_al_sellar": {b: {"usd_total": round(tot[b], 2),
                                            "cuota_tareas_pct": round(cuota[b], 1),
                                            "cuota_disparos_pct": round(100 - cuota[b], 1)}
                                        for b in sorted(C.TARIFA, key=lambda x: tot[x])},
        "que_era_cierto": "«las tareas dominan» es cierto en Rigetti (87,6 %) e IQM, y "
                          "FALSO en AQT IBEX-Q1 (11,3 %) y en IonQ Forte (3,6 %). La "
                          "cuota recorre un continuo, no un caso aislado: hay DOS "
                          "backends por debajo del 50 %, no uno.",
        "lo_unico_invariante": "la tarifa por tarea, USD 0,30, identica en los cinco "
                               "backends que el instrumento tabula. Eso es lo que se "
                               "midio; «el costo no se mueve» es lo que se escribio.",
        "defecto_B_en_el_instrumento": {
            "cual": "costo_braket_hsbc.py imprimia «EL COSTO LO DOMINAN LAS TAREAS, no "
                    "los disparos» seguida de UN solo ejemplo, el de Rigetti. De ahi "
                    "viajo la frase al artefacto.",
            "arreglo": "el instrumento imprime ahora la cuota POR BACKEND y deriva la "
                       "conclusion de ellas. Chequeo que falla cerrado: si la cuota cruza "
                       "el 50 %, se niega a insinuar una frase general y nombra el backend "
                       "que la desmiente.",
            "efecto_secundario": "ejecutar el arreglo destapo un quinto backend, AQT "
                                 "IBEX-Q1, tambien por debajo del 50 %. La tabla original "
                                 "tenia tres.",
            "por_que_no_bastaba_arreglar_el_sello": "el instrumento habria producido la "
                                 "misma frase la proxima vez.",
        },
        "defecto_C_una_cifra_sin_respaldo": {
            "cual": "el original dice «per-task USD 0,30 identico en los SEIS QPU». "
                    "Nuestro instrumento tabula CINCO.",
            "estado": "PENDIENTE DE VERIFICAR en la fuente. Comprobarlo exige volver a la "
                      "pagina de tarifas de AWS y esta errata no la consulto.",
            "impacto": "ninguno sobre las cifras: ningun numero de esta errata ni del "
                       "original depende de que sean cinco o seis.",
        },
        "QUE_NO_SE_RETRACTA": "la decision operativa. La demostracion acotada sobre "
            "Rigetti Cepheus a USD 3.425 sigue siendo la elegida y sigue siendo la "
            "respuesta al «under what conditions» del §4.2. Se corrige el alcance de la "
            "explicacion, no la decision. El gasto autorizado sigue en US$0 y ninguna "
            "tarea se envio a Braket.",
        "afirmacion_corregida": "la tarifa por tarea (USD 0,30) es identica en los "
            "backends tabulados y no se negocia; por eso en los de disparo barato "
            "(Rigetti, IQM) el costo lo dominan las tareas y reducir disparos no lo mueve "
            "de forma apreciable. En AQT e IonQ Forte no: su disparo cuesta hasta 188 "
            "veces mas, los disparos pasan a ser el 89-96 % del total, y el mismo trabajo "
            "sube de USD 3.425 a USD 83.000. La unica palanca que reduce el costo en "
            "TODOS los backends es reducir pares, y reducir pares rompe la comparabilidad "
            "con el test sellado.",
    },
    "como": {
        "recomputado_por": {"archivo": "costo_braket_hsbc.py", "sha256": "sha256:" + sha(SCRIPT),
                            "publicado_como": "code/costo_braket_hsbc@%s.py" % sha(SCRIPT)[:8],
                            "nota": "version CON el arreglo del defecto B. El original "
                                    "citaba este script por NOMBRE y sin hash, asi que "
                                    "corregirlo no contradice ningun hash sellado."},
        "tarifa": {"fuente": C.FUENTE["url"], "leida": C.FUENTE["leida"],
                   "salvedad": "leida por nosotros; AWS no publica checksum de su pagina."},
        "afirmaciones_ejercidas_antes_de_sellar": 19,
    },
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "local, ningun backend de pago"},
    "porque": {"question": "¿«cambiar de proveedor no mueve el costo» sobrevive a la "
                           "tabla del propio artefacto que lo afirma?",
               "respuesta": "no: factor 24,2 entre el backend mas barato y el mas caro."},
    "quien": {
        "escribio_el_defecto": "la sesion de laboratorio, que redacto y sello "
            "RQ-PREREG-HSBC-003-CUANTICO. La frase paso por la revision de coordinacion y "
            "por el OK de Nicholas sin que ninguno de los tres la contrastara contra la "
            "tabla que estaba dos lineas mas abajo, en el mismo artefacto.",
        "lo_encontro": "la sesion «Rosetta · Cuantico», revisando el SPEC de Laboratorio "
            "Rosetta — FUERA del alcance de esa revision.",
        "verificacion": "coordinacion recomputo con el instrumento antes de redactar; el "
            "laboratorio recomputo de nuevo a mano y ejercio las 19 afirmaciones "
            "comprobables del documento antes de sellar.",
        "lab": "Rosetta Quantum — sesion laboratorio", "lead": "Nicholas Iakl Freundlich",
        "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario.",
    },
}}
_yo = os.path.basename(__file__); _mi = sha(__file__)
exigir_procedencia(doc, extra=(ERRATA, SCRIPT, __file__))
rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(EV, "reports", "2026", "08", NOMBRE)
copias = [(ERRATA, os.path.join(EV, "data", "2026", "08", "ERRATA-PREREG-HSBC-003@%s.md" % h_err[:8])),
          (SCRIPT, os.path.join(EV, "code", "costo_braket_hsbc@%s.py" % sha(SCRIPT)[:8])),
          (__file__, os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8])))]
assert not os.path.exists(dst)
for _, d_ in copias: assert not os.path.exists(d_), d_
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
for s_, d_ in copias:
    shutil.copy2(s_, d_); assert sha(s_) == sha(d_)
assert rs.verify(json.load(open(dst)))
print("ERRATA sellada:", doc["meta"]["content_hash"])
print("corrige       :", orig["meta"]["content_hash"][:24], "(intacto)")
for _, d_ in copias: print("  publicado:", os.path.relpath(d_, EV))
