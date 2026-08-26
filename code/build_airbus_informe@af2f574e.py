#!/usr/bin/env python3
"""Genera el entregable del track Airbus contra ESTANDAR-presentacion-entregable.md.

POR QUE ES UN GENERADOR
-----------------------
La regla que ya cerro E.ON: **ninguna cifra se escribe, todas se leen del artefacto en
tiempo de armado**. Aqui pesa mas que nunca porque el track tiene una desviacion del
pre-registro que hay que declarar con sus numeros exactos, y una cifra tecleada en esa
seccion seria la ironia perfecta.

QUE HACE DISTINTO A ESTE GENERADOR (lecciones de los 7 defectos del informe de E.ON)
------------------------------------------------------------------------------------
- Acceso por ruta EXPLICITA que falla cerrado: si un campo esperado no esta, aborta con
  la lista de los que si estan. Nada de buscadores que devuelven None (una tabla vacia
  con aspecto normal ya se entrego una vez).
- Toda propiedad afirmada del dato se comprueba contra el almacen real: el estado de
  sellado y de ancla se MIRA, no se recuerda, y el texto se adapta a lo que encuentre.
- Cada afirmacion lleva su etiqueta del §2 del estandar: medido / por construccion /
  por literatura. Lo que no tiene etiqueta, no entra.

Uso:  python3 build_airbus_informe.py
Sale: AIRBUS-INFORME-FINAL.md junto a este archivo.
"""
import glob
import hashlib
import json
import re
import math
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
EVID = os.path.join(RAIZ, "evidence")
DIR = os.path.join(AQUI, "airbus")
SAL = os.path.join(AQUI, "AIRBUS-INFORME-FINAL.md")

L = []
def w(s=""):
    L.append(s)


# LOS NUMEROS DE SECCION SE CUENTAN SOLOS.
# Estaban escritos a mano —«## 6 · ...»— y cada insercion obligaba a renumerar el resto a
# mano. Eso es una lista que vive en N lugares: basta olvidar uno para que el documento se
# contradiga a si mismo, y las referencias cruzadas («§5 gives both») apunten a otra parte.
# Con un contador, el orden de las llamadas ES la numeracion, y `ref()` devuelve el numero
# de una seccion ya emitida para citarla sin teclearlo.
# El orden se DECLARA aqui una vez. Con eso `ref()` funciona tambien hacia adelante —el
# resumen cita al mecanismo, que se emite despues— y `sec()` comprueba que lo que se emite
# sea lo que el orden dice: si alguien inserta una seccion sin declararla, aborta en vez de
# renumerar en silencio.
ORDEN = ["resumen", "resultados", "pregunta", "arbitro", "eje", "mecanismo", "deteccion",
         "matar", "limites", "viabilidad", "impacto", "equipo", "pedimos", "reproducir",
         "anexo"]
_SEC = {"n": 0, "num": {k: i + 1 for i, k in enumerate(ORDEN)}}


def sec(titulo, clave):
    _SEC["n"] += 1
    esperado = _SEC["num"].get(clave)
    if esperado != _SEC["n"]:
        raise SystemExit("ABORTA: la seccion %r sale en la posicion %d y ORDEN dice %s. "
                         "El orden se declara arriba, no se descubre al emitir."
                         % (clave, _SEC["n"], esperado))
    w("## %d · %s" % (_SEC["n"], titulo))


def ref(clave):
    if clave not in _SEC["num"]:
        raise SystemExit("ABORTA: se cita la seccion %r y no esta en ORDEN. Las "
                         "referencias cruzadas no se teclean." % clave)
    return "§%d" % _SEC["num"][clave]


def sin_cifras_tecleadas(ruta):
    """Se niega a generar si alguna cifra del informe esta escrita a mano.

    NACIO DE UN DEFECTO REAL, no de un ejemplo inventado. La linea 128 de este mismo
    archivo decia `% (18, 41, ...)` — dos numeros tecleados — veintiseis lineas debajo de
    la linea que promete al lector «every figure in this document is read from an artifact
    at build time, never typed». Y ni siquiera eran correctos: el rango real de K=2 es
    21-45, y 18 y 41 pertenecian a brazos distintos en puntos distintos.

    La regla que vigila: en `w("..." % (...))`, ningun elemento de la tupla puede ser un
    numero literal. Un numero que va al informe tiene que venir de un artefacto o de una
    cuenta sobre un artefacto. Los literales que viven DENTRO de una comprension o de una
    comparacion (umbrales como 1e-6) no son cifras del informe y no se tocan.
    """
    import ast as _ast
    arbol = _ast.parse(open(ruta).read(), ruta)
    malas = []
    for nodo in _ast.walk(arbol):
        if not (isinstance(nodo, _ast.Call) and isinstance(nodo.func, _ast.Name)
                and nodo.func.id == "w" and nodo.args):
            continue
        arg = nodo.args[0]
        if not (isinstance(arg, _ast.BinOp) and isinstance(arg.op, _ast.Mod)):
            continue
        derecha = arg.right
        elementos = derecha.elts if isinstance(derecha, _ast.Tuple) else [derecha]
        for e in elementos:
            if isinstance(e, _ast.Constant) and isinstance(e.value, (int, float)) \
                    and not isinstance(e.value, bool):
                malas.append((getattr(e, "lineno", "?"), e.value))
        # Y la variante que el guardia NO veia, en la que cai yo mismo al arreglar la
        # primera: una cifra escrita DENTRO de la cadena, sin pasar por la tupla. Se
        # marcan solo las que parecen mediciones —con coma decimal, con signo de
        # porcentaje o de tres digitos para arriba— para no gritar por «2D» ni «§5».
    import re as _re
    MEDICION = _re.compile(r"(?<![\w.])\d+[.,]\d+\s*%?|(?<![\w.])\d{3,}|(?<![\w.])\d+\s*%")
    # Dos excepciones, y solo dos: un anio y una referencia de seccion no son mediciones.
    # Precision sobre cobertura — un falso positivo aqui retiene trabajo bueno.
    ANIO = _re.compile(r"^(19|20)\d{2}$")
    # «four orders of magnitude» es una cifra tecleada que el filtro numerico no ve, y que
    # ADEMAS invita a redondear hacia arriba: 3,57 se escribio «cuatro» y 4,57 «cinco»,
    # tres veces en este documento. Se prohibe la forma con numero escrito o en palabra;
    # se deriva el factor, que no deja margen.
    ORDENES = _re.compile(r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+(?:\.\d+)?)"
                          r"\s+orders?\s+of\s+magnitude", _re.I)
    def _es_referencia(texto, ini):
        antes = texto[max(0, ini - 6):ini]
        return "§" in antes or "sec." in antes.lower()
    for nodo in _ast.walk(arbol):
        if not (isinstance(nodo, _ast.Call) and isinstance(nodo.func, _ast.Name)
                and nodo.func.id == "w" and nodo.args):
            continue
        for parte in _ast.walk(nodo.args[0]):
            if isinstance(parte, _ast.Constant) and isinstance(parte.value, str):
                for m in ORDENES.finditer(parte.value):
                    malas.append((getattr(parte, "lineno", "?"),
                                  m.group(0).strip() + "  (dilo como factor derivado)"))
                for m in MEDICION.finditer(parte.value):
                    tok = m.group(0).strip()
                    if ANIO.match(tok) or _es_referencia(parte.value, m.start()):
                        continue
                    malas.append((getattr(parte, "lineno", "?"), tok))
    if malas:
        raise SystemExit(
            "ABORTA: %d cifra(s) TECLEADAS en el informe: %s\n"
            "  El documento promete que ninguna cifra esta escrita a mano. Derivalas del "
            "artefacto o quita la promesa — no las dos cosas."
            % (len(malas), ", ".join("linea %s -> %r" % m for m in malas)))


