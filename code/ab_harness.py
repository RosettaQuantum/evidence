"""
A/B EN CADA RUN — Brazo A (gestor cuántico: caminata sobre grafo anotado de Glifo)
vs Brazo B (ML clásico supervisado, mismas features de Glifo + propagadores clásicos,
SIN la caminata cuántica). Mismo train/test (leave-one-protein-out), misma verdad-
terreno, misma métrica → comparación limpia y honesta en cada corrida.

Brazo B = regresión logística (regularizada, class_weight balanced) sobre features
por residuo. Se entrena en las OTRAS proteínas y predice la dejada fuera A CIEGAS.
La pregunta del A/B: ¿un ML clásico sobre los mismos datos iguala o supera al brazo
cuántico? Publicamos el resultado gane quien gane.
"""
import sys, json, numpy as np, prody
prody.confProDy(verbosity='none')
sys.path.insert(0, "/home/claude/rosettaq")
from allo_challenge import ca_network, contacts, idx_of, props, gnm_score, betweenness_closeness, percentile, DISTAL_A
from sigo_features import build_feature_table, annotated_hamiltonian, load_pdb

WEIGHTS = {"uni_binding_site":1.0,"uni_active_site":1.0,"clinvar_density":0.5,"coordination":0.3}
WIN = (0.5, 8.0)
# columnas del vector por residuo para el ML (clásicas + Glifo; NADA cuántico)
FEATCOLS = ["degree","closeness_to_active","coordination","uni_binding_site",
            "uni_active_site","uni_domain","uni_ptm","uni_motif","clinvar_density",
            "diffusion","gnm","betweenness"]

def ctqw_score(M, src):
    n=M.shape[0]; TS=np.linspace(*WIN,16); w,V=np.linalg.eigh(M)
    psi=np.zeros(n); psi[src]=1/np.sqrt(len(src)); c=V.T@psi; q=np.zeros(n)
    for t in TS: q+=np.abs(V@(np.exp(-1j*w*t)*c))**2
    return q

def build_one(name, m):
    """Devuelve dict con features por residuo, etiqueta y, máscara distal, y el score
    del brazo A (cuántico anotado) — todo alineado a los residuos de la apo."""
    ft = build_feature_table(m, cutoff=8.5)
    A, ids, coords, feats, src = ft["A"], ft["ids"], ft["coords"], ft["features"], ft["src_idx"]
    if not src:
        return None
    # verdad-terreno desde la holo
    holo = load_pdb(m["holo"]); ch = m["chain"]
    gt = [(ch, r) for (c, r) in contacts(holo, "resname %s" % m["gt_ligand"], "protein")]
    allo = idx_of(ids, gt)
    if len(allo) < 5:
        return None
    dmin = np.min(np.linalg.norm(coords[:, None, :]-coords[src][None, :, :], axis=-1), axis=1)
    mask = dmin > DISTAL_A
    # propagadores clásicos (features del ML) + brazo A (cuántico)
    P,_,_ = props(A, src, *WIN)
    diff = P["diffusion"][0]; gnm = gnm_score(A, src); btw = betweenness_closeness(A, src)[0]
    H,_ = annotated_hamiltonian(A, coords, feats, WEIGHTS, edge_mode="gaussian")
    armA = ctqw_score(H, src)
    # matriz de features por residuo
    cols = {}
    for c in FEATCOLS:
        if c == "diffusion": cols[c]=diff
        elif c == "gnm": cols[c]=gnm
        elif c == "betweenness": cols[c]=btw
        else:
            v = feats.get(c)
            cols[c] = np.asarray(v, float) if v is not None else np.zeros(len(ids))
    X = np.column_stack([cols[c] for c in FEATCOLS])
    y = np.zeros(len(ids)); y[allo] = 1.0
    return {"name":name,"X":X,"y":y,"mask":mask,"allo":allo,"armA":armA,"n":len(ids)}

def score(vec, allo, mask):
    allo_d = [a for a in allo if mask[a]]
    return percentile(vec, allo_d, mask), len(allo_d)

if __name__ == "__main__":
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    man = json.load(open("/home/claude/rosettaq/cleveland_manifest.json"))["targets"]
    which = sys.argv[1:] or ["KRAS_G12C","BCR_ABL1"]   # smoke: los que tienen src por ligando
    data = []
    for name in which:
        d = build_one(name, man[name])
        if d: data.append(d); print("  cargada %s (n=%d, allo=%d)" % (name, d["n"], int(d["y"].sum())))
        else: print("  (saltada %s: sin src o GT<5)" % name)
    if len(data) < 2:
        print("necesito >=2 proteinas con src para el A/B (leave-one-out)"); sys.exit()
    print("\n== A/B por proteina (leave-one-protein-out) ==")
    print("%-13s %8s %8s   %s" % ("proteina","A_cuant","B_ml","(percentil distal del bolsillo)"))
    rowsA, rowsB = [], []
    for i, d in enumerate(data):
        # entrenar B en las OTRAS proteinas (residuos distales), predecir la dejada fuera
        Xtr = np.vstack([data[j]["X"][data[j]["mask"]] for j in range(len(data)) if j!=i])
        ytr = np.concatenate([data[j]["y"][data[j]["mask"]] for j in range(len(data)) if j!=i])
        sc = StandardScaler().fit(Xtr)
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
        clf.fit(sc.transform(Xtr), ytr)
        probB = np.zeros(d["n"])
        probB[d["mask"]] = clf.predict_proba(sc.transform(d["X"][d["mask"]]))[:,1]
        a,_ = score(d["armA"], d["allo"], d["mask"])
        b,_ = score(probB, d["allo"], d["mask"])
        rowsA.append(a); rowsB.append(b)
        print("%-13s %8.1f %8.1f" % (d["name"], a, b))
    print("%-13s %8.1f %8.1f   <- media" % ("MEDIA", np.mean(rowsA), np.mean(rowsB)))
    print("\nNota: smoke de la maquinaria (pocas proteinas). El A/B de verdad corre sobre")
    print("las 16 del set congelado una vez sellado el pre-registro y curado el src.")
