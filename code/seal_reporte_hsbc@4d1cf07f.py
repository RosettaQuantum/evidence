#!/usr/bin/env python3
"""Sella el ENTREGABLE del track HSBC en sus dos idiomas. Publica los .md por hash.

POR QUE LOS DOS EN UN SOLO SELLO
--------------------------------
Son el mismo entregable. Sellarlos aparte permitiria que uno avance y el otro no, que es
exactamente la deriva que la guardia de divergencia del generador ingles existe para
impedir. Un sello, dos archivos, un hash cada uno.

LA GUARDIA QUE IMPORTA
----------------------
Antes de sellar se RE-EJECUTAN los dos generadores en un directorio aparte y se compara el
resultado con el .md del disco. Si difieren, alguien edito el .md a mano — y un documento
editado a mano ya no es «toda cifra se lee de un artefacto sellado», que es lo que el propio
documento promete en su encabezado. Aborta.

Ademas: todo sello que los documentos citan por file_id tiene que existir y verificar.

Costo US$0.
"""
import hashlib, json, os, shutil, subprocess, sys, glob, re, tempfile
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

ES = os.path.join(AQUI, "ENTREGABLE-HSBC.md")
EN = os.path.join(AQUI, "ENTREGABLE-HSBC-EN.md")
GEN_ES = os.path.join(AQUI, "build_hsbc_entregable.py")
GEN_EN = os.path.join(AQUI, "build_hsbc_entregable_en.py")
FUENTES = os.path.join(AQUI, "fuentes_hsbc.py")

# ---------------- GUARDIA: el .md tiene que ser lo que el generador produce
def regenera_igual(gen, md, nombre_salida):
    """Re-ejecuta el generador con la salida desviada y compara byte a byte."""
    with tempfile.TemporaryDirectory() as tmp:
        src = open(gen, encoding="utf-8").read()
        destino = os.path.join(tmp, "salida.md")
        mut = src.replace('"%s"' % nombre_salida, repr(destino), 1)
        if mut == src:
            raise SystemExit("ABORTA: no supe desviar la salida de %s" % os.path.basename(gen))
        cop = os.path.join(AQUI, "_regen_tmp.py")
        open(cop, "w", encoding="utf-8").write(mut)
        try:
            # EL CENSO SE FIJA AL COMMIT QUE EL DOCUMENTO DECLARA. Si no, la regeneracion
            # cuenta contra la punta de origin/main —que avanza cuando otra sesion sella— y
            # la guardia acusa de «editado a mano» un documento que solo es de hace un rato.
            env = dict(os.environ)
            # ANCLADO A LA FRASE DEL CENSO. La primera version buscaba «commit `X`» a secas
            # y agarraba el commit del PRE-REGISTRO, que aparece antes en el documento: la
            # regeneracion contaba el archivo de julio y acusaba de edicion a mano.
            mcom = re.search(r"(?:contados en el commit|at commit) `([0-9a-f]{7,40})`",
                             open(md, encoding="utf-8").read())
            if mcom:
                env["RQ_CENSO_COMMIT"] = mcom.group(1)
            r = subprocess.run([sys.executable, cop], cwd=AQUI, capture_output=True,
                               text=True, env=env)
            if r.returncode != 0:
                raise SystemExit("ABORTA: %s no corre: %s" % (os.path.basename(gen),
                                                              r.stderr.strip()[-300:]))
            if not os.path.exists(destino):
                raise SystemExit("ABORTA: %s no escribio la salida desviada" % os.path.basename(gen))
            a, b = open(destino, "rb").read(), open(md, "rb").read()
            if a != b:
                raise SystemExit("ABORTA: %s NO coincide con lo que su generador produce. "
                                 "Un .md editado a mano rompe la promesa del encabezado: "
                                 "«toda cifra se lee de un artefacto sellado, ninguna se "
                                 "tipea»." % os.path.basename(md))
        finally:
            if os.path.exists(cop): os.remove(cop)

regenera_igual(GEN_ES, ES, "ENTREGABLE-HSBC.md")
regenera_igual(GEN_EN, EN, "ENTREGABLE-HSBC-EN.md")

# ---------------- GUARDIA: cada sello citado existe y verifica
texto = open(ES, encoding="utf-8").read() + open(EN, encoding="utf-8").read()
ids = sorted(set(re.findall(r"RQ-[A-Z0-9-]+", texto)))
citados = {}
for i in ids:
    cand = [f for f in glob.glob(os.path.join(EV, "**", "*%s*.json" % i), recursive=True)
            if "/code/" not in f]
    cand = [f for f in cand if re.search(r"__%s__" % re.escape(i), os.path.basename(f))]
    if not cand:
        raise SystemExit("ABORTA: los documentos citan %s y no hay sello con ese id" % i)
    d = json.load(open(cand[0], encoding="utf-8"))
    if not rs.verify(d):
        raise SystemExit("ABORTA: el sello %s citado por los documentos no verifica" % i)
    citados[i] = {"content_hash": d["meta"]["content_hash"],
                  "anclado": os.path.exists(cand[0] + ".ots")}

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
# La version se DERIVA de cuantos sellos de este entregable ya existen: publicado es
# publicado, y un documento corregido es un sello nuevo, no una reescritura del anterior.
_previos = sorted(glob.glob(os.path.join(EV, "reports", "**", "*RQ-REPORT-HSBC-*.json"),
                            recursive=True))
