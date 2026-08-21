#!/usr/bin/env python3
"""Produce la DISTRIBUCION IDEAL por nodo de la CTQW de KRAS_G12C — el dato que
faltaba para poder comprobar la errata de RQ-POC-QPU-001.

POR QUE EXISTE
--------------
La errata afirma que lo medido en hardware se parece mas al ruido uniforme que a la
caminata ideal. Un tercero no puede comprobar eso: el sello guardo la distribucion
MEDIDA pero nunca la IDEAL, y el archivo `poc_result_KRAS_G12C.json` solo guardo las
masas agregadas, no el vector por nodo. Corregir una afirmacion no verificable con
otra afirmacion no verificable seria peor que el defecto original (CLAUDE.md §1 bis).

Este script emite el vector completo y se valida contra las dos cifras que YA estan
publicadas en ese archivo. Si no las reproduce, aborta: no emite un numero nuevo
apoyado en una reconstruccion que no se parece a la sellada.

DETERMINISMO
------------
`subgraph()` arma el sub-grafo con un `set`, cuyo orden de iteracion decide que
vecinos entran cuando se llena el cupo de 12 nodos. Para que un tercero no dependa de
eso, el artefacto publica `subgraph_node_ids` — los indices globales elegidos — de
modo que pueda comprobar que reconstruyo EL MISMO sub-grafo antes de comparar
distribuciones. Un vector que calza sobre otro sub-grafo no prueba nada.

NADA DE ESTO TOCA HARDWARE. Simulacion local, costo US$0.
"""
import hashlib, json, os, sys, numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
POC = os.path.join(RAIZ, "poc")

# el pickle del cache se escribio con numpy 2.x; aqui corre 1.x. El puente se declara
# en el artefacto porque cambia como se deserializa el insumo.
_SHIM = None
if not hasattr(np, "_core"):
    import numpy.core as _c
    sys.modules["numpy._core"] = _c
    for _s in ("multiarray", "umath", "numeric", "numerictypes", "_multiarray_umath"):
        try: sys.modules["numpy._core." + _s] = __import__("numpy.core." + _s, fromlist=[_s])
        except Exception: pass
    _SHIM = "numpy._core -> numpy.core (pickle escrito con numpy 2.x, runtime 1.x)"

sys.path.insert(0, POC)
import poc_ibm as P

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

CACHE = os.path.join(POC, "cache", "KRAS_G12C.pkl")
HARNESS = os.path.join(POC, "poc_ibm.py")
PUBLICADO = os.path.join(RAIZ, "evidence", "code", "poc_result_KRAS_G12C@68aada40.json")

ref = json.load(open(PUBLICADO))
d = P.load("KRAS_G12C")
idx, W, v, roles = P.subgraph(d)
allo = set(roles["allo"])
src = [(roles["src"] or [0])[0]]          # main() toma UNA sola fuente

# --- el sub-grafo reconstruido tiene que ser el mismo que el publicado
assert len(idx) == ref["nodes"] == 12, "el sub-grafo no tiene 12 nodos"
assert sorted(allo) == sorted(ref["pocket"]), "el bolsillo no coincide con el publicado"
assert src == ref["source"], "la fuente no coincide con la publicada"

exact = P.ctqw_exact(W, v, src, P.WIN_T)
r = ref["trotter_r"]
qc = P.build_circuit(W, v, src, P.WIN_T, r=r)
ideal = P.ideal_probs(qc, len(idx))

# --- FALLA CERRADO: si no reproduce lo publicado, no emite nada
me = float(sum(exact[a] for a in allo)); mi = float(sum(ideal[a] for a in allo))
for nombre, obt, esp in (("exact_pocket_mass", me, ref["exact_pocket_mass"]),
                         ("ideal_pocket_mass", mi, ref["ideal_pocket_mass"])):
    if abs(obt - esp) > 1e-9:
        raise SystemExit("ABORTA: %s recomputado %.12f != publicado %.12f — la "
                         "reconstruccion no es la sellada" % (nombre, obt, esp))

