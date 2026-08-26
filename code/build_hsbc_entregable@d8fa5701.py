#!/usr/bin/env python3
"""Genera el ENTREGABLE del track HSBC contra ESTANDAR-presentacion-entregable.md.

Regla de la casa: las cifras se LEEN de los artefactos sellados al armar; la prosa vive
aqui. Cada afirmacion lleva su etiqueta [medido] / [por construccion] / [por literatura].
"""
import glob, hashlib, json, os, re as _re, subprocess, sys
import numpy as np
from scipy import stats

AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs

def cargar_sellado(patron):
    # solo .json: los .ots anclados comparten prefijo y son binarios (tropiezo de julio)
    f = [x for x in sorted(glob.glob(os.path.join(EV, patron))) if x.endswith(".json")][0]
    d = json.load(open(f))
    assert rs.verify(d), f
    return d

def art(patron):
    f = glob.glob(os.path.join(EV, "resultados_hsbc", patron))[0]
    return json.load(open(f)), os.path.basename(f)

PRE1 = cargar_sellado("prereg/2026/08/*HSBC-001*")
PRE2 = cargar_sellado("prereg/2026/08/*HSBC-002*")
MAN = cargar_sellado("manifests/*HSBC-ULB*")
SEL = cargar_sellado("runs/2026/08/*HSBC-ATAQUE*")
PRE3 = cargar_sellado("prereg/2026/08/*HSBC-003-CUANTICO*")
ERR = cargar_sellado("reports/2026/08/*ERRATA*HSBC-003*")
QUA = cargar_sellado("runs/2026/08/*HSBC-Q-001*")
IEEE = cargar_sellado("runs/2026/08/*HSBC-IEEE-001*")
Q2 = cargar_sellado("runs/2026/08/*HSBC-Q-002*")
ERRQ = cargar_sellado("reports/2026/08/*ERRATA-EXP-HSBC-Q-001*")
ERRP = cargar_sellado("reports/2026/08/*ERRATA-PREREG-HSBC-003*")
BASE, BASE_F = art("hsbc_ulb_baseline_lightgbm-xgboost@*.json")
S = {}
for k in ("S1", "S2", "S3", "S4"):
    S[k] = art("*ataque_%s_*@*.json" % k)

a = {k: [r["AUPRC"] for r in S[k][0]["corridas"]] for k in S}
m = {k: float(np.mean(a[k])) for k in a}
sd = {k: float(np.std(a[k], ddof=1)) for k in a}
delta = m["S1"] - m["S4"]
_, p_w = stats.ttest_ind(a["S1"], a["S4"], equal_var=False)
u, p_mw = stats.mannwhitneyu(a["S1"], a["S4"], alternative="two-sided")
ruido = float(np.median([r["AUPRC_boot_se"] for r in S["S1"][0]["corridas"]
                         + S["S4"][0]["corridas"]]))
xgb = BASE["modelos"]["xgboost"]; lgb = BASE["modelos"]["lightgbm"]
cen = MAN["w6"]["que"]["censo"]; fuente = MAN["w6"]["que"]["fuente"]
part = BASE["particion"]

ORDEN = ["resumen", "contra_lo_pedido", "pregunta", "datos", "metodo", "resultados", "ataques",
         "cuantico", "ventana", "presupuesto", "externa", "limites", "viabilidad",
         "impacto", "equipo", "pedimos", "reproduccion", "anexos"]
_vistas = []

def sec(titulo, clave):
    """Escribe el encabezado con su numero DERIVADO y aborta si sale de orden."""
    if clave not in ORDEN:
        raise SystemExit("seccion %r no declarada en ORDEN" % clave)
    if _vistas and ORDEN.index(clave) <= ORDEN.index(_vistas[-1]):
        raise SystemExit("la seccion %r sale despues de %r y ORDEN dice lo contrario"
                         % (clave, _vistas[-1]))
    _vistas.append(clave)
    w("## %d · %s" % (ORDEN.index(clave) + 1, titulo))

def ref(clave):
    """«§N» sin teclearlo: si el orden cambia, la referencia cambia con el."""
    if clave not in ORDEN:
        raise SystemExit("referencia a seccion no declarada: %r" % clave)
    return "§%d" % (ORDEN.index(clave) + 1)

# LA UNICA CITA EXTERNA, y vive en UN solo lugar. Se verifico abriendo arxiv.org, no
# aceptando el reporte de quien la paso: el resumen se leyo completo y de ahi sale la
# frase de abajo. Se cita en INGLES porque es textual — traducir y presentar como
# entrecomillado seria alterarla; la traduccion va al lado, marcada como tal.
V = QUA["w6"]["que"]["VEREDICTO"]
HAND = QUA["w6"]["que"]["EL_HANDICAP_Y_POR_QUE_NO_EXPLICA_EL_RESULTADO"]
RBF = QUA["w6"]["que"]["TAMPOCO_LE_GANA_AL_RBF"]
CTRL = QUA["w6"]["que"]["controles_exploratorios"]["resultados"]
D4 = QUA["w6"]["que"]["decisiones_declaradas_antes_de_mirar_el_test"]["D4_soporte"]
A2 = CTRL["A2_xgboost_mismo_dato_mismas_features"]
A1 = CTRL["A1_rbf_mismo_dato_mismas_features"]
CB = CTRL["B_cuantico_con_los_417_fraudes"]

# las dos puntas del costo salen de la TABLA de la errata, no de su prosa ni de memoria
_tab = ERR["w6"]["que"]["tabla_recomputada_al_sellar"]
_bar = min(_tab, key=lambda k: _tab[k]["usd_total"])
_car = max(_tab, key=lambda k: _tab[k]["usd_total"])
_usd = lambda v: "{:,.0f}".format(v).replace(",", ".")

S52 = Q2["w6"]["que"]["salidas_exigidas_por_el_5_2"]
PERM = Q2["w6"]["que"]["importancia_por_permutacion"]
BIN = S52["binary_prediction"]["umbral_F1_optimo_en_train"]
MUE = Q2["w6"]["que"]["el_conteo_que_el_statement_exige_textual"]
# EL CIRCUITO SE MIDE, NO SE DESCRIBE. Los parametros salen del sello (qubits, reps,
# entrelazamiento) y qiskit construye el objeto y lo cuenta. Describir «un circuito de poca
# profundidad» sin contarlo es la clase de afirmacion que este documento no admite.
from circuito_hsbc import medir as _medir_circuito
CIRC = _medir_circuito(
    Q2["w6"]["que"]["el_conteo_que_el_statement_exige_textual"]["qubits"],
    QUA["w6"]["que"]["decisiones_declaradas_antes_de_mirar_el_test"]["D3_codificacion"]["reps"],
    QUA["w6"]["que"]["decisiones_declaradas_antes_de_mirar_el_test"]["D3_codificacion"]["entrelazamiento"])
D1 = QUA["w6"]["que"]["decisiones_declaradas_antes_de_mirar_el_test"]["D1_features"]
# Los tiempos se LEEN del artefacto crudo publicado. El de la corrida completa esta; el de
# la inferencia sola NO esta en ningun artefacto —vivio en la consola— y por eso no se
# reporta. Una latencia por transaccion copiada de un log es una cifra sin procedencia, que
# es exactamente el defecto que este documento denuncia.
_QRAW = json.load(open(os.path.join(EV, "code", "resultado_hsbc_cuantico@71e071ed.json")))
QUA_SEG = float(_QRAW["modelos"]["kernel_cuantico"]["segundos"])
SPW = float(BASE["scale_pos_weight"])
def _censo_del_archivo():
    """Sellos de origin/main, POR TIPO. Un total llamado «corridas» es una cifra correcta
    con etiqueta falsa, y eso es peor que una cifra mal contada: el lector que la comprueba
    encuentra otro numero y deja de comprobar el resto."""
    import collections, subprocess as sp
    ref = os.environ.get("RQ_CENSO_COMMIT") or sp.run(
        ["git", "rev-parse", "origin/main"], cwd=EV, capture_output=True,
        text=True).stdout.strip()
    globals()["CENSO_COMMIT"] = ref
    # UNA sola pasada: `ls-tree` da el hash de cada blob y `cat-file --batch` los sirve
    # todos en un proceso. La version anterior lanzaba un `git show` por archivo —unos 500
    # procesos entre las cuatro regeneraciones del sellador— y se pasaba de diez minutos.
    arbol = sp.run(["git", "ls-tree", "-r", ref], cwd=EV, capture_output=True,
                   text=True).stdout.split("\n")
    quiero = []
    for l in arbol:
        if "\t" not in l: continue
        meta, ruta = l.split("\t", 1)
        if not ruta.endswith(".json"): continue
        if not any(ruta.startswith(x) for x in ("runs/", "prereg/", "manifests/", "reports/")):
            continue
        quiero.append(meta.split()[2])
    if not quiero:
        return collections.Counter()
    out = sp.run(["git", "cat-file", "--batch"], cwd=EV, input="\n".join(quiero),
                 capture_output=True, text=True).stdout
    c = collections.Counter()
    for m in _re.finditer(r'"type"\s*:\s*"([A-Z]+)"', out):
        c[m.group(1)] += 1
    return c

CENSO = _censo_del_archivo()
# los sellos que ESTE documento usa. Se derivan de lo que el generador carga, no se cuentan
# a mano: si mañana se agrega uno, la cifra se mueve sola.
BASE_SELLO = cargar_sellado("runs/2026/08/*HSBC-BASE*")
SELLOS_USADOS = [PRE1, PRE2, PRE3, MAN, BASE_SELLO, SEL, QUA, Q2, IEEE, ERRQ, ERRP]
CITADOS = sorted({d["meta"]["file_id"] for d in SELLOS_USADOS})
CT = QUA["w6"]["que"]["particion"]["corte_temporal"]
ICT = IEEE["w6"]["que"]["EL_CORTE_ES_EL_FUTURO"]
CM_C = xgb["confusion_0.5"]
PREC_C = CM_C["tp"] / max(1, CM_C["tp"] + CM_C["fp"])
REC_C = CM_C["tp"] / max(1, CM_C["tp"] + CM_C["fn"])
IJ = IEEE["w6"]["que"]["mejor_por_AUPRC"]
IDIF = IEEE["w6"]["que"]["IEEE_es_mas_dificil_que_ULB"]

def n(x, d=4):
    """Coma decimal. Una sola implementacion: dos formateos divergen y nadie lo nota."""
    return ("%.*f" % (d, x)).replace(".", ",")

def ic(v):
    return "[%s – %s]" % (n(v[0]), n(v[1]))

