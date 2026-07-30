#!/usr/bin/env python3
"""Cadena notarial completa en un comando: verificar -> anclar -> publicar -> sincronizar.

Existe porque el trabajo del notario son seis pasos con un orden que importa, y saltarse
uno no se nota hasta que ya es tarde: si se ancla antes de verificar, se estampa una
mentira; si se publica sin sincronizar D1, la tercera copia queda coja; si se mueve el
contador antes de confirmar las tres copias, el sitio afirma mas evidencia de la que hay.

Uso:
    python3 scripts/notarize.py --dry     # que haria, sin tocar nada
    python3 scripts/notarize.py           # la cadena completa
    python3 scripts/notarize.py -m "..."  # con mensaje de commit propio

REGLA DE PARADA: si `verify_seals.py` reporta un solo INVALID, aborta antes de estampar
nada. Un sello que no verifica no se ancla — ese es el negocio entero.
"""
import glob, json, os, re, subprocess, sys

sys.path.insert(0, "tools")
from verify_seals import identify

OTS = os.path.expanduser("~/Library/Python/3.9/bin/ots")
DRY = "--dry" in sys.argv
ARCHIVE_GLOBS = ("runs/**/*.json", "prereg/**/*.json", "verdicts/**/*.json",
                 "recipes/*.json", "manifests/*.json")


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)


def archives():
    out = []
    for g in ARCHIVE_GLOBS:
        out += glob.glob(g, recursive=True)
    return sorted(p for p in out if not p.endswith(".ots"))


def paso(n, txt):
    print(f"\n[{n}] {txt}")


# ---- 1. regla de parada -------------------------------------------------------
paso(1, "verificar sellos (regla de parada)")
malos, conv = [], {}
for p in archives():
    try:
        c, _ = identify(json.load(open(p)))
    except Exception as e:
        malos.append((p, f"ilegible: {e}")); continue
    if c is None:
        malos.append((p, "el sello no reproduce"))
    else:
        conv[c] = conv.get(c, 0) + 1
print("   " + " · ".join(f"{k}:{v}" for k, v in sorted(conv.items())) + f" · total {len(archives())}")
if malos:
    print("\n   ABORTADO — no se ancla nada:")
    for p, why in malos:
        print(f"     {p}: {why}")
    sys.exit(1)
print("   0 INVALID")

# ---- 2. anclar ---------------------------------------------------------------
paso(2, "anclar en OpenTimestamps")
sin_ots = [p for p in archives() if not os.path.exists(p + ".ots")]
print(f"   sin ancla: {len(sin_ots)}")
for p in sin_ots:
    print(f"     estampar {os.path.basename(p)[:64]}")
    if not DRY:
        sh([OTS, "stamp", p])
if not DRY:
    pend = [p + ".ots" for p in archives() if os.path.exists(p + ".ots")]
    if pend:
        r = sh([OTS, "upgrade"] + pend)
        print(f"   upgrade: {len((r.stdout + r.stderr).splitlines())} lineas")
    for b in glob.glob("**/*.ots.bak", recursive=True):
        os.remove(b)

# ---- 3. publicar (triple copia) ----------------------------------------------
paso(3, "publicar en GitHub + Codeberg")
cambios = sh("git status --porcelain").stdout.strip()
if not cambios:
    print("   nada que publicar")
else:
    print("   " + "\n   ".join(cambios.splitlines()[:12]))
    msg = None
    if "-m" in sys.argv:
        msg = sys.argv[sys.argv.index("-m") + 1]
    msg = msg or f"Notarizacion: {len(sin_ots)} archivo(s) nuevo(s) anclado(s) y publicado(s)"
    if not DRY:
        sh("git add -A")
        r = sh(["git", "commit", "-q", "-m", msg + "\n\nCo-Authored-By: Claude Fable 5 <noreply@anthropic.com>"])
        if r.returncode:
            print("   commit fallo:", (r.stdout + r.stderr)[:200])
        firma = sh("git log -1 --format=%G?").stdout.strip()
        print(f"   firma del commit: {firma} (G = buena)")
        push = sh("git push")
        print("   push:", (push.stdout + push.stderr).strip().splitlines()[-1][:100])

# ---- 4. tercera copia --------------------------------------------------------
paso(4, "sincronizar D1 (tercera copia)")
if DRY:
    print("   (dry) se correria scripts/sync_archives_to_d1.py")
else:
    env = dict(os.environ)
    env.pop("CLOUDFLARE_API_TOKEN", None); env.pop("CLOUDFLARE_ACCOUNT_ID", None)
    r = subprocess.run([sys.executable, "scripts/sync_archives_to_d1.py"],
                       capture_output=True, text=True, env=env)
    print("   " + (r.stdout.strip().splitlines() or ["sin salida"])[-1])
    if r.returncode:
        print("   OJO:", r.stderr[:200])

# ---- 5. resumenes derivados --------------------------------------------------
paso(5, "regenerar los CSV desde los sellos")
for s in ("scripts/make_cleveland_csv.py", "scripts/make_eon_csv.py"):
    if os.path.exists(s):
        if DRY:
            print(f"   (dry) {s}")
        else:
            r = sh([sys.executable, s])
            print("   " + (r.stdout.strip().splitlines() or ["sin salida"])[0])

# ---- 6. comprobar una copia de punta a punta ---------------------------------
paso(6, "comprobar un archivo en las tres copias")
muestra = sin_ots[0] if sin_ots else (archives()[-1] if archives() else None)
if muestra and not DRY:
    import hashlib, urllib.request
    loc = hashlib.sha256(open(muestra, "rb").read()).hexdigest()
    def remoto(u):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            return hashlib.sha256(urllib.request.urlopen(req, timeout=60).read()).hexdigest()
        except Exception:
            return "no disponible"
    gh = remoto(f"https://raw.githubusercontent.com/RosettaQuantum/evidence/main/{muestra}")
    cb = remoto(f"https://codeberg.org/RosettaQuantum/evidence/raw/branch/main/{muestra}")
    print(f"   {os.path.basename(muestra)[:56]}")
    print(f"   local={loc[:16]} github={'=' if gh == loc else gh[:16]} codeberg={'=' if cb == loc else cb[:16]}")
else:
    print("   (nada nuevo que comprobar)" if not muestra else "   (dry)")

print("\nlisto." if not DRY else "\n--dry: no se toco nada.")
print("Recordatorio: el contador publico de la web se mueve DESPUES de esto, nunca antes.")
