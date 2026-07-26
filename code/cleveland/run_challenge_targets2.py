"""
Parte 2: miosina cardiaca y c-Myc.

MIOSINA — correccion documentada al conjunto de validacion.
  La Tabla 1 del reto indica 5TBY (entrada) -> 6C1H (validacion) para el sitio de
  mavacamten. 6C1H NO CONTIENE MAVACAMTEN: sus unicos heteroatomos son ADP y Mg
  (es una estructura crio-EM de miosina unida a actina, Mentes et al.). Con esa
  pareja el sitio alosterico no puede leerse geometricamente del farmaco.
  Estructuras de mavacamten (ligando XB2) verificadas en el PDB hoy: 8QYP/8QYQ/
  8QYR/9GZ1/9GZ2/9GZ3/9YP9/9YR7. Usamos 9GZ1 (motivo de cabezas interactuantes con
  mavacamten), que es el mismo estado conformacional que 5TBY modela, y corroboramos
  el sitio contra 8QYR de forma independiente.
"""
import json, sys, numpy as np, prody
sys.path.insert(0, "/home/claude/rosettaq")
from allo_challenge import *
from run_challenge_targets import evaluate, map_gt, resname_map, RS

results = {}

# ---- 3. MIOSINA CARDIACA: 5TBY (modelo IHM, sin nucleotido) -> 9GZ1 (mavacamten XB2)
print("== MIOSINA  5TBY -> 9GZ1 (correccion documentada de 6C1H)")
apo = load("5TBY"); holo = load("9GZ1")
sel = "protein and name CA and chain A"
ca = apo.select(sel)
seq = ca.getSequence(); resn = [int(r) for r in ca.getResnums()]
# fuente = lazo P (motivo Walker-A GESGAGKT), hallado por busqueda de secuencia
motif = "GESGAGKT"
pos = seq.find(motif)
if pos < 0:
    for m in ("GESGAGKS", "GAGKT"):
        pos = seq.find(m)
        if pos >= 0:
            motif = m; break
assert pos >= 0, "no se hallo el motivo Walker-A"
src = [("A", resn[i]) for i in range(pos, pos + len(motif))]
print("   motivo %s hallado en residuos %d-%d" % (motif, src[0][1], src[-1][1]))
gt, dropped = map_gt(holo, "resname XB2", "protein", apo, sel, "A")
print("   fuente(lazo P) n=%d  |  GT(mavacamten) n=%d  descartados=%d"
      % (len(src), len(gt), len(dropped)))
# corroboracion independiente contra 8QYR
h2 = load("8QYR")
gt2, _ = map_gt(h2, "resname XB2", "protein", apo, sel, "A")
overlap = len(set(gt) & set(gt2))
print("   corroboracion 8QYR: n=%d, solapamiento con 9GZ1 = %d" % (len(gt2), overlap))

rows, sites = evaluate(apo, sel, "A", src, gt, "MIOSINA", None)
results["CARDIAC_MYOSIN"] = dict(
    apo="5TBY", holo="9GZ1", chain="A",
    challenge_table_holo="6C1H",
    deviation_note="6C1H no contiene mavacamten (solo ADP+Mg). Se sustituye por 9GZ1 "
                   "(mismo estado IHM, ligando XB2=mavacamten) y se corrobora con 8QYR.",
    apo_note="5TBY es un MODELO POR HOMOLOGIA (SWISS-MODEL a partir del homologo de "
             "tarantula), no una estructura experimental; la topologia de entrada hereda "
             "el error del modelo.",
    source_residues=[list(x) for x in src],
    gt_residues=[list(x) for x in gt],
    gt_corroboration_8QYR=[list(x) for x in gt2],
    gt_overlap_9GZ1_8QYR=overlap,
    gt_dropped_numbering_mismatch=dropped,
    source_method="lazo P / motivo Walker-A %s localizado por busqueda de secuencia" % motif,
    gt_method="residuos <4.5A de mavacamten (XB2) en 9GZ1, mapeados por numero con identidad verificada",
    rows=rows, sites=sites)

# ---- 4. c-MYC: 1NKP, sin verdad de referencia (declarado por el reto)
print("== c-MYC  1NKP (sin ground truth; solo prediccion)")
apo = load("1NKP")
sel = "protein and name CA and (chain A or chain B)"
src = contacts(apo, "nucleic", sel)
print("   fuente(contactos con el ADN) n=%d" % len(src))
rows, sites = evaluate(apo, sel, None, src, [], "cMYC", None)
results["c_MYC"] = dict(apo="1NKP", holo=None, chain="A+B",
                        source_residues=[list(x) for x in src],
                        gt_residues=[],
                        source_method="residuos de Myc/Max a <4.5A del ADN co-cristalizado "
                                      "(sitio funcional; no hay sitio activo enzimatico)",
                        gt_method="NO EXISTE: el reto declara que c-Myc se evalua por consenso "
                                  "entre equipos y viabilidad de docking. Prediccion sellada "
                                  "y fechada ANTES de conocer el consenso.",
                        rows=rows, sites=sites)

json.dump(results, open("/home/claude/rosettaq/challenge_results_part2.json", "w"),
          indent=1, ensure_ascii=False)
print("\nparte 2 guardada")
