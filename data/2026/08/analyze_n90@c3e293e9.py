#!/usr/bin/env python3
"""Recómputo independiente del N=90 (deja-una-fuera, sin fuga).

QUÉ HACE Y POR QUÉ
------------------
Recompone los Fisher **desde los conteos crudos** (`n_ge`, `nperm`) de cada proteína,
que es como lo haría un tercero, y los compara con lo publicado. No hereda ninguna cifra
de la sesión coordinadora.

LA TRAMPA QUE ESTE ARCHIVO EXISTE PARA NO REPETIR
-------------------------------------------------
La corrida anterior (31531185175) publicaba `p = 0.0` para una proteína —`SLC6A4_ALLO`—
porque el p se redondeaba a 3 decimales y el suyo caía bajo el piso. Un p de cero no
existe: el test de permutación tiene **piso 1/(nperm+1)**. Metido a Fisher, ese cero
llevaba la combinada de 4,9e-09 a 6,8e-241 — 232 órdenes, todos en la dirección de
parecer un resultado más fuerte del medido. Por eso el artefacto nuevo guarda los
conteos y el p pasa a ser cantidad derivada.

Este script **falla cerrado** si encuentra un p publicado en cero o si una fila no trae
sus conteos: sin el dato crudo, el recómputo vuelve a depender de saber que existe un
piso, que es justo el conocimiento tácito que hacía irreproducible el artefacto.

Uso:  python3 analyze_n90.py
"""
import json
import math
import os

from scipy.stats import chi2

AQUI = os.path.dirname(os.path.abspath(__file__))
QRUN = os.path.join(os.path.dirname(AQUI), "quantum-run")
ART = os.environ.get("N90_ART") or os.path.join(
    QRUN, "resultados_n90", "RQ-EXP-N90-LOPO@116e42d4.json")
OUT = os.environ.get("N90_OUT") or os.path.join(AQUI, "n90_result.json")
LOG = os.path.join(AQUI, "n90_log.jsonl")

BRAZOS = [("armA_manager", "A", "gestor cuantico"),
          ("armB_ml", "B", "ML de features"),
          ("armC_stacked", "C", "ML apilado de propagadores")]


def anota(evento, **kv):
    with open(LOG, "a") as f:
        f.write(json.dumps({"evento": evento, **kv}, ensure_ascii=False) + "\n")


def fisher(ps):
    X = -2.0 * sum(math.log(p) for p in ps)
    return X, float(chi2.sf(X, 2 * len(ps)))


def ps_desde_conteos(filas, clave):
    """p por proteina desde el dato crudo, con el piso explicito. Falla cerrado."""
    ps, sin_conteo = [], []
    pre = (clave + "_") if clave else ""
    for f in filas:
        ng, npm = f.get(pre + "n_ge"), f.get(pre + "nperm")
        if ng is None or npm is None:
            sin_conteo.append(f.get("name", "?"))
            continue
        ps.append(max(ng / float(npm), 1.0 / (npm + 1)))
    return ps, sin_conteo


