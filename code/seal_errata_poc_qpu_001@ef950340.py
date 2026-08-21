#!/usr/bin/env python3
"""Sella la ERRATA de RQ-POC-QPU-001. No toca el sello original: publicado es publicado.

QUE CORRIGE
-----------
El sello RQ-POC-QPU-001 afirma «62.6% de la masa cae en el bolsillo alosterico
(estructura, no ruido blanco)». Dos defectos independientes:
  A) el numero esta calculado leyendo la cadena de bits SIN invertir, al reves de la
     convencion que usa el harness que el propio sello declara. La masa es 0,3534.
  B) el bolsillo son 8 de 12 nodos, asi que el ruido uniforme deposita 0,6667 ahi por
     pura geometria: las dos cifras estan POR DEBAJO del azar y ninguna sostiene la
     frase. Y la estructura medida no es la del caminante — comparada contra la
     caminata ideal, que se publica junto a esta errata.

Lo que NO se toca: el archivo original, su hash y su ancla. Esta errata se encadena.

GUARDIA
-------
Antes de sellar se recomputan, desde el crudo publicado, las cifras que la errata
afirma. Si alguna dejo de reproducir, aborta: no se sella una correccion cuyas propias
cifras no se sostienen en el momento de sellarla.

Simulacion y lectura de archivos ya publicados. Costo US$0.
"""
import hashlib, json, os, shutil, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

ERRATA   = os.path.join(RAIZ, "ERRATA-POC-QPU-001-borrador.md")
DIST     = os.path.join(AQUI, "dist_ideal_KRAS_G12C.json")
GEN      = os.path.join(AQUI, "ideal_ctqw_kras.py")
IBM_RUN  = os.path.join(RAIZ, "poc", "poc_ibm_run.py")
FETCH    = os.path.join(RAIZ, "quantum-run", "fetch_job.py")
CRUDO    = os.path.join(EV, "code", "poc_job_d9mu2bmij12s73ft86t0@3b45dd49.json")
HARNESS  = os.path.join(EV, "code", "poc_ibm@db044b45.py")
SELLO    = os.path.join(EV, "runs", "2026", "08",
                        "RosettaQ__RUN__RQ-POC-QPU-001__20260801T1851Z__ctqw-kras-ibm-kingston.json")

orig = json.load(open(SELLO))
assert rs.verify(orig), "el sello original no verifica: no se le encadena una errata"

# ---------------------------------------------------------------- GUARDIA
# Se recomputan desde el crudo las cifras que la errata afirma. Falla cerrado.
counts = json.load(open(CRUDO))["resultado_crudo"][0]["data"]["c"]["counts"]
inv = [0]*12; dire = [0]*12; n_val = 0; n_tot = 0
for b, c in counts.items():
    b = b.replace(" ", ""); n_tot += c
    if b.count("1") == 1:
        inv[b[::-1].index("1")] += c; dire[b.index("1")] += c; n_val += c
POCKET = orig["w6"]["que"]["pocket_nodes"]
m_sello = round(sum(dire[i] for i in POCKET) / n_val, 4)
m_corr  = round(sum(inv[i]  for i in POCKET) / n_val, 4)
esperado = {"shots": 2000, "validos": 1228, "cadenas": 301,
            "masa_sello": 0.6262, "masa_corregida": 0.3534,
            "uniforme": round(len(POCKET)/12, 4)}
obtenido = {"shots": n_tot, "validos": n_val, "cadenas": len(counts),
            "masa_sello": m_sello, "masa_corregida": m_corr,
            "uniforme": round(len(POCKET)/12, 4)}
if obtenido != esperado:
    raise SystemExit("ABORTA: las cifras de la errata no reproducen desde el crudo.\n"
                     "  esperado: %s\n  obtenido: %s" % (esperado, obtenido))
if m_sello != orig["w6"]["que"]["masa_bolsillo_alosterico_cond_validos"]:
    raise SystemExit("ABORTA: la convencion sin invertir ya no reproduce el sello — el "
                     "diagnostico del defecto A dejo de sostenerse")
