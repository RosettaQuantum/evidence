#!/usr/bin/env python3
"""Pruebas del motor. Cada guardia trae su caso positivo — un chequeo que nunca se
comprobo gritando es indistinguible de un chequeo borrado.

Corre sin descargar nada y sin los caches de 165 MB: usa grafos sinteticos donde la
respuesta correcta se conoce de antemano, mas los caches ciegos que si estan en git.

    python3 tests/test_engine.py
    python3 tests/test_engine.py --self-test   # se obliga a fallar
"""
import glob
import json
import os
import pickle
import sys

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "rq_engine"))

import rq_engine                       # noqa: E402  (el paquete arma el sys.path)
import allo_challenge as AC            # noqa: E402

SELF = "--self-test" in sys.argv
pasaron, fallaron, saltados = 0, 0, 0


def ok(n):
    global pasaron
    pasaron += 1
    print("  ok    %s" % n)


def mal(n, d):
    global fallaron
    fallaron += 1
    print("  FALLO %s\n        %s" % (n, d))


def comprobar(n, cond, detalle=""):
    ok(n) if cond else mal(n, detalle)


def saltar(n, por_que):
    """Un chequeo que NO se pudo ejercer. Entra al resumen, no a una linea suelta.

    Antes esto era un `print` arriba de 49 lineas de `ok`, y el numero que la gente lee
    seguia diciendo "49 pasaron, 0 fallaron": la suite salia en verde sin haber ejercido
    los tres chequeos de reproducibilidad, y nada en la cifra lo decia. Es el defecto que
    perseguimos —cobertura menor que la declarada, en verde— dentro del propio guardia.
    """
    global saltados
    saltados += 1
    print("  SALTA %s\n        %s" % (n, por_que))


# ---------------------------------------------------------------- red de contactos
def camino(n):
    """Grafo camino 0-1-2-...-n-1 con coordenadas a 1 A de paso."""
    coords = np.zeros((n, 3))
    coords[:, 0] = np.arange(n, dtype=float)
    A = np.zeros((n, n))
    for i in range(n - 1):
        A[i, i + 1] = A[i + 1, i] = 1.0
    return coords, A


def pesos(coords, A, sigma=6.0):
    D = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    W = np.exp(-(D ** 2) / (2 * sigma ** 2)) * (A > 0)
    np.fill_diagonal(W, 0.0)
    return W


print("RED DE CONTACTOS")
# El corte es el parametro que define la red entera. Si cambiarlo no cambia nada,
# la red no depende de la geometria y todo lo demas es ruido.
coords = np.array([[0., 0, 0], [3., 0, 0], [7., 0, 0], [20., 0, 0]])
d = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
A5 = ((d < 5.0) & (d > 0)).astype(float)
A85 = ((d < 8.5) & (d > 0)).astype(float)
comprobar("un corte mas grande agrega aristas y ninguna se pierde",
          A85.sum() > A5.sum() and np.all(A85 >= A5),
          "corte 5: %d aristas · corte 8.5: %d" % (A5.sum() / 2, A85.sum() / 2))
comprobar("el residuo lejano queda aislado con los dos cortes",
          A5[3].sum() == 0 and A85[3].sum() == 0)
comprobar("la adyacencia es simetrica y sin lazos",
          np.allclose(A85, A85.T) and np.allclose(np.diag(A85), 0))
comprobar("allo_challenge declara las constantes selladas",
          AC.GT_RADIUS == 4.5 and AC.DISTAL_A == 6.0,
          "GT_RADIUS=%s DISTAL_A=%s" % (AC.GT_RADIUS, AC.DISTAL_A))

# ---------------------------------------------------------------- propagadores
print("\nPROPAGADORES")
n = 12
coords, A = camino(n)
W = pesos(coords, A)
L = np.diag(W.sum(1)) - W
p0 = np.zeros(n); p0[0] = 1.0

from scipy.linalg import expm  # noqa: E402

