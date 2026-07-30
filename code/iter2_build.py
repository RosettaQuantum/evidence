"""Iteracion 2 — Stage 1: construye y cachea por proteina {A, coords, ids, features,
src, allo, mask}. Fuente (sitio activo) CURADA por familia, no auto-detectada.
Resumible: si el cache existe, se salta. Correr por lotes para no chocar el timeout."""
import sys, os, re, json, pickle, numpy as np, prody
prody.confProDy(verbosity='none'); sys.path.insert(0,'.')
from allo_challenge import ca_network, contacts, idx_of, DISTAL_A
from sigo_features import build_feature_table, load_pdb

CACHE = "/home/claude/rosettaq/iter2_cache"
os.makedirs(CACHE, exist_ok=True)

# Fuente CURADA por proteina: ('lig', selector) contactos con ligando/cofactor natural,
# o ('motif', patron_regex) residuos del motivo catalitico por secuencia.
SRC = {
 'KRAS_G12C':     ('lig',  '(resname GDP or resname MG)'),
 'BCR_ABL1':      ('lig',  'resname P16'),                 # inhibidor de sitio ATP en 1OPL
 'CARDIAC_MYOSIN':('motif', r'GESGAGK'),                   # Walker-A (lazo P), NO kinasa
 'SHP2_PTPN11':   ('motif', r'HC.{5}R'),                   # PTP: Cys catalitica (CX5R)
 'PTP1B':         ('motif', r'HC.{5}R'),
 'IDH1_R132H':    ('lig',  'resname NDP'),                 # NADP (sitio activo)
 'IDH2':          ('lig',  'resname NDP'),
 'MEK1':          ('motif', r'HRD[LIVM]K'),                # kinasa: lazo catalitico HRD
 'AKT1':          ('motif', r'DFG'),
 'PKM2':          ('motif', r'GG.{1,3}[KR].{5,20}D'),      # PK: se refina abajo; fallback Mg
 'GLS':           ('motif', r'[ST].K.{2}[ILV].{2,4}[ST]'), # glutaminasa: dificil; ver fallback
 'PDK1_PDPK1':    ('motif', r'HRD[LIVM]K'),
 'CASP3':         ('motif', r'QAC.G'),                     # caspasa: Cys catalitica
 'HIV1_RT':       ('motif', r'YMDD'),                      # RT: aspartatos cataliticos YMDD
 'P38A_MAPK':     ('motif', r'HRD[LIVM]K'),
 'HEMOGLOBIN_B':  ('lig',  'resname HEM'),
}
# fallback si el motivo no aparece o da <3: contactos con Mg (metal catalitico)
FALLBACK_MG = {'PKM2','GLS','MEK1','KRAS_G12C'}

def get_src(apo, name, ch):
    sel = "protein and name CA and chain %s" % ch
    ca = apo.select(sel); rn = [int(x) for x in ca.getResnums()]
    _, ids, _, seq, _ = ca_network(apo, sel, 8.5); idset = set(ids)
    kind, pat = SRC[name]
    src = []
    if kind == 'lig':
        c = contacts(apo, "(%s) and chain %s" % (pat, ch), sel)
        src = [(ch, r) for (cc, r) in c if (ch, r) in idset]
        method = "cofactor/nucleotido: %s" % pat
    else:
        m = re.search(pat, seq)
        if m:
            idxs = range(m.start(), m.end())
            src = [(ch, rn[i]) for i in idxs if i < len(rn)]
            method = "motivo %s @seq[%d:%d]" % (pat, m.start(), m.end())
        else:
            method = "motivo %s NO hallado" % pat
    if len(src) < 3 and name in FALLBACK_MG:
        c = contacts(apo, "resname MG and chain %s" % ch, sel)
        src = [(ch, r) for (cc, r) in c if (ch, r) in idset]
        method = "fallback Mg (metal catalitico)"
    return sorted(set(src)), method

def build(name, m):
    apo = load_pdb(m['apo']); ch = m['chain']
    src_res, method = get_src(apo, name, ch)
    if len(src_res) < 3:
        return None, "SIN FUENTE LIMPIA (%s)" % method
    ft = build_feature_table(m, cutoff=8.5)
    A, ids, coords, feats = ft["A"], ft["ids"], ft["coords"], ft["features"]
    src = idx_of(ids, src_res)
    holo = load_pdb(m['holo'])
    gt = [(ch, r) for (c, r) in contacts(holo, "resname %s" % m['gt_ligand'], "protein")]
    allo = idx_of(ids, gt)
    if len(allo) < 5 or not src:
        return None, "GT<5 o src vacio"
    D = np.linalg.norm(coords[:, None, :]-coords[src][None, :, :], axis=-1)
    mask = D.min(axis=1) > DISTAL_A
    obj = {"name": name, "ids": ids, "coords": coords, "A": A, "features": feats,
           "src": src, "allo": allo, "mask": mask, "src_method": method,
           "n": len(ids), "n_distal": int(mask.sum()), "k": int(sum(mask[a] for a in allo))}
    pickle.dump(obj, open("%s/%s.pkl" % (CACHE, name), "wb"))
    return obj, "OK src=%d(%s) allo=%d distal=%d k=%d" % (len(src), method[:22], len(allo), obj["n_distal"], obj["k"])

if __name__ == "__main__":
    man = json.load(open("cleveland_manifest_v2.json"))["targets"]
    which = sys.argv[1:] or list(man.keys())
    for name in which:
        cp = "%s/%s.pkl" % (CACHE, name)
        if os.path.exists(cp):
            print("%-15s (cacheada)" % name); continue
        try:
            _, msg = build(name, man[name])
            print("%-15s %s" % (name, msg))
        except Exception as e:
            print("%-15s ERROR %s: %s" % (name, type(e).__name__, str(e)[:60]))
