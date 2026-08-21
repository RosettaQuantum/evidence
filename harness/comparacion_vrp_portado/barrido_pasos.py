"""Cuanto depende el resultado del brazo cuantico del NUMERO DE PASOS que alcanzo a dar.

Es el mismo archivo, la misma instancia y la misma semilla: lo unico que cambia es cuantos
pasos de Adam permitio el reloj. El artefacto de hoy NO registra ese numero.
"""
import os, sys, json
os.environ.update(RQ_NODOS="8", RQ_CAMIONES="2", RQ_CAPACIDAD="60", RQ_SEED="42")
sys.path.insert(0, "/Users/nicholasiakl/Documents/Claude/Projects/Rosetta Quantum/evidence/harness")
import numpy as np, importlib
M = importlib.import_module("vrp_harness")
import time as _t
real = _t.time

class Reloj:
    def __init__(self, n): self.n, self.c = n, 0
    def __call__(self):
        self.c += 1
        return 0.0 if self.c <= self.n + 1 else 1e9

for pasos in [6, 8, 10, 12, 14, 16, 18, 20, 24]:
    M.time.time = real
    M.rng = np.random.default_rng(42)
    coords, demanda, D = M.construir_instancia()
    M.costo_bajo_incertidumbre([[0,6,3,5,0],[0,7,4,2,1,0]], D)
    M.costo_bajo_incertidumbre([[0,6,3,5,0],[0,1,2,4,7,0]], D)
    M.time.time = Reloj(pasos)
    r = M.brazo_cuantico(D, demanda, 20.0)
    print("%3d pasos -> value=%-10s estado=%s" % (pasos, r["value"], r["estado"]), flush=True)