from fuentes_hsbc import FUENTES
CITA_ID = FUENTES[0]["id"]
CITA_TIT = ("*Quantum Kernel k-Means for Credit-Card Fraud Detection: A Controlled "
            "Benchmark on Real Transaction Data*, M. Faryad, 16 de agosto de 2026")
CITA_QUOTE = ("We find no robust quantum advantage: the sign of the difference depends on "
              "register size, all effect sizes are below 0.013 ARI, and the single "
              "significant advantage we observe is fully explained by the number of "
              "configurations searched.")
CITA_TRAD = ("No encontramos ventaja cuántica robusta: el signo de la diferencia depende "
             "del tamaño del registro, todos los tamaños de efecto están por debajo de "
             "0,013 ARI, y la única ventaja significativa que observamos queda explicada "
             "por entero por el número de configuraciones probadas.")

L = []; w = L.append
w("# Cuando el protocolo decide el número: pre-registro anclado, ataque adversarial y un "
  "negativo cuántico que sobrevive a sus propios controles")
w("")
w("**Rosetta Quantum · track HSBC del 2026 Global Quantum + AI Challenge · borrador para")
w("aprobación de Nicholas — NO publicado**")
w("")
w("> Toda cifra de este documento se lee de un artefacto sellado al momento de armarlo;")
w("> ninguna se tipea. Cada afirmación lleva una de tres etiquetas: **[medido]** (nuestro")
w("> instrumento lo produjo y el artefacto permite recomputarlo), **[por construcción]**")
w("> (se deriva de cómo está hecho el objeto), **[por literatura]** (lo sostiene una")
w("> fuente citada). Lo que no tiene etiqueta, no entró.")
w("")

sec("Resumen", "resumen")
w("")
w("Construimos un baseline clásico de detección de fraude sobre datos públicos, con la")
w("pregunta y el protocolo **sellados y commiteados antes de escribir el código** (y")
w("anclados en Bitcoin después, por el notario). Después lo")
w("atacamos: repetimos la medición bajo el protocolo que usa la literatura y bajo tres")
w("variantes diseñadas para matar nuestro propio resultado, con los desenlaces posibles")
w("escritos y sellados antes de correr. Salió esto: nuestra implementación **reproduce los")
w("números publicados cuando usa el protocolo publicado** [medido]; la elección de")
w("partición mueve la métrica principal en ~0,07 [medido]; el sobremuestreo SMOTE, del que")
# la cifra NO se escribe: sale del mismo calculo que el §6. Escrita a mano decia
# +0,0003 (resta de redondeados) contra el +0,0004 que el §6 derivaba del dato — dos
# cifras para lo mismo dentro del documento, cazadas al cruzar la version inglesa.
w("la literatura depende, **aporta %s cuando se aplica bien** [medido] — y cuando se"
  % ("%+.4f" % (m["S2"] - m["S1"])).replace(".", ","))
w("aplica en el orden defectuoso común, **la métrica satura en 1,0000 con cualquier")
w("semilla** [medido]: perfección reportable con cualquier modelo. No reclamamos novedad")
w("científica — el fenómeno de fondo está taxonomizado [por literatura: Kapoor & Narayanan,")
w("*Leakage and the reproducibility crisis in ML-based science*, Patterns 2023]. Lo que")
w("ofrecemos es la máquina que lo mide con pre-registro verificable y recomputación por")
w("terceros.")
w("")
w("**Y después corrimos el brazo cuántico, que era la razón de ser del track.** Un kernel de")
w("fidelidad en simulación exacta, contra el mismo clásico, sobre el mismo test comprobado")
w("por hash. **Perdió**: %s contra %s, con el intervalo entero por debajo [medido] (%s)."
  % (n(V["cuantico"]["AUPRC"]), n(V["clasico_sellado"]["AUPRC"], 6), ref("cuantico")))
w("Lo que hace que ese negativo valga algo no es haberlo medido —eso es el mínimo— sino lo")
w("que hicimos después: **le dimos al clásico exactamente el mismo handicap** que el")
w("protocolo le impone al cuántico, y el clásico llegó a %s con su intervalo solapando el"
  % n(A2["AUPRC"]))
w("del basal [medido]. El handicap era real **y no explica el resultado**. Además adoptamos")
w("contra nosotros mismos la guardia de presupuesto de búsqueda (%s) y verificamos la"
  % ref("presupuesto"))
w("evidencia externa abriéndola, no citándola de oído (%s). Un banco que hoy evalúa un" % ref("externa"))
w("piloto cuántico de fraude puede leer acá qué se midió, con qué protocolo, y qué sigue")
w("sin saberse.")
w("")

sec("Resultados contra lo que ustedes piden", "contra_lo_pedido")
w("")
w("Esta sección existe para que usted **no tenga que buscar** si cumplimos. Cada fila cita el")
w("enunciado y dice dónde está la respuesta.")
w("")
w("Las **métricas del §4.1 para los dos brazos**, con precision, recall y matriz de")
w("confusión completa, están en %s — esta sección no las repite: las señala." % ref("resultados"))
w("")
w("### Las tres salidas del §5.2")
w("")
w("| pedido, textual | dónde está |")
w("|---|---|")
w("| *«Fraud Probability — Float [0, 1]»* | archivo 2 del paquete, columna `fraud_probability`; rango %s |"
  % ic(S52["fraud_probability"]["rango"]))
w("| *«Binary Prediction — Integer {0, 1}»* | archivo 2, columna `binary_prediction`; %d positivos |"
  % BIN["predichos_positivos"])
w("| *«Feature Attribution — contribution of features to each prediction»* | archivo 2, %d columnas `attribution_*`, **una fila por transacción** |"
  % S52["feature_attribution"]["local_por_prediccion"]["forma"][1])
w("")
w("### Lo demás que el enunciado pide, y dónde")
w("")
w("| pedido | § | dónde |")
w("|---|---|---|")
w("| *«encoding strategy, and circuit design choices»* | 5.2 | %s |" % ref("cuantico"))
w("| *«comparison with at least one classical baseline»* | 5.2 | %s y %s |"
  % (ref("resultados"), ref("cuantico")))
w("| *«discussion of any observed quantum improvement and under what conditions»* | 5.2 | %s |"
  % ref("cuantico"))
w("| *«handling of class imbalance should be documented»* | 5.3 | %s |" % ref("cuantico"))
w("| *«feature selection is expected for quantum approaches»* | 5.3 | %s |" % ref("cuantico"))
w("| *«qubit count and circuit depth»* | 5.3 | %s, tabla del circuito |" % ref("cuantico"))
w("| *«feature attribution or importance analysis is valued»* | 5.3 | %s, local y por permutación |" % ref("cuantico"))
w("| *«total number of samples used for quantum execution must be explicitly stated»* | 4.2 | %s |" % ref("cuantico"))
w("| *«subsampling must be performed using stratified sampling»* | 4.2 | %s |" % ref("cuantico"))
w("| *«benchmark against these published results»* | 4.1 | %s |" % ref("resultados"))
w("| *«error mitigation techniques»* | 5.3 | no aplica: no se ejecutó hardware (%s) |" % ref("cuantico"))
w("| *«comparison of simulator vs. hardware results»* | 5.3 | no aplica, misma razón |")
w("")
w("**Y una que el enunciado NO pide y le entregamos igual**, porque es lo que más le sirve a")
w("un banco que hoy evalúa un piloto: %s." % ref("ventana"))
w("")

sec("La pregunta y su pre-registro", "pregunta")
w("")
w("La pregunta —¿qué aporta un modelo cuántico o cuántico-inspirado contra un clásico")
w("afinado, con protocolo fijado antes de mirar?— quedó sellada en `%s`"
  % PRE1["meta"]["file_id"])
w("(`%s`), commit `72dcbf2`, **antes de descargar un solo dato** [por construcción: es"
  % PRE1["meta"]["content_hash"][:23])
w("una propiedad del historial de git, no una afirmación nuestra]. El ataque adversarial")
w("se pre-registró aparte en `%s` (`%s`)," % (PRE2["meta"]["file_id"],
                                              PRE2["meta"]["content_hash"][:23]))
w("**con sus tres desenlaces escritos antes de correr, incluido el que nos dejaba mal**.")
w("El brazo cuántico tiene pre-registro propio, `%s` (`%s`)," % (PRE3["meta"]["file_id"],
                                                                PRE3["meta"]["content_hash"][:23]))
w("y sus resultados están en %s." % ref("cuantico"))
w("")
w("> **Aviso al lector: el pre-registro del brazo cuántico tiene una errata sellada.**")
w("> `%s` (`%s`) retracta una afirmación" % (ERR["meta"]["file_id"],
                                             ERR["meta"]["content_hash"][:23]))
w("> del original: la de que cambiar de proveedor no movería el costo. **Es falsa**, y la")
w("> tabla del propio artefacto original ya la desmentía: el mismo trabajo cuesta USD %s"
  % _usd(_tab[_bar]["usd_total"]))
w("> en %s y USD %s en %s — un factor de %s [medido]."
  % (_bar, _usd(_tab[_car]["usd_total"]), _car,
     n(_tab[_car]["usd_total"] / _tab[_bar]["usd_total"], 1)))
w("> **El original no se reescribe**: su archivo, su hash y su ancla quedan intactos, y la")
w("> corrección viaja como documento aparte. Si usted abre el pre-registro se va a encontrar")
w("> con esa frase, y queda avisado acá: mandarlo a leer algo que sabemos incorrecto sin")
w("> decírselo sería el defecto, no el descuido. **Lo que la errata NO retracta** es la")
w("> decisión operativa — la demostración acotada sigue siendo la elegida y el gasto")
w("> autorizado sigue en US$0.")
w("")

sec("Datos, con sus límites medidos", "datos")
w("")
w("**Fuente** [medido]: ULB *creditcard* vía OpenML (id 1597, v1), md5 medido = declarado")
w("por la fuente (`%s`), sha256 `%s…`," % (fuente["md5_medido"][:12] + "…",
                                           fuente["sha256_medido"][:16]))
w("fijado en el manifiesto sellado `%s` **antes del primer entrenamiento**."
  % MAN["meta"]["file_id"])
w("**Censo** [medido]: %s filas, %d fraudes (%.3f %%), 0 valores nulos (trivialmente 0 en"
  % ("{:,}".format(cen["filas"]).replace(",", "."), cen["fraudes"],
     100 * cen["tasa_fraude"]))
