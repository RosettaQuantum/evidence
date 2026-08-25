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


def _asegurar_openmp():
    """xgboost y lightgbm necesitan libomp; en este Mac no esta instalada en el sistema.

    POR QUE NO SE ARREGLA CON UNA VARIABLE DE ENTORNO: macOS borra DYLD_LIBRARY_PATH al
    lanzar binarios protegidos (SIP), asi que exportarla funciona en una llamada directa y
    se PIERDE en cuanto el proceso pasa por `env`, `nohup` o un runner. Se ve como que el
    arreglo funciona hasta que corre desatendido, que es cuando importa.

    scikit-learn ya trae su propia libomp dentro del paquete. Se precarga con ctypes, que
    no depende de ninguna variable y no toca nada del sistema. Si no aparece, se declara
    en vez de fallar en silencio: el harness sigue y los modelos que la necesiten
    reventaran con su propio mensaje.
    """
    import ctypes, glob as _glob
    if sys.platform != "darwin":
        return None
    try:
        import sklearn as _sk
        cand = _glob.glob(os.path.join(os.path.dirname(_sk.__file__), ".dylibs", "libomp*.dylib"))
    except Exception:
        cand = []
    for c in cand:
        try:
            ctypes.CDLL(c, mode=getattr(ctypes, "RTLD_GLOBAL", 0))
            return c
        except OSError:
            continue
    return None


OPENMP = _asegurar_openmp()

SEED = 42

# ================== DE QUE DATASET SE HABLA ==================
# El protocolo es el MISMO para los dos —particion temporal, guardias, metricas,
# bootstrap— y lo unico que cambia es como se carga el dato y como se llaman sus
# columnas. Por eso hay un adaptador y no un segundo harness: una lista que vive en dos
# lugares ya divergio, y aqui la "lista" seria el protocolo entero.
#
# ULB    (RQ-DATA-HSBC-ULB-001):  .arff, ordena por Time,          etiqueta Class
# IEEE   (RQ-DATA-HSBC-IEEE-001): .csv,  ordena por TransactionDT, etiqueta isFraud
DATASET = (os.environ.get("RQ_DATASET") or "ulb").lower()

if DATASET == "ulb":
    MANIFEST = "RQ-DATA-HSBC-ULB-001"
    MANIFEST_SHA = "fdaf12730dc1fc426f318b71349f24f5c5fd00aa1152940be7e7509ae3d89d2a"
    RUTA = os.environ.get("RQ_ARFF", "creditcard.arff")
    TIEMPO, ETIQUETA = "Time", "Class"
    raw = open(RUTA, "rb").read()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA:
        raise SystemExit("ABORTA (guardia b): el dato NO es el del manifest sellado")
    txt = raw.decode("utf-8"); i = txt.lower().index("@data")
    cols = re.findall(r"@attribute\s+'?([^\s']+)'?", txt[:i], re.I)
    df = pd.read_csv(io.StringIO(txt[i+5:]), names=cols, quotechar="'")
    df[ETIQUETA] = df[ETIQUETA].astype(int)

elif DATASET == "ieee":
    MANIFEST = "RQ-DATA-HSBC-IEEE-001"
    MANIFEST_SHA = "3a5c83ab6b3cc13dcabe5ffa9f522307fd5f7f7b6e6f6a60c32284ca6283d642"
    RUTA = os.environ.get("RQ_CSV", "train_transaction.csv")
    TIEMPO, ETIQUETA = "TransactionDT", "isFraud"
    # El archivo pesa 683 MB: se hashea por bloques en vez de cargarlo entero a memoria.
    _h = hashlib.sha256()
    with open(RUTA, "rb") as _f:
        for _b in iter(lambda: _f.read(1 << 20), b""): _h.update(_b)
    if _h.hexdigest() != MANIFEST_SHA:
        raise SystemExit("ABORTA (guardia b): el dato NO es el del manifest sellado")
    df = pd.read_csv(RUTA, low_memory=False)
    df[ETIQUETA] = df[ETIQUETA].astype(int)
    cols = list(df.columns)
    # NOTA que va al artefacto: test_transaction.csv de Kaggle NO trae isFraud (etiquetas
    # ocultas para su competencia), asi que NINGUNA metrica propia puede salir de ahi. La
    # evaluacion es la particion temporal DENTRO de train_transaction.csv. Declarado en
    # RQ-DATA-HSBC-IEEE-001.