VERSION = len(_previos) + 1
FILE_ID = "RQ-REPORT-HSBC-%03d" % VERSION
NOMBRE = ("RosettaQ__REPORT__%s__%s__entregable-track-hsbc-es-y-en.json" % (FILE_ID, STAMP))
doc = {"meta": {
    "file_name": NOMBRE, "file_id": FILE_ID, "type": "REPORT", "is_demo": False,
    "reemplaza_a": ([json.load(open(_previos[-1]))["meta"]["file_id"],
                     json.load(open(_previos[-1]))["meta"]["content_hash"]] if _previos else None),
    "por_que_una_version_nueva": ("el titulo del documento en ingles habia quedado en la "
        "version anterior del entregable —hablaba de «a fraud baseline» cuando el nucleo ya "
        "era el brazo cuantico— y la guardia de divergencia compara NUMEROS, no prosa, asi "
        "que no lo vio. El sello anterior no se reescribe." if _previos else None),
    "scope_note": "El entregable del track HSBC en sus dos idiomas. Ninguna cifra esta "
                  "tecleada: las dos redacciones leen los MISMOS artefactos sellados al "
                  "armarse, y el generador ingles aborta si aparece un numero que el "
                  "español no tiene.",
}, "w6": {
    "que": {
        "documentos": [
            {"idioma": "es", "archivo": os.path.basename(ES), "sha256": "sha256:" + sha(ES),
             "publicado_como": "data/2026/08/ENTREGABLE-HSBC@%s.md" % sha(ES)[:8]},
            {"idioma": "en", "archivo": os.path.basename(EN), "sha256": "sha256:" + sha(EN),
             "publicado_como": "data/2026/08/ENTREGABLE-HSBC-EN@%s.md" % sha(EN)[:8]},
        ],
        "sellos_que_citan": citados,
        "aprobacion": "el texto en español lo aprobo Nicholas antes de generar el ingles; "
                      "el ingles no es traduccion sino una redaccion paralela sobre los "
                      "mismos artefactos.",
        "cruce_ventaja_cuantica": 0,
    },
    "como": {
        "generadores": [
            {"archivo": os.path.basename(GEN_ES), "sha256": "sha256:" + sha(GEN_ES),
             "publicado_como": "code/build_hsbc_entregable@%s.py" % sha(GEN_ES)[:8]},
            {"archivo": os.path.basename(GEN_EN), "sha256": "sha256:" + sha(GEN_EN),
             "publicado_como": "code/build_hsbc_entregable_en@%s.py" % sha(GEN_EN)[:8]},
            {"archivo": os.path.basename(FUENTES), "sha256": "sha256:" + sha(FUENTES),
             "publicado_como": "code/fuentes_hsbc@%s.py" % sha(FUENTES)[:8],
             "por_que_separado": "las tres citas externas vivian duplicadas en los dos "
                 "generadores. Una cita que difiere entre los dos idiomas del mismo "
                 "entregable es un defecto que nadie ve hasta que un lector compara."},
        ],
        "guardias": "antes de sellar se re-ejecutan los dos generadores con la salida "
                    "desviada y se comparan byte a byte con los .md del disco: un archivo "
                    "editado a mano rompe la promesa de su propio encabezado. Ademas, todo "
                    "sello citado por file_id tiene que existir y verificar.",
    },
    "cuando": {"archived_at": ISO},
    "donde": {"compute": "Mac local (laboratorio).", "gasto_usd": 0.0},
    "porque": {"question": "¿que entregamos al track HSBC, y puede el lector comprobarlo "
                           "sin creernos nada?"},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "sellado por el laboratorio; anclaje del notario; el "
                  "texto publico lleva el OK de Nicholas."},
}}
_yo = os.path.basename(__file__); _mi = sha(__file__)
D8 = os.path.join(EV, "data", "2026", "08")
copias = [(ES, os.path.join(D8, "ENTREGABLE-HSBC@%s.md" % sha(ES)[:8])),
          (EN, os.path.join(D8, "ENTREGABLE-HSBC-EN@%s.md" % sha(EN)[:8])),
          (GEN_ES, os.path.join(EV, "code", "build_hsbc_entregable@%s.py" % sha(GEN_ES)[:8])),
          (GEN_EN, os.path.join(EV, "code", "build_hsbc_entregable_en@%s.py" % sha(GEN_EN)[:8])),
          (FUENTES, os.path.join(EV, "code", "fuentes_hsbc@%s.py" % sha(FUENTES)[:8])),
          (__file__, os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8])))]
exigir_procedencia(doc, extra=tuple(p for p, _ in copias))
rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(EV, "reports", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
# Una pieza que NO cambio entre versiones ya esta publicada bajo su propio hash: se
# reutiliza. Lo que no se permite nunca es que un nombre con hash apunte a otro contenido.
for s_, d_ in copias:
    if os.path.exists(d_) and sha(s_) != sha(d_):
        raise SystemExit("ABORTA: %s existe con OTRO contenido — un nombre con hash que "
                         "miente es peor que un archivo faltante." % os.path.basename(d_))
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
for s_, d_ in copias:
    if not os.path.exists(d_): shutil.copy2(s_, d_)
    assert sha(s_) == sha(d_)
assert rs.verify(json.load(open(dst)))
print("REPORTE SELLADO:", doc["meta"]["content_hash"])
print("  es: %s  en: %s" % (sha(ES)[:8], sha(EN)[:8]))
print("  sellos citados por los documentos: %d, todos verifican" % len(citados))
print("  sin ancla entre los citados:",
      [k for k, v in citados.items() if not v["anclado"]] or "ninguno")
for _, d_ in copias: print("  publicado:", os.path.relpath(d_, EV))
