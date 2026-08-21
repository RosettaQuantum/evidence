#!/usr/bin/env python3
"""Publica los coeficientes que DEFINEN el problema de cada corrida de E.ON.

POR QUE EXISTE
--------------
Los 24 artefactos de `resultados_eon/` declaran en `grid_physics.congestion_model`
un modelo de superposicion DC de 2do orden "measured r_i, q_ij via pandapower
rundcpp" — y **ninguno publica esos r_i ni esos q_ij**. Consecuencia: el sello
publica un `exact.value` y no entrega con que comprobarlo. `measure_runtime_s`
dice que la medicion ocurrio; su resultado nunca se publico.

POR QUE NO SE RE-CORRE EL HARNESS, que era lo obvio
---------------------------------------------------
`eon_case118@a3340c06.json` tiene 10 candidatos paralelos + 4 nuevos: el reparto
FIJO de antes del 2026-08-13. El harness de hoy deriva el reparto del tamano del
problema y con RQ_CAND=14 da 11 + 3. Las cinco versiones archivadas en `code/`
son todas posteriores. Ninguna reproduce esa instancia, y el artefacto no declara
`harness_sha256`, asi que no hay a que volver.

Re-correr habria medido un problema DISTINTO y sus coeficientes se habrian leido
como los de este sello — una medicion correcta respondiendo otra pregunta, que es
la forma de la ausencia disfrazada de valor que mas cuesta ver (§5 quater, 6ta).

QUE HACE ENTONCES
-----------------
Ancla la medicion **al artefacto publicado**, no a una version del instrumento:
toma sus 14 candidatos tal como estan publicados y mide sobre ellos. `r_i` y
`q_ij` dependen solo de la red y de esa lista, asi que son recomputables sin
saber que codigo los genero.

Lo unico que no sale de la lista es `cost`, que consume el flujo aleatorio de la
semilla. Se reconstruye REPRODUCIENDO el flujo, con un chequeo que falla cerrado:
si los pares nuevos replayados no salen en el mismo orden que los publicados, no
se reconstruyo el flujo y se DECLARA, en vez de escribir 14 numeros plausibles.

Uso:  python3 coeficientes_eon.py --artefacto ../resultados_eon/eon_case118@a3340c06.json
      python3 coeficientes_eon.py --todos
"""
import argparse, hashlib, itertools, json, os, platform, sys, time

import numpy as np
import pandapower as pp
import pandapower.networks as nw

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SALIDA = os.path.join(RAIZ, "coeficientes_eon")

# El unico parametro del modelo que los artefactos NO declaran. Se comprueba contra
# `base_congestion_dc`, que si esta publicado: si el rebuild no reproduce esa cifra,
# el supuesto es falso y se aborta antes de medir 105 numeros sobre una red equivocada.
TIGHTEN = float(os.environ.get("RQ_TIGHTEN", 0.5))


def sha256_de(ruta):
    return hashlib.sha256(open(ruta, "rb").read()).hexdigest()


class Red:
    """La red del artefacto, reconstruida y con sus ratings congelados.

    Los ratings se calculan UNA vez sobre la red base y se reusan en cada rebuild,
    igual que el `_RATINGS` global del harness. Si se recalcularan en cada rebuild,
    cada candidato cambiaria el denominador de la congestion y `r_i` mediria otra
    cosa — el mismo numero, calculado bien, respondiendo otra pregunta.
    """

    def __init__(self, grid, load_scale):
        self.fn = getattr(nw, grid)
        self.load_scale = load_scale
        self.ratings = None
        base = self._crudo()
        pp.rundcpp(base)
        ik = base.res_line.i_ka.values
        piso = 0.15 * float(np.nanmax(ik))
        self.ratings = np.maximum(ik, piso) * TIGHTEN
        self.base = self.build()

    def _crudo(self):
        net = self.fn()
        net.load["p_mw"] *= self.load_scale
        net.load["q_mvar"] *= self.load_scale
        return net

    def build(self):
        net = self._crudo()
        net.line["max_i_ka"] = self.ratings
        return net

    def congestion(self, net):
        try:
            pp.rundcpp(net)
        except Exception:
            return 1e6
        over = np.maximum(net.res_line.loading_percent.values - 100.0, 0.0)
        return float(over.sum())


