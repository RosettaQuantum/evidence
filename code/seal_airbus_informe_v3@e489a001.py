#!/usr/bin/env python3
"""Sella la v2 del informe de Airbus. La v1 queda intacta y anclada.

POR QUE HAY UNA v2
------------------
La v1 (RQ-REPORT-AIRBUS-001, sha c35ecd83) afirma en su §7, con etiqueta [measured]:
«The sweep artifacts are not sealed yet». Era CIERTO al generarla y dejo de serlo veinte
minutos despues, cuando se sellaron las corridas en el mismo acto. Nada estaba mal
medido: **el acto de archivar cambio el hecho descrito.**

No es una errata —la v1 no era falsa cuando se sello— es una version nueva que supersede.
La v1 no se toca: publicado es publicado.

EL ARREGLO NO ES EDITAR LA FRASE
--------------------------------
El generador ahora DERIVA el estado del sello en las dos direcciones: si hay sellos, los
declara con su id, su content_hash y si estan anclados; si no, dice que faltan. Probado
por mutacion en ambos sentidos.

Y la v2 es ESTABLE BAJO SU PROPIO SELLADO: solo describe los sellos de tipo RUN, que
sellar este informe no cambia. Un documento que describiera el conteo total volveria a
quedar obsoleto en el acto de sellarse — que es la paradoja que costo la v1.

TAMBIEN CORRIGE el §8: citaba un solo hash por artefacto. Un jurado que re-corra obtiene
otro archivo por el reloj y concluye que encontro un error nuestro. Ahora van los dos,
cada uno con lo que sirve.

Costo US$0.
"""
import hashlib, json, os, shutil, sys, glob
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
INFORME = os.path.join(AQUI, "AIRBUS-INFORME-FINAL.md")
GEN = os.path.join(AQUI, "build_airbus_informe.py")
# La version que supersede se ELIGE derivandola: el REPORT que nadie supersede todavia.
# Nombrarla a mano seria teclear un identificador que el archivo ya sabe.
_reports = [json.load(open(p_)) for p_ in
            glob.glob(os.path.join(EV, "reports", "2026", "08", "*RQ-REPORT-AIRBUS-*.json"))]
_sup = {d_["meta"].get("supersede", {}).get("file_id") for d_ in _reports}
_vig = [d_ for d_ in _reports if d_["meta"]["file_id"] not in _sup]
if len(_vig) != 1:
    raise SystemExit("ABORTA: esperaba 1 informe vigente y hay %d: %s"
                     % (len(_vig), [d_["meta"]["file_id"] for d_ in _vig]))
v1 = _vig[0]; assert rs.verify(v1)

# --------------------------------------------------------------- GUARDIA
h_inf = sha(INFORME)
texto = open(INFORME, encoding="utf-8").read()
if "are not sealed yet" in texto:
    raise SystemExit("ABORTA: el informe sigue diciendo que los artefactos no estan "
                     "sellados. La v2 existe justamente para no repetir eso.")
if "**The sweep artifacts are sealed**" not in texto:
    raise SystemExit("ABORTA: el informe no declara el estado del sello. El §7 tiene que "
                     "decir lo que el archivo dice, en la direccion que sea.")
if "content hash" not in texto:
    raise SystemExit("ABORTA: el §8 no explica los dos hashes — el jurado que re-corra "
                     "creeria que encontro un error nuestro.")
import re as _re
if _re.search(r"(one|two|three|four|five|\d+)\s+orders?\s+of\s+magnitude", texto, _re.I):
    raise SystemExit("ABORTA: quedo una «N orders of magnitude» escrita a mano. Esa forma "
                     "invita a redondear hacia arriba y ya lo hizo tres veces.")
if "are anchored in Bitcoin" in texto:
    raise SystemExit("ABORTA: el informe CUENTA anclas. Un conteo caduca en cuanto el "
                     "notario ancla la siguiente, y ademas confunde recibo con bloque.")
if "A receipt is not yet a Bitcoin block" not in texto:
    raise SystemExit("ABORTA: el informe no distingue recibo de confirmacion en bloque")
if "What your benchmark can detect" not in texto:
    raise SystemExit("ABORTA: falta el §6, que es el titular de esta version")
corridas = []
for sub in ("runs",):
    for p_ in glob.glob(os.path.join(EV, sub, "**", "*.json"), recursive=True):
        if "AIRBUS" in os.path.basename(p_).upper():
            d_ = json.load(open(p_))
            corridas.append((d_["meta"]["file_id"], d_["meta"]["content_hash"],
                             os.path.exists(p_ + ".ots")))
for fid, ch, _ in corridas:
    if fid not in texto or ch[:21] not in texto:
        raise SystemExit("ABORTA: el informe no cita %s con su content_hash" % fid)
if h_inf == sha(os.path.join(EV, "data", "2026", "08",
                             "AIRBUS-INFORME-FINAL@%s.md" % v1["meta"]["texto_fuente"]["sha256"][7:15])):
    raise SystemExit("ABORTA: la v2 es identica a la v1; no hay nada que sellar")

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
NOMBRE = ("RosettaQ__REPORT__RQ-REPORT-AIRBUS-003__%s__"
          "airbus-fase-1-informe-final-v3.json" % STAMP)
doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-REPORT-AIRBUS-003", "type": "REPORT",
    "is_demo": False,
    "scope_note": "Version 3 del entregable de Fase 1 del track Airbus. SUPERSEDE a "
                  "RQ-REPORT-AIRBUS-001, que queda intacto y anclado — no era falso "
                  "cuando se sello.",
    "supersede": {
        "file_id": v1["meta"]["file_id"], "content_hash": v1["meta"]["content_hash"],
        "por_que": "la v2 contaba anclas —«N of M are anchored in Bitcoin»— sobre RECIBOS, no sobre bloques confirmados, y ademas un conteo caduca en cuanto el notario ancla la siguiente. Esta version describe el mecanismo y le da al lector el comando, asi que no caduca. Y suma el §6, la medicion del umbral de deteccion. Antecedente: la v1 afirmaba en su §7, con etiqueta [measured], que «the sweep "
                   "artifacts are not sealed yet». Era CIERTO al generarla y dejo de "
                   "serlo veinte minutos despues, cuando se sellaron las corridas. El "
                   "acto de archivar cambio el hecho descrito.",
        "regla": "la v1 no se reescribe ni se re-sella. Un jurado que la lea encontrara "
                 "una afirmacion que era verdadera en su fecha.",
    },
    "prereg": v1["meta"]["prereg"],
    "texto_fuente": {"archivo": "AIRBUS-INFORME-FINAL.md", "sha256": "sha256:" + h_inf,
                     "publicado_como": "data/2026/08/AIRBUS-INFORME-FINAL@%s.md" % h_inf[:8]},
}, "w6": {
    "que": {
        "que_cambia_respecto_de_la_v1": {
            "1_el_estado_del_sello_se_deriva": "el §7 ya no solo sabe decir «no estan "
                "sellados»: mira el archivo y declara los sellos con su id, su "
                "content_hash y si estan anclados. Probado por mutacion en las DOS "
                "direcciones — simulando cero sellos vuelve a decir que faltan.",
            "2_el_§8_cita_los_dos_hashes": "antes citaba solo el del archivo. Un jurado "
                "que re-corra obtiene otro archivo por el reloj y concluye que encontro "
                "un error nuestro. Ahora van los dos, cada uno con lo que sirve: el del "
                "archivo para comprobar que son nuestros bytes exactos, el del contenido "
                "para comprobar que la ciencia reproduce.",
        },
        "estable_bajo_su_propio_sellado": "la v2 describe SOLO los sellos de tipo RUN, que "
            "sellar este informe no cambia. Un documento que describiera el conteo total "
            "volveria a quedar obsoleto en el acto de sellarse. Esa es la leccion de la "
            "v1 y esta puesta en el diseno, no en una nota.",
        "corridas_declaradas": [{"file_id": f, "content_hash": c, "anclado": a}
                                for f, c, a in sorted(corridas)],
        "lo_que_NO_cambia": "ninguna cifra ni ningun hallazgo. El termino no lineal sigue "
            "anulandose en 2.35e-16 y la regla se cumple en las 18 filas.",
    },
    "como": {"generador": {"archivo": "build_airbus_informe.py", "sha256": "sha256:" + sha(GEN),
                           "publicado_como": "code/build_airbus_informe@%s.py" % sha(GEN)[:8]},
             "guardias": "el generador aborta si encuentra una cifra tecleada (en tuplas o "
                         "en prosa) y si el conteo del titular no coincide con el de la "
                         "tabla del eje. Este sellador aborta si el informe volviera a "
                         "decir que los artefactos no estan sellados."},
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "Mac local"},
    "porque": {"question": "¿que dice el informe cuando el archivo ya contiene sus "
                           "propias corridas selladas?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lo_encontro": "la sesion de coordinacion, leyendo el informe entero antes "
                             "de empaquetarlo — y el laboratorio en paralelo, al comprobar "
                             "que el informe no reproducia desde su generador sellado.",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario."},
}}
_yo = os.path.basename(__file__); _mi = sha(__file__)
copias = [(INFORME, os.path.join(EV, "data", "2026", "08", "AIRBUS-INFORME-FINAL@%s.md" % h_inf[:8])),
          (GEN, os.path.join(EV, "code", "build_airbus_informe@%s.py" % sha(GEN)[:8])),
          (__file__, os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8])))]
exigir_procedencia(doc, extra=tuple(p for p, _ in copias))
rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(EV, "reports", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
for _, d_ in copias: assert not os.path.exists(d_), d_
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
for s_, d_ in copias: shutil.copy2(s_, d_); assert sha(s_) == sha(d_)
assert rs.verify(json.load(open(dst)))
print("v3 SELLADA:", doc["meta"]["content_hash"])
print("supersede :", v1["meta"]["content_hash"][:24], "(intacta)")
for _, d_ in copias: print("  publicado:", os.path.relpath(d_, EV))