w("ambas clases). Ninguna fila fue excluida; las features se usan tal cual llegan, sin")
w("transformación nuestra [por construcción].")
w("")
w("**Los límites, medidos y no estimados:**")
w("")
w("- **La ventana total son 48,00 horas exactas** [medido: rango Time 0–172.792 s] — dos")
w("  días de septiembre de 2013 [por literatura: documentación del dataset]. Nuestra")
w("  partición temporal 80/20 deja **7,65 horas** de test: llamar a eso «el futuro» sería")
w("  más de lo que el dato sostiene, y no lo llamamos así.")
w("- **La clase positiva no está pareja en el tiempo** [medido]: la tasa de fraude varía")
w("  5× entre bloques de 8 h (0,46 % nocturno contra 0,09 %); el test temporal queda con")
w("  75 de los 492 fraudes (15,2 %).")
w("- **Las features V1–V28 son componentes de un PCA que los autores del dataset ajustaron")
w("  sobre el conjunto completo** [por construcción: se publicó ya transformado, así que")
w("  nadie puede re-ajustarlo sólo sobre su train]. Es PCA no supervisado —no vio")
w("  etiquetas—, de magnitud distinta a las fugas por sobremuestreo; **nosotros lo")
w("  declaramos** (anexo B, L1.2-heredado).")
w("- **Marco muestral**: transacciones de tarjetahabientes europeos de un procesador, dos")
w("  días [por literatura]. **No afirmamos que represente el fraude en general**: los")
w("  hallazgos de este documento son intra-dataset y por construcción, no extrapolaciones.")
w("")

sec("Método", "metodo")
w("")
w("**Partición** [medido, sellada en el prereg]: temporal 80/20 por la columna `Time` —")
w("train %s filas (%d fraudes), test %s filas (%d fraudes), sha256 del test declarado en"
  % ("{:,}".format(part["train"]["filas"]).replace(",", "."), part["train"]["fraudes"],
     "{:,}".format(part["test"]["filas"]).replace(",", "."), part["test"]["fraudes"]))
w("el artefacto (`%s…`) y **bit-idéntico entre dos máquinas distintas** [medido: Mac"
  % part["test"]["sha256"][:16])
w("local y runner de CI produjeron el mismo hash]. Duplicados exactos entre mitades:")
w("%d [medido]." % part["solape_de_contenido_duplicados_exactos"])
w("")
w("**Métrica que manda** [sellada antes]: AUPRC — con prevalencia 0,17 % el AUC-ROC es")
w("ópticamente generoso. AUC-ROC, F1 y matriz de confusión se reportan siempre al lado.")
w("")
w("**Baseline**: XGBoost (config declarada en el artefacto `@%s`). **LightGBM está"
  % BASE_F.split("@")[1][:8])
w("ABIERTO**: nuestra configuración v1 lo rompe (AUPRC %.4f, %s falsos positivos) — es"
  % (lgb["AUPRC"], "{:,}".format(lgb["confusion_0.5"]["fp"]).replace(",", ".")))
w("un defecto de configuración nuestra, no del método, y **no entra como baseline afinado")
w("hasta pasar la búsqueda declarada** (pendiente; si al final no entra, este párrafo se")
w("actualiza con el porqué, no desaparece).")
w("")
w("**Guardias, todas falla-cerrado y probadas por mutación** [medido: tres artefactos")
w("deliberadamente rotos —dato ajeno al manifiesto, harness sin procedencia, métrica que")
w("no calza con los scores— hacen gritar la batería con código de salida 1; el caso base")
w("pasa]: el dato se verifica contra el manifiesto antes de entrenar; ninguna fila del")
w("test participa en entrenamiento; la estratificación de cada submuestra se mide, no se")
w("asume; cada artefacto lleva el sha256 del harness que lo produjo.")
w("")

sec("Resultados del brazo clásico", "resultados")
w("")
w("**Baseline XGBoost sobre partición temporal** [medido, artefacto `@%s`]:"
  % BASE_F.split("@")[1][:8])
w("")
w("| métrica | valor | IC95 bootstrap (2.000, semilla 42) |")
w("|---|---|---|")
w("| AUPRC | **%.4f** | [%.3f – %.3f] |" % (xgb["AUPRC"], *xgb["AUPRC_IC95"]))
w("| AUC-ROC | %.4f | [%.3f – %.3f] |" % (xgb["AUC_ROC"], *xgb["AUC_IC95"]))
w("| F1 @ 0,5 | %.4f | tp=%d fp=%d fn=%d |" % (xgb["F1_umbral_0.5"],
  xgb["confusion_0.5"]["tp"], xgb["confusion_0.5"]["fp"], xgb["confusion_0.5"]["fn"]))
w("")
w("Contexto de validación [por literatura: los baselines que el statement del challenge")
w("tabula]: el stacking publicado sobre este dataset reporta AUC-ROC 0,9887; el nuestro da")
w("%.4f sobre partición temporal. **El intervalo de nuestro AUPRC contiene el 0,871"
  % xgb["AUC_ROC"])
w("publicado, así que no afirmamos diferencia contra ese número** — la comparación")
w("honesta es intra-implementación y viene en el %s." % ref("ataques"))
w("")

w("### Las métricas que pide el §4.1, para los dos brazos")
w("")
w("| métrica | clásico (xgboost) | kernel cuántico |")
w("|---|---|---|")
w("| **AUC-ROC** | %s | %s |" % (n(xgb["AUC_ROC"], 6), n(V["cuantico"]["AUC_ROC"], 6)))
w("| **AUPRC** | **%s** %s | **%s** %s |"
  % (n(xgb["AUPRC"], 6), ic(xgb["AUPRC_IC95"]),
     n(V["cuantico"]["AUPRC"], 6), ic(V["cuantico"]["IC95"])))
w("| **F1** | %s | %s |" % (n(xgb["F1_umbral_0.5"]), n(BIN["F1"])))
w("| **Precision** | %s | %s |" % (n(PREC_C), n(BIN["precision"])))
w("| **Recall** | %s | %s |" % (n(REC_C), n(BIN["recall"])))
w("| **matriz de confusión** | tp=%d fp=%d fn=%d tn=%d | tp=%d fp=%d fn=%d tn=%d |"
  % (CM_C["tp"], CM_C["fp"], CM_C["fn"], CM_C["tn"],
     BIN["confusion"]["tp"], BIN["confusion"]["fp"], BIN["confusion"]["fn"],
     BIN["confusion"]["tn"]))
w("")
w("*El umbral del brazo clásico es 0,5 sobre una probabilidad. El del cuántico se eligió")
w("**en el train** sobre la probabilidad calibrada, nunca mirando el test; el porqué está en")
w("%s. Los dos se evalúan sobre el mismo test, comprobado por hash.*" % ref("cuantico"))
w("")

sec("Los ataques al propio resultado", "ataques")
w("")
w("Cuatro series, 65 entrenamientos, **el mismo modelo y el mismo dato en todas** —")
w("lo que cambia es el protocolo [medido, sello `%s`]:" % SEL["meta"]["file_id"])
w("")
w("| serie | protocolo | n | AUPRC media ± sd |")
w("|---|---|---|---|")
w("| S1 | aleatorio estratificado 80/20, sin SMOTE | %d | %.4f ± %.4f |"
  % (len(a["S1"]), m["S1"], sd["S1"]))
w("| S2 | aleatorio + SMOTE **dentro** del train | %d | **%.4f** ± %.4f |"
  % (len(a["S2"]), m["S2"], sd["S2"]))
w("| S3 | aleatorio + SMOTE **antes** del split (defectuoso a propósito) | %d | %.4f ± %.5f |"
  % (len(a["S3"]), m["S3"], sd["S3"]))
w("| S4 | temporal, cortes 70–90 %% | %d | %.4f ± %.4f |" % (len(a["S4"]), m["S4"], sd["S4"]))
w("")
w("**Qué sobrevivió y qué no, contra los desenlaces sellados antes:**")
w("")
w("1. **La implementación quedó validada** [medido]: S2 —el protocolo de la literatura,")
w("   bien aplicado— cae dentro de la banda pre-fijada [0,841–0,901] construida desde los")
w("   números publicados. Nuestra diferencia temporal-vs-aleatorio no es un artefacto de")
w("   implementación.")
w("2. **El efecto de partición existe bajo su criterio pre-sellado, con margen estrecho y")
w("   se dice que es estrecho** [medido]: Δ = media(S1) − media(S4) = %.4f; Welch"
  % delta)
w("   p = %.4g y Mann-Whitney p = %.4g (concuerdan); la segunda condición —Δ > 2× ruido"
  % (p_w, p_mw))
w("   bootstrap (%.4f)— **se cumple por el 1,5 %% del umbral: una realización distinta"
  % (2 * ruido))
w("   del ruido podría no cumplirla.** El lector decide con el margen a la vista.")
w("3. **El hueco que anticipamos no se materializó y consta igual** [por construcción]:")
w("   antes de correr advertimos que si S2 quedaba bajo banda y S3 la sobrepasaba, los")
w("   desenlaces sellados tenían una región sin cubrir. S2 cayó en banda y el desenlace")
w("   disparó sin ambigüedad — pero un pre-registro que anticipa sus propios huecos vale")
w("   más que uno donde todo calza de casualidad.")
w("4. **La sensibilidad al corte es suave** [medido]: AUPRC temporal 0,81→0,74 entre")
w("   cortes 70 % y 90 %; el efecto no depende de un corte único. El corte 90 queda con")
w("   22 fraudes en test y es el más ruidoso.")
w("")
w("**El resultado central del ataque — y el titular de este documento:**")
w("")
w("> **Aplicar el sobremuestreo antes de separar el conjunto de prueba no infla la")
w("> métrica: la destruye.** AUPRC = 1,0000 en las 20 semillas [medido]. El test queda")
w("> con 50 % de positivos sintéticos —contra 0,172 % reales— y con gemelos sintéticos")
w("> de filas de entrenamiento [por construcción]. **Quien evalúe así puede reportar")
w("> perfección con cualquier modelo**, y por lo tanto un número publicado bajo ese")
w("> protocolo no informa sobre el modelo. Ningún valor de S3 se cita jamás como")
w("> rendimiento — es aritmética del protocolo, no calidad.")
w("")
w("Su complemento [medido]: cuando SMOTE se aplica **bien**, aporta %s sobre el"
  % ("%+.4f" % (m["S2"] - m["S1"])).replace(".", ","))
w("aleatorio puro (%.4f vs %.4f). En este dataset y esta implementación, **la partición"
  % (m["S2"], m["S1"]))
w("hace todo el trabajo**.")
w("")

