#!/usr/bin/env python3
"""Copy 3 of the triple archive: upsert every sealed file in recipes/ (and runs/,
verdicts/ once they exist) into the D1 `run_archives` table, payload included,
with its .ots proof base64-encoded alongside.

Run after every push that adds or upgrades archive files:
    python3 scripts/sync_archives_to_d1.py
Requires wrangler authenticated against the account that owns `rosettaq-ledger`
(in Claude Code: strip CLOUDFLARE_API_TOKEN so the OAuth login is used).
Idempotent: INSERT OR REPLACE keyed on file_id, so re-running is safe.
"""
import base64, glob, json, subprocess, tempfile

OWNER, REPO, DB = "RosettaQuantum", "evidence", "rosettaq-ledger"

def esc(s):
    return s.replace("'", "''")

rows = []
for path in sorted(glob.glob("recipes/*.json") + glob.glob("runs/**/*.json", recursive=True) + glob.glob("verdicts/**/*.json", recursive=True)):
    doc = json.load(open(path))
    meta, w6 = doc["meta"], doc["w6"]
    payload = open(path).read()
    try:
        ots = base64.b64encode(open(path + ".ots", "rb").read()).decode()
    except FileNotFoundError:
        ots = None
    rows.append(
        "INSERT OR REPLACE INTO run_archives "
        "(file_id,file_name,type,recipe_id,is_demo,content_hash,started_at,archived_at,github_url,codeberg_url,ots_proof,payload) VALUES ("
        f"'{esc(meta['file_id'])}','{esc(meta['file_name'])}','{esc(meta['type'])}',"
        f"'{esc(w6['que'].get('recipe_id', meta['file_id']))}',{1 if meta.get('is_demo') else 0},"
        f"'{esc(meta['content_hash'])}',NULL,'{esc(w6['cuando']['archived_at'])}',"
        f"'https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{esc(path)}',"
        f"'https://codeberg.org/{OWNER}/{REPO}/raw/branch/main/{esc(path)}',"
        + (f"'{ots}'" if ots else "NULL") + f",'{esc(payload)}');"
    )

# D1 limita el tamaño por ejecución: subir en lotes chicos
BATCH = 6
done = 0
for i in range(0, len(rows), BATCH):
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as f:
        f.write("\n".join(rows[i:i+BATCH]))
        sql_path = f.name
    out = subprocess.run(
        ["npx", "wrangler", "d1", "execute", DB, "--remote", "--file", sql_path, "--json"],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"wrangler failed en lote {i//BATCH+1}:\nstderr: {out.stderr[:400]}\nstdout: {out.stdout[:400]}")
    done += len(rows[i:i+BATCH])
    print(f"  lote {i//BATCH+1}: {done}/{len(rows)}")
print(f"synced {len(rows)} archive file(s) to D1 run_archives")
