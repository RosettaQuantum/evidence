#!/usr/bin/env python3
"""Publica el insumo de `poc_ibm.py` en formato portable, para que su corrida sellada
sea REPRODUCIBLE por un tercero.

EL PROBLEMA QUE CIERRA
----------------------
`code/poc_ibm@db044b45.py` esta publicado y su sha256 calza con el `harness_sha256` que
el sello RQ-POC-QPU-001 declara. Y aun asi **no se puede ejecutar**: su primera linea util
es `pickle.load(os.path.join(CACHE, "%s.pkl"))`, y ese pickle vive solo en `quantum-run`,
que es un repositorio PRIVADO. Ademas solo se deserializa con numpy 2.x — con 1.x revienta
con `No module named numpy._core`.

Publicado no es lo mismo que ejecutable, y ejecutable no es lo mismo que verificable. El
auditor de procedencia garantiza lo primero; esto cierra los otros dos.

Medido sobre el archivo: 4 de 42 scripts publicados leen un cache `.pkl` y hay CERO
pickles publicados. Este es el primero de los cuatro, y es el mas urgente por ser harness
de un sello anclado.

QUE SE PUBLICA Y POR QUE ASI
----------------------------
No el pickle: 15 KB de numeros planos en vez de 260 KB de binario. Un JSON no ejecuta
codigo al cargarse, no depende de la version de numpy, y se lee desde cualquier lenguaje.
El mapa de contactos es binario, asi que va como lista de aristas.

GUARDIA
-------
Falla cerrado: reconstruye el sub-grafo de 12 nodos USANDO SOLO el archivo portable y
exige que de identico al que sale del pickle — mismos indices, misma W, mismo v. Un
insumo portable que produce otro sub-grafo no sirve de nada, y se veria bien igual.

Simulacion local. Costo US$0.
"""
import hashlib, json, os, sys, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
POC = os.path.join(RAIZ, "poc")
_SHIM = None
if not hasattr(np, "_core"):
    import numpy.core as _c
    sys.modules["numpy._core"] = _c
    for _s in ("multiarray", "umath", "numeric", "numerictypes", "_multiarray_umath"):
        try: sys.modules["numpy._core." + _s] = __import__("numpy.core." + _s, fromlist=[_s])
        except Exception: pass
    _SHIM = "numpy._core -> numpy.core (el pickle exige numpy 2.x; este runtime es 1.x)"
sys.path.insert(0, POC)
import poc_ibm as P

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
NOMBRE = "KRAS_G12C"
CACHE = os.path.join(POC, "cache", "%s.pkl" % NOMBRE)

d = P.load(NOMBRE)
A = np.asarray(d["A"])
assert set(np.unique(A).tolist()) <= {0.0, 1.0}, "el mapa de contactos no es binario"
assert np.allclose(A, A.T), "el mapa de contactos no es simetrico"

port = {
    "file_id": "RQ-CACHE-PORTABLE-KRAS-001",
    "que_es": "el insumo de poc_ibm.py para %s, en formato plano. Reemplaza al pickle "
              "para efectos de verificacion: mismo contenido, sin binario y sin depender "
              "de la version de numpy." % NOMBRE,
    "para_que_sello": {"file_id": "RQ-POC-QPU-001",
                       "harness": "poc_ibm.py",
                       "harness_sha256": "sha256:" + sha(os.path.join(POC, "poc_ibm.py"))},
    "proteina": NOMBRE, "n_residuos": int(d["n"]),
    "src_method": d["src_method"],
    "ids_residuo": [[c, int(r)] for c, r in d["ids"]],
    "contactos": [[int(i), int(j)] for i, j in zip(*np.triu_indices_from(A, 1)) if A[i, j] > 0],
    "coords": [[round(float(x), 3) for x in r] for r in d["coords"]],
    "conservation": [round(float(x), 6) for x in np.asarray(d["features"]["conservation"], float)],
    "src": [int(x) for x in d["src"]], "allo": [int(x) for x in d["allo"]],
    "mask": [bool(x) for x in np.asarray(d["mask"])],
    "como_se_usa": "reconstruir A como matriz simetrica 0/1 desde `contactos`, armar el "
                   "dict {A, n, src, allo, mask, coords, features:{conservation}} y "
                   "pasarlo a subgraph() de poc_ibm.py. Da el sub-grafo de 12 nodos que "
                   "el sello uso.",
    "entorno_original": {"numpy_del_pickle": "2.x", "numpy_de_esta_corrida": np.__version__,
                         "shim": _SHIM},
    "insumo_original": {"archivo": "cache/%s.pkl" % NOMBRE, "sha256": "sha256:" + sha(CACHE),
                        "donde_vive": "quantum-run (repositorio PRIVADO) — por eso este "
                                      "archivo existe."},
}