out = {
    "file_id": "RQ-DIST-IDEAL-KRAS-001",
    "que_es": "distribucion por nodo de la CTQW de KRAS_G12C en el subespacio de una "
              "excitacion: la exacta exp(-iHt) y la Trotter ideal sin ruido (r=%d), que "
              "es el circuito que se envio a hardware. Publicada para que la errata de "
              "RQ-POC-QPU-001 sea comprobable por un tercero." % r,
    "producido_por": {"script": "ideal_ctqw_kras.py", "sha256": "sha256:" + sha(__file__),
                      "harness": "poc_ibm.py", "harness_sha256": "sha256:" + sha(HARNESS),
                      "insumo": "cache/KRAS_G12C.pkl", "insumo_sha256": "sha256:" + sha(CACHE)},
    "entorno": {"numpy": np.__version__, "python": sys.version.split()[0],
                "shim_de_pickle": _SHIM},
    "parametros": {"WIN_T": P.WIN_T, "NQ": P.NQ, "trotter_r": r,
                   "source_nodes": src, "pocket_nodes": sorted(allo)},
    "subgraph_node_ids": [int(x) for x in idx],
    # EL INSUMO VIAJA EN EL ARTEFACTO, no por referencia a un archivo privado.
    # El pickle del que sale esto vive en `quantum-run`, que es un repositorio PRIVADO, y
    # ademas solo carga con numpy 2.x (con 1.x revienta con `No module named
    # numpy._core`). O sea: la receta "corra este script" no la podia cumplir nadie de
    # afuera, ni con el script en la mano. Publicando la matriz y el potencial en JSON, la
    # verificacion deja de depender del repo cerrado Y de la version de numpy.
    "subgrafo_portable": {
        "que_es": "todo lo que hace falta para recomputar sin el pickle: la adyacencia "
                  "pesada del sub-grafo (W), el potencial on-site (v) y la fuente. "
                  "H = W + diag(v); psi0 = |fuente>; psi(t) = exp(-i H t) psi0.",
        "W": [[round(float(x), 12) for x in fila] for fila in W],
        "v": [round(float(x), 12) for x in v],
        "source_nodes": src, "t": P.WIN_T,
    },
    "convencion_de_bits": "nodo i = qubit i = bit clasico i. En una cadena de conteos de "
                          "qiskit el caracter mas a la izquierda es el bit MAS ALTO, asi "
                          "que el indice del nodo se lee invirtiendo la cadena "
                          "(b[::-1].index('1')), igual que counts_to_p1 e ideal_probs.",
    "dist_exacta_por_nodo": [round(float(x), 8) for x in exact],
    "dist_ideal_trotter_por_nodo": [round(float(x), 8) for x in ideal],
    "masa_bolsillo_exacta": me, "masa_bolsillo_ideal_trotter": mi,
    "validado_contra": {"archivo": "poc_result_KRAS_G12C@68aada40.json",
                        "sha256": "sha256:" + sha(PUBLICADO),
                        "reproduce": ["exact_pocket_mass", "ideal_pocket_mass"],
                        "tolerancia": 1e-9},
    "NO_afirma": "nada sobre hardware. Es la prediccion sin ruido; la comparacion contra "
                 "lo medido vive en la errata.",
}
# FALLA CERRADO: lo publicado tiene que bastar. Se recomputa la distribucion exacta
# usando SOLO los numeros que van dentro del artefacto —sin tocar el pickle ni el
# harness— y tiene que dar lo mismo. Si no, el artefacto promete una verificacion que no
# se puede hacer con lo que trae, que es el defecto que vino a arreglar.
from scipy.linalg import expm as _expm
_W = np.array(out["subgrafo_portable"]["W"], float)
_v = np.array(out["subgrafo_portable"]["v"], float)
_psi0 = np.zeros(len(_v), complex); _psi0[out["subgrafo_portable"]["source_nodes"][0]] = 1.0
_psi = _expm(-1j * (_W + np.diag(_v)) * out["subgrafo_portable"]["t"]) @ _psi0
_rec = np.abs(_psi) ** 2; _rec /= _rec.sum()
_dif = float(np.max(np.abs(_rec - exact)))
if _dif > 1e-9:
    raise SystemExit("ABORTA: recomputar desde el JSON publicado difiere del calculo "
                     "original en %.2e — lo publicado no basta para verificar" % _dif)
out["verificable_sin_el_pickle"] = {
    "comprobado": True, "max_diferencia": _dif,
    "como": "reconstruir H = W + diag(v) desde `subgrafo_portable`, exponenciar y "
            "normalizar sobre el subespacio de una excitacion; da `dist_exacta_por_nodo`.",
}

dst = os.path.join(RAIZ, "evidence-staging", "dist_ideal_KRAS_G12C.json")
json.dump(out, open(dst, "w"), indent=1, ensure_ascii=False)
print("emitido:", os.path.basename(dst))
print("  reprodujo exact=%.12f  ideal=%.12f" % (me, mi))
print("  sha256:", sha(dst)[:16])