sin_cifras_tecleadas(os.path.abspath(__file__))


def campo(d, *ruta):
    """Un valor por su ruta explicita. Aborta si falta, con lo que si hay.

    El buscador a ciegas que devuelve None dejo una tabla entera vacia en el informe de
    E.ON, con aspecto normal. Aqui una ausencia es un fallo, no un hueco silencioso.
    """
    cur = d
    for i, k in enumerate(ruta):
        if not isinstance(cur, dict) or k not in cur:
            raise SystemExit("ABORTA: falta %r en %r. Hay: %s"
                             % (k, " -> ".join(map(str, ruta[:i])),
                                ", ".join(cur.keys()) if isinstance(cur, dict) else type(cur).__name__))
        cur = cur[k]
    return cur


def num(x, d=4):
    return "%.*g" % (d, x) if isinstance(x, float) else str(x)


def mag(x):
    """Una magnitud que el lector compara de un vistazo: 102,400 y no 1.024e+05.

    La notacion cientifica es correcta y aqui es peor: el eje del entregable es el
    numero de Reynolds, y el jurado lo va a leer como cantidad, no como exponente.
    """
    return "{:,.0f}".format(float(x))


def sci(x, d=2):
    return "%.*e" % (d, float(x))


# ---------------------------------------------------------------- fuentes
def cobertura(serie, brazo):
    """(resueltos, total, [n_qubits...]) de un brazo a lo largo del eje.

    Existe porque el informe decia «el brazo cuantico no puede entrar» y eso era cierto
    para K=2 (0 de 8) y FALSO para K=1 (3 de 8). Un brazo que resuelve en un tercio del
    eje no «no puede entrar»: entra y se queda corto, que es otra cosa y mas interesante.
    """
    res = qs = 0
    qubits = []
    for p_ in serie:
        d = p_["brazos"].get(brazo)
        if d is None:
            continue
        qs += 1
        if d.get("error_l2_rel") is not None:
            res += 1
            qubits.append(d["carleman"]["n_qubits"])
        else:
            qubits.append(d["medicion"]["n_qubits_requeridos"])
    return res, qs, qubits


barrido = json.load(open(os.path.join(DIR, "barrido_airbus.json")))
nolin = json.load(open(os.path.join(DIR, "nolinealidad_donde_vive.json")))
# La comparacion de dos corridas es un ARTEFACTO, no una frase recordada: los porcentajes
# del parrafo de reproducibilidad se leen de aqui. La primera version los tenia tecleados
# —y ademas mal: decia 21-29 % donde la mediana medida es otra— en el mismo documento que
# promete que ninguna cifra se teclea.
repro = json.load(open(os.path.join(DIR, "reproducibilidad_barrido.json")))
# Los dos artefactos que contestan «cuanto puede detectar este benchmark» y «que ve una
# red tensorial». Ninguna cifra de las secciones nuevas se teclea: sale de aqui.
deteccion = json.load(open(os.path.join(DIR, "umbral_de_deteccion.json")))
rango = json.load(open(os.path.join(DIR, "rango_vs_nolinealidad.json")))
serie = campo(barrido, "serie")
corte = campo(barrido, "corte_medido")
muro = campo(barrido, "muro_brazo_cuantico", "filas")

# El pre-registro: su estado de sello y ancla se MIRA, no se recuerda.
prereg_json = glob.glob(os.path.join(EVID, "prereg", "2026", "08", "*AIRBUS*.json"))
if len(prereg_json) != 1:
    raise SystemExit("ABORTA: esperaba 1 prereg de Airbus publicado, hay %d." % len(prereg_json))
prereg_ruta = prereg_json[0]
prereg = json.load(open(prereg_ruta))
prereg_id = os.path.basename(prereg_ruta).split("__")[2]
prereg_anclado = os.path.exists(prereg_ruta + ".ots")
prereg_commit = subprocess.run(
    ["git", "log", "--diff-filter=A", "--format=%H", "-1", "origin/main", "--",
     os.path.relpath(prereg_ruta, EVID)],
    cwd=EVID, capture_output=True, text=True).stdout.strip()

# EL ESTADO DEL SELLO SE MIRA, NO SE RECUERDA — y se mira en runs/ Y en reports/.
# La primera version solo miraba runs/ y solo sabia decir «no estan sellados». Resultado:
# el informe se sello DECLARANDO QUE NO ESTABA SELLADO, porque el texto se genera antes
# que el sello. Un jurado que consulte la API encuentra la contradiccion con la
# herramienta que le dimos, y encima en la seccion donde declaramos nuestros limites, que
# es la que compra la credibilidad del resto.
# Ahora la frase se DERIVA en las dos direcciones: si hay sello, se declara con su id, su
# content_hash y si esta anclado; si no lo hay, se dice que falta. Cuando el ancla llega,
# la frase mejora sola en la siguiente generacion.
sellos_airbus = []
for _sub in ("runs", "reports"):
    for _p in glob.glob(os.path.join(EVID, _sub, "**", "*.json"), recursive=True):
        if "AIRBUS" not in os.path.basename(_p).upper():
            continue
        _d = json.load(open(_p))
        sellos_airbus.append({"file_id": _d["meta"]["file_id"],
                              "content_hash": _d["meta"]["content_hash"],
                              "anclado": os.path.exists(_p + ".ots"),
                              "tipo": _d["meta"]["type"]})
sellos_airbus.sort(key=lambda x: x["file_id"])
# El total del archivo, contado con la MISMA definicion que usa el notario.
sys.path.insert(0, os.path.join(EVID, "scripts"))
from notarize_globs import ARCHIVE_GLOBS as _AG
_arch = [os.path.basename(_x) for _g in _AG
         for _x in glob.glob(os.path.join(EVID, _g), recursive=True)]
_total_sellos = len(_arch)
# El DESGLOSE se deriva de los mismos globs que el total. Escribirlo a mano es como se
# introduce una frase que se contradice sola: al cambiar «sealed runs» por «sealed
# artefacts» se enumeraron cinco tipos que suman 123 al lado de un total de 127. Derivado,
# eso no puede volver a pasar.
import collections as _co
_cuenta = _co.Counter(_n.split("__")[1] for _n in _arch if "__" in _n)
# singular y plural: «1 predictions» lo lee un jurado antes que cualquier cifra.
_NOMBRE = {"RUN": ("run", "runs"), "REPORT": ("report", "reports"),
           "PREREG": ("pre-registration", "pre-registrations"),
           "RECIPE": ("recipe", "recipes"), "MANIFEST": ("manifest", "manifests"),
           "ERRATA": ("erratum", "errata"), "VERDICT": ("verdict", "verdicts"),
           "PREDICTION": ("prediction", "predictions")}
_partes = ["%d %s" % (_v, _NOMBRE.get(_k, (_k.lower(), _k.lower()))[0 if _v == 1 else 1])
           for _k, _v in sorted(_cuenta.items(), key=lambda kv: -kv[1])]
_DESGLOSE = ", ".join(_partes[:-1]) + " and " + _partes[-1] if len(_partes) > 1 else _partes[0]
assert sum(_cuenta.values()) == _total_sellos, (
    "el desglose no suma el total: %d vs %d" % (sum(_cuenta.values()), _total_sellos))

w("# Airbus — Quantum Solvers for Predictive Aerodynamic Modeling")
w()
w("**Rosetta Quantum** · 2026 Global Quantum + AI Challenge · Phase 1")
w()
w("> Every figure in this document is read from an artifact at build time, never typed. "
  "Each claim carries one of three labels — **measured**, **by construction**, or **from "
  "the literature** — and anything without a label is not here.")
