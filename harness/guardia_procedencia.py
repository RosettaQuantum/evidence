#!/usr/bin/env python3
"""Se niega a SELLAR un documento que cite por sha256 un archivo no publicado.

POR QUE EXISTE
--------------
Habia tres capas contra la procedencia perdida —el historial de evidence-staging, el
notario que no ancla con referencias sin resolver, y el CI que audita los 109 sellos— y
todas actuan DESPUES de que el sello existe. Por esa ventana entraron las 8 perdidas
declaradas: el sellador citaba un archivo que solo vivia en el disco de quien sellaba, el
sello nacia bien formado, y para cuando el notario lo frenaba los bytes ya habian mutado.

Esta es la capa que previene en vez de atrapar, y va del lado del que sella.

UNA SOLA DEFINICION
-------------------
La resolucion NO se reescribe aqui: se importa de `scripts/check_provenance.py`, que ya
conoce las dos formas de referencia del archivo (bloque con nombre+sha, y claves hermanas
sufijadas) y los dos registros de excepcion (PROCEDENCIA-PERDIDA y
PROCEDENCIA-EN-FUENTE-DE-TERCEROS). Una lista que vive en dos lugares ya divergio.

USO
---
    from guardia_procedencia import exigir_procedencia
    exigir_procedencia(doc)      # antes de rs.seal(...)
    rs.seal(doc, ...)

Para el caso legitimo en que un sello cita algo cuya publicacion es imposible, se declara
en el registro correspondiente ANTES de sellar — que es justamente el acto que la
declaracion documenta.
"""
import hashlib, importlib.util, os, re, sys

EV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ProcedenciaSinPublicar(Exception):
    pass


def _auditor():
    """El modulo del auditor, importado sin ejecutar su cuerpo de linea de comandos."""
    ruta = os.path.join(EV, "scripts", "check_provenance.py")
    fuente = open(ruta).read()
    # el archivo audita al importarse; se corta en la primera linea de ejecucion
    corte = fuente.index("\npub = publicados()")
    spec = importlib.util.spec_from_loader("check_provenance_lib", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__["__file__"] = ruta
    exec(compile(fuente[:corte], ruta, "exec"), mod.__dict__)
    return mod


def _declarados():
    """Los sha256 que ya tienen excepcion declarada: perdidos o verificables en tercero."""
    out = set()
    for nombre in ("PROCEDENCIA-PERDIDA.md", "PROCEDENCIA-EN-FUENTE-DE-TERCEROS.md"):
        p = os.path.join(EV, nombre)
        if os.path.exists(p):
            out |= {h for h in re.findall(r"sha256:([0-9a-f]{8,})", open(p).read())}
    return out


def exigir_procedencia(doc, extra=()):
    """Aborta si alguna referencia del documento no resuelve a un archivo publicado.

    `extra`: rutas que se van a publicar en el mismo acto y aun no estan en el arbol
    (la capa 1: el sellador que se copia a code/ junto con su sello).
    """
    aud = _auditor()
    # `publicados()` arma su mapa con glob("**/*") RELATIVO AL DIRECTORIO ACTUAL. El auditor
    # se escribio para correrse desde evidence/, donde eso es correcto; los selladores viven
    # en evidence-staging/ y ahi escanea el arbol equivocado. No se noto nunca porque hasta
    # hoy todo sellador PUBLICABA en el mismo acto lo que citaba, y esos archivos entran por
    # `extra` sin pasar por el glob. El primer sello que cita algo YA publicado —una errata—
    # destapa la dependencia: da «no esta publicado» sobre archivos que si lo estan.
    # Se fija el directorio en vez de confiar en desde donde llamen.
    _antes = os.getcwd()
    try:
        os.chdir(EV)
        pub = aud.publicados()
    finally:
        os.chdir(_antes)
    for r in extra:
        if os.path.isfile(r):
            pub.setdefault(hashlib.sha256(open(r, "rb").read()).hexdigest(), r)
    declarados = _declarados()

    faltan = []
    for nombre, h in aud.referencias(doc):
        if h in pub:
            continue
        if any(d.startswith(h[:12]) or h.startswith(d[:12]) for d in declarados):
            continue
        faltan.append((nombre, h))

    if faltan:
        det = "\n".join("    %-40s %s…" % (n, h[:16]) for n, h in faltan)
        raise ProcedenciaSinPublicar(
            "ABORTA: este sello citaria %d archivo(s) que NO estan publicados:\n%s\n"
            "  Publicalos versionados por hash (code/nombre@hash8.ext) ANTES de sellar,\n"
            "  o declara la excepcion en PROCEDENCIA-PERDIDA.md /\n"
            "  PROCEDENCIA-EN-FUENTE-DE-TERCEROS.md. Un sello que promete «baja el\n"
            "  archivo y comprueba el hash» sobre algo que nadie puede bajar es la\n"
            "  ventana por la que entraron las 8 perdidas declaradas."
            % (len(faltan), det))
    return len(aud.referencias(doc))
