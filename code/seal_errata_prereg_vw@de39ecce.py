#!/usr/bin/env python3
"""Sella la ERRATA de RQ-PREREG-VW-001. El original NO se toca.

POR QUE UNA ERRATA Y NO UN RE-SELLO
-----------------------------------
El pre-registro se sello y anclo a las 14:56:14Z; el laboratorio corrio el contraste DESPUES.
Re-sellarlo hoy —aunque no le cambiaramos una coma— pondria su fecha DESPUES de los resultados
y romperia lo unico que un pre-registro tiene que garantizar: que estos bytes existian antes
que los datos. Un pre-registro que se corrige reescribiendose deja de ser un pre-registro.

TRES CORRECCIONES, DE TRES CLASES DISTINTAS
-------------------------------------------
  A) DOS CRITERIOS DE FALSACION QUE NO PODIAN FALLAR. El pre-registro fijo tres formas de
     que el instrumento no sirviera. Dos de ellas —«si no ordena» y «si no es monotona»— son
     consecuencia de Eckart-Young, no propiedades del instrumento: el error al truncar es la
     raiz de la energia que queda fuera, asi que bajar chi solo suma terminos no negativos.
     Un pre-registro con tres criterios de los cuales dos son teoremas disfrazados OFRECE MAS
     GARANTIA DE LA QUE DA, y desde fuera se ve identico a uno bueno.
  B) EL ANCLA SE FIJO SIN LEER LA FILA MAS FUERTE DE LA MISMA TABLA. Se anclo sobre
     FWSVD/ASVD/SVD-LLM y la fila de SAES-SVD estaba a dos centimetros. Abierta despues:
     tampoco cumple el umbral, asi que la conclusion se refuerza — pero se habia afirmado
     sin mirarla.
  C) UNA CONCLUSION SOSTENIDA CON n=1. El reshape se midio sobre UNA matriz y se concluyo
     «no hay estructura de orden». La coordinacion avalo ese n argumentando que «la
     comparacion es interna». Con n=21 x 3 semillas la conclusion se DA VUELTA.

  D) Y una anomalia de archivo, declarada aqui para que no quede escondida: el pre-registro
     se sello con `lib_version 3.0.0` sobre una libreria ya modificada, de modo que en el
     archivo `3.0.0` nombra DOS codigos. La version subio a 3.1.0 hacia adelante; este
     artefacto es el unico con esa ambiguedad y queda declarado, no borrado.

GUARDIA: antes de sellar se RECOMPRUEBAN las tres correcciones. Si alguna deja de sostenerse,
aborta — no se sella una correccion cuyas afirmaciones no se verifican al sellarse.

CPU. Sin GPU. Costo US$0.
"""
import glob, hashlib, json, os, sys
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from reloj_sello import ahora_stamp, ahora_iso, coherentes

ORIG = glob.glob(os.path.join(EV, "prereg", "2026", "08", "*RQ-PREREG-VW-001*.json"))[0]
orig = json.load(open(ORIG))
assert rs.verify(orig), "el pre-registro original no verifica"

# ---------------------------------------------------------------- GUARDIA A
# ¿Es cierto que los criterios de monotonia no pueden dar rojo? Se comprueba, no se cita.
rng = np.random.default_rng(11)
N = 256
espectros = {
    "decae exponencial": np.exp(-0.05 * np.arange(N)),
    "plano":             np.ones(N),
    "un solo valor":     np.r_[1.0, np.zeros(N - 1)],
    "creciente":         np.arange(1, N + 1, dtype=float),
    "ruido puro":        np.abs(rng.standard_normal(N)),
}
def err(s, chi):
    s = np.asarray(s, float)
    return float(np.sqrt((s[chi:] ** 2).sum() / (s ** 2).sum()))
contraejemplos = []
for nombre, s in espectros.items():
    e = [err(s, c) for c in range(1, N + 1)]
    if any(e[i + 1] > e[i] + 1e-12 for i in range(len(e) - 1)):
        contraejemplos.append(nombre)
if contraejemplos:
    raise SystemExit("ABORTA: la errata afirma que la monotonia esta garantizada y estos "
                     "espectros la violan: %s" % ", ".join(contraejemplos))

# ---------------------------------------------------------------- GUARDIA B
# La aritmetica del ancla nueva se recomputa; no se copia de un mensaje.
PARAMS_LLAMA7B, BASE_PPL = 6.738e9, 5.68
GB_FP16 = PARAMS_LLAMA7B * 2 / 1e9
if abs(GB_FP16 - 13.48) > 0.01:
    raise SystemExit("ABORTA: LLaMA-7B fp16 recomputa %.2f GB, la errata dice 13,48" % GB_FP16)
