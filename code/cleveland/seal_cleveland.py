"""
Sellado v2 de la evidencia nueva del track Cleveland.

Regla vigente: sellar es del laboratorio, no del notario, y pasa SIEMPRE por
seal() de harness/rosettaq_seal.py. Nada de sellado inline. Este script produce
siete documentos RUN bajo RQ-0007 y los deja listos para que el notario
verifique, ancle en OTS y publique en triple copia.

  EXP-0007-013  KRAS G12C          rejilla congelada, 7 metodos, 18 configs
  EXP-0007-014  BCR-ABL1           idem
  EXP-0007-015  Miosina cardiaca   idem
  EXP-0007-016  c-Myc              prediccion ciega, sin ground truth
  EXP-0007-017  Nulos espaciales   bolsillo contiguo + prueba pareada
  EXP-0007-018  Cripticidad        los dos regimenes de fallo
  EXP-0007-019  Entregables        ruido, coarse-graining, costo de circuito

Cada documento declara su procedencia (que archivo de resultados lo respalda y
con que sha256), de modo que el sello cubre el resumen Y la trazabilidad al dato
crudo.
"""
import json, os, sys, datetime as dt

sys.path.insert(0, "/home/claude/evidence-repo/harness")
import rosettaq_seal as rs

R = "/home/claude/rosettaq"
OUT = "/home/claude/evidence-repo/runs/2026/07"
GH = "https://github.com/RosettaQuantum/evidence/blob/main/runs/2026/07/"
RAW = "https://raw.githubusercontent.com/RosettaQuantum/evidence/main/runs/2026/07/"
CB = "https://codeberg.org/RosettaQuantum/evidence/src/branch/main/runs/2026/07/"
RAWDATA = "https://raw.githubusercontent.com/RosettaQuantum/evidence/main/data/2026/07/"

LIBS = {"prody": "2.6.1", "numpy": "2.4.4", "scipy": "1.16.3", "python": "3.11.15"}
METHODS = ["ctqw", "diffusion", "gnm", "anm", "betweenness", "closeness", "random"]


def ts(path):
    """Hora real del archivo de resultados que respalda el documento."""
    return dt.datetime.fromtimestamp(os.path.getmtime(path), dt.timezone.utc)


def stamp(t):
    return t.strftime("%Y%m%dT%H%MZ")


def prov(*files):
    return [{"archivo": f, "sha256": rs.file_fingerprint(os.path.join(R, f))}
            for f in files]


def storage(fn):
    return {"policy": "triple-copia identica; verificar con content_hash",
            "locations": [
                {"n": 1, "kind": "github", "role": "primary",
                 "url": GH + fn, "raw_url": RAW + fn},
                {"n": 2, "kind": "codeberg", "role": "mirror", "url": CB + fn},
                {"n": 3, "kind": "cloudflare-d1", "role": "mirror",
                 "uri": "d1://rosettaq-ledger/run_archives/" + fn.split("__")[2]}]}


def mean(rows, key):
    v = [r[key] for r in rows if key in r and r[key] is not None]
    return round(sum(v) / len(v), 2) if v else None


def total(rows, key):
    return sum(r[key] for r in rows if key in r and r[key] is not None)


def build(file_id, slug, t, scope, w6, sources, scripts=None):
    fn = "RosettaQ__RUN__%s__%s__%s.json" % (file_id, stamp(t), slug)
    doc = {"meta": {"file_name": fn, "file_id": file_id, "type": "RUN",
                    "is_demo": False, "scope_note": scope},
           "w6": w6, "storage": storage(fn)}
    doc["w6"]["como"]["procedencia"] = prov(*sources)
    # todo script que participo en producir este resultado, con su sha256, para
    # que la procedencia sea verificable y no una declaracion de buena fe.
    doc["w6"]["como"]["scripts"] = prov(*(scripts or [w6["como"]["harness"]]))
    doc["w6"]["cuando"] = {
        "started_at": t.isoformat(), "archived_at": t.isoformat(),
        "timezone_note": "UTC; equipo en America/Punta_Arenas"}
    doc["w6"]["quien"] = {
        "operator": "Nicholas", "agents": ["Claude (Cowork cloud)", w6["como"]["harness"]],
        "judge_protocol_version": "juez-v1", "org": "Rosetta Quantum",
        "team": "Rosetta Quantum"}
    rs.seal(doc, harness=(w6["como"]["harness"], "1.0.0",
                          rs.file_fingerprint(os.path.join(R, w6["como"]["harness"]))))
    assert rs.verify(doc), file_id
    json.dump(doc, open(os.path.join(OUT, fn), "w"), indent=2, ensure_ascii=False)
    open(os.path.join(OUT, fn), "a").write("\n")
    return fn, doc["meta"]["content_hash"]


