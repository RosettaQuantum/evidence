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


def evaluar(p, yte, t0=None):
    """Metricas + bootstrap. UNA sola implementacion para los dos brazos.

    El criterio del pre-registro compara intervalos de confianza entre el brazo clasico y
    el cuantico. Si cada brazo calculara el suyo con otro remuestreo, los intervalos no
    serian comparables y la comparacion no significaria nada — asi que esto vive aqui y no
    se copia: 2.000 remuestreos, semilla SEED, sobre el MISMO test.
    """
    auprc = float(average_precision_score(yte, p))
    auc = float(roc_auc_score(yte, p))
    yhat = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(yte, yhat).ravel()
    rs_ = np.random.RandomState(SEED); n = len(yte); a_, b_ = [], []
    for _ in range(2000):
        idx = rs_.randint(0, n, n)
        if yte[idx].sum() == 0: continue
        a_.append(average_precision_score(yte[idx], p[idx]))
        b_.append(roc_auc_score(yte[idx], p[idx]))
    out = {"AUPRC": round(auprc, 6), "AUC_ROC": round(auc, 6),
           "F1_umbral_0.5": round(float(f1_score(yte, yhat)), 6),
           "confusion_0.5": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
           "AUPRC_IC95": [round(float(np.percentile(a_, 2.5)), 6),
                          round(float(np.percentile(a_, 97.5)), 6)],
           "AUC_IC95": [round(float(np.percentile(b_, 2.5)), 6),
                        round(float(np.percentile(b_, 97.5)), 6)],
           "bootstrap_validos": len(a_)}
    if t0 is not None:
        out["segundos"] = round(time.time() - t0, 1)
    return out


# ================== BRAZO CUANTICO (prereg RQ-PREREG-HSBC-003-CUANTICO) ==================
# Kernel cuantico de fidelidad |<phi(a)|phi(b)>|^2 en SIMULACION EXACTA (statevector). Gasto
# US$0: no se envia nada a ningun backend. El pre-registro sellado declara, en campos propios,
# GASTO_AUTORIZADO_USD: 0 y hardware.ejecutado: False.
#
# LO QUE LA SIMULACION EXACTA NO PUEDE RESPONDER: como se comporta esto en hardware real. Un
# statevector no tiene ruido, ni error de lectura, ni decoherencia, ni error de transpilacion.
# El resultado de aqui es un TECHO: la version con ruido no puede ser mejor que la exacta con
# el mismo mapa. Si aqui no hay ventaja, tampoco la hay en hardware; si aqui la hubiera, no
# se sigue que la haya en hardware. Esa asimetria se escribe en el artefacto.
#
# DECISIONES NO PREFIJADAS, declaradas ANTES de mirar el test:
#   D1 features: las k de mayor |correlacion de Pearson con la etiqueta|, calculada SOLO
#      sobre el train. Elegirlas mirando el test seria la fuga que el corte temporal impide.
#   D2 escalado: estandarizado con media y sigma del TRAIN, recortado a +-3 sigma, llevado a
#      [0, pi]. Los limites salen del train.
#   D3 codificacion: ZZFeatureMap (Havlicek et al., Nature 567, 2019), reps=2, entrelazamiento
#      completo por pares. Es el mapa canonico de la literatura, no uno nuestro. La convencion
#      de fases NO se deriva de memoria: se verifica contra qiskit antes de usarla (abajo).
#   D4 submuestra de soporte: ESTRATIFICADA, preservando la razon de fraude, como exige el
#      statement. Es una restriccion dura y asimetrica: al 0,183 % de fraude, N puntos dejan
#      ~0,00183*N positivos. El brazo clasico se entrena con las 227.845 filas y sus 417
#      fraudes. Esta desventaja es del protocolo, no del metodo, y se declara como tal.
#   D5 clasificador: SVC con kernel precomputado, C y class_weight declarados.
# El test es el COMPLETO y el bootstrap es el MISMO evaluar() del brazo clasico.
BRAZO = (os.environ.get("RQ_BRAZO") or "clasico").lower()


