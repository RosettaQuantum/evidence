"""Holdout K-fold AGRUPADO por proteina — prueba de generalizacion mas dura que el LOPO.
El LOPO entrena con 89 para predecir 1. Aqui entrenamos con 2/3 (60) y predecimos el
tercio restante (30) que el modelo NUNCA vio; cada proteina cae en test exactamente una vez.
Fisher combina las 90 predicciones de test. Comparable directo al Fisher del run LOPO N=90.

Honestidad (se declara): el DISENO de features vio las 90; esto NO es un test prospectivo
ciego (esos no existen: el pool esta agotado, todo lo que pasa la reja distal ya esta dentro).
Es una prueba de que la senal no la carga el set de entrenamiento casi-completo del LOPO.

Pre-registro: split determinista por seed; config CONGELADO = run N=90. Se hashea antes de leer p.
"""
import os, sys, json, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import sigo_features as SF

FEAT_COLS = ['degree','closeness_to_active','coordination','uni_binding_site','uni_active_site',
             'uni_domain','uni_ptm','uni_motif','clinvar_density','conservation','gnm_msf','anm_msf',
             'diffusion','gnm','betweenness']
GLIFO_FEATS = ['uni_binding_site','uni_active_site','uni_domain','uni_ptm','uni_motif',
               'clinvar_density','coordination','degree','closeness_to_active','conservation','gnm_msf','anm_msf']
WIN = (0.5, 8.0); NPERM = 2000; SEED_NULL = 20260717
SPLIT_SEED = 20260802   # seed del split k-fold, pre-registrado (fecha de hoy)
KFOLDS = 3
ABLATION_DROP = ['uni_binding_site','uni_active_site','uni_site','uni_domain','uni_motif','uni_ptm']

def precompute(names):
    D = []
    for name in names:
        cp = os.path.join(E.CACHE, "%s.pkl" % name)
        if not os.path.exists(cp): continue
        d = __import__('pickle').load(open(cp, "rb"))
        A, coords, src, feats = d["A"], d["coords"], d["src"], d["features"]
        P, _, _ = E.props(A, src, *WIN)
        Hf, _ = SF.annotated_hamiltonian(A, coords, feats, E.WEIGHTS_FIXED, edge_mode="gaussian")
        d["btw"] = E.betweenness_closeness(A, src)[0]
        d["det"] = {"ctqw_bare": P["ctqw"][0], "ctqw_glifo_fixed": E.ctqw(Hf, src, WIN),
                    "diffusion": P["diffusion"][0], "gnm": E.gnm_score(A, src)}
        d["y"] = np.zeros(d["n"]); d["y"][d["allo"]] = 1.0
        cols = {}
        for c in FEAT_COLS:
            if c in ("diffusion","gnm"): cols[c] = d["det"][c]
            elif c == "betweenness": cols[c] = d["btw"]
            else: cols[c] = E._col(d, c)
        d["X"] = np.column_stack([cols[c] for c in FEAT_COLS])
        d["pockets"] = E.contiguous_null(coords, np.where(d["mask"])[0], max(1, d["k"]), NPERM, SEED_NULL)
        d["desc"] = np.array([np.log(d["n"]), d["n_distal"]/d["n"], float(np.mean(d["det"]["gnm"])),
                              float(np.mean(cols.get("coordination", E._col(d,"coordination")))),
                              float(np.mean(E._col(d,"uni_binding_site")))])
        D.append(d)
    return D

def fit_predict_ml(train, test, cols):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    def Xof(dd): return np.column_stack([(dd["det"][c] if c in ("diffusion","gnm")
                    else dd["btw"] if c == "betweenness" else E._col(dd, c)) for c in cols])
    Xtr = np.vstack([Xof(t)[t["mask"]] for t in train])
    ytr = np.concatenate([t["y"][t["mask"]] for t in train])
    sc = StandardScaler().fit(Xtr)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0).fit(sc.transform(Xtr), ytr)
    ps = []
    for d in test:
        prob = np.zeros(d["n"]); prob[d["mask"]] = clf.predict_proba(sc.transform(Xof(d)[d["mask"]]))[:,1]
        ps.append((d["name"], E.null_p(prob, d)[1]))
    return ps

