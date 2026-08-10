"""JCS — serializacion canonica de JSON segun RFC 8785, en stdlib puro.

POR QUE EXISTE
--------------
El sello del archivo se calcula sobre un TEXTO. Hasta v2 ese texto lo producia
`json.dumps(..., sort_keys=True, ensure_ascii=False)`, que es una serializacion de
Python, no una canonica. Consecuencia medida el 2026-08-10: **64 de 69 archivos sellados
sólo se pueden recomputar en Python**, porque Python escribe un float `6.0` donde
JavaScript, Go y Rust escriben `6`. Un tercero que verifica en otro lenguaje obtiene un
hash distinto, en silencio, con la misma cara que tendria una manipulacion. Es el peor
fallo posible para un chequeo de integridad: **acusa a un archivo honesto**.

RFC 8785 (JSON Canonicalization Scheme) es el estandar que resuelve exactamente eso: fija
una unica forma de escribir cada valor JSON, para que el mismo dato de un mismo texto en
cualquier lenguaje.

SIN DEPENDENCIAS, A PROPOSITO
-----------------------------
`harness/rosettaq_seal.py` es stdlib puro y eso es una virtud del notario, no un
accidente: un archivo que existe para que otros puedan probar cosas no deberia depender
de que un paquete de terceros siga publicado dentro de diez anos. Asi que JCS va
implementado aca, y se valida contra los **vectores del propio RFC** (ver
`test_jcs.py`), no contra ejemplos inventados por quien lo escribio.

LAS TRES COSAS QUE JCS FIJA, Y POR QUE CADA UNA NOS IMPORTA
-----------------------------------------------------------
1. **Numeros**, con el algoritmo `Number::toString` de ECMAScript. Aca vive el `6.0`
   contra `6` que nos trajo hasta aca.
2. **Orden de claves por unidades UTF-16**, no por code point. Difieren fuera del BMP:
   un emoji (U+1F600, par suplente D83D DE00) ordena ANTES de U+FB33 en UTF-16 y DESPUES
   por code point. Todavia no nos mordio, y por eso mismo hay que probarlo.
3. **Sin espacios** y escapes minimos de cadena, como `JSON.stringify`.

LIMITE DECLARADO
----------------
JCS define el JSON sobre numeros IEEE 754 de doble precision. Un entero de Python mayor
que 2^53 no sobrevive a ese viaje: JavaScript lo redondearia y el hash no calzaria. En vez
de emitir algo que el otro lado no puede reproducir, **este modulo falla cerrado** y lo
dice. NaN e infinitos tampoco existen en JSON y tambien fallan cerrado.
"""
import math

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
