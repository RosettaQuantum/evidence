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
import glob, hashlib, json, os, sys

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
    """(nombre, sha256) de cada bloque de procedencia, a cualquier profundidad."""
    out = []

    def rec(o):
        if isinstance(o, dict):
            nombre = next((o[k] for k in CLAVES_NOMBRE if o.get(k)), None)
            sha = o.get("sha256")
            if nombre and sha:
                out.append((str(nombre), str(sha).replace("sha256:", "")))
            for v in o.values():
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)

    rec(doc)
    return out


pub = publicados()
total, faltan, ok = 0, {}, []
for p in sorted(glob.glob("runs/**/*.json", recursive=True)
                + glob.glob("prereg/**/*.json", recursive=True)
                + glob.glob("verdicts/**/*.json", recursive=True)):
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

print(f"referencias de procedencia declaradas: {total}")
print(f"resueltas contra archivos publicados:  {total - sum(len(v) for v in faltan.values())}")
print(f"SIN publicar:                          {len(faltan)}")
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
