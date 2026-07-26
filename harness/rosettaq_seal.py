"""
RosettaQ — libreria unica de sellado.  Esquema: rosettaq-archive/v2

POR QUE EXISTE ESTE ARCHIVO
---------------------------
Hasta hoy el sellado se hacia inline, dentro de cada harness. Eso produjo dos
convenciones distintas bajo la misma etiqueta `v1` y un archivo (EXP-0007-001)
sellado sobre una serializacion irrecuperable. La regla ahora es:

    todo sello pasa por seal() de esta libreria, y esta libreria se archiva
    junto al run. Sellar inline esta prohibido.

CONVENCION v2
-------------
    content_hash = "sha256:" + sha256(
        json.dumps({"meta": meta_reducido, **cuerpo},
                   sort_keys=True, ensure_ascii=False)      # separadores por defecto
    )

donde:
    meta_reducido = meta SIN las claves  {"content_hash", "schema"}
    cuerpo        = todas las claves de nivel superior SALVO {"meta", "storage"}

Las cuatro exclusiones, cada una con su razon:

  meta.content_hash  autorreferencia: no puede estar dentro de lo que resume.
  meta.schema        es el PUNTERO a la convencion de hash, no contenido medido.
                     Es la unica diferencia real con v1 y la razon del bump
                     (ver abajo).
  storage            describe DONDE vive la copia, no QUE dice. Un archivo
                     espejado en un cuarto sitio no cambia lo que afirma.
  (nada mas)         todo lo demas —incluido seal_correction— entra al hash.

POR QUE v2 EXCLUYE `schema` (el punto entero del bump)
------------------------------------------------------
En v1 el campo `schema` vive dentro de `meta`, y `meta` entra al payload
hasheado. Consecuencia: **cambiarle la etiqueta de convencion a un archivo le
cambia el hash y le rompe el ancla OTS.** Es un lazo cerrado: el campo que
declara como se hasheo el archivo no se puede corregir nunca sin destruir la
prueba. Por eso los 43 archivos ya publicados no se pueden "reetiquetar" para
desambiguarlos: quedan como estan, y la ambiguedad se resuelve hacia adelante
(v2) mas un manifiesto publicado que dice cual convencion uso cada uno.

En v2 la etiqueta queda FUERA del payload. El sello sigue atado a todo el
contenido; solo el puntero de convencion es corregible. Esto no debilita nada:
la convencion es auto-evidente —solo una reproduce el hash almacenado— asi que
una etiqueta equivocada la detecta igual el verificador, que prueba todas las
convenciones conocidas. La etiqueta es una pista, no la prueba.

COMPATIBILIDAD
--------------
v2 NO se aplica retroactivamente. Los archivos ya anclados conservan su
convencion y su hash: son hechos publicos y re-sellarlos rompería anclas reales.
`tools/verify_seals.py` acepta las tres (v2, v1-canonica, v1-legada) y declara
cual uso cada archivo.

USO
---
    import rosettaq_seal as rs
    doc = rs.seal(doc, harness=("allo_multi.py", "1.2.0", "<sha256 del harness>"))
    assert rs.verify(doc)
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib

SCHEMA = "rosettaq-archive/v2"
LIB_NAME = "rosettaq_seal.py"
LIB_VERSION = "2.0.0"

EXCLUDED_META = ("content_hash", "schema")
EXCLUDED_TOP = ("meta", "storage")


# ---------------------------------------------------------------- hashing ---
def canonical_payload(doc: dict) -> str:
    """La cadena exacta sobre la que se calcula el sello v2."""
    meta = {k: v for k, v in doc["meta"].items() if k not in EXCLUDED_META}
    body = {k: v for k, v in doc.items() if k not in EXCLUDED_TOP}
    return json.dumps({"meta": meta, **body}, sort_keys=True, ensure_ascii=False)


def content_hash(doc: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical_payload(doc).encode("utf-8")).hexdigest()


def verify(doc: dict) -> bool:
    return doc.get("meta", {}).get("content_hash") == content_hash(doc)


def lib_fingerprint() -> str:
    """sha256 de ESTA libreria, para que el sello diga con que codigo se hizo."""
    raw = pathlib.Path(__file__).read_bytes()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def file_fingerprint(path) -> str:
    raw = pathlib.Path(path).read_bytes()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


# ----------------------------------------------------------------- sealing ---
def seal(doc: dict, harness: tuple | None = None, sealed_at: str | None = None,
         correction: dict | None = None, allow_reseal: bool = False) -> dict:
    """
    Sella `doc` in-place bajo rosettaq-archive/v2 y devuelve el mismo dict.

    harness     (nombre, version, sha256) del harness que produjo el contenido.
    sealed_at   ISO-8601 UTC; si no se pasa, se toma la hora actual.
    correction  bloque meta.seal_correction para un re-sellado (obligatorio si
                el documento ya traia content_hash).
    """
    if "meta" not in doc:
        raise ValueError("el documento no tiene bloque meta")

    previous = doc["meta"].get("content_hash")
    if previous and not (correction or allow_reseal):
        raise ValueError(
            "el documento ya esta sellado. Un re-sellado exige un bloque "
            "`correction` que registre el hash previo y la razon."
        )

    meta = doc["meta"]
    meta["schema"] = SCHEMA
    meta["sealed_at"] = sealed_at or _dt.datetime.now(_dt.timezone.utc).isoformat()
    meta["sealed_by"] = {
        "lib": LIB_NAME,
        "lib_version": LIB_VERSION,
        "lib_sha256": lib_fingerprint(),
        "harness": harness[0] if harness else None,
        "harness_version": harness[1] if harness else None,
        "harness_sha256": harness[2] if harness else None,
        "convention": "v2: sha256(json.dumps({meta sin content_hash/schema, cuerpo sin storage}, "
                      "sort_keys=True, ensure_ascii=False))",
    }
    if correction:
        meta["seal_correction"] = correction

    # el hash va SIEMPRE ultimo, calculado sobre todo lo anterior
    meta.pop("content_hash", None)
    doc["meta"] = meta
    meta["content_hash"] = content_hash(doc)
    return doc


# ------------------------------------------------------------------- CLI -----
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(f"{LIB_NAME} {LIB_VERSION}  schema={SCHEMA}")
        print(f"lib_sha256={lib_fingerprint()}")
        sys.exit(0)
    bad = 0
    for p in sys.argv[1:]:
        d = json.load(open(p))
        good = verify(d)
        bad += 0 if good else 1
        print(f"{'VALID(v2)' if good else 'INVALID  '} {d['meta'].get('file_id','?'):<16} "
              f"{content_hash(d)}")
    sys.exit(1 if bad else 0)
