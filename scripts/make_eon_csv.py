#!/usr/bin/env python3
"""Genera RosettaQ-EON-sealed-runs.csv A PARTIR de los archivos sellados de la serie
EXP-0033 (track E.ON, expansion de red).

Incluye a proposito DOS columnas para la red: lo que dice el nombre del archivo y lo
que dicen los parametros internos con los que corrio el harness. Estaban en desacuerdo
en 6 de 9 runs (errata del 29-jul, ver NOTES/2026-07-29-eon-scale-errata.md), y la
manera de tratar eso no es elegir la que suena mejor: es publicar las dos y dejar la
contradiccion a la vista hasta que el laboratorio re-selle.

Uso: python3 scripts/make_eon_csv.py
"""
import csv, glob, json, os, re, subprocess, sys

sys.path.insert(0, "tools")
from verify_seals import identify

OTS = os.path.expanduser("~/Library/Python/3.9/bin/ots")
OUT = "RosettaQ-EON-sealed-runs.csv"


def fecha_de(doc):
    """Fecha del archivo, tolerando las dos formas que ha tenido `cuando`.

    Era un objeto {archived_at | published_at | started_at}; desde EXP-0007-020 el
    laboratorio tambien emite una cadena ISO suelta. Un PREREG la lleva en
    prereg.committed_at_utc. Como los archivos ya estan sellados y anclados, no se
    pueden normalizar: se normaliza la lectura.
    """
    c = (doc.get("w6") or {}).get("cuando")
    if isinstance(c, str):
        return c[:10]
    if isinstance(c, dict):
        for k in ("archived_at", "published_at", "started_at"):
            if c.get(k):
                return str(c[k])[:10]
    return str((doc.get("prereg") or {}).get("committed_at_utc", ""))[:10]


def bitcoin_blocks(ots_path):
    try:
        info = subprocess.run([OTS, "info", ots_path], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return []
    return sorted(set(int(b) for b in re.findall(r"BitcoinBlockHeaderAttestation\((\d+)\)", info)))


# El alcance se DECLARA y se cuenta, no se codifica en un mes y un prefijo.
#
# La version anterior era `runs/2026/07/*EXP-0033-*.json`: mes fijo y una sola convencion
# de identificador. El 2026-08-13 se sellaron ocho corridas nuevas de este mismo track
# —en `runs/2026/08/` y con identificadores `RQ-EXP-EON-*`— y este generador siguio
# escribiendo «9 run(s)» sin saltarse ni una linea de aviso. El CSV es el resumen PUBLICO
# del track: decia nueve sobre un track de diecisiete. Es la §5 bis en su forma pura —
# cubrir menos de lo declarado y salir en verde.
PATRONES = ["runs/**/*EXP-0033-*.json",        # los nueve de julio
            "runs/**/*RQ-EXP-EON-*.json"]      # la convencion nueva, desde agosto
candidatos = sorted({p for g in PATRONES for p in glob.glob(g, recursive=True)
                     if not p.endswith(".ots")})
if not candidatos:
    raise SystemExit("ABORTA: ningun archivo del track E.ON. Un CSV vacio se lee como "
                     "«no hay corridas», no como «no las encontre».")

rows = []
omitidos = []
for path in candidatos:
    doc = json.load(open(path))
    meta, q = doc["meta"], doc["w6"]["que"]
    convention, _ = identify(doc)
    if convention is None:
        omitidos.append(path)
        print(f"  OMITIDO (sello no verifica): {path}")
        continue
    ip, fuente = parametros(doc)
    fn = re.search(r"case(\d+)", os.path.basename(path))
    filename_claim = f"IEEE case{fn.group(1)}" if fn else ""
    internal = str(ip.get("grid", ""))
    # Sin nombre de red en el archivo NO hay dos etiquetas que comparar, y «no hay dos»
    # no es «no calzan». La version anterior de esta linea marcaba NO CALZA sobre los
    # sellos v3 —cuyo censo vive en otra rama— y sobre las corridas cuyo nombre no lleva
    # la red: cuatro falsos positivos en el CSV publico. Un falso positivo retiene
    # trabajo bueno, que es peor que dejar pasar un caso (CLAUDE.md Rosetta §2).
    if not filename_claim or not internal:
        acuerdo = "n/a"
    else:
        acuerdo = "yes" if filename_claim == internal else "NO"
    rows.append({
        "file_id": meta["file_id"],
        "archived_at": fecha_de(doc),
        "grid_per_filename": filename_claim,
        "grid_per_internal_params": internal,
        "labels_agree": "yes" if filename_claim == internal else "NO",
        "instance": q.get("instance", ""),
        "load_scale": ip.get("load_scale", ""),
        "n_candidates": ip.get("n_candidates", ""),
        "k_budget": ip.get("k_budget", ""),
        "seed": ip.get("seed", ""),
        "time_budget_s": ip.get("time_budget_s", ""),
        "outcome": q.get("outcome", ""),
        "seal_convention": convention,
        "content_hash": meta["content_hash"],
        "bitcoin_blocks": " ".join(str(b) for b in bitcoin_blocks(path + ".ots")) or "pending",
        "github_raw": f"https://raw.githubusercontent.com/RosettaQuantum/evidence/main/{path}",
    })

with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

bad = [r for r in rows if r["labels_agree"] == "NO"]
# El DENOMINADOR, siempre: vistos / escritos / omitidos. «9 run(s)» a secas fue lo que
# dejo pasar ocho corridas sin que nadie lo notara (§5 bis regla 1).
print(f"escrito {OUT}: {len(candidatos)} archivo(s) del track vistos · {len(rows)} "
      f"escrito(s) · {len(omitidos)} omitido(s) por sello que no verifica · "
      f"{len(bad)} con etiqueta en desacuerdo")
for r in rows:
    mark = "  <-- NO CALZA" if r["labels_agree"] == "NO" else ""
    print(f"  {r['file_id']}  nombre:{r['grid_per_filename']:<13} interno:{r['grid_per_internal_params']:<13}{mark}")