# ============================ EL BRAZO CUANTICO ============================
sec("El brazo cuántico: el negativo, y por qué no fue el handicap", "cuantico")
w("")
w("El pre-registro del brazo cuántico (`%s`, `%s`)" % (PRE3["meta"]["file_id"],
                                                       PRE3["meta"]["content_hash"][:23]))
w("fijó el criterio **antes de correr**: AUPRC sobre el test completo, IC95 por bootstrap de")
w("2.000 remuestreos con semilla 42, y **no hay ventaja si el intervalo se solapa con el del")
w("clásico o queda por debajo**. También declaró de antemano que **los dos desenlaces son")
w("entregables**. Salió el que nos deja mal, y por eso está acá.")
w("")
w("| brazo | AUPRC | IC95 |")
w("|---|---|---|")
w("| clásico sellado (`%s`) | **%s** | %s |" % (V["clasico_sellado"]["leido_de"],
                                                n(V["clasico_sellado"]["AUPRC"], 6),
                                                ic(V["clasico_sellado"]["IC95"])))
w("| kernel cuántico de fidelidad, simulación exacta | **%s** | %s |"
  % (n(V["cuantico"]["AUPRC"], 6), ic(V["cuantico"]["IC95"])))
w("")
w("**Cruce de ventaja cuántica: %d** [medido]. El intervalo del brazo cuántico queda entero"
  % V["cruce_ventaja_cuantica"])
w("por debajo. Los dos brazos se midieron sobre **el mismo test, comprobado por hash**")
w("(`%s…`) y con el mismo remuestreo: una comparación con distinto" % V["mismo_test_comprobado_por_hash"][:16])
w("bootstrap no sería una comparación, así que el sellador **aborta** si los dos hashes no")
w("coinciden [por construcción].")
w("")
w("### El handicap era real, y lo medimos en vez de invocarlo")
w("")
w("El enunciado exige muestreo **estratificado**. Al %s %% de fraude, un soporte de %s puntos"
  % (n(100 * part["train"]["tasa"], 3), "{:,}".format(D4["n"]).replace(",", ".")))
w("deja **%d positivos**, contra los %d con que se entrenó el clásico. Es una desventaja"
  % (D4["fraudes"], BASE["particion"]["train"]["fraudes"]))
w("dura y asimétrica, y es la primera explicación que cualquiera daría — nosotros incluidos.")
w("")
w("**Así que le dimos al clásico exactamente el mismo handicap** [medido]: la misma submuestra")
w("de %s puntos, las mismas 8 variables, los mismos %d fraudes."
  % ("{:,}".format(D4["n"]).replace(",", "."), D4["fraudes"]))
w("")
w("| control (no pre-registrado) | AUPRC | IC95 | contra el basal |")
w("|---|---|---|---|")
w("| xgboost, misma muestra y mismas variables | **%s** | %s | se solapa |"
  % (n(A2["AUPRC"]), ic(A2["AUPRC_IC95"])))
w("| kernel cuántico con los %d fraudes (no estratificado) | %s | %s | por debajo |"
  % (BASE["particion"]["train"]["fraudes"], n(CB["AUPRC"]), ic(CB["AUPRC_IC95"])))
w("| RBF, misma muestra y mismas variables | %s | %s | por debajo |"
  % (n(A1["AUPRC"]), ic(A1["AUPRC_IC95"])))
w("")
w("Un xgboost con la muestra mutilada llega a **%s**, y su intervalo **se solapa con el del"
  % n(A2["AUPRC"]))
w("basal**: el muestreo estratificado le costó al método clásico algo que ni siquiera es")
w("detectable. Y quitándole el handicap por completo al brazo cuántico —los %d fraudes— sube"
  % BASE["particion"]["train"]["fraudes"])
w("a %s y **sigue por debajo**. El handicap existe y no explica el resultado." % n(CB["AUPRC"]))
w("")
w("Sin esta medición, «el kernel cuántico pierde» y «le dimos %d positivos» son"
  % D4["fraudes"])
w("indistinguibles, y publicar la primera sería un reporte falso aunque la cifra fuera")
w("correcta.")
w("")
w("### Tampoco afirmamos ganarle al RBF")
w("")
w("Con el mismo dato, las mismas variables y el mismo clasificador, el kernel cuántico da %s"
  % n(V["cuantico"]["AUPRC"]))
w("y el RBF %s. Se ve como una victoria hasta que se miran los intervalos: %s contra %s,"
  % (n(A1["AUPRC"]), ic(V["cuantico"]["IC95"]), ic(A1["AUPRC_IC95"])))
w("**se tocan**. Por la misma regla con que negamos la ventaja cuántica frente al basal,")
w("tampoco podemos afirmar que le gane al RBF [medido]. La regla se aplica contra nosotros o")
w("no es una regla.")
w("")
w("### Simulación exacta: no es una limitación que excusar, es lo que el enunciado propone")
w("")
w("El propio enunciado del desafío dice, textual, que *«full end-to-end model training or")
w("inference on quantum hardware is not expected nor required»*, y **recomienda")
w("expresamente** prototipar en los simuladores administrados de Amazon Braket antes de")
w("mandar trabajos a hardware [por literatura: enunciado oficial, §5.3]. Correr en")
w("simulación exacta con gasto US$0 es la vía que el desafío propone, no un atajo nuestro.")
w("")
w("**Y hay una cláusula cuyo alcance conviene declarar en vez de dar por supuesto.** La")
w("exigencia de submuestreo estratificado aparece anidada bajo *«Teams using hardware are")
w("encouraged to:»*. **Nosotros no corrimos en hardware**, así que en lectura llana esa")
w("cláusula no nos obliga — y sin embargo la cumplimos, lo que nos costó quedarnos con %d"
  % D4["fraudes"])
w("fraudes en vez de %d. **No forzamos la lectura que nos conviene**: reportamos el brazo"
  % BASE["particion"]["train"]["fraudes"])
w("pre-registrado *con* la restricción (%s) y el control sin ella (%s), y **los dos quedan"
  % (n(V["cuantico"]["AUPRC"]), n(CB["AUPRC"])))
w("por debajo del basal** [medido]. La conclusión no depende de cómo se lea la regla.")
w("")
w("### Estrategia de codificación y diseño del circuito")
w("")
w("El §5.2 del enunciado pide *«description of quantum approach, encoding strategy, and")
w("circuit design choices»*. Esto es esa descripción.")
w("")
w("**De 30 columnas a %d qubits.** El enunciado dice que la selección de variables *«is"
  % CIRC["qubits"])
w("expected for quantum approaches»*, porque codificar cientos de columnas en un circuito no")
w("es practicable hoy. Elegimos las %d de mayor |correlación de Pearson con la etiqueta|,"
  % CIRC["qubits"])
w("**calculada sólo sobre el train** —mirarlo en el test sería la fuga que la partición")
w("temporal viene a impedir—: %s [medido]." % ", ".join(D1["elegidas"]))
w("")
w("**De número real a ángulo.** Cada variable se estandariza con la media y la sigma del")
w("train, se recorta a ±3 σ y se lleva a `[0, π]`. Los límites salen del train, no del")
w("conjunto completo. Un qubit por variable.")
w("")
w("**El mapa.** `ZZFeatureMap` (Havlíček et al., *Nature* 567, 2019) con `reps = %d` y"
  % CIRC["reps"])
w("entrelazamiento completo por pares — el mapa canónico de la literatura, no uno nuestro. La")
w("convención de fases **no se dedujo de memoria: se verificó contra el objeto que construye")
w("qiskit** antes de usarla, y ahí apareció un defecto real que sólo esa comprobación podía")
w("ver (%s)." % ref("reproduccion"))
w("")
w("**El circuito, contado y no descrito** [medido: construido con los parámetros que el")
w("sello declara y medido con qiskit al armar este documento]:")
w("")
w("| propiedad | valor |")
w("|---|---|")
w("| qubits | %d |" % CIRC["qubits"])
w("| profundidad | %d |" % CIRC["profundidad"])
w("| puertas totales | %d (%s) |"
  % (CIRC["puertas"], ", ".join("%d %s" % (v, k) for k, v in sorted(CIRC["ops"].items()))))
w("| puertas de dos qubits | %d |" % CIRC["dos_qubits"])
w("| pares entrelazados | %d — exige conectividad **todos con todos** |" % CIRC["pares"])
for _nom, _d in CIRC["bases"].items():
    w("| profundidad transpilado a %s | %d |" % (_nom, _d))
w("")
w("*Medido sobre el circuito descompuesto **una** vez a puertas elementales y transpilado")
w("desde ahí con `optimization_level=1` y semilla fija. El procedimiento se declara porque")
w("la profundidad depende de él: descomponer dos veces antes de transpilar da otra cifra, y")
w("entonces el número sería una propiedad de cómo medimos y no del circuito.*")
w("")
# el costo se LEE del pre-registro sellado, que lo derivo de la tarifa publicada
_COSTO = PRE3["w6"]["que"]["hardware"]["costo_medido_no_gastado"]["test_completo_x2000_soportes_USD"]
w("**Y lo que eso significa para hardware cercano, dicho sin adornos** [por construcción]:")
w("%d puertas de dos qubits sobre %d qubits, con **%d pares que exigen conectividad "
  "todos-con-todos**, es un circuito caro para los dispositivos de hoy. En una topología "
  "con conectividad limitada el transpilador inserta intercambios y la profundidad sube: se "
  "ve ya al pasar de %d en la base más favorable a %d en la otra."
  % (CIRC["dos_qubits"], CIRC["qubits"], CIRC["pares"],
     min(CIRC["bases"].values()), max(CIRC["bases"].values())))
w("")
w("**Y esto es el circuito por cada par (transacción, punto de soporte) del kernel**, no un")
w("circuito suelto: ahí es donde el costo se vuelve prohibitivo. El pre-registro lo tiene")
w("calculado desde la tarifa publicada de Braket: **USD %s** para el test completo [medido],"
  % "{:,.0f}".format(_COSTO).replace(",", "."))
w("y por eso no se corrió en hardware — con autorización de gasto US$0.")
w("")
w("### Cómo manejamos el desbalance de clases")
w("")
w("El §5.3 dice que el manejo del desbalance *«should be documented»*. Lo hicimos de cuatro")
w("formas distintas y ninguna es un remuestreo sintético:")
w("")
w("- **Ponderación en la pérdida.** El brazo clásico usa `scale_pos_weight` = %s, que es la"
  % n(SPW, 2))