# LA AFIRMACION CENTRAL DEL METODO, PROBADA:
# el analogo clasico promediado a tiempo largo pierde toda la informacion (converge al
# reparto uniforme), y la caminata cuantica no. Si esto se cae, el metrico entero se cae.
clasico_largo = expm(-L * 5000.0) @ p0
comprobar("la difusion clasica a tiempo largo converge al uniforme (no informa)",
          np.allclose(clasico_largo, np.ones(n) / n, atol=1e-6),
          "max desvio %.2e" % np.abs(clasico_largo - 1.0 / n).max())

vals, vecs = np.linalg.eigh(W)
C = np.zeros_like(W)
i = 0
while i < len(vals):
    j = i
    while j + 1 < len(vals) and abs(vals[j + 1] - vals[i]) < 1e-9:
        j += 1
    P = vecs[:, i:j + 1] @ vecs[:, i:j + 1].T
    C += P ** 2
    i = j + 1
col = C[:, 0]
comprobar("la matriz de mezcla NO es uniforme (retiene estructura)",
          col.std() / col.mean() > 0.1,
          "coef. de variacion %.4f" % (col.std() / col.mean()))
comprobar("cada columna de la matriz de mezcla suma 1",
          np.allclose(C.sum(axis=0), 1.0, atol=1e-9),
          "suma min %.6f max %.6f" % (C.sum(0).min(), C.sum(0).max()))
comprobar("la matriz de mezcla es simetrica",
          np.allclose(C, C.T, atol=1e-12))
# HALLAZGO, no suposicion. Escribi este chequeo esperando decaimiento con la distancia
# y grito: en un grafo camino la matriz de mezcla es PLANA en el interior y se dispara en
# los DOS extremos — el extremo lejano puntua igual que la propia fuente. No es un
# error del metrico: es lo que hace la localizacion espectral en nodos de grado 1.
# Consecuencia directa para el challenge: en una proteina eso significa que los extremos
# de cadena y las protuberancias de superficie suben solos. Queda como prueba para que
# si alguien "arregla" el metrico y esto cambia, se entere.
comprobar("en un camino, el extremo lejano puntua como la fuente (localizacion espectral)",
          abs(col[0] - col[n - 1]) < 1e-9 and col[1] < col[0],
          "fuente %.4f · interior %.4f · extremo %.4f" % (col[0], col[1], col[n - 1]))
comprobar("el interior del camino es plano (el metrico NO mide distancia ahi)",
          np.allclose(col[1:n - 1], col[1], atol=1e-9),
          "desvio interior %.2e" % np.abs(col[1:n - 1] - col[1]).max())

# ---------------------------------------------------------------- catalogo
print("\nCATALOGO")
cat = json.load(open(os.path.join(RAIZ, "rq_engine", "catalog.json")))
prots = cat["proteins"]
comprobar("el catalogo tiene proteinas", len(prots) > 0, "%d" % len(prots))
faltan = [k for k, v in prots.items()
          if not all(v.get(c) for c in ("apo", "holo", "chain", "uniprot", "gene"))]
comprobar("ninguna entrada del catalogo esta incompleta (falla cerrado)",
          not faltan, "incompletas: %s" % faltan[:5])
train = json.load(open(os.path.join(RAIZ, "rq_engine", "_train90.json")))
huerfanas = [p for p in train if p not in prots]
comprobar("las %d proteinas de entrenamiento existen en el catalogo" % len(train),
          not huerfanas, "huerfanas: %s" % huerfanas[:5])

# FUGA DE DATOS: los blancos del challenge que estan en el set de entrenamiento no
# pueden predecirse con un modelo entrenado con las 90 sin dejarlos fuera. El guardia
# no prohibe el solapamiento — lo hace visible, que es lo que se puede exigir.
BLANCOS = ["KRAS_G12C", "BCR_ABL1", "CARDIAC_MYOSIN"]
solapan = [b for b in BLANCOS if b in train]
comprobar("el solapamiento entrenamiento/challenge esta declarado",
          set(solapan) == {"KRAS_G12C", "BCR_ABL1", "CARDIAC_MYOSIN"},
          "solapan: %s — si esta lista cambia, el reporte metodologico tiene que cambiar" % solapan)

