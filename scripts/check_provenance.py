#!/usr/bin/env python3
"""Audita la cadena de procedencia: cada sha256 que un sello declara, ¿esta publicado?

Desde la convencion v2, un archivo sellado no solo dice que midio: dice con que datos y
con que codigo, cada uno por sha256, y esos hashes entran al sello. Eso solo vale algo
si el archivo referenciado esta publicado y su hash calza — si no, un juez que siga la
cadena llega a un 404 o a un archivo distinto, y la promesa "baja el script y re-corre"
queda vacia.

Nada verificaba eso de punta a punta. Este script si:
  python3 scripts/check_provenance.py          # resumen
  python3 scripts/check_provenance.py -v       # ademas lista lo resuelto

No bloquea el anclaje a proposito: un sello valido con un archivo de apoyo pendiente es
publicable siempre que la falta se declare. Lo que no se tolera es que pase inadvertida.
"""
import glob, hashlib, json, os, re, sys

VERBOSE = "-v" in sys.argv
CLAVES_NOMBRE = ("name", "file", "path", "script", "archivo", "nombre")


def publicados():
    """sha256 -> ruta, de todo lo que vive en el repo."""
    fuera = (".git", "node_modules")
    out = {}
    for f in glob.glob("**/*", recursive=True):
        if os.path.isfile(f) and not any(f.startswith(x) for x in fuera):
            try:
                out.setdefault(hashlib.sha256(open(f, "rb").read()).hexdigest(), f)
            except OSError:
                pass
    return out


def referencias(doc):
    """(nombre, sha256) de cada bloque de procedencia, a cualquier profundidad.

    Dos formas conviven en el archivo y las dos cuentan:

      A) un bloque con su nombre y su hash:   {"file": "x.py", "sha256": "..."}
      B) claves hermanas sufijadas:           {"script": "x.py", "script_sha256": "..."}

    La forma B aparecio con RQ-POC-QPU-001 y esta funcion no la veia. El efecto fue
    peor que no auditarla: el resumen decia "43 declaradas, 41 resueltas" con las dos
    referencias nuevas invisibles, o sea daba por auditado lo que nunca miro. Un
    auditor ciego a un campo nuevo no avisa menos — miente mas.
    """
    out = []

    def rec(o):
        if isinstance(o, dict):
            # forma A
            nombre = next((o[k] for k in CLAVES_NOMBRE if o.get(k)), None)
            sha = o.get("sha256")
            if nombre and sha:
                out.append((str(nombre), str(sha).replace("sha256:", "")))
            # forma B: cualquier <algo>_sha256 cuyo <algo> (o <algo>_file) sea el nombre
            for k, v in o.items():
                if not k.endswith("_sha256") or not v:
                    continue
                base = k[: -len("_sha256")]
                # El valor puede ser un hash suelto o un mapa {archivo: hash} — en
                # PR-ITER2-001 es lo segundo, y tratarlo como cadena convertia todo el
                # diccionario en un unico "archivo" inexistente: seis referencias reales
                # se contaban como una falsa.
                if isinstance(v, dict):
                    for nom, h in v.items():
                        if isinstance(h, str):
                            out.append((str(nom), h.replace("sha256:", "")))
                    continue
                ref = next((c for c in (o.get(base), o.get(base + "_file"),
                                        o.get(base + "_name")) if isinstance(c, str)), base)
                out.append((ref, str(v).replace("sha256:", "")))
            for v in o.values():
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)

    rec(doc)
    return out


pub = publicados()
total, faltan, ok = 0, {}, []
# EL ALCANCE SALE DE LA DEFINICION UNICA, no de una lista escrita aqui. La version
# anterior recorria solo runs/, prereg/ y verdicts/ — 95 de 108 sellos — y en la zona
# ciega (reports, recipes, manifests, predictions) habia 8 referencias sin resolver que
# nunca reporto. Decia «0 pendientes» y era verdad sobre lo que miraba, no sobre el
# archivo: la §5 bis literal, alcance menor que el declarado y en verde. Lo encontro el
# laboratorio el 19-ago midiendo el denominador. Una lista que vive en dos lugares ya
# divergio (§5 bis regla 3): esta se importa de donde el notario toma la suya.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notarize_globs import ARCHIVE_GLOBS

_sellos = sorted(set(f for g in ARCHIVE_GLOBS for f in glob.glob(g, recursive=True)
                     if not f.endswith(".ots")))
print(f"sellos auditados: {len(_sellos)} (alcance = ARCHIVE_GLOBS, la misma del notario)")
for p in _sellos:
    try:
        doc = json.load(open(p))
    except Exception:
        continue
    if "meta" not in doc:          # payload crudo, no es un sello
        continue
    fid = doc["meta"].get("file_id", os.path.basename(p))
    for nombre, sha in referencias(doc):
        total += 1
        if sha in pub:
            ok.append((fid, nombre, pub[sha]))
        else:
            faltan.setdefault((nombre, sha), set()).add(fid)

