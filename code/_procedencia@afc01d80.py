"""Cada artefacto declara el sha256 de TODOS los instrumentos que lo produjeron.

POR QUE EXISTE
--------------
El informe de Airbus afirmaba, con la etiqueta `[by construction]`, que «el
instrumento declara su propio sha256 dentro de cada artefacto que escribe». Medido:
no lo hacia. Los artefactos llevaban `producido_por` como NOMBRE pelado y el unico
hash era el del PDF del enunciado. Una afirmacion de verificabilidad que el lector
desmiente en un comando, con la herramienta que le dimos nosotros.

Un nombre no identifica codigo: `barrido_airbus.py` de hoy y el de la semana pasada
son el mismo nombre y distinto programa. Por eso va la cadena completa —el script de
entrada y sus dependencias— y no solo el que escribe el archivo.
"""
import hashlib, os

AQUI = os.path.dirname(os.path.abspath(__file__))
DEPENDENCIAS = ("airbus_harness.py", "airbus_carleman.py")


def _sha(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return "sha256:" + h.hexdigest()


def procedencia(archivo_principal):
    """{nombre: sha256} del script que escribe y de cada dependencia que use."""
    out = {os.path.basename(archivo_principal): _sha(archivo_principal)}
    for d in DEPENDENCIAS:
        p = os.path.join(AQUI, d)
        if os.path.isfile(p): out[d] = _sha(p)
    return out


# ---------------------------------------------------------------- contenido_sha256
# POR QUE NO BASTA CON EL HASH DEL ARCHIVO
# ----------------------------------------
# El artefacto le dice a un tercero "bajalo y recomputa el hash". Pero si re-corre, el
# hash cambia por el RELOJ, no por la ciencia — medido: dos corridas de
# nolinealidad_donde_vive.py difieren solo en `pared_total_s`. Una promesa que falla por
# diseno. Declararla no la arregla: la convierte en advertencia y el tercero sigue sin
# poder verificar nada.
#
# `contenido_sha256` se calcula sobre el contenido determinista, excluyendo lo que
# depende de la maquina y del momento. Ese hash SI reproduce, y es el que se cita.
#
# El caso del barrido obliga a una precision que no es obvia: ahi el tiempo de pared NO
# es un campo de reloj incidental, **es una de las dos mediciones del experimento**
# (error contra tiempo-a-solucion). Se excluye igual — porque un tercero en otra maquina
# no lo va a reproducir jamas — y por eso la exclusion se DECLARA en el artefacto en vez
# de esconderse: lo que reproduce exacto son los errores; los tiempos son mediciones de
# esta maquina y se comparan entre brazos, no entre computadores.
import re as _re

_EXCLUIR_CLAVE = ("pared_total_s", "pared_total_eje_s", "pared_total_script_s",
                  "tiempo_pared_s", "entorno", "contenido_sha256",
                  "campos_no_reproducibles")
# nombres de archivo con marca de tiempo: airbus_punto_Re10_N32_20260819T205544Z.json
_SELLO_TIEMPO = _re.compile(r"_\d{8}T\d{6}Z")


def _poda(o, ruta="", fuera=None):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if k in _EXCLUIR_CLAVE:
                fuera.append(ruta + "/" + k); continue
            out[k] = _poda(v, ruta + "/" + k, fuera)
        return out
    if isinstance(o, list):
        return [_poda(v, ruta + "[%d]" % i, fuera) for i, v in enumerate(o)]
    if isinstance(o, str) and _SELLO_TIEMPO.search(o):
        fuera.append(ruta + " (marca de tiempo en el nombre)")
        return _SELLO_TIEMPO.sub("_<marca-de-tiempo>", o)
    return o


def contenido(doc):
    """(sha256 del contenido determinista, lista de lo excluido REALMENTE encontrado)."""
    import json
    fuera = []
    podado = _poda(doc, "", fuera)
    txt = json.dumps(podado, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(txt.encode()).hexdigest(), sorted(set(fuera))
