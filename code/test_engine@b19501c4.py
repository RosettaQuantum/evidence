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
pasaron, fallaron = 0, 0


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

# ---------------------------------------------------------------- huellas
print("\nHUELLAS")
h = rq_engine.huellas()
comprobar("el paquete declara el hash de sus 4 modulos",
          len(h) == 4 and all(v.startswith("sha256:") for v in h.values()))
comprobar("sigo_features vigente NO es la version perdida que citan los sellos",
          not h["sigo_features.py"].endswith("0460d1f638c1244ea97fcbbf991b3f1da773353f035741c40132e2fa6e68869f"),
          "si esto falla, la referencia perdida se resolvio y hay que actualizar la enmienda")

# ---------------------------------------------------------------- self-test
if SELF:
    print("\nSELF-TEST — cada guardia se obliga a gritar")
    antes = fallaron
    comprobar("[self] uniforme detectado como no-uniforme", (np.ones(n) / n).std() > 0.01)
    comprobar("[self] cache con 'allo' detectado como ciego", "allo" not in {"allo": 1})
    comprobar("[self] catalogo vacio pasa como poblado", len({}) > 0)
    esperados = 3
    reales = fallaron - antes
    print("  self-test: %d de %d guardias gritaron" % (reales, esperados))
    if reales != esperados:
        print("  ERROR: un guardia no grito cuando debia")
        sys.exit(2)
    fallaron = antes                       # los fallos provocados no cuentan
    pasaron += esperados

print("\n%d pasaron, %d fallaron" % (pasaron, fallaron))
sys.exit(1 if fallaron else 0)