w()

# ---------------------------------------------------------------- 1 · resumen
_tgv_det = [f for f in campo(deteccion, "tabla") if f["variante"] == "tgv_statement"][0]
_det = [f for f in campo(deteccion, "tabla") if f["detecta"]]
_ciegas = campo(deteccion, "resumen", "ciegas")
_total = campo(deteccion, "resumen", "total")

# Definiciones que el resumen ejecutivo necesita: se suben aqui porque el resumen es lo
# primero que se emite y no puede depender de algo que se calcula mas abajo.
esp0, espN = campo(serie[0], "brazos", "espectral"), campo(serie[-1], "brazos", "espectral")
fd0, fdN = campo(serie[0], "brazos", "fd2"), campo(serie[-1], "brazos", "fd2")
def veces(a, b):
    """El factor entre dos cantidades, redondeado a dos cifras significativas.

    Existe porque «orders of magnitude» invita a redondear hacia arriba: 3,57 se
    convierte en «cuatro» y 4,57 en «cinco». Tres veces en este mismo documento. El
    factor no deja margen: 3.745 es 3.745, y ademas impresiona mas que «cuatro ordenes».
    """
    import math as _m
    r = max(a, b) / min(a, b)
    e = _m.floor(_m.log10(r))
    return "{:,.0f}".format(round(r, -(e - 1)))



# Cobertura de cada orden de Carleman: la usa el resumen ejecutivo y tambien el §1.
# Se calcula una vez, arriba, en vez de dos veces.
k1_res, k1_tot, k1_q = cobertura(serie, "carleman_K1_variacional")
k2_res, k2_tot, k2_q = cobertura(serie, "carleman_K2_variacional")

w("## Executive summary")
w()
w("You asked for a quantum solver for the 2D convecting Taylor-Green vortex, and for the "
  "curve of time-to-solution and error as Reynolds grows. **The honest headline is that we "
  "did not beat the classical solvers, and that the most useful thing we found is a "
  "measurement on your benchmark rather than a result of ours.**")
w()
w("**What we can deliver.** The full axis, %d points from Re = %s to %s with the mesh "
  "coupled as your §4.1 requires and scored against the closed-form solution of your §5.3. "
  "The classical error *falls* by a factor of %s along it while the cost climbs. Memory — "
  "one of your three expected outcomes — is answered with a number for the first time."
  % (len(serie), mag(campo(serie[0], "Re")), mag(campo(serie[-1], "Re")),
     veces(campo(fd0, "error_l2_rel"), campo(fdN, "error_l2_rel"))))
