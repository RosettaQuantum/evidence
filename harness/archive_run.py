"""Sella un run como archivo RosettaQ (spec rosetta-archivo-triple v1)."""
import json, hashlib, sys
from datetime import datetime, timezone

RESULT = json.load(open("/home/claude/rosettaq/runs/result_EXP-0012-001.json"))
FILE_ID = "EXP-0012-001"
RECIPE_ID = "RQ-0012"
now = datetime.now(timezone.utc)
started = sys.argv[1] if len(sys.argv) > 1 else now.isoformat(timespec="seconds")
ts_name = now.strftime("%Y%m%dT%H%MZ")
context = f"qaoa-vs-cpsat--portfolio-{RESULT['params']['n_assets']}-seed{RESULT['params']['seed']}"
file_name = f"RosettaQ__RUN__{FILE_ID}__{ts_name}__{context}.json"
repo_path = f"runs/{now.strftime('%Y')}/{now.strftime('%m')}/{file_name}"

meta = {
    "schema": "rosettaq-archive/v1",
    "file_name": file_name,
    "file_id": FILE_ID,
    "type": "RUN",
    "is_demo": False,
    "scope_note": ("Run real medido en simulador CPU a escala pequena (12 qubits). "
                   "Primer run del harness v0 — valor: establecer el protocolo y la linea base honesta."),
    "content_hash": None,
}
w6 = {
    "que": {
        "recipe_id": RECIPE_ID,
        "recipe_name": "Constrained portfolio compression",
        "problem_class": "Portfolio optimization",
        "instance": RESULT["instance"],
        "quantum_side": RESULT["quantum"],
        "classical_side": RESULT["classical"],
        "exact_optimum": RESULT["exact"],
        "outcome": RESULT["verdict"]["outcome"],
        "quality_gaps_pct": {"classical": RESULT["verdict"]["classical_gap_pct"],
                              "quantum": RESULT["verdict"]["quantum_gap_pct"]},
    },
    "como": {
        "protocol": RESULT["verdict"]["protocol"],
        "seed": RESULT["params"]["seed"],
        "instance_params": RESULT["params"],
        "lib_versions": RESULT["lib_versions"],
        "compute": "contenedor cloud Cowork (CPU, Linux)",
        "harness": "harness_v0.py (publicado junto al archivo)",
        "raw_data_url": "pendiente de publicacion en repo",
    },
    "cuando": {"started_at": started, "archived_at": now.isoformat(timespec="seconds"),
               "timezone_note": "UTC; equipo en America/Punta_Arenas"},
    "donde": {"quantum_backend": "PennyLane default.qubit (simulador CPU)",
              "classical_backend": "misma maquina, OR-Tools CP-SAT",
              "region": "cloud sandbox Anthropic"},
    "porque": {
        "hypothesis": "a 12 activos NO se espera ventaja cuantica; este run fija la linea base del protocolo",
        "question": "Como se comporta QAOA p=2 vs CP-SAT con presupuesto igual en la instancia semilla-42?",
        "ledger_goal": "primer run real de la serie EXP-0012; alimenta el verdict V-0012 y la entrada al Global Quantum + AI Challenge",
    },
    "quien": {"operator": "Nicholas", "agents": ["Claude (Cowork cloud)", "harness_v0.py"],
              "judge_protocol_version": "juez-v1", "org": "Rosetta Quantum"},
}
canon = json.dumps({"meta": meta, "w6": w6}, sort_keys=True, separators=(",", ":"))
meta["content_hash"] = "sha256:" + hashlib.sha256(canon.encode()).hexdigest()

storage = {
    "policy": "triple-copia identica; verificar con content_hash",
    "locations": [
        {"n": 1, "kind": "github", "role": "primary",
         "url": f"https://github.com/RosettaQ/evidence/blob/main/{repo_path}",
         "raw_url": f"https://raw.githubusercontent.com/RosettaQ/evidence/main/{repo_path}"},
        {"n": 2, "kind": "codeberg", "role": "mirror",
         "url": f"https://codeberg.org/RosettaQ/evidence/src/branch/main/{repo_path}",
         "raw_url": f"https://codeberg.org/RosettaQ/evidence/raw/branch/main/{repo_path}"},
        {"n": 3, "kind": "cloudflare-d1", "role": "database",
         "uri": f"d1://rosettaq-ledger/run_archives/{FILE_ID}",
         "public_read": f"https://ledger.rosettaquantum.com/api/archive/{FILE_ID}"},
    ],
    "self_note": "Este archivo es una de las 3 copias listadas. Si el hash de cualquier copia difiere, esa copia no es valida.",
}
doc = {"meta": meta, "w6": w6, "storage": storage}
out = f"/home/claude/rosettaq/runs/{file_name}"
with open(out, "w") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)
print(out)
print(meta["content_hash"])