# el argumento del §2 se apoya en que el harness publicado ES el que el sello declara
if "sha256:" + sha(HARNESS) != orig["meta"]["sealed_by"]["harness_sha256"]:
    raise SystemExit("ABORTA: el harness publicado no es el que el sello declara — el "
                     "argumento del §2 se quedaria sin su archivo")

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
h_err = sha(ERRATA)
NOMBRE = ("RosettaQ__ERRATA__RQ-ERRATA-POC-QPU-001__%s__"
          "masa-en-bolsillo-bajo-el-azar-y-etiquetas-espejadas.json" % STAMP)
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-ERRATA-POC-QPU-001", "type": "ERRATA",
    "is_demo": False,
    "scope_note": "Errata del sello RQ-POC-QPU-001. NO modifica el original: publicado es "
                  "publicado, y el archivo, su hash y su ancla quedan intactos. Corrige "
                  "una cifra mal calculada y retracta la inferencia que se apoyaba en "
                  "ella. Revisada por la sesion de coordinacion y aprobada por Nicholas "
                  "antes de sellar.",
    "nota_para_el_notario": "El tipo ERRATA es nuevo en esta taxonomia. Se archiva bajo "
                            "reports/ —que ya esta en ARCHIVE_GLOBS— a proposito: una "
                            "carpeta nueva habria quedado fuera del notario, del auditor "
                            "de procedencia y de la copia a D1 hasta que alguien se "
                            "acordara de agregarla, que es exactamente el fallo del "
                            "'63 de 64'. Si prefieres otra ubicacion, se mueve.",
    "corrige": {"file_id": "RQ-POC-QPU-001",
                "content_hash": orig["meta"]["content_hash"],
                "sealed_at": orig["meta"]["sealed_at"],
                "regla": "el sello original no se reescribe ni se re-sella."},
    "texto_fuente": {"archivo": "ERRATA-POC-QPU-001.md", "sha256": "sha256:" + h_err,
                     "publicado_como": "data/2026/08/ERRATA-POC-QPU-001@%s.md" % h_err[:8]},
}, "w6": {
    "que": {
        "afirmacion_retractada": orig["w6"]["que"]["outcome"],
        "defecto_A_numero_mal_calculado": {
            "causa": "la cadena de bits se leyo SIN invertir. En qiskit el caracter mas a "
                     "la izquierda es el bit mas alto, asi que el indice del nodo se "
                     "obtiene con b[::-1].index('1'). El harness que el propio sello "
                     "declara (poc_ibm.py, ideal_probs) invierte; el sello no.",
            "masa_bolsillo_sellada": m_sello, "masa_bolsillo_corregida": m_corr,
            "masa_fuente_sellada": 0.0358, "masa_fuente_corregida": 0.1515,
            "efecto": "espejo exacto, nodo i <-> nodo 11-i",
        },
        "defecto_B_estadistico_no_sostiene": {
            "bolsillo_nodos": len(POCKET), "nodos_totales": 12,
            "baseline_azar_uniforme": round(len(POCKET)/12, 4),
            "IC95_wilson_sellada": [0.5988, 0.6528],
            "IC95_wilson_corregida": [0.3272, 0.3806],
            "lectura": "las dos cifras estan POR DEBAJO del azar y su IC no lo toca. El "
                       "estadistico citado como prueba de estructura apunta al reves.",
        },
        "la_estructura_no_es_la_del_caminante": {
            "chi2_vs_uniforme": 1167.0, "gl": 11,
            "chi2_vs_ideal_trotter_r2": 18804,
            "spearman_ideal_vs_medido_corregido": 0.266,
            "spearman_ideal_vs_medido_sellado": -0.196,
            "TVD_medido_uniforme": 0.408, "TVD_medido_ideal": 0.616,
            "conclusion": "la distribucion no es plana, pero su desviacion no apunta "
                          "hacia la fisica del caminante — y eso vale bajo LAS DOS "
                          "convenciones de bits, que es lo que lo vuelve solido.",
        },
        "modelo_descartado": {
            "cual": "medido = lambda*ideal + (1-lambda)*uniforme",
            "lambda_ajustado": 0.015, "chi2": 1166.7, "gl": 10,
            "contra_uniforme_puro": 1167.0,
            "por_que_se_publica": "era la lectura favorable —una caminata real lavada por "
                                  "ruido— y no sobrevivio a la prueba. Cero mejora.",
        },
        "QUE_QUEDA_INTACTO": {
            "proposito_del_sello": orig["w6"]["porque"]["question"],
            "supervivencia_one_hot": round(n_val/n_tot, 4),
            "nota": "el proposito declarado se sostiene entero y su respuesta es "
                    "correcta: se reprodujo exacta desde el crudo publicado. "
                    "cruce_ventaja_cuantica sigue en 0.",
        },
        "afirmacion_corregida": "el circuito se ejecuta en hardware real y el 61,4 % de "
                "los disparos sobrevive como fisica valida; la estructura del caminante "
                "NO sobrevive al ruido, medido contra la caminata ideal publicada aqui.",
        "alcance_del_defecto": "llego al archivo y a notas internas. NO viajo al paquete "
                "entregado a Cleveland: se revisaron los 5 archivos de la postulacion "
                "—dos PDF, el CSV de corridas, el harness y el artefacto JSON— y ninguno "
                "menciona esta corrida ni esta cifra.",
        "hueco_declarado": "el sello nombra al recolector fetch_job.py pero NO registra "
                "su sha256, asi que no se puede fijar que version bajo estos conteos. Se "
                "publica la version actual como referencia y el argumento no depende de "
                "ella: la contradiccion se establece entre el crudo publicado y el "
                "harness que el sello declara.",
    },
    "como": {
        "recomputo": "desde code/poc_job_d9mu2bmij12s73ft86t0@3b45dd49.json, sobre los "
                     "conteos ENTEROS y no sobre la distribucion redondeada a 4 decimales "
                     "que guarda el sello (la diferencia es de la tercera cifra y se "
                     "declara en el documento).",
        "distribucion_ideal": {"archivo": "dist_ideal_KRAS_G12C.json",
                               "sha256": "sha256:" + sha(DIST),
                               "publicado_como": "code/dist_ideal_KRAS_G12C@%s.json" % sha(DIST)[:8],
                               "autosuficiente": "trae adentro W, v y la fuente, asi que se "
                                   "recomputa con seis lineas de numpy sin el pickle "
                                   "original —que vive en un repo PRIVADO y solo carga con "
                                   "numpy 2.x— ni ningun codigo nuestro."},
        "generador": {"archivo": "ideal_ctqw_kras.py", "sha256": "sha256:" + sha(GEN),
                      "publicado_como": "code/ideal_ctqw_kras@%s.py" % sha(GEN)[:8]},
        "evidencia_concurrente": {"archivo": "poc_ibm_run.py", "sha256": "sha256:" + sha(IBM_RUN),
                                  "publicado_como": "code/poc_ibm_run@%s.py" % sha(IBM_RUN)[:8],
                                  "que_muestra": "su counts_to_p1 invierte la cadena y lo "
                                      "documenta: 'qiskit: bit string little-endian'."},
        "recolector_de_referencia": {"archivo": "fetch_job.py", "sha256": "sha256:" + sha(FETCH),
                                     "publicado_como": "code/fetch_job@%s.py" % sha(FETCH)[:8],
                                     "salvedad": "version ACTUAL; el sello no registra cual "
                                         "corrio."},
    },
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "local, sin backend de pago"},
    "porque": {"question": "¿la cifra que RQ-POC-QPU-001 publica como prueba de estructura "
                           "distingue senal de ruido?",
               "respuesta": "no. Esta por debajo del azar geometrico, y ademas estaba mal "
                            "calculada."},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "revision": "sesion de coordinacion; aprobada por Nicholas antes de sellar",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}