# Un hueco IMPOSIBLE contado junto a los pendientes hace que el numero mienta en la
# direccion comoda: parece que queda trabajo por hacer cuando en realidad no lo hay, y
# el pendiente real se esconde detras del arrastrado. PROCEDENCIA-PERDIDA.md declara
# cuales no se van a poder publicar nunca, con la busqueda que lo determino; aqui se
# cuentan aparte para que "sin publicar" vuelva a significar "pendiente de publicar".
PERDIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "PROCEDENCIA-PERDIDA.md")
declarados_perdidos = set()
if os.path.exists(PERDIDA):
    declarados_perdidos = {m.lower() for m in
                           re.findall(r'sha256:([0-9a-f]{8,})', open(PERDIDA).read())}

# Tercera categoria (20-ago, diseno de Norte + Main, la ejerce el lab como tercero):
# VERIFICABLE-EN-FUENTE-DE-TERCEROS — no republicable por licencia, pero el tercero lo
# sirve desde su fuente oficial. La diferencia con una perdida es COMPROBABLE, no
# declarada: cada entrada exige `fuente-oficial:` con URL http(s) y `verificacion:`.
# Una entrada sin esos campos hace fallar al auditor ENTERO (falla cerrado): sin fuente
# publica, es una perdida con mejor nombre y va al otro archivo.
TERCEROS = os.path.join(os.path.dirname(PERDIDA), "PROCEDENCIA-EN-FUENTE-DE-TERCEROS.md")
verificables_terceros = set()
if os.path.exists(TERCEROS):
    cuerpo = open(TERCEROS).read()
    # cada entrada arranca en "## " y debe traer sus tres campos
    entradas = re.split(r"\n## ", cuerpo)[1:]
    for e in entradas:
        sha = re.search(r"sha256:([0-9a-f]{16,64})", e)
        url = re.search(r"fuente-oficial\**:?\**\s*(https?://\S+)", e)
        ver = re.search(r"verificacion\**:", e)
        if not (sha and url and ver):
            print("ERROR: entrada malformada en PROCEDENCIA-EN-FUENTE-DE-TERCEROS.md — "
                  "faltan campos obligatorios (sha256 / fuente-oficial con URL / "
                  "verificacion) en: %s" % e.split("\n")[0][:70])
            sys.exit(1)
        verificables_terceros.add(sha.group(1).lower())

perdidas = {k: v for k, v in faltan.items()
            if any(k[1].split(":")[-1].lower().startswith(h) for h in declarados_perdidos)}
faltan = {k: v for k, v in faltan.items() if k not in perdidas}
terceros = {k: v for k, v in faltan.items()
            if any(k[1].split(":")[-1].lower().startswith(h) or h.startswith(k[1].split(":")[-1].lower())
                   for h in verificables_terceros)}
faltan = {k: v for k, v in faltan.items() if k not in terceros}

print(f"referencias de procedencia declaradas: {total}")
print(f"resueltas contra archivos publicados:  "
      f"{total - sum(len(v) for v in faltan.values()) - sum(len(v) for v in perdidas.values())}")
print(f"SIN publicar (pendientes):             {len(faltan)}")
print(f"declaradas PERDIDAS (no recuperables): {len(perdidas)}"
      f"{'' if not perdidas else '  <- ver PROCEDENCIA-PERDIDA.md'}")
print(f"verificables en fuente de terceros:    {len(terceros)}"
      f"{'' if not terceros else '  <- ver PROCEDENCIA-EN-FUENTE-DE-TERCEROS.md'}")
for (nombre, sha), ids in sorted(terceros.items()):
    print(f"   tercero  {nombre[:32]:<34} {sha[:16]}...  lo declara {', '.join(sorted(ids))}")
for (nombre, sha), ids in sorted(perdidas.items()):
    print(f"   perdida  {nombre[:32]:<34} {sha[:16]}...  la declaran {', '.join(sorted(ids))}")
if VERBOSE:
    for fid, nombre, ruta in ok:
        print(f"   ok  {fid:<14} {nombre[:30]:<32} -> {ruta}")
if faltan:
    print("\nCada una de estas rompe la promesa de 'baja el archivo y comprueba el hash':")
    for (nombre, sha), ids in sorted(faltan.items()):
        print(f"   {nombre[:36]:<38} {sha[:16]}...  lo declara {', '.join(sorted(ids))}")
    print("\nSe resuelven publicando la version EXACTA con nombre versionado por hash")
    print("(p.ej. sigo_features@0460d1f6.py), nunca sobreescribiendo la otra: cada sello")
    print("tiene que resolver a su propio archivo.")
sys.exit(0)