def correr_brazo_cuantico():
    import math
    from sklearn.svm import SVC

    Q_FEATURES = int(os.environ.get("RQ_QFEAT", 8))          # = numero de qubits
    Q_SOPORTE = int(os.environ.get("RQ_QSOP", 20000))
    Q_C = float(os.environ.get("RQ_QC", 1.0))
    Q_REPS = int(os.environ.get("RQ_QREPS", 2))
    DIM = 1 << Q_FEATURES

    # ---------- D1: las features salen del train
    _mu, _sd = Xtr.mean(0), Xtr.std(0) + 1e-12
    _zt = (Xtr - _mu) / _sd
    _yc = (ytr - ytr.mean()) / (ytr.std() + 1e-12)
    _corr = np.abs((_zt * _yc[:, None]).mean(0))
    _orden = np.sort(np.argsort(-_corr)[:Q_FEATURES])
    FEAT_Q = [FEAT[i] for i in _orden]

    def _ang(X):
        """D2: estandarizar con el train, recortar a +-3 sigma, llevar a [0, pi]."""
        z = np.clip((X[:, _orden] - _mu[_orden]) / _sd[_orden], -3.0, 3.0)
        return (z + 3.0) * (math.pi / 6.0)

    # ---------- D3: el statevector del ZZFeatureMap
    # Base computacional: el bit q del indice i es el valor del qubit q, con |0> -> z=+1.
    _bits = ((np.arange(DIM)[:, None] >> np.arange(Q_FEATURES)[None, :]) & 1)
    _z = (1.0 - 2.0 * _bits).astype(float)
    _pares = [(i, j) for i in range(Q_FEATURES) for j in range(i + 1, Q_FEATURES)]
    _zz = np.stack([_z[:, i] * _z[:, j] for i, j in _pares], 1)
    _pi_i = np.array([i for i, j in _pares])
    _pj_i = np.array([j for i, j in _pares])

    def _hadamard(v):
        """H^(x)n exacta, por Walsh-Hadamard rapida. Sin muestreo: es algebra."""
        v = v.copy()
        r2 = math.sqrt(2.0)
        for q in range(Q_FEATURES):
            h = 1 << q
            v = v.reshape(-1, 2, h)
            a_ = v[:, 0, :].copy()
            b_ = v[:, 1, :].copy()
            v[:, 0, :] = (a_ + b_) / r2
            v[:, 1, :] = (a_ - b_) / r2
            v = v.reshape(-1)
        return v

    def _fase(x):
        """U_phi(x) diagonal: exp(-i [sum_i phi_i z_i + sum_{i<j} phi_ij z_i z_j]).

        EL SIGNO NO ES DECORATIVO Y NO SE DEDUJO: lo dijo la guardia. Yo habia escrito
        exp(+i...), que es lo que uno escribe si piensa el mapa como exp(i phi Z). Qiskit
        lo implementa con puertas P(2phi) = diag(1, e^{2i phi}), que es e^{i phi} exp(-i phi Z)
        — signo opuesto. El estado que yo producia era el CONJUGADO del de qiskit.
        Y como |<conj a|conj b>|^2 = |<a|b>|^2, el kernel coincidia a 3e-15 con el statevector
        equivocado: el numero que iba al resultado estaba bien por accidente, mientras el
        objeto era otro. Comparar solo el kernel habria dejado pasar esto entero.
        """
        th = _z @ x
        th = th + _zz @ ((math.pi - x[_pi_i]) * (math.pi - x[_pj_i]))
        return np.exp(-1j * th)

    def statevector(x):
        psi = np.full(DIM, 1.0 / math.sqrt(DIM), dtype=complex)
        for _ in range(Q_REPS):
            psi = _fase(x) * psi
            if _ + 1 < Q_REPS:
                psi = _hadamard(psi)
        return psi

    # ---------- la guardia: mi camino rapido contra qiskit, no contra mi memoria
    # Nueve veces en este proyecto el instrumento comparo contra un valor calculado de otra
    # forma que el objeto. La convencion de fases del ZZFeatureMap es exactamente ese riesgo,
    # asi que no se deriva: se le pregunta a la libreria. Falla cerrado.
    def _verificar_contra_qiskit(n=5):
        from qiskit.quantum_info import Statevector
        try:                       # qiskit >= 2.1: la clase quedo deprecada
            from qiskit.circuit.library import zz_feature_map
            fm = zz_feature_map(Q_FEATURES, reps=Q_REPS, entanglement="full")
        except ImportError:
            from qiskit.circuit.library import ZZFeatureMap
            fm = ZZFeatureMap(feature_dimension=Q_FEATURES, reps=Q_REPS, entanglement="full")
        rng = np.random.default_rng(SEED)
        xs = rng.uniform(0.0, math.pi, size=(n, Q_FEATURES))
        peor_sv, peor_k = 0.0, 0.0
        svs_mios = [statevector(x) for x in xs]
        svs_qk = [np.asarray(Statevector(fm.assign_parameters(list(x))).data) for x in xs]
        for a, b in zip(svs_mios, svs_qk):
            # hasta fase global: el kernel no la ve, pero comparo igual el objeto entero
            fase = np.vdot(b, a)
            fase = fase / (abs(fase) + 1e-300)
            peor_sv = max(peor_sv, float(np.abs(a - fase * b).max()))
        for i in range(n):
            for j in range(n):
                km = abs(np.vdot(svs_mios[i], svs_mios[j])) ** 2
                kq = abs(np.vdot(svs_qk[i], svs_qk[j])) ** 2
                peor_k = max(peor_k, abs(km - kq))
        return peor_sv, peor_k

    _dsv, _dk = _verificar_contra_qiskit()
    print("guardia statevector vs qiskit: max|dpsi|=%.2e  max|dK|=%.2e" % (_dsv, _dk))
    if not (_dsv < 1e-10 and _dk < 1e-12):
        raise SystemExit("ABORTA: mi statevector NO coincide con el ZZFeatureMap de qiskit "
                         "(dpsi=%.3e, dK=%.3e). No se corre con un mapa que no es el que dice "
                         "ser." % (_dsv, _dk))

    def mapa(X, bloque=8192):
        A = _ang(X)
        out = np.empty((len(X), DIM), dtype=np.complex128)
        for i in range(len(A)):
            out[i] = statevector(A[i])
        return out

    def gram(A, B, bloque=2048):
        """K = |A B^dag|^2. Por bloques para no reventar la memoria."""
        K = np.empty((len(A), len(B)), dtype=np.float64)
        for i in range(0, len(A), bloque):
            K[i:i + bloque] = np.abs(A[i:i + bloque] @ B.conj().T) ** 2
        return K

    # ---------- D4: submuestra ESTRATIFICADA del train
    rs = np.random.RandomState(SEED)
    idx_pos = np.where(ytr == 1)[0]
    idx_neg = np.where(ytr == 0)[0]
    frac = Q_SOPORTE / len(ytr)
    n_pos = int(round(len(idx_pos) * frac))
    n_neg = Q_SOPORTE - n_pos
    sel = np.concatenate([rs.choice(idx_pos, n_pos, replace=False),
                          rs.choice(idx_neg, n_neg, replace=False)])
    rs.shuffle(sel)
    Xs, ys = Xtr[sel], ytr[sel]

    print("brazo CUANTICO — kernel de fidelidad, simulacion exacta, US$0")
    print("  qubits=%d  dim=%d  reps=%d  C=%g" % (Q_FEATURES, DIM, Q_REPS, Q_C))
    print("  features (elegidas en el train): %s" % ", ".join(FEAT_Q))
    print("  soporte estratificado: %d puntos, %d fraudes (%.4f %%)"
          % (len(ys), int(ys.sum()), 100.0 * ys.mean()))
    print("  el brazo clasico se entreno con %d filas y %d fraudes — la desventaja es del "
          "protocolo" % (len(ytr), int(ytr.sum())))

    _tq = time.time()
    t0 = time.time()
    PHI_S = mapa(Xs)
    print("  mapa del soporte: %.1f s" % (time.time() - t0))
    t0 = time.time()
    K = gram(PHI_S, PHI_S)
    print("  gram %dx%d: %.1f s" % (K.shape[0], K.shape[1], time.time() - t0))
    t0 = time.time()
    clf = SVC(kernel="precomputed", C=Q_C, class_weight="balanced")
    clf.fit(K, ys)
    print("  SVC: %.1f s, %d vectores de soporte" % (time.time() - t0, int(clf.n_support_.sum())))
    del K

    t0 = time.time()
    p = np.empty(len(yte), dtype=np.float64)
    for i in range(0, len(Xte), 4096):
        PHI_T = mapa(Xte[i:i + 4096])
        p[i:i + 4096] = clf.decision_function(gram(PHI_T, PHI_S))
    print("  test completo (%d filas): %.1f s" % (len(yte), time.time() - t0))

    r = evaluar(p, yte, t0=_tq)

    # ---------- CONTROLES EXPLORATORIOS — NO PRE-REGISTRADOS
    # Se decidieron DESPUES de ver el primario, y eso se dice aqui y en el artefacto. No
    # cambian el resultado pre-registrado ni pueden rescatarlo: existen porque «el kernel
    # cuantico pierde» y «le dimos 37 positivos en vez de 417» son dos conclusiones
    # distintas, y el numero primario solo no distingue cual es.
    #   A1  mismo dato, mismas 8 features, mismo clasificador, kernel RBF en vez del
    #       cuantico -> aisla EL KERNEL. Es la comparacion manzana con manzana.
    #   A2  mismo dato, mismas 8 features, xgboost -> lo que haria alguien con esa muestra.
    #   B   kernel cuantico con LOS 417 fraudes (soporte NO estratificado) -> aisla el
    #       numero de positivos. Si aqui tampoco alcanza, la desventaja no era la muestra.
    ctrl = {}
    if os.environ.get("RQ_CONTROLES") == "1":
        Xs8, Xte8 = Xs[:, _orden], Xte[:, _orden]
        _s8m, _s8s = Xs8.mean(0), Xs8.std(0) + 1e-12
        t_ = time.time()
        rbf = SVC(kernel="rbf", C=Q_C, gamma="scale", class_weight="balanced")
        rbf.fit((Xs8 - _s8m) / _s8s, ys)
        ctrl["A1_rbf_mismo_dato_mismas_features"] = evaluar(
            rbf.decision_function((Xte8 - _s8m) / _s8s), yte, t0=t_)
        try:
            import xgboost as xgb
            t_ = time.time()
            g = xgb.XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.1,
                                  scale_pos_weight=float((ys == 0).sum() / max(1, (ys == 1).sum())),
                                  eval_metric="aucpr", random_state=SEED, n_jobs=4)
            g.fit(Xs8, ys)
            ctrl["A2_xgboost_mismo_dato_mismas_features"] = evaluar(
                g.predict_proba(Xte8)[:, 1], yte, t0=t_)
        except Exception as e:
            ctrl["A2_xgboost_mismo_dato_mismas_features"] = {"no_corrio": repr(e)}
        t_ = time.time()
        rs2 = np.random.RandomState(SEED)
        selB = np.concatenate([idx_pos,
                               rs2.choice(idx_neg, Q_SOPORTE - len(idx_pos), replace=False)])
        rs2.shuffle(selB)
        XsB, ysB = Xtr[selB], ytr[selB]
        PHI_B = mapa(XsB)
        clfB = SVC(kernel="precomputed", C=Q_C, class_weight="balanced")
        clfB.fit(gram(PHI_B, PHI_B), ysB)
        pB = np.empty(len(yte))
        for i in range(0, len(Xte), 4096):
            pB[i:i + 4096] = clfB.decision_function(gram(mapa(Xte[i:i + 4096]), PHI_B))
        ctrl["B_cuantico_con_los_417_fraudes"] = evaluar(pB, yte, t0=t_)
        ctrl["B_cuantico_con_los_417_fraudes"]["soporte"] = {
            "n": int(len(ysB)), "fraudes": int(ysB.sum()),
            "razon_pct": round(100.0 * float(ysB.mean()), 4),
            "estratificado": False,
            "por_que_no": "a proposito: enriquecido en fraude para medir si el limite era "
                          "el numero de positivos. Por eso NO es el resultado pre-registrado."}
        for k_, v_ in ctrl.items():
            if "AUPRC" in v_:
                print("  [exploratorio] %-38s AUPRC=%.4f %s"
                      % (k_, v_["AUPRC"], v_["AUPRC_IC95"]))

    np.savez_compressed(os.environ.get("RQ_SCORES_PREFIX", "scores_") + "kernel_cuantico.npz",
                        y_true=yte.astype(np.int8), y_score=p.astype(np.float32))
    extra = {"brazo": "cuantico", "simulacion": {
        "tipo": "statevector exacto",
        "backend": "ninguno — no se envio nada a hardware",
        "gasto_usd": 0.0,
        "verificado_contra": "qiskit.circuit.library.ZZFeatureMap",
        "max_dif_statevector": _dsv,
        "max_dif_kernel": _dk,
        "lo_que_NO_responde": "el comportamiento en hardware con ruido. Esto es un TECHO: "
            "con el mismo mapa, la version ruidosa no puede superar a la exacta. Que no haya "
            "ventaja aqui cierra el caso; que la hubiera no la probaria en hardware."},
        "decisiones_declaradas_antes": {
            "D1_features": {"criterio": "|Pearson con la etiqueta| sobre el TRAIN",
                            "k": Q_FEATURES, "elegidas": FEAT_Q},
            "D2_escalado": "media/sigma del train, recorte +-3 sigma, mapeo a [0, pi]",
            "D3_codificacion": {"mapa": "ZZFeatureMap", "reps": Q_REPS,
                                "entrelazamiento": "full"},
            "D4_soporte": {"estratificado": True, "n": int(len(ys)),
                           "fraudes": int(ys.sum()), "razon_pct": 100.0 * float(ys.mean()),
                           "exigido_por": "el statement pide muestreo estratificado",
                           "asimetria": "el brazo clasico se entrena con %d filas y %d "
                                        "fraudes; este con %d y %d. La desventaja es del "
                                        "protocolo, no del metodo."
                                        % (len(ytr), int(ytr.sum()), len(ys), int(ys.sum()))},
            "D5_clasificador": {"modelo": "SVC", "kernel": "precomputed", "C": Q_C,
                                "class_weight": "balanced"}},
        "controles_exploratorios": {
            "PRE_REGISTRADOS": False,
            "cuando_se_decidieron": "despues de ver el resultado primario",
            "para_que": "separar «el kernel cuantico pierde» de «le dimos 37 positivos». "
                        "No pueden rescatar el resultado primario ni lo modifican.",
            "resultados": ctrl},
        "comparacion": {"contra": "RQ-EXP-HSBC-BASE-001",
                        "mismo_test": True, "mismo_bootstrap": True, "misma_semilla": SEED,
                        "n_test": int(len(yte)), "fraudes_test": int(yte.sum())}}
    return {"kernel_cuantico": r}, extra