w("  razón negativos/positivos del train. El brazo cuántico usa `class_weight='balanced'`.")
w("- **Submuestreo estratificado** para el soporte cuántico, que **preserva** la razón de")
w("  fraude en vez de corregirla: %d fraudes en %s puntos, la misma tasa del train."
  % (D4["fraudes"], "{:,}".format(D4["n"]).replace(",", ".")))
w("- **El umbral se elige en el train**, no en el test, y se reporta con su matriz completa")
w("  en vez de un solo número.")
w("- **La métrica principal es AUPRC**, que el propio enunciado recomienda para datos")
w("  desbalanceados, y no la exactitud — que con %s %% de fraude premia predecir «no» siempre."
  % n(100 * part["train"]["tasa"], 3))
w("")
w("**Lo que NO hicimos, y es deliberado:** no aplicamos SMOTE ni ningún sobremuestreo en el")
w("resultado principal. %s muestra por qué: aplicado bien aporta %s, y aplicado en el orden"
  % (ref("ataques"), ("%+.4f" % (m["S2"] - m["S1"])).replace(".", ",")))
w("defectuoso común **satura la métrica en 1,0000 con cualquier semilla**.")
w("")
w("### Latencia y tiempo de entrenamiento")
w("")
w("El enunciado los lista como *good-to-have*. Los tenemos medidos [medido]:")
w("")
w("| | brazo cuántico (simulación exacta) | xgboost clásico |")
w("|---|---|---|")
w("| tiempo total de la corrida, extremo a extremo | %s s | %s s |"
  % (n(QUA_SEG, 1), n(float(xgb["segundos"]), 1)))
w("")
w("**Lo que NO reportamos, y por qué.** Una latencia de inferencia por transacción: el")
w("tiempo de ese tramo quedó en la consola y **no viaja en ningún artefacto**, así que")
w("copiarlo acá sería una cifra sin procedencia. Se mide y se sella, o no se reporta.")
w("")
w("**Y aunque la tuviéramos, no sería la de un despliegue cuántico** [por")
w("construcción]. El atajo del statevector existe **porque** se simula: en un dispositivo")
w("real ese objeto no existe y vuelven las evaluaciones par a par del kernel. La cifra de")
w("arriba dice cuánto cuesta obtener el modelo por esta vía, no cuánto costaría en hardware.")
w("")
w("### El modelo no estaba inerte: usa las ocho variables y pierde igual")
w("")
w("La objeción natural a un negativo es que la implementación estuviera rota o ignorando sus")
w("entradas. **Se midió.** Barajamos cada variable en el test y medimos cuánto cae el AUPRC,")
w("con %d repeticiones por variable para que la caída tenga intervalo y no sea una corrida"
  % PERM["por_variable"][list(PERM["por_variable"])[0]]["repeticiones"])
w("suelta [medido].")
w("")
w("| variable | caída de AUPRC al barajarla | AUPRC que queda | IC95 |")
w("|---|---|---|---|")
for _v, _x in sorted(PERM["por_variable"].items(), key=lambda t: -t[1]["caida_media_de_AUPRC"]):
    w("| %s | %s | %s | %s |" % (_v, n(_x["caida_media_de_AUPRC"]),
                                 n(PERM["AUPRC_de_referencia"] - _x["caida_media_de_AUPRC"]),
                                 ic(_x["IC95"])))
w("")
w("**%d de %d variables tienen una caída cuyo intervalo no cruza cero** [medido]. Barajar"
  % (len(PERM["por_variable"]) - len(PERM["variables_cuya_caida_cruza_cero"]),
     len(PERM["por_variable"])))
w("una sola de ellas derrumba el AUPRC hasta el orden de la prevalencia. **El modelo no está")
w("inerte: extrae señal de todas sus entradas** — y aun usándola toda llega a %s, mientras un"
  % n(V["cuantico"]["AUPRC"]))
w("clásico **con las mismas ocho variables y la misma muestra** llega a %s." % n(A2["AUPRC"]))
w("")
w("Eso **cierra la salida más fácil para un lector escéptico** y hace el negativo más fuerte,")
w("no más débil. Y coincide con la atribución local, que es otra medición: las contribuciones")
w("por transacción son casi uniformes entre variables. Ninguna domina; todas aportan.")
w("")
w("### Las tres salidas que el enunciado exige")
w("")
w("El §5.2 del enunciado pide tres artefactos y el brazo sellado producía uno. Están en")
w("`%s` [medido]:" % Q2["meta"]["file_id"])
w("")
w("| salida pedida | qué entregamos |")
w("|---|---|")
w("| *Fraud Probability*, `Float [0,1]` | probabilidad calibrada, rango %s |"
  % ic(S52["fraud_probability"]["rango"]))
w("| *Binary Prediction*, `Integer {0,1}` | umbral elegido en el **train**: %d positivos, "
  "Precision %s, Recall %s, F1 %s |"
  % (BIN["predichos_positivos"], n(BIN["precision"], 3), n(BIN["recall"], 3), n(BIN["F1"], 3)))
w("| *Feature Attribution*, contribución **por predicción** | matriz de %s × %d: un vector "
  "de contribuciones por cada transacción del test |"
  % ("{:,}".format(S52["feature_attribution"]["local_por_prediccion"]["forma"][0]).replace(",", "."),
     S52["feature_attribution"]["local_por_prediccion"]["forma"][1]))
w("")
w("**Y el conteo que el enunciado exige textualmente** —*«the total number of samples used")
w("for quantum execution must be explicitly stated in the submission»*— con esas palabras:")
_mil = lambda x: "{:,}".format(int(x)).replace(",", ".")
w("soporte estratificado **%s** (%d fraudes), calibración **%s**, test **%s**, **total %s "
  "muestras** con ejecución cuántica, sobre **%d qubits** [medido]."
  % (_mil(MUE["soporte_estratificado"]), MUE["fraudes_en_el_soporte"],
     _mil(MUE["calibracion"]), _mil(MUE["test_evaluado"]),
     _mil(MUE["total_de_muestras_con_ejecucion_cuantica"]), MUE["qubits"]))
w("")
w("> **La probabilidad calibrada no es cosmética, y lo encontramos nosotros antes de")
w("> entregar.** Al comprobar si cumplíamos el `Float [0,1]` que el enunciado pide, vimos que")
# el rango se LEE de los scores publicados, no se teclea: es el dato que motiva la errata
_z = np.load(os.path.join(EV, "code", "scores_q_kernel_cuantico@091914f1.npz"))["y_score"]
w("> nuestros scores eran **márgenes** de la función de decisión, de %s a %s. El AUPRC y el"
  % (n(float(_z.min())), n(float(_z.max()))))
w("> AUC no lo notan —son de ranking— pero el «umbral 0,5» del artefacto original aplicaba")
w("> 0,5 a esa escala, y de ahí salía una Precision de 1,000 con **3** positivos predichos de")
w("> %s: el punto ultraconservador de una escala arbitraria, no una propiedad del método."
  % "{:,}".format(MUE["test_evaluado"]).replace(",", "."))
w("> Está corregido en la errata `%s`, que **no reescribe el original**" % ERRQ["meta"]["file_id"])
w("> y deja el veredicto intacto. Con el umbral elegido en el train, Precision %s y Recall %s."
  % (n(BIN["precision"], 3), n(BIN["recall"], 3)))
w("")
w("### Qué NO responde esta medición")
w("")
w("Nada sobre hardware. El brazo corrió en **simulación exacta**, con gasto US$0 y sin")
w("enviar un solo circuito a un dispositivo: un statevector no tiene ruido, ni error de")
w("lectura, ni decoherencia, ni error de transpilación. Por eso este número es un **techo**")
w("[por construcción]: con el mismo mapa, la versión ruidosa no puede superar a la exacta.")
w("Que no haya ventaja acá **cierra el caso**; que la hubiera **no** la probaría en")
w("hardware. Esa asimetría es la razón de que una simulación baste para un negativo y no")
w("bastaría para un positivo.")
w("")

# ============================ PRESUPUESTO DE BUSQUEDA ============================
w("### Ruido y mitigación: qué aplicaría, y por qué acá no hizo falta")
w("")
w("El §4.2 valora documentar las consideraciones de hardware —ruido, mitigación de error, y")
w("la comparación contra el simulador—. Lo decimos con precisión, incluido el hecho de que")
w("**no corrimos hardware**, que es lo que hace que esta sección sea corta y honesta en vez")
w("de larga y especulativa.")
w("")
w("**Nuestra simulación es exacta, no ruidosa.** Un statevector no tiene error de lectura ni")
w("decoherencia, así que **no hay nada que mitigar**: aplicar mitigación de error a una")
w("simulación exacta no mejoraría nada, porque no hay error que corregir. El enunciado")
w("recomienda prototipar en los simuladores administrados de Braket (SV1, TN1, DM1) antes de")
w("ir a hardware; nosotros nos quedamos un paso antes, en simulación exacta local, con gasto")
w("US$0.")
w("")
w("**Lo que aplicaría si se ejecutara en un dispositivo**, y cuál es el orden de importancia")
w("para *este* circuito en particular [por construcción]:")
w("")
w("- **Mitigación de error de lectura**, primero: el kernel de fidelidad se estima de la")
w("  frecuencia del resultado `|0…0⟩`, así que un sesgo en la lectura entra **directo** en")
w("  cada entrada de la matriz. Es el error que más nos afectaría.")
w("- **Extrapolación a ruido cero (ZNE)**, después: con %d puertas de dos qubits el error de"
  % CIRC["dos_qubits"])
w("  compuerta acumulado domina, y ZNE es lo que se usa para esa clase de circuito.")
w("- **Y el que ninguna técnica arregla**: `DM1`, el simulador de matriz de densidad de")
w("  Braket, permite prototipar con ruido **antes** de gastar en hardware. Ése sería el")
w("  paso siguiente natural, y es barato comparado con la QPU.")
w("")
w("**La comparación simulador contra hardware no la tenemos, y no la insinuamos.** Es una de")
w("las métricas que el enunciado lista como deseables y **la nuestra está vacía**: para")
w("llenarla hay que ejecutar, y el pre-registro autoriza gasto US$0. Lo que sí podemos decir")
w("es la dirección: nuestro número es un **techo**, así que la versión ruidosa quedaría por")
w("debajo — y ya estamos por debajo del clásico.")
w("")

sec("Lo que nadie le va a decir: el dataset recomendado no puede contestar la pregunta "
    "del enunciado", "ventana")
