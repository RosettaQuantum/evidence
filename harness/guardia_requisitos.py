"""¿Contestamos lo que nos preguntaron? — la guardia del TERCER eje, compartida.

POR QUE EXISTE Y POR QUE ESTA AQUI Y NO EN LA CARPETA DE UN DESAFIO
-------------------------------------------------------------------
Nuestras guardias contestaban dos preguntas: «¿de donde salio este numero?» (procedencia) y
«¿de que habla este documento?» (el titulo de E.ON pegado en el informe de Airbus). Faltaba la
tercera: **¿el documento contesta lo que el enunciado pide?** Se escribio para HSBC despues de
armar el entregable tres veces sin compararlo con el pedido — faltaban la estrategia de
codificacion, el diseño del circuito y el manejo del desbalance de clases, y ninguna guardia de
procedencia podia verlo.

Vivia en `evidence-staging/requisitos_hsbc.py`: **local a un desafio y fuera del archivo**. O sea
que Volkswagen habria partido de cero justo en el eje que nos costo tres pasadas. Por eso el motor
esta aca y **la lista de cada desafio vive en su propia ficha** `desafios/<track>.toml`.

QUE COMPRUEBA Y QUE NO
----------------------
Comprueba **cobertura**: que el documento diga algo sobre cada requisito. NO comprueba que lo diga
bien — eso lo lee una persona. Una lista que se declarara juez de la calidad seria peor que
ninguna, porque daria verde sobre texto vacio.

NIVELES, tomados del verbo del propio enunciado — no se inventan, y la cita textual viaja al lado
para que cualquiera lo verifique:
  «must» / «expected»       -> OBLIGATORIO: si falta, ABORTA.
  «should» / «are asked»    -> ESPERADO:    si falta, ABORTA.
  «encouraged» / «valued»   -> SUGERIDO:    si falta, se reporta y no aborta.
  «good-to-have»            -> OPCIONAL:    idem.

DOS TRAMPAS QUE ESTE MODULO YA PAGO. No las quites sin leer por que estan:

1. LIGADURAS. Un PDF escribe «stratiﬁed» con UN caracter. Buscar «stratif» sobre el texto crudo da
   CERO, y el falso negativo cae justo en las palabras largas y tecnicas —«stratified»,
   «classification», «efficiency»— que son las que importan. `normalizar()` las deshace.

2. LA SECCION DE MAPEO SE EXCLUYE ANTES DE COMPROBAR. Esa seccion CITA cada requisito para que el
   lector no tenga que buscarlo. Si la lista mirara ahi, «circuit depth» o «class imbalance»
   quedarian cubiertos **por la cita del requisito, no por la respuesta**. Una lista que se
   satisface repitiendo la pregunta es peor que no tener lista.
"""
import re
import unicodedata

try:
    import tomllib as _toml
    _MODO_BIN = True
except ImportError:                      # Python < 3.11
    import tomli as _toml
    _MODO_BIN = True

DUROS = {"OBLIGATORIO", "ESPERADO"}
NIVELES = {"OBLIGATORIO", "ESPERADO", "SUGERIDO", "OPCIONAL"}

LIGADURAS = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff",
             "ﬃ": "ffi", "ﬄ": "ffl"}


def normalizar(t):
    """Deshace ligaduras y normaliza. Ver trampa 1 en el encabezado."""
    for k, v in LIGADURAS.items():
        t = t.replace(k, v)
    return unicodedata.normalize("NFKC", t)


def cargar(ruta_toml):
    """Lee la lista de requisitos de la ficha de un desafio.

    Devuelve (requisitos, seccion_mapeo). Cada requisito es la misma tupla de siempre:
    (id, seccion, nivel, cita, patron) — para que el resto del codigo no cambie.

    ABORTA si la ficha no trae requisitos: una ficha sin lista y una lista vacia se ven
    igual desde afuera, y la segunda daria verde sobre cualquier documento.
    """
    with open(ruta_toml, "rb") as f:
        doc = _toml.load(f)
    bloque = doc.get("requisitos")
    if not bloque:
        raise SystemExit("ABORTA: %s no declara [requisitos]. Una ficha sin lista da verde "
                         "sobre cualquier documento, que es peor que no tener guardia."
                         % ruta_toml)
    items = bloque.get("item") or []
    if not items:
        raise SystemExit("ABORTA: %s declara [requisitos] pero sin ningun [[requisitos.item]]."
                         % ruta_toml)
    reqs = []
    for i, it in enumerate(items):
        faltan = [k for k in ("id", "seccion", "nivel", "cita", "patron") if k not in it]
        if faltan:
            raise SystemExit("ABORTA: el requisito #%d de %s no trae %s"
                             % (i, ruta_toml, ", ".join(faltan)))
        if it["nivel"] not in NIVELES:
            raise SystemExit("ABORTA: nivel «%s» desconocido en %s (%s). El nivel sale del "
                             "verbo del enunciado, no se inventa."
                             % (it["nivel"], it["id"], ruta_toml))
        try:
            re.compile(it["patron"])
        except re.error as e:
            raise SystemExit("ABORTA: el patron de %s en %s no compila: %s"
                             % (it["id"], ruta_toml, e))
        reqs.append((it["id"], it["seccion"], it["nivel"], it["cita"], it["patron"]))
    return reqs, bloque.get("seccion_mapeo", ""), set(bloque.get("no_cumplidos", []))


