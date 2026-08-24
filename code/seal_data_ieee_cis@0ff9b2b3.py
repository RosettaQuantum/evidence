#!/usr/bin/env python3
"""Manifiesto del dataset IEEE-CIS, sellado ANTES de la primera corrida de entrenamiento.

POR QUE EXISTE
--------------
La guardia (b) del pre-registro RQ-PREREG-HSBC-001 lo exige: los sha256 de los archivos
exactos se sellan ANTES de que exista un modelo, para que ningun resultado pueda elegir
sus datos despues de verlos.

QUE SE PUBLICA Y QUE NO
-----------------------
NINGUN dato de IEEE-CIS entra al repositorio publico. Las reglas de Kaggle (§7.B)
prohiben redistribuirlo, y §7.A lo limita a uso NO comercial; se usa solo como benchmark
dentro del challenge, al amparo de la designacion del organizador (tabla §6.1 del
statement). Lo que viaja es este manifiesto: hashes, tamanos y censo. Cada verificador
baja el dato con su propia cuenta.

LA DISTINCION QUE ESTE MANIFIESTO NO BORRA
------------------------------------------
Kaggle publica `totalBytes` por archivo, asi que **los tamanos tienen ancla externa**.
Kaggle NO publica checksums: **los sha256 los computamos nosotros y NO certifican
procedencia** — fijan los bytes para que la corrida sea reproducible. Calzar en tamano no
es calzar en bytes, y el manifiesto lo dice en vez de dejarlo implicito.

Por eso el zip entra como RAIZ de la cadena: es el unico artefacto que vino directo del
endpoint; los CSV son producto de descomprimirlo en este Mac.

SEPARACION DE DEBERES
---------------------
El bloque `medido_por_el_laboratorio` lo recompute yo, aqui, sobre los archivos. El bloque
`declarado_por_el_notario` son los campos de la descarga, que solo la sesion que la corrio
puede sostener. No se mezclan, y lo que nadie puede sostener se declara AUSENTE en vez de
estimarse.

Ningun backend de pago. Costo US$0.
"""
import csv, hashlib, json, os, shutil, sys
csv.field_size_limit(10**9)
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from guardia_procedencia import exigir_procedencia
from reloj_sello import ahora_stamp, ahora_iso, coherentes

DATOS = os.path.join(RAIZ, "lab-hsbc-2026-08-20", "ieee-cis")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

# --- lo que el notario declara y solo el puede sostener -----------------------------
NOTARIO = {
    "quien_descargo": "sesion de coordinacion (notario)",
    "endpoint": "GET https://www.kaggle.com/api/v1/competitions/data/download-all/"
                "ieee-fraud-detection  (Authorization: Bearer, -L)",
    "cuenta_kaggle": "nicholasiakl",
    "cuenta_confirmada_por": "Nicholas, desde la pantalla de su cuenta",
    "acepto_las_reglas_de_la_competencia": True,
    "como_se_comprobo_la_aceptacion": "competitions/list?group=entered paso de vacio a "
        "listar ieee-fraud-detection.",
    "fin_de_la_descarga_utc": "2026-08-24T16:43:45Z",
    "inicio_de_la_descarga": None,
    "inicio_AUSENTE_por_que": "no se registro; la linea se sobrescribio. Se declara "
        "ausente en vez de estimarse.",
    "ancla_externa_de_TAMANOS": "totalBytes por archivo de "
        "/api/v1/competitions/data/list/ieee-fraud-detection; los cinco calzan.",
    "SIN_ancla_externa_de_BYTES": "Kaggle no publica checksums. Los sha256 de este "
        "manifiesto los computamos nosotros: fijan reproducibilidad, NO certifican "
        "procedencia.",
}

ARCHIVOS = ["train_transaction.csv", "train_identity.csv", "test_transaction.csv",
            "test_identity.csv", "sample_submission.csv"]
ZIP = "ieee-fraud-detection.zip"

inventario = []
for n in ARCHIVOS + [ZIP]:
    p = os.path.join(DATOS, n)
    inventario.append({"archivo": n, "sha256": "sha256:" + sha(p),
                       "bytes": os.path.getsize(p),
                       "rol": "raiz de la cadena (unico artefacto directo del endpoint)"
                              if n == ZIP else "extraido del zip en este Mac"})