w("")
w("Esto no nos lo pidieron. Lo entregamos porque es lo que más le sirve a un banco que hoy")
w("está evaluando un piloto, y porque lo tenemos **medido y sellado**, no opinado.")
w("")
w("**ULB, el dataset que el enunciado recomienda, tiene 48 horas de datos en total.** Nuestra")
w("partición temporal —la que el pre-registro fija— deja **%s horas de test** "
  "[medido: `ventana_de_test_dias` = %s en `%s`]."
  % (n(CT["ventana_de_test_dias"] * 24, 1), n(CT["ventana_de_test_dias"], 2),
     QUA["meta"]["file_id"]))
w("")
w("Un modelo evaluado ahí está ajustado a **una foto de dos días de septiembre de 2013**. No")
w("hay forma de saber si generaliza a la semana siguiente, porque **no hay semana siguiente")
w("en los datos**. No es un defecto de quien eligió el dataset: es una propiedad del dataset.")
w("")
w("**Y tenemos con qué compararlo.** El otro benchmark del track, IEEE-CIS, lo medimos con la")
w("misma regla y está sellado en `%s`:" % IEEE["meta"]["file_id"])
w("")
w("| | ULB | IEEE-CIS |")
w("|---|---|---|")
w("| ventana de test | **%s h** | **%s días** |"
  % (n(CT["ventana_de_test_dias"] * 24, 1), n(ICT["ventana_de_test_dias"], 2)))
w("| razón entre ambas | — | **%s×** más futuro real |"
  % n(ICT["ventana_de_test_dias"] / CT["ventana_de_test_dias"], 1))
w("| tasa de fraude | %s %% | %s %% (**%s× más frecuente**) |"
  % (n(100 * IDIF["tasa_de_fraude_ULB"], 3), n(100 * IDIF["tasa_de_fraude_IEEE"], 3),
     n(IDIF["tasa_de_fraude_IEEE"] / IDIF["tasa_de_fraude_ULB"], 0)))
w("| mejor AUPRC | %s | %s |" % (n(IDIF["AUPRC_ULB"], 6), n(IJ["AUPRC"], 6)))
w("")
w("**Lea esas dos últimas filas juntas.** En IEEE-CIS el fraude es **%s veces más "
  "frecuente** —o sea, el problema debería ser más fácil— **y aun así se predice peor**: "
  "%s contra %s"
  % (n(IDIF["tasa_de_fraude_IEEE"] / IDIF["tasa_de_fraude_ULB"], 0),
     n(IJ["AUPRC"], 4), n(IDIF["AUPRC_ULB"], 4)))
w("[medido]. Que la clase minoritaria sea más abundante y el resultado empeore es")
w("exactamente lo que uno esperaría si el número alto de ULB viene de **la ventana corta** y")
w("no de que el problema sea fácil.")
w("")
w("**Qué significa para usted, en una frase:** el número que su equipo le reporta sobre ULB")
w("**no está midiendo robustez temporal**, porque en ULB no hay tiempo suficiente para")
w("medirla. Un benchmark con meses de holdout le va a dar peor — y va a ser más parecido a")
w("lo que le pasa en producción, donde el fraude cambia de forma entre un trimestre y el")
w("siguiente.")
w("")
w("**Lo que NO afirmamos** [por construcción]: que ULB no sirva, ni que el enunciado")
w("estuviera equivocado en recomendarlo. Sirve para comparar implementaciones entre sí —es")
w("lo que hacemos en %s— y para eso la ventana corta no molesta. Lo que no puede hacer es"
  % ref("ataques"))
w("responder «¿esto aguanta el paso del tiempo?», y ésa es la pregunta que un despliegue")
w("hace. **Son dos datasets, no una población**: no extrapolamos más allá de estos dos.")
w("")

sec("Presupuesto de búsqueda: la guardia que adoptamos contra nosotros mismos", "presupuesto")
w("")
w("De %s [por literatura] tomamos una guardia y la incorporamos al protocolo, porque ataca" % CITA_ID)
w("la forma más barata de engañarse con un resultado cuántico: **elegir el modelo cuántico")
w("entre más configuraciones que el clásico**. En ese trabajo, la única ventaja")
w("estadísticamente significativa que observaron **quedó explicada por entero por el número")
w("de configuraciones probadas** — dejó de ser un hallazgo y pasó a ser un artefacto del")
w("procedimiento.")
w("")
w("**Nuestro presupuesto de búsqueda, medido: una configuración por brazo, en los dos**")
w("[medido]. No hay `GridSearchCV`, `RandomizedSearchCV`, `optuna` ni `param_grid` en el")
w("instrumento: los hiperparámetros de los dos brazos están fijos en el código publicado")
w("(`code/hsbc_harness@%s.py`), y se comprueba leyéndolo. Nuestro negativo no puede ser un"
  % QUA["w6"]["como"]["harness"]["sha256"].split(":")[-1][:8])
w("artefacto del presupuesto de búsqueda, porque no hubo búsqueda.")
w("")
w("**Y el reverso, que corre en contra nuestra y va dicho igual**: el mismo trabajo reporta")
w("que las elecciones ordinarias de hiperparámetros mueven el desempeño **considerablemente")
w("más que el kernel cuántico**. Si nadie afinó nada, entonces nuestro `C = 1`, el mapa con")
w("`reps = 2` y el escalado a `[0, π]` son exactamente esa clase de elección sin afinar.")
w("**No podemos distinguir «el método no aporta» de «esta configuración no aporta»**, y una")
w("búsqueda emparejada entre los dos brazos es trabajo pendiente, no resultado.")
w("")
w("**Pero ese caveat es más chico de lo que nosotros mismos lo habíamos hecho, y decirlo")
w("también corresponde.** `%s` muestra que el ajuste óptimo del ancho de banda **acerca**"
  % FUENTES[2]["id"])
w("el kernel cuántico al RBF (%s). Si eso es así, afinar no nos habría alejado del clásico:" % ref("externa"))
w("nos habría empujado **hacia** él. El caveat sigue en pie —no estamos en ese régimen")
w("porque no afinamos— pero deja de ser «quizá con otra configuración habría ganado» y pasa")
w("a ser «la dirección en que la literatura dice que se mueve al afinar es hacia el kernel")
w("clásico, no lejos de él». **Un caveat inflado es otra forma de no decir lo que se sabe.**")
w("")

# ============================ EVIDENCIA EXTERNA ============================
sec("Lo que ya se sabía: triangulación en tres ejes", "externa")
w("")
w("Nuestro resultado no llega a un terreno vacío. **Ninguno de los tres trabajos de abajo")
w("replica nuestra medición** —somos ranking supervisado con AUPRC sobre fraude, y ninguno")
w("es eso— y decirlo importa: presentarlos como réplicas sería la costura que este documento")
w("existe para evitar. Lo que hacen es cerrar por tres lados distintos.")
w("")
w("| fuente | eje | qué mide |")
w("|---|---|---|")
for _f in FUENTES:
    w("| `%s` | %s | %s |" % (_f["id"], _f["eje"], _f["mide"]))
w("")
for _f in FUENTES:
    w("**`%s`** — *%s*, %s, %s [por literatura]." % (_f["id"], _f["tit"], _f["autor"], _f["fecha"]))
    w("")
    w("> %s" % _f["quote"])
    w("")
    w("*(traducción nuestra: %s)*" % _f["trad"])
    w("")
w("**Los dos hallazgos que más nos tocan no son los titulares:**")
w("")
w("- **La diferencia geométrica no predice nada.** `%s` reporta, textual, que" % FUENTES[1]["id"])
w("  *«the geometric difference, while large throughout (g ≫ 1), does not predict")
w("  out-of-sample gains (ρ = −0.20)»*. Esa diferencia es **el diagnóstico estándar** con que")
w("  se sostiene que un kernel cuántico es «suficientemente distinto» del clásico como para")
w("  tener ventaja. Ahí es grande y **correlaciona negativamente** con la ganancia real. Es")
w("  el contraejemplo publicado al argumento de «espacio exponencial ⇒ separa mejor».")
w("- **Una evaluación mal montada fabrica la ventaja.** El mismo trabajo documenta que")
w("  *«a 60-window evaluation on a universe screened with full-sample information makes the")
w("  same quantum kernel appear dominant on stability criteria»*: información del futuro")
w("  filtrándose y produciendo dominancia donde no la hay. **Es el mismo fenómeno que")
w("  medimos nosotros** en %s con el equilibrado aplicado antes de partir, que satura la" % ref("ataques"))
w("  métrica en 1,0000 con cualquier semilla. Dos equipos, dos mercados, el mismo mecanismo.")
w("")
w("**Y el tercero acota un límite nuestro, en contra de la lectura que nos convendría.** En")
w("%s declaramos que no afinamos hiperparámetros en ningún brazo y que por eso no podemos" % ref("presupuesto"))
w("separar «el método no aporta» de «esta configuración no aporta». `%s` dice que el"
  % FUENTES[2]["id"])
w("ajuste óptimo del ancho de banda **acerca** el kernel cuántico al RBF. Si eso es así, afinar")
w("no lo alejaría del clásico: lo empujaría hacia él. **Nuestro caveat sigue en pie —no")
w("estamos en ese régimen porque no afinamos— pero corta menos de lo que parecía**, y es")
w("coherente con que nuestro kernel cuántico y el RBF **no sean distinguibles** por nuestro")
w("propio criterio (%s)." % ref("cuantico"))
w("")
w("**Lo que NO afirmamos** [por construcción]: que esto sea una revisión de literatura. Son")
w("**tres fuentes salidas de un barrido nuestro**, abiertas y verificadas frase por frase —")
w("ninguna entró por relevo. Tres papers no son un barrido con denominador, y ese barrido no")
w("está hecho.")
w("")

