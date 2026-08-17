#!/usr/bin/env python3
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


# ── canonizador JCS (RFC 8785) ──────────────────────────────────────────
# Pegado desde evidence/harness/jcs.py, que es la fuente unica y la misma que
# usa nuestro verificador interno. sha256 de ese archivo:
#   9c12e33a6a5d16a11d75cb9e4fa971be20dfee20cd2615ee7354530b05f9a0bb
# Si esa fuente cambia, este archivo se regenera con
# tools/construir_verificador.py. No se edita a mano.


MAX_SEGURO = 2 ** 53          # mas alla, un double ya no representa cada entero


class NoCanonizable(Exception):
    """El valor no se puede escribir de forma que otro lenguaje lo reproduzca."""


# --------------------------------------------------------------------- numeros
def numero(x):
    """`Number::toString` de ECMAScript (ES6 7.1.12.1), que es lo que exige RFC 8785.

    Se apoya en que `repr` de Python ya da los digitos mas cortos que redondean de
    vuelta al mismo double; lo que cambia es como se FORMATEAN esos digitos.
    """
    if isinstance(x, bool):                     # bool es subclase de int: se ataja antes
        raise NoCanonizable("un booleano no es un numero")
    if isinstance(x, int):
        if abs(x) > MAX_SEGURO:
            raise NoCanonizable(
                "el entero %d supera 2^53: un double no lo representa exacto y otro "
                "lenguaje lo redondearia. No se sella lo que el tercero no puede "
                "reproducir." % x)
        x = float(x)
    if not isinstance(x, float):
        raise NoCanonizable("no es un numero: %r" % (x,))
    if math.isnan(x) or math.isinf(x):
        raise NoCanonizable("NaN e infinito no existen en JSON")
    if x == 0:
        return "0"                              # tambien -0.0, como String(-0) en ES6

    signo = "-" if x < 0 else ""
    r = repr(abs(x))

    # separar mantisa y exponente del repr
    if "e" in r:
        mant, _, exp = r.partition("e")
        exp = int(exp)
    else:
        mant, exp = r, 0

    entero, _, frac = mant.partition(".")
    if entero != "0":
        n = len(entero)
        digitos = entero + frac
    else:
        ceros = len(frac) - len(frac.lstrip("0"))
        n = -ceros
        digitos = frac[ceros:]
    digitos = digitos.rstrip("0") or "0"
    n += exp                                    # valor = 0.digitos x 10^n

    k = len(digitos)
    if k <= n <= 21:
        return signo + digitos + "0" * (n - k)
    if 0 < n <= 21:
        return signo + digitos[:n] + "." + digitos[n:]
    if -6 < n <= 0:
        return signo + "0." + "0" * (-n) + digitos
    e = n - 1
    cabeza = digitos if k == 1 else digitos[0] + "." + digitos[1:]
    return signo + cabeza + "e" + ("+" if e >= 0 else "-") + str(abs(e))


# --------------------------------------------------------------------- cadenas
_CORTOS = {0x08: "\\b", 0x09: "\\t", 0x0A: "\\n", 0x0C: "\\f", 0x0D: "\\r"}


def cadena(s):
    """Escapes de `JSON.stringify`: los minimos, y el resto literal en UTF-8."""
    out = ['"']
    for ch in s:
        c = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif c in _CORTOS:
            out.append(_CORTOS[c])
        elif c < 0x20:
            out.append("\\u%04x" % c)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _clave_utf16(s):
    """Orden por unidades de codigo UTF-16, que es lo que manda el RFC.

    Comparar los bytes de UTF-16 big-endian equivale a comparar las unidades de codigo:
    es lo que hace que un emoji (par suplente, primera unidad D83D) ordene ANTES de
    U+FB33, al reves de lo que da el orden por code point de Python.
    """
    return s.encode("utf-16-be")


# ------------------------------------------------------------------ serializar
def canonico(v):
    """El texto canonico RFC 8785 de un valor JSON."""
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, str):
        return cadena(v)
    if isinstance(v, (int, float)):
        return numero(v)
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(canonico(x) for x in v) + "]"
    if isinstance(v, dict):
        for k in v:
            if not isinstance(k, str):
                raise NoCanonizable("clave que no es cadena: %r" % (k,))
        pares = sorted(v.items(), key=lambda kv: _clave_utf16(kv[0]))
        return "{" + ",".join(cadena(k) + ":" + canonico(x) for k, x in pares) + "}"
    raise NoCanonizable("tipo sin forma canonica: %s" % type(v).__name__)


def bytes_canonicos(v):
    """El texto canonico en UTF-8 — lo que se hashea."""
    return canonico(v).encode("utf-8")

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


def _por_id(ident):
    """Baja los BYTES SELLADOS de un id, no el JSON re-serializado.

    Defecto real, encontrado por la sesion web el 2026-08-14: esta funcion pedia
    `/v1/archive/<id>`, que entrega el documento re-parseado, y contestaba NO CALZA sobre
    sellos v1 y v2 perfectamente validos. El modo --todo ya bajaba del espejo; el modo de
    un solo id no. **La misma herramienta daba dos veredictos distintos segun como se la
    invocara**, que es exactamente lo que un verificador no puede hacer.

    Ahora usa `/v1/archive/<id>/raw`, que sirve los bytes originales.
    """
    try:
        return _traer("%s/archive/%s/raw" % (API, ident))
    except Exception:
        # Si /raw no esta, se cae al espejo antes que al endpoint que re-serializa.
        item = None
        for x in _traer("%s/runs?limit=1000" % API)["items"]:
            if x["id"] == ident:
                item = x
                break
        if item:
            doc, _ = _bytes_originales(item)
            if doc:
                return doc
        raise SystemExit("no pude obtener los bytes sellados de %s. NO verifico contra el "
                         "endpoint que re-serializa: daria un NO CALZA falso." % ident)


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__); sys.exit(0)
    args = [a for a in sys.argv[1:] if a != "--todo"]
    if "--todo" in sys.argv:
        items = _traer("%s/runs?limit=1000" % API)["items"]
        print("verificando %d corrida(s) contra los bytes del espejo\n" % len(items))
        ok = sin_espejo = 0
        for it in items:
            doc, de_donde = _bytes_originales(it)
            if doc is None:
                print("  SIN ESPEJO %-32s no se pudo bajar el original" % it["id"])
                sin_espejo += 1
                continue
            ok += _una(doc, it["id"])
        print("\n%d de %d verifican · %d sin espejo alcanzable" % (ok, len(items), sin_espejo))
        sys.exit(0 if ok == len(items) else 1)

    if not args:
        print(__doc__); sys.exit(2)

    bien = True
    for a in args:
        import os as _os
        doc = (_desenvolver(json.load(open(a))) if a.endswith(".json") and _os.path.exists(a)
               else _desenvolver(_por_id(a)))
        bien &= _una(doc, a)
    sys.exit(0 if bien else 1)
