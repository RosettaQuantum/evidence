"""Manifiesto de datos ULB: se mide TODO del archivo descargado, nada se hereda."""
import hashlib, json
import pandas as pd
from scipy.io import arff  # lector estandar
raw = open("creditcard.arff", "rb").read()
import io, re
txt = raw.decode("utf-8")
i = txt.lower().index("@data")
cols = re.findall(r"@attribute\s+'?([^\s']+)'?", txt[:i], re.I)
df = pd.read_csv(io.StringIO(txt[i+5:]), names=cols, quotechar="'")
frac = df["Class"].astype(int)
man = {
 "dataset": "European Cardholder (ULB) — creditcard",
 "fuente": {"url": "https://openml.org/data/v1/download/1673544/creditcard.arff",
            "openml_id": 1597, "version": 1,
            "md5_declarado_por_openml": "178bcf9bb1f31a3dfe12d0e577884add",
            "md5_medido": hashlib.md5(raw).hexdigest(),
            "sha256_medido": hashlib.sha256(raw).hexdigest(),
            "licencia": "OpenML lo publica como 'Public'; la tabla §6.1 del statement "
                        "de HSBC lo lista via Kaggle como 'Open Database License'. Ambas "
                        "procedencias se declaran; ninguna restringe este uso."},
 "censo": {"filas": int(len(df)), "columnas": int(df.shape[1]),
           "nombres_columnas": cols,
           "fraudes": int(frac.sum()),
           "no_fraudes": int((1-frac).sum()),
           "tasa_fraude": round(float(frac.mean()), 8),
           "rango_Time_s": [float(df.Time.min()), float(df.Time.max())],
           "nulos_totales": int(df.isna().sum().sum())},
}
json.dump(man, open("01_manifiesto_ulb.json", "w"), indent=1)
print(json.dumps(man["censo"], indent=1)[:400])
print("sha256:", man["fuente"]["sha256_medido"][:16], "| md5 calza:",
      man["fuente"]["md5_medido"] == man["fuente"]["md5_declarado_por_openml"])