P1 = json.load(open(R + "/challenge_results_part1.json"))
P2 = json.load(open(R + "/challenge_results_part2.json"))
SN = json.load(open(R + "/spatial_null.json"))
PN = json.load(open(R + "/paired_null.json"))
CR = json.load(open(R + "/crypticity.json"))
RD = json.load(open(R + "/required_deliverables.json"))

emitted = []

# ------------------------------------------------------------------ dianas --
DIANAS = [
    ("EXP-0007-013", "KRAS_G12C", P1, "challenge_results_part1.json",
     "ctqw-vs-clasicos--allosteria-kras-g12c",
     "Diana obligatoria 1/4 del reto Cleveland. Rejilla congelada en PR-CLEV-001, "
     "sin ajuste por proteina. CTQW queda POR DEBAJO del azar.",
     "run_challenge_targets.py", None),
    ("EXP-0007-014", "BCR_ABL1", P1, "challenge_results_part1.json",
     "ctqw-vs-clasicos--allosteria-bcr-abl1",
     "Diana obligatoria 2/4. Top-5 = 0 para TODOS los metodos salvo el azar. "
     "La entrada 1OPL no es ciega: el acido miristico ya ocupa el bolsillo.",
     "run_challenge_targets.py", None),
    ("EXP-0007-015", "CARDIAC_MYOSIN", P2, "challenge_results_part2.json",
     "ctqw-vs-clasicos--allosteria-miosina-cardiaca",
     "Diana obligatoria 3/4. Unica ventaja cuantica del conjunto: CTQW supera a la "
     "difusion en 18/18 celdas de la rejilla. NO significativa bajo el nulo correcto.",
     "run_challenge_targets2.py", None),
]

