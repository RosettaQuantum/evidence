#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La plantilla de experimento: lo que NO se vuelve a escribir a mano.

POR QUE EXISTE, con nombres y fechas
------------------------------------
Tres desafios, tres archivos, cero lineas compartidas: `eon_harness.py`,
`eon_estocastico.py` y `vrp_harness.py` reimplementaron cada uno las mismas reglas de
la casa. Los cinco defectos de la semana del 2026-08-13 al 18 son todos de
reimplementacion, no de fisica ni de algoritmos:

  1. QUBO->Ising con el campo lineal a la mitad  -> el retador competia sobre otro problema.
  2. El censo de red estampado como literal      -> nueve sellos diciendo una red y midiendo otra.
  3. Una variable de entorno vacia leida a int   -> cuatro corridas muertas en 45 s.
  4. El truncamiento del optimizador sin declarar-> dos conclusiones retiradas.
  5. Un guardia de memoria mirando la cifra mala -> la maquina se cayo y hubo que reiniciarla.

Cada uno se arreglo UNA vez, en UN archivo. Los otros dos siguen sin el arreglo. Esta
plantilla existe para que el arreglo viva en un solo lugar y el sexto defecto de la
familia no tenga donde nacer.

QUE DECLARA EL AUTOR DE UN EXPERIMENTO NUEVO, Y NADA MAS
--------------------------------------------------------
  - El problema y sus parametros.
  - EL RIVAL: el mejor metodo que el cliente usa hoy. La plantilla se niega a correr sin
    uno, y exige por escrito POR QUE ese es el rival — el campo existe para que una
    version debil no pueda entrar callada.
  - EL ARBITRO: quien prueba el optimo, y que pasa cuando no hay.
  - EL CRITERIO, escrito antes de ver un numero. La plantilla le toma la huella al
    declararlo y la vuelve a mirar antes de escribir el veredicto.
  - COMO SE EVALUA UNA SOLUCION: UNA funcion, la misma para todos los brazos.

QUE PONE LA PLANTILLA, PORQUE ES DONDE NACIERON LOS DEFECTOS
------------------------------------------------------------
  G1  `env()`            — la cadena vacia es ausencia, y un valor ilegible aborta con nombre.
  G2  denominador        — intentados / con valor / sin valor por motivo, y la suma tiene que cerrar.
  G3  truncamiento       — pasos dados, presupuesto, `truncado_por_reloj`; falla cerrado si el brazo no lo reporta.
  G4  guardia de memoria — `vm_stat` + presion (NO el `unused` de `top`), falla cerrado.
  G5  censo              — medido, nunca estampado; aborta si no calza con lo declarado y si nunca corrio.
  G6a puntaje comun      — todos los brazos se puntuan con LA MISMA funcion, o el desvio se declara.
  G6b reformulacion      — una reescritura del objetivo (QUBO->Ising) reproduce el original, o aborta.
  G7  criterio sellado   — el criterio no cambia entre que se declara y que se lee el numero.
  G8  artefacto          — forma unica, con semillas y versiones, listo para sellar.

QUE **NO** CUBRE ESTA PLANTILLA (leer entero; un control sin sus limites se lee como si cubriera todo)
------------------------------------------------------------------------------------------------------
  - **No mira la fisica ni el modelo.** El defecto del modelo de transporte sin KVL de
    `eon_estocastico.py` —un numero correcto respondiendo otra pregunta— pasa por aqui
    intacto. G6a compara el puntaje de los brazos entre si; no sabe si la funcion que
    todos usan es la correcta.
  - **No verifica que el rival este bien configurado.** Exige que se nombre y se
    justifique por escrito. Un OR-Tools con un presupuesto de un segundo pasa igual.
  - **No mide corrección de un solver.** Si CP-SAT miente, la plantilla lo cree.
  - **No hace reproducible lo que no lo es.** Un brazo que itera contra el reloj da
    distinto en una maquina cargada; la plantilla lo DECLARA (G3), no lo arregla.
  - **No sella ni publica.** Produce el artefacto; el notario es otro y sigue separado
    a proposito (CLAUDE.md Rosetta §11).
  - **No vigila el codigo fuente.** Ningun guardia de aqui lee texto: todos miran valores
    y estructuras. Por eso las pruebas incluyen el caso paradojico —un experimento cuyo
    COMENTARIO describe el defecto y cuyo codigo no lo tiene— y ahi tienen que callarse.
  - **G4 solo sabe de macOS y Linux.** En otro sistema no adivina: falla cerrado.
  - **G6a no ve un sustituto.** Un brazo que optimiza un subrogado (el QAOA del VRP
    decide el reparto, no el orden) lo declara en `alcance`; la plantilla no puede saber
    si el subrogado es razonable.
