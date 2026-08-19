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
import datetime as _dt
import glob, json, os, re, subprocess, sys

sys.path.insert(0, "tools")
from verify_seals import identify

OTS = os.path.expanduser("~/Library/Python/3.9/bin/ots")
DRY = "--dry" in sys.argv
sys.path.insert(0, "scripts")
from notarize_globs import ARCHIVE_GLOBS   # definicion unica; ver el modulo


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

# ---- 1 bis. la procedencia se exige ANTES de estampar --------------------------
# Pregunta de diseno de Norte (20-ago) tras un caso real: el prereg de Airbus se sello
# y se anclo citando su script productor (seal_prereg_airbus.py) que NO estaba publicado
# — el guard solo protesto DESPUES, en el CI. Un sello cuya procedencia no resuelve nace
# con una promesa a plazo, y el plazo es donde los archivos mutan (caso eon_estocastico:
# la promesa vencio sin pagarse y hubo que declarar la perdida).
# Desde ahora el notario exige la procedencia resuelta ANTES de estampar nada: si el
# conteo de pendientes no es cero —o no se puede leer, que no es lo mismo que cero
# (§5 quater)— no hay ancla. Las perdidas DECLARADAS se cuentan aparte y no bloquean;
# los archivos de terceros no-republicables necesitaran su propia categoria declarada.
# El CI sigue auditando despues: esta capa atrapa el nacimiento, aquella atrapa la deriva.
paso("1 bis", "procedencia resuelta antes de anclar (falla cerrado)")
r = sh([sys.executable, "scripts/check_provenance.py"])
_salida = r.stdout + r.stderr
_m = re.search(r"SIN publicar \(pendientes\):\s+(\d+)", _salida)
if not _m:
    print("   ABORTADO — no pude leer el conteo de procedencia. La ausencia del dato no")
    print("   es un cero: sin conteo no se ancla.")
    sys.exit(1)
if int(_m.group(1)) > 0:
    print("   ABORTADO — %s referencias de procedencia sin publicar. No se estampa un" % _m.group(1))
    print("   sello cuyo propio productor o fuentes no estan publicados:")
    for _l in _salida.splitlines():
        if _l.strip().startswith(("lab-", "seal_", "evidence")) or "declara" in _l:
            print("   " + _l.strip()[:100])
    sys.exit(1)
print("   0 sin publicar (las perdidas declaradas se cuentan aparte)")

# ---- 1 ter. ningun sello declara el futuro ------------------------------------
# El identificador de cada artefacto lleva una marca de tiempo, y la escribia quien
# redactaba leyendola de SU contexto — que puede estar corrido respecto del reloj real.
# Resultado medido el 19-ago: 14 artefactos publicados declaran una fecha POSTERIOR a su
# propio commit, lo que es imposible. Cae justo sobre el eje temporal donde vive toda la
# afirmacion de esta casa («la pregunta quedo fijada antes que el codigo»), asi que el
# defecto es barato de cometer y caro de explicar.
#
# Este guardia vive en el NOTARIO ademas de en el sellador a proposito: es la
# comprobacion que hace OTRO actor. Un guardia que solo vive en quien produce el sello
# es un guardia que se revisa a si mismo (§11 de CLAUDE.md, la separacion).
#
# Las incoherencias historicas estan declaradas en FECHAS-DECLARADAS-INCOHERENTES.md y no
# bloquean —publicado es publicado, se marca y no se reescribe—; cualquier sello NUEVO con
# fecha futura si bloquea. Asi la nota no es decorativa: la lee el codigo.
paso("1 ter", "ningun sello declara una fecha futura (falla cerrado)")
_ahora = _dt.datetime.now(_dt.timezone.utc)
_NOTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "FECHAS-DECLARADAS-INCOHERENTES.md")
_declaradas = set()
if os.path.exists(_NOTA):
    _declaradas = set(re.findall(r"(2026\d{4}T\d{4}Z)", open(_NOTA).read()))
