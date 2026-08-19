#!/usr/bin/env python3
"""El corredor: la bateria de verificacion post-CI, siempre y con denominador.

Uso:
  python3 tools/replicar.py verificar --track hsbc            # todos los artefactos
  python3 tools/replicar.py verificar --track hsbc ARCHIVO    # uno

Cada tramo termina en OK, FALLA o SALTADO. Un tramo que no se pudo ejercer entra al
resumen como SALTADO — nunca como silencio (CLAUDE.md §5 quater: verde no es cubierto).
Sale con codigo != 0 si hay FALLA; los SALTADOS no fallan pero se listan y se cuentan.
"""
import glob, hashlib, json, os, subprocess, sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def verificar_artefacto(ruta, cfg):
    tramos = []          # (nombre, estado, detalle)
    def t(nombre, estado, detalle=""):
        tramos.append({"tramo": nombre, "estado": estado, "detalle": detalle})

    base = os.path.basename(ruta)
    d = json.load(open(ruta))

    # 1. integridad del nombre
    h = sha256(ruta)
    if "@" in base:
        dec = base.split("@")[1].split(".")[0]
        t("integridad_@", "OK" if h.startswith(dec) else "FALLA",
          "%s vs %s" % (dec, h[:8]))
    else:
        t("integridad_@", "SALTADO", "el nombre no declara hash")

    # 2. el dato es el del manifest sellado
    decl = d.get("arff_sha256")
    if decl is None:
        t("dato_vs_manifest", "FALLA", "el artefacto no declara arff_sha256")
    else:
        t("dato_vs_manifest", "OK" if decl == cfg["datos"]["arff_sha256"] else "FALLA",
          decl[:16])

    # 3. procedencia del harness: el vivo o una copia archivada
    hs = d.get("harness_sha256")
    if hs is None:
        t("harness_sha256", "FALLA", "ausente")
    else:
        vivo = sha256(os.path.join(RAIZ, cfg["harness"]["ruta"]))
        if hs == vivo:
            t("harness_sha256", "OK", "== harness vivo")
        else:
            archivadas = {sha256(f): f for f in
                          glob.glob(os.path.join(RAIZ, cfg["harness"]["archivadas"]))}
            if hs in archivadas:
                t("harness_sha256", "OK",
                  "== %s" % os.path.basename(archivadas[hs]))
            else:
                t("harness_sha256", "FALLA", "no resuelve a vivo ni archivado")

    # 4. el prereg que el artefacto cita esta sellado en el repo
    pr = d.get("prereg")
    if pr is None:
        t("prereg_citado", "SALTADO", "artefacto sin campo prereg (baseline v1)")
    else:
        hay = glob.glob(os.path.join(RAIZ, "prereg", "**", "*%s*" % pr), recursive=True)
        t("prereg_citado", "OK" if hay else "FALLA", pr)

    # 5. campos de guardia segun el modo
    modo = "ataque" if d.get("ataque") else "baseline"
    faltan = [c for c in cfg["guardias"]["campos_siempre"] +
              cfg["guardias"]["campos_" + modo] if c not in d]
    t("campos_de_guardia[%s]" % modo, "OK" if not faltan else "FALLA",
      "faltan: %s" % faltan if faltan else "todos")

    # 6. recomputo de metricas desde scores crudos, si existen
    if modo == "baseline":
        try:
            import numpy as np
            from sklearn.metrics import average_precision_score, roc_auc_score
            hechos = 0
            for m, decl_m in d.get("modelos", {}).items():
                fs = glob.glob(os.path.join(os.path.dirname(ruta),
                                            "scores_%s@*.npz" % m))
                if not fs:
                    continue
                z = np.load(fs[0]); y, p = z["y_true"], z["y_score"]
                ok = (abs(average_precision_score(y, p) - decl_m["AUPRC"]) < 5e-5 and
                      abs(roc_auc_score(y, p) - decl_m["AUC_ROC"]) < 5e-5)
                if not ok:
                    t("recomputo_scores[%s]" % m, "FALLA", "no calza")
                hechos += 1
            t("recomputo_scores", "OK" if hechos else "SALTADO",
              "%d modelos recomputados" % hechos if hechos else "sin npz publicados")
        except ImportError:
            t("recomputo_scores", "SALTADO", "sin sklearn en este entorno")
    else:
        # en modo ataque el resumen se recomputa de las corridas
        vals = [r["AUPRC"] for r in d.get("corridas", [])]
        if vals:
            import statistics
            media = statistics.mean(vals)
            t("recomputo_resumen", "OK" if abs(media - d["resumen"]["AUPRC_media"]) < 5e-5
              else "FALLA", "media %.6f" % media)
        else:
            t("recomputo_resumen", "FALLA", "sin corridas")

    # 7. ¿hay sello que cite este artefacto? (estado, no fallo: sellar es acto aparte)
    r = subprocess.run(["grep", "-rl", h, os.path.join(RAIZ, "runs")],
                       capture_output=True, text=True)
    t("sello_que_lo_cita", "OK" if r.stdout.strip() else "SALTADO",
      os.path.basename(r.stdout.split("\n")[0]) if r.stdout.strip() else
      "sin sellar todavia")

    return {"artefacto": base, "tramos": tramos,
            "denominador": {"ejercidos": sum(1 for x in tramos if x["estado"] != "SALTADO"),
                            "ok": sum(1 for x in tramos if x["estado"] == "OK"),
                            "fallados": sum(1 for x in tramos if x["estado"] == "FALLA"),
                            "saltados": sum(1 for x in tramos if x["estado"] == "SALTADO"),
                            "total": len(tramos)}}

def main():
    if len(sys.argv) < 3 or sys.argv[1] != "verificar":
        raise SystemExit(__doc__)
    args = sys.argv[2:]
    track = args[args.index("--track") + 1]
    cfg = tomllib.load(open(os.path.join(RAIZ, "desafios", "%s.toml" % track), "rb"))
    objetivos = [a for a in args if a.endswith(".json") and "--" not in a]
    if not objetivos:
        objetivos = sorted(glob.glob(os.path.join(RAIZ, cfg["track"]["resultados"],
                                                  "*.json")))
    informes, fallo = [], False
    for o in objetivos:
        inf = verificar_artefacto(o, cfg)
        informes.append(inf)
        den = inf["denominador"]
        print("%-58s %d OK / %d FALLA / %d SALTADO (de %d)"
              % (inf["artefacto"][:58], den["ok"], den["fallados"], den["saltados"],
                 den["total"]))
        for x in inf["tramos"]:
            if x["estado"] != "OK":
                print("    %-26s %-8s %s" % (x["tramo"], x["estado"], x["detalle"]))
        fallo |= den["fallados"] > 0
    salida = {"track": track, "artefactos": len(informes), "informes": informes}
    out = os.environ.get("RQ_VERIFICACION_OUT")
    if out:
        json.dump(salida, open(out, "w"), indent=1)
    print("\n%d artefactos verificados; fallados en total: %d"
          % (len(informes), sum(i["denominador"]["fallados"] for i in informes)))
    sys.exit(1 if fallo else 0)

if __name__ == "__main__":
    main()
