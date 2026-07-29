#!/usr/bin/env python3
"""Genera RosettaQ-Cleveland-sealed-runs.csv A PARTIR de los archivos sellados.

Se genera, no se escribe a mano: un CSV tecleado aparte se desincroniza del archivo
en cuanto un run cambia, y entonces el adjunto de la postulacion afirma numeros que
el sello no respalda. Aqui la unica fuente es el JSON sellado.

Uso: python3 scripts/make_cleveland_csv.py
"""
import csv, glob, json, subprocess, re, sys, os

sys.path.insert(0, "tools")
from verify_seals import identify

OTS = os.path.expanduser("~/Library/Python/3.9/bin/ots")
OUT = "RosettaQ-Cleveland-sealed-runs.csv"


def bitcoin_blocks(ots_path):
    """Bloques de Bitcoin que atestiguan el sello (vacio si sigue pendiente)."""
    try:
        info = subprocess.run([OTS, "info", ots_path], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return []
    return sorted(set(int(b) for b in re.findall(r"BitcoinBlockHeaderAttestation\((\d+)\)", info)))


rows = []
for path in sorted(glob.glob("runs/2026/07/*EXP-0007-0*.json")):
    doc = json.load(open(path))
    meta, q = doc["meta"], doc["w6"]["que"]
    convention, _ = identify(doc)
    if convention is None:                       # regla de parada: no se publica
        print(f"  OMITIDO (sello no verifica): {path}")
        continue
    blocks = bitcoin_blocks(path + ".ots")
    n = int(meta["file_id"].split("-")[-1])
    rows.append({
        "file_id": meta["file_id"],
        # 013-019 son las dianas exigidas por el reto; 001-012 es la exploracion
        # previa (2HHB / caspasa-3). Se publican las dos: recortar el CSV a lo que
        # luce bien seria elegir la evidencia despues de verla.
        "series": "cleveland-mandated" if n >= 13 else "exploratory-2HHB-caspase",
        "archived_at": doc["w6"]["cuando"].get("archived_at", "")[:10],
        "instance": q.get("instance", ""),
        "problem_class": q.get("problem_class", ""),
        "outcome": q.get("outcome", ""),
        "metric": (q.get("metric") or "")[:180],
        "seal_convention": convention,
        "content_hash": meta["content_hash"],
        "bitcoin_blocks": " ".join(str(b) for b in blocks) or "pending",
        "github_raw": f"https://raw.githubusercontent.com/RosettaQuantum/evidence/main/{path}",
        "codeberg_raw": f"https://codeberg.org/RosettaQuantum/evidence/raw/branch/main/{path}",
    })

with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"escrito {OUT} con {len(rows)} run(s) sellado(s)")
for r in rows:
    print(f"  {r['file_id']}  {r['archived_at']}  btc:{r['bitcoin_blocks']}  {r['instance'][:34]}")