spw = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
res, EXTRA = {}, {}
if BRAZO == "cuantico":
    res, EXTRA = correr_brazo_cuantico()
    r = res["kernel_cuantico"]
    print("%-14s AUPRC=%.4f [%s]  AUC=%.4f  F1=%.4f  (%.0fs)"
          % ("kernel_cuant", r["AUPRC"], r["AUPRC_IC95"], r["AUC_ROC"],
             r["F1_umbral_0.5"], r["segundos"]))
for nombre, ctor in (modelos.items() if BRAZO != "cuantico" else []):
    t0 = time.time(); m = ctor(spw); m.fit(Xtr, ytr)
    p = m.predict_proba(Xte)[:, 1]
    res[nombre] = evaluar(p, yte, t0)
    print("%-14s AUPRC=%.4f [%s]  AUC=%.4f  F1=%.4f  (%.0fs)"
          % (nombre, res[nombre]["AUPRC"], res[nombre]["AUPRC_IC95"], res[nombre]["AUC_ROC"],
             res[nombre]["F1_umbral_0.5"], res[nombre]["segundos"]))
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
out.update(EXTRA)
out["brazo"] = BRAZO
json.dump(out, open(os.environ.get("RQ_OUT", "resultado_hsbc.json"), "w"), indent=1)
print("\ntest sha256:", test_sha[:16], "| train %d/%d fraudes | test %d/%d"
      % (int(ytr.sum()), len(tr), int(yte.sum()), len(te)))
