#!/usr/bin/env python3
"""Puntuacion de las predicciones ciegas contra los bolsillos validados (DESCIEGA).

Este script ABRE LAS HOLO. Correrlo es cruzar la linea: las predicciones quedaron
comprometidas en git (commit 4cfac34, posterior al metrico 407fa7b) y lo que salga de
aqui se publica igual — acierto o negativo. No hay tercera opcion.

VERDAD DE TERRENO — convenciones selladas del motor, declaradas antes de correr:
  - bolsillo validado = residuos de proteina con algun atomo a < 4.5 A del farmaco
    co-cristalizado (GT_RADIUS del motor), en la cadena del farmaco.
  - farmacos, verificados contra RCSB (titulos y HETATM, 2026-08-10):
      KRAS    6OIM  MOV = sotorasib (AMG 510)
      ABL1    5MO4  AY7 = asciminib  (NIL = nilotinib se EXCLUYE: marca el sitio ATP,
                    que es nuestra fuente, no el bolsillo alosterico)
      MIOSINA 9GZ1  XB2 = mavacamten — NO 6C1H: la Tabla 1 del challenge cita 6C1H
                    pero esa estructura solo contiene ADP/Mg (errata publica
                    2026-07-28 en evidence/NOTES; sustitucion pre-registrada en
                    PR-CLEV-001 y usada por EXP-0007-015)
  - mapeo holo->apo por numero de residuo en la cadena del cache; la cobertura del
    mapeo se reporta como denominador (bolsillo de N residuos, M presentes en la red).
  - c-Myc queda FUERA del scoring y se declara: no existe bolsillo validado publicado.

METRICAS (las tres, decididas antes de mirar nada):
  1. rank_acierto: el rank del primer sitio predicho (top-5) con >=1 residuo dentro
     del bolsillo validado. Ademas, distancia minima (A) de cada sitio al bolsillo.
  2. percentil_bolsillo: percentil promedio de los residuos del bolsillo en el score
     entre distales — comparable con la serie historica del motor (V-0012: -18.01).
  3. p_permutacion: 2000 parches CONTIGUOS aleatorios (BFS espacial sobre la red,
     mismo tamano que el bolsillo mapeado, solo distales, semilla 20260810);
     p = fraccion de parches con score promedio >= el del bolsillo. Parches contiguos
     y no residuos sueltos: un bolsillo es un parche, compararlo contra confeti seria
     inflar la significancia.

Uso:  python3 score_predictions.py     # escribe scoring/RESULTADO.json y lo imprime
"""
import glob, gzip, hashlib, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EST = os.path.join(HERE, "structures")
GT_RADIUS = 4.5
SEED = 20260810
NPERM = 2000

VALIDACION = {
    "KRAS_4OBE":   {"holo": "6oim", "chain": "A", "drug": "MOV", "nombre": "sotorasib"},
    "ABL1_1OPL":   {"holo": "5mo4", "chain": "A", "drug": "AY7", "nombre": "asciminib"},
    "MYOSIN_5TBY": {"holo": "9gz1", "chain": "A", "drug": "XB2", "nombre": "mavacamten",
                    "nota": "9GZ1 y no 6C1H — errata publica 2026-07-28, sustitucion "
                            "pre-registrada en PR-CLEV-001"},
}
AA3 = {"ALA","ARG","ASN","ASP","CYS","GLN","GLU","GLY","HIS","ILE","LEU","LYS","MET",
       "PHE","PRO","SER","THR","TRP","TYR","VAL","MSE"}


def atomos(pid):
    out = []
    in_model = 0
    for l in gzip.open(os.path.join(EST, pid + ".pdb.gz"), "rt", encoding="latin1"):
        if l.startswith("MODEL"):
            in_model += 1
            if in_model > 1:
                break
        if l.startswith(("ATOM", "HETATM")) and l[16] in (" ", "A"):
            out.append((l[:6].strip(), l[17:20].strip(), l[21], int(l[22:26]),
                        np.array([float(l[30:38]), float(l[38:46]), float(l[46:54])])))
    return out


def bolsillo_validado(holo, chain, drug):
    ats = atomos(holo)
    L = np.vstack([x for reg, res, c, rn, x in ats if reg == "HETATM" and res == drug and c == chain])
    prot = [(rn, x) for reg, res, c, rn, x in ats if reg == "ATOM" and c == chain and res in AA3]
    P = np.vstack([x for _, x in prot])
    dmin = np.linalg.norm(P[:, None, :] - L[None, :, :], axis=-1).min(axis=1)
    return sorted({rn for (rn, _), dm in zip(prot, dmin) if dm < GT_RADIUS})


def parche_contiguo(A, semillas_rng, distal_set, tam):
    """Parche contiguo por BFS desde un residuo distal aleatorio, restringido a distales."""
    inicio = semillas_rng.choice(sorted(distal_set))
    parche = {int(inicio)}; frontera = [int(inicio)]
    while len(parche) < tam and frontera:
        u = frontera.pop(0)
        vecinos = [int(v) for v in np.nonzero(A[u])[0] if int(v) in distal_set and int(v) not in parche]
        semillas_rng.shuffle(vecinos)
        for v in vecinos:
            if len(parche) >= tam:
                break
            parche.add(v); frontera.append(v)
    return parche if len(parche) == tam else None