for fid, key, src, srcfile, slug, scope, harness, _ in DIANAS:
    T = src[key]
    rows = T["rows"]
    t = ts(os.path.join(R, srcfile))
    resumen = {m: {"percentil_medio": mean(rows, m + "_pct"),
                   "top5_total": total(rows, m + "_top5"),
                   "top10_total": total(rows, m + "_top10")} for m in METHODS}
    w6 = {
        "que": {
            "recipe_id": "RQ-0007",
            "recipe_name": "Deteccion de sitios alostericos por propagador sobre red de contactos",
            "problem_class": "Allosteric site prediction (Cleveland Clinic track)",
            "instance": "%s -> %s cadena %s" % (T["apo"], T["holo"], T["chain"]),
            "quantum_side": {"metodo": "CTQW, U(t)=exp(-iAt), probabilidad integrada en la ventana",
                             "percentil_medio": resumen["ctqw"]["percentil_medio"],
                             "top5_total_18_configs": resumen["ctqw"]["top5_total"]},
            "classical_side": {"metodos": ["difusion exp(-Lt)", "GNM", "ANM",
                                           "betweenness (Brandes)", "closeness", "nulo aleatorio"],
                               "percentiles_medios": {m: resumen[m]["percentil_medio"]
                                                      for m in METHODS if m != "ctqw"}},
            "ground_truth": {"metodo": T["gt_method"], "n_residuos": len(T["gt_residues"]),
                             "descartados_por_numeracion": len(T["gt_dropped_numbering_mismatch"]),
                             "residuos": T["gt_residues"]},
            "fuente_perturbacion": {"metodo": T["source_method"],
                                    "n_residuos": len(T["source_residues"]),
                                    "residuos": T["source_residues"]},
            "outcome": ("cuantico peor que el azar" if resumen["ctqw"]["percentil_medio"] < 50
                        else "cuantico por encima del azar pero no significativo"),
            "metric": "percentil medio de los residuos alostericos verdaderos entre los distales (>6A de la fuente); 100 = el mejor",
            "scores": resumen,
            "rejilla_completa": rows,
            "top5_sitios_por_config": T["sites"],
        },
        "como": {
            "protocol": "juez-v1: misma red de residuos, misma fuente y misma ventana en ambos lados; "
                        "ground truth leido geometricamente del efector co-cristalizado (<4.5A), "
                        "definido por NINGUNO de los propagadores",
            "instance_params": {"cutoffs_A": [7.5, 8.0, 8.5, 9.0, 9.5, 10.0],
                                "windows": [[0.5, 4.0], [0.5, 8.0], [0.5, 14.0]],
                                "n_times": 16, "distal_A": 6.0, "gt_radius_A": 4.5,
                                "n_configuraciones": len(rows),
                                "n_residuos": rows[0]["n_nodes"]},
            "sweep_note": "rejilla IDENTICA a la congelada y sellada en PR-CLEV-001 el 2026-07-24, "
                          "antes de ver estos datos. Ningun parametro se ajusto por proteina.",
            "lib_versions": LIBS,
            "compute": "contenedor cloud Cowork (CPU, Linux)",
            "harness": harness,
            "raw_data_url": RAWDATA + srcfile,
        },
        "donde": {
            "quantum_backend": "CTQW por eigendescomposicion (simulacion exacta; ruta NISQ = simulacion "
                               "hamiltoniana gate-based, costo medido en EXP-0007-019)",
            "classical_backend": "difusion, GNM, ANM y centralidades por eigendescomposicion / Brandes",
            "protein_source": "RCSB PDB via ProDy",
            "region": "cloud sandbox Anthropic",
        },
        "porque": {
            "hypothesis": "si la caminata cuantica capturara algo que la difusion no captura, deberia "
                          "rankear el bolsillo alosterico verdadero por encima de ella de forma estable "
                          "a lo largo de toda la rejilla",
            "question": "En la diana %s del reto, que percentil alcanza el sitio alosterico verdadero "
                        "bajo cada propagador?" % key,
            "ledger_goal": "evidencia primaria de la propuesta Fase I del Global Quantum + AI Challenge "
                           "(Cleveland Clinic); insumo del veredicto RQ-0007",
        },
    }
    emitted.append(build(fid, slug, t, scope, w6, (srcfile,)))

# ------------------------------------------------------------------- c-Myc --
T = P2["c_MYC"]
t = ts(R + "/challenge_results_part2.json")
w6 = {
    "que": {
        "recipe_id": "RQ-0007",
        "recipe_name": "Deteccion de sitios alostericos por propagador sobre red de contactos",
        "problem_class": "Allosteric site prediction (Cleveland Clinic track)",
        "instance": "1NKP cadenas A+B (c-Myc / Max sobre ADN E-box)",
        "quantum_side": {"metodo": "CTQW sobre la red de contactos Ca",
                         "prediccion": "top-5 sitios por configuracion, adjunta"},
        "classical_side": {"metodos": ["difusion exp(-Lt)"]},
        "ground_truth": None,
        "fuente_perturbacion": {"metodo": T["source_method"],
                                "n_residuos": len(T["source_residues"]),
                                "residuos": T["source_residues"]},
        "outcome": "prediccion ciega: no existe efector co-cristalizado del que leer el sitio",
        "metric": "no evaluable hoy; queda sellada y fechada para contraste futuro",
        "rejilla_completa": T["rows"],
        "top5_sitios_por_config": T["sites"],
    },
    "como": {
        "protocol": "juez-v1 sin arbitro disponible: se emite la prediccion y se sella ANTES de que "
                    "exista el consenso de los organizadores. Es la unica forma confiable de responder "
                    "una diana que se juzgara por consenso posterior.",
        "instance_params": {"cutoffs_A": [7.5, 8.0, 8.5, 9.0, 9.5, 10.0],
                            "windows": [[0.5, 4.0], [0.5, 8.0], [0.5, 14.0]],
                            "n_times": 16, "distal_A": 6.0,
                            "n_configuraciones": len(T["rows"]),
                            "n_residuos": T["rows"][0]["n_nodes"]},
        "sweep_note": "misma rejilla congelada en PR-CLEV-001; sin ajuste",
        "lib_versions": LIBS, "compute": "contenedor cloud Cowork (CPU, Linux)",
        "harness": "run_challenge_targets2.py",
        "raw_data_url": RAWDATA + "challenge_results_part2.json",
    },
    "donde": {"quantum_backend": "CTQW por eigendescomposicion",
              "classical_backend": "difusion por eigendescomposicion del Laplaciano",
              "protein_source": "RCSB PDB 1NKP via ProDy",
              "region": "cloud sandbox Anthropic"},
    "porque": {
        "hypothesis": "una prediccion sellada y fechada antes del arbitro es la unica forma no "
                      "falsificable de participar en una diana sin ground truth",
        "question": "Que residuos distales predice la caminata cuantica como sitio alosterico en c-Myc?",
        "ledger_goal": "compromiso hacia adelante; se contrasta cuando los organizadores publiquen su consenso",
    },
}
emitted.append(build("EXP-0007-016", "ctqw--prediccion-ciega-c-myc", t,
                     "Diana obligatoria 4/4. Sin ground truth geometrico: se sella la prediccion "
                     "ANTES de que exista el consenso de los organizadores. Imposible de ajustar a posteriori.",
                     w6, ("challenge_results_part2.json",)))