# ---------------------------------------------------------------- caches ciegos
print("\nCACHES CIEGOS")
import build_cache as BC                # noqa: E402
ciegos = sorted(os.path.basename(p)[:-4]
                for p in glob.glob(os.path.join(RAIZ, "cache_blind", "*.npz")))
comprobar("hay 4 caches ciegos", len(ciegos) == 4, "%d" % len(ciegos))
comprobar("ningun cache quedo en pickle (formato no portable entre versiones de numpy)",
          not glob.glob(os.path.join(RAIZ, "cache_blind", "*.pkl")))
for nom_c in ciegos:
    d = BC.load(nom_c)
    nom = d["name"]
    # LA CEGUERA, COMPROBADA: un cache con 'allo' adentro sabe donde esta el bolsillo,
    # y cualquier prediccion hecha con el estaria contaminada.
    comprobar("%s no contiene el bolsillo (es ciego)" % nom,
              "allo" not in d and d.get("ciego") is True,
              "claves: %s" % [k for k in d if k in ("allo", "ciego")])
    comprobar("%s ancla su estructura por hash" % nom,
              str(d.get("pdb_sha256", "")).startswith("sha256:"))
    A = d["A"]
    seen, pila = set(d["src"]), list(d["src"])
    while pila:
        u = pila.pop()
        for v in np.nonzero(A[u])[0]:
            if int(v) not in seen:
                seen.add(int(v)); pila.append(int(v))
    comprobar("%s: la red es conexa desde la fuente" % nom,
              len(seen) == d["n"], "%d de %d alcanzables" % (len(seen), d["n"]))

# ---------------------------------------------------------------- costos
print("\nCOSTOS")
import costos as CO                       # noqa: E402
comprobar("cada dispositivo declara region, precio y ARN",
          all(all(k in d for k in ("region", "por_disparo", "por_tarea", "arn", "qubits"))
              for d in CO.BRAKET.values()),
          "faltan campos en: %s" % [k for k, d in CO.BRAKET.items()
                                    if not all(x in d for x in ("region", "arn"))])
# La region del ARN y la declarada tienen que ser la misma: enviar a la region equivocada
# es un error que solo aparece cuando ya gastaste. Y ya me equivoque una vez diciendo que
# todos los dispositivos vivian en us-east-1 cuando Rigetti esta en us-west-1 e IQM en
# eu-north-1.
malas = [k for k, d in CO.BRAKET.items() if (":braket:%s:" % d["region"]) not in d["arn"]]
comprobar("la region declarada calza con la del ARN en los %d dispositivos" % len(CO.BRAKET),
          not malas, "no calzan: %s" % malas)
c = CO.costo("rigetti-cepheus", 6, 4000)
comprobar("el costo se calcula: 6 tareas x 4000 disparos en Cepheus",
          abs(c["usd_total"] - (6 * 0.30 + 24000 * 0.000425)) < 1e-9,
          "da %.4f" % c["usd_total"])
comprobar("sin validez MEDIDA no se inventa costo por medicion util",
          CO.por_medicion_valida(c, None) is None)
comprobar("con validez medida, el costo por medicion util sube respecto del nominal",
          CO.por_medicion_valida(c, 0.614) > c["usd_total"] / c["disparos_totales"],
          "el ruido encarece cada medicion util; si no sube, la formula esta al reves")

# ---------------------------------------------------------------- huellas
print("\nHUELLAS")
h = rq_engine.huellas()
comprobar("el paquete declara el hash de sus 4 modulos",
          len(h) == 4 and all(v.startswith("sha256:") for v in h.values()))
comprobar("sigo_features vigente NO es la version perdida que citan los sellos",
          not h["sigo_features.py"].endswith("0460d1f638c1244ea97fcbbf991b3f1da773353f035741c40132e2fa6e68869f"),
          "si esto falla, la referencia perdida se resolvio y hay que actualizar la enmienda")