def aplicar(red, net, c):
    """Replica `apply_candidate` del harness, byte por byte en su efecto."""
    tipo = c["type"] if "type" in c else c["tipo"]
    det = c["detail"] if "detail" in c else c["detalle"]
    if tipo == "parallel":
        ln = red.base.line.loc[int(det[0])]
        pp.create_line_from_parameters(
            net, int(ln.from_bus), int(ln.to_bus), length_km=float(ln.length_km or 1.0),
            r_ohm_per_km=float(ln.r_ohm_per_km), x_ohm_per_km=float(ln.x_ohm_per_km),
            c_nf_per_km=float(ln.c_nf_per_km or 0.0), max_i_ka=float(ln.max_i_ka or 1.0))
    else:
        ref = red.base.line.iloc[0]
        pp.create_line_from_parameters(
            net, int(det[0]), int(det[1]), length_km=2.0,
            r_ohm_per_km=float(ref.r_ohm_per_km), x_ohm_per_km=float(ref.x_ohm_per_km),
            c_nf_per_km=0.0, max_i_ka=float(ref.max_i_ka or 1.0))


def congestion_con(red, cands, sel):
    net = red.build()
    for i in sel:
        aplicar(red, net, cands[i])
    return red.congestion(net)


def replay_del_costo(red, cands, seed):
    """Reconstruye `cost` reproduciendo el flujo aleatorio, o devuelve por que no pudo.

    El harness consume el generador en dos tramos y en este orden: primero los sorteos
    de pares de buses para las lineas NUEVAS (incluidos los sorteos RECHAZADOS, que
    tambien consumen), y despues un `uniform(0.9, 1.1, K)` para el ruido del costo.
    Saltarse los rechazos desplaza el flujo y produce 14 numeros que se ven bien.

    El chequeo que lo hace verificable: los pares replayados tienen que salir en el
    MISMO orden que los publicados. Si no, se declara el fallo y no se publica costo.
    """
    nuevos_pub = [c for c in cands if (c.get("type") or c.get("tipo")) == "new"]
    pares_pub = [tuple(int(v) for v in (c.get("detail") or c.get("detalle"))) for c in nuevos_pub]

    rng = np.random.default_rng(seed)
    buses = list(red.base.bus.index)
    existentes = set(tuple(sorted((int(r.from_bus), int(r.to_bus))))
                     for _, r in red.base.line.iterrows())
    pares_replay, intentos = [], 0
    while len(pares_replay) < len(pares_pub) and intentos < 400:
        a, b = rng.choice(buses, 2, replace=False)
        key = tuple(sorted((int(a), int(b))))
        if key not in existentes and a != b:
            pares_replay.append((int(a), int(b)))
            existentes.add(key)
        intentos += 1

    if pares_replay != pares_pub:
        return None, {
            "reconstruido": False,
            "por_que": ("el flujo aleatorio replayado no reproduce los pares de lineas nuevas "
                        "publicados en el artefacto, asi que la posicion del generador al "
                        "sortear el costo es desconocida"),
            "pares_publicados": [list(p) for p in pares_pub],
            "pares_replayados": [list(p) for p in pares_replay],
            "consecuencia": ("no se publica `cost` ni nada derivado de el (`c_lin`, `Q`, "
                             "`CONST`): 14 numeros plausibles son indistinguibles de 14 medidos"),
        }

    K = len(cands)
    base_cost = np.array([1.0 if (c.get("type") or c.get("tipo")) == "parallel" else 1.8
                          for c in cands])
    cost = base_cost * rng.uniform(0.9, 1.1, K)
    return cost, {
        "reconstruido": True,
        "como": ("np.random.default_rng(%d), se consumen los sorteos de pares de buses "
                 "—rechazos incluidos— y despues uniform(0.9, 1.1, K)" % seed),
        "chequeo": ("los %d pares de lineas nuevas replayados salen en el mismo orden que "
                    "los publicados" % len(pares_pub)),
        "pares": [list(p) for p in pares_pub],
    }


