#!/usr/bin/env python3
"""DERIVAR: todo lo que se calcula a partir del archivo, en un solo comando.

EL PROBLEMA QUE RESUELVE, dicho por Nicholas el 2026-08-14
-----------------------------------------------------------
    «nuestro sistema y web no estan conectados, son todas piezas sueltas.
     cada vez que lanzamos una corrida todo debe actualizarse.
     estas no son estatuas son elementos vivos»

Y tenia razon. Hasta hoy, cuando terminaba una corrida la cadena era: alguien baja el
artefacto, alguien lo sella, alguien lo ancla, alguien regenera un CSV, alguien regenera
el mapa, alguien refresca el Terminal. **Seis pasos manuales**, y cada uno se podia
olvidar sin que nada avisara. El resultado medible de ese olvido ya lo pagamos hoy: el
CSV publico del track E.ON declaraba 9 corridas sobre un track de 17, y el mapa
descartaba 8 corridas selladas con un motivo falso. Ninguna de las dos cosas fallo.
Las dos salieron en verde.

QUE AUTOMATIZA Y QUE NO
-----------------------
**Automatiza todo lo DERIVADO**: los resumenes, el mapa, el estado del Terminal. Son
funciones puras del archivo — si el archivo cambia, tienen que cambiar, y que dependan
de que alguien se acuerde es el defecto.

**NO automatiza el sello ni el anclaje.** La separacion laboratorio/notario esta
documentada como decision, no como pendiente (CLAUDE.md Rosetta §11), y este archivo no
la toca. Lo que si hace es **contar lo que espera sello y mostrarlo**, para que el
pendiente sea visible en vez de vivir en la memoria de alguien.

LA REGLA QUE LO GOBIERNA
------------------------
Una derivacion que falla NO se salta: se declara y el comando termina distinto de cero.
Un resumen viejo que parece nuevo es peor que un resumen ausente.

Uso:
    python3 scripts/derivar.py            # deriva todo
    python3 scripts/derivar.py --dry      # dice que haria
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROYECTO = os.path.dirname(RAIZ)
DRY = "--dry" in sys.argv
AGENTE = "RosettaQuantum-derivar/1.0 (+https://rosettaquantum.com)"

# LA LISTA VIVE AQUI Y EN NINGUN OTRO LADO. `notarize.py` la importa en vez de tener la
# suya: una lista que vive en dos lugares ya divergio (CLAUDE.md Rosetta §5 bis regla 3),
# y esa divergencia es exactamente como el mapa se quedo fuera de la regeneracion.
DERIVACIONES = [
    ("resumen Cleveland", "scripts/make_cleveland_csv.py", RAIZ),
    ("resumen E.ON", "scripts/make_eon_csv.py", RAIZ),
    ("mapa de frontera", "scripts/mapa_frontera.py", RAIZ),
    ("estado del Terminal", "terminal/estado.py", PROYECTO),
]


def corre(nombre, script, cwd):
    ruta = os.path.join(cwd, script)
    if not os.path.exists(ruta):
        return {"nombre": nombre, "ok": False, "motivo": "no existe %s" % script}
    if DRY:
        return {"nombre": nombre, "ok": None, "motivo": "(dry) se correria %s" % script}
    r = subprocess.run([sys.executable, script], cwd=cwd, capture_output=True, text=True)
    linea = (r.stdout.strip().splitlines() or [""])[0][:150]
    return {"nombre": nombre, "ok": r.returncode == 0, "salida": linea,
            "motivo": None if r.returncode == 0 else (r.stderr.strip()[-220:] or "sin stderr")}


def esperando_sello():
    """Artefactos de resultado que todavia NINGUN sello cita por su sha256.

    Es el pendiente que hasta hoy vivia en la cabeza de alguien. No se automatiza el
    sellado —eso es del laboratorio— pero se cuenta y se muestra, que es distinto.
    """
    sellados = set()
    for p in glob.glob(os.path.join(RAIZ, "runs", "**", "*.json"), recursive=True):
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        sellados.update(re.findall(r"[0-9a-f]{64}", txt))

    pendientes = []
    for patron in ("resultados_eon/*.json", "harness/resultado_*.json"):
        for p in sorted(glob.glob(os.path.join(RAIZ, patron))):
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if h not in sellados:
                pendientes.append({"archivo": os.path.relpath(p, RAIZ), "sha256": h[:16]})
    return pendientes


def local_contra_publico():
    """Las dos copias que un cliente puede comparar. Si difieren, se dice.

    El archivo local y la API publica tienen que contar lo mismo. Nadie los restaba, y
    dos totales que nadie resta esconden su diferencia durante años (§5 bis regla 2).
    """
    local = len([p for p in glob.glob(os.path.join(RAIZ, "runs", "**", "*.json"),
                                      recursive=True)])
    try:
        req = urllib.request.Request("https://rosettaquantum.com/v1/runs?limit=1000",
                                     headers={"User-Agent": AGENTE})
        with urllib.request.urlopen(req, timeout=25) as r:
            publico = len(json.load(r).get("items", []))
    except Exception as e:
        return {"local": local, "publico": None, "calzan": None,
                "motivo": "no se pudo consultar la API: %s" % str(e)[:90]}
    return {"local": local, "publico": publico, "calzan": local == publico,
            "_nota": ("el archivo local incluye pre-registros y otros tipos que la lista "
                      "publica puede filtrar; una diferencia NO es por si sola un error, "
                      "pero tiene que poder explicarse")}


if __name__ == "__main__":
    print("DERIVAR — todo lo que se calcula desde el archivo\n")
    resultados = [corre(n, s, c) for n, s, c in DERIVACIONES]
    for r in resultados:
        marca = {True: "ok   ", False: "FALLO", None: "dry  "}[r["ok"]]
        print("  [%s] %-22s %s" % (marca, r["nombre"], r.get("salida") or r.get("motivo") or ""))
        if r["ok"] is False and r.get("motivo"):
            print("         %s" % r["motivo"].replace("\n", " ")[:200])

    print()
    pend = esperando_sello()
    if pend:
        print("  ESPERANDO SELLO: %d artefacto(s) que ningun sello cita todavia" % len(pend))
        for x in pend[:8]:
            print("     %-52s %s" % (x["archivo"], x["sha256"]))
        print("     (sellar es del laboratorio; aqui solo se cuenta y se muestra)")
    else:
        print("  esperando sello: 0")

    if not DRY:
        cmp = local_contra_publico()
        if cmp["calzan"] is None:
            print("  local vs publico: NO SE PUDO COMPARAR — %s" % cmp.get("motivo"))
        elif cmp["calzan"]:
            print("  local vs publico: %d = %d" % (cmp["local"], cmp["publico"]))
        else:
            print("  local vs publico: %d local · %d publico  <- DIFIEREN, hay que explicarlo"
                  % (cmp["local"], cmp["publico"]))

    fallos = [r for r in resultados if r["ok"] is False]
    if fallos:
        print("\n%d derivacion(es) fallaron. NO se dan por buenas: un resumen viejo que "
              "parece nuevo es peor que uno ausente." % len(fallos))
        sys.exit(1)
    print("\nlisto.")
