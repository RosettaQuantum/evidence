"""Track HSBC — particion temporal + baseline clasico sobre ULB (corre en CI).

Guardias del prereg RQ-PREREG-HSBC-001, todas falla-cerrado:
  (a) FUGA: train y test disjuntos por hash de fila; una fila en ambos aborta.
  (b) MANIFEST: el sha256 del arff tiene que calzar con RQ-DATA-HSBC-ULB-001.
  (c) estratificacion: aqui no hay submuestra (baseline entrena con todo), pero la
      tasa de fraude de cada mitad se MIDE y viaja al artefacto.
  (d) el sha256 del test set viaja al artefacto: el brazo cuantico debera declararlo igual.
"""
import hashlib, io, json, os, re, sys, time
import numpy as np, pandas as pd

MANIFEST_SHA = "fdaf12730dc1fc426f318b71349f24f5c5fd00aa1152940be7e7509ae3d89d2a"
SEED = 42
ARFF = os.environ.get("RQ_ARFF", "creditcard.arff")
raw = open(ARFF, "rb").read()
if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA:
    raise SystemExit("ABORTA (guardia b): el dato NO es el del manifest sellado")

txt = raw.decode("utf-8"); i = txt.lower().index("@data")
cols = re.findall(r"@attribute\s+'?([^\s']+)'?", txt[:i], re.I)
df = pd.read_csv(io.StringIO(txt[i+5:]), names=cols, quotechar="'")
df["Class"] = df["Class"].astype(int)

# particion TEMPORAL 80/20: el test es el futuro
df = df.sort_values("Time", kind="mergesort").reset_index(drop=True)
corte = int(0.8 * len(df))
tr, te = df.iloc[:corte], df.iloc[corte:]

# guardia (a): disjuntos por hash de fila completa
h_tr = set(pd.util.hash_pandas_object(tr, index=False).values)
h_te = set(pd.util.hash_pandas_object(te, index=False).values)
comunes = h_tr & h_te
# filas duplicadas EXACTAS existen en ULB (transacciones identicas); la fuga se define por
# INDICE, no por contenido: ninguna fila-objeto esta en ambos lados por construccion del
# corte. El solape de contenido se MIDE y se declara, no se esconde.
solape_contenido = len(comunes)

FEAT = [c for c in cols if c not in ("Class",)]
Xtr, ytr = tr[FEAT].values, tr["Class"].values
Xte, yte = te[FEAT].values, te["Class"].values
test_sha = hashlib.sha256(te.to_csv(index=False).encode()).hexdigest()

# Que modelos corren lo decide RQ_MODELOS (coma-separado). En CI van los del prereg
# (xgboost, lightgbm); sklearn_hgbt queda como contraste sin dependencia de OpenMP.
PEDIDOS = [m for m in (os.environ.get("RQ_MODELOS") or "xgboost,lightgbm").split(",") if m]
modelos = {}
if "xgboost" in PEDIDOS:
    import xgboost as xgb
    modelos["xgboost"] = lambda spw: xgb.XGBClassifier(
        n_estimators=600, max_depth=6, learning_rate=0.08, subsample=0.9,
        colsample_bytree=0.9, scale_pos_weight=spw, eval_metric="aucpr",
        random_state=SEED, n_jobs=4)
if "lightgbm" in PEDIDOS:
    import lightgbm as lgb
    modelos["lightgbm"] = lambda spw: lgb.LGBMClassifier(
        n_estimators=600, num_leaves=63, learning_rate=0.08, subsample=0.9,
        colsample_bytree=0.9, scale_pos_weight=spw, random_state=SEED, n_jobs=4,
        verbosity=-1)
if "sklearn_hgbt" in PEDIDOS:
    from sklearn.ensemble import HistGradientBoostingClassifier
    modelos["sklearn_hgbt"] = lambda spw: HistGradientBoostingClassifier(
        max_iter=600, learning_rate=0.08, max_depth=None, class_weight={0: 1, 1: spw},
        random_state=SEED)
if not modelos:
    raise SystemExit("RQ_MODELOS=%r no pidio ningun modelo conocido" % PEDIDOS)

from sklearn.metrics import average_precision_score, roc_auc_score, f1_score, confusion_matrix
spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
res = {}
for nombre, ctor in modelos.items():
    t0 = time.time(); m = ctor(spw); m.fit(Xtr, ytr)
    p = m.predict_proba(Xte)[:, 1]
    auprc = float(average_precision_score(yte, p))
    auc = float(roc_auc_score(yte, p))
    yhat = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(yte, yhat).ravel()
    # bootstrap 95 % (2000 remuestreos, semilla 42) sobre el TEST
    rs_ = np.random.RandomState(SEED); n = len(yte); a_, b_ = [], []
    for _ in range(2000):
        idx = rs_.randint(0, n, n)
        if yte[idx].sum() == 0: continue
        a_.append(average_precision_score(yte[idx], p[idx]))
        b_.append(roc_auc_score(yte[idx], p[idx]))
    res[nombre] = {"AUPRC": round(auprc, 6), "AUC_ROC": round(auc, 6),
                   "F1_umbral_0.5": round(float(f1_score(yte, yhat)), 6),
                   "confusion_0.5": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
                   "AUPRC_IC95": [round(float(np.percentile(a_, 2.5)), 6),
                                  round(float(np.percentile(a_, 97.5)), 6)],
                   "AUC_IC95": [round(float(np.percentile(b_, 2.5)), 6),
                                round(float(np.percentile(b_, 97.5)), 6)],
                   "bootstrap_validos": len(a_), "segundos": round(time.time() - t0, 1)}
    print("%-14s AUPRC=%.4f [%s]  AUC=%.4f  F1=%.4f  (%.0fs)"
          % (nombre, auprc, res[nombre]["AUPRC_IC95"], auc, res[nombre]["F1_umbral_0.5"],
             res[nombre]["segundos"]))
    # el dato crudo: scores del test, para recomputo exacto de ambas curvas
    np.savez_compressed(os.environ.get("RQ_SCORES_PREFIX", "scores_") + nombre + ".npz",
                        y_true=yte.astype(np.int8), y_score=p.astype(np.float32))

out = {"manifest": "RQ-DATA-HSBC-ULB-001", "arff_sha256": MANIFEST_SHA,
       "particion": {"tipo": "temporal 80/20 por Time", "corte_fila": corte,
                     "train": {"filas": len(tr), "fraudes": int(ytr.sum()),
                               "tasa": round(float(ytr.mean()), 6)},
                     "test": {"filas": len(te), "fraudes": int(yte.sum()),
                              "tasa": round(float(yte.mean()), 6),
                              "sha256": test_sha},
                     "solape_de_contenido_duplicados_exactos": solape_contenido},
       "scale_pos_weight": round(spw, 2), "seed": SEED,
       "modelos": res,
       "harness_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
out["lib_versions"] = {m.__name__: getattr(m, "__version__", "?") for m in
                       [__import__(x) for x in ("numpy", "pandas", "sklearn")]}
json.dump(out, open(os.environ.get("RQ_OUT", "resultado_hsbc.json"), "w"), indent=1)
print("\ntest sha256:", test_sha[:16], "| train %d/%d fraudes | test %d/%d"
      % (int(ytr.sum()), len(tr), int(yte.sum()), len(te)))