"""
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, Sequence

VERSION_PLANTILLA = "experimento/v1"


# ============================================================ G1 — LECTURA DE ENTORNO
def env(nombre, defecto, tipo=str):
    """Lee una variable de entorno tratando la CADENA VACIA como ausente.

    DEFECTO REAL (eon_harness.py, 2026-08-13T19:37): GitHub Actions pasa "" —no la
    ausencia— cuando un input opcional se deja en blanco, y `os.environ.get(x, 120)`
    devuelve "" en ese caso, no 120. Cuatro corridas murieron en 45 segundos con
    `invalid literal for int() with base 10: ''`.

    Y la otra mitad, que en el original no estaba: un valor ILEGIBLE ("abc") tampoco
    puede reventar con el mensaje de la libreria. Aborta diciendo que variable era.
    """
    v = os.environ.get(nombre, "")
    if not str(v).strip():
        return defecto
    try:
        return tipo(v)
    except (TypeError, ValueError) as e:
        raise SystemExit(
            "ABORTA: %s=%r no se puede leer como %s (%s).\n"
            "  Una variable ilegible no se reemplaza por su defecto en silencio: eso\n"
            "  convierte un error de invocacion en una corrida que mide otra cosa."
            % (nombre, v, getattr(tipo, "__name__", tipo), e))


# ============================================================ G4 — GUARDIA DE MEMORIA
def memoria_disponible_gb():
    """GB realmente disponibles. None si no se puede saber — y None significa NO CORRER.

    DEFECTO REAL (banco_de_ensayo.py, primera version, cazado el 2026-08-17): leia
    `PhysMem: ... N unused` de `top`. En macOS ese numero es casi cero SIEMPRE, porque
    el sistema usa la RAM libre como cache de disco. Medido en este Mac el 2026-08-18:
    `top` decia 757 MB unused mientras `vm_stat` daba 10,4 GB recuperables.

    Un guardia que grita sin razon no protege: lo desactiva el primero que lo choque.
    Lo correcto en macOS es free + inactive + speculative, que el kernel recupera de
    inmediato, y mirar la presion aparte.
    """
    so = platform.system()
    if so == "Darwin":
        try:
            out = subprocess.run(["vm_stat"], capture_output=True, text=True,
                                 timeout=10).stdout
        except Exception:
            return None
        m = re.search(r"page size of (\d+) bytes", out)
        if not m:
            return None
        pag = int(m.group(1))

        def paginas(nombre):
            mm = re.search(r"Pages %s:\s+(\d+)" % nombre, out)
            return int(mm.group(1)) if mm else 0
        libres = paginas("free") + paginas("inactive") + paginas("speculative")
        if libres == 0:
            return None                     # no se pudo leer nada util -> falla cerrado
        return libres * pag / (1024 ** 3)
    if so == "Linux":
        try:
            txt = open("/proc/meminfo").read()
        except Exception:
            return None
        m = re.search(r"MemAvailable:\s+(\d+) kB", txt)
        return int(m.group(1)) / (1024 ** 2) if m else None
    return None                              # sistema desconocido -> falla cerrado


def presion_de_memoria_pct():
    """Cuanta presion declara el propio sistema. None si no se puede leer."""
    if platform.system() != "Darwin":
        return None
    try:
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True,
                             timeout=10).stdout
    except Exception:
        return None
    m = re.search(r"System-wide memory free percentage:\s*(\d+)%", out)
    return (100 - int(m.group(1))) if m else None


def guardia_de_memoria(min_libre_gb, presion_maxima_pct=85,
                       _libre=memoria_disponible_gb, _presion=presion_de_memoria_pct):
    """Se niega a correr si la maquina no tiene aire. FALLA CERRADO.

    CASO REAL (2026-08-14): se corrio el banco con 984 MB libres, habiendolo medido un
    minuto antes. El pico de K=18 fue 4,34 GB y hubo que reiniciar el Mac con todo
    abierto. El dato que lo habria evitado estaba en pantalla y no se uso: por eso el
    chequeo vive en codigo y no en la cabeza del que lanza (CLAUDE.md Rosetta §4).

    Las DOS condiciones, y ninguna sola basta: memoria disponible Y presion no critica.
    """
    libre = _libre()
    presion = _presion()
    if libre is None:
        raise SystemExit(
            "ABORTA: no pude leer la memoria disponible en %s. Sin ese dato no se corre:\n"
            "  un experimento asi puede pedir varios GB y tumbar la maquina, y ya lo hizo\n"
            "  una vez." % platform.system())
    if presion is not None and presion >= presion_maxima_pct:
        raise SystemExit(
            "ABORTA: el sistema declara %d%% de presion de memoria (tope %d%%). Hay %.1f GB\n"
            "  recuperables, pero el kernel ya esta apretando: correr ahora es como corrio\n"
            "  la vez que hubo que reiniciar." % (presion, presion_maxima_pct, libre))
    if libre < min_libre_gb:
        raise SystemExit(
            "ABORTA: %.1f GB disponibles y el minimo declarado es %.1f.\n"
            "  Cierra aplicaciones y vuelve a intentar." % (libre, min_libre_gb))
    return {"gb_disponibles": round(libre, 2), "presion_pct": presion,
            "minimo_exigido_gb": min_libre_gb, "presion_maxima_pct": presion_maxima_pct,
            "metodo": ("vm_stat: free+inactive+speculative, mas memory_pressure"
                       if platform.system() == "Darwin" else "/proc/meminfo MemAvailable")}


# ============================================================ G5 — CENSO DE LA INSTANCIA
class Censo:
    """Lo que la instancia ES, MEDIDO. Nunca un literal estampado.

    DEFECTO REAL (eon_harness.py, hasta el 2026-08-13): el archivo cargaba la red desde
    RQ_GRID y despues estampaba `instance="case14_..."` y `params.grid="IEEE case14"`.
    Corriendo case118 el sello decia case14 y ningun campo registraba el tamano real.
    Nueve sellos salieron asi. El arreglo no es cambiar literales por variables —eso ya
    seria correcto y seguiria siendo indemostrable— sino MEDIR y comprobar que calza.

    Y la trampa de la primera version de aquel guardia, que aqui no se puede repetir: su
    tabla de referencia estaba escrita de memoria (decia que case14 tenia 20 lineas y
    tiene 15). Aqui la referencia la pasa el experimento y se compara CAMPO POR CAMPO;
    un campo declarado que no se midio aborta, en vez de aprobarse por omision.
    """

    def __init__(self):
        self._medido = None
        self._declarado = None

    def medir(self, declarado, medido):
        declarado = dict(declarado or {})
        medido = dict(medido or {})
        if not medido:
            raise SystemExit("ABORTA: el censo no midio nada. Un censo vacio aprueba todo.")
        sin_medir = sorted(set(declarado) - set(medido))
        if sin_medir:
            raise SystemExit(
                "ABORTA: se declaro %s y el censo no lo midio. Un campo declarado que\n"
                "  nadie mide se aprueba por omision, que es exactamente como salieron los\n"
                "  nueve sellos de case14." % ", ".join(sin_medir))
        malos = {k: (declarado[k], medido[k]) for k in declarado if declarado[k] != medido[k]}
        if malos:
            det = "; ".join("%s: se declaro %r y se midio %r" % (k, d, m)
                            for k, (d, m) in sorted(malos.items()))
            raise SystemExit(
                "ABORTA: el censo no calza con lo declarado (%s).\n"
                "  El sello habria dicho una instancia y medido otra, que es exactamente\n"
                "  el defecto que este guardia existe para impedir." % det)
        self._declarado, self._medido = declarado, medido
        return medido

    def exigir(self):
        if self._medido is None:
            raise SystemExit(
                "ABORTA: el censo nunca corrio, asi que el artefacto no puede declarar que\n"
                "  instancia se midio. Un campo ausente es mejor que uno inventado, pero un\n"
                "  artefacto a medias no se publica.")
        return dict(self._medido)


# ============================================================ G3 — TRUNCAMIENTO
def truncamiento(pasos_dados, pasos_de_presupuesto=None, reloj_s=None,
                 criterio_de_parada=None):
    """El bloque que declara si el optimizador AGOTO su presupuesto o lo corto el reloj.

    DEFECTO REAL (eon_harness.py, 2026-08-13): con K=20 el optimizador alcanzo a dar 6
    pasos de 120 antes de que el reloj lo cortara, y con K=16 dio 83. Sus brechas
    (4,41 % y 2,44 %) se publicaron como si midieran al ALGORITMO, y median NUESTRO
    presupuesto. Dos conclusiones se retiraron.

    `pasos_de_presupuesto=None` es legitimo y significa "no hay presupuesto de pasos: el
    unico limite es el reloj" — el caso del QAOA de `vrp_harness.py`, cuyo bucle es
    `while time.time()-t0 < segundos*0.8`. En ese caso hay que decir
    `criterio_de_parada="reloj"`, para que la ausencia sea una declaracion y no un olvido.
    """
    if pasos_de_presupuesto is None:
        crit = criterio_de_parada or "reloj"
        trunc = True
    else:
        crit = criterio_de_parada or "pasos o reloj, lo que llegue antes"
        trunc = bool(pasos_dados < pasos_de_presupuesto)
    return {
        "pasos_dados": int(pasos_dados),
        "pasos_de_presupuesto": (None if pasos_de_presupuesto is None
                                 else int(pasos_de_presupuesto)),
        "reloj_s": reloj_s,
        "criterio_de_parada": crit,
        "truncado_por_reloj": trunc,
        "advertencia": (None if not trunc else
                        "el optimizador se detuvo por reloj (%s pasos de %s). Una brecha "
                        "medida asi mide el presupuesto, no el metodo."
                        % (pasos_dados, pasos_de_presupuesto if pasos_de_presupuesto
                           is not None else "sin tope de pasos")),
    }


_CLAVES_TRUNC = ("pasos_dados", "pasos_de_presupuesto", "reloj_s",
                 "criterio_de_parada", "truncado_por_reloj")


def exigir_truncamiento(nombre_brazo, res):
    """FALLA CERRADO: un brazo que itera y no declara su truncamiento no se publica.

    LA UNICA EXCEPCION, y su precio: un brazo `fuera_de_alcance` no corrio su optimizador,
    asi que no hay truncamiento que declarar. Para que la excepcion no sea una puerta
    —CLAUDE.md Rosetta §5 quater.4: «un chequeo con una excepcion hecha para su propio
    defecto»— se exige ademas que ese brazo NO traiga valor. Un brazo que se declara fuera
    de alcance y devuelve un numero es una contradiccion, y grita.
    """
    if res.get("motivo_sin_valor") == "fuera_de_alcance":
        if res.get("value") is not None:
            raise SystemExit(
                "ABORTA: el brazo %r se declara `fuera_de_alcance` y devolvio un valor.\n"
                "  Si corrio, tiene que declarar su truncamiento como todos; si no corrio,\n"
                "  no puede tener valor." % nombre_brazo)
        return None
    t = res.get("truncamiento")
    if t is None:
        raise SystemExit(
            "ABORTA: el brazo %r declara que itera y no reporto `truncamiento`.\n"
            "  Sin ese bloque, una brecha grande por falta de tiempo se lee como una brecha\n"
            "  grande del metodo — que es lo que paso con K=16 y K=20 el 2026-08-13.\n"
            "  Usa experimento.truncamiento(...) y devuelvelo en el resultado del brazo."
            % nombre_brazo)
    if not isinstance(t, dict):
        raise SystemExit("ABORTA: el `truncamiento` de %r no es un bloque." % nombre_brazo)
    faltan = [k for k in _CLAVES_TRUNC if k not in t]
    if faltan:
        raise SystemExit(
            "ABORTA: al `truncamiento` de %r le faltan %s. Un bloque a medias declara\n"
            "  menos de lo que aparenta." % (nombre_brazo, ", ".join(faltan)))
    if t["pasos_de_presupuesto"] is None and t["criterio_de_parada"] != "reloj":
        raise SystemExit(
            "ABORTA: el brazo %r no declara presupuesto de pasos y su criterio de parada\n"
            "  es %r. Sin tope de pasos el unico criterio posible es el reloj; si es otro,\n"
            "  falta declararlo." % (nombre_brazo, t["criterio_de_parada"]))
    return t


# ================================================= G6b — REFORMULACION DEL OBJETIVO
def guardia_de_reformulacion(f_original, f_reformulada, n_vars, muestras=24,
                             semilla=0, tol=1e-6, nombre="reformulacion"):
    """Comprueba que una reescritura del objetivo reproduce el objetivo original.

    DEFECTO REAL (eon_harness.py, corregido el 2026-08-18): la conversion QUBO->Ising
    hacia `h[i] -= Qs[i][j]/4` pero NO `h[j] -=`. El acoplamiento J salia bien —cada par
    se recorre dos veces— y el campo lineal `h` quedaba EN LA MITAD. Consecuencia: el
    brazo cuantico optimizaba una funcion DISTINTA de la que resolvian CP-SAT y la fuerza
    bruta, y su brecha se inflaba por una razon que no es del metodo. Desvio medido:
    24,381 en K=8 y 165,857 en K=20.

    Es barato —unas pocas asignaciones al azar— y habria gritado el primer dia.
    """
    import numpy as np
    rs = np.random.RandomState(semilla)
    peor, peor_x = 0.0, None
    for _ in range(muestras):
        x = rs.randint(0, 2, n_vars).astype(float)
        d = abs(float(f_reformulada(x)) - float(f_original(x)))
        if d > peor:
            peor, peor_x = d, [int(b) for b in x]
    if peor > tol:
        raise SystemExit(
            "ABORTA: %s no reproduce el objetivo original (desvio %.6g > %.1g sobre %d\n"
            "  asignaciones; peor caso x=%s).\n"
            "  El brazo que la usa estaria optimizando una funcion DISTINTA de la de los\n"
            "  demas, y su brecha se inflaria por una razon que no es del metodo.\n"
            "  Exactamente el defecto del 2026-08-18." % (nombre, peor, tol, muestras, peor_x))
    return {"nombre": nombre, "muestras": muestras, "n_vars": n_vars,
            "desvio_maximo": float(peor), "tolerancia": tol}


# =================================================== G6a — PUNTAJE COMUN A TODOS LOS BRAZOS
def guardia_de_puntaje_comun(resultados, evaluar, tol_rel=1e-9, decimales_reportados=None):
    """Todos los brazos se puntuan con LA MISMA funcion, o el desvio se DECLARA.

    Es la version general del guardia que le faltaba a E.ON: alli el retador optimizaba
    otra funcion; aqui se exige ademas que todos se MIDAN con la misma. Un brazo puede
    reportar un valor calculado por su propio solucionador (`puntaje_propio`), pero
    entonces tiene que declararlo con su tolerancia — y el desvio medido entra al
    artefacto en vez de esconderse dentro de una brecha.

    HALLAZGO REAL de la primera corrida de este guardia (2026-08-18, sobre el artefacto
    de `vrp_harness.py`): el arbitro reportaba `ObjectiveValue()/1000` —el objetivo
    ENTERO escalado de CP-SAT— y el rival reportaba `costo(rutas, D)` sobre la matriz de
    flotantes. Con las MISMAS rutas (278,9027071...) el artefacto decia optimo 278,9 y
    rival 278,9027, y de ahi salia una `brecha_clasico_pct` de 0,001 % que no es una
    brecha: es el redondeo del entero. `barrido_vrp.py` cita ese 0,001 % como hallazgo.
    """
    # El artefacto redondea los valores que publica; sin esta holgura el guardia gritaria
    # por el redondeo del propio artefacto, que es un falso positivo — y un falso positivo
    # lo desactiva el primero que lo choque (CLAUDE.md Rosetta §2: precision sobre cobertura).
    holgura_redondeo = (0.0 if decimales_reportados is None
                        else 0.5 * 10 ** (-int(decimales_reportados)))
    filas, peor = [], 0.0
    for nombre, res in resultados.items():
        sol = res.get("solucion")
        val = res.get("value")
        if sol is None or val is None:
            filas.append({"brazo": nombre, "estado": "sin solucion que puntuar"})
            continue
        recomputado = float(evaluar(sol))
        base = abs(recomputado) if abs(recomputado) > 1e-12 else 1.0
        desvio = abs(recomputado - float(val)) / base
        propio = res.get("puntaje_propio")
        tol = tol_rel if propio is None else float(propio.get("tolerancia_rel", tol_rel))
        tol_efectiva = max(tol, holgura_redondeo / base)
        fila = {"brazo": nombre, "valor_reportado": float(val),
                "valor_con_la_funcion_comun": recomputado,
                "desvio_relativo": desvio, "tolerancia": tol,
                "tolerancia_efectiva": tol_efectiva,
                "puntaje_propio": (None if propio is None else propio.get("que_es"))}
        filas.append(fila)
        peor = max(peor, desvio if propio is None else 0.0)
        if desvio > tol_efectiva:
            raise SystemExit(
                "ABORTA: el brazo %r reporta %.10g y la funcion de evaluacion del\n"
                "  experimento da %.10g para SU PROPIA solucion (desvio relativo %.3g >\n"
                "  %.3g).\n"
                "  Dos brazos puntuados con funciones distintas producen una brecha que no\n"
                "  es una brecha. Si la diferencia es legitima —un objetivo escalado a\n"
                "  enteros, por ejemplo— hay que DECLARARLA con `puntaje_propio`, no\n"
                "  dejarla viajando dentro del porcentaje."
                % (nombre, float(val), recomputado, desvio, tol_efectiva))
    return {"filas": filas, "peor_desvio_no_declarado": peor,
            "tolerancia_por_defecto": tol_rel,
            "decimales_reportados": decimales_reportados,
            "que_no_cubre": ("compara los brazos entre si; no sabe si la funcion comun es "
                             "la correcta para el problema del cliente")}


# ============================================================ G7 — EL CRITERIO, SELLADO
@dataclass(frozen=True)
class Criterio:
    """El criterio, escrito ANTES de ver un numero, y su huella para probar que no cambio.

    `porque_este_rival` no es decorativo: la plantilla se niega a correr sin el. Es el
    unico lugar donde queda por escrito que el rival es lo mejor que el cliente usa hoy
    y no una version debil elegida para ganarle.
    """
    texto: str                  # que tiene que pasar para llamarlo una victoria
    rival: str                  # el mejor metodo que el cliente usa HOY
    porque_este_rival: str      # por que ese y no otro
    arbitro: str                # quien prueba el optimo
    sin_arbitro: str            # que pasa cuando NO hay optimo probado

    def __post_init__(self):
        for campo in ("texto", "rival", "porque_este_rival", "arbitro", "sin_arbitro"):
            if not str(getattr(self, campo) or "").strip():
                raise SystemExit(
                    "ABORTA: el criterio no declara %r. Un experimento sin rival nombrado y\n"
                    "  justificado, sin arbitro, o sin decir que pasa cuando no hay optimo,\n"
                    "  no se puede leer despues." % campo)

    def huella(self):
        canon = json.dumps(asdict(self), sort_keys=True, ensure_ascii=True,
                           separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canon.encode("ascii", "backslashreplace")).hexdigest()


# ============================================================ LOS BRAZOS
@dataclass
class Brazo:
    """Un competidor. `rol` decide como lo lee la plantilla.

    itera=True  -> el brazo tiene un optimizador iterativo y DEBE devolver `truncamiento`.
    """
    nombre: str
    rol: str                    # "arbitro" | "rival" | "retador"
    correr: Callable
    itera: bool = False

    def __post_init__(self):
        if self.rol not in ("arbitro", "rival", "retador"):
            raise SystemExit("ABORTA: rol %r desconocido en el brazo %r "
                             "(arbitro | rival | retador)." % (self.rol, self.nombre))


# ============================================================ G2 — EL DENOMINADOR
_MOTIVOS = ("fuera_de_alcance", "cortado_por_reloj", "cortado_por_memoria",
            "sin_solucion_valida")


def denominador_de(resultados):
    """Cuantos se intentaron, cuantos dieron valor, y los que no, POR QUE no.

    CLAUDE.md Rosetta §5 bis: todo proceso que recorre un conjunto reporta su
    denominador. Un total sin denominador no es un resultado. Y la suma tiene que
    cerrar: si no cierra, hay un brazo que no esta en ninguna categoria y el resumen
    estaria contando de menos sin decirlo.
    """
    con_valor, sin_valor = 0, {m: 0 for m in _MOTIVOS}
    truncados = 0
    for nombre, res in resultados.items():
        t = res.get("truncamiento") or {}
        if t.get("truncado_por_reloj"):
            truncados += 1
        if res.get("value") is not None:
            con_valor += 1
            continue
        motivo = res.get("motivo_sin_valor")
        if motivo not in _MOTIVOS:
            raise SystemExit(
                "ABORTA: el brazo %r no produjo valor y su motivo es %r, que no es uno de\n"
                "  %s. Un brazo sin valor y sin motivo no entra a ninguna categoria y el\n"
                "  denominador cerraria de mas." % (nombre, motivo, list(_MOTIVOS)))
        sin_valor[motivo] += 1
    total = len(resultados)
    suma = con_valor + sum(sin_valor.values())
    if suma != total:
        raise SystemExit("ABORTA: el denominador no cierra: %d intentados, %d clasificados."
                         % (total, suma))
    return {"brazos_intentados": total, "brazos_con_valor": con_valor,
            "brazos_sin_valor": sin_valor,
            "brazos_truncados_por_reloj": truncados}


# ============================================================ G8 — EL EXPERIMENTO
class Experimento:
    """La corrida entera: declara arriba, y la plantilla pone los guardias y el artefacto."""

    def __init__(self, track, instancia, params, criterio, evaluar, brazos,
                 semillas, versiones, censo=None, memoria_minima_gb=None,
                 despues_de_cada_brazo=None, tol_puntaje_rel=1e-9,
                 decimales_reportados=None):
        if not isinstance(criterio, Criterio):
            raise SystemExit("ABORTA: `criterio` tiene que ser un experimento.Criterio.")
        self.track, self.instancia, self.params = track, instancia, dict(params)
        self.criterio = criterio
        self._huella_criterio = criterio.huella()      # G7: se toma al declarar
        self.evaluar = evaluar
        self.brazos = list(brazos)
        self.semillas = dict(semillas)
        self.versiones = dict(versiones)
        self.censo = censo if censo is not None else Censo()
        self.memoria_minima_gb = memoria_minima_gb
        self.despues_de_cada_brazo = despues_de_cada_brazo
        self.tol_puntaje_rel = tol_puntaje_rel
        self.decimales_reportados = decimales_reportados
        if not self.semillas:
            raise SystemExit("ABORTA: el experimento no declara semillas. Sin semilla el\n"
                             "  artefacto no se puede reconstruir.")
        roles = [b.rol for b in self.brazos]
        if roles.count("rival") != 1:
            raise SystemExit(
                "ABORTA: hay %d brazos con rol 'rival' y tiene que haber exactamente uno.\n"
                "  El rival es el mejor metodo que el cliente usa hoy; sin uno nombrado no\n"
                "  hay contra que medir, y un experimento sin rival se lee como una victoria."
                % roles.count("rival"))
        if roles.count("arbitro") > 1:
            raise SystemExit("ABORTA: mas de un arbitro. Solo uno prueba el optimo.")
        if "retador" not in roles:
            raise SystemExit("ABORTA: no hay ningun brazo retador; no hay nada que medir.")
        nombres = [b.nombre for b in self.brazos]
        if len(set(nombres)) != len(nombres):
            raise SystemExit("ABORTA: dos brazos con el mismo nombre: %s" % nombres)

    # ---------------------------------------------------------------- la corrida
    def correr(self, contexto=None, veredicto=None, verboso=True):
        ctx = contexto if contexto is not None else {}
        memoria = None
        if self.memoria_minima_gb is not None:
            memoria = guardia_de_memoria(self.memoria_minima_gb)

        resultados = {}
        for b in self.brazos:
            if verboso:
                print("  corriendo %s…" % b.nombre, flush=True)
            try:
                res = b.correr(ctx)
            except MemoryError:
                res = {"value": None, "estado": "sin memoria",
                       "motivo_sin_valor": "cortado_por_memoria"}
            if not isinstance(res, dict):
                raise SystemExit("ABORTA: el brazo %r no devolvio un bloque." % b.nombre)
            if "value" not in res:
                raise SystemExit(
                    "ABORTA: el brazo %r no devolvio `value`. Un brazo sin valor declarado\n"
                    "  —aunque sea None— no se puede contar ni comparar." % b.nombre)
            if b.itera:
                exigir_truncamiento(b.nombre, res)
            res["rol"] = b.rol
            resultados[b.nombre] = res
            if self.despues_de_cada_brazo is not None:
                self.despues_de_cada_brazo(b.nombre, res, ctx)

        # los guardias que no tocan el azar corren DESPUES, para no alterar el orden
        puntaje = guardia_de_puntaje_comun(resultados, self.evaluar, self.tol_puntaje_rel,
                                           self.decimales_reportados)
        denominador = denominador_de(resultados)
        censo = self.censo.exigir()

        # G7: el criterio no puede haber cambiado entre que se declaro y ahora
        if self.criterio.huella() != self._huella_criterio:
            raise SystemExit(
                "ABORTA: el criterio cambio entre que se declaro y que se leyeron los\n"
                "  numeros. Un criterio que se ablanda despues de ver el resultado no es\n"
                "  un criterio.")

        ver = veredicto(resultados, ctx) if veredicto is not None else {}
        ver = dict(ver)
        ver.setdefault("criterio", self.criterio.texto)
        ver.setdefault("rival", self.criterio.rival)
        ver.setdefault("arbitro", self.criterio.arbitro)

        artefacto = {"track": self.track, "instance": self.instancia,
                     "params": self.params}
        for nombre, res in resultados.items():
            limpio = {k: v for k, v in res.items()
                      if k not in ("solucion", "rol", "motivo_sin_valor")}
            artefacto[nombre] = limpio
        artefacto["verdict"] = ver
        artefacto["lib_versions"] = dict(self.versiones)
        artefacto["plantilla"] = {
            "version": VERSION_PLANTILLA,
            "criterio": asdict(self.criterio),
            "criterio_huella": self._huella_criterio,
            "roles": {b.nombre: b.rol for b in self.brazos},
            "censo_medido": censo,
            "denominador": denominador,
            "puntaje_comun": puntaje,
            "memoria": memoria,
            "semillas": self.semillas,
            "corrida_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return artefacto

    @staticmethod
    def escribir(artefacto, ruta, indent=1):
        """El artefacto sale por ARCHIVO, nunca copiado a mano (CLAUDE.md Rosetta §10)."""
        with open(ruta, "w") as f:
            json.dump(artefacto, f, indent=indent)
        return ruta


def versiones_base(**extra):
    """Las versiones que todo artefacto declara, mas las que agregue el experimento."""
    import numpy as np
    v = {"numpy": np.__version__, "python": platform.python_version()}
    v.update(extra)
    return v
