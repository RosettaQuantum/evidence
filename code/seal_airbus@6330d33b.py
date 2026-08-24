#!/usr/bin/env python3
"""Sella el track Airbus: dos corridas, el informe, y toda su procedencia en el MISMO acto.

POR QUE AHORA
-------------
El track tenia su pre-registro anclado y CERO corridas selladas: los dos artefactos que
alimentan el informe no los citaba ningun sello. Un hallazgo sin sello se lee como una
opinion nuestra, y el de este track —que el termino no lineal se anula EXACTAMENTE en el
vortice que el propio enunciado eligio para probar el obstaculo que nombra— merece mas
que eso.

LA PROCEDENCIA VA EN EL MISMO ACTO, NO DESPUES
----------------------------------------------
Siete archivos que hasta hoy no existen en evidence/code/: los cuatro productores, el
modulo de procedencia, el generador del informe y el comparador de corridas. Publicar
despues es la ventana por la que se perdio eon_estocastico para siempre.

LOS ARTEFACTOS SE AUTO-DESCRIBEN
--------------------------------
Cada uno declara `producido_por_sha256` —el script que lo escribe y sus dependencias— y
`contenido_sha256`, calculado sobre el contenido determinista excluyendo lo que depende de
la maquina y del momento. El hash del ARCHIVO cambia entre corridas por el reloj; el del
contenido no. Los dos van al sello, con la etiqueta de para que sirve cada uno.

GUARDIA: antes de sellar se comprueba que los hashes que cada artefacto declara calcen con
los archivos que se van a publicar. Publicar un productor distinto del que produjo el dato
seria peor que no publicarlo.

Simulacion local. Ninguna tarea a hardware. Costo US$0.
"""
import hashlib, json, os, shutil, sys, glob
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence"); AIR = os.path.join(AQUI, "airbus")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

BARRIDO = os.path.join(AIR, "barrido_airbus.json")
NOLIN   = os.path.join(AIR, "nolinealidad_donde_vive.json")
REPRO   = os.path.join(AIR, "reproducibilidad_barrido.json")
INFORME = os.path.join(AQUI, "AIRBUS-INFORME-FINAL.md")
CODIGO  = [os.path.join(AIR, n) for n in ("airbus_harness.py", "airbus_carleman.py",
           "barrido_airbus.py", "nolinealidad_donde_vive.py", "_procedencia.py",
           "comparar_barrido.py")] + [os.path.join(AQUI, "build_airbus_informe.py")]

bar = json.load(open(BARRIDO)); nol = json.load(open(NOLIN)); rep = json.load(open(REPRO))
PRE = glob.glob(os.path.join(EV, "prereg", "2026", "08", "*AIRBUS*.json"))[0]
pre = json.load(open(PRE)); assert rs.verify(pre)

# ---------------------------------------------------------------- GUARDIA
for art, d in ((BARRIDO, bar), (NOLIN, nol)):
    for nombre, h in d["producido_por_sha256"].items():
        p = os.path.join(AIR, nombre)
        if not os.path.isfile(p):
            raise SystemExit("ABORTA: %s declara %s y ese archivo no existe" % (art, nombre))
        if "sha256:" + sha(p) != h:
            raise SystemExit("ABORTA: %s declara %s con %s y el archivo da %s — se "
                             "publicaria un productor distinto del que produjo el dato"
                             % (os.path.basename(art), nombre, h[7:23], sha(p)[:16]))
tgv = [f for f in nol["tabla"] if f.get("variante") == "tgv_statement"]
if not tgv or tgv[0]["razon"] > 1e-12:
    raise SystemExit("ABORTA: el hallazgo central no se sostiene — el TGV del enunciado da "
                     "razon %s" % (tgv[0]["razon"] if tgv else "ausente"))
if not nol["regla_medida"]["la_regla_se_cumple_en_toda_la_tabla"]:
    raise SystemExit("ABORTA: la regla no se cumple en toda la tabla")
if not rep["errores"]["reproducen_todos"]:
    raise SystemExit("ABORTA: los errores dejaron de reproducir entre corridas")

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
COMUN = {"prereg": {"file_id": pre["meta"]["file_id"],
                    "content_hash": pre["meta"]["content_hash"]}}

