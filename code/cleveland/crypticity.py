"""
La medicion que explica el fallo: cuanto se MUEVE el bolsillo alosterico entre la
estructura apo (entrada) y la holo (arbitro). Si el bolsillo se CREA al unirse el
farmaco en vez de estar presente y oculto, entonces ninguna funcion de la topologia
de la apo puede contenerlo, y el fallo de todos los propagadores no es de metodo:
es de informacion en la entrada.

Se superponen apo y holo por los Ca comunes (superposicion global, minimos cuadrados)
y se mide el desplazamiento por residuo. Se compara el sitio alosterico contra el
resto de la proteina.
"""
import json, sys, numpy as np, prody
prody.confProDy(verbosity='none')

PAIRS = [("KRAS_G12C", "4OBE", "A", "6OIM", "A", "resname MOV"),
         ("BCR_ABL1", "1OPL", "A", "5MO4", "A", "resname AY7")]

res = {}
for name, ap, ach, ho, hch, lig in PAIRS:
    a = prody.parsePDB("/tmp/%s.pdb.gz" % ap.lower())
    h = prody.parsePDB("/tmp/%s.pdb.gz" % ho.lower())
    ca_a = a.select("protein and name CA and chain %s" % ach)
    ca_h = h.select("protein and name CA and chain %s" % hch)
    ma = {int(r): (c, n) for r, c, n in
          zip(ca_a.getResnums(), ca_a.getCoords(), ca_a.getResnames())}
    mh = {int(r): (c, n) for r, c, n in
          zip(ca_h.getResnums(), ca_h.getCoords(), ca_h.getResnames())}
    common = sorted(r for r in ma if r in mh and ma[r][1] == mh[r][1])
    X = np.array([ma[r][0] for r in common])
    Y = np.array([mh[r][0] for r in common])

    # superposicion de Kabsch
    Xc, Yc = X - X.mean(0), Y - Y.mean(0)
    U, S, Vt = np.linalg.svd(Xc.T @ Yc)
    d = np.sign(np.linalg.det(U @ Vt))
    R = U @ np.diag([1, 1, d]) @ Vt
    disp = np.linalg.norm(Xc @ R - Yc, axis=1)

    gt = h.select("protein and name CA and chain %s and same residue as "
                  "(within 4.5 of (%s))" % (hch, lig))
    gtres = set(int(r) for r in gt.getResnums()) if gt is not None else set()
    idx_gt = [i for i, r in enumerate(common) if r in gtres]
    idx_rest = [i for i in range(len(common)) if i not in set(idx_gt)]

    r_ = {"n_comunes": len(common), "rmsd_global": round(float(np.sqrt((disp**2).mean())), 2),
          "desplazamiento_medio_sitio": round(float(disp[idx_gt].mean()), 2),
          "desplazamiento_mediano_sitio": round(float(np.median(disp[idx_gt])), 2),
          "desplazamiento_medio_resto": round(float(disp[idx_rest].mean()), 2),
          "desplazamiento_mediano_resto": round(float(np.median(disp[idx_rest])), 2),
          "razon_sitio_vs_resto": round(float(disp[idx_gt].mean() / disp[idx_rest].mean()), 2),
          "percentil_del_sitio_en_desplazamiento": round(float(
              100.0 * (disp[idx_rest] < disp[idx_gt].mean()).mean()), 1),
          "n_residuos_sitio_comunes": len(idx_gt)}

    # cuantos contactos NUEVOS aparecen en el sitio al pasar de apo a holo
    def ncontacts(coords, sel_idx, cutoff=8.5):
        D = np.linalg.norm(coords[:, None] - coords[None, :], axis=-1)
        return float(((D[sel_idx] < cutoff) & (D[sel_idx] > 0)).sum())
    r_["contactos_sitio_apo"] = ncontacts(X, idx_gt)
    r_["contactos_sitio_holo"] = ncontacts(Y, idx_gt)
    res[name] = r_
    print("==", name, ap, "->", ho)
    for k, v in r_.items():
        print("   %-42s %s" % (k, v))

json.dump(res, open("/home/claude/rosettaq/crypticity.json", "w"), indent=1, ensure_ascii=False)
