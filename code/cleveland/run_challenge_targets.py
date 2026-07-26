"""
Driver: corre la suite Cleveland sobre el CONJUNTO OFICIAL de validacion.
Rejilla congelada (PR-CLEV-001). Ningun parametro se ajusta por proteina.
"""
import json, sys, numpy as np, prody, datetime
sys.path.insert(0, "/home/claude/rosettaq")
from allo_challenge import *

RS = np.random.RandomState(0)
AA3 = prody.atomic.flags.__dict__  # no usado; identidad se compara por getResnames


def resname_map(atoms, sel):
    ca = atoms.select(sel)
    return {(c, int(r)): rn for c, r, rn in
            zip(ca.getChids(), ca.getResnums(), ca.getResnames())}


def map_gt(holo, holo_lig, holo_protsel, apo, apo_sel, apo_chain):
    """Contactos del farmaco en holo -> residuos de la apo, por numero,
    EXIGIENDO identidad de tipo de residuo. Devuelve (mapeados, descartados)."""
    gt = contacts(holo, holo_lig, holo_protsel)
    hmap = resname_map(holo, holo_protsel + " and name CA")
    amap = resname_map(apo, apo_sel)
    keep, drop = [], []
    for (ch, rn) in gt:
        tgt = (apo_chain, rn)
        if tgt in amap and amap[tgt] == hmap.get((ch, rn)):
            keep.append(tgt)
        else:
            drop.append([ch, rn, hmap.get((ch, rn)), amap.get(tgt)])
    return sorted(set(keep)), drop


def evaluate(apo, apo_sel, apo_chain, src_res, gt_res, label, notes):
    rows = []
    per_config_sites = {}
    for cutoff in CUTOFFS:
        A, ids, coords, seq, D = ca_network(apo, apo_sel, cutoff)
        src = idx_of(ids, src_res)
        allo = idx_of(ids, gt_res) if gt_res else []
        if not src:
            raise SystemExit("fuente no hallada en %s" % label)
        dmin = D[:, src].min(axis=1)
        mask = dmin > DISTAL_A
        n_allo_distal = sum(1 for a in allo if mask[a])

        # lineas base independientes de la ventana temporal
        gnm = gnm_score(A, src)
        btw, close = betweenness_closeness(A, src)
        anm = anm_score(coords, src) if len(ids) <= 1200 else None
        rnd = RS.rand(len(ids))

        for (tlo, thi) in WINDOWS:
            P, _, _ = props(A, src, tlo, thi)
            scores = {"ctqw": P["ctqw"][0], "diffusion": P["diffusion"][0],
                      "gnm": gnm, "betweenness": btw, "closeness": close,
                      "random": rnd}
            if anm is not None:
                scores["anm"] = anm
            row = {"cutoff": cutoff, "window": [tlo, thi], "n_nodes": len(ids),
                   "n_source": len(src), "n_allo": len(allo),
                   "n_allo_distal": n_allo_distal, "n_distal": int(mask.sum()),
                   "runtime_ctqw_s": P["ctqw"][1],
                   "runtime_diffusion_s": P["diffusion"][1]}
            for k, v in scores.items():
                row[k + "_pct"] = round(percentile(v, allo, mask), 2) if allo else None
                if allo:
                    h5, _ = topk_hits(v, allo, mask, 5)
                    h10, _ = topk_hits(v, allo, mask, 10)
                    row[k + "_top5"] = h5
                    row[k + "_top10"] = h10
            rows.append(row)
            key = "c%.1f_w%.1f-%.1f" % (cutoff, tlo, thi)
            per_config_sites[key] = {
                m: cluster_sites(scores[m], mask, coords, ids)
                for m in ("ctqw", "diffusion", "gnm")
            }
            print("  %s cut=%.1f w=%s n=%d  CTQW=%s  diff=%s  gnm=%s  btw=%s"
                  % (label, cutoff, (tlo, thi), len(ids), row.get("ctqw_pct"),
                     row.get("diffusion_pct"), row.get("gnm_pct"),
                     row.get("betweenness_pct")))
    return rows, per_config_sites


# =============================================================== TARGETS
results = {}

# ---- 1. KRAS G12C: 4OBE (GDP-bound apo) -> 6OIM (AMG 510 / sotorasib)
print("== KRAS G12C  4OBE -> 6OIM")
apo = load("4OBE"); holo = load("6OIM")
sel = "protein and name CA and chain A"
src = contacts(apo, "(resname GDP or resname MG) and chain A",
               "protein and name CA and chain A")
gt, dropped = map_gt(holo, "resname MOV", "protein", apo, sel, "A")
print("   fuente(GDP/Mg) n=%d  |  GT(sotorasib) n=%d  descartados=%d"
      % (len(src), len(gt), len(dropped)))
rows, sites = evaluate(apo, sel, "A", src, gt, "KRAS", None)
results["KRAS_G12C"] = dict(apo="4OBE", holo="6OIM", chain="A",
                            source_residues=[list(x) for x in src],
                            gt_residues=[list(x) for x in gt],
                            gt_dropped_numbering_mismatch=dropped,
                            source_method="residuos <4.5A del GDP+Mg co-cristalizado en la apo",
                            gt_method="residuos <4.5A de AMG 510 (MOV) en 6OIM, mapeados por numero con identidad de tipo verificada",
                            rows=rows, sites=sites)

# ---- 2. BCR-ABL1: 1OPL (auto-inhibida) -> 5MO4 (asciminib AY7)
print("== BCR-ABL1  1OPL -> 5MO4")
apo = load("1OPL"); holo = load("5MO4")
sel = "protein and name CA and chain A"
src = contacts(apo, "resname P16 and chain A", "protein and name CA and chain A")
gt, dropped = map_gt(holo, "resname AY7", "protein", apo, sel, "A")
print("   fuente(sitio ATP) n=%d  |  GT(asciminib) n=%d  descartados=%d"
      % (len(src), len(gt), len(dropped)))
rows, sites = evaluate(apo, sel, "A", src, gt, "ABL1", None)
results["BCR_ABL1"] = dict(apo="1OPL", holo="5MO4", chain="A",
                           source_residues=[list(x) for x in src],
                           gt_residues=[list(x) for x in gt],
                           gt_dropped_numbering_mismatch=dropped,
                           source_method="residuos <4.5A del inhibidor de sitio ATP (P16) co-cristalizado en 1OPL",
                           gt_method="residuos <4.5A de asciminib (AY7) en 5MO4, mapeados por numero con identidad verificada",
                           caveat="1OPL tiene acido miristico (MYR) ocupando el bolsillo miristoilo: la conformacion de entrada NO es ciega respecto del sitio a predecir. Se declara; ver corrida de control sin MYR.",
                           rows=rows, sites=sites)

json.dump(results, open("/home/claude/rosettaq/challenge_results_part1.json", "w"),
          indent=1, ensure_ascii=False)
print("\nparte 1 guardada")