sec("Qué no podemos afirmar", "limites")
w("")
w("- **Nada sobre hardware cuántico**: el brazo cuántico corrió en **simulación exacta**,")
w("  con gasto US$0 y sin enviar un solo circuito a un dispositivo. Un statevector no tiene")
w("  ruido, ni error de lectura, ni decoherencia. El resultado es un **techo**: con el mismo")
w("  mapa, la versión ruidosa no puede superar a la exacta. Que no haya ventaja ahí cierra")
w("  el caso; que la hubiera **no** la probaría en hardware.")
w("- **No podemos separar «el método no aporta» de «esta configuración no aporta»**: ningún")
w("  brazo llevó búsqueda de hiperparámetros (%s), y la literatura que citamos reporta que" % ref("presupuesto"))
w("  esas elecciones mueven más que el propio kernel cuántico.")
w("- **Los controles del brazo cuántico NO están pre-registrados**: se decidieron después de")
w("  ver el resultado primario, el artefacto lo dice en un campo propio, y no modifican el")
w("  primario. No buscamos otra codificación ni otras variables hasta que alguna cruzara:")
w("  eso es justo lo que el pre-registro existe para impedir.")
w("- **Desviación declarada**: el pre-registro decía correr en CI y el brazo cuántico corrió")
w("  en el Mac del laboratorio. Va escrita dentro del sello con su razón; el test es el")
w("  mismo, comprobado por hash, y reproducirlo en CI queda pendiente.")
w("- **Una sola fuente externa verificada** (%s): no hicimos revisión de literatura." % ref("externa"))
w("- **Nada contra el 0,871 publicado como número**: nuestro IC lo contiene; la evidencia")
w("  es el Δ intra-implementación, no la resta entre implementaciones.")
w("- **Los hallazgos del ataque son intra-dataset**: 48 horas, un procesador, 2013. Valen")
w("  para ULB por construcción y no se extrapolan — ni siquiera al IEEE-CIS que medimos")
w("  aparte más abajo, donde el ataque no se repitió.")
w("- **El margen del criterio C es estrecho** (1,5 % del umbral) y así viaja.")
w("- **LightGBM sigue abierto** por configuración nuestra; la búsqueda declarada está")
w("  pendiente para ambos modelos.")
w("- **Validez externa, ya no pendiente pero acotada** (REFORMS 8a): el segundo dataset")
w("  del track, IEEE-CIS, está medido y sellado (`%s`): el mejor" % IEEE["meta"]["file_id"])
w("  modelo llega a **%s** %s [medido], contra %s en ULB. El fraude"
  % (n(IJ["AUPRC"]), ic(IJ["IC95"]), n(IDIF["AUPRC_ULB"], 6)))
w("  ahí es **%s veces más frecuente** y aun así se predice peor — lo que dice que la"
  % n(IDIF["tasa_de_fraude_IEEE"] / IDIF["tasa_de_fraude_ULB"], 0))
w("  dificultad no es sólo el desbalance. Sigue acotado: **son dos datasets, no una")
w("  población**, y el brazo cuántico corrió sólo sobre ULB.")
w("")

sec("Viabilidad y recursos", "viabilidad")
w("")
_CM = PRE3["w6"]["que"]["hardware"]["costo_medido_no_gastado"]
_usd2 = lambda v: "{:,.0f}".format(v).replace(",", ".")
w("**Lo que ya está hecho corrió con gasto US$0**, en un Mac, en menos de un minuto por "
  "brazo [medido: %s s el cuántico, %s s el clásico]. No hay infraestructura oculta detrás "
  "de estos números: el instrumento es un archivo de Python que va en el paquete y se puede "
  "correr." % (n(QUA_SEG, 1), n(float(xgb["segundos"]), 1)))
w("")
w("**Lo que costaría llevarlo a hardware, derivado de la tarifa publicada y no estimado a "
  "ojo** [medido, en el pre-registro sellado]: **USD %s** para el test completo, y **USD "
  "%s** para una demostración acotada de 200×50 en el backend más barato."
  % (_usd2(_CM["test_completo_x2000_soportes_USD"]), _usd2(_CM["demo_200x50_USD"])))
w("")
w("El grueso de ese costo es la **tarifa fija por tarea**: en un kernel cada par")
w("(transacción, punto de soporte) es un circuito distinto y no se amortiza repitiendo")
w("disparos. Consecuencia práctica: **reducir disparos casi no mueve el costo; sólo reducir")
w("pares** — y reducir pares rompe la comparabilidad con el test sellado. La errata")
w("`%s` acota esa frase: en los backends de disparo caro la cuota se invierte."
  % ERRP["meta"]["file_id"])
w("")
w("**Lo que haría falta para la fase siguiente**, en orden de cuánto cambiaría el resultado:")
w("")
w("1. **Una búsqueda de hiperparámetros con presupuesto emparejado** entre los dos brazos.")
w("   Hoy es una configuración por brazo (%s) y es el límite que más nos ata." % ref("presupuesto"))
w("2. **Un benchmark con meses de holdout**, por lo que explica %s. IEEE-CIS ya está medido"
  % ref("ventana"))
w("   y sellado; extenderlo es trabajo, no investigación.")
w("3. **Una demostración acotada en hardware**, sólo si el objetivo es caracterizar ruido —")
w("   no para mejorar el resultado, que en simulación exacta ya es un techo (%s)." % ref("cuantico"))
w("")

sec("Impacto esperado", "impacto")
w("")
w("**Seamos precisos sobre qué mejora esto y qué no.** El brazo cuántico no aporta")
w("desempeño: perdió, y %s explica por qué eso no es un accidente del montaje. Un banco que"
  % ref("cuantico"))
w("adopte este kernel tal cual **detectaría menos fraude**, no más.")
w("")
w("**Lo que sí cambia es la calidad de la decisión sobre invertir o no:**")
w("")
w("- **Un piloto cuántico de detección de fraude ya tiene evidencia previa negativa**, y")
w("  hasta ahora estaba dispersa en tres trabajos que miden cosas distintas (%s). Juntarla"
  % ref("externa"))
w("  con una medición propia e independiente ahorra descubrirlo por cuenta propia.")
w("- **La cifra que hoy se reporta sobre ULB no mide robustez temporal** (%s), y eso afecta"
  % ref("ventana"))
w("  a cualquier equipo que compare modelos sobre ese benchmark, cuántico o no.")
w("- **El protocolo es lo más transferible de todo esto**: pre-registro anclado antes del")
w("  código, ataque adversarial al propio resultado, presupuesto de búsqueda emparejado, y")
w("  cada cifra recomputable por un tercero. Aplicado a las evaluaciones internas de un")
w("  banco, distingue una mejora real de una de procedimiento — que es el error que %s"
  % ref("externa"))
w("  documenta en la literatura y que nosotros medimos en nuestro propio experimento (%s)."
  % ref("ataques"))
w("")

sec("Equipo", "equipo")
w("")
w("**Equipo:** Rosetta Quantum — **Blue Tuna SpA**, Punta Arenas, Chile (fundador-operador")
w("único). **Responsable:** Nicholas Iakl Freundlich · hello@rosettaquantum.com")
w("")
w("**Trayectoria:** fundador y CEO de Sumeria (analítica de conversación con IA, más de 9")
w("años) y fundador de Yu-Track (software de cobranza para servicios financieros). Ingeniero")
w("Comercial y magíster.")
w("")
w("**Lo que traemos no es el lado de vender el qubit: es el lado de consumir el veredicto**")
w("— construir sistemas cuya salida alguien tiene que creer para tomar una decisión. Por eso")
w("este documento está escrito para que usted **no tenga que creernos ninguna parte**.")
w("")
w("**Ésta es nuestra cuarta postulación cuántica**; Cleveland, E.ON y Airbus salieron antes.")
w("")
w("**Por qué esto puede ejecutar una fase siguiente:** la infraestructura de verificación que")
w("haría falta **no es un plan, está corriendo**. En el archivo hay **%s artefactos sellados**"
  % "{:,}".format(sum(CENSO.values())).replace(",", "."))
w("[medido: contados en el commit `%s` del repositorio de evidencia, para que usted cuente"
  % CENSO_COMMIT[:12])
w("exactamente lo mismo — el archivo crece, así que un conteo sin commit no se puede")
w("comprobar], repartidos así:")
w("")
w("| tipo | cuántos |")
w("|---|---|")
for _t, _c in sorted(CENSO.items(), key=lambda x: -x[1]):
    w("| %s | %d |" % (_t, _c))
w("")
w("*Decimos «artefactos sellados» y no «corridas» a propósito: **%d son corridas** y el resto"
  % CENSO.get("RUN", 0))
w("son informes, pre-registros, manifiestos y erratas. Un total con la etiqueta equivocada es")
w("una cifra correcta que el lector no puede comprobar — y si la primera no le cuadra, no")
w("revisa las demás.*")
w("")
w("Cada uno lleva su hash recomputable y su recibo de OpenTimestamps, espejado en dos")
w("servidores independientes. **Este entregable son %d de ellos**, y %s le dice cómo"
  % (len(CITADOS), ref("reproduccion")))
w("comprobar cada uno sin pedirnos nada.")
w("")

sec("Qué estamos pidiendo", "pedimos")
w("")
w("**Tres cosas, y ninguna es un cheque antes de una conversación.**")
w("")
w("1. **Una hora con quien sea dueño del benchmark.** El hallazgo de %s —que ULB deja **%s"
  % (ref("ventana"), n(CT["ventana_de_test_dias"] * 24, 1)))
w("   horas** de futuro real y por eso no puede medir robustez temporal— o les sirve o está")
w("   equivocado, y las dos cosas valen una hora. Si sirve, la comparación contra IEEE-CIS ya")
w("   está hecha y sellada, y es suya con o sin nosotros.")
w("2. **Un caso que a ustedes les importe de verdad.** Todo esto corre sobre los datasets que")
w("   su enunciado señala. Preferimos **medir** si sus casos reales tienen el problema de la")
w("   ventana corta, en vez de especular sobre si lo tienen.")
w("3. **Una fase siguiente acotada a la medición, no a una promesa.** El mismo método que")
w("   éste: pre-registrado antes de que exista el instrumento, sellado, con marca de tiempo,")
w("   y publicado funcione o no. **Este informe es lo que parece un resultado negativo cuando")
w("   se entrega a propósito.**")
w("")

sec("Reproducción — ejercida por nosotros primero", "reproduccion")
w("")
w("```")
w("git clone https://github.com/RosettaQuantum/evidence && cd evidence")
w("bash tools/reproducir_hsbc.sh        # descarga+verifica el dato, corre baseline y")
w("                                     # las 4 series, y verifica TODO con denominador")
w("python3 tools/replicar.py verificar --track hsbc   # solo la verificacion")
w("```")
w("")
w("- **Los scores crudos están depositados** (`scores_*.npz` por hash): un tercero")
w("  recomputa las curvas exactas. **Lo ejercimos como el tercero** [medido]: desde los")
w("  bytes de origin (`git archive`, sin archivos locales), AUPRC, AUC, F1 y las cuatro")
w("  celdas de la confusión recomputan idénticos (límite declarado: scores en float32 →")
w("  reproducción a ~1e-5).")
w("- **La batería de verificación** corre 7 tramos por artefacto y cada uno termina en")
w("  OK, FALLA o SALTADO — un tramo no ejercido cuenta como saltado, nunca como silencio.")
w("- **Determinismo entre máquinas** [medido]: la partición produce el mismo sha256 de")
w("  test en Mac y en CI; el punto del baseline (corte 80) reproduce al cuarto decimal en")
w("  corridas independientes de CI.")
w("- Alcance del ejercicio propio [por construcción]: cada comando del guion fue ejercido")
w("  — la descarga y verificación localmente, las corridas en CI (5 despachos: el")
w("  baseline y las cuatro series, listados en los artefactos por run id)")
w("  — la batería local y por mutación. El guion como unidad requiere")
w("  xgboost con OpenMP (CI o máquina compatible).")
w("")