# ------------------------------------------------------------------- nulos --
t = ts(R + "/paired_null.json")
w6 = {
    "que": {
        "recipe_id": "RQ-0007",
        "recipe_name": "Nulo espacial de bolsillo contiguo — instrumento de medicion",
        "problem_class": "Metodologia estadistica para prediccion de sitios alostericos",
        "instance": "KRAS G12C, BCR-ABL1 y miosina cardiaca",
        "quantum_side": {"nota": "el instrumento se aplica a TODOS los metodos por igual, "
                                 "empezando por el nuestro"},
        "classical_side": {"nota": "idem"},
        "ground_truth": "los mismos sitios geometricos de EXP-0007-013/014/015",
        "outcome": "NADA es significativo, para ningun metodo, en ninguna diana: todos los p entre 0.15 y 0.85",
        "metric": "p-valor por permutacion contra bolsillos distales contiguos del mismo tamano",
        "hallazgo_central": (
            "El percentil medio de un sitio alosterico no se puede comparar contra 50 suponiendo "
            "residuos independientes: los residuos verdaderos forman UN bolsillo contiguo, estan "
            "correlacionados espacialmente y el n efectivo es mucho menor que el numero de residuos. "
            "Toda prueba que suponga independencia infla la significancia. Al reemplazar ese supuesto "
            "por el nulo correcto, los z ingenuos de hasta |4.64| colapsan a |z| < 1.2."),
        "nulo_espacial": SN,
        "prueba_pareada": {k: {kk: v[kk] for kk in v if kk != "rows"} for k, v in PN.items()},
        "prueba_pareada_rejilla": {k: v["rows"] for k, v in PN.items()},
        "potencia": {
            "nota": "el tamano de efecto de miosina (d=+0.589) implica cuantas dianas harian falta "
                    "para zanjar el unico indicio favorable al cuantico",
            "dianas_para_p_005": 8, "dianas_para_p_001": 16,
            "combinado_tres_dianas_d": -0.196, "combinado_stouffer_z": -0.34,
            "lectura": "no hay evidencia en ninguna direccion con tres dianas; el conjunto de "
                       "validacion del propio reto es demasiado chico para detectar el efecto que "
                       "parece existir"},
    },
    "como": {
        "protocol": "nulo por permutacion espacial: se sortea un residuo distal semilla y se toman sus "
                    "k-1 vecinos distales mas cercanos (k = tamano del sitio verdadero). Preserva "
                    "contiguidad, tamano y la restriccion distal. La prueba pareada evalua la DIFERENCIA "
                    "cuantico-menos-clasico contra el mismo nulo, que tiene mucha menos varianza porque "
                    "ambos propagadores comparten grafo, fuente y ventana.",
        "instance_params": {"nulo_espacial": {"nperm": 2000, "seed": 20260717,
                                              "cutoff_A": 8.5, "window": [0.5, 8.0]},
                            "prueba_pareada": {"nperm": 5000, "seed": 20260717,
                                               "configuraciones_por_diana": 18}},
        "sweep_note": "la prueba pareada corre sobre la rejilla completa congelada, no sobre una "
                      "configuracion elegida; se reporta cada celda",
        "lib_versions": LIBS, "compute": "contenedor cloud Cowork (CPU, Linux)",
        "harness": "paired_null.py",
        "raw_data_url": RAWDATA + "spatial_null.json ; " + RAWDATA + "paired_null.json",
    },
    "donde": {"quantum_backend": "CTQW por eigendescomposicion",
              "classical_backend": "difusion, GNM, ANM, betweenness, closeness, nulo aleatorio",
              "protein_source": "RCSB PDB via ProDy", "region": "cloud sandbox Anthropic"},
    "porque": {
        "hypothesis": "la significancia reportada en este campo esta inflada por un supuesto de "
                      "independencia que los sitios alostericos violan por construccion",
        "question": "Con el nulo espacial correcto, algun metodo separa el bolsillo verdadero del azar?",
        "ledger_goal": "entregar el INSTRUMENTO DE MEDICION, no otra metrica: un nulo reutilizable con "
                       "el que evaluar la metrica de cualquiera, aplicado primero a la nuestra y con "
                       "el resultado en contra",
    },
}
emitted.append(build("EXP-0007-017", "nulo-espacial-contiguo--instrumento-de-medicion", t,
                     "Contribucion metodologica central del track. Aplicado a los 7 metodos sobre las "
                     "3 dianas con ground truth: ninguno alcanza significancia. El resultado va en "
                     "contra de nuestra propia metrica y se publica igual.",
                     w6, ("spatial_null.json", "paired_null.json"),
                     scripts=("spatial_null.py", "paired_null.py", "power.py")))