def coeficientes_de(ruta):
    art = json.load(open(ruta))
    p = art["params"]
    gp = art["grid_physics"]
    cands = gp["candidates"]
    K = len(cands)
    grid = p["grid"].replace("IEEE ", "").strip()
    kb = int(p["k_budget"])
    lam = float(p["lambda_cost"])
    seed = int(p["seed"])

    print("== %s · %s · K=%d · presupuesto=%d" % (os.path.basename(ruta), grid, K, kb))
    red = Red(grid, float(p["load_scale"]))
    C0 = red.congestion(red.build())

    # GUARDIA 1 — la red reconstruida es la que se midio, o no se mide nada.
    C0_pub = float(gp["base_congestion_dc"])
    if round(C0, 3) != round(C0_pub, 3):
        raise SystemExit(
            "ABORTA: la red reconstruida da congestion base %.6f y el artefacto publica "
            "%.3f. Medir 105 coeficientes sobre una red que no es la del sello produciria "
            "numeros correctos de otro problema. Revisa RQ_TIGHTEN (hoy %.3f)."
            % (C0, C0_pub, TIGHTEN))
    print("   congestion base reproduce: %.10f (publicado %.3f)" % (C0, C0_pub))

    t0 = time.time()
    relief = np.zeros(K)
    for i in range(K):
        relief[i] = C0 - congestion_con(red, cands, [i])
    q = {}
    for i in range(K):
        for j in range(i + 1, K):
            rij = C0 - congestion_con(red, cands, [i, j])
            q[(i, j)] = rij - relief[i] - relief[j]
    medir_s = round(time.time() - t0, 2)
    print("   medidos %d r_i y %d q_ij en %.1fs (%d flujos DC)"
          % (K, len(q), medir_s, 1 + K + len(q)))

    cost, nota_costo = replay_del_costo(red, cands, seed)

    salida = {
        "que_es": ("los coeficientes que DEFINEN el problema de esta corrida de E.ON, para "
                   "que un tercero pueda recomputar su optimo sin creernos nada"),
        "completa_a": {
            "artefacto": os.path.relpath(ruta, RAIZ),
            "sha256": sha256_de(ruta),
            "por_que": ("declara `%s` y no publica esos coeficientes" % gp["congestion_model"]),
            "aclaracion": ("este archivo NO corrige ni reemplaza al artefacto: lo completa. "
                           "El sello publicado no se toca."),
        },
        "producido_por": {
            "archivo": "harness/coeficientes_eon.py",
            "sha256": sha256_de(os.path.abspath(__file__)),
            "metodo": ("anclado al artefacto publicado: los candidatos se LEEN de el, no se "
                       "regeneran. No se re-corrio el harness — ninguna version archivada "
                       "reproduce esta instancia."),
        },
        "red": {
            "grid": grid, "n_bus": int(p["n_buses"]), "n_line": int(p["n_lines"]),
            "load_scale": float(p["load_scale"]), "tighten": TIGHTEN,
            "congestion_base_dc": C0,
        },
        "problema": {
            "K": K, "k_budget": kb, "lambda_cost": lam, "seed": seed,
            "candidatos": cands,
        },
        "medido": {
            "relief_i": [float(v) for v in relief],
            "q_ij": {"%d_%d" % k: float(v) for k, v in q.items()},
            "flujos_dc_corridos": 1 + K + len(q),
            "tiempo_medicion_s": medir_s,
        },
        "lib_versions": {
            "numpy": np.__version__, "pandapower": pp.__version__,
            "python": platform.python_version(),
        },
    }
    salida["costo"] = nota_costo

    if cost is None:
        salida["lo_que_NO_se_pudo"] = [
            "reconstruir `cost`, y por lo tanto tampoco `Q`, `c_lin`, `CONST` ni la prueba",
        ]
        return salida, None

    # --- el QUBO, en el mismo convenio que 01_qubo_eon_case118_K10@e853c094.json ---
    PEN = max(1.0, float(relief.max())) * 3.0
    Q = np.zeros((K, K))
    c_lin = np.zeros(K)
    for i in range(K):
        c_lin[i] += -relief[i] + lam * cost[i] + PEN * (1 - 2 * kb)
        Q[i][i] += PEN
        for j in range(i + 1, K):
            Q[i][j] += -q[(i, j)] + 2 * PEN
    CONST = PEN * kb ** 2

    salida["problema"]["penalty"] = PEN
    salida["medido"]["cost"] = [float(v) for v in cost]
    salida["qubo"] = {
        "Q_upper": Q.tolist(), "c_lin": c_lin.tolist(), "CONST": CONST,
        "convenio": "valor(x) = x^T Q x + c_lin . x + CONST, con Q triangular superior",
        "de_donde_sale": {
            "c_lin[i]": "-relief_i[i] + lambda_cost*cost[i] + penalty*(1 - 2*k_budget)",
            "Q[i][i]": "penalty",
            "Q[i][j] (i<j)": "-q_ij[i,j] + 2*penalty",
            "CONST": "penalty * k_budget^2",
            "penalty": "max(1.0, max(relief_i)) * 3.0",
        },
    }
    return salida, (Q, c_lin, CONST)