_futuros = []
for _p in archives():
    _m = re.search(r"__(2026\d{4}T\d{4}Z)__", os.path.basename(_p))
    if not _m:
        continue
    _id = _dt.datetime.strptime(_m.group(1), "%Y%m%dT%H%MZ").replace(tzinfo=_dt.timezone.utc)
    if _id > _ahora and _m.group(1) not in _declaradas:
        _futuros.append((os.path.basename(_p)[:70], _m.group(1)))
if _futuros:
    print("   ABORTADO — %d sello(s) declaran una fecha que todavia no ocurrio." % len(_futuros))
    print("   Un sello no puede declarar el futuro: el ID sale del reloj, no del contexto.")
    for _n, _i in _futuros:
        print("     %s  <- %s" % (_i, _n))
    print("   Si son historicos y no se pueden reescribir, se declaran en")
    print("   FECHAS-DECLARADAS-INCOHERENTES.md con su tabla y su explicacion.")
    sys.exit(1)
print("   0 sellos con fecha futura (%d historicos declarados en la nota)" % len(_declaradas))

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
        sh("git push")
        # No se confia en el codigo de salida de `git push`: origin escribe a dos
        # remotos y si uno falla el comando devuelve error aunque el otro haya
        # recibido el commit. Se comprueba el estado real de cada copia por HTTPS,
        # que ademas no depende de la llave SSH.
        import urllib.request as _u
        local = sh("git rev-parse HEAD").stdout.strip()
        def remoto(url, extraer):
            try:
                req = _u.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                return extraer(json.load(_u.urlopen(req, timeout=45)))
            except Exception as e:
                return f"no responde ({str(e)[:40]})"
        gh = remoto("https://api.github.com/repos/RosettaQuantum/evidence/commits/main",
                    lambda d: d["sha"])
        cb = remoto("https://codeberg.org/api/v1/repos/RosettaQuantum/evidence/commits?limit=1",
                    lambda d: d[0]["sha"])
        print(f"   local    {local[:8]}")
        for nombre, sha in (("github  ", gh), ("codeberg", cb)):
            estado = "al dia" if sha == local else f"DESFASADO ({sha[:8]})"
            print(f"   {nombre} {sha[:8]}  {estado}")
        if cb != local:
            print("   nota: el Action del mirror sincroniza Codeberg en ~1 min; re-comprobar")

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
paso(5, "regenerar TODO lo derivado")
# La lista de derivaciones NO vive aqui. Vive en scripts/derivar.py y este paso la
# invoca. Antes estaban escritas a mano los dos CSV, y por eso el mapa de frontera y el
# estado del Terminal quedaron fuera de la regeneracion durante todo su primer dia de
# vida: el mapa publicado descartaba ocho corridas selladas con un motivo falso y nadie
# se entero. Una lista que vive en dos lugares ya divergio (§5 bis regla 3).
r = sh([sys.executable, "scripts/derivar.py"] + (["--dry"] if DRY else []))
for linea in (r.stdout.strip().splitlines() or ["sin salida"]):
    if linea.strip():
        print("   " + linea)
if r.returncode and not DRY:
    print("   OJO: alguna derivacion fallo. El archivo esta bien; los resumenes NO.")

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

# ---- 7. cadena de procedencia -------------------------------------------------
paso(7, "auditar la cadena de procedencia")
if os.path.exists("scripts/check_provenance.py"):
    r = sh([sys.executable, "scripts/check_provenance.py"])
    for linea in r.stdout.strip().splitlines():
        print("   " + linea)
# No aborta: un sello valido con un archivo de apoyo pendiente es publicable si la
# falta se declara. Lo que no se tolera es que pase inadvertida.

print("\nlisto." if not DRY else "\n--dry: no se toco nada.")
print("Recordatorio: el contador publico de la web se mueve DESPUES de esto, nunca antes.")