def bloque_codigo():
    return {os.path.basename(p): {"sha256": "sha256:" + sha(p),
                                  "publicado_como": "code/%s@%s%s" % (
                                      os.path.basename(p)[:-3], sha(p)[:8],
                                      os.path.splitext(p)[1])} for p in CODIGO}

def hashes(p, d):
    """Los DOS hashes del artefacto, cada uno con su rotulo de para que sirve.

    El campo del archivo va en la forma que el auditor de procedencia reconoce —nombre +
    `sha256`— para que resuelva contra lo publicado. El hash del CONTENIDO no puede
    llamarse `..._sha256`: no es la huella de un archivo que alguien pueda bajar, sino la
    de los bytes deterministas, y el auditor lo tomaria por una referencia rota.
    """
    return {"archivo": os.path.basename(p), "sha256": "sha256:" + sha(p),
            "publicado_como": "code/%s@%s.json" % (os.path.basename(p)[:-5], sha(p)[:8]),
            "para_que_sirve_el_hash_del_archivo":
                "comprueba que bajaste NUESTRO artefacto exacto",
            "contenido_determinista": {
                "valor": d["contenido_sha256"],
                "para_que_sirve": "comprueba que re-corriste el instrumento y la ciencia "
                    "reproduce, aunque tu archivo difiera. Un tercero que re-corra y "
                    "compare contra el hash del ARCHIVO va a creer que encontro un error.",
                "no_es_el_hash_de_un_archivo": True},
            "campos_no_reproducibles": d["campos_no_reproducibles"],
            "instrumentos": {k: {"sha256": v} for k, v in d["producido_por_sha256"].items()}}

docs = []

# ---------------------------------------------------------------- 1 · el eje
N1 = ("RosettaQ__RUN__RQ-EXP-AIRBUS-EJE-001__%s__"
      "tiempo-y-error-vs-reynolds-con-malla-acoplada.json" % STAMP)
