#!/usr/bin/env python3
"""Verifica el sello de un archivo RosettaQ (rosettaq-archive/v1).
Uso: python3 verify_archive.py <archivo.json> [...]
Sale con codigo 0 si todos los sellos son validos."""
import json, hashlib, sys, glob

def verify(path):
    d = json.load(open(path))
    claimed = d["meta"]["content_hash"]
    d["meta"]["content_hash"] = None
    canon = json.dumps({"meta": d["meta"], "w6": d["w6"]},
                       sort_keys=True, separators=(",", ":"))
    actual = "sha256:" + hashlib.sha256(canon.encode()).hexdigest()
    ok = claimed == actual
    print(f"{'VALID  ' if ok else 'INVALID'} {path}")
    if not ok:
        print(f"  claimed: {claimed}\n  actual:  {actual}")
    return ok

if __name__ == "__main__":
    paths = [p for arg in sys.argv[1:] for p in sorted(glob.glob(arg))]
    if not paths:
        print(__doc__); sys.exit(2)
    sys.exit(0 if all([verify(p) for p in paths]) else 1)
