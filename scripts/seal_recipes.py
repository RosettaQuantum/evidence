#!/usr/bin/env python3
"""Seal the current recipes as immutable RECIPE archive files (is_demo=true).
Matches the triple-archive protocol: RosettaQ naming, meta+w6+storage, sha256 seal.
Re-run only to add NEW recipes; existing sealed files are immutable."""
import json, hashlib
from datetime import datetime, timezone

OWNER, REPO = "RosettaQuantum", "evidence"
NOW = datetime.now(timezone.utc)

RECIPES = [
  {"id":"RQ-0007","name":"Molecular ground-state search","class":"Molecular simulation","vertical":"Pharma","algorithm":"VQE","qubits":None,"status":"pending","source":None},
  {"id":"RQ-0012","name":"Constrained portfolio compression","class":"Portfolio optimization","vertical":"Finance","algorithm":"QAOA","qubits":28,"status":"measuring","source":None},
  {"id":"RQ-0019","name":"Fleet routing under uncertainty","class":"Vehicle routing","vertical":"Mining","algorithm":"QAOA","qubits":None,"status":"in test","source":None},
  {"id":"RQ-0033","name":"Grid balancing with renewables","class":"Grid optimization","vertical":"Energy","algorithm":"QAOA","qubits":None,"status":"queued","source":None},
]

def canonical(o): return json.dumps(o, sort_keys=True, separators=(",",":")).encode()

for r in RECIPES:
    stamp = NOW.strftime("%Y%m%dT%H%MZ")
    ctx = f"{r['algorithm'].lower()}--{r['class'].lower().replace(' ','-')}"
    fname = f"RosettaQ__RECIPE__{r['id']}__{stamp}__{ctx}.json"
    path = f"recipes/{fname}"
    meta = {"schema":"rosettaq-archive/v1","file_name":fname,"file_id":r["id"],
            "type":"RECIPE","is_demo":True,"content_hash":None}
    w6 = {
      "que":{"recipe_id":r["id"],"recipe_name":r["name"],"problem_class":r["class"],
             "vertical":r["vertical"],"algorithm":r["algorithm"],"qubits_required":r["qubits"],
             "status":r["status"],"advantage_claimed":None,"source":r["source"]},
      "como":{"protocol":"harvested recipe card; no fight run yet","notebook_url":"#"},
      "cuando":{"archived_at":NOW.isoformat()},
      "donde":{"note":"recipe card only — no compute yet"},
      "porque":{"ledger_goal":f"register {r['id']} in the public pipeline"},
      "quien":{"operator":"Nicholas","agents":["Claude"],"org":"Rosetta Quantum"},
    }
    meta["content_hash"] = hashlib.sha256(canonical({"meta":meta,"w6":w6})).hexdigest()
    storage = {"policy":"identical triple-copy + external anchor; verify by content_hash",
      "locations":[
        {"n":1,"kind":"github","role":"primary",
         "url":f"https://github.com/{OWNER}/{REPO}/blob/main/{path}",
         "raw_url":f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{path}"},
        {"n":2,"kind":"codeberg","role":"mirror",
         "url":f"https://codeberg.org/{OWNER}/{REPO}/src/branch/main/{path}",
         "raw_url":f"https://codeberg.org/{OWNER}/{REPO}/raw/branch/main/{path}"},
        {"n":3,"kind":"cloudflare-d1","role":"database",
         "uri":f"d1://rosettaq-ledger/recipes/{r['id']}"}],
      "anchor":{"kind":"opentimestamps","proof_file":f"{fname}.ots"},
      "self_note":"One of 3 identical copies. If any copy's hash differs, that copy is invalid."}
    doc = {"meta":meta,"w6":w6,"storage":storage}
    with open(path,"w") as f: json.dump(doc, f, indent=2)
    print(f"sealed {fname}  hash={meta['content_hash'][:12]}…")
