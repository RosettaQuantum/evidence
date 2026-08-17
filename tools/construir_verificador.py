#!/usr/bin/env python3
"""Genera `verificar.py`: el verificador de UN SOLO ARCHIVO que se le entrega a un tercero.

POR QUE SE GENERA Y NO SE ESCRIBE
---------------------------------
El verificador que publicamos necesita el canonizador JCS adentro —un comprador tiene que
poder copiar UN archivo y correrlo, sin instalar nada—. Pero si ese canonizador se copia a
mano, ya divergió: una lista que vive en dos lugares divergió el día que se copió
(CLAUDE.md Rosetta §5 bis regla 3). Y aquí la divergencia sería del peor tipo: dos
verificadores nuestros dando veredictos distintos sobre el mismo sello.

Así que se GENERA, pegando `harness/jcs.py` —la fuente única, la misma que usa el
verificador interno— dentro de una plantilla. Y el archivo generado declara el sha256 del
jcs.py del que salió, para que se pueda comprobar que no se tocó por el camino.

EL DEFECTO QUE ESTE ARCHIVO EXISTE PARA CERRAR
-----------------------------------------------
Cada respuesta de nuestra API dice «recomputa el sha256 según /api-docs». Medido el
2026-08-14, siguiendo esa instrucción al pie de la letra sobre un sello v3:

    declara:     sha256:4ffdfeb485ceb9b0bf90491...
    recomputado: sha256:a6ff6a5f5ff9904843be71b...
    CALZA: False

El sello es válido —nuestro verificador dice v3— y la instrucción es la que está mal: el
`content_hash` NO es el sha256 del archivo, es el sha256 de un payload canónico. Mientras
el sitio bloqueaba a Python nadie llegaba a descubrirlo. Ahora sí.

Uso:  python3 tools/construir_verificador.py
"""
import hashlib
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
JCS = os.path.join(RAIZ, "harness", "jcs.py")
SALIDA = os.path.join(AQUI, "verificar.py")

CABEZA = '''#!/usr/bin/env python3
"""Verifica un sello de Rosetta Quantum. Sin instalar nada: sólo la librería estándar.

    python3 verificar.py RQ-EXP-EON-C-K08-003      # lo baja de la API y lo verifica
    python3 verificar.py archivo.json              # verifica un archivo que ya tienes
    python3 verificar.py --todo                    # verifica TODO el archivo publicado

QUE COMPRUEBA, Y QUE NO
-----------------------
Comprueba que el contenido del sello produce exactamente el `content_hash` que declara.
Si alguien cambió un solo carácter del documento, el hash cambia y esto lo dice.

NO comprueba que el resultado sea cierto. Un sello válido significa «este documento es
idéntico al que se publicó y se ancló en esa fecha», no «esta medición es correcta».
Son dos cosas distintas y conviene no confundirlas.

EL HASH NO ES EL SHA256 DEL ARCHIVO
-----------------------------------
Es el sha256 de un PAYLOAD CANONICO: el documento sin los campos que no forman parte de
lo sellado (`meta.content_hash`, `meta.schema` y `storage`), serializado con una regla
fija. Recomputar el sha256 del archivo crudo da un valor distinto — correcto para el
archivo, equivocado para el sello.

Hay CUATRO convenciones en circulación. No es desorden: es historia declarada, y este
programa dice con cuál verificó cada archivo.

  v3           RFC 8785 (JCS). La única recomputable fuera de Python.
  v2           json.dumps(sort_keys=True, ensure_ascii=False)
  v1-canonica  como v2 pero `schema` entra al payload
  v1-legada    content_hash se anula en vez de quitarse; separadores compactos;
               ensure_ascii por defecto (escapa los no-ASCII)

Los archivos viejos NO se re-sellan: sus hashes están anclados en Bitcoin y son hechos
públicos que terceros ya citaron. Re-sellarlos invalidaría anclas reales. La ambigüedad
se resuelve hacia adelante.
"""
import hashlib
import json
import math
import sys
import urllib.request

API = "https://rosettaquantum.com/v1"

'''