# ------------------------------------------------------------- cripticidad --
t = ts(R + "/crypticity.json")
w6 = {
    "que": {
        "recipe_id": "RQ-0007",
        "recipe_name": "Cripticidad del bolsillo — mecanismo de los dos regimenes de fallo",
        "problem_class": "Diagnostico estructural de por que falla la prediccion alosterica",
        "instance": "KRAS G12C (4OBE/6OIM) y BCR-ABL1 (1OPL/5MO4)",
        "quantum_side": {"nota": "no aplica: es un analisis estructural, no un propagador"},
        "classical_side": {"nota": "no aplica"},
        "ground_truth": "desplazamiento Ca apo-holo y conteo de contactos, medidos directamente",
        "outcome": "dos modos de fallo distintos, con mecanismo medido y no supuesto",
        "metric": "desplazamiento Ca (A) del sitio vs el resto, y contactos antes/despues de unir",
        "regimen_1_bolsillo_criptico": {
            "diana": "KRAS G12C",
            "desplazamiento_sitio_A": 1.70, "desplazamiento_resto_A": 0.83,
            "razon": 2.05, "percentil_del_sitio": 88.7,
            "contactos_apo": 214, "contactos_holo": 188,
            "lectura": "el sitio se mueve el doble que el resto y PIERDE contactos al unirse: el "
                       "bolsillo lo crea el ligando. Ningun propagador sobre la red de contactos de "
                       "la apo puede encontrar algo que todavia no existe."},
        "regimen_2_preformado_rigido": {
            "diana": "BCR-ABL1",
            "desplazamiento_sitio_A": 0.43, "desplazamiento_resto_A": 0.73,
            "razon": 0.59, "percentil_del_sitio": 32.1,
            "contactos_apo": 221, "contactos_holo": 218,
            "lectura": "el sitio se mueve MENOS que el promedio y sus contactos no cambian: esta "
                       "preformado y rigido, y aun asi es inencontrable. Aqui el problema no es que "
                       "el sitio no exista, es que la topologia de contactos Ca no lo distingue."},
        "datos_crudos": CR,
    },
    "como": {
        "protocol": "superposicion apo-holo por residuos comunes, desplazamiento Ca por residuo, y "
                    "conteo de contactos del sitio en ambas conformaciones",
        "instance_params": {"cutoff_A": 8.5, "gt_radius_A": 4.5},
        "sweep_note": "analisis explicativo posterior a la rejilla; no altera ningun resultado sellado",
        "lib_versions": LIBS, "compute": "contenedor cloud Cowork (CPU, Linux)",
        "harness": "crypticity.py",
        "raw_data_url": RAWDATA + "crypticity.json",
    },
    "donde": {"quantum_backend": "no aplica", "classical_backend": "ProDy / numpy",
              "protein_source": "RCSB PDB via ProDy", "region": "cloud sandbox Anthropic"},
    "porque": {
        "hypothesis": "un negativo sin mecanismo es un negativo debil; si el metodo falla, hay que "
                      "poder decir POR QUE falla y si el fallo es del metodo o del planteamiento",
        "question": "Por que ningun propagador encuentra estos bolsillos?",
        "ledger_goal": "convertir el negativo en diagnostico: dos regimenes, dos rutas de solucion "
                       "distintas para Fase II",
    },
}
emitted.append(build("EXP-0007-018", "cripticidad--dos-regimenes-de-fallo", t,
                     "Explicacion mecanicista del negativo. El bolsillo de KRAS lo crea el ligando; "
                     "el de BCR-ABL1 esta preformado y rigido y aun asi es inencontrable.",
                     w6, ("crypticity.json",)))

