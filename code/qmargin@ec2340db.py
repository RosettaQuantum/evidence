"""RQ-EXP-QMARGIN-001 — Contribucion marginal de la caminata cuantica (pre-registrado FORWARD).
Pregunta: ¿los propagadores CTQW aportan senal NO-REDUNDANTE para predecir el bolsillo
alosterico, mas alla de los propagadores clasicos? No "¿gana?" sino "¿suma?".

Diseno: dos modelos ML (LogisticRegression identica) LOPO sobre las 90:
  - C_all       = 6 propagadores: ctqw_bare, ctqw_glifo_fixed, ctqw_glifo_learned, diffusion, gnm, betweenness
  - C_classical = 3 propagadores clasicos: diffusion, gnm, betweenness
Metrica por proteina: percentil del bolsillo (distal). Test:
  (a) Fisher p de cada variante vs nulo espacial contiguo (nperm=2000, seed 20260717).
  (b) Wilcoxon pareado sobre los percentiles (C_all vs C_classical) — ¿lo cuantico mejora el ranking?
  (c) Delta medio y #proteinas mejoradas.
Exito pre-registrado: si C_all supera a C_classical de forma pareada (Wilcoxon p<0.05, delta>0),
es la PRIMERA contribucion cuantica NO-REDUNDANTE medida en tarea biomedica real. Si no, es un
NEGATIVO preciso publicable: la caminata no aporta senal extra sobre los propagadores clasicos.
Presupuesto pareado: mismo modelo, mismo LOPO, mismas proteinas; unica diferencia = 3 columnas cuanticas.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine as E
import sigo_features as SF
from scipy.stats import wilcoxon

WIN = (0.5, 8.0); NPERM = 2000; SEED_NULL = 20260717
GLIFO_FEATS = ['uni_binding_site','uni_active_site','uni_domain','uni_ptm','uni_motif',
               'clinvar_density','coordination','degree','closeness_to_active','conservation','gnm_msf','anm_msf']
Q_PROPS = ['ctqw_bare','ctqw_glifo_fixed','ctqw_glifo_learned']
C_PROPS = ['diffusion','gnm','betweenness']

def precompute(names):
    import pickle
    D = []
    for name in names:
        cp = os.path.join(E.CACHE, "%s.pkl" % name)
        if not os.path.exists(cp): continue
        d = pickle.load(open(cp, "rb"))
        A, coords, src, feats = d["A"], d["coords"], d["src"], d["features"]
        P, _, _ = E.props(A, src, *WIN)
        Hf, _ = SF.annotated_hamiltonian(A, coords, feats, E.WEIGHTS_FIXED, edge_mode="gaussian")
        d["btw"] = E.betweenness_closeness(A, src)[0]
        d["det"] = {"ctqw_bare": P["ctqw"][0], "ctqw_glifo_fixed": E.ctqw(Hf, src, WIN),
                    "diffusion": P["diffusion"][0], "gnm": E.gnm_score(A, src)}
        d["y"] = np.zeros(d["n"]); d["y"][d["allo"]] = 1.0
        d["pockets"] = E.contiguous_null(coords, np.where(d["mask"])[0], max(1, d["k"]), NPERM, SEED_NULL)
        D.append(d)
    return D

def build_props(D):
    # pesos Glifo aprendidos LOPO -> ctqw_glifo_learned por proteina
    learned = []
    for i, d in enumerate(D):
        w = E.learn_weights([D[j] for j in range(len(D)) if j != i], GLIFO_FEATS)
        H, _ = SF.annotated_hamiltonian(d["A"], d["coords"], d["features"], w, edge_mode="gaussian")
        learned.append(E.ctqw(H, d["src"], WIN))
    for i, d in enumerate(D):
        sig = {"ctqw_bare": d["det"]["ctqw_bare"], "ctqw_glifo_fixed": d["det"]["ctqw_glifo_fixed"],
               "ctqw_glifo_learned": learned[i], "diffusion": d["det"]["diffusion"],
               "gnm": d["det"]["gnm"], "betweenness": d["btw"]}
        d["col"] = {k: E.norm01(sig[k]) for k in (Q_PROPS + C_PROPS)}

def lopo_variant(D, cols):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    pcts, ps = [], []
    for i, d in enumerate(D):
        others = [j for j in range(len(D)) if j != i]
        Xtr = np.vstack([np.column_stack([D[j]["col"][c] for c in cols])[D[j]["mask"]] for j in others])
        ytr = np.concatenate([D[j]["y"][D[j]["mask"]] for j in others])
        sc = StandardScaler().fit(Xtr)
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0).fit(sc.transform(Xtr), ytr)
        Xte = np.column_stack([d["col"][c] for c in cols])
        prob = np.zeros(d["n"]); prob[d["mask"]] = clf.predict_proba(sc.transform(Xte[d["mask"]]))[:, 1]
        o, p = E.null_p(prob, d)
        pcts.append(o); ps.append(p)
    return np.array(pcts), np.array(ps)

def main():
    names = json.load(open(os.path.join(E.HERE, "_train90.json")))
    print("precomputando %d..." % len(names)); D = precompute(names); print("ok", len(D)); build_props(D)
    pct_all, p_all = lopo_variant(D, Q_PROPS + C_PROPS)
    pct_cla, p_cla = lopo_variant(D, C_PROPS)
    delta = pct_all - pct_cla
    # Wilcoxon pareado (los percentiles del modelo cuantico-aumentado vs clasico)
    try: w_stat, w_p = wilcoxon(pct_all, pct_cla, alternative="greater")
    except Exception as ex: w_stat, w_p = float("nan"), float("nan"); print("wilcoxon:", ex)
    out = {
        "exp_id": "RQ-EXP-QMARGIN-001", "n": len(D),
        "fisher_p_C_all_6prop": round(E.fisher(p_all), 6),
        "fisher_p_C_classical_3prop": round(E.fisher(p_cla), 6),
        "wilcoxon_pareado_all_vs_classical_greater": {"stat": float(w_stat), "p": float(w_p)},
        "delta_pct_medio": round(float(delta.mean()), 3),
        "n_mejoradas": int((delta > 0).sum()), "n_empeoradas": int((delta < 0).sum()),
        "n_sig_all": int((p_all < 0.05).sum()), "n_sig_classical": int((p_cla < 0.05).sum()),
        "veredicto": None}
    # veredicto honesto
    if w_p < 0.05 and delta.mean() > 0:
        out["veredicto"] = "CONTRIBUCION CUANTICA NO-REDUNDANTE MEDIDA (los propagadores cuanticos suman senal, pareado p<0.05)"
    else:
        out["veredicto"] = "NEGATIVO PRECISO: la caminata cuantica NO aporta senal extra sobre los propagadores clasicos (pareado n.s.)"
    json.dump(out, open(os.path.join(E.HERE, "qmargin_result.json"), "w"), indent=1)
    print(json.dumps(out, indent=1, ensure_ascii=False))

if __name__ == "__main__":
    main()
