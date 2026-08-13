#!/usr/bin/env python3
"""El mapa de frontera: dónde lo cuántico se acerca y dónde se aleja, por clase y tamaño.

QUE ES Y POR QUE ES EL PRODUCTO
-------------------------------
Sesenta corridas selladas diciendo que el clasico gana son, hoy, sesenta archivos que
nadie va a leer. Puestas en un plano —**tamaño del problema contra brecha respecto del
mejor clasico**— son otra cosa: la unica respuesta que un decisor necesita antes de
gastar seis meses en un piloto. *«Para mi clase y mi tamaño, ¿hay algo o no hay nada?»*

Nadie mas puede construir este mapa, y no por la tecnologia: porque **nadie publica sus
negativos**. Cada «no» que agregamos lo hace mas filoso. Es el unico activo del proyecto
que compone con el tiempo.

LO QUE EL MAPA NO HACE
----------------------
No extrapola. Los puntos son los medidos; entre ellos hay hueco y el hueco se dibuja como
hueco. Una curva ajustada a cuatro puntos es un adorno que se lee como prediccion — ya nos
paso hoy: con dos puntos «la brecha bajaba», con cuatro no era monotona, y con el problema
creciendo de verdad resulto que sube. Lo que cambio no fue el ajuste: fue el dato.

EL EJE COMUN, Y SU LIMITE DECLARADO
-----------------------------------
X = variables binarias del problema de decision (= qubits en nuestro encoding).
Y = brecha porcentual del brazo cuantico respecto del OPTIMO EXACTO, cuando hay arbitro
    que lo pruebe; si no lo hay, el punto se marca como «sin arbitro» y no se dibuja como
    si lo tuviera.

Sirve para optimizacion combinatoria (E.ON, portafolio, ruteo). **No sirve para alosteria**,
cuya metrica es un percentil de ranking y no una brecha de optimalidad: mezclarlas daria un
plano cuyos ejes significan cosas distintas segun el punto. Esa clase se declara aparte.

Uso:
    python3 scripts/mapa_frontera.py                 # lee el archivo local
    python3 scripts/mapa_frontera.py --api           # lee la API publica, como un tercero
"""
import glob
import json
import os
import sys
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "mapa_frontera.json")
API = "https://rosettaquantum.com/v1"

# El muro, medido y no supuesto (2026-08-13): 22 variables es el ultimo tamaño que cabe
# en memoria Y termina en el reloj de CI. 26 entra en 1 GB de vector de estado y NO
# termina en 90 minutos — la corrida de case118 se cancelo por tiempo, no por memoria.
MURO_SIMULACION = 22
MURO_MEMORIA = 30          # ~16 GB de vector de estado; por encima, imposible en CPU

# UNA CLASE, UN NOMBRE. Los sellos de julio dicen «Grid optimization» y los de agosto
# traen la red en otra rama; leidos tal cual, el mismo problema —expansion de red
# electrica de E.ON— salia partido en dos clases de 9 y 8 puntos. Para un cliente eso
# es peor que un error de etiqueta: dos nubes chicas dicen «poco medido» donde una nube
# de 17 dice «esto lo tenemos recorrido».
#
# Se unifica SOLO lo que es el mismo problema. Portafolio y red no se mezclan aunque
# ambas sean optimizacion combinatoria: sus brechas viven en ordenes distintos y
# juntarlas produciria un promedio que no describe a ninguna.
SINONIMOS = {
    "optimizacion de red electrica": "Grid optimization",
    "optimización de red eléctrica": "Grid optimization",
    "grid expansion": "Grid optimization",
}