# ------------------------------------------------------------- entregables --
t = ts(R + "/required_deliverables.json")
circ = {k: RD[k]["circuito"] for k in RD}
w6 = {
    "que": {
        "recipe_id": "RQ-0007",
        "recipe_name": "Entregables exigidos por el reto: ruido, escalabilidad y costo de circuito",
        "problem_class": "Caracterizacion de implementabilidad (Cleveland Clinic track)",
        "instance": "KRAS G12C, BCR-ABL1, miosina cardiaca",
        "quantum_side": {
            "costo_de_circuito_medido": circ,
            "hallazgo": ("los grafos de contacto de proteinas tienen GRADO ACOTADO: grado maximo 19/18/19 "
                         "y exactamente 19 clases de color en un rango de tamano de 5.6x (169 a 954 "
                         "residuos). La profundidad por paso de Trotter es por tanto O(1) en el tamano "
                         "de la proteina; solo los qubits crecen logaritmicamente. La profundidad TOTAL "
                         "sigue siendo demasiado grande para NISQ, y lo decimos con el numero.")},
        "classical_side": {"nota": "el propagador exacto por eigendescomposicion es la referencia"},
        "ground_truth": "los mismos sitios geometricos de EXP-0007-013/014/015",
        "outcome": "los tres entregables quedan cubiertos, dos de ellos con resultado desfavorable",
        "metric": "Spearman del ranking distal contra el propagador ideal, y percentil del sitio",
        "resiliencia_al_ruido": {
            "desfase_cuantico": {k: RD[k]["desfase_hardware"] for k in RD},
            "ruido_de_coordenadas": {k: RD[k]["ruido_coordenadas"] for k in RD},
            "perdida_de_aristas": {k: RD[k]["perdida_aristas"] for k in RD},
            "lectura": ("el desfase a gamma=1.0 deja Spearman en 0.85/0.91/0.97 y casi no mueve el "
                        "percentil del sitio, mientras que 1 A de ruido en coordenadas lo baja a 0.59 "
                        "en KRAS. El cuello de botella NO es el hardware cuantico: es la estructura "
                        "de entrada.")},
        "escalabilidad_por_coarse_graining": {
            "datos": {k: RD[k]["coarse_graining"] for k in RD},
            "lectura": ("hasta 67x de aceleracion, pero el percentil del sitio se pasea sin monotonia "
                        "(KRAS 29.9->32.8->39.3->16.7; miosina 61.3->58.7->47.4->66.9). Hay velocidad, "
                        "no hay senal estable a la resolucion necesaria. Cualquier afirmacion de que "
                        "'escala por coarse-graining' seria insostenible con estos datos.")},
        "matrices_de_conectividad_cuantica": {
            "definicion": "C_ij = promedio_t |<i|exp(-iAt)|j>|^2 sobre la ventana; simetrica, N x N",
            "config": {"cutoff_A": 8.5, "window": [0.5, 8.0], "n_times": 16},
            "archivos": ["qmatrix_KRAS_G12C.npy (169x169)",
                         "qmatrix_BCR_ABL1.npy (451x451)",
                         "qmatrix_CARDIAC_MYOSIN.npy (954x954)",
                         "qmatrix_c_MYC.npy (171x171)"]},
        "visualizacion_3d": {"archivo": "cleveland_viz.html",
                             "nota": "HTML autocontenido, sin CDN ni almacenamiento del navegador; "
                                     "renderizador 3D propio con el sitio verdadero, el top-5 predicho "
                                     "y el panel estadistico"},
        "datos_crudos": RD,
    },
    "como": {
        "protocol": ("el costo de circuito se MIDE, no se cita de una cota asintotica: la caminata se "
                     "descompone por coloreo voraz de aristas en clases que son emparejamientos, cuyo "
                     "exponencial es exacto en forma cerrada 2x2; se construye el producto de Trotter "
                     "de primer orden y se mide cuantos pasos r hacen falta para que converja el "
                     "RANKING (Spearman >= 0.99), exigencia mucho mas debil que converger el estado. "
                     "El desfase se modela por desdoblamiento estocastico con el ruido INTERCALADO con "
                     "la evolucion en 8 subintervalos: aplicado solo al final no tendria efecto sobre "
                     "las poblaciones, que es lo que se mide."),
        "instance_params": {"cutoff_A": 8.5, "window": [0.5, 8.0], "n_times": 16,
                            "gammas": [0.0, 0.01, 0.05, 0.2, 1.0], "trayectorias": 24,
                            "sigmas_coordenadas_A": [0.25, 0.5, 1.0],
                            "prob_perdida_aristas": [0.01, 0.05, 0.10],
                            "bloques_coarse_grain": [1, 2, 4, 8],
                            "barrido_trotter_r": [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]},
        "sweep_note": "configuracion central de la rejilla congelada; los parametros de ruido y de "
                      "circuito se fijaron antes de mirar los resultados",
        "lib_versions": LIBS, "compute": "contenedor cloud Cowork (CPU, Linux)",
        "harness": "required_deliverables.py",
        "raw_data_url": RAWDATA + "required_deliverables.json ; " + RAWDATA + "qmatrices.npz",
    },
    "donde": {"quantum_backend": "CTQW exacta por eigendescomposicion + producto de Trotter de primer "
                                 "orden desde el coloreo de aristas + canal de defasaje por trayectorias",
              "classical_backend": "numpy / scipy",
              "protein_source": "RCSB PDB via ProDy", "region": "cloud sandbox Anthropic"},
    "porque": {
        "hypothesis": "el reto penaliza los circuitos profundos sin optimizar; hay que llegar con la "
                      "profundidad medida en la mano, aunque el numero sea malo",
        "question": "Cuanto ruido tolera el metodo, escala por coarse-graining, y cuanto cuesta el "
                    "circuito de verdad?",
        "ledger_goal": "cubrir los tres entregables exigidos de Fase I con medicion propia y reportar "
                       "los dos que salen desfavorables",
    },
}
emitted.append(build("EXP-0007-019", "entregables-exigidos--ruido-escala-y-costo-de-circuito", t,
                     "Los tres entregables que el reto exige, medidos. Dos salen desfavorables "
                     "(coarse-graining inestable, circuito demasiado profundo para NISQ) y se reportan igual.",
                     w6, ("required_deliverables.json", "viz_payload.json", "qmatrices.npz"),
                     scripts=("required_deliverables.py", "make_viz.py", "build_viz.py")))

print("Sellados %d documentos bajo rosettaq-archive/v2:\n" % len(emitted))
for fn, h in emitted:
    print("  %-14s %s" % (fn.split("__")[2], h))
    print("  %s\n" % fn)
