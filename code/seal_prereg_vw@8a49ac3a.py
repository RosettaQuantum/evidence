#!/usr/bin/env python3
"""Sella el PRE-REGISTRO del track VW, ANTES de que existan los resultados del contraste.

POR QUE ESTE SELLO Y POR QUE AHORA
----------------------------------
El laboratorio escribio `lab-vw-2026-08-26/PREREG-calibracion.md` y lo corrio despues. Ese
archivo dice, entre otras cosas, TRES FORMAS DE QUE EL INSTRUMENTO NO SIRVA. Un criterio de
fallo escrito antes vale; el mismo criterio escrito despues no vale nada, y desde fuera
**los dos se ven identicos**. Lo unico que los distingue es una marca de tiempo que no
podamos mover — por eso el sello va antes del resultado y se ancla.

QUE NO HACE ESTE ARNES: no copia el texto del pre-registro a mano. El markdown se archiva
POR ARCHIVO y se referencia POR HASH. La regla de la casa es que los documentos no pasan
por el contexto de un modelo, porque se corrompen en silencio — `micrositio` por `micrositio`
con una tilde invisible, mismo largo, ningun chequeo de tamaño lo ve.
"""
import hashlib, json, os, shutil, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "evidence", "harness"))
import rosettaq_seal as rs

SELLADO_A = "2026-08-27T14:56:14+00:00"
STMT = "/Users/nicholasiakl/Downloads/VW-Group-Challenge-Statement-vF.pdf"
PREREG_MD = os.path.join(RAIZ, "lab-vw-2026-08-26", "PREREG-calibracion.md")

def sha(p):
    return "sha256:" + hashlib.sha256(open(p, "rb").read()).hexdigest()

stmt_sha, md_sha = sha(STMT), sha(PREREG_MD)

# El markdown del laboratorio se ARCHIVA como archivo, no se transcribe.
DST_MD = os.path.join(RAIZ, "evidence", "code",
                      "PREREG-calibracion-vw@%s.md" % md_sha.split(":")[1][:8])
if not os.path.exists(DST_MD):
    shutil.copy2(PREREG_MD, DST_MD)
assert sha(DST_MD) == md_sha, "la copia archivada no coincide con el original"

NOMBRE = ("RosettaQ__PREREG__RQ-PREREG-VW-001__20260827T1456Z__"
          "calibracion-del-instrumento-y-alcance-declarado.json")

doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-PREREG-VW-001", "type": "PREREG",
    "is_demo": False,
    "scope_note":
        "Pre-registro del track VW (Quantum-Enhanced Vision-Language-Action Models) del "
        "2026 Global Quantum + AI Challenge. Sellado ANTES de correr el contraste de "
        "calibracion contra la literatura de bajo rango. Entrada al track decidida por "
        "Nicholas el 27-ago-2026 tras cerrar por medicion las cuatro vias del enunciado. "
        "Todas las citas del statement se leyeron del PDF oficial, no de relevos.",
    "statement_oficial": {"archivo": "VW-Group-Challenge-Statement-vF.pdf",
                          "sha256": stmt_sha, "paginas": 10},
    "prereg_del_laboratorio": {
        "archivo": os.path.basename(DST_MD), "sha256": md_sha,
        "escrito_por": "Rosetta Q Lab", "escrito_a": "2026-08-27T11:49:49-03:00",
        "nota": "El contenido vive en ese archivo. Aqui se referencia por hash: no se "
                "transcribio."},
}, "w6": {
    "que": {
        "objetivo_del_challenge_textual":
            "«Demonstrate a clear, well-justified quantum-enhanced or quantum-inspired "
            "computational advantage over an accepted classical baseline.» (§4.1). "
            "Sub-track elegido: Compression, Application Context 1 (Autonomous Driving) — "
            "modelo de referencia LLaVA-1.5-7B, baseline aceptado INT8 via bitsandbytes.",
        "DECISION_que_entregamos":
            "NO entregamos un metodo de compresion: entregamos la medicion de lo que el "
            "espectro de LLaVA-1.5-7B dice sobre la afirmacion del propio §5.1 del "
            "enunciado — «MPS and TTNS ... enabling 2-10x compression while preserving "
            "accuracy». Las tres vias de compresion se midieron y ninguna cruza el umbral.",
        "DECISION_como_se_llama":
            "NO se llama «tamiz de factibilidad» ni «curva de calibracion» mientras no "
            "este validado. Un tamiz PREDICE; nosotros describimos un modelo. Y tres "
            "compresiones de UN modelo son tres puntos de una recta, no una curva. "
            "Ponerle a un objeto el nombre de lo que queremos que sea es el defecto que "
            "este equipo corrigio cuatro veces el 27-ago.",
        "resultados_ya_medidos_antes_de_este_sello": {
            "reparto_de_chi_por_capa":
                "1.02x-1.08x de mejora sobre corte uniforme en espectros REALES, contra "
                "1.1x-18.8x en espectros sinteticos fabricados por nosotros. La "
                "heterogeneidad real entre capas es 1.22x, no las ~15x del sintetico.",
            "error_a_la_compresion_exigida":
                "Frobenius relativo, 21 matrices (7 tipos x 3 capas): mediana ~0.55 y peor "
                "0.5924 a 2x. Las del MLP, que son las que mas parametros tienen, son las "
                "peores. Una cifra previa de 0.4397 salio de una muestra solo de atencion "
                "y era optimista: queda corregida aqui.",
            "reshape_a_MPO":
                "corte del medio, capa 16 q_proj: orden natural chi(90%)=226 contra "
                "permutado al azar 228. Sin señal de estructura de orden. n=1 declarado.",
        },
        "LIMITES_de_lo_que_medimos":
            "Es error de reconstruccion de PESOS, no caida de precision en tarea. No dice "
            "si la sanacion recupera, ni si TTNS se comporta distinto de MPO, ni que pasa "
            "combinando redes tensoriales con cuantizacion — que es lo que hace "
            "CompactifAI, el paper que el propio enunciado cita.",
    },
    "como": {
        "obtencion_de_pesos":
            "peticiones HTTP por rango sobre los safetensors publicados: se lee la "
            "cabecera JSON con los desplazamientos y se pide solo el tensor buscado. 32 MB "
            "por matriz en vez de 14 GB de modelo.",
        "contraste_de_calibracion":
            "contra la familia de bajo rango sobre LLaMA-7B (FWSVD, ASVD, SVD-LLM), que "
            "hace NUESTRA operacion —truncamiento de SVD 2D— y publica precision a razones "
            "declaradas. NO contra CompactifAI: ellos validan MPO mas sanacion, que es "
            "otra operacion.",
        "procedencia_de_las_cifras_del_contraste":
            "tabla comparativa de arXiv:2602.03051 (SAES-SVD, 3-feb-2026), abierta por el "
            "laboratorio. Son cifras que un TERCERO reporta de esos tres metodos, no las "
            "que cada metodo publica de si mismo. Se declara porque no siempre coinciden.",
        "compute": "CPU. Cero GPU. Cero gasto — el tope autorizado era US$40 y no se usa.",
    },
    "cuando": {"archived_at": SELLADO_A, "fase_I_cierra": "2026-09-15",
               "entrega_a_Nicholas": "2026-09-14 (margen, no plan)"},
    "donde": {"trabajo": "lab-vw-2026-08-26 (arbol del laboratorio, un actor)",
              "paquete": "evidence-staging y evidence (coordinacion)"},
    "porque": {
        "question":
            "¿puede la compresion por redes tensoriales llevar un VLAM de 7B a hardware "
            "embarcado sin perder precision, como afirma el §5.1 del enunciado — y se "
            "puede saber ANTES de gastar en GPU?",
        "para_que":
            "el problema declarado de VW es meter un VLAM en un SoC de vehiculo. Hoy si "
            "una campaña de compresion va a funcionar se descubre despues de pagarla.",
    },
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "coordinacion": "Rosetta Q Main (notario)",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes":
                  "medicion y guion del laboratorio; informe, guardias y sello de la "
                  "coordinacion; el texto que lee el jurado pasa por Nicholas antes de "
                  "salir."},
    "DECLARACION_de_lo_que_NO_vamos_a_cumplir": {
        "nota": "Se fija ANTES para que no se pueda ablandar despues. Van en el CUERPO del "
                "informe, no en un apendice.",
        "§4.1_ventaja": "NO se demuestra ventaja sobre el baseline clasico. Nuestra "
                        "contribucion propia midio 1.02x.",
        "R2_parametros_a_precision_equivalente": "NO se logra.",
        "R15_latencia": "NO se reporta latencia de inferencia del modelo desplegado: no "
                        "tenemos un VLAM comprimido que medir. Poner ahi la latencia del "
                        "instrumento seria un numero correcto en la casilla equivocada.",
        "amparo_textual": "§5.5: «Submissions are not penalized for accuracy degradation "
                          "below the stated minimum threshold, provided the tradeoff is "
                          "clearly characterized.»",
    },
}}
_mi = "sha256:" + hashlib.sha256(open(__file__, "rb").read()).hexdigest()
rs.seal(doc, harness=("seal_prereg_vw.py", "1.0.0", _mi),
        sealed_at=SELLADO_A, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(RAIZ, "evidence", "prereg", "2026", "08", NOMBRE)
assert not os.path.exists(dst), "ya existe: no se re-sella sin bloque de correccion"
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
assert rs.verify(json.load(open(dst))), "no verifica desde disco"
print("PREREG sellado   :", doc["meta"]["content_hash"])
print("statement anclado:", stmt_sha[:31])
print("prereg del lab   :", md_sha[:31], "->", os.path.basename(DST_MD))
print("archivo          :", NOMBRE)
