"""Comparacion DETERMINISTA del brazo cuantico: original vs portado, con reloj falso.

El bucle del QAOA es `while time.time()-t0 < segundos*0.8`: cuantos pasos da depende de
lo cargada que este la maquina, asi que dos corridas del MISMO archivo pueden diferir.
Con un reloj falso los dos dan EXACTAMENTE los mismos pasos y la comparacion mide el
codigo, no el reloj.
"""
import os, sys, json
os.environ.update(RQ_NODOS="8", RQ_CAMIONES="2", RQ_CAPACIDAD="60", RQ_SEED="42")
sys.path.insert(0, "/Users/nicholasiakl/Documents/Claude/Projects/Rosetta Quantum/evidence/harness")
import numpy as np

PASOS = int(sys.argv[1]) if len(sys.argv) > 1 else 12

class Reloj:
    """Devuelve 0.0 las primeras PASOS+1 llamadas y despues salta: N pasos exactos."""
    def __init__(self, n): self.n, self.c = n, 0
    def __call__(self):
        self.c += 1
        return 0.0 if self.c <= self.n + 1 else 1e9

def corre(nombre):
    import importlib
    M = importlib.import_module(nombre)
    M.rng = np.random.default_rng(42)
    coords, demanda, D = M.construir_instancia()
    # se consume el azar en el MISMO orden que la corrida real: dos evaluaciones bajo
    # incertidumbre antes del brazo cuantico
    M.costo_bajo_incertidumbre([[0,6,3,5,0],[0,7,4,2,1,0]], D)
    M.costo_bajo_incertidumbre([[0,6,3,5,0],[0,1,2,4,7,0]], D)
    rel = Reloj(PASOS)
    M.time.time = rel
    if nombre == "vrp_harness":
        r = M.brazo_cuantico(D, demanda, 20.0)
    else:
        r = M.brazo_cuantico({"D": D, "demanda": demanda, "segundos": 20.0})
    r["_llamadas_al_reloj"] = rel.c
    return r

a = corre("vrp_harness")
b = corre("vrp_experimento")
comunes = sorted(set(a) & set(b))
print("pasos fijados:", PASOS)
print("campos comunes:", len(comunes), "| solo en portado:", sorted(set(b) - set(a)))
iguales = [k for k in comunes if json.dumps(a[k], default=str) == json.dumps(b[k], default=str)]
print("iguales:", len(iguales), "de", len(comunes))
for k in comunes:
    if k not in iguales:
        print("  DIFIERE", k, "->", repr(a[k])[:70], "|", repr(b[k])[:70])
print("\noriginal:", json.dumps({k: a[k] for k in comunes}, default=str)[:400])
