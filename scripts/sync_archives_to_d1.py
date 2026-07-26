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
import base64, glob, json, os, re, sys, urllib.request
sys.path.insert(0, "tools")
from verify_seals import identify   # API v2: (convencion, hash) | (None, esperado)

OWNER, REPO, DB = "RosettaQuantum", "evidence", "rosettaq-ledger"


def seal_ok(doc):
    """True si el sello reproduce bajo ALGUNA convencion reconocida (v2, v1-canonica
    o v1-legada ya anclada). El guardarrail no publica lo que no verifica."""
    convention, _ = identify(doc)
    return convention is not None


def esc(s):
    return s.replace("'", "''")

rows = []
skipped = []
for path in sorted(glob.glob("recipes/*.json") + glob.glob("runs/**/*.json", recursive=True)
                   + glob.glob("verdicts/**/*.json", recursive=True)
                   + glob.glob("prereg/**/*.json", recursive=True)):
    doc = json.load(open(path))
    # guardarraíl: un sello que no verifica no se publica en ninguna copia
    if not seal_ok(doc):
        print(f"  OMITIDO (sello no verifica): {path}")
        skipped.append(path)
        continue
    meta = doc["meta"]
    # RUN/VERDICT traen w6; PREREG trae su propio bloque con committed_at_utc
    w6 = doc.get("w6") or {}
    cuando = w6.get("cuando", {})
    when = (cuando.get("archived_at") or cuando.get("published_at")
            or doc.get("prereg", {}).get("committed_at_utc") or "")
    payload = open(path).read()
    try:
        ots = base64.b64encode(open(path + ".ots", "rb").read()).decode()
    except FileNotFoundError:
        ots = None
    rows.append([
        meta["file_id"], meta["file_name"], meta["type"],
        w6.get("que", {}).get("recipe_id", meta["file_id"]),
        1 if meta.get("is_demo") else 0,
        meta["content_hash"], None, when,
        f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{path}",
        f"https://codeberg.org/{OWNER}/{REPO}/raw/branch/main/{path}",
        ots, payload,
    ])

# Transporte: API REST de D1 con parametros ligados, NO texto SQL.
# Por que: `wrangler d1 execute --file` mete el payload dentro del texto de la
# sentencia, y una sentencia tiene limite duro (SQLITE_TOOBIG). Los archivos con
# bloque de procedencia ya pasan los 180 KB, asi que ningun tamano de lote alcanza:
# hay filas individuales mas grandes que el limite. Con parametros, la sentencia es
# corta y el payload viaja como dato — escala con el archivo, que solo crece.
ACCOUNT_ID = "6398d10da6c1f1e8b38b5e7c15d2410f"
DB_UUID = "f0919403-5bd0-4842-a1d3-0954fdd47633"
SQL = ("INSERT OR REPLACE INTO run_archives "
       "(file_id,file_name,type,recipe_id,is_demo,content_hash,started_at,"
       "archived_at,github_url,codeberg_url,ots_proof,payload) "
       "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)")


def d1_token():
    """El token OAuth de wrangler (el unico con permiso D1 en este Mac)."""
    cfg = open(os.path.expanduser(
        "~/Library/Preferences/.wrangler/config/default.toml")).read()
    m = re.search(r'oauth_token\s*=\s*"([^"]+)"', cfg)
    if not m:
        raise SystemExit("no encontre el token OAuth de wrangler: corre `npx wrangler login`")
    return m.group(1)


token = d1_token()
url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DB_UUID}/query"
for n, params in enumerate(rows, 1):
    req = urllib.request.Request(
        url, data=json.dumps({"sql": SQL, "params": params}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST")
    try:
        res = json.load(urllib.request.urlopen(req, timeout=120))
    except Exception as e:
        raise SystemExit(f"D1 falló en {params[0]}: {str(e)[:300]}")
    if not res.get("success"):
        raise SystemExit(f"D1 rechazó {params[0]}: {json.dumps(res.get('errors'))[:300]}")
    if n % 10 == 0 or n == len(rows):
        print(f"  {n}/{len(rows)}")
print(f"synced {len(rows)} archive file(s) to D1 run_archives")
if skipped:
    print(f"OJO: {len(skipped)} archivo(s) omitidos por sello inválido: {skipped}")