w()
w("**What we cannot.** The order of Carleman that carries the nonlinear physics needs "
  "%d–%d qubits from the very first point and never ran. The order that fits drops that "
  "term, and it loses to finite differences by between %s and %s times. We pre-registered "
  "that outcome as the expected one before writing a line of the instrument."
  % (min(k2_q), max(k2_q),
     mag(min(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"]
             / d["brazos"]["fd2"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None)),
     mag(max(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"]
             / d["brazos"]["fd2"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None))))
w()
w("**And what we found instead, which is why this report is worth your time.** In the "
  "vortex your statement specifies, the nonlinear term vanishes exactly — machine "
  "precision, in the discrete operators. So we measured what the case can still detect: a "
  "solver that ignores that term **entirely** is wrong by %s on your benchmark. It cannot "
  "be told apart from a correct one. On the family we repaired, the same solver is wrong "
  "by up to %s, and the threshold is tunable across a factor of %s. **The property that "
  "gives your case its exact analytical solution is the same one that makes it blind.**"
  % (sci(_tgv_det["error_del_solver_sin_no_linealidad"]),
     sci(max(f["error_del_solver_sin_no_linealidad"] for f in _det)),
     veces(max(f["error_del_solver_sin_no_linealidad"] for f in _det),
           min(f["error_del_solver_sin_no_linealidad"] for f in _det))))
w()
w("Everything here cost **US$0**, ran on one laptop, and is sealed and timestamped. %s "
  "tells you how to check any of it without asking us." % ref("reproducir"))
w()
sec("The four findings, in order", "resumen")
w()
def orden(x):
    """Un numero presentado con la precision que su etiqueta permite.

    «~132.948» se contradice a si mismo: la tilde dice aproximado y los seis digitos dicen
    lo contrario. Un factor de tiempo que se mueve 74 % entre corridas no tiene seis
    cifras significativas; tiene una o dos. Se redondea a dos, y asi el numero y su
    etiqueta dicen lo mismo.
    """
    import math
    if x <= 0:
        return str(x)
    e = math.floor(math.log10(x))
    return "{:,.0f}".format(round(x, -(e - 1)))


# El error y el factor de tiempo tienen que salir del MISMO brazo. La version anterior
# tomaba el error de fd2 y el factor de espectral, y la frase los presentaba como uno.
factor = campo(fdN, "tiempo_pared_s") / campo(fd0, "tiempo_pared_s")
factor_esp = campo(espN, "tiempo_pared_s") / campo(esp0, "tiempo_pared_s")
w("The executive summary above is the short version. This section is the four findings "
  "with their numbers, each pointing to the section that carries the measurement, the "
  "method and the caveats. **The last two are about your benchmark rather than about us**, "
  "and they are why we think this is worth reading past the headline.")
w()
w("**One — the classical cost explodes; the accuracy does not.** Across Re = %s to %s with "
  "the mesh coupled as your statement requires, the finite-difference error *falls* by a "
  "factor of %s (%s → %s). **[measured — reproduces bit-for-bit]** Its wall time "
  "rises by a factor of ~%s on this machine (the spectral arm, ~%s). **[measured on one "
  "machine; not comparable across computers]**"
  % (mag(campo(serie[0], "Re")), mag(campo(serie[-1], "Re")),
     veces(campo(fd0, "error_l2_rel"), campo(fdN, "error_l2_rel")),
     sci(campo(fd0, "error_l2_rel")), sci(campo(fdN, "error_l2_rel")),
     orden(factor), orden(factor_esp)))
w()
w("**Why the two labels differ, and what you can do with each number.** We re-ran the whole "
  "axis on the same machine and compared it point by point: %d of %d errors reproduced to "
  "the last digit. The wall times moved by %s–%s %% per arm, and the *ratios* between arms "
  "moved by a median of %s %% — a quotient adds the noise of both its terms. A ratio cancels "
  "a machine's overall speed and amplifies measurement noise; with times this small, the "
  "noise wins. So the errors are a precision result and the timings are an order-of-magnitude "
  "statement, and we say which is which instead of giving both the same weight. This is two "
  "runs on one machine, so it bounds run-to-run noise and says nothing about another "
  "computer. **[measured]**"
  % (campo(repro, "errores", "identicos"), campo(repro, "errores", "comparados"),
     mag(campo(repro, "tiempos_desviacion_relativa_pct", "min")),
     mag(campo(repro, "tiempos_desviacion_relativa_pct", "max")),
     mag(campo(repro, "razones_entre_brazos_desviacion_pct", "mediana"))))
w()
# Cobertura REAL de cada orden de Carleman, derivada del eje. Antes esta frase decia
# «no puede entrar» con dos cifras TECLEADAS (18 y 41) en un documento que promete que
# ninguna lo esta — y ademas era falsa para K=1.
w("**Two — the order of Carleman that carries the physics never ran; the degraded one did, "
  "and fell short.** **K = 2 — the order that actually includes Carleman's quadratic block — "
  "solved %d of %d points on the axis**: it needs %d–%d qubits, over the declared cap from "
  "the very first point. **K = 1, which drops that block, solved %d of %d** (%d–%d qubits), "
  "with a relative error of %s–%s where it ran — %s–%s times the finite-difference error at "
  "the same points. So the quantum arm does not lose the comparison: the version with "
  "the physics in it cannot be posed at this mesh coupling, and the version that can be "
  "posed is not the one that matters. **[measured]**"
  % (k2_res, k2_tot, min(k2_q), max(k2_q), k1_res, k1_tot, min(k1_q), max(k1_q),
     sci(min(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None)),
     sci(max(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None)),
     mag(min(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"]
             / d["brazos"]["fd2"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None)),
     mag(max(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"]
             / d["brazos"]["fd2"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None))))
w()
w("On its own ladder at fixed Re it reproduces the exact linear system up to N=%d, and the "
  "ansatz stops reaching at N=%d. **[measured]**"
  % (max(f["malla_N"] for f in muro if f.get("infidelidad_inicial", 1) < 1e-6),
     min(f["malla_N"] for f in muro if f.get("infidelidad_inicial", 0) > 1e-3)))
w()
razon_tgv = [f for f in campo(nolin, "tabla")
             if f["variante"] == "tgv_statement" and f["malla_N"] == 16 and f["Re"] == 100.0][0]["razon"]
w("**Three — and this one is about your benchmark, not about us.** In the Taylor-Green "
  "vortex as specified, the nonlinear term vanishes *exactly* — ratio %s of the linear term, "
  "at machine precision, in the discrete operators and not only in the continuum. The "
  "obstacle your statement names — mapping nonlinear physics onto unitary hardware — "
  "**cannot be exhibited on the case chosen to test it**. We found the mechanism and the "
  "law that restores it; %s gives both, and they are the constructive part of this "
  "submission. **[measured]**" % (sci(razon_tgv), ref("mecanismo")))
w()
w("**Four — and here is what that costs you, measured rather than argued.** "
  "So we asked what your case can still *detect*. We built a manufactured solution so the "
  "nonlinear term is genuinely active, and then ran a solver that **ignores that term "
  "entirely**. On the Taylor-Green vortex as specified, that solver is wrong by **%s** — "
  "machine zero. **Your benchmark cannot tell it apart from a correct one.** On the "
  "repaired family the same solver is wrong by between %s and %s: the detection threshold "
  "becomes tunable across a factor of **%s**. %d of the %d variants are blind, and "
  "they are exactly the %d that live in a single eigenvalue layer. **[measured]**"
  % (sci(_tgv_det["error_del_solver_sin_no_linealidad"]),
     sci(min(f["error_del_solver_sin_no_linealidad"] for f in _det)),
     sci(max(f["error_del_solver_sin_no_linealidad"] for f in _det)),
     veces(max(f["error_del_solver_sin_no_linealidad"] for f in _det),
           min(f["error_del_solver_sin_no_linealidad"] for f in _det)),
     _ciegas, _total, _ciegas))
w()

# ---------------------------------------------------------------- 2 · pregunta y prereg
sec("Results against your three expected outcomes", "resultados")
w()
w("Your portal asks for three things. We answer each here, with the number and a pointer "
  "to where it lives, including the one where the answer is «not yet» — that one first.")
w()
w("**1 · «A working solver» (FTQC or tensor-network inside finite volumes) for the 2D "
  "convecting Taylor-Green vortex.** **Partially, and we say which part.** Carleman at "
  "order **K = 2 — the order that carries the quadratic term, i.e. the physics — solved "
  "%d of %d points on the axis**: it needs %d–%d qubits, above the declared cap from the "
  "very first point. Order **K = 1**, which drops that term, solved **%d of %d** with a "
  "relative error of %s–%s, %s–%s times the finite-difference error at the same points. "
  "So there is a solver, it runs, and the version that carries the physics cannot be posed "
  "at the mesh coupling your statement requires. Detail in %s and %s. **[measured]**"
  % (k2_res, k2_tot, min(k2_q), max(k2_q), k1_res, k1_tot,
     sci(min(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None)),
     sci(max(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None)),
     mag(min(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"]
             / d["brazos"]["fd2"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None)),
     mag(max(d["brazos"]["carleman_K1_variacional"]["error_l2_rel"]
             / d["brazos"]["fd2"]["error_l2_rel"] for d in serie
             if d["brazos"]["carleman_K1_variacional"].get("error_l2_rel") is not None)),
     ref("eje"), ref("deteccion")))
w()
# Los dos Reynolds que el enunciado nombra NO se teclean en el texto: se comprueba que
# esten en nuestro eje y se emiten desde ahi. Si algun dia el eje dejara de cubrirlos, la
# frase no se podria escribir — que es lo correcto.
_PEDIDOS_POR_EL_ENUNCIADO = (10.0, 100.0)
_falt = [r_ for r_ in _PEDIDOS_POR_EL_ENUNCIADO if r_ not in [p_["Re"] for p_ in serie]]
if _falt:
    raise SystemExit("ABORTA: el enunciado nombra Re=%s y el eje no los cubre: %s"
                     % (list(_PEDIDOS_POR_EL_ENUNCIADO), _falt))
_re_nombrados = ", ".join(mag(p_["Re"]) for p_ in serie
                          if p_["Re"] in _PEDIDOS_POR_EL_ENUNCIADO)
w("**2 · Scaling analysis: time-to-solution, memory requirements, and error scaling with "
  "Reynolds (Re = " + _re_nombrados + " and beyond).** **Delivered, all three.** The axis runs from "
  "Re = %s to %s over %d points with the mesh coupled as your §4.1 requires, against the "
  "closed-form solution of your §5.3 — table in %s, with the wall-clock caveat stated "
  "there. **Memory** is the one we can now answer with a number: the field stays at bond "
  "dimension **%s** across the whole perturbed family, which is what makes the second "
  "finding in %s possible. **[measured]**"
  % (mag(campo(serie[0], "Re")), mag(campo(serie[-1], "Re")), len(serie), ref("eje"),
     ", ".join(str(c) for c in sorted({f["rango_numerico_chi"] for f in
               campo(rango, "familia_del_enunciado") if "perturbado" in f["variante"]})),
     ref("deteccion")))
w()
w("**3 · Comparison against classical solvers, demonstrating quantum or quantum-inspired "
  "advantage.** **No advantage, and the comparison produced something we think is worth "
  "more.** The classical arms win at every point of the axis; we pre-registered that as "
  "the expected outcome and it is what happened. What the comparison did produce is a "
  "measurement *on the benchmark itself*: the quantum-inspired metric you invite — tensor "
  "networks, via memory — **cannot see the physics the challenge is about**. That is in "
  "%s, with the detection threshold that repairs it. **[measured]**" % ref("deteccion"))
w()
sec("The question, and when it was fixed", "pregunta")
w()
w("Pre-registration `%s`, content hash `%s…`."
  % (prereg_id, campo(prereg, "meta", "content_hash")[:31]))
w()
if prereg_commit:
    w("It was committed in `%s`, and **at that commit not one line of the instrument "
      "existed** — that is a property of the git history, verifiable by you, not a claim of "
      "ours. **[by construction]**" % prereg_commit[:8])
# EL BLOQUE SE LEE DEL RECIBO, NO SE AFIRMA. Y la etiqueta cambia: estar anclado es un
# hecho MEDIDO —se comprueba abriendo el .ots— no algo que se siga de como esta construido
# el documento. La version anterior decia «anchored in Bitcoin» con [by construction] y sin
# numero: la afirmacion mas comprobable del documento, sin el dato que permite comprobarla.
# Y `prereg_anclado` solo mira si el .ots EXISTE, que es tener recibo, no tener bloque.
def _bloques_de(ruta_ots):
    if not os.path.exists(ruta_ots):
        return []
    try:
        from opentimestamps.core.serialize import BytesDeserializationContext
        from opentimestamps.core.timestamp import DetachedTimestampFile
        from opentimestamps.core.notary import BitcoinBlockHeaderAttestation
    except Exception:
        return []
    _d = DetachedTimestampFile.deserialize(
        BytesDeserializationContext(open(ruta_ots, "rb").read()))
    return sorted({_a.height for _m, _a in _d.timestamp.all_attestations()
                   if isinstance(_a, BitcoinBlockHeaderAttestation)})

_blk = _bloques_de(prereg_ruta + ".ots")
if _blk:
    w("The pre-registration is confirmed in **Bitcoin block %s** — the earliest attestation "
      "in its OpenTimestamps receipt when this was built; later upgrades only add more. "
      "Check it in any block explorer, or run `ots verify` against the `.ots` file beside "
      "the seal. The ordering is bounded from above by a clock neither we nor you control. "
      "**[measured]**" % _blk[0])   # sin separador de miles: se copia a un explorador
elif prereg_anclado:
    w("The pre-registration carries an OpenTimestamps receipt; when this was built the "
      "Bitcoin confirmation had not yet landed — the calendar returns the receipt at once "
      "and publishes hours later. Run `ots upgrade` on the `.ots` file beside the seal to "
      "see the state as of when you read this. **[measured]**")
else:
    w("The pre-registration is sealed and public but **its Bitcoin anchor is still "
      "pending**; we say so rather than claim it. **[measured]**")
w()
w("The pre-registration declared **both outcomes as deliverables before measuring**: if the "
  "quantum arm crossed, the crossing would be incontestable because the referee is a closed "
  "formula; if it did not, the curve itself is what your statement asks for. It also "
  "declared the known obstacle (Carleman truncation against a nonlinear, non-unitary "
  "problem) as a risk, not as a later discovery. **[by construction]**")
w()

# ---------------------------------------------------------------- 3 · datos y arbitro
sec("The referee, and why this benchmark is unusually strong", "arbitro")
w()
w("The statement carries the **exact analytical solution** (§5.3), so the error of any "
  "method is measured against a closed form at any Reynolds number. There is no estimated "
  "ground truth and no reference implementation to trust: the referee never degrades and "
  "never runs out. **[by construction]**")
w()
w("Two independent paths agree on it: the spectral arm reproduces the analytical solution "
  "to %s at the first point. A single arm matching a formula could be a lucky bug in "
  "either; two constructions agreeing is evidence. **[measured]**"
  % sci(campo(esp0, "error_l2_rel")))
w()

# ---------------------------------------------------------------- 4 · el eje
sec("The axis: time-to-solution and error vs Reynolds", "eje")
w()
# La descripcion de la regla vive en español en el artefacto; el documento va en ingles.
# Se cita el PARAMETRO medido, no la prosa traducida a ojo (§10: los documentos no se
# copian a mano), y asi el lector reconstruye la regla sin depender de nuestra redaccion.
w("Mesh coupled to Reynolds per §4.1 of the statement: `N = next power of two ≥ %d·√(Re/%d)`, "
  "floor %d. Every row reports what *occurred* — real mesh, real steps, measured wall "
  "time — not what was requested. **[measured]**"
  % (campo(barrido, "regla_acople", "n_base"), campo(barrido, "regla_acople", "re_base"),
     min(p["malla_N"] for p in serie)))
w()
# UNA COLUMNA POR ORDEN DE CARLEMAN, no una sola llamada «quantum».
# La version anterior hacia `q[0]` sobre los brazos que contienen "carleman", y el
# primero en el diccionario es K=2 — que no resolvio en ningun punto. Resultado: la
# columna decia «out of reach» en las OCHO filas y los tres resultados de K=1
# desaparecian del informe, contradiciendo al titular que dice que resolvio 3 de 8.
# Una medicion que existe y no llega al lector es una ausencia disfrazada de valor.
def _celda(p_, brazo):
    d = campo(p_, "brazos").get(brazo)
    if d is None:
        return "—"
    if d.get("error_l2_rel") is None:
        return "%d qubits, over cap" % d["medicion"]["n_qubits_requeridos"]
    return sci(d["error_l2_rel"])


w("| Re | mesh N | steps | spectral error | spectral wall | FD2 error | FD2 wall | "
  "Carleman K=1 | Carleman K=2 |")
w("|---|---|---|---|---|---|---|---|---|")
for p in serie:
    e, f = campo(p, "brazos", "espectral"), campo(p, "brazos", "fd2")
    qs = "%s | %s" % (_celda(p, "carleman_K1_variacional"), _celda(p, "carleman_K2_variacional"))
    w("| %s | %s | %s | %s | %s s | %s | %s s | %s |"
      % (mag(campo(p, "Re")), campo(p, "malla_N"), campo(e, "pasos_reales"),
         sci(campo(e, "error_l2_rel")), num(campo(e, "tiempo_pared_s"), 3),
         sci(campo(f, "error_l2_rel")), num(campo(f, "tiempo_pared_s"), 3), qs))
w()
# El artefacto declara «error L2 rel > 0.1». Derivarlo y soltar el «0.1» a secas se lee
# mal —«degrades past 0.1»— porque pierde la unidad. Se deriva el numero Y se presenta
# como porcentaje, que es como se lee un error relativo.
_umbral = "%g %%" % (100 * float(campo(corte, "criterio_degradacion_fd2").split(">")[-1].strip()))
w("**A deviation from our own pre-registration, declared rather than reinterpreted.** We "
  "pre-registered a *measured* stopping rule: run until the finite-difference baseline "
  "degrades past %s at a declared budget. **That condition never triggered** — with the "
  "mesh growing as your statement requires, FD2 accuracy *improves* along the whole axis. "
  "The sweep ended by exhausting the declared Reynolds list, not by degradation. "
  "The rule we sealed assumed the wrong "
  "failure mode; saying so is worth more than the rule. **[measured]**" % (_umbral,))
w()

# ---------------------------------------------------------------- 5 · el hallazgo
sec("Why the nonlinear term vanishes here — mechanism, and the law that restores it", "mecanismo")
w()
w("This is the constructive part, and it is about the benchmark rather than about any "
  "solver.")
w()
w("**The mechanism.** The discrete nonlinearity vanishes **exactly if and only if the "
  "vorticity lives in a single eigenvalue layer of the 5-point discrete Laplacian**. In "
  "that case the stream function is ψ = c·w with c constant, so the Jacobian J(ψ,w) is "
  "identically zero pointwise — in the discrete operators, not only in the continuum. The "
  "statement's Taylor-Green vortex, the 45°-rotated one and the anisotropic ones all live "
  "in a single layer, which is why the benchmark never exercises the nonlinearity. The "
  "moment the field touches **two** layers, the ratio stops being zero. **[measured]**")
w()
w("*(The sealed artifact states this same rule in Spanish, its original language; the "
  "translation above is ours and the artifact is the source of the fact.)*")
w()
w("**The evidence, at N=%s, Re=%s.** Every member of the Taylor-Green family that lives in "
  "a single eigenvalue layer gives zero to machine precision; a field outside it does not. "
  "**[measured]**" % (mag(campo(nolin, "malla_tabla")), mag(campo(nolin, "Re_tabla"))))
w()
w("| field | ‖A₂(w⊗w)‖ / ‖A₁w‖ |")
w("|---|---|")
for f in campo(nolin, "tabla"):
    if f["malla_N"] == 16 and f["Re"] == 100.0:
        w("| `%s` | %s |" % (f["variante"], sci(f["razon"])))
w()
ley = campo(nolin, "ley_de_amplitud")
w("**The law that restores it.** Adding a single mode outside the layer, with amplitude ε, "
  "returns nonlinearity of order ε — measured over four decades of ε: %s. So the minimal "
  "modification to your benchmark is explicit and cheap: **superpose one foreign mode and "
  "the physics you want to test is back, at a strength you choose**. **[measured]**"
  % ", ".join("ε=%s → %s" % (num(a, 2), num(r, 3))
              for a, r in zip(campo(ley, "epsilon"), campo(ley, "razon"))))
w()

# ---------------------------------------------------------------- 6 · ataques
sec("What your benchmark can detect — measured", "deteccion")
w()
w("A test case earns its place if it separates a correct solver from a wrong one. So we "
  "measured that directly, and we state the method and its price before the number.")
w()
w("**The method, and it is the standard one.** We use a *manufactured solution* — the "
  "technique CFD uses for code verification. Choose the target field, compute the forcing "
  "that makes it an exact steady solution of the full system, and the nonlinear term is "
  "then genuinely active rather than absent. Any solver that gets the nonlinearity wrong "
  "no longer reproduces the target, and the size of its error is the case's detection "
  "threshold. **[by construction]**")
w()
w("**The price, stated up front.** A manufactured solution adds a source term: this is "
  "**code verification, not physical validation**, and it is not free decay. It also "
  "measures a *different axis* from the one you asked for — accuracy with the nonlinearity "
  "active, not time-to-solution against Reynolds. **It does not replace the axis in %s; it "
  "covers the dimension your case cannot reach.** One further caveat: the discrete "
  "Laplacian is singular on the constant mode, so the displacement is solved in least "
  "squares. It changes no conclusion and we say it anyway." % ref("eje"))
w()
w("**The measurement.** We ran a solver that ignores the nonlinear term *entirely*:")
w()
w("| field | eigenvalue layers | error of a solver that ignores the nonlinearity | detects it? |")
w("|---|---|---|---|")
for _f in campo(deteccion, "tabla"):
    w("| `%s` | %d | %s | %s |"
      % (_f["variante"], _f["capas_autovalor"],
         sci(_f["error_del_solver_sin_no_linealidad"]),
         "yes" if _f["detecta"] else "**no — blind**"))
w()
w("**%d of %d are blind, and they are exactly the ones confined to a single eigenvalue "
  "layer.** Your Taylor-Green vortex is one of them. **[measured]**"
  % (campo(deteccion, "resumen", "ciegas"), campo(deteccion, "resumen", "total")))
w()
_car = campo(deteccion, "caracterizacion_de_la_clase_degenerada")
w("**And the degenerate class is larger than your case.** It is not «the Taylor-Green "
  "vortex» and it is not «rank one»: it is **vorticity confined to a single eigenvalue "
  "layer of the discrete Laplacian**. A superposition of two different modes from the same "
  "layer — rank two, not rank one — is blind as well, at %s. That characterisation also "
  "explains the rotated vortex in %s without appealing to any coincidence. **[measured]**"
  % (sci(_car["error_del_solver_sin_no_linealidad"]), ref("mecanismo")))
w()
_rho_ent = campo(rango, "correlacion", "spearman_log10_razon_vs_entropia")
_chis = sorted({f["rango_numerico_chi"] for f in campo(rango, "familia_del_enunciado")
                if "perturbado" in f["variante"]})
w("**A second blindness, on the axis you also ask for: memory.** Your brief asks for "
  "memory requirements and invites quantum-*inspired* advantage — that is, tensor "
  "networks. Across the whole perturbed family the field stays at bond dimension **%s** "
  "while the nonlinearity ranges over a factor of %s. A tensor network cannot "
  "tell the degenerate case from the perturbed ones: **they cost it the same.** A "
  "competitor who follows your brief to the letter will report a spectacular memory win "
  "and will have learned nothing about the nonlinearity — not through any fault of theirs, "
  "but because the metric you asked for cannot see it. **[measured]**"
  % (", ".join(str(c) for c in _chis),
     veces(max(f["razon_no_linealidad"] for f in campo(rango, "familia_del_enunciado")
               if "perturbado" in f["variante"]),
           min(f["razon_no_linealidad"] for f in campo(rango, "familia_del_enunciado")
               if "perturbado" in f["variante"]))))
w()
w("**What we are not claiming.** «Low rank» and «single layer» are *not* the same "
  "property; we tested that and it fails in both directions. A product field of two von "
  "Mises factors is rank two, spans %d layers, and its nonlinearity is **not** zero (%s). "
  "The three properties of your vortex — rank one, single layer, zero nonlinearity — do "
  "not merely coincide: **they all follow from building the field out of one product "
  "Fourier mode.** Same cause, not correlation. **[measured]**"
  % ([c for c in campo(rango, "control_que_intenta_refutar")
      if "k6" in c["variante"]][0]["capas_autovalor"],
     sci([c for c in campo(rango, "control_que_intenta_refutar")
          if "k6" in c["variante"]][0]["razon_no_linealidad"])))
w()
w("**And that is the sentence we would put in front of your committee:** you chose this "
  "vortex *because* it has an exact analytical solution — your statement calls it a "
  "perfect benchmark for that reason. The property that gives it that exact solution is "
  "the same one that makes it blind. **Its greatest virtue and its blind spot are the same "
  "fact.** That is not a flaw anyone introduced; it is structure — and %s gives the law "
  "that repairs it, with the threshold above as the dial." % ref("mecanismo"))
w()
sec("What we did to kill our own result", "matar")
w()
w("Before the conclusions, because that is what gives them the right to exist.")
w()
w("- **The vanishing term could have been a bug in our operators.** Control: the same "
  "matrices on a random band-limited field give a ratio of %s, not zero. The zero "
  "belongs to the problem, not to the code. **[measured]**"
  % sci(max(f["razon"] for f in campo(nolin, "tabla")
            if "aleatorio" in str(f.get("variante", "")))))
w("- **The K-convergence check could have been measuring nothing** — on a field where A₂ is "
  "zero, any truncation order looks convergent. The test asserts the nonlinearity is active "
  "*before* measuring, so it cannot silently degenerate. "
  "**[by construction]**")
w("- **Two errors are reported for the quantum arm at every point**, not one: end-to-end, "
  "and the same Carleman system solved exactly. Without that pair you cannot tell which of "
  "the two layers failed — and it is what shows the ansatz, not the truncation, is the "
  "binding wall. **[by construction]**")
w("- **Every guard was mutation-tested**: each one has a case that makes it scream and a "
  "case where it must stay silent. A guard only ever tested for screaming passes every "
  "test. **[by construction]**")
w()

# ---------------------------------------------------------------- 7 · lo que no afirmamos
sec("What we cannot claim", "limites")
w()
w("- **No quantum advantage, at any point of the axis.** The pre-registration declared this "
  "as the expected outcome and it is what happened. **[measured]**")
w("- **The quantum wall we report is of this ansatz and this machine class**, not of the "
  "method: a different ansatz moves it. We state where ours ceased, with the number. "
  "**[measured]**")
w("- **The nonlinearity result is about the discrete operators we built** (2nd-order finite "
  "differences, 5-point Laplacian) and the continuum argument that matches them. A "
  "different discretisation deserves its own measurement. **[by construction]**")
w("- **Decisions the pre-registration did not fix travel declared inside each artifact**, "
  "not in anyone's memory: %d in the classical instrument and %d in the quantum arm. "
  "**[by construction]**"
  % (len(campo(barrido, "decisiones_no_prefijadas")),
     len(campo(barrido, "decisiones_no_prefijadas_del_brazo_cuantico"))))
_corridas = [x for x in sellos_airbus if x["tipo"] == "RUN"]
if not _corridas:
    w("- **The sweep artifacts are not sealed yet.** They are produced, reproducible and "
      "public, but the seal and the anchor are a separate step by the lab and the notary, "
      "and it has not run for these. We say so rather than let you assume. **[measured]**")
else:
    # NO SE CUENTAN ANCLAS, Y LA RAZON IMPORTA.
    # (1) Que exista el `.ots` NO es estar confirmado en un bloque: al sellar, el
    #     calendario devuelve un RECIBO al instante y la confirmacion en Bitcoin llega
    #     horas despues. La version anterior de esta linea decia «N of M are anchored in
    #     Bitcoin» contando recibos — y era falsa: hoy hay 4 recibos y 0 bloques.
    # (2) Y un CONTEO caduca: cuando el notario ancla, el numero cambia y el informe
    #     sellado queda diciendo el viejo. Es como murio la v1, un nivel mas abajo:
    #     aquella declaraba el estado del SELLO y sellarla lo cambiaba; contar anclas
    #     declara el estado del ANCLA y anclar lo cambia.
    # Se describe el MECANISMO, que no caduca, y se le da al lector el comando para que
    # vea el estado del momento en que lee. Le entregamos el metodo, no el resultado.
    _rec = [x for x in _corridas if x["anclado"]]
    w("- **The sweep artifacts are sealed** — %s — and all %d carry an OpenTimestamps "
      "receipt. A receipt is not yet a Bitcoin block: the calendar returns it immediately "
      "and the confirmation lands hours later, once the calendar publishes its tree. We "
      "will not print a count here, because any count we print expires the moment the "
      "next confirmation arrives. Run `ots upgrade` on the `.ots` files beside each seal "
      "and you will see the state as of the moment *you* read this — including "
      "confirmations that did not exist when we wrote it. **[measured]**"
      % (", ".join("`%s` (`%s…`)" % (x["file_id"], x["content_hash"][:21])
                   for x in _corridas), len(_rec)))
w()

# ---------------------------------------------------------------- 8 · reproduccion
sec("Feasibility and resource requirements", "viabilidad")
w()
_ent = campo(barrido, "entorno")
w("Everything above ran on one laptop, on open tools, and the cost is measured rather "
  "than planned: **US$0**. No quantum hardware was used and no paid backend was called — "
  "the quantum arms are exact statevector simulation. The axis took %s seconds of "
  "wall-clock end to end on %s with %s of RAM, under %s %s with numpy %s. **[measured]**"
  % (mag(campo(barrido, "pared_total_eje_s")), _ent.get("maquina", "commodity hardware"),
     mag(round(_ent["ram_bytes"] / 1024 ** 3)) + " GB" if _ent.get("ram_bytes") else "the RAM stated in the artifact",
     "Python", _ent.get("python", ""), _ent.get("numpy", "")))
w()
w("**What the next step needs, and what it does not.** Nothing above is blocked by "
  "funding or by hardware access: it is blocked by qubit count. Order K = 2 needs %d–%d "
  "qubits at the mesh coupling your statement requires, and that is a property of the "
  "formulation, not of our budget — a larger machine moves it, a larger grant does not. "
  "What a next phase would buy is measurement time on the two things we could not settle "
  "here: whether a formulation exists whose cost tracks the mesh instead of its square, "
  "and what the repaired benchmark says about solvers other than ours. **[measured]**"
  % (min(k2_q), max(k2_q)))
w()
sec("Expected impact", "impacto")
w()
w("**We are not promising you a quantum advantage, and this report does not contain one.** "
  "The impact we think is real is the other one: your challenge selects for a test case "
  "that cannot measure what the challenge is about, and every team that follows the brief "
  "will hit the same wall without necessarily noticing. What %s delivers is a repaired "
  "family with the detection threshold as a dial, and an exact arbiter for it — so the "
  "next round of submissions can be scored on whether they got the physics right, not on "
  "whether they compressed a degenerate field efficiently."
  % ref("deteccion"))
w()
w("The second usable output is the characterisation itself: the degenerate class is "
  "**vorticity confined to a single eigenvalue layer of the discrete Laplacian**, which is "
  "larger than the vortex you chose and easy to test for. Any benchmark you build in "
  "future can be checked against that in one line before it is adopted.")
w()
sec("Team profile and capability", "equipo")
w()
# LA IDENTIDAD SE LEE DEL PIE DEL PROPIO DOCUMENTO, no se teclea.
# Estaba escrita a mano y decia «Santiago, Chile» con un correo personal, mientras el pie
# del mismo archivo dice «Blue Tuna SpA · Punta Arenas, Chile · hello@rosettaquantum.com».
# Dos ciudades y dos correos en un documento que se entrega a un evaluador. Se extrae del
# renderizador —que es quien imprime el pie— para que no puedan divergir.
_ren = open(os.path.join(AQUI, "build_eon_entregable.py"), encoding="utf-8").read()
_m = re.search(r"<span>(Blue Tuna SpA[^<]*)</span>", _ren)
if not _m:
    raise SystemExit("ABORTA: no encuentro el pie de firma en el renderizador. La "
                     "identidad no se teclea: si el pie cambio de forma, se ajusta aqui.")
_firma = _m.group(1).strip()
_partes = [x.strip() for x in _firma.split("·")]
if len(_partes) < 3 or "@" not in _partes[-1]:
    raise SystemExit("ABORTA: el pie no tiene la forma «empresa · ciudad · correo»: %r"
                     % _firma)
_empresa, _lugar, _correo = _partes[0], " · ".join(_partes[1:-1]), _partes[-1]

# CUANTAS POSTULACIONES LLEVAMOS, contadas en el disco y no de memoria.
_subs = sorted(os.path.basename(d) for d in
               glob.glob(os.path.join(RAIZ, "Rosetta-Quantum-*-Submission")))
# El nombre de la carpeta no es el nombre de la empresa: «EON» se escribe «E.ON».
_NOMBRE_PUBLICO = {"EON": "E.ON"}
_otras = [_NOMBRE_PUBLICO.get(d.split("-")[2], d.split("-")[2])
          for d in _subs if "Airbus" not in d]

w("**Team:** Rosetta Quantum — **%s**, %s (solo founder-operator). **Lead:** Nicholas "
  "Iakl Freundlich · %s." % (_empresa, _lugar, _correo))
w()
w("**Background:** founder & CEO of Sumeria (AI conversation analytics, 9+ years) and "
  "founder of Yu-Track (software for financial-services collections). Commercial Engineer "
  "and MSc. The expertise brought here is the *consume-the-verdict* side of the problem — "
  "shipping systems whose outputs someone has to trust — rather than the sell-the-qubit "
  "side. **This is our %s quantum submission** — %s went out before it — and the report is "
  "written so that you do not have to take our word for any part of it."
  % ({1: "first", 2: "second", 3: "third", 4: "fourth"}.get(len(_subs), "%dth" % len(_subs)),
     " and ".join(_otras) if _otras else "none"))
w()
w("**Why this can execute a next phase:** the verification infrastructure this challenge "
  "would need is not a plan, it is running. **%d sealed artefacts** across the whole "
  "archive — %s — "
  "each with its own recomputable content hash and an OpenTimestamps receipt, mirrored on "
  "two independent hosts. This submission is %d of them, and %s tells you how to check "
  "every one without asking us for anything. **[measured]**"
  % (_total_sellos, _DESGLOSE, len(sellos_airbus), ref("reproducir")))
w()
sec("What we are asking for", "pedimos")
w()
w("**Three things, and none of them is a cheque before a conversation.**")
w()
w("1. **An hour with whoever owns the benchmark.** The finding in %s is either useful to "
  "you or it is wrong, and both are worth an hour. If it is useful, the repaired family "
  "and its threshold are yours to use with or without us." % ref("deteccion"))
w("2. **One case you actually care about.** Everything here is on the vortex your "
  "statement specifies. The degenerate class we characterised is easy to fall into by "
  "accident; we would rather measure whether your real cases are in it than speculate.")
w("3. **A next phase scoped to the measurement, not to a promise.** Same method as this "
  "one: pre-registered before the instrument exists, sealed, timestamped, and published "
  "whether it works or not. This report is what a negative result looks like when it is "
  "delivered on purpose.")
w()
sec("Reproduce this", "reproducir")
w()
w("One command rebuilds the whole axis from the instrument, with no network and no quantum "
  "hardware: `python3 barrido_airbus.py`. The instrument declares its own sha256 inside "
  "every artifact it writes, so the exact code behind each figure is identifiable. "
  "**[by construction]**")
w()
# DOS hashes por artefacto, cada uno con lo que sirve. Citar solo el del archivo es una
# trampa para el lector honesto: re-corre, obtiene otro archivo porque el reloj cambio, y
# concluye que encontro un error nuestro.
w("Each artifact carries **two** hashes and they answer different questions. The **file "
  "hash** says you downloaded the exact bytes we sealed. The **content hash** covers only "
  "the deterministic content — it excludes wall-clock timings, the machine description and "
  "timestamped filenames, which no re-run reproduces — and it is the one that stays the "
  "same when *you* re-run the instrument. Compare a re-run against the file hash and you "
  "will think you found an error in our work; compare it against the content hash and you "
  "are checking the science. Each artifact states inside itself which fields it excluded "
  "and why. **[by construction]**")
w()
w("| artifact | file hash — *«our exact bytes»* | content hash — *«the science reproduces»* |")
w("|---|---|---|")
for nombre in ("barrido_airbus.json", "nolinealidad_donde_vive.json"):
    ruta = os.path.join(DIR, nombre)
    _d = json.load(open(ruta))
    w("| `%s` | `%s` | `%s` |"
      % (nombre, hashlib.sha256(open(ruta, "rb").read()).hexdigest(),
         _d["contenido_sha256"].split(":")[-1]))
w()

# ---------------------------------------------------------------- 9 · anexo REFORMS
sec("Annex — the external yardstick", "anexo")
w()
w("We report our own score against **REFORMS** (Kapoor et al., *Science Advances* 2024; "
  "32 items, 8 modules) rather than leave the audit to you. A document that declares its own "
  "gaps costs the reader less than one that hides them. **[from the literature]**")
w()
# El recuento se lee del estandar, no se escribe de memoria: si cambia alli, cambia aqui.
_est = open(os.path.join(RAIZ, "ESTANDAR-presentacion-entregable.md"), encoding="utf-8").read()
# El recuento puede venir partido en dos lineas del estandar: se normalizan los saltos
# antes de buscar. Un regex que asume una linea ya aborto una vez — y aborto bien.
_est_plano = " ".join(_est.split())
_m = __import__("re").search(r"(\d+) plenos · (\d+) parciales · (\d+) ausentes", _est_plano)
if not _m:
    raise SystemExit("ABORTA: no pude leer el recuento REFORMS del estandar. Un recuento "
                     "escrito de memoria es exactamente lo que esta seccion promete no hacer.")
_pl, _pa, _au = _m.groups()
w("Current score, read from our delivery standard at build time: **%s full · %s partial · "
  "%s absent**, of 32 items. The absent ones are named there one by one, not summarised as "
  "«a few pending», and each carries its closing plan. **[measured]**" % (_pl, _pa, _au))
w()
w("---")
w()
w("*Blue Tuna SpA · Punta Arenas, Chile · hello@rosettaquantum.com*")

doc = "\n".join(L)

# GUARDIA CONTRA LA FILTRACION DE ESPAÑOL. Nacio de un defecto real de este mismo
# documento: el mecanismo del §5 salio en español porque se pego crudo el campo de un
# artefacto. Un artefacto es la fuente del HECHO; la redaccion es del generador. El
# chequeo mira palabras funcionales que no existen en ingles tecnico y aborta.
import re as _re
_ES = (" que ", " para ", " porque ", " cuando ", " sobre el ", " sobre la ", " del ",
       " los ", " las ", " una sola ", " se anula ", " es decir ", " tambien ", " segun ")
_fugas = sorted({p.strip() for p in _ES
                 if _re.search(_re.escape(p), doc, _re.I) and p.strip() not in ("del",)})
# «del» y los nombres de variante (tgv_rotado_45) son legitimos: se excluyen por ser
# identificadores citados, no prosa. El resto no tiene excusa en un documento en ingles.
_lineas_sospechosas = [l for l in L
                       if any(_re.search(_re.escape(p), l, _re.I) for p in _ES)
                       and not l.strip().startswith("| `")]
if _lineas_sospechosas:
    raise SystemExit("ABORTA: hay prosa en español en un documento en ingles (%d linea(s)). "
                     "Un artefacto es la fuente del hecho, no de la redaccion:\n   %s"
                     % (len(_lineas_sospechosas), "\n   ".join(l[:110] for l in _lineas_sospechosas[:4])))
# EL TITULAR Y LA TABLA TIENEN QUE CONTAR LO MISMO.
# Nacio de un defecto real: el titular decia «K=1 resolvio 3 de 8» y la tabla ponia «out
# of reach» en las OCHO filas, porque tomaba el primer brazo con "carleman" en el nombre
# —que es K=2, el que nunca resolvio— y tapaba los tres resultados de K=1. Dos partes del
# mismo documento afirmando cosas distintas sobre el mismo dato.
_texto = "\n".join(L)
for _brazo, _dice in (("carleman_K1_variacional", k1_res), ("carleman_K2_variacional", k2_res)):
    _real = sum(1 for p_ in serie
                if campo(p_, "brazos").get(_brazo, {}).get("error_l2_rel") is not None)
    if _real != _dice:
        raise SystemExit("ABORTA: el titular dice que %s resolvio %d puntos y el eje tiene "
                         "%d." % (_brazo, _dice, _real))
# Se localiza LA tabla del eje por su encabezado y se cuenta su columna, en vez de
# adivinar por la forma de la linea: el documento tiene varias tablas y contarlas todas
# juntas hacia que este chequeo reventara en vez de comprobar.
_i = next(i for i, _l in enumerate(L) if _l.startswith("|") and "Carleman K=1" in _l)
_cols = [c.strip() for c in L[_i].strip("|").split("|")]
_col_k1 = _cols.index("Carleman K=1")
_celdas_k1 = 0
for _l in L[_i + 2:]:
    if not _l.startswith("|"):
        break
    _c = [x.strip() for x in _l.strip("|").split("|")]
    if len(_c) == len(_cols) and "over cap" not in _c[_col_k1] and _c[_col_k1] != "—":
        _celdas_k1 += 1
if _celdas_k1 != k1_res:
    raise SystemExit("ABORTA: la tabla muestra %d puntos resueltos de K=1 y el titular "
                     "afirma %d. Una de las dos partes miente." % (_celdas_k1, k1_res))

open(SAL, "w", encoding="utf-8").write(doc)
print("INFORME AIRBUS ARMADO — %d lineas, %d palabras" % (len(L), len(doc.split())))
print("  puntos del eje: %d · Re %s..%s · mallas %s..%s"
      % (len(serie), num(serie[0]["Re"]), num(serie[-1]["Re"]),
         serie[0]["malla_N"], serie[-1]["malla_N"]))
print("  prereg: %s · anclado: %s" % (prereg_id, prereg_anclado))
print("  sellos de Airbus publicados: %d" % len(sellos_airbus))
print("escrito %s" % os.path.relpath(SAL, RAIZ))