SAES = [(10, 7.17), (9, 8.22), (8, 8.96), (7, 10.15)]
tabla_saes = [{"presupuesto_gb": gb,
               "compresion_x": round(GB_FP16 / gb, 2),
               "perplejidad": ppl,
               "veces_la_base": round(ppl / BASE_PPL, 2),
               "degradacion_pct": round(100 * (ppl / BASE_PPL - 1), 1)} for gb, ppl in SAES]
cercano = min(tabla_saes, key=lambda r: abs(r["compresion_x"] - 2.0))
if not (1.9 <= cercano["compresion_x"] <= 2.0 and cercano["degradacion_pct"] > 50):
    raise SystemExit("ABORTA: el punto mas cercano a 2x ya no sostiene la afirmacion")

# ---------------------------------------------------------------- GUARDIA C
# Las frases que esta errata corrige tienen que ESTAR en el original.
crudo = json.dumps(orig, ensure_ascii=False)
for frase in ("Sin señal de estructura de orden", "n=1"):
    if frase not in crudo:
        raise SystemExit("ABORTA: la errata corrige «%s» y esa frase no esta en el "
                         "original — se estaria retractando algo que nadie afirmo" % frase)
if orig["meta"]["sealed_by"]["lib_version"] != "3.0.0":
    raise SystemExit("ABORTA: la anomalia D dice que el original declara 3.0.0 y declara %s"
                     % orig["meta"]["sealed_by"]["lib_version"])

STAMP, ISO = ahora_stamp(), ahora_iso()
assert coherentes(STAMP, ISO)
NOMBRE = ("RosettaQ__ERRATA__RQ-ERRATA-VW-001__%s__"
          "dos-criterios-vacios-un-ancla-sin-leer-y-un-n-de-uno.json" % STAMP)

doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-ERRATA-VW-001", "type": "ERRATA",
    "is_demo": False,
    "scope_note":
        "Errata de RQ-PREREG-VW-001. NO modifica el original: su archivo, su hash y su "
        "ancla de OpenTimestamps quedan intactos. Corrige dos criterios de falsacion que "
        "no podian fallar, un ancla fijada sin leer la fila mas fuerte de la misma tabla, "
        "y una conclusion sostenida con n=1 que con n=21 se da vuelta. Declara ademas una "
        "anomalia de version en el archivo. Las tres correcciones las encontro el propio "
        "laboratorio que escribio el pre-registro.",
    "corrige": {"file_id": orig["meta"]["file_id"],
                "content_hash": orig["meta"]["content_hash"],
                "sealed_at": orig["meta"]["sealed_at"],
                "regla": "el sello original no se reescribe ni se re-sella. Se sello ANTES "
                         "de que existieran los resultados; re-anclarlo hoy pondria su "
                         "fecha despues de ellos."},
}, "w6": {
    "que": {
        "A_criterios_que_no_podian_fallar": {
            "afirmacion_retractada":
                "el pre-registro declara TRES criterios de fallo del instrumento",
            "por_que_es_falsa":
                "los criterios 1 («no ordena») y 3 («no es monotona») son consecuencia de "
                "Eckart-Young y no propiedades del instrumento: el error al truncar es la "
                "raiz de la energia excluida, asi que bajar chi solo suma terminos no "
                "negativos. Comprobado al sellar sobre 5 espectros (exponencial, plano, un "
                "solo valor, creciente, ruido puro): 0 contraejemplos en 256 cortes cada uno.",
            "lo_que_sobrevive": "SOLO el criterio 2. La validacion vale UN BIT: el "
                                "instrumento no reporta salud donde la literatura reporta "
                                "catastrofe. Descarta que este mal escalado; no muestra "
                                "que prediga.",
            "regla_que_sale": "un criterio de fallo se prueba con un caso que lo dispare "
                              "ANTES de sellarlo. Un criterio que nunca se vio en rojo no "
                              "esta probado.",
        },
        "B_ancla_fijada_sin_leer_la_fila_mas_fuerte": {
            "afirmacion_corregida":
                "el ancla se fijo sobre FWSVD/ASVD/SVD-LLM sin abrir la fila de SAES-SVD, "
                "que esta en la MISMA tabla y es el metodo mas fuerte de la familia.",
            "el_ancla_correcta_recomputada_al_sellar": tabla_saes,
            "base_sin_comprimir": BASE_PPL,
            "modelo_gb_fp16": round(GB_FP16, 2),
            "consecuencia":
                "la conclusion se REFUERZA, no se cae: en el punto mas cercano al que exige "
                "el enunciado (%.2fx) el mejor metodo publicado degrada la perplejidad "
                "%.1f %%. Pero se habia afirmado sin mirarlo, y eso es lo que se corrige."
                % (cercano["compresion_x"], cercano["degradacion_pct"]),
            "procedencia":
                "cifras de FWSVD/ASVD/SVD-LLM segun la tabla comparativa de arXiv:2602.03051 "
                "(SAES-SVD), no segun sus papers originales. La fila de SAES-SVD es "
                "AUTORREPORTADA y va marcada como tal.",
            "limitacion_que_va_en_contra_nuestra":
                "ninguna fila de esa tabla es truncamiento simple, que es lo que mide "
                "nuestro instrumento: FWSVD pondera por Fisher, ASVD por activaciones, "
                "SVD-LLM por blanqueo, SAES por supresion de error acumulado. Nuestro error "
                "de Frobenius NO se puede mapear a esas perplejidades: la comparacion es "
                "ORDINAL, no cuantitativa.",
        },
        "C_conclusion_con_n_igual_a_uno": {
            "afirmacion_retractada":
                "«Sin señal de estructura de orden» en el reshape a MPO, medido con n=1.",
            "quien_la_avalo":
                "la coordinacion, argumentando que «la comparacion es interna, ahi el n "
                "importa poco». Falso: la comparacion interna protege contra un sesgo de "
                "escala, NO contra caer en un caso no representativo — y se habia caido en "
                "uno de los mas debiles (q_proj, capa 16).",
            "lo_correcto_con_n_21_por_3_semillas":
                "SI hay estructura de orden, pero solo en la capa 0 de atencion (6,1-11,8 % "
                "bajo el nulo gaussiano de 228) y se apaga con la profundidad. El MLP no la "
                "tiene a ninguna profundidad (0,0-0,2 %).",
            "por_que_la_rama_sigue_cerrada":
                "aun en su punto mas fuerte, chi(90 %) es el 88 % del enlace maximo. Un "
                "corte casi maximamente enredado no comprime. No es «no hay señal»: es «hay "
                "señal y no alcanza», que es mas honesto y mas dificil de refutar.",
        },
        "D_anomalia_de_version_en_el_archivo": {
            "hecho": "RQ-PREREG-VW-001 declara lib_version 3.0.0 con lib_sha256 bbe3ffcd..., "
                     "mientras 61 artefactos declaran 3.0.0 con e5c5d5c3... En el archivo, "
                     "3.0.0 nombra dos codigos.",
            "causa": "la libreria de sellado se edito en el sitio (se le agrego el esquema "
                     "consultable) sin subir LIB_VERSION.",
            "correccion": "LIB_VERSION subio a 3.1.0 HACIA ADELANTE. Este artefacto es el "
                          "unico con la ambiguedad y queda DECLARADO, no borrado: un "
                          "archivo auditable no es uno sin anomalias, es uno donde cada "
                          "anomalia tiene su explicacion sellada al lado.",
            "no_se_corrige_re_sellando": "eso moveria la fecha del pre-registro a despues "
                                         "de los resultados — se cambiaria lo que sostiene "
                                         "el edificio por lo que se ve bien en una etiqueta.",
        },
        "LO_QUE_NO_SE_RETRACTA":
            "la decision de entrar al track y el encuadre del entregable. Y la afirmacion "
            "central del informe, que NO depende de nada que hayamos construido nosotros: "
            "el estado del arte publicado de la descomposicion de bajo rango 2D no alcanza "
            "el umbral de este desafio.",
    },
    "como": {"guardia_al_sellar":
                 "las tres correcciones se recomputan antes de sellar: la monotonia sobre 5 "
                 "espectros x 256 cortes, la aritmetica del ancla desde el conteo de "
                 "parametros, y la presencia literal en el original de las frases que se "
                 "retractan. Si alguna falla, aborta.",
             "compute": "CPU. Sin GPU. US$0."},
    "cuando": {"archived_at": ISO, "original_sellado_a": orig["meta"]["sealed_at"]},
    "donde": {"original": os.path.basename(ORIG)},
    "porque": {"question": "¿que afirmo el pre-registro que la medicion posterior no "
                           "sostiene, y como se corrige sin tocar el sello?",
               "para_que": "un pre-registro que se publica con su defecto adentro vale mas "
                           "que uno que acierta callandolo — y es exactamente lo que le "
                           "exigimos a todos los demas."},
    "quien": {"encontro_los_defectos": "Rosetta Quantum — sesion laboratorio (los tres, "
                                       "sobre su propio trabajo)",
              "sella": "Rosetta Q Main (notario)",
              "lead": "Nicholas Iakl Freundlich"},
}}
_mi = "sha256:" + hashlib.sha256(open(__file__, "rb").read()).hexdigest()
rs.seal(doc, harness=("seal_errata_prereg_vw.py", "1.0.0", _mi),
        sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(EV, "prereg", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
assert rs.verify(json.load(open(dst)))
print("ERRATA sellada  :", doc["meta"]["content_hash"])
print("corrige         :", orig["meta"]["file_id"], orig["meta"]["content_hash"][:24])
print("lib_version     :", doc["meta"]["sealed_by"]["lib_version"], "(el original: 3.0.0)")
print("guardias        : monotonia 5/5 espectros · ancla recomputada · frases presentes")
print("archivo         :", NOMBRE)