def fit_predict_stacked(train, test):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    # propagadores: incluye ctqw_glifo_learned aprendido en train
    w = E.learn_weights(train, GLIFO_FEATS)
    def prop_of(d):
        H, _ = SF.annotated_hamiltonian(d["A"], d["coords"], d["features"], w, edge_mode="gaussian")
        learned = E.ctqw(H, d["src"], WIN)
        sig = {"ctqw_bare": d["det"]["ctqw_bare"], "ctqw_glifo_fixed": d["det"]["ctqw_glifo_fixed"],
               "ctqw_glifo_learned": learned, "diffusion": d["det"]["diffusion"],
               "gnm": d["det"]["gnm"], "betweenness": d["btw"]}
        return np.column_stack([E.norm01(sig[c]) for c in E.PROP_FEATS])
    Ptr = np.vstack([prop_of(t)[t["mask"]] for t in train])
    ytr = np.concatenate([t["y"][t["mask"]] for t in train])
    sc = StandardScaler().fit(Ptr)
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0).fit(sc.transform(Ptr), ytr)
    ps = []
    for d in test:
        Pd = prop_of(d)
        prob = np.zeros(d["n"]); prob[d["mask"]] = clf.predict_proba(sc.transform(Pd[d["mask"]]))[:,1]
        ps.append((d["name"], E.null_p(prob, d)[1]))
    return ps

def main():
    names = json.load(open(os.path.join(E.HERE, "_train90.json")))
    # PRE-REGISTRO: hash del protocolo antes de leer resultados
    prereg = {"protocol": "kfold_grouped_holdout", "k": KFOLDS, "split_seed": SPLIT_SEED,
              "train_names": sorted(names), "feat_cols": FEAT_COLS, "glifo_feats": GLIFO_FEATS,
              "nperm": NPERM, "seed_null": SEED_NULL, "window": list(WIN),
              "ablation_drop": ABLATION_DROP,
              "claim": "generalizacion out-of-fold: modelo entrenado en 2/3 predice el 1/3 no visto"}
    prereg_hash = hashlib.sha256(json.dumps(prereg, sort_keys=True).encode()).hexdigest()
    print("PRE-REG hash:", prereg_hash[:16])
    print("cargando y precomputando %d proteinas..." % len(names))
    D = precompute(names)
    print("precomputadas:", len(D))
    # split determinista
    rs = np.random.RandomState(SPLIT_SEED)
    order = list(range(len(D))); rs.shuffle(order)
    folds = [order[i::KFOLDS] for i in range(KFOLDS)]
    pB_all, pC_all, pAbl_all = [], [], []
    for fi, fold in enumerate(folds):
        test = [D[i] for i in fold]; train = [D[i] for i in range(len(D)) if i not in set(fold)]
        print("fold %d: train=%d test=%d" % (fi+1, len(train), len(test)))
        pB_all += fit_predict_ml(train, test, FEAT_COLS)
        pC_all += fit_predict_stacked(train, test)
        pAbl_all += fit_predict_ml(train, test, [c for c in FEAT_COLS if c not in set(ABLATION_DROP)])
    def combine(ps): return round(E.fisher([p for _, p in ps]), 6), int(sum(p < 0.05 for _, p in ps))
    fB, nB = combine(pB_all); fC, nC = combine(pC_all); fAbl, nAbl = combine(pAbl_all)
    out = {"prereg": prereg, "prereg_hash": prereg_hash, "n": len(D),
           "results": {
               "armB_ml":        {"fisher_p": fB,   "n_sig_p05": nB,   "of": len(pB_all)},
               "armC_stacked":   {"fisher_p": fC,   "n_sig_p05": nC,   "of": len(pC_all)},
               "sin_anotaciones":{"fisher_p": fAbl, "n_sig_p05": nAbl, "of": len(pAbl_all)}},
           "per_protein": {"armB": {n: round(p,4) for n,p in pB_all}}}
    json.dump(out, open(os.path.join(E.HERE, "holdout_kfold_result.json"), "w"), indent=1)
    print("\n=== HOLDOUT K-FOLD (train 60 -> predice 30 no visto, x3) ===")
    print("arm B (ML features):    Fisher p = %.6f   (%d/%d con p<0.05)" % (fB, nB, len(pB_all)))
    print("arm C (ML propagadores):Fisher p = %.6f   (%d/%d con p<0.05)" % (fC, nC, len(pC_all)))
    print("sin_anotaciones (de novo):Fisher p = %.6f (%d/%d)" % (fAbl, nAbl, len(pAbl_all)))
    print("\ncomparar con LOPO N=90: armB=0.0, armC=0.0, sin_anotaciones=0.0")
    print("guardado holdout_kfold_result.json")

if __name__ == "__main__":
    main()