# ---------------------------------------------------------------- guardias
# Los dos defectos que estos guardias cubren son REALES y del 2026-08-10: la conservacion
# que falla abierto a una columna de ceros (Biopython 1.79 contra el >=1.80 que pide
# conservation.py), y el `continue` silencioso que corre con menos proteinas de las
# declaradas. Los casos se escriben contra ESOS defectos, no contra un ejemplo inventado.
print("\nGUARDIAS")
import guardias as G                        # noqa: E402

comprobar("una columna con datos esta viva", G.viva([0.1, 0.4, 0.9]))
comprobar("la columna de ceros que deja la conservacion rota esta MUERTA",
          not G.viva(np.zeros(50)))
comprobar("una columna ausente (None) esta muerta", not G.viva(None))
comprobar("una columna toda NaN esta muerta", not G.viva([float("nan")] * 5))

# el caso legitimo que NO debe gritar: una proteina sin motivos declarados
_cols = ["conservation", "uni_motif", "degree"]
_D = [{"name": "P1", "features": {"conservation": [0.2, 0.9, 0.5], "uni_motif": [0, 0, 0],
                                  "degree": [3, 5, 4]}},
      {"name": "P2", "features": {"conservation": [0.7, 0.1, 0.3], "uni_motif": [0, 1, 0],
                                  "degree": [2, 6, 4]}}]
_c = G.censo_features(_D, _cols)
comprobar("el censo reporta su denominador (proteinas y columnas)",
          _c["proteinas"] == 2 and _c["columnas_declaradas"] == 3)
comprobar("una proteina sin motivos NO cuenta como columna muerta del conjunto",
          _c["muertas_en_todas"] == [] and _c["vivas_por_columna"]["uni_motif"] == 1,
          "muertas: %s · uni_motif viva en %d de 2"
          % (_c["muertas_en_todas"], _c["vivas_por_columna"]["uni_motif"]))
try:
    G.exigir_features(_D, _cols)
    ok("exigir_features deja pasar un conjunto sano")
except G.ColumnaMuerta as e:
    mal("exigir_features deja pasar un conjunto sano", str(e))

# EL CASO POSITIVO QUE IMPORTA: conservacion muerta en TODAS, como la deja Biopython 1.79
_Droto = [{"name": d["name"], "features": dict(d["features"], conservation=None)} for d in _D]
try:
    G.exigir_features(_Droto, _cols)
    mal("la conservacion muerta en todas hace gritar al guardia",
        "NO grito — el defecto mas grave del motor pasaria de nuevo")
except G.ColumnaMuerta as e:
    # el mensaje tiene que nombrar la COLUMNA y las DOS causas conocidas. La segunda
    # —escritor y lector en rutas distintas— mato todas las corridas del N=90 y no
    # estaba en el mensaje original, que solo culpaba a Biopython.
    comprobar("la conservacion muerta en todas hace gritar al guardia",
              "conservation" in str(e) and "1.80" in str(e) and "CWD" in str(e),
              "grito, pero sin nombrar la columna o alguna de las dos causas: %s" % e)

comprobar("exigir_cobertura deja pasar cuando estan todas",
          G.exigir_cobertura(["A", "B"], ["B", "A"])["faltan"] == 0)
try:
    G.exigir_cobertura(["A", "B", "C"], ["A"], "proteinas")
    mal("correr con menos proteinas de las declaradas hace gritar al guardia",
        "NO grito — el `continue` silencioso pasaria de nuevo")
except G.AlcanceMenorQueLoDeclarado as e:
    comprobar("correr con menos proteinas de las declaradas hace gritar al guardia",
              "B" in str(e) and "C" in str(e),
              "grito, pero sin decir CUALES faltan: %s" % e)


