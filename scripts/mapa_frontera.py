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


def extraer(doc, fid):
    """Un punto del mapa, o None con su razon. Nunca inventa el tamaño ni la brecha."""
    clase = _hondo(doc, {"problem_class", "clase_de_problema"})
    inst = _hondo(doc, {"instance", "instancia"})
    gaps = _hondo(doc, {"quality_gaps_pct"})
    params = _hondo(doc, {"instance_params", "params"}) or {}

    # --- el tamaño, por orden de confianza: declarado > derivado > ausente
    tam, fuente_tam = None, None
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
    if isinstance(gaps, dict):
        gq, gc = gaps.get("quantum"), gaps.get("classical")
    if gq is None:
        gq = _hondo(doc, {"quantum_gap_pct"})
        gc = _hondo(doc, {"classical_gap_pct"})

    if tam is None:
        return None, "sin tamaño: ningun campo declara cuantas variables tenia"
    if gq is None:
        return None, "sin brecha cuantica medida"

    arbitro = _hondo(doc, {"arbitro_efectivo", "arbitro"}) or (
        "optimo exacto declarado" if _hondo(doc, {"exact_optimum"}) is not None else None)

    return {
        "id": fid, "clase": clase or "sin declarar", "instancia": inst,
        "variables": tam, "fuente_del_tamaño": fuente_tam,
        "brecha_cuantica_pct": round(float(gq), 4),
        "brecha_clasica_pct": round(float(gc), 4) if gc is not None else None,
        "arbitro": arbitro,
        "cabe_en_simulacion": tam <= MURO_SIMULACION,
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


def desde_api():
    with urllib.request.urlopen("%s/runs?limit=1000" % API, timeout=30) as r:
        ids = [it["id"] for it in json.load(r)["items"]]
    docs = []
    for i in ids:
        try:
            with urllib.request.urlopen("%s/archive/%s" % (API, i), timeout=30) as r:
                docs.append((json.load(r), i))
        except Exception as e:
            print("  no se pudo traer %s: %s" % (i, str(e)[:60]))
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