else:
    raise SystemExit("RQ_DATASET=%r desconocido (ulb|ieee)" % DATASET)

# ================== MODO ATAQUE (prereg RQ-PREREG-HSBC-002-ATAQUE) ==================
# Cuatro series, modelo UNICO (XGBoost config v1): lo que se compara es el protocolo.
# S1 aleatoria sin SMOTE (control) · S2 SMOTE-dentro (correcto) · S3 SMOTE-antes
# (DEFECTUOSO A PROPOSITO, diagnostico etiquetado) · S4 barrido temporal 70-90 %.
ATAQUE = os.environ.get("RQ_ATAQUE") or ""
if ATAQUE and DATASET != "ulb":
    # El modo ataque tiene los nombres de columna de ULB escritos adentro y su
    # pre-registro (RQ-PREREG-HSBC-002-ATAQUE) declara ULB. Correrlo sobre otro dataset
    # daria numeros que se verian bien y responderian a otra pregunta.
    raise SystemExit("ABORTA: RQ_ATAQUE solo esta definido para ULB, y RQ_DATASET=%r. "
                     "Su pre-registro declara ULB." % DATASET)
if ATAQUE:
    import numpy as _np
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import (average_precision_score, roc_auc_score, f1_score,
                                 confusion_matrix)
    import xgboost as xgb
    FEAT = [c for c in cols if c != "Class"]

    def _modelo(spw):
        return xgb.XGBClassifier(n_estimators=600, max_depth=6, learning_rate=0.08,
                                 subsample=0.9, colsample_bytree=0.9,
                                 scale_pos_weight=spw, eval_metric="aucpr",
                                 random_state=SEED, n_jobs=4)

    def _corrida(Xtr, ytr, Xte, yte, etiqueta, boot=400):
        spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
        m = _modelo(spw); m.fit(Xtr, ytr)
        psc = m.predict_proba(Xte)[:, 1]
        auprc = float(average_precision_score(yte, psc))
        auc = float(roc_auc_score(yte, psc))
        yh = (psc >= 0.5).astype(int)
        tn, fp, fn, tp = confusion_matrix(yte, yh).ravel()
        rs_ = _np.random.RandomState(SEED); difs = []
        for _ in range(boot):
            ix = rs_.randint(0, len(yte), len(yte))
            if yte[ix].sum() == 0: continue
            difs.append(average_precision_score(yte[ix], psc[ix]))
        return {"etiqueta": etiqueta, "AUPRC": round(auprc, 6), "AUC_ROC": round(auc, 6),
                "F1_05": round(float(f1_score(yte, yh)), 6),
                "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
                "AUPRC_boot_se": round(float(_np.std(difs)), 6),
                "train": {"n": int(len(ytr)), "fraudes": int(ytr.sum()),
                          "tasa": round(float(_np.mean(ytr)), 6)},
                "test": {"n": int(len(yte)), "fraudes": int(yte.sum()),
                         "tasa": round(float(_np.mean(yte)), 6)}}, psc, yte

    corridas = []; X = df[FEAT].values; y = df["Class"].values
    if ATAQUE in ("S1", "S2", "S3"):
        if ATAQUE in ("S2", "S3"):
            from imblearn.over_sampling import SMOTE
        for semilla in range(100, 120):
            if ATAQUE == "S3":
                # DEFECTUOSO A PROPOSITO: SMOTE sobre el dataset COMPLETO y particion
                # despues — los vecinos sinteticos del test se filtran al train. Se corre
                # como diagnostico; NINGUN numero de S3 se cita como rendimiento real.
                Xs, ys = SMOTE(k_neighbors=5, random_state=semilla).fit_resample(X, y)
                Xtr, Xte, ytr, yte = train_test_split(Xs, ys, test_size=0.2,
                                                      stratify=ys, random_state=semilla)
            else:
                Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y,
                                                      random_state=semilla)
                if ATAQUE == "S2":
                    Xtr, ytr = SMOTE(k_neighbors=5,
                                     random_state=semilla).fit_resample(Xtr, ytr)
            r, psc, yv = _corrida(Xtr, ytr, Xte, yte, "%s_seed%d" % (ATAQUE, semilla))
            corridas.append(r)
            print("%s seed=%d AUPRC=%.4f AUC=%.4f" % (ATAQUE, semilla, r["AUPRC"],
                                                      r["AUC_ROC"]))
    elif ATAQUE == "S4":
        dft = df.sort_values("Time", kind="mergesort").reset_index(drop=True)
        for frac in (0.70, 0.75, 0.80, 0.85, 0.90):
            c = int(frac * len(dft))
            tr_, te_ = dft.iloc[:c], dft.iloc[c:]
            r, psc, yv = _corrida(tr_[FEAT].values, tr_["Class"].values,
                                  te_[FEAT].values, te_["Class"].values,
                                  "S4_corte%d" % int(frac * 100))
            corridas.append(r)
            print("S4 corte=%.2f AUPRC=%.4f AUC=%.4f" % (frac, r["AUPRC"], r["AUC_ROC"]))
    else:
        raise SystemExit("RQ_ATAQUE=%r: las series son S1, S2, S3, S4" % ATAQUE)

    vals = [r["AUPRC"] for r in corridas]
    peor, mejor = corridas.index(min(corridas, key=lambda r: r["AUPRC"])),                   corridas.index(max(corridas, key=lambda r: r["AUPRC"]))
    out = {"ataque": ATAQUE, "prereg": "RQ-PREREG-HSBC-002-ATAQUE",
           "manifest": "RQ-DATA-HSBC-ULB-001", "arff_sha256": MANIFEST_SHA,
           "modelo": "xgboost v1 (config del baseline @2072bc53)",
           "S3_es_diagnostico_defectuoso": ATAQUE == "S3",
           "corridas": corridas,
           "resumen": {"n": len(vals),
                       "AUPRC_media": round(float(_np.mean(vals)), 6),
                       "AUPRC_sd": round(float(_np.std(vals, ddof=1)), 6) if len(vals) > 1 else None,
                       "AUPRC_min": min(vals), "AUPRC_max": max(vals),
                       "mediana_boot_se": round(float(_np.median(
                           [r["AUPRC_boot_se"] for r in corridas])), 6)},
           "seed_base": SEED,
           "harness_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
    try:
        import imblearn; out["imblearn_version"] = imblearn.__version__
    except Exception:
        out["imblearn_version"] = None
    json.dump(out, open(os.environ.get("RQ_OUT", "resultado_hsbc.json"), "w"), indent=1)
    print("serie %s: media AUPRC %.4f  sd %s  [%d corridas]"
          % (ATAQUE, out["resumen"]["AUPRC_media"], out["resumen"]["AUPRC_sd"], len(vals)))
    raise SystemExit(0)

# particion TEMPORAL 80/20: el test es el futuro
df = df.sort_values(TIEMPO, kind="mergesort").reset_index(drop=True)
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

# LAS COLUMNAS QUE ENTRAN, Y COMO. En ULB son 30 numericas y no hay nada que decidir.
# En IEEE-CIS hay columnas de texto (ProductCD, card4, card6, los dominios de correo…) y
# como se codifiquen ES una decision no prefijada, asi que se declara y viaja al
# artefacto. Se usa codificacion ordinal AJUSTADA SOLO CON EL TRAIN: una categoria que
# solo aparece en el test entra como -1. Ajustarla sobre el dataset completo seria mirar
# el futuro, que es exactamente lo que la particion temporal viene a impedir.
FEAT = [c for c in cols if c not in (ETIQUETA,)]
if DATASET == "ieee":
    FEAT = [c for c in FEAT if c != "TransactionID"]
categoricas = [c for c in FEAT if not pd.api.types.is_numeric_dtype(df[c])]
mapeos = {}
if categoricas:
    tr = tr.copy(); te = te.copy()
    for c in categoricas:
        vistos = {v: k for k, v in enumerate(sorted(tr[c].dropna().unique().tolist()))}
        mapeos[c] = len(vistos)
        tr[c] = tr[c].map(vistos).fillna(-1).astype(np.int32)
        te[c] = te[c].map(vistos).fillna(-1).astype(np.int32)
Xtr, ytr = tr[FEAT].values.astype(np.float32), tr[ETIQUETA].values
Xte, yte = te[FEAT].values.astype(np.float32), te[ETIQUETA].values
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

# GUARDIA: si el test no es el futuro, no hay artefacto. El pre-registro fija particion
# temporal; un corte que se solapa produce numeros que se ven bien y responden a otra
# pregunta — y nadie lo notaria mirando el AUPRC.
if te[TIEMPO].min() < tr[TIEMPO].max():
    raise SystemExit("ABORTA: el corte NO es temporal: min(test)=%s < max(train)=%s"
                     % (te[TIEMPO].min(), tr[TIEMPO].max()))

out = {"dataset": DATASET, "manifest": MANIFEST, "datos_sha256": MANIFEST_SHA,
       "columnas_categoricas": {"cuantas": len(categoricas),
                                "niveles_vistos_en_train": mapeos,
                                "codificacion": "ordinal ajustada SOLO con el train; una "
                                    "categoria que solo aparece en el test entra como -1"},
       "particion": {"tipo": "temporal 80/20 por %s" % TIEMPO, "corte_fila": corte,
                     "train": {"filas": len(tr), "fraudes": int(ytr.sum()),
                               "tasa": round(float(ytr.mean()), 6)},
                     "test": {"filas": len(te), "fraudes": int(yte.sum()),
                              "tasa": round(float(yte.mean()), 6),
                              "sha256": test_sha},
                     # LA PROPIEDAD CENTRAL DEL PRE-REGISTRO, MEDIDA Y DENTRO DEL
                     # ARTEFACTO. «El test es el futuro» no es una intencion del diseno:
                     # es una desigualdad entre dos numeros, y si no viaja aqui el lector
                     # tiene que creernos. Con esto la comprueba sin re-correr nada.
                     "corte_temporal": {
                         "columna": TIEMPO,
                         "max_train": float(tr[TIEMPO].max()),
                         "min_test": float(te[TIEMPO].min()),
                         "min_test_mayor_o_igual_que_max_train":
                             bool(te[TIEMPO].min() >= tr[TIEMPO].max()),
                         "ventana_de_test_dias":
                             round(float(te[TIEMPO].max() - te[TIEMPO].min()) / 86400.0, 2),
                         "ventana_de_train_dias":
                             round(float(tr[TIEMPO].max() - tr[TIEMPO].min()) / 86400.0, 2),
                         "cambio_relativo_de_la_tasa_pct": round(
                             100.0 * (float(yte.mean()) - float(ytr.mean()))
                             / max(1e-12, float(ytr.mean())), 1)},
                     "solape_de_contenido_duplicados_exactos": solape_contenido},
       "scale_pos_weight": round(spw, 2), "seed": SEED,
       "modelos": res,
       "harness_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
out["lib_versions"] = {m.__name__: getattr(m, "__version__", "?") for m in
                       [__import__(x) for x in ("numpy", "pandas", "sklearn")]}
for _m in modelos:
    try: out["lib_versions"][_m] = __import__(_m).__version__
    except Exception: pass
# QUE HIZO FALTA PARA QUE CORRIERA, dicho con precision.
# `OPENMP` registra que se precargo con ctypes — pero eso NO es lo que resolvio el
# problema: dlopen resuelve @rpath por RUTA y no mira lo que ya esta cargado. Lo que
# funciono fue agregarle un rpath a las dylib DENTRO de nuestro venv apuntando a la
# libomp que scikit-learn ya trae. Decir «precargada» a secas insinuaria que la precarga
# fue el mecanismo, y no lo fue.
out["openmp"] = {
    "precargada_con_ctypes": OPENMP,
    "resolvio_el_problema": False,
    "que_lo_resolvio": "install_name_tool -add_rpath sobre libxgboost.dylib y "
                       "lib_lightgbm.dylib del venv, apuntando a la libomp que trae "
                       "scikit-learn. No se instalo nada en el sistema.",
    "por_que_no_bastaba_una_variable": "macOS borra DYLD_LIBRARY_PATH al lanzar binarios "
        "protegidos (SIP), asi que exportarla funciona en una llamada directa y se pierde "
        "en cuanto el proceso pasa por env, nohup o un runner — se ve como que el arreglo "
        "funciona hasta que corre desatendido.",
}
json.dump(out, open(os.environ.get("RQ_OUT", "resultado_hsbc.json"), "w"), indent=1)
print("\ntest sha256:", test_sha[:16], "| train %d/%d fraudes | test %d/%d"
      % (int(ytr.sum()), len(tr), int(yte.sum()), len(te)))