def _hondo(o, claves):
    """Busca una clave a cualquier profundidad. Devuelve el primer valor no nulo."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k in claves and v is not None:
                return v
            r = _hondo(v, claves)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = _hondo(v, claves)
            if r is not None:
                return r
    return None


def _esquema_v3(doc):
    """Los campos del sello nuevo, leidos por RUTA EXPLICITA. Nunca a ciegas.

    POR QUE POR RUTA Y NO CON _hondo(): en el sello v3 hay DOS campos llamados
    `gap_pct` —uno bajo `clasico_CP_SAT` y otro bajo `cuantico_QAOA`— y el del clasico
    aparece primero. Una busqueda a ciegas devuelve 0,0 y lo pinta como brecha cuantica:
    un empate falso, en el eje que es el producto entero. El valor existiria, seria
    correcto, y estaria respondiendo a otra pregunta (CLAUDE.md Rosetta §5 quater, la
    sexta forma).
    """
    q = ((doc.get("w6") or {}).get("que") or {})
    tam = ((q.get("el_tamano_del_problema") or {}).get("variables_binarias"))
    res = q.get("resultado") or {}
    cu = res.get("cuantico_QAOA") or {}
    cl = res.get("clasico_CP_SAT") or {}
    return {
        "variables": tam,
        "gq": cu.get("gap_pct"),
        "gc": cl.get("gap_pct"),
        "arbitro": ("CP-SAT %s" % cl["status"]) if cl.get("status") else None,
        "clase": (q.get("censo_de_la_red") or {}).get("grid"),
        "instancia": (q.get("artefacto") or {}).get("archivo"),
        # Lo que este esquema TODAVIA no registra, y el mapa no puede inventar: si el
        # optimizador agoto su presupuesto o lo corto el reloj. Sin eso, un punto alto
        # por falta de tiempo es indistinguible de un punto alto por el metodo.
        "pasos": ((cu.get("optimizador") or {}) or {}).get("pasos_dados"),
        "tope_pasos": ((cu.get("optimizador") or {}) or {}).get("pasos_de_presupuesto"),
    }


def _desenvolver(doc):
    """La API entrega el sello DENTRO de `archivo_sellado`; el archivo local lo entrega
    plano. Es el mismo documento con un sobre distinto.

    Sin esto, el modo --api descartaba las ocho corridas nuevas con «sin tamaño»: el
    lector buscaba `w6` en la raiz y ahi vive el sobre, no el sello. El mapa desde la
    API salia con 28 puntos y desde el archivo con 37, y **ninguna de las dos cifras
    avisaba de la otra** — que es exactamente lo que un tercero habria visto al
    reconstruirlo, concluyendo que el archivo es mas chico de lo que es.
    """
    if isinstance(doc, dict) and "w6" not in doc and isinstance(doc.get("archivo_sellado"), dict):
        return doc["archivo_sellado"]
    return doc


def extraer(doc, fid):
    """Un punto del mapa, o None con su razon. Nunca inventa el tamaño ni la brecha."""
    doc = _desenvolver(doc)
    clase = _hondo(doc, {"problem_class", "clase_de_problema"})
    inst = _hondo(doc, {"instance", "instancia"})
    gaps = _hondo(doc, {"quality_gaps_pct"})
    params = _hondo(doc, {"instance_params", "params"}) or {}

    # El sello v3 guarda tamaño y brechas en otra rama. Leerlo PRIMERO y por ruta.
    # Sin esto el mapa descartaba las ocho corridas selladas del 13-ago —incluido el
    # unico empate del archivo— con el motivo «sin tamaño: ningun campo declara cuantas
    # variables tenia». El campo estaba; el lector miraba donde ya no vive. Un descarte
    # con un motivo falso es peor que un error: se lee como si el dato no existiera.
    v3 = _esquema_v3(doc)

    # --- el tamaño, por orden de confianza: v3 > declarado > derivado > ausente
    tam, fuente_tam = None, None
    if v3["variables"]:
        tam, fuente_tam = int(v3["variables"]), "v3:el_tamano_del_problema.variables_binarias"
    if tam is None:
        for k in ("n_candidates", "n_assets", "n_variables", "n_qubits"):
            if isinstance(params, dict) and params.get(k):
                tam, fuente_tam = int(params[k]), "declarado:%s" % k
                break
    if tam is None:
        x = _hondo(doc, {"x"})                       # el vector solucion tiene una entrada por variable
        if isinstance(x, list) and x and all(isinstance(v, (int, float)) for v in x):
            tam, fuente_tam = len(x), "derivado:len(x)"

    # --- la brecha
    gq = gc = None
    if v3["gq"] is not None:
        gq, gc = v3["gq"], v3["gc"]
    if gq is None and isinstance(gaps, dict):
        gq, gc = gaps.get("quantum"), gaps.get("classical")
    if gq is None:
        gq = _hondo(doc, {"quantum_gap_pct"})
        gc = _hondo(doc, {"classical_gap_pct"})
    if clase is None and v3["clase"]:
        clase = "Grid optimization"
    if inst is None:
        inst = v3["instancia"]
    clase = SINONIMOS.get((clase or "").strip().lower(), clase)

    if tam is None:
        return None, "sin tamaño: ningun campo declara cuantas variables tenia"
    if gq is None:
        return None, "sin brecha cuantica medida"

    arbitro = (v3["arbitro"] or _hondo(doc, {"arbitro_efectivo", "arbitro"}) or
               ("optimo exacto declarado" if _hondo(doc, {"exact_optimum"}) is not None
                else None))

    return {
        "id": fid, "clase": clase or "sin declarar", "instancia": inst,
        "variables": tam, "fuente_del_tamaño": fuente_tam,
        "brecha_cuantica_pct": round(float(gq), 4),
        "brecha_clasica_pct": round(float(gc), 4) if gc is not None else None,
        "arbitro": arbitro,
        "cabe_en_simulacion": tam <= MURO_SIMULACION,
        # Si el sello lo declara, el punto viaja sabiendo si el optimizador agoto su
        # presupuesto. Si NO lo declara, viaja como None — que significa «no se sabe»,
        # no «no se trunco». Un None leido como False pintaria como medicion limpia un
        # punto que quizas se corto por reloj.
        "pasos_dados": v3["pasos"], "pasos_de_presupuesto": v3["tope_pasos"],
        "truncado": (None if v3["pasos"] is None or v3["tope_pasos"] is None
                     else v3["pasos"] < v3["tope_pasos"]),
    }, None


def desde_archivo():
    docs = []
    for p in glob.glob(os.path.join(RAIZ, "runs", "**", "*.json"), recursive=True):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if "meta" in d:
            docs.append((d, d["meta"].get("file_id", os.path.basename(p))))
    return docs


# EL AGENTE DE USUARIO, Y POR QUE ESTA LINEA VALE UN COMENTARIO LARGO
# --------------------------------------------------------------------
# Medido el 2026-08-13: rosettaquantum.com devuelve 403 al agente por defecto de
# urllib (`Python-urllib/3.x`) y 200 a cualquier otro, incluido `curl`. O sea que
# **este mismo modo `--api` nunca funciono contra produccion** — y es el modo que
# existe precisamente para demostrar que un tercero puede reconstruir el mapa desde
# la API publica, sin nuestro repositorio.
#
# Poner una cabecera aca lo desbloquea para NOSOTROS y no arregla el problema: un
# comprador que abra Python —el lenguaje en el que estan escritas nuestras propias
# herramientas de verificacion— sigue recibiendo 403 siguiendo nuestras instrucciones.
# El arreglo de verdad es en la regla del borde; esto es la venda mientras tanto, y se
# deja anotado para que nadie confunda una con otra.
AGENTE = "RosettaQuantum-mapa-frontera/1.0 (+https://rosettaquantum.com)"


def _traer(url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def desde_api():
    ids = [it["id"] for it in _traer("%s/runs?limit=1000" % API)["items"]]
    docs, fallidos = [], []
    for i in ids:
        try:
            docs.append((_traer("%s/archive/%s" % (API, i)), i))
        except Exception as e:
            fallidos.append(i)
            print("  no se pudo traer %s: %s" % (i, str(e)[:60]))
    # El denominador tambien aca: «37 puntos» sobre 68 corridas leidas no es lo mismo
    # que sobre 68 pedidas y 12 caidas. Sin esta linea, una API a medias produce un
    # mapa mas chico que se lee como un archivo mas chico.
    print("  API: %d corridas pedidas · %d traidas · %d fallidas"
          % (len(ids), len(docs), len(fallidos)))
    return docs


if __name__ == "__main__":
    docs = desde_api() if "--api" in sys.argv else desde_archivo()
    puntos, descartados = [], []
    for d, fid in docs:
        p, porque = extraer(d, fid)
        (puntos.append(p) if p else descartados.append({"id": fid, "porque": porque}))

    puntos.sort(key=lambda x: (x["clase"], x["variables"]))
    clases = {}
    for p in puntos:
        clases.setdefault(p["clase"], []).append(p)

    mapa = {
        "que_es": "Brecha del brazo cuantico respecto del mejor clasico, por clase de problema y "
                  "tamaño del problema de decision. Cada punto es una corrida sellada y verificable.",
        "eje_x": "variables binarias del problema (= qubits en nuestro encoding)",
        "eje_y": "brecha % del cuantico respecto del optimo exacto; 0 = lo empata",
        "muro_simulacion": MURO_SIMULACION,
        "muro_memoria": MURO_MEMORIA,
        "nota_del_muro": "22 es el ultimo tamaño que cabe en memoria Y termina en el reloj de CI, "
                         "medido el 2026-08-13. Por encima hay que ir a hardware real, que cuesta.",
        # DENOMINADOR, siempre: un mapa que no dice cuantas corridas dejo fuera se lee como
        # si las hubiera usado todas.
        "denominador": {"corridas_leidas": len(docs), "puntos_en_el_mapa": len(puntos),
                        "descartadas": len(descartados)},
        "no_cubre": "Alosteria (RQ-0007): su metrica es un percentil de ranking, no una brecha de "
                    "optimalidad. Mezclarla daria un plano cuyos ejes significan cosas distintas "
                    "segun el punto. Se declara aparte en vez de forzarla.",
        "clases": {},
        "puntos": puntos,
        "descartadas": descartados,
    }
    for c, ps in clases.items():
        ps2 = sorted(ps, key=lambda x: x["variables"])
        mapa["clases"][c] = {
            "n_puntos": len(ps2),
            "rango_variables": [ps2[0]["variables"], ps2[-1]["variables"]],
            "brecha_min_pct": min(p["brecha_cuantica_pct"] for p in ps2),
            "brecha_max_pct": max(p["brecha_cuantica_pct"] for p in ps2),
            "algun_empate": any(p["brecha_cuantica_pct"] <= 0.0 for p in ps2),
            "alguna_victoria": any(p["brecha_cuantica_pct"] < 0.0 for p in ps2),
        }

    json.dump(mapa, open(SALIDA, "w"), indent=1, ensure_ascii=False)
    print("MAPA DE FRONTERA — %d corridas leidas · %d puntos · %d descartadas\n"
          % (len(docs), len(puntos), len(descartados)))
    for c, r in sorted(mapa["clases"].items()):
        print("  %-28s %2d puntos · %2d-%2d variables · brecha %.2f%% a %.2f%%%s"
              % (c[:28], r["n_puntos"], r["rango_variables"][0], r["rango_variables"][1],
                 r["brecha_min_pct"], r["brecha_max_pct"],
                 "  ← EMPATA" if r["algun_empate"] else ""))
    if descartados:
        print("\n  descartadas y por que (no se rellenan):")
        vistos = {}
        for d in descartados:
            vistos.setdefault(d["porque"], []).append(d["id"])
        for porque, ids in vistos.items():
            print("    %-52s %d (%s…)" % (porque[:52], len(ids), ids[0]))
    print("\nescrito %s" % os.path.relpath(SALIDA, RAIZ))