COLA = '''

# ─────────────────────────────────────────────────── las cuatro convenciones

def _payload(d):
    meta = {k: v for k, v in d["meta"].items() if k not in ("content_hash", "schema")}
    body = {k: v for k, v in d.items() if k not in ("meta", "storage")}
    return {"meta": meta, **body}


def _v3(d):
    try:
        return "sha256:" + hashlib.sha256(canonico(_payload(d)).encode("utf-8")).hexdigest()
    except NoCanonizable:
        return None


def _v2(d):
    return "sha256:" + hashlib.sha256(json.dumps(
        _payload(d), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _v1_canonica(d):
    meta = {k: v for k, v in d["meta"].items() if k != "content_hash"}
    body = {k: v for k, v in d.items() if k not in ("meta", "storage")}
    return "sha256:" + hashlib.sha256(json.dumps(
        {"meta": meta, **body}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _v1_legada(d):
    meta = dict(d["meta"]); meta["content_hash"] = None
    return "sha256:" + hashlib.sha256(json.dumps(
        {"meta": meta, "w6": d.get("w6")}, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()


CONVENCIONES = [("v3", _v3), ("v2", _v2), ("v1-canonica", _v1_canonica),
                ("v1-legada", _v1_legada)]


def verificar(doc):
    """Devuelve (convencion, hash) si alguna reproduce el declarado; si no, (None, None)."""
    declarado = doc.get("meta", {}).get("content_hash")
    for nombre, fn in CONVENCIONES:
        try:
            h = fn(doc)
        except Exception:
            continue
        if h and h == declarado:
            return nombre, h
    return None, None


def _traer(url):
    # Sin cabeceras especiales: exactamente lo que haria un tercero con Python pelado.
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def _bytes_originales(item):
    """Baja el sello del ESPEJO, no de la API. Y la razon es medible.

    Medido el 2026-08-14 sobre las 72 corridas publicadas:
        por el espejo GitHub : 72 de 72 verifican
        por la API           : 17 de 72

    La API entrega el documento re-serializado, y eso destruye los literales exactos de
    los que dependen los hashes de las convenciones viejas: Python escribe un float `6.0`
    donde otro serializador escribe `6`, y el sha256 cambia. El sello sigue siendo bueno;
    lo que se pierde es la posibilidad de recomputarlo.

    v3 es inmune porque JCS normaliza los numeros — que es exactamente para lo que se
    creo v3. Los 55 archivos anteriores NO se re-sellan: sus hashes estan anclados en
    Bitcoin y son hechos publicos que terceros ya citaron.

    Asi que la verificacion se hace SIEMPRE contra los bytes del espejo. La API sirve
    para descubrir que existe; el espejo, para comprobarlo.
    """
    for clave in ("github_raw", "codeberg_raw"):
        url = item.get(clave)
        if not url:
            continue
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode("utf-8")), clave
        except Exception:
            continue
    return None, None


def _desenvolver(d):
    # La API entrega el sello dentro de `archivo_sellado`; un archivo en disco lo trae
    # plano. Es el mismo documento con un sobre distinto.
    if "meta" not in d and isinstance(d.get("archivo_sellado"), dict):
        return d["archivo_sellado"]
    return d


def _una(doc, etiqueta):
    conv, h = verificar(doc)
    decl = doc.get("meta", {}).get("content_hash", "(sin declarar)")
    if conv:
        print("  VALIDO   %-34s  %s  %s" % (etiqueta, conv, decl[:26] + "..."))
        return True
    print("  NO CALZA %-34s  declara %s" % (etiqueta, decl[:26] + "..."))
    print("           ninguna de las cuatro convenciones lo reproduce.")
    return False


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--todo"]
    if "--todo" in sys.argv:
        items = _traer("%s/runs?limit=1000" % API)["items"]
        print("verificando %d corrida(s) contra los bytes del espejo\\n" % len(items))
        ok = sin_espejo = 0
        for it in items:
            doc, de_donde = _bytes_originales(it)
            if doc is None:
                print("  SIN ESPEJO %-32s no se pudo bajar el original" % it["id"])
                sin_espejo += 1
                continue
            ok += _una(doc, it["id"])
        print("\\n%d de %d verifican · %d sin espejo alcanzable" % (ok, len(items), sin_espejo))
        sys.exit(0 if ok == len(items) else 1)

    if not args:
        print(__doc__); sys.exit(2)

    bien = True
    for a in args:
        doc = _desenvolver(json.load(open(a)) if a.endswith(".json") and "/" in a or
                           a.endswith(".json") and __import__("os").path.exists(a)
                           else _traer("%s/archive/%s" % (API, a)))
        bien &= _una(doc, a)
    sys.exit(0 if bien else 1)
'''

if __name__ == "__main__":
    jcs_src = open(JCS, encoding="utf-8").read()
    jcs_hash = hashlib.sha256(jcs_src.encode("utf-8")).hexdigest()

    # Se quita la cabecera de módulo y los imports de jcs.py: ya van en la plantilla.
    cuerpo = []
    for linea in jcs_src.splitlines():
        if linea.startswith("import ") or linea.startswith("from "):
            continue
        cuerpo.append(linea)
    # Quitar el docstring inicial del módulo (entre las dos primeras comillas triples).
    texto = "\n".join(cuerpo)
    if texto.lstrip().startswith('"""'):
        i = texto.index('"""') + 3
        texto = texto[texto.index('"""', i) + 3:]

    marca = ('\n# ── canonizador JCS (RFC 8785) ──────────────────────────────────────────\n'
             '# Pegado desde evidence/harness/jcs.py, que es la fuente unica y la misma que\n'
             '# usa nuestro verificador interno. sha256 de ese archivo:\n'
             '#   %s\n'
             '# Si esa fuente cambia, este archivo se regenera con\n'
             '# tools/construir_verificador.py. No se edita a mano.\n' % jcs_hash)

    open(SALIDA, "w", encoding="utf-8").write(CABEZA + marca + texto + COLA)
    print("escrito %s" % os.path.relpath(SALIDA, RAIZ))
    print("  jcs.py sha256: %s" % jcs_hash[:32])
    print("  %d lineas · sin dependencias" % len(open(SALIDA).read().splitlines()))
