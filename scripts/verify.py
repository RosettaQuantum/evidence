#!/usr/bin/env python3
"""Verify sealed archive files: recompute content_hash and compare."""
import json, hashlib, sys
def canonical(o): return json.dumps(o, sort_keys=True, separators=(",",":")).encode()
ok=True
for path in sys.argv[1:]:
    d=json.load(open(path)); m=dict(d["meta"]); sealed=m["content_hash"]; m["content_hash"]=None
    got=hashlib.sha256(canonical({"meta":m,"w6":d["w6"]})).hexdigest()
    status = 'OK ' if got==sealed else 'FAIL'
    if got!=sealed: ok=False
    print(f"{status} {path}  sealed={sealed[:12]}… got={got[:12]}…")
sys.exit(0 if ok else 1)