_yo = os.path.basename(__file__); _mi = sha(__file__)
exigir_procedencia(doc, extra=(ERRATA, DIST, GEN, IBM_RUN, FETCH, __file__))
rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)

dst = os.path.join(EV, "reports", "2026", "08", NOMBRE)
copias = [(ERRATA, os.path.join(EV, "data", "2026", "08", "ERRATA-POC-QPU-001@%s.md" % h_err[:8])),
          (DIST,   os.path.join(EV, "code", "dist_ideal_KRAS_G12C@%s.json" % sha(DIST)[:8])),
          (GEN,    os.path.join(EV, "code", "ideal_ctqw_kras@%s.py" % sha(GEN)[:8])),
          (IBM_RUN,os.path.join(EV, "code", "poc_ibm_run@%s.py" % sha(IBM_RUN)[:8])),
          (FETCH,  os.path.join(EV, "code", "fetch_job@%s.py" % sha(FETCH)[:8])),
          (__file__, os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8])))]
assert not os.path.exists(dst), "publicado es publicado: no se reescribe un sello"
for _, d in copias:
    assert not os.path.exists(d), "ya existe: %s" % d
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
for s_, d_ in copias:
    shutil.copy2(s_, d_); assert sha(s_) == sha(d_), "la copia no calza: %s" % d_
assert rs.verify(json.load(open(dst)))
print("ERRATA sellada :", doc["meta"]["content_hash"])
print("corrige        :", orig["meta"]["content_hash"][:24], "(intacto)")
print("publicados     :", len(copias), "archivos")
for _, d_ in copias: print("   ", os.path.relpath(d_, EV))
