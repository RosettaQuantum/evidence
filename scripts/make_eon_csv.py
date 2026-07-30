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


rows = []
for path in sorted(glob.glob("runs/2026/07/*EXP-0033-*.json")):
    doc = json.load(open(path))
    meta, q = doc["meta"], doc["w6"]["que"]
    convention, _ = identify(doc)
    if convention is None:
        print(f"  OMITIDO (sello no verifica): {path}")
        continue
    ip = (doc["w6"].get("como", {}) or {}).get("instance_params", {}) or {}
    fn = re.search(r"case(\d+)", os.path.basename(path))
    filename_claim = f"IEEE case{fn.group(1)}" if fn else ""
    internal = str(ip.get("grid", ""))
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
print(f"escrito {OUT} con {len(rows)} run(s); {len(bad)} con etiqueta en desacuerdo")
for r in rows:
    mark = "  <-- NO CALZA" if r["labels_agree"] == "NO" else ""
    print(f"  {r['file_id']}  nombre:{r['grid_per_filename']:<13} interno:{r['grid_per_internal_params']:<13}{mark}")