# ------------------------------------------------- el resultado se reproduce solo
# Escrito contra el defecto REAL de la corrida 31531185175, no contra un ejemplo
# inventado. Ese artefacto publicaba `"B_p": 0.0` para SLC6A4_ALLO. Un tercero que
# lo bajara y recomputara Fisher —que es LA instruccion que le damos— obtenia
# 6,8e-241 en vez de 4,9e-09: 230 ordenes de magnitud, y en la direccion de parecer
# un resultado mucho mas fuerte del que medimos. El sello verificaba perfecto; la
# promesa que lo acompanaba, no.
from engine import fisher, p_legible                        # noqa: E402
from scipy.stats import chi2 as chi2dist                    # noqa: E402

_p_piso = 1.0 / 2001                                        # piso de nperm=2000

comprobar("p_legible NO convierte una p chica en cero",
          p_legible(4.896e-09) != 0.0 and p_legible(1.333e-07) != 0.0,
          "una p menor a la resolucion del redondeo vuelve a salir como 0.0")

comprobar("p_legible conserva el orden entre dos p chicas distintas",
          p_legible(4.896e-09) < p_legible(1.333e-07),
          "dos brazos distintos quedan indistinguibles al escribirse")

# El caso exacto que rompio, con la magnitud MEDIDA y no supuesta: con 89 p en la
# mediana del brazo B (0,249), publicar la nonagesima como 0.0 en vez de su piso de
# 4,9975e-4 lleva la combinada de 5,7e-05 a 1,5e-231 para quien la lea literalmente.
# Son 226 ordenes de magnitud, todos en la direccion de parecer un resultado mucho
# mas fuerte del que medimos.
_ps_reales = [0.249] * 89                                   # mediana medida del brazo B
_con_piso = fisher(_ps_reales + [_p_piso])
_leido_literal = float(chi2dist.sf(
    -2 * float(np.sum(np.log(np.array(_ps_reales + [1e-300])))), 2 * 90))
comprobar("publicar una p como cero desplaza Fisher mas de 100 ordenes de magnitud",
          _con_piso / max(_leido_literal, 1e-320) > 1e100,
          "el cero y el piso dan casi lo mismo — este test ya no distingue el defecto")

comprobar("ninguna p de permutacion publicada puede ser exactamente cero",
          all(p_legible(_p_piso, d) != 0.0 for d in (2, 3, 4)),
          "el piso 4,9975e-4 se sigue escribiendo como 0.0 al redondear")

# y el guardia que importa: el artefacto tiene que reproducirse a si mismo
def _fisher_desde_filas(filas, clave):
    """Recomputa Fisher como lo haria un tercero: desde los per_protein publicados."""
    ps = []
    for f in filas:
        if clave + "_n_ge" in f:                            # dato crudo: preferirlo
            ps.append(max(f[clave + "_n_ge"] / float(f[clave + "_nperm"]),
                          1.0 / (f[clave + "_nperm"] + 1)))
        elif clave + "_p" in f:
            ps.append(f[clave + "_p"])
    return fisher(ps) if ps else None

def _reproduce(doc, clave):
    """(publicado, recomputado, veredicto) para un brazo de un artefacto.

    Una p publicada en CERO es un fallo, no un caso a perdonar: es irreproducible por
    construccion. La primera version de esta condicion empezaba con `_pub == 0.0 or
    ...`, o sea daba por bueno exactamente el caso roto y salia en verde contra el
    artefacto defectuoso. Un chequeo con una excepcion hecha para el defecto que
    vigila deja de ser un chequeo."""
    pub = doc.get("fisher_p", {}).get(clave[0])
    rec = _fisher_desde_filas(doc.get("per_protein", []), clave[1])
    if pub is None or rec is None:
        return None, None, None
    if pub == 0.0:
        return pub, rec, False
    return pub, rec, 0.1 <= (rec / pub) <= 10.0      # los p por proteina van a 3 decimales


BRAZOS = (("armA_manager", "A"), ("armB_ml", "B"), ("armC_stacked", "C"))
_FIJAS = os.path.join(RAIZ, "tests", "fixtures")