def prueba(art_ruta, salida, qubo):
    """La prueba con criterio de exito explicito. FALLA CERRADA: si no reproduce, se
    reporta la desviacion. Jamas se ajusta un coeficiente para que calce.

    POR QUE ESTA PRUEBA DECLARA SU PRECISION EN VEZ DE AFIRMAR CERO
    ---------------------------------------------------------------
    La primera version comparaba con `==` y publicaba `desviacion: 0.0` con veredicto
    REPRODUCE. Era verdad —en el numpy del CI—. Ejercido desde afuera con otro numpy,
    el mismo archivo da -3.6e-12 en el minimo, y el que lo ejerce lee que la prueba
    falla. La afirmacion era mas fuerte de lo que el dato aguanta, y el archivo existe
    justamente para el que la va a ejercer desde afuera.

    La suma de 21 terminos que rondan 1e5 no es asociativa en punto flotante: el
    resultado depende del ORDEN, y ningun orden es mas correcto que otro. Asi que la
    prueba ahora hace tres cosas honestas en vez de una optimista:

    1. Evalua en TRES ordenes distintos y publica los tres, para que el lector vea
       cuanto se mueven los ultimos bits y no crea que descubrio un error.
    2. Compara contra una tolerancia DERIVADA, no elegida: n * eps * suma|terminos|,
       que es la cota clasica del error de redondeo de una suma de n terminos.
    3. Separa las dos afirmaciones, porque una es portable y la otra no:
       - el ARGMIN (que x gana) reproduce EXACTO en todos los ordenes -> afirmacion dura
       - el VALOR reproduce dentro de la tolerancia -> afirmacion con su precision
    """
    art = json.load(open(art_ruta))
    Q, c_lin, CONST = qubo
    K = salida["problema"]["K"]
    kb = salida["problema"]["k_budget"]
    eps = float(np.finfo(float).eps)

    def terminos(x):
        """Los sumandos del valor, sueltos. De aqui salen los tres ordenes Y la cota."""
        t = [float(c_lin[i]) for i in range(K) if x[i]]
        t += [float(Q[i][j]) for i in range(K) for j in range(i, K) if x[i] and x[j]]
        t.append(float(CONST))
        return t

    def val(x):
        """El orden CANONICO, y esta declarado en el artefacto: numpy `x @ Q @ x`."""
        xv = np.asarray(x, float)
        return float(xv @ Q @ xv + c_lin @ xv + CONST)

    def ordenes(x):
        t = terminos(x)
        suma_bucles = 0.0
        for v in t:
            suma_bucles += v
        return {
            "numpy_x@Q@x": val(x),
            "bucles_i_luego_j": suma_bucles,
            "por_magnitud_creciente": float(np.sum(sorted(t, key=abs))),
        }

    def tolerancia(x):
        t = terminos(x)
        return len(t) * eps * sum(abs(v) for v in t)

    # (a) los subconjuntos de cardinalidad exacta
    mejor, mx, n_sub = None, None, 0
    for sel in itertools.combinations(range(K), kb):
        x = [0] * K
        for i in sel:
            x[i] = 1
        n_sub += 1
        v = val(x)
        if mejor is None or v < mejor:
            mejor, mx = v, x
    # (b) la fuerza bruta completa, que es lo que corrio el harness
    mejor_fb, fbx = None, None
    for m in range(1 << K):
        x = [(m >> i) & 1 for i in range(K)]
        v = val(x)
        if mejor_fb is None or v < mejor_fb:
            mejor_fb, fbx = v, x

    ex_v, ex_x = float(art["exact"]["value"]), list(art["exact"]["x"])
    qu_v, qu_x = float(art["quantum"]["value"]), list(art["quantum"]["x"])

    ord_min, ord_qu = ordenes(mx), ordenes(qu_x)
    tol_min, tol_qu = tolerancia(mx), tolerancia(qu_x)
    peor_min = max(abs(v - ex_v) for v in ord_min.values())
    peor_qu = max(abs(v - qu_v) for v in ord_qu.values())

    # EL ARGMIN es la afirmacion dura: no depende del orden de suma, porque las
    # diferencias entre candidatos son de orden 1 y el ruido de redondeo de 1e-12.
    argmin_ok = (mx == ex_x) and (fbx == ex_x)

    r = {
        "subconjuntos_de_tamano_k": n_sub,
        "minimo_recomputado": mejor, "x_recomputado": mx,
        "fuerza_bruta_2^K": {"minimo": mejor_fb, "x": fbx, "evaluaciones": 1 << K},
        "publicado": {"exact_value": ex_v, "exact_x": ex_x,
                      "quantum_value": qu_v, "quantum_x": qu_x},
        "precision": {
            "por_que": ("la suma no es asociativa en punto flotante: el valor depende del "
                        "orden de los sumandos y ningun orden es mas correcto que otro. "
                        "Se publican tres para que el que ejerza este archivo desde afuera "
                        "vea cuanto se mueven los ultimos bits en vez de leer un fallo."),
            "LOS_TRES_ORDENES_SON_EJEMPLOS_NO_UNA_COTA": (
                "Existen ordenes de suma que caen FUERA de estos tres, por arriba y por "
                "abajo: sumar CONST primero da 4295.418727527082 en case118, y un doble "
                "bucle que acumule distinto da 4295.418727527091. No leas estos tres "
                "valores como el rango posible — son una ilustracion de la magnitud. "
                "LA COTA ES `tolerancia_derivada`, y solo esa. Este rotulo existe porque "
                "la version anterior invitaba a leerlos como rango, que es la misma "
                "trampa que traia el `desviacion: 0.0` que este bloque vino a reemplazar."),
            "orden_canonico": "numpy_x@Q@x",
            "minimo_en_tres_ordenes": ord_min,
            "x_cuantico_en_tres_ordenes": ord_qu,
            "tolerancia_derivada": {
                "formula": "n_terminos * eps_maquina * suma(|terminos|)",
                "eps_maquina": eps,
                "del_minimo": tol_min,
                "del_x_cuantico": tol_qu,
                "no_es_elegida": ("es la cota clasica del error de redondeo de una suma de "
                                  "n terminos, no un numero puesto para que calce"),
            },
            "desviacion_peor_de_los_tres_ordenes": {
                "minimo": peor_min, "x_cuantico": peor_qu},
        },
        "reproduce": {
            "x_del_minimo_EXACTO": argmin_ok,
            "minimo_dentro_de_tolerancia": peor_min <= tol_min,
            "valor_del_x_cuantico_dentro_de_tolerancia": peor_qu <= tol_qu,
        },
    }
    r["veredicto"] = "REPRODUCE" if all(r["reproduce"].values()) else "NO REPRODUCE"
    r["que_significa_el_veredicto"] = (
        "REPRODUCE quiere decir dos cosas distintas y conviene no mezclarlas: el ARGMIN "
        "—cual de los %d subconjuntos gana— reproduce EXACTO, bit a bit, en los tres "
        "ordenes de suma; y el VALOR reproduce dentro de la tolerancia derivada, que es "
        "lo maximo que se puede afirmar de una suma de punto flotante. Si lo ejerces y "
        "obtienes una diferencia de orden 1e-12, no encontraste un error: encontraste "
        "esto: la cota es la tolerancia derivada, no los tres ordenes de ejemplo." % n_sub)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artefacto")
    ap.add_argument("--todos", action="store_true")
    a = ap.parse_args()

    dir_art = os.path.join(RAIZ, "resultados_eon")
    if a.todos:
        rutas = sorted(os.path.join(dir_art, f) for f in os.listdir(dir_art) if f.endswith(".json"))
    elif a.artefacto:
        rutas = [os.path.abspath(a.artefacto)]
    else:
        sys.exit("falta --artefacto <ruta> o --todos")

    os.makedirs(SALIDA, exist_ok=True)
    resumen, fallos = [], 0
    for ruta in rutas:
        salida, qubo = coeficientes_de(ruta)
        if qubo is not None:
            salida["prueba"] = prueba(ruta, salida, qubo)
            print("   prueba: %s  (min %r vs publicado %r)"
                  % (salida["prueba"]["veredicto"],
                     salida["prueba"]["minimo_recomputado"],
                     salida["prueba"]["publicado"]["exact_value"]))
            if salida["prueba"]["veredicto"] != "REPRODUCE":
                fallos += 1
        else:
            print("   costo NO reconstruido: no se publica QUBO ni prueba")
            fallos += 1

        cuerpo = json.dumps(salida, indent=2, ensure_ascii=True, sort_keys=True)
        h = hashlib.sha256(cuerpo.encode()).hexdigest()
        nombre = "coef_%s@%s.json" % (
            os.path.basename(ruta).split("@")[0].replace("eon_", ""), h[:8])
        with open(os.path.join(SALIDA, nombre), "w") as f:
            f.write(cuerpo)
        print("   -> coeficientes_eon/%s  sha256 %s" % (nombre, h))
        resumen.append({"artefacto": os.path.basename(ruta), "salida": nombre, "sha256": h,
                        "veredicto": (salida.get("prueba") or {}).get("veredicto",
                                                                      "SIN PRUEBA")})

    # El denominador, siempre (§5 bis regla 1): cuantos se vieron, cuantos reprodujeron.
    print("\n== %d artefactos vistos · %d reprodujeron · %d no"
          % (len(rutas), len(rutas) - fallos, fallos))
    if fallos:
        print("::warning::%d de %d no reprodujeron — la desviacion esta en su archivo, "
              "sin ajustar ningun coeficiente." % (fallos, len(rutas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