if __name__ == "__main__":
    d = json.load(open(ART))
    filas = d["per_protein"]
    open(LOG, "w").close()
    anota("inicio", artefacto=os.path.basename(ART), n_filas=len(filas))

    # --- guardia 1: ningun p publicado puede ser exactamente cero
    ceros = [b for b, _, _ in BRAZOS if d["fisher_p"].get(b) == 0.0]
    if ceros:
        raise SystemExit("p publicada en CERO en %s — irreproducible por construccion. "
                         "Un p de permutacion no puede ser cero: el piso es 1/(nperm+1)."
                         % ceros)

    brazos = []
    for pub_key, k, nombre in BRAZOS:
        ps, sin_conteo = ps_desde_conteos(filas, k)
        anota("intento", brazo=k, con_conteo=len(ps), sin_conteo=len(sin_conteo))
        if sin_conteo:
            raise SystemExit("brazo %s: %d de %d filas sin conteos crudos (%s…). Sin el "
                             "dato crudo el recomputo depende de saber que existe un piso."
                             % (k, len(sin_conteo), len(filas), sin_conteo[:3]))
        X, p = fisher(ps)
        pub = d["fisher_p"][pub_key]
        brazos.append({
            "brazo": pub_key, "nombre": nombre,
            "chi2": round(X, 2), "grados_de_libertad": 2 * len(ps),
            "p_recomputado": p, "p_publicado": pub,
            "razon_recomputado_sobre_publicado": round(p / pub, 4),
            "reproduce": abs(p - pub) / pub < 0.01,
            "n_significativas_p05": sum(1 for x in ps if x < 0.05),
            "n_proteinas": len(ps),
            "p_minimo": min(ps), "en_el_piso": sum(1 for x in ps
                                                   if abs(x - 1.0 / 2001) < 1e-9),
        })
        anota("medido", brazo=k, p_recomputado=p, reproduce=brazos[-1]["reproduce"])

    # --- las ablaciones, que antes eran tres ceros incomprobables
    abl = []
    for nombre, blk in d.get("ablations", {}).items():
        fs = blk.get("per_protein")
        if not fs:
            abl.append({"ablacion": nombre, "recomputable": False,
                        "por_que": "no trae per_protein"})
            continue
        # las ablaciones usan claves planas (`n_ge`/`nperm`), no prefijadas por brazo
        ps, sin_conteo = ps_desde_conteos(fs, "")
        if sin_conteo:
            raise SystemExit("ablacion %s: %d de %d filas sin conteos crudos"
                             % (nombre, len(sin_conteo), len(fs)))
        X, p = fisher(ps)
        abl.append({"ablacion": nombre, "recomputable": True,
                    "p_recomputado": p, "p_publicado": blk.get("fisher_p"),
                    "reproduce": abs(p - blk.get("fisher_p", 0)) / max(blk.get("fisher_p", 1), 1e-300) < 0.01,
                    "n_significativas": blk.get("n_sig"), "dropped": blk.get("dropped")})

    distintos = len({round(a.get("p_recomputado", 0), 12) for a in abl if a["recomputable"]})

    res = {
        "_doc": "Recomputo independiente del N=90 desde los conteos crudos. No hereda "
                "ninguna cifra: los tres Fisher se rehacen como los rehace un tercero.",
        "artefacto": {"archivo": os.path.basename(ART),
                      "ruta": ART,
                      "sha256": "sha256:" + __import__("hashlib").sha256(
                          open(ART, "rb").read()).hexdigest()},
        "denominador": {"proteinas_declaradas": d["n_proteins"],
                        "filas_en_per_protein": len(filas),
                        "calzan": d["n_proteins"] == len(filas)},
        "brazos": brazos,
        "todos_reproducen": all(b["reproduce"] for b in brazos),
        "ablaciones": abl,
        "ablaciones_distinguibles": distintos,
        "por_metodo": d.get("mean_pct_by_method"),
        "elecciones_del_gestor": d.get("manager_choices"),
    }
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    anota("fin", todos_reproducen=res["todos_reproducen"])

    print("N=90 — %d proteinas declaradas, %d filas (calzan: %s)"
          % (d["n_proteins"], len(filas), res["denominador"]["calzan"]))
    print("\n%-14s %10s %6s %14s %14s %7s %6s"
          % ("brazo", "chi2", "gl", "recomputado", "publicado", "razon", "sig."))
    for b in brazos:
        print("%-14s %10.1f %6d %14.4g %14.4g %7.2f %6d"
              % (b["brazo"], b["chi2"], b["grados_de_libertad"], b["p_recomputado"],
                 b["p_publicado"], b["razon_recomputado_sobre_publicado"],
                 b["n_significativas_p05"]))
    print("\nreproducen los tres:", res["todos_reproducen"])
    print("\nABLACIONES (antes eran tres 0.0 identicos e incomprobables)")
    for a in abl:
        if a["recomputable"]:
            print("  %-24s %12.4g  reproduce=%s  sig=%s"
                  % (a["ablacion"], a["p_recomputado"], a["reproduce"], a["n_significativas"]))
        else:
            print("  %-24s NO recomputable: %s" % (a["ablacion"], a["por_que"]))
    print("  -> valores distintos entre si: %d de %d" % (distintos, len(abl)))
    print("\nPOR METODO:", res["por_metodo"])
    print("ELECCIONES DEL GESTOR:", res["elecciones_del_gestor"])