def puntuar(target, val):
    import build_cache as BC
    d = BC.load(target)
    pred = json.load(open(os.path.join(HERE, "predictions_blind", target + ".prediction.json")))
    # score por residuo: reconstruir desde la matriz comprometida (no recalcular)
    npz = np.load(os.path.join(HERE, "predictions_blind", pred["matriz_conectividad"]["archivo"]))
    C = npz["C"]; src = d["src"]
    score = C[:, src].mean(axis=1)

    gt_holo = bolsillo_validado(val["holo"], val["chain"], val["drug"])
    resnum2idx = {rn: i for i, (c, rn) in enumerate(d["ids"])}
    gt_idx = [resnum2idx[rn] for rn in gt_holo if rn in resnum2idx]
    gt_set = set(gt_idx)

    # metrica 1: rank del primer sitio que toca el bolsillo + distancia de cada sitio
    sitios = pred["sitios_predichos_top5"]
    rank_hit, detalle_sitios = None, []
    for s in sitios:
        idxs = [resnum2idx[r["resnum"]] for r in s["residuos"] if r["resnum"] in resnum2idx]
        overlap = len(set(idxs) & gt_set)
        dmin = float(np.linalg.norm(
            d["coords"][idxs][:, None, :] - d["coords"][gt_idx][None, :, :], axis=-1).min()) if idxs and gt_idx else None
        detalle_sitios.append({"rank": s["rank"], "overlap_residuos": overlap,
                               "dist_min_al_bolsillo_A": round(dmin, 2) if dmin is not None else None})
        if overlap and rank_hit is None:
            rank_hit = s["rank"]

    # metrica 2: percentil promedio del bolsillo entre distales
    distal = np.where(d["mask"])[0]
    orden = {int(i): 100.0 * k / max(1, len(distal) - 1)
             for k, i in enumerate(distal[np.argsort(score[distal])])}
    pct = float(np.mean([orden[i] for i in gt_idx if i in orden])) if gt_idx else None

    # metrica 3: p por permutacion con parches contiguos
    rng = np.random.default_rng(SEED)
    distal_set = set(int(i) for i in distal)
    gt_en_distal = [i for i in gt_idx if i in distal_set]
    media_gt = float(score[gt_en_distal].mean()) if gt_en_distal else None
    p = None; hechos = 0
    if media_gt is not None and len(gt_en_distal) >= 2:
        peores = 0
        for _ in range(NPERM * 3):
            if hechos >= NPERM:
                break
            parche = parche_contiguo(d["A"], rng, distal_set, len(gt_en_distal))
            if parche is None:
                continue
            hechos += 1
            if float(score[sorted(parche)].mean()) >= media_gt:
                peores += 1
        p = (peores + 1) / (hechos + 1) if hechos else None

    return {
        "target": target, "farmaco": "%s (%s, %s)" % (val["drug"], val["nombre"], val["holo"].upper()),
        "nota": val.get("nota"),
        "bolsillo_validado": {"residuos_holo": len(gt_holo), "mapeados_en_red": len(gt_idx),
                              "en_distal": len(gt_en_distal), "resnums": gt_holo},
        "rank_primer_sitio_que_acierta": rank_hit,
        "sitios": detalle_sitios,
        "percentil_bolsillo_entre_distales": round(pct, 2) if pct is not None else None,
        "p_permutacion_parches_contiguos": round(p, 4) if p is not None else None,
        "n_permutaciones_efectivas": hechos,
    }


if __name__ == "__main__":
    resultados = {"_doc": "Scoring de las predicciones ciegas (4cfac34) contra bolsillos "
                          "validados. c-Myc excluido: sin bolsillo validado publicado. "
                          "Se publica tal cual salga.",
                  "seed": SEED, "targets": {}}
    for target, val in VALIDACION.items():
        r = puntuar(target, val)
        resultados["targets"][target] = r
        print("%-14s bolsillo %d/%d en red · rank acierto: %s · percentil: %s · p=%s (n=%d)" % (
            target, r["bolsillo_validado"]["mapeados_en_red"], r["bolsillo_validado"]["residuos_holo"],
            r["rank_primer_sitio_que_acierta"], r["percentil_bolsillo_entre_distales"],
            r["p_permutacion_parches_contiguos"], r["n_permutaciones_efectivas"]))
        for s in r["sitios"]:
            print("    sitio %d: overlap=%d, dist_min=%s A" % (s["rank"], s["overlap_residuos"], s["dist_min_al_bolsillo_A"]))
    os.makedirs(os.path.join(HERE, "scoring"), exist_ok=True)
    out = os.path.join(HERE, "scoring", "RESULTADO.json")
    json.dump(resultados, open(out, "w"), indent=1, ensure_ascii=False)
    print("\nescrito scoring/RESULTADO.json — se publica tal cual, acierto o negativo.")