# ------------------------------------------------------- GUARDIA: falla cerrado
# Reconstruir usando SOLO lo que se publica, y exigir que de el mismo sub-grafo.
n = port["n_residuos"]
A2 = np.zeros((n, n))
for i, j in port["contactos"]: A2[i, j] = A2[j, i] = 1.0
d2 = {"A": A2, "n": n, "src": port["src"], "allo": port["allo"],
      "mask": np.array(port["mask"]), "coords": np.array(port["coords"], float),
      "features": {"conservation": np.array(port["conservation"], float)}}
idx1, W1, v1, r1 = P.subgraph(d)
idx2, W2, v2, r2 = P.subgraph(d2)
if list(idx1) != list(idx2):
    raise SystemExit("ABORTA: el archivo portable produce OTRO sub-grafo.\n  pickle:  %s\n"
                     "  portable: %s" % (list(idx1), list(idx2)))
dW = float(np.max(np.abs(W1 - W2))); dv = float(np.max(np.abs(v1 - v2)))
if dW > 1e-6 or dv > 1e-6:
    raise SystemExit("ABORTA: mismo sub-grafo pero distintos pesos — W difiere %.2e, "
                     "v difiere %.2e" % (dW, dv))
if r1 != r2:
    raise SystemExit("ABORTA: los roles (fuente/bolsillo) no coinciden")

# La comparacion de arriba solo mira los 12 nodos del sub-grafo. Eso deja pasar en
# silencio cualquier error en los otros 157 residuos — y el archivo se publica como el
# insumo de la proteina ENTERA, no como el del sub-grafo. Un guardia que solo cubre la
# parte que le interesa a un consumidor se lee como si cubriera todo.
for etiqueta, a_, b_ in (("mapa de contactos", A, A2),
                         ("coordenadas", np.asarray(d["coords"], float),
                          np.asarray(port["coords"], float)),
                         ("conservacion", np.asarray(d["features"]["conservation"], float),
                          np.asarray(port["conservation"], float)),
                         ("mascara", np.asarray(d["mask"]).astype(bool),
                          np.asarray(port["mask"], bool))):
    a_ = np.asarray(a_); b_ = np.asarray(b_)
    if a_.shape != b_.shape:
        raise SystemExit("ABORTA: %s cambio de forma: %s -> %s" % (etiqueta, a_.shape, b_.shape))
    # las coordenadas se redondean a 3 decimales y la conservacion a 6, a proposito;
    # la tolerancia es la del redondeo declarado, no una tolerancia inventada.
    tol = {"coordenadas": 5e-4, "conservacion": 5e-7}.get(etiqueta, 0.0)
    dif = float(np.max(np.abs(a_.astype(float) - b_.astype(float)))) if a_.size else 0.0
    if dif > tol:
        raise SystemExit("ABORTA: %s difiere en %.2e (tolerancia %.0e por el redondeo "
                         "declarado) — lo publicado no es el insumo" % (etiqueta, dif, tol))
if len(port["src"]) != len(d["src"]) or len(port["allo"]) != len(d["allo"]):
    raise SystemExit("ABORTA: las listas de fuente/bolsillo cambiaron de largo")
port["verificado"] = {
    "reconstruye_el_mismo_subgrafo": True,
    "subgraph_node_ids": [int(x) for x in idx2],
    "max_dif_W": dW, "max_dif_v": dv,
    "como": "se corrio subgraph() dos veces —una desde el pickle y otra desde SOLO este "
            "archivo— y se compararon indices, pesos, potencial y roles. Ademas se "
            "comparan los 169 residuos completos: contactos, coordenadas, conservacion y "
            "mascara, con la tolerancia del redondeo declarado y no una inventada.",
    "alcance_de_la_comprobacion": "los 169 residuos, no solo los 12 del sub-grafo.",
}
port["producido_por"] = {"script": "cache_portable_kras.py", "sha256": "sha256:" + sha(__file__)}

dst = os.path.join(os.environ.get("RQ_OUT_DIR", AQUI), "cache_portable_KRAS_G12C.json")
json.dump(port, open(dst, "w"), indent=1, ensure_ascii=False)
print("emitido:", os.path.basename(dst), "| %d bytes (el pickle: %d)"
      % (os.path.getsize(dst), os.path.getsize(CACHE)))
print("  mismo sub-grafo:", port["verificado"]["subgraph_node_ids"])
print("  max dif W=%.2e  v=%.2e" % (dW, dv))
print("  sha256:", sha(dst)[:16])
