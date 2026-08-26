"""¿De que habla este documento? — la guardia del SEGUNDO eje, compartida y sobre el PDF.

POR QUE EXISTE
--------------
El PDF `5_verificar.pdf` del paquete de Airbus salio con «Quantum-Enabled Grid Expansion
Planning» —el titulo del desafio de E.ON— impreso en su primera pagina, dos lineas debajo de
«Airbus». **Y se entrego asi.** Sobrevivio cuatro reconstrucciones.

No lo cazo ninguna guardia y no fue por descuido: **todas nuestras guardias leen el markdown y
el defecto vive en el PDF.** El titulo no esta en el texto fuente — lo pone el conversor como
valor por omision cuando el llamador no le pasa uno. Un chequeo sobre el .md mira un objeto
donde el defecto no puede aparecer.

De ahi la regla que este modulo encarna: **la compuerta va sobre el formato que viaja.**

POR QUE AQUI Y NO EN UN EMPAQUETADOR
------------------------------------
La version original de esta guardia vive dentro de `build_hsbc_paquete.py`. Funciona — y por
eso HSBC esta cubierto. Pero `build_airbus_paquete.py` no la tiene, y por eso Airbus se
entrego roto. **Una guardia dentro del empaquetador de un desafio protege a ese desafio y a
ninguno mas.**

PRECISION SOBRE COBERTURA (CLAUDE.md §2)
----------------------------------------
Se comprueba **la primera pagina**, que es donde vive el titulo, para los nombres de otros
desafios: mas adentro, un documento puede nombrar legitimamente a E.ON —el informe de Airbus
dice «Cleveland y E.ON salieron antes» en la seccion de equipo, y eso es correcto—. Un falso
positivo retendria trabajo bueno, que es peor que dejar pasar un caso.

El **titulo completo** de otro documento nuestro si se busca en todo el PDF: esa cadena no
tiene por que aparecer en ninguna parte.
"""
import re


def _nombra(t, texto):
    """Coincidencia por palabra: «E.ON» no debe casar dentro de «EONIA» ni «eon_harness»."""
    return bool(re.search(r"(?<![\w.])%s(?![\w])" % re.escape(t), texto))


def texto_de(ruta_pdf):
    """Devuelve (texto_pagina_1, texto_entero). Falla cerrado: sin lector, no se comprueba."""
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    pgs = PdfReader(ruta_pdf).pages
    p1 = pgs[0].extract_text() or ""
    entero = "".join((p.extract_text() or "") for p in pgs)
    return p1, entero


def revisar(ruta_pdf, track, otros_tracks, titulos_ajenos, andamiaje=True):
    """Devuelve la lista de defectos. NO aborta — el que llama decide. Lista vacia = limpio."""
    p1, entero = texto_de(ruta_pdf)
    llano = entero.replace("\n", " ")
    fallas = []

    if not _nombra(track, p1):
        fallas.append("la pagina 1 no nombra su propio track (%s). Un documento que no se "
                      "identifica es peor que uno mal identificado." % track)

    intrusos = [t for t in otros_tracks if _nombra(t, p1)]
    if intrusos:
        fallas.append("la pagina 1 del entregable de %s nombra otro desafio: %s. Asi salio "
                      "el PDF de Airbus con el titulo de E.ON." % (track, ", ".join(intrusos)))

    ajenos = [t for t in titulos_ajenos
              if t.replace(" ", "").lower() in llano.replace(" ", "").lower()]
    if ajenos:
        fallas.append("contiene el titulo completo de otro documento nuestro: %s"
                      % ", ".join(ajenos))

    if andamiaje:
        # Marcadores de proceso que jamas deben llegar al jurado. La linea «borrador para
        # aprobacion de Nicholas — NO publicado» llego impresa a la portada del PDF de HSBC.
        BLANDAS = [r"NOT\s+published", r"drafted\s+for", r"\bborrador\b",
                   r"NO\s+publicado", r"\blorem ipsum\b", r"\bplaceholder\b"]
        # SENSIBLES A MAYUSCULAS, y esto no es cosmetico: `\bTODO\b` con re.I casa con la
        # palabra española «todo» y hacia gritar a un documento correcto. Como marcador de
        # andamiaje estas siglas se escriben SIEMPRE en mayusculas, asi que exigirlas asi no
        # pierde ningun caso real y elimina el falso positivo. Lo cazo la prueba de mutacion
        # de este mismo modulo, en su primera corrida.
        DURAS = [r"\bTODO\b", r"\bFIXME\b", r"\bTBD\b", r"\bXXX\b"]
        vistos = sorted({m.group(0) for p in BLANDAS
                         for m in re.finditer(p, llano, re.I)}
                        | {m.group(0) for p in DURAS
                           for m in re.finditer(p, llano)})
        if vistos:
            fallas.append("contiene marcadores de andamiaje: %s" % ", ".join(vistos))

    return fallas


def exigir(ruta_pdf, track, otros_tracks, titulos_ajenos, andamiaje=True):
    """Comprueba y ABORTA si el documento habla de otra cosa. Para usar en un empaquetador."""
    fallas = revisar(ruta_pdf, track, otros_tracks, titulos_ajenos, andamiaje)
    if fallas:
        raise SystemExit("ABORTA: %s\n%s" % (ruta_pdf,
                         "\n".join("    - " + f for f in fallas)))
    print("  guardia de documento: %s nombra %s y ningun otro desafio"
          % (ruta_pdf.split("/")[-1], track))
    return True
