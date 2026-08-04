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
import base64, glob, json, os, re, subprocess, sys, urllib.request
sys.path.insert(0, "tools")
from verify_seals import identify   # API v2: (convencion, hash) | (None, esperado)

OWNER, REPO, DB = "RosettaQuantum", "evidence", "rosettaq-ledger"


def seal_ok(doc):
    """True si el sello reproduce bajo ALGUNA convencion reconocida (v2, v1-canonica
    o v1-legada ya anclada). El guardarrail no publica lo que no verifica."""
    convention, _ = identify(doc)
    return convention is not None


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


def esc(s):
    return s.replace("'", "''")

# La lista de carpetas la manda notarize.py: tener dos listas separadas ya costo caro.
# Este script se olvidaba de manifests/, asi que la tercera copia iba 63 de 64 y el
# archivo ausente era justamente el MANIFEST que documenta como verificar los sellos —
# el sitio ofrecia comprobarlo todo salvo las instrucciones para comprobar. Importarla
# de un solo lugar hace imposible que vuelvan a divergir en silencio.
sys.path.insert(0, "scripts")
from notarize_globs import ARCHIVE_GLOBS

rows = []
skipped = []
for path in sorted(p for g in ARCHIVE_GLOBS for p in glob.glob(g, recursive=True)
                   if not p.endswith(".ots")):
    doc = json.load(open(path))
    # guardarraíl: un sello que no verifica no se publica en ninguna copia
    if not seal_ok(doc):
        print(f"  OMITIDO (sello no verifica): {path}")
        skipped.append(path)
        continue
    meta = doc["meta"]
    # RUN/VERDICT traen w6; PREREG trae su propio bloque con committed_at_utc
    w6 = doc.get("w6") or {}
    when = fecha_de(doc)
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
    """El token OAuth de wrangler (el unico con permiso D1 en este Mac).

    Se invoca wrangler primero a proposito: el access token OAuth caduca en horas y
    wrangler lo renueva con su refresh token al ejecutarse. Leyendo el archivo sin ese
    paso, un token vencido da 401 y la tercera copia se queda sin actualizar.
    """
    subprocess.run(["npx", "wrangler", "whoami"], capture_output=True, text=True,
                   env={k: v for k, v in os.environ.items()
                        if k not in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")})
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