# --- censo, medido aqui -------------------------------------------------------------
def censo(nombre, con_etiqueta):
    r = csv.reader(open(os.path.join(DATOS, nombre), newline="", encoding="utf-8",
                        errors="replace"))
    h = next(r)
    iDT = h.index("TransactionDT") if "TransactionDT" in h else None
    iY = h.index("isFraud") if "isFraud" in h else None
    dt, y = [], []
    n = 0
    for row in r:
        n += 1
        if iDT is not None and len(row) > iDT: dt.append(int(row[iDT]))
        if iY is not None and len(row) > iY: y.append(int(row[iY]))
    out = {"filas": n, "columnas": len(h), "tiene_isFraud": iY is not None}
    if dt: out["TransactionDT"] = {"min": min(dt), "max": max(dt),
                                   "span_dias": round((max(dt)-min(dt))/86400, 2)}
    if y:
        out["fraudes"] = sum(y); out["tasa_fraude"] = round(sum(y)/n, 6)
    return out, dt, y

c_tr, dt_tr, y_tr = censo("train_transaction.csv", True)
c_te, dt_te, _ = censo("test_transaction.csv", False)
c_itr, _, _ = censo("train_identity.csv", False)
c_ite, _, _ = censo("test_identity.csv", False)

# --- la consecuencia de la particion del pre-registro, medida ANTES de entrenar ------
o = sorted(range(len(dt_tr)), key=lambda i: dt_tr[i]); k = int(len(o)*0.8)
def tramo(g):
    d = [dt_tr[i] for i in g]; f = sum(y_tr[i] for i in g)
    return {"filas": len(g), "fraudes": f, "tasa_fraude": round(f/len(g), 6),
            "TransactionDT": [min(d), max(d)],
            "ventana_dias": round((max(d)-min(d))/86400, 2)}
part = {"regla": "80/20 por TransactionDT, la del pre-registro RQ-PREREG-HSBC-001 §3",
        "train": tramo(o[:k]), "test": tramo(o[k:])}
part["cambio_relativo_de_la_tasa_pct"] = round(
    100*(part["test"]["tasa_fraude"]-part["train"]["tasa_fraude"])/part["train"]["tasa_fraude"], 1)

# --- guardia: falla cerrado ---------------------------------------------------------
if c_tr["filas"] != 590540:
    raise SystemExit("ABORTA: el statement declara 590.540 filas de entrenamiento y se "
                     "midieron %d" % c_tr["filas"])
if c_te["tiene_isFraud"]:
    raise SystemExit("ABORTA: test_transaction.csv trae isFraud — el diseno de este "
                     "manifiesto asume que NO, y la evaluacion cambiaria por completo")
for it in inventario:
    if it["bytes"] <= 0: raise SystemExit("ABORTA: %s vacio" % it["archivo"])
# El §7.B de Kaggle prohibe redistribuir. La proteccion real no es acordarse: es que los
# datos no esten donde un `git add` pueda alcanzarlos. Se comprueba subiendo por el arbol.
_d = os.path.abspath(DATOS)
while True:
    if os.path.exists(os.path.join(_d, ".git")):
        raise SystemExit("ABORTA: los datos de IEEE-CIS estan dentro del repositorio %s. "
                         "El §7.B de Kaggle prohibe redistribuirlos y un commit accidental "
                         "los publicaria." % _d)
    _p = os.path.dirname(_d)
    if _p == _d: break
    _d = _p

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
NOMBRE = ("RosettaQ__MANIFEST__RQ-DATA-HSBC-IEEE-001__%s__"
          "ieee-cis-manifiesto-antes-de-entrenar.json" % STAMP)
PREREG = os.path.join(EV, "prereg", "2026", "08",
    "RosettaQ__PREREG__RQ-PREREG-HSBC-001__20260820T1500Z__fraude-tarjetas-diseno-y-protocolo.json")
pre = json.load(open(PREREG)); assert rs.verify(pre)

doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-DATA-HSBC-IEEE-001", "type": "MANIFEST",
    "is_demo": False,
    "scope_note": "Manifiesto del dataset de BENCHMARK del track HSBC (IEEE-CIS), sellado "
                  "ANTES de la primera corrida de entrenamiento, como exige la guardia (b) "
                  "del pre-registro. NINGUN dato de IEEE-CIS entra al repositorio publico: "
                  "las reglas de Kaggle prohiben redistribuirlo. Lo que viaja son hashes, "
                  "tamanos y censo; cada verificador baja el dato con su propia cuenta.",
    "prereg": {"file_id": pre["meta"]["file_id"],
               "content_hash": pre["meta"]["content_hash"]},
}, "w6": {
    "que": {
        "dataset": "IEEE-CIS Fraud Detection (Vesta) — benchmark designado por el "
                   "organizador en la tabla §6.1 del statement",
        "licencia_y_limites": {
            "kaggle_7A": "uso NO comercial. Se usa solo como benchmark dentro del "
                         "challenge, al amparo de la designacion del organizador.",
            "kaggle_7B": "prohibido redistribuir. Por eso ningun byte del dataset entra "
                         "al repositorio publico y la referencia viaja por sha256.",
            "comprobado": "la carpeta de datos no esta dentro de ningun repositorio git.",
        },
        "medido_por_el_laboratorio": {
            "inventario": inventario,
            "censo_train_transaction": c_tr,
            "censo_test_transaction": c_te,
            "censo_train_identity": c_itr,
            "censo_test_identity": c_ite,
            "particion_temporal_del_prereg": part,
            "HALLAZGO_test_de_kaggle_sin_etiquetas":
                "test_transaction.csv NO trae isFraud: es el test de la competencia con "
                "etiquetas ocultas. Por lo tanto NINGUNA metrica propia puede calcularse "
                "sobre el, y la evaluacion sale de una particion temporal DENTRO de "
                "train_transaction.csv. Se declara aqui para que nadie lo asuma al reves.",
            "hueco_temporal_entre_train_y_test_de_kaggle_dias":
                round((c_te["TransactionDT"]["min"]-c_tr["TransactionDT"]["max"])/86400, 2),
        },
        "declarado_por_el_notario": NOTARIO,
        "contraste_con_ULB": {
            "por_que_importa": "el pre-registro fija particion temporal en los dos "
                "datasets. La pregunta que decide cuanto vale esa particion es cuanto "
                "FUTURO ve el test, y las dos respuestas no se parecen.",
            "ULB_ventana_de_test_horas": 7.65,
            "IEEE_ventana_de_test_dias": part["test"]["ventana_dias"],
            "ULB_cambio_de_tasa_pct": -28.0,
            "IEEE_cambio_de_tasa_pct": part["cambio_relativo_de_la_tasa_pct"],
            "medido_como": "misma regla 80/20 temporal en los dos. Las cifras de ULB se "
                "recomputaron desde creditcard.arff, cuyo sha256 calza con el que sella "
                "RQ-DATA-HSBC-ULB-001, y reproducen la particion del run "
                "RQ-EXP-HSBC-BASE-001 (227.845/417 y 56.962/75).",
        },
        "ambiguedad_del_statement_resuelta":
            "el statement menciona «~24,000 rows» en su guia de hardware. Medido: IEEE-CIS "
            "tiene 590.540 filas de entrenamiento, que es exactamente lo que el mismo "
            "statement declara. Las ~24.000 no corresponden a este dataset ni a ninguno de "
            "los tres designados (ULB 284.807; Sparkov ~1,8 M).",
    },
    "como": {
        "receta_para_un_tercero":
            "1) crear cuenta en Kaggle y aceptar las reglas de ieee-fraud-detection; "
            "2) descargar con la API oficial; 3) descomprimir; 4) recomputar los sha256 de "
            "este manifiesto. Si difieren, NO seguir: los resultados de este track estan "
            "atados a estos bytes.",
        "medido_por": {"archivo": "evidence-staging/seal_data_ieee_cis.py"},
    },
    "cuando": {"archived_at": ISO},
    "donde": {"datos": "Mac local, fuera de todo repositorio git",
              "compute": "local, sin backend de pago"},
    "porque": {"question": "fijar los bytes exactos del benchmark ANTES de que exista un "
                           "modelo, para que ningun resultado pueda elegir sus datos "
                           "despues de verlos."},
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio (censo y hashes)",
              "notario": "sesion de coordinacion (descarga y sus campos)",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "quien descarga declara la descarga; quien sella "
                                       "recomputa los bytes; el notario ancla."},
}}
_yo = os.path.basename(__file__); _mi = sha(__file__)
exigir_procedencia(doc, extra=(__file__,))
rs.seal(doc, harness=(_yo, "1.0.0", "sha256:" + _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(EV, "manifests", NOMBRE)
pub = os.path.join(EV, "code", "%s@%s.py" % (_yo[:-3], _mi[:8]))
assert not os.path.exists(dst) and not os.path.exists(pub)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
shutil.copy2(__file__, pub)
assert rs.verify(json.load(open(dst)))
print("MANIFIESTO sellado:", doc["meta"]["content_hash"])
print("  train: %d filas, %d fraudes (%.3f %%), %.2f dias"
      % (c_tr["filas"], c_tr["fraudes"], 100*c_tr["tasa_fraude"], c_tr["TransactionDT"]["span_dias"]))
print("  ventana de test: %.2f dias (ULB: 7,65 horas)" % part["test"]["ventana_dias"])
print("  sellador publicado:", os.path.basename(pub))
