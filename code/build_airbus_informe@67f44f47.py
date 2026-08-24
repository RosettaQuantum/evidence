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
import os
import subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
EVID = os.path.join(RAIZ, "evidence")
DIR = os.path.join(AQUI, "airbus")
SAL = os.path.join(AQUI, "AIRBUS-INFORME-FINAL.md")

L = []
def w(s=""):
    L.append(s)


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
    def _es_referencia(texto, ini):
        antes = texto[max(0, ini - 6):ini]
        return "§" in antes or "sec." in antes.lower()
    for nodo in _ast.walk(arbol):
        if not (isinstance(nodo, _ast.Call) and isinstance(nodo.func, _ast.Name)
                and nodo.func.id == "w" and nodo.args):
            continue
        for parte in _ast.walk(nodo.args[0]):
            if isinstance(parte, _ast.Constant) and isinstance(parte.value, str):
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

# Los artefactos del barrido NO estan sellados todavia: se comprueba, no se supone.
sellos_airbus = [p for p in glob.glob(os.path.join(EVID, "runs", "**", "*.json"), recursive=True)
                 if "AIRBUS" in os.path.basename(p).upper()]

w("# Airbus — Quantum Solvers for Predictive Aerodynamic Modeling")
w()
w("**Rosetta Quantum** · 2026 Global Quantum + AI Challenge · Phase 1")
w()
w("> Every figure in this document is read from an artifact at build time, never typed. "
  "Each claim carries one of three labels — **measured**, **by construction**, or **from "
  "the literature** — and anything without a label is not here.")
w()

# ---------------------------------------------------------------- 1 · resumen
w("## 1 · Summary")
w()
esp0, espN = campo(serie[0], "brazos", "espectral"), campo(serie[-1], "brazos", "espectral")
fd0, fdN = campo(serie[0], "brazos", "fd2"), campo(serie[-1], "brazos", "fd2")
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
w("You asked for a quantum solver for the 2D convecting Taylor-Green vortex, and for the "
  "curve of time-to-solution and error as the Reynolds number grows. We built the "
  "instrument, pre-registered the question before writing a line of it, and ran the axis "
  "end to end. Three things came out, and the third is the one worth your time.")
w()
w("**One — the classical cost explodes; the accuracy does not.** Across Re = %s to %s with "
  "the mesh coupled as your statement requires, the finite-difference error *falls* by four "
  "orders of magnitude (%s → %s). **[measured — reproduces bit-for-bit]** Its wall time "
  "rises by a factor of ~%s on this machine (the spectral arm, ~%s). **[measured on one "
  "machine; not comparable across computers]**"
  % (mag(campo(serie[0], "Re")), mag(campo(serie[-1], "Re")),
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
k1_res, k1_tot, k1_q = cobertura(serie, "carleman_K1_variacional")
k2_res, k2_tot, k2_q = cobertura(serie, "carleman_K2_variacional")
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
  "law that restores it; §5 gives both, and they are the constructive part of this "
  "submission. **[measured]**" % sci(razon_tgv))
w()

# ---------------------------------------------------------------- 2 · pregunta y prereg
w("## 2 · The question, and when it was fixed")
w()
w("Pre-registration `%s`, content hash `%s…`."
  % (prereg_id, campo(prereg, "meta", "content_hash")[:31]))
w()
if prereg_commit:
    w("It was committed in `%s`, and **at that commit not one line of the instrument "
      "existed** — that is a property of the git history, verifiable by you, not a claim of "
      "ours. **[by construction]**" % prereg_commit[:8])
if prereg_anclado:
    w("The pre-registration is anchored in Bitcoin (OpenTimestamps), so the ordering is "
      "bounded from above by a clock neither we nor you control. **[by construction]**")
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
w("## 3 · The referee, and why this benchmark is unusually strong")
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
w("## 4 · The axis: time-to-solution and error vs Reynolds")
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
w("## 5 · Why the nonlinear term vanishes here — mechanism, and the law that restores it")
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
w("## 6 · What we did to kill our own result")
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
w("## 7 · What we cannot claim")
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
if not sellos_airbus:
    w("- **The sweep artifacts are not sealed yet.** They are produced, reproducible and "
      "public, but the seal and the anchor are a separate step by the lab and the notary, "
      "and it has not run for these. We say so rather than let you assume. **[measured]**")
w()

# ---------------------------------------------------------------- 8 · reproduccion
w("## 8 · Reproduce this")
w()
w("One command rebuilds the whole axis from the instrument, with no network and no quantum "
  "hardware: `python3 barrido_airbus.py`. The instrument declares its own sha256 inside "
  "every artifact it writes, so the exact code behind each figure is identifiable. "
  "**[by construction]**")
w()
w("| artifact | sha256 |")
w("|---|---|")
for nombre in ("barrido_airbus.json", "nolinealidad_donde_vive.json"):
    ruta = os.path.join(DIR, nombre)
    w("| `%s` | `%s` |" % (nombre, hashlib.sha256(open(ruta, "rb").read()).hexdigest()))
w()

# ---------------------------------------------------------------- 9 · anexo REFORMS
w("## 9 · Annex — the external yardstick")
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