# Las dos fijas son el MISMO experimento: el artefacto real de la corrida 31531185175 y
# su version con el piso de permutacion restituido. La unica diferencia entre ambas es
# el defecto, que es lo que el guardia tiene que ver — y por eso se ejercen SIEMPRE, sin
# depender de que alguien haya corrido el experimento en este arbol. Un guardia que solo
# corre cuando hay artefacto es un guardia que casi nunca corre.
for _nom, _archivo, _espera_ok in (
        ("bueno", "n90_bueno.json", True),
        ("roto (corrida 31531185175)", "n90_roto_31531185175.json", False)):
    _ruta = os.path.join(_FIJAS, _archivo)
    if not os.path.exists(_ruta):
        saltar("fija %s: el guardia de reproducibilidad se ejerce" % _nom,
               "falta tests/fixtures/%s — sin ella el guardia no tiene caso positivo" % _archivo)
        continue
    _doc = json.load(open(_ruta))
    _veredictos = [_reproduce(_doc, b)[2] for b in BRAZOS]
    _veredictos = [v for v in _veredictos if v is not None]
    if _espera_ok:
        comprobar("fija buena: los 3 brazos reproducen desde el artefacto",
                  len(_veredictos) == 3 and all(_veredictos),
                  "veredictos %s — el guardia retiene un artefacto sano" % _veredictos)
    else:
        # El caso positivo: contra el defecto REAL tiene que gritar, y en los brazos
        # donde estaba el cero (B y C), no en el que estaba sano (A).
        comprobar("fija rota: el guardia grita en B y C y deja pasar A",
                  _veredictos == [True, False, False],
                  "veredictos %s — se esperaba [A ok, B falla, C falla]" % _veredictos)

# Y si ademas hay un resultado real en el arbol, se comprueba tambien.
_res = os.path.join(RAIZ, "rq_engine", "results", "RQ-EXP-N90-LOPO.json")
if os.path.exists(_res):
    _d = json.load(open(_res))
    for _brazo in BRAZOS:
        _pub, _rec, _v = _reproduce(_d, _brazo)
        if _v is None:
            continue
        comprobar("brazo %s del resultado en el arbol: reproduce lo publicado" % _brazo[1],
                  _v, "publicado %s, recomputado %.3e — un tercero no reproduce"
                      % (_pub, _rec))


# ---------------------------------------------------------------- self-test
if SELF:
    print("\nSELF-TEST — cada guardia se obliga a gritar")
    antes = fallaron
    comprobar("[self] uniforme detectado como no-uniforme", (np.ones(n) / n).std() > 0.01)
    comprobar("[self] cache con 'allo' detectado como ciego", "allo" not in {"allo": 1})
    comprobar("[self] catalogo vacio pasa como poblado", len({}) > 0)
    # el contador de saltados tambien necesita su caso positivo: si `saltar()` dejara de
    # sumar, la linea final diria "0 saltados" con chequeos sin ejercer, que es
    # exactamente el defecto que este contador existe para hacer visible.
    _saltados_antes = saltados
    saltar("[self] un chequeo que no se pudo ejercer", "provocado por el self-test")
    comprobar("[self] el contador de saltados suma cuando algo no se ejerce",
              saltados == _saltados_antes + 1,
              "saltar() no incremento el contador: la linea final mentiria")
    saltados = _saltados_antes          # el salto provocado no cuenta, como los fallos

    esperados = 3
    reales = fallaron - antes
    print("  self-test: %d de %d guardias gritaron" % (reales, esperados))
    if reales != esperados:
        print("  ERROR: un guardia no grito cuando debia")
        sys.exit(2)
    fallaron = antes                       # los fallos provocados no cuentan
    pasaron += esperados

print("\n%d pasaron, %d fallaron, %d saltados" % (pasaron, fallaron, saltados))
if saltados:
    print("OJO: %d chequeo(s) no se ejercieron. Verde no es lo mismo que cubierto."
          % saltados)
sys.exit(1 if fallaron else 0)