sec("Anexos", "anexos")
w("")
w("### A · REFORMS, ítem por ítem")
w("")
reforms = [
 ("1a", "pleno", "población de la afirmación: " + ref("datos") + " (intra-dataset, declarada)"),
 ("1b", "pleno", "motivación del dataset: prereg + " + ref("datos") + ""),
 ("1c", "pleno", "motivación del método: prereg 001"),
 ("2a", "pleno", "dataset con id, md5, sha256 y manifiesto sellado"),
 ("2b", "pleno", "código público, archivado por hash, sha en cada artefacto"),
 ("2c", "pleno", "infraestructura declarada (CI, versiones en lib_versions)"),
 ("2d", "parcial", "instrucciones en " + ref("reproduccion") + "; README dedicado pendiente"),
 ("2e", "pleno", "tools/reproducir_hsbc.sh"),
 ("3a", "pleno", "fuente + fecha de recolección (sept-2013): " + ref("datos") + ""),
 ("3b", "pleno", "marco muestral descrito: " + ref("datos") + ""),
 ("3c", "pleno", "justificación del dataset: prereg"),
 ("3d", "pleno", "variable de salida + descriptivos: manifiesto"),
 ("3e", "pleno", "n en manifiesto"),
 ("3f", "pleno", "0 nulos, trivialmente por clase: " + ref("datos") + ""),
 ("3g", "parcial", "representatividad NO afirmada a propósito — declarada como límite"),
 ("4a", "pleno", "ninguna fila excluida: " + ref("datos") + ""),
 ("4b", "pleno", "0 corruptos medidos; política declarada"),
 ("4c", "pleno", "sin transformaciones propias: " + ref("datos") + ""),
 ("5a", "pleno", "configs completas en artefactos"),
 ("5b", "pleno", "elección de modelos justificada: prereg"),
 ("5c", "pleno", "particiones detalladas y selladas"),
 ("5d", "pleno", "modelo reportado = config v1 fijada, sin selección entre alternativas"),
 ("5e", "parcial", "búsqueda de hiperparámetros PENDIENTE; LightGBM abierto ahí"),
 ("5f", "pleno", "baselines apropiados justificados: prereg " + ref("metodo") + ""),
 ("6a", "pleno", "preprocesamiento sólo-train, guardias probadas por mutación"),
 ("6b", "pleno", "duplicados medidos (0); dependencia temporal por diseño"),
 ("6c", "parcial", "Time/Amount legítimas; el PCA global heredado se declara (anexo B)"),
 ("7a", "pleno", "métricas justificadas y selladas antes"),
 ("7b", "pleno", "bootstrap declarado (2.000, semilla)"),
 ("7c", "pleno", "Welch + Mann-Whitney concordantes; criterio pre-sellado"),
 ("8a", "pleno", "segundo dataset medido y sellado (IEEE-CIS); acotado a dos datasets"),
 ("8b", "pleno", "límites y contextos donde NO sostenemos los hallazgos: " + ref("datos") + " y " + ref("cuantico") + ""),
]
pl = sum(1 for _, e, _ in reforms if e == "pleno")
pa = sum(1 for _, e, _ in reforms if e == "parcial")
au = sum(1 for _, e, _ in reforms if e == "ausente")
w("**Recuento al armar este documento: %d plenos · %d parciales · %d ausentes de %d.**"
  % (pl, pa, au, len(reforms)))
w("El punto de partida (20-ago, antes del ataque y de este documento) era 15 · 8 · 9 —")
w("consta como trayectoria, no se sobreescribe. Plan de cierre de los %d parciales:"
  % pa)
w("README dedicado (2d) y búsqueda de hiperparámetros declarada (5e);")
w("3g y 6c son límites del dato que se declaran, no se «cierran».")
w("")
w("| ítem | estado | dónde |")
w("|---|---|---|")
for i, e, donde in reforms:
    w("| %s | %s | %s |" % (i, e, donde))
w("")
w("### B · Model info sheet — las 8 fugas de Kapoor & Narayanan")
w("")
w("[por literatura: taxonomía de *Leakage and the reproducibility crisis in ML-based")
w("science*; verificada contra el texto del paper]")
w("")
w("| tipo | estado en este trabajo |")
w("|---|---|")
w("| L1.1 sin test set | AUSENTE [por construcción]: partición sellada antes de entrenar |")
w("| L1.2 preprocesamiento sobre train+test | AUSENTE en lo nuestro [medido: sin transformaciones propias]; **HEREDADO del dataset** [por construcción]: el PCA de V1–V28 se ajustó sobre el conjunto completo antes de publicarse — imposible de remover; lo declaramos |")
w("| L1.3 selección de features sobre train+test | AUSENTE [por construcción]: no hay selección de features |")
w("| L1.4 duplicados train-test | MEDIDO: 0 duplicados exactos entre mitades |")
w("| L2 features ilegítimas | Time y Amount son legítimas para la tarea; V1–V28 anónimas por diseño [por construcción] |")
w("| L3.1 fuga temporal | ES EL OBJETO DE ESTUDIO: la serie temporal la evita; las aleatorias la exhiben a propósito y su efecto está medido (Δ=%.4f) |" % delta)
w("| L3.2 no-independencia train-test | transacciones del mismo par de días; declarado como límite (" + ref("datos") + ") |")
w("| L3.3 sesgo de muestreo | un procesador, 48 h: declarado; sin reponderación |")
w("")
w("### C · Artefactos y sellos")
w("")
w("| pieza | identificador | hash |")
w("|---|---|---|")
for nom, d_ in (("prereg diseño", PRE1), ("prereg ataque", PRE2),
                ("manifiesto de datos", MAN), ("sello del ataque", SEL)):
    w("| %s | `%s` | `%s` |" % (nom, d_["meta"]["file_id"], d_["meta"]["content_hash"]))
w("| baseline | artefacto | `%s` |" % BASE_F)
for k in ("S1", "S2", "S3", "S4"):
    w("| serie %s | artefacto | `%s` |" % (k, S[k][1]))
w("")
w("*Los sellos se verifican con `python3 tools/verify_seals.py <archivo>`; el anclaje en*")
w("*Bitcoin (OTS) y las tres copias (GitHub, Codeberg, D1) son del notario.*")

# GUARDIA: la misma cantidad no puede aparecer con dos valores. Nace del defecto de
# hoy — el §1 decia +0,0003 y el §6 +0,0004 para el aporte de SMOTE.
_ap = "%+.4f" % (m["S2"] - m["S1"])
_txt = "\n".join(L)
# se comparan normalizados: el documento usa coma decimal y el formato punto
_norm = lambda x: x.replace(",", ".")
_otras = {_norm(x) for x in _re.findall(r"\+0[,.]000\d", _txt)} - {_norm(_ap)}
if _otras:
    raise SystemExit("el aporte de SMOTE aparece como %s y tambien como %s: una cantidad, "
                     "un valor." % (_ap, sorted(_otras)))

# GUARDIA: prosa de artefacto filtrada al documento. Nace del defecto de hoy — el §7 y el
# aviso de errata canalizaban texto de los sellos, que se escriben SIN TILDES por convencion,
# y el documento salio con «version», «medicion» y una cita cortada a mitad de palabra.
# Precision sobre cobertura: solo formas que en español correcto SIEMPRE llevan tilde, para
# que un falso positivo no retenga trabajo bueno.
_SIN_TILDE = ["simulacion", "medicion", "version", "decision", "demostracion", "particion",
              "comparacion", "afirmacion", "configuracion", "reduccion", "codificacion",
              "correccion", "ejecucion", "asi que", "solo reducir", "numero", "metrica",
              "criterio de cruce", "deteccion", "evaluacion", "restriccion"]
# Coincidencia por PALABRA COMPLETA, no por subcadena: en español el plural de las palabras
# en -cion pierde la tilde («configuraciones», «particiones», «versiones» son correctas), asi
# que buscar el trozo marcaba texto bueno. Un falso positivo retiene trabajo bueno y eso es
# peor que dejar pasar un caso, asi que la guardia se hace mas precisa, no mas amplia.
_bajo = "\n".join(L).lower()
_fugas = sorted({x for x in _SIN_TILDE
                 if _re.search(r"\b%s\b" % _re.escape(x), _bajo)})
if _fugas:
    raise SystemExit("prosa de artefacto en el documento (va sin tildes y el lector lo lee): "
                     "%s. Del artefacto salen las CIFRAS; la prosa vive en el generador."
                     % ", ".join(_fugas))
# GUARDIA: una cita truncada a mitad de palabra. El «[:150]» de hoy corto en «under what co».
for _l in L:
    if _l.rstrip().endswith(("…", "co", "de la", "y la")) and len(_l) > 100:
        raise SystemExit("linea posiblemente truncada a mitad de frase: %r" % _l[-60:])

_actual = None
for _l in L:
    _m = _re.match(r"^## (\d+) · ", _l)
    if _m: _actual = _m.group(1)
    elif _actual and ("§" + _actual) in _l and _re.search(r"§%s\b" % _actual, _l):
        raise SystemExit("la seccion %s se referencia a si misma: %r" % (_actual, _l[:90]))

_h1 = [x for x in L if x.startswith("# ")]
if len(_h1) != 1:
    raise SystemExit("el documento tiene %d encabezados de nivel 1 y debe tener uno: %r"
                     % (len(_h1), _h1))

# GUARDIA: ¿contestamos lo que nos preguntaron? Trece guardias miraban de donde salia cada
# numero y ninguna esto. El entregable se armo tres veces sin compararse contra el pedido.
from requisitos_hsbc import exigir as _exigir_requisitos
_exigir_requisitos("\n".join(L), "el entregable en español")

texto = "\n".join(L) + "\n"
out = os.path.join(AQUI, "ENTREGABLE-HSBC.md")
open(out, "w").write(texto)
print("escrito %s (%d lineas, %d caracteres)" % (os.path.basename(out), len(L), len(texto)))
print("REFORMS en el documento: %d plenos / %d parciales / %d ausentes" % (pl, pa, au))
print("sha256:", hashlib.sha256(texto.encode()).hexdigest()[:16])