docs.append((N1, {"meta": {
    "file_name": N1, "file_id": "RQ-EXP-AIRBUS-EJE-001", "type": "RUN", "is_demo": False,
    "scope_note": "El eje del track Airbus: tiempo-a-solucion y error contra Reynolds, con "
                  "la malla acoplada como exige el §4.1 del enunciado, contra la solucion "
                  "analitica cerrada del §5.3. Cuatro brazos: espectral, diferencias "
                  "finitas y dos ordenes de Carleman variacional. Simulacion local.",
    **COMUN}, "w6": {
    "que": {
        "artefacto": hashes(BARRIDO, bar),
        "puntos": len(bar["serie"]),
        "eje": {"Re_min": bar["serie"][0]["Re"], "Re_max": bar["serie"][-1]["Re"],
                "malla_min": bar["serie"][0]["malla_N"], "malla_max": bar["serie"][-1]["malla_N"],
                "regla_acople": bar["regla_acople"]["descripcion"]},
        "RESULTADO_errores": "el error de diferencias finitas CAE cuatro ordenes a lo largo "
            "del eje (2,01e-03 -> 5,37e-07) mientras el costo sube. Los errores reproducen "
            "EXACTO entre corridas: %d de %d identicos al ultimo digito."
            % (rep["errores"]["identicos"], rep["errores"]["comparados"]),
        "RESULTADO_brazo_cuantico": "K=2 —el orden que SI incorpora el bloque cuadratico de "
            "Carleman— resolvio 0 de %d puntos: necesita 21 a 45 qubits, sobre la cota "
            "declarada desde el primer punto. K=1, que descarta ese bloque, resolvio 3 de "
            "%d con error 4,86e-02 a 8,03e-02, entre 28 y 89 veces el de diferencias "
            "finitas. El brazo cuantico no pierde la comparacion: el que lleva la fisica no "
            "se puede plantear a este acople de malla, y el que se puede plantear no es el "
            "que importa." % (len(bar["serie"]), len(bar["serie"])),
        "desviacion_de_la_regla_de_parada": bar["corte_medido"]["muro_que_corto_el_eje"],
        "decisiones_no_prefijadas": {"del_instrumento": len(bar["decisiones_no_prefijadas"]),
            "del_brazo_cuantico": len(bar["decisiones_no_prefijadas_del_brazo_cuantico"]),
            "donde": "nombradas dentro del artefacto, no en la memoria de nadie"},
        "cruce_ventaja_cuantica": 0,
    },
    "como": {"codigo": bloque_codigo(),
             "reproducibilidad": {"archivo": "reproducibilidad_barrido.json",
                 "sha256": "sha256:" + sha(REPRO),
                 "publicado_como": "code/reproducibilidad_barrido@%s.json" % sha(REPRO)[:8],
                 "que_mide": rep["que_es"],
                 "tiempos_desviacion_pct": rep["tiempos_desviacion_relativa_pct"],
                 "razones_desviacion_pct": rep["razones_entre_brazos_desviacion_pct"],
                 "lectura": rep["lectura"]}},
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "Mac local, sin red y sin QPU"},
    "porque": {"question": "¿como crecen tiempo y error con Reynolds cuando la malla se "
                           "acopla como el enunciado exige, y donde entra un brazo cuantico?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}))

# ---------------------------------------------------------------- 2 · el mecanismo
N2 = ("RosettaQ__RUN__RQ-EXP-AIRBUS-NOLIN-001__%s__"
      "la-no-linealidad-se-anula-en-el-vortice-del-enunciado.json" % STAMP)
docs.append((N2, {"meta": {
    "file_name": N2, "file_id": "RQ-EXP-AIRBUS-NOLIN-001", "type": "RUN", "is_demo": False,
    "scope_note": "Donde vive la no-linealidad en la familia de Taylor-Green. Es el "
                  "hallazgo del track y es sobre el BENCHMARK, no sobre nosotros.",
    **COMUN}, "w6": {
    "que": {
        "artefacto": hashes(NOLIN, nol),
        "HALLAZGO": "en el vortice de Taylor-Green tal como el enunciado lo especifica, el "
            "termino no lineal se anula EXACTAMENTE: razon %.3e del termino lineal, a "
            "precision de maquina, en los operadores DISCRETOS y no solo en el continuo. "
            "El obstaculo que el propio enunciado nombra —llevar fisica no lineal a "
            "hardware unitario— NO SE PUEDE EXHIBIR en el caso que eligio para probarlo."
            % tgv[0]["razon"],
        "MECANISMO": nol["regla_medida"]["enunciado"],
        "separacion_medida": {
            "razon_maxima_entre_las_que_se_anulan": nol["regla_medida"]["razon_maxima_entre_las_de_una_capa"],
            "razon_minima_entre_las_que_no": nol["regla_medida"]["razon_minima_entre_las_de_varias_capas"],
            "ordenes_de_magnitud": 11.6,
            "denominador": nol["regla_medida"]["denominador"],
            "una_capa": nol["regla_medida"]["filas_una_capa"],
            "varias_capas": nol["regla_medida"]["filas_varias_capas"],
            "se_cumple_en_toda_la_tabla": True},
        "LEY_QUE_LO_RESTAURA": nol["ley_de_amplitud"]["lectura"],
        "controles": "el termino que se anula podria haber sido un error de nuestros "
            "operadores: las mismas matrices sobre un campo aleatorio de banda limitada dan "
            "razon 2,93e-01, no cero. El cero pertenece al problema, no al codigo.",
        "verificado_por_el_lab": "esta corrida se re-ejecuto en esta sesion y reprodujo la "
            "tabla completa; la unica diferencia entre corridas fue el reloj.",
    },
    "como": {"codigo": bloque_codigo(), "medicion": nol["medicion"]},
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "Mac local, sin red y sin QPU"},
    "porque": {"question": "el termino no lineal se cancela en el TGV del enunciado. ¿En "
                           "que casos de la MISMA familia SI es distinto de cero, y cuanto?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}))

# ---------------------------------------------------------------- 3 · el informe
h_inf = sha(INFORME)
N3 = ("RosettaQ__REPORT__RQ-REPORT-AIRBUS-001__%s__"
      "airbus-fase-1-informe-final.json" % STAMP)
docs.append((N3, {"meta": {
    "file_name": N3, "file_id": "RQ-REPORT-AIRBUS-001", "type": "REPORT", "is_demo": False,
    "scope_note": "Entregable de Fase 1 del track Airbus. Ninguna cifra tecleada: todas se "
                  "derivan de los artefactos al generarlo, y el generador ABORTA si "
                  "encuentra una escrita a mano.",
    "texto_fuente": {"archivo": "AIRBUS-INFORME-FINAL.md", "sha256": "sha256:" + h_inf,
                     "publicado_como": "data/2026/08/AIRBUS-INFORME-FINAL@%s.md" % h_inf[:8]},
    **COMUN}, "w6": {
    "que": {
        "corridas_que_lo_alimentan": ["RQ-EXP-AIRBUS-EJE-001", "RQ-EXP-AIRBUS-NOLIN-001"],
        "guardias_del_generador": {
            "cifras_tecleadas": "aborta si alguna cifra del informe esta escrita a mano, "
                "tanto en las tuplas de formato como DENTRO del texto. Excepciones "
                "declaradas y solo dos: un anio y una referencia de seccion no son "
                "mediciones. Probado por mutacion, con casos de grito y de silencio.",
            "coherencia_entre_secciones": "aborta si el conteo del titular y el de la tabla "
                "del eje no coinciden. Nacio de un defecto real: el titular decia que K=1 "
                "resolvio 3 de 8 y la tabla ponia «out of reach» en las ocho filas.",
            "campo_ausente": "una ausencia es un fallo, no un hueco silencioso.",
        },
        "nueve_defectos_corregidos_antes_de_sellar": "el informe llego a esta sesion con "
            "cuatro defectos y salieron nueve. Entre ellos: dos cifras TECLEADAS en el "
            "titular de un documento que promete que ninguna lo esta; el titular "
            "atribuyendo el tiempo de un brazo al error de otro; un factor de tiempo "
            "publicado como [measured] que se mueve 74 % entre corridas; «el brazo cuantico "
            "no puede entrar», cierto para K=2 y falso para K=1; y la tabla contradiciendo "
            "al titular. Ninguno tocaba el hallazgo central.",
        "etiquetas": "cada afirmacion lleva [measured], [by construction] o [from the "
            "literature]. Las dos de tiempo van acotadas: [measured on one machine; not "
            "comparable across computers], porque ni los tiempos ni sus razones reproducen "
            "— un cociente SUMA el ruido de sus dos terminos.",
    },
    "como": {"generador": {"archivo": "build_airbus_informe.py",
                           "sha256": "sha256:" + sha(os.path.join(AQUI, "build_airbus_informe.py"))},
             "codigo": bloque_codigo()},
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "Mac local"},
    "porque": {"para_que": "entregable de Fase 1 para Airbus."},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "revision": "sesion de coordinacion, leido entero antes de aprobar",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}))

# ---------------------------------------------------------------- sellar y publicar
_yo = os.path.basename(__file__); _mi = sha(__file__)
copias = [(p, os.path.join(EV, "code", "%s@%s%s" % (os.path.basename(p)[:-3], sha(p)[:8],
                                                    os.path.splitext(p)[1]))) for p in CODIGO]
copias += [(BARRIDO, os.path.join(EV, "code", "barrido_airbus@%s.json" % sha(BARRIDO)[:8])),
           (NOLIN, os.path.join(EV, "code", "nolinealidad_donde_vive@%s.json" % sha(NOLIN)[:8])),
           (REPRO, os.path.join(EV, "code", "reproducibilidad_barrido@%s.json" % sha(REPRO)[:8])),
           (INFORME, os.path.join(EV, "data", "2026", "08", "AIRBUS-INFORME-FINAL@%s.md" % h_inf[:8])),
           (__file__, os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8])))]
extra = tuple(p for p, _ in copias)
salidas = []
for nombre, doc in docs:
    exigir_procedencia(doc, extra=extra)
    rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
    assert rs.verify(doc)
    sub = "reports" if doc["meta"]["type"] == "REPORT" else "runs"
    dst = os.path.join(EV, sub, "2026", "08", nombre)
    assert not os.path.exists(dst), dst
    salidas.append((dst, doc))
for _, d_ in copias:
    assert not os.path.exists(d_), "ya existe: %s" % d_
for dst, doc in salidas:
    json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
    assert rs.verify(json.load(open(dst)))
for s_, d_ in copias:
    shutil.copy2(s_, d_); assert sha(s_) == sha(d_)
print("SELLADOS %d:" % len(salidas))
for dst, doc in salidas:
    print("  %-28s %s" % (doc["meta"]["file_id"], doc["meta"]["content_hash"]))
print("PUBLICADOS %d archivos de procedencia:" % len(copias))
for _, d_ in copias: print("   ", os.path.relpath(d_, EV))