def sin_mapeo(texto, seccion_mapeo):
    """Recorta la seccion que cita los requisitos. Ver trampa 2 en el encabezado."""
    if not seccion_mapeo:
        return texto
    m = re.search(r"^(#{1,3}) .*(?:%s).*$" % seccion_mapeo, texto, re.M)
    if not m:
        return texto
    # Se corta hasta el siguiente encabezado de nivel IGUAL O SUPERIOR, no hasta el
    # siguiente encabezado cualquiera: la seccion de mapeo tiene subsecciones «###», y
    # detenerse en la primera deja DENTRO las citas de los requisitos. Eso infla la
    # cobertura exactamente como describe la trampa 2 — pasa de 19 a 23 sobre el mismo
    # documento sin que cambie una palabra. Comprobado al generalizar este modulo.
    nivel = len(m.group(1))
    sig = re.search(r"^#{1,%d} " % nivel, texto[m.end():], re.M)
    fin = m.end() + (sig.start() if sig else len(texto[m.end():]))
    return texto[:m.start()] + texto[fin:]


def comprobar(texto, reqs, seccion_mapeo="", no_cumplidos=()):
    """Devuelve (cubiertos, faltantes_duros, faltantes_blandos, declarados_no_cumplidos).

    POR QUE EXISTE `no_cumplidos` — medido el 27-ago-2026 sobre el track VW.
    Un documento honesto declara en su cuerpo los requisitos que NO cumple, con su razon. Al
    hacerlo escribe las mismas palabras que el patron busca —«public code repository», «task
    accuracy on held-out split»— y el guardia los cuenta como CUBIERTOS. O sea: **declarar un
    fallo con honestidad pone el guardia en verde**, que es exactamente al reves.

    La causa es que un patron de presencia no puede leer una negacion: «tenemos repositorio» y
    «el repositorio no existe todavia» contienen la misma palabra. No se arregla con una
    expresion mas lista — se arregla declarandolo en la ficha, como se declara una anomalia.

    Los declarados salen del numerador y viajan en su propia lista. La cobertura deja de
    inflarse y el lector ve las tres cantidades por separado.
    """
    texto = normalizar(sin_mapeo(texto, seccion_mapeo))
    cub, duros, blandos, declarados = [], [], [], []
    for r in reqs:
        if r[0] in no_cumplidos:
            declarados.append(r)
            continue
        # INSENSIBLE A MAYUSCULAS, y la razon esta medida: el patron sale de una CITA del
        # enunciado («an ablation isolating...», «theoretical motivation») y un documento
        # escribe esas mismas frases como TITULO, capitalizadas. R6 y R7 daban rojo sobre
        # un documento que SI traia las dos secciones. Es un falso positivo, y un falso
        # positivo retiene trabajo bueno — peor que dejar pasar un caso (CLAUDE.md §2).
        # Ojo: esto vale para ESTE guardia, cuyos patrones son frases del enunciado. NO
        # vale para el guardia de documento, donde «TODO» en mayusculas es un marcador y
        # «todo» en minusculas es una palabra corriente del español.
        if re.search(r[4], texto, re.IGNORECASE):
            cub.append(r[0])
        elif r[2] in DUROS:
            duros.append(r)
        else:
            blandos.append(r)
    return cub, duros, blandos, declarados


def exigir(texto, reqs, etiqueta, seccion_mapeo=""):
    """Comprueba y ABORTA si falta algo que el enunciado pide con «must» o «should»."""
    cub, duros, blandos = comprobar(texto, reqs, seccion_mapeo)
    print("  requisitos del enunciado cubiertos en %s: %d de %d"
          % (etiqueta, len(cub), len(reqs)))
    if blandos:
        print("    sin cubrir (no bloquean): %s"
              % ", ".join("%s §%s" % (r[0], r[1]) for r in blandos))
    if duros:
        det = "\n".join("    %s (§%s, %s): «%s»" % (r[0], r[1], r[2], r[3]) for r in duros)
        raise SystemExit("ABORTA: %s no cubre %d requisito(s) que el enunciado pide con «must» "
                         "o «should»:\n%s\n"
                         "  Esta lista comprueba COBERTURA, no calidad: que falte es un hecho; "
                         "que este no significa que este bien dicho." % (etiqueta, len(duros), det))
    return cub


def auditar_contra_el_enunciado(ruta_txt, reqs):
    """¿La lista representa lo que el enunciado pide, o lo que su autor recordo?

    Extrae del enunciado TODA unidad con verbo modal y comprueba que su terminologia aparezca
    en algun requisito. Una lista curada leyendo hereda los puntos ciegos de quien la leyo;
    esta funcion es lo que los destapa. Asi aparecio R26 en HSBC.

    Devuelve (cuantas_unidades_modales, huerfanas).
    """
    t = normalizar(open(ruta_txt, encoding="utf-8").read())
    buf, out = "", []
    for l in t.split("\n"):
        if not l.strip():
            if buf:
                out.append(buf); buf = ""
            continue
        if re.match(r"^\s*([●○•§▪]|\d+\.\d|\d+\.\s|o\s)", l):
            if buf:
                out.append(buf)
            buf = l.strip()
        else:
            buf = (buf + " " + l.strip()).strip()
    if buf:
        out.append(buf)
    MODAL = (r"\b(must|should|are asked|is expected|are expected|required|encouraged|"
             r"is valued|are valued)\b")
    unidades = [re.sub(r"\s+", " ", u).strip(" ●○•§▪")
                for u in out if re.search(MODAL, u, re.I)]
    unidades = [u for u in unidades if 30 < len(u) < 400]
    mias = " ".join(r[3].lower() for r in reqs)
    STOP = {"participants", "challenge", "should", "their", "these", "which", "using",
            "under", "other", "there", "where", "include"}
    huerfanas = []
    for u in unidades:
        ws = [w for w in re.findall(r"[a-z]{5,}", u.lower()) if w not in STOP]
        if ws and sum(1 for w in ws if w in mias) / len(ws) < 0.30:
            huerfanas.append(u)
    return len(unidades), huerfanas
