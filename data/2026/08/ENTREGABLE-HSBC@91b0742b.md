# Cuando el protocolo decide el número: pre-registro anclado, ataque adversarial y un negativo cuántico que sobrevive a sus propios controles

**Rosetta Quantum · track HSBC del 2026 Global Quantum + AI Challenge · borrador para
aprobación de Nicholas — NO publicado**

> Toda cifra de este documento se lee de un artefacto sellado al momento de armarlo;
> ninguna se tipea. Cada afirmación lleva una de tres etiquetas: **[medido]** (nuestro
> instrumento lo produjo y el artefacto permite recomputarlo), **[por construcción]**
> (se deriva de cómo está hecho el objeto), **[por literatura]** (lo sostiene una
> fuente citada). Lo que no tiene etiqueta, no entró.

## 1 · Resumen

Construimos un baseline clásico de detección de fraude sobre datos públicos, con la
pregunta y el protocolo **sellados y commiteados antes de escribir el código** (y
anclados en Bitcoin después, por el notario). Después lo
atacamos: repetimos la medición bajo el protocolo que usa la literatura y bajo tres
variantes diseñadas para matar nuestro propio resultado, con los desenlaces posibles
escritos y sellados antes de correr. Salió esto: nuestra implementación **reproduce los
números publicados cuando usa el protocolo publicado** [medido]; la elección de
partición mueve la métrica principal en ~0,07 [medido]; el sobremuestreo SMOTE, del que
la literatura depende, **aporta +0,0004 cuando se aplica bien** [medido] — y cuando se
aplica en el orden defectuoso común, **la métrica satura en 1,0000 con cualquier
semilla** [medido]: perfección reportable con cualquier modelo. No reclamamos novedad
científica — el fenómeno de fondo está taxonomizado [por literatura: Kapoor & Narayanan,
*Leakage and the reproducibility crisis in ML-based science*, Patterns 2023]. Lo que
ofrecemos es la máquina que lo mide con pre-registro verificable y recomputación por
terceros.

**Y después corrimos el brazo cuántico, que era la razón de ser del track.** Un kernel de
fidelidad en simulación exacta, contra el mismo clásico, sobre el mismo test comprobado
por hash. **Perdió**: 0,2575 contra 0,800822, con el intervalo entero por debajo [medido] (§8).
Lo que hace que ese negativo valga algo no es haberlo medido —eso es el mínimo— sino lo
que hicimos después: **le dimos al clásico exactamente el mismo handicap** que el
protocolo le impone al cuántico, y el clásico llegó a 0,7460 con su intervalo solapando el
del basal [medido]. El handicap era real **y no explica el resultado**. Además adoptamos
contra nosotros mismos la guardia de presupuesto de búsqueda (§10) y verificamos la
evidencia externa abriéndola, no citándola de oído (§11). Un banco que hoy evalúa un
piloto cuántico de fraude puede leer acá qué se midió, con qué protocolo, y qué sigue
sin saberse.

## 2 · Resultados contra lo que ustedes piden

Esta sección existe para que usted **no tenga que buscar** si cumplimos. Cada fila cita el
enunciado y dice dónde está la respuesta.

Las **métricas del §4.1 para los dos brazos**, con precision, recall y matriz de
confusión completa, están en §6 — esta sección no las repite: las señala.

### Las tres salidas del §5.2

| pedido, textual | dónde está |
|---|---|
| *«Fraud Probability — Float [0, 1]»* | archivo 2 del paquete, columna `fraud_probability`; rango [0,0293 – 1,0000] |
| *«Binary Prediction — Integer {0, 1}»* | archivo 2, columna `binary_prediction`; 18 positivos |
| *«Feature Attribution — contribution of features to each prediction»* | archivo 2, 8 columnas `attribution_*`, **una fila por transacción** |

### Lo demás que el enunciado pide, y dónde

| pedido | § | dónde |
|---|---|---|
| *«encoding strategy, and circuit design choices»* | 5.2 | §8 |
| *«comparison with at least one classical baseline»* | 5.2 | §6 y §8 |
| *«discussion of any observed quantum improvement and under what conditions»* | 5.2 | §8 |
| *«handling of class imbalance should be documented»* | 5.3 | §8 |
| *«feature selection is expected for quantum approaches»* | 5.3 | §8 |
| *«qubit count and circuit depth»* | 5.3 | §8, tabla del circuito |
| *«feature attribution or importance analysis is valued»* | 5.3 | §8, local y por permutación |
| *«total number of samples used for quantum execution must be explicitly stated»* | 4.2 | §8 |
| *«subsampling must be performed using stratified sampling»* | 4.2 | §8 |
| *«benchmark against these published results»* | 4.1 | §6 |
| *«error mitigation techniques»* | 5.3 | no aplica: no se ejecutó hardware (§8) |
| *«comparison of simulator vs. hardware results»* | 5.3 | no aplica, misma razón |

**Y una que el enunciado NO pide y le entregamos igual**, porque es lo que más le sirve a
un banco que hoy evalúa un piloto: §9.

## 3 · La pregunta y su pre-registro

La pregunta —¿qué aporta un modelo cuántico o cuántico-inspirado contra un clásico
afinado, con protocolo fijado antes de mirar?— quedó sellada en `RQ-PREREG-HSBC-001`
(`sha256:b04f214fae845b1c`), commit `72dcbf2`, **antes de descargar un solo dato** [por construcción: es
una propiedad del historial de git, no una afirmación nuestra]. El ataque adversarial
se pre-registró aparte en `RQ-PREREG-HSBC-002-ATAQUE` (`sha256:87c187b48627d529`),
**con sus tres desenlaces escritos antes de correr, incluido el que nos dejaba mal**.
El brazo cuántico tiene pre-registro propio, `RQ-PREREG-HSBC-003-CUANTICO` (`sha256:e15b1808c03c29a8`),
y sus resultados están en §8.

> **Aviso al lector: el pre-registro del brazo cuántico tiene una errata sellada.**
> `RQ-ERRATA-PREREG-HSBC-003` (`sha256:3b46354aaf213c16`) retracta una afirmación
> del original: la de que cambiar de proveedor no movería el costo. **Es falsa**, y la
> tabla del propio artefacto original ya la desmentía: el mismo trabajo cuesta USD 3.425
> en Rigetti Cepheus y USD 83.000 en IonQ Forte — un factor de 24,2 [medido].
> **El original no se reescribe**: su archivo, su hash y su ancla quedan intactos, y la
> corrección viaja como documento aparte. Si usted abre el pre-registro se va a encontrar
> con esa frase, y queda avisado acá: mandarlo a leer algo que sabemos incorrecto sin
> decírselo sería el defecto, no el descuido. **Lo que la errata NO retracta** es la
> decisión operativa — la demostración acotada sigue siendo la elegida y el gasto
> autorizado sigue en US$0.

## 4 · Datos, con sus límites medidos

**Fuente** [medido]: ULB *creditcard* vía OpenML (id 1597, v1), md5 medido = declarado
por la fuente (`178bcf9bb1f3…`), sha256 `fdaf12730dc1fc42…`,
fijado en el manifiesto sellado `RQ-DATA-HSBC-ULB-001` **antes del primer entrenamiento**.
**Censo** [medido]: 284.807 filas, 492 fraudes (0.173 %), 0 valores nulos (trivialmente 0 en
ambas clases). Ninguna fila fue excluida; las features se usan tal cual llegan, sin
transformación nuestra [por construcción].

**Los límites, medidos y no estimados:**

- **La ventana total son 48,00 horas exactas** [medido: rango Time 0–172.792 s] — dos
  días de septiembre de 2013 [por literatura: documentación del dataset]. Nuestra
  partición temporal 80/20 deja **7,65 horas** de test: llamar a eso «el futuro» sería
  más de lo que el dato sostiene, y no lo llamamos así.
- **La clase positiva no está pareja en el tiempo** [medido]: la tasa de fraude varía
  5× entre bloques de 8 h (0,46 % nocturno contra 0,09 %); el test temporal queda con
  75 de los 492 fraudes (15,2 %).
- **Las features V1–V28 son componentes de un PCA que los autores del dataset ajustaron
  sobre el conjunto completo** [por construcción: se publicó ya transformado, así que
  nadie puede re-ajustarlo sólo sobre su train]. Es PCA no supervisado —no vio
  etiquetas—, de magnitud distinta a las fugas por sobremuestreo; **nosotros lo
  declaramos** (anexo B, L1.2-heredado).
- **Marco muestral**: transacciones de tarjetahabientes europeos de un procesador, dos
  días [por literatura]. **No afirmamos que represente el fraude en general**: los
  hallazgos de este documento son intra-dataset y por construcción, no extrapolaciones.

## 5 · Método

**Partición** [medido, sellada en el prereg]: temporal 80/20 por la columna `Time` —
train 227.845 filas (417 fraudes), test 56.962 filas (75 fraudes), sha256 del test declarado en
el artefacto (`88f43ccb6ffcd6ae…`) y **bit-idéntico entre dos máquinas distintas** [medido: Mac
local y runner de CI produjeron el mismo hash]. Duplicados exactos entre mitades:
0 [medido].

**Métrica que manda** [sellada antes]: AUPRC — con prevalencia 0,17 % el AUC-ROC es
ópticamente generoso. AUC-ROC, F1 y matriz de confusión se reportan siempre al lado.

**Baseline**: XGBoost (config declarada en el artefacto `@2072bc53`). **LightGBM está
ABIERTO**: nuestra configuración v1 lo rompe (AUPRC 0.0058, 9.624 falsos positivos) — es
un defecto de configuración nuestra, no del método, y **no entra como baseline afinado
hasta pasar la búsqueda declarada** (pendiente; si al final no entra, este párrafo se
actualiza con el porqué, no desaparece).

**Guardias, todas falla-cerrado y probadas por mutación** [medido: tres artefactos
deliberadamente rotos —dato ajeno al manifiesto, harness sin procedencia, métrica que
no calza con los scores— hacen gritar la batería con código de salida 1; el caso base
pasa]: el dato se verifica contra el manifiesto antes de entrenar; ninguna fila del
test participa en entrenamiento; la estratificación de cada submuestra se mide, no se
asume; cada artefacto lleva el sha256 del harness que lo produjo.

## 6 · Resultados del brazo clásico

**Baseline XGBoost sobre partición temporal** [medido, artefacto `@2072bc53`]:

| métrica | valor | IC95 bootstrap (2.000, semilla 42) |
|---|---|---|
| AUPRC | **0.8008** | [0.705 – 0.883] |
| AUC-ROC | 0.9878 | [0.977 – 0.996] |
| F1 @ 0,5 | 0.8235 | tp=56 fp=5 fn=19 |

Contexto de validación [por literatura: los baselines que el statement del challenge
tabula]: el stacking publicado sobre este dataset reporta AUC-ROC 0,9887; el nuestro da
0.9878 sobre partición temporal. **El intervalo de nuestro AUPRC contiene el 0,871
publicado, así que no afirmamos diferencia contra ese número** — la comparación
honesta es intra-implementación y viene en el §7.

### Las métricas que pide el §4.1, para los dos brazos

| métrica | clásico (xgboost) | kernel cuántico |
|---|---|---|
| **AUC-ROC** | 0,987796 | 0,743759 |
| **AUPRC** | **0,800822** [0,7054 – 0,8828] | **0,257453** [0,1546 – 0,3691] |
| **F1** | 0,8235 | 0,3226 |
| **Precision** | 0,9180 | 0,8333 |
| **Recall** | 0,7467 | 0,2000 |
| **matriz de confusión** | tp=56 fp=5 fn=19 tn=56882 | tp=15 fp=3 fn=60 tn=56884 |

*El umbral del brazo clásico es 0,5 sobre una probabilidad. El del cuántico se eligió
**en el train** sobre la probabilidad calibrada, nunca mirando el test; el porqué está en
§8. Los dos se evalúan sobre el mismo test, comprobado por hash.*

## 7 · Los ataques al propio resultado

Cuatro series, 65 entrenamientos, **el mismo modelo y el mismo dato en todas** —
lo que cambia es el protocolo [medido, sello `RQ-EXP-HSBC-ATAQUE-001`]:

| serie | protocolo | n | AUPRC media ± sd |
|---|---|---|---|
| S1 | aleatorio estratificado 80/20, sin SMOTE | 20 | 0.8542 ± 0.0324 |
| S2 | aleatorio + SMOTE **dentro** del train | 20 | **0.8545** ± 0.0306 |
| S3 | aleatorio + SMOTE **antes** del split (defectuoso a propósito) | 20 | 1.0000 ± 0.00001 |
| S4 | temporal, cortes 70–90 % | 5 | 0.7829 ± 0.0295 |

**Qué sobrevivió y qué no, contra los desenlaces sellados antes:**

1. **La implementación quedó validada** [medido]: S2 —el protocolo de la literatura,
   bien aplicado— cae dentro de la banda pre-fijada [0,841–0,901] construida desde los
   números publicados. Nuestra diferencia temporal-vs-aleatorio no es un artefacto de
   implementación.
2. **El efecto de partición existe bajo su criterio pre-sellado, con margen estrecho y
   se dice que es estrecho** [medido]: Δ = media(S1) − media(S4) = 0.0713; Welch
   p = 0.002451 y Mann-Whitney p = 0.001092 (concuerdan); la segunda condición —Δ > 2× ruido
   bootstrap (0.0702)— **se cumple por el 1,5 % del umbral: una realización distinta
   del ruido podría no cumplirla.** El lector decide con el margen a la vista.
3. **El hueco que anticipamos no se materializó y consta igual** [por construcción]:
   antes de correr advertimos que si S2 quedaba bajo banda y S3 la sobrepasaba, los
   desenlaces sellados tenían una región sin cubrir. S2 cayó en banda y el desenlace
   disparó sin ambigüedad — pero un pre-registro que anticipa sus propios huecos vale
   más que uno donde todo calza de casualidad.
4. **La sensibilidad al corte es suave** [medido]: AUPRC temporal 0,81→0,74 entre
   cortes 70 % y 90 %; el efecto no depende de un corte único. El corte 90 queda con
   22 fraudes en test y es el más ruidoso.

**El resultado central del ataque — y el titular de este documento:**

> **Aplicar el sobremuestreo antes de separar el conjunto de prueba no infla la
> métrica: la destruye.** AUPRC = 1,0000 en las 20 semillas [medido]. El test queda
> con 50 % de positivos sintéticos —contra 0,172 % reales— y con gemelos sintéticos
> de filas de entrenamiento [por construcción]. **Quien evalúe así puede reportar
> perfección con cualquier modelo**, y por lo tanto un número publicado bajo ese
> protocolo no informa sobre el modelo. Ningún valor de S3 se cita jamás como
> rendimiento — es aritmética del protocolo, no calidad.

Su complemento [medido]: cuando SMOTE se aplica **bien**, aporta +0,0004 sobre el
aleatorio puro (0.8545 vs 0.8542). En este dataset y esta implementación, **la partición
hace todo el trabajo**.

## 8 · El brazo cuántico: el negativo, y por qué no fue el handicap

El pre-registro del brazo cuántico (`RQ-PREREG-HSBC-003-CUANTICO`, `sha256:e15b1808c03c29a8`)
fijó el criterio **antes de correr**: AUPRC sobre el test completo, IC95 por bootstrap de
2.000 remuestreos con semilla 42, y **no hay ventaja si el intervalo se solapa con el del
clásico o queda por debajo**. También declaró de antemano que **los dos desenlaces son
entregables**. Salió el que nos deja mal, y por eso está acá.

| brazo | AUPRC | IC95 |
|---|---|---|
| clásico sellado (`RQ-EXP-HSBC-BASE-001`) | **0,800822** | [0,7054 – 0,8828] |
| kernel cuántico de fidelidad, simulación exacta | **0,257453** | [0,1546 – 0,3691] |

**Cruce de ventaja cuántica: 0** [medido]. El intervalo del brazo cuántico queda entero
por debajo. Los dos brazos se midieron sobre **el mismo test, comprobado por hash**
(`88f43ccb6ffcd6ae…`) y con el mismo remuestreo: una comparación con distinto
bootstrap no sería una comparación, así que el sellador **aborta** si los dos hashes no
coinciden [por construcción].

### El handicap era real, y lo medimos en vez de invocarlo

El enunciado exige muestreo **estratificado**. Al 0,183 % de fraude, un soporte de 20.000 puntos
deja **37 positivos**, contra los 417 con que se entrenó el clásico. Es una desventaja
dura y asimétrica, y es la primera explicación que cualquiera daría — nosotros incluidos.

**Así que le dimos al clásico exactamente el mismo handicap** [medido]: la misma submuestra
de 20.000 puntos, las mismas 8 variables, los mismos 37 fraudes.

| control (no pre-registrado) | AUPRC | IC95 | contra el basal |
|---|---|---|---|
| xgboost, misma muestra y mismas variables | **0,7460** | [0,6429 – 0,8429] | se solapa |
| kernel cuántico con los 417 fraudes (no estratificado) | 0,4887 | [0,3699 – 0,5979] | por debajo |
| RBF, misma muestra y mismas variables | 0,1004 | [0,0673 – 0,1575] | por debajo |

Un xgboost con la muestra mutilada llega a **0,7460**, y su intervalo **se solapa con el del
basal**: el muestreo estratificado le costó al método clásico algo que ni siquiera es
detectable. Y quitándole el handicap por completo al brazo cuántico —los 417 fraudes— sube
a 0,4887 y **sigue por debajo**. El handicap existe y no explica el resultado.

Sin esta medición, «el kernel cuántico pierde» y «le dimos 37 positivos» son
indistinguibles, y publicar la primera sería un reporte falso aunque la cifra fuera
correcta.

### Tampoco afirmamos ganarle al RBF

Con el mismo dato, las mismas variables y el mismo clasificador, el kernel cuántico da 0,2575
y el RBF 0,1004. Se ve como una victoria hasta que se miran los intervalos: [0,1546 – 0,3691] contra [0,0673 – 0,1575],
**se tocan**. Por la misma regla con que negamos la ventaja cuántica frente al basal,
tampoco podemos afirmar que le gane al RBF [medido]. La regla se aplica contra nosotros o
no es una regla.

### Simulación exacta: no es una limitación que excusar, es lo que el enunciado propone

El propio enunciado del desafío dice, textual, que *«full end-to-end model training or
inference on quantum hardware is not expected nor required»*, y **recomienda
expresamente** prototipar en los simuladores administrados de Amazon Braket antes de
mandar trabajos a hardware [por literatura: enunciado oficial, §5.3]. Correr en
simulación exacta con gasto US$0 es la vía que el desafío propone, no un atajo nuestro.

**Y hay una cláusula cuyo alcance conviene declarar en vez de dar por supuesto.** La
exigencia de submuestreo estratificado aparece anidada bajo *«Teams using hardware are
encouraged to:»*. **Nosotros no corrimos en hardware**, así que en lectura llana esa
cláusula no nos obliga — y sin embargo la cumplimos, lo que nos costó quedarnos con 37
fraudes en vez de 417. **No forzamos la lectura que nos conviene**: reportamos el brazo
pre-registrado *con* la restricción (0,2575) y el control sin ella (0,4887), y **los dos quedan
por debajo del basal** [medido]. La conclusión no depende de cómo se lea la regla.

### Estrategia de codificación y diseño del circuito

El §5.2 del enunciado pide *«description of quantum approach, encoding strategy, and
circuit design choices»*. Esto es esa descripción.

**De 30 columnas a 8 qubits.** El enunciado dice que la selección de variables *«is
expected for quantum approaches»*, porque codificar cientos de columnas en un circuito no
es practicable hoy. Elegimos las 8 de mayor |correlación de Pearson con la etiqueta|,
**calculada sólo sobre el train** —mirarlo en el test sería la fuga que la partición
temporal viene a impedir—: V3, V7, V10, V11, V12, V14, V16, V17 [medido].

**De número real a ángulo.** Cada variable se estandariza con la media y la sigma del
train, se recorta a ±3 σ y se lleva a `[0, π]`. Los límites salen del train, no del
conjunto completo. Un qubit por variable.

**El mapa.** `ZZFeatureMap` (Havlíček et al., *Nature* 567, 2019) con `reps = 2` y
entrelazamiento completo por pares — el mapa canónico de la literatura, no uno nuestro. La
convención de fases **no se dedujo de memoria: se verificó contra el objeto que construye
qiskit** antes de usarla, y ahí apareció un defecto real que sólo esa comprobación podía
ver (§17).

**El circuito, contado y no descrito** [medido: construido con los parámetros que el
sello declara y medido con qiskit al armar este documento]:

| propiedad | valor |
|---|---|
| qubits | 8 |
| profundidad | 67 |
| puertas totales | 200 (112 cx, 88 u) |
| puertas de dos qubits | 112 |
| pares entrelazados | 28 — exige conectividad **todos con todos** |
| profundidad transpilado a IBM (rz, sx, x, cx) | 71 |
| profundidad transpilado a Rigetti (rz, rx, cz) | 206 |

*Medido sobre el circuito descompuesto **una** vez a puertas elementales y transpilado
desde ahí con `optimization_level=1` y semilla fija. El procedimiento se declara porque
la profundidad depende de él: descomponer dos veces antes de transpilar da otra cifra, y
entonces el número sería una propiedad de cómo medimos y no del circuito.*

**Y lo que eso significa para hardware cercano, dicho sin adornos** [por construcción]:
112 puertas de dos qubits sobre 8 qubits, con **28 pares que exigen conectividad todos-con-todos**, es un circuito caro para los dispositivos de hoy. En una topología con conectividad limitada el transpilador inserta intercambios y la profundidad sube: se ve ya al pasar de 71 en la base más favorable a 206 en la otra.

**Y esto es el circuito por cada par (transacción, punto de soporte) del kernel**, no un
circuito suelto: ahí es donde el costo se vuelve prohibitivo. El pre-registro lo tiene
calculado desde la tarifa publicada de Braket: **USD 39.018.970** para el test completo [medido],
y por eso no se corrió en hardware — con autorización de gasto US$0.

### Cómo manejamos el desbalance de clases

El §5.3 dice que el manejo del desbalance *«should be documented»*. Lo hicimos de cuatro
formas distintas y ninguna es un remuestreo sintético:

- **Ponderación en la pérdida.** El brazo clásico usa `scale_pos_weight` = 545,39, que es la
  razón negativos/positivos del train. El brazo cuántico usa `class_weight='balanced'`.
- **Submuestreo estratificado** para el soporte cuántico, que **preserva** la razón de
  fraude en vez de corregirla: 37 fraudes en 20.000 puntos, la misma tasa del train.
- **El umbral se elige en el train**, no en el test, y se reporta con su matriz completa
  en vez de un solo número.
- **La métrica principal es AUPRC**, que el propio enunciado recomienda para datos
  desbalanceados, y no la exactitud — que con 0,183 % de fraude premia predecir «no» siempre.

**Lo que NO hicimos, y es deliberado:** no aplicamos SMOTE ni ningún sobremuestreo en el
resultado principal. §7 muestra por qué: aplicado bien aporta +0,0004, y aplicado en el orden
defectuoso común **satura la métrica en 1,0000 con cualquier semilla**.

### Latencia y tiempo de entrenamiento

El enunciado los lista como *good-to-have*. Los tenemos medidos [medido]:

| | brazo cuántico (simulación exacta) | xgboost clásico |
|---|---|---|
| tiempo total de la corrida, extremo a extremo | 45,2 s | 63,4 s |

**Lo que NO reportamos, y por qué.** Una latencia de inferencia por transacción: el
tiempo de ese tramo quedó en la consola y **no viaja en ningún artefacto**, así que
copiarlo acá sería una cifra sin procedencia. Se mide y se sella, o no se reporta.

**Y aunque la tuviéramos, no sería la de un despliegue cuántico** [por
construcción]. El atajo del statevector existe **porque** se simula: en un dispositivo
real ese objeto no existe y vuelven las evaluaciones par a par del kernel. La cifra de
arriba dice cuánto cuesta obtener el modelo por esta vía, no cuánto costaría en hardware.

### El modelo no estaba inerte: usa las ocho variables y pierde igual

La objeción natural a un negativo es que la implementación estuviera rota o ignorando sus
entradas. **Se midió.** Barajamos cada variable en el test y medimos cuánto cae el AUPRC,
con 10 repeticiones por variable para que la caída tenga intervalo y no sea una corrida
suelta [medido].

| variable | caída de AUPRC al barajarla | AUPRC que queda | IC95 |
|---|---|---|---|
| V17 | 0,2444 | 0,0131 | [0,2223 – 0,2527] |
| V12 | 0,2361 | 0,0213 | [0,2185 – 0,2476] |
| V14 | 0,2301 | 0,0273 | [0,2135 – 0,2460] |
| V11 | 0,2232 | 0,0343 | [0,1872 – 0,2484] |
| V10 | 0,2202 | 0,0373 | [0,1781 – 0,2383] |
| V16 | 0,1999 | 0,0576 | [0,1668 – 0,2265] |
| V3 | 0,1311 | 0,1263 | [0,0814 – 0,1828] |
| V7 | 0,1284 | 0,1290 | [0,0609 – 0,1656] |

**8 de 8 variables tienen una caída cuyo intervalo no cruza cero** [medido]. Barajar
una sola de ellas derrumba el AUPRC hasta el orden de la prevalencia. **El modelo no está
inerte: extrae señal de todas sus entradas** — y aun usándola toda llega a 0,2575, mientras un
clásico **con las mismas ocho variables y la misma muestra** llega a 0,7460.

Eso **cierra la salida más fácil para un lector escéptico** y hace el negativo más fuerte,
no más débil. Y coincide con la atribución local, que es otra medición: las contribuciones
por transacción son casi uniformes entre variables. Ninguna domina; todas aportan.

### Las tres salidas que el enunciado exige

El §5.2 del enunciado pide tres artefactos y el brazo sellado producía uno. Están en
`RQ-EXP-HSBC-Q-002` [medido]:

| salida pedida | qué entregamos |
|---|---|
| *Fraud Probability*, `Float [0,1]` | probabilidad calibrada, rango [0,0293 – 1,0000] |
| *Binary Prediction*, `Integer {0,1}` | umbral elegido en el **train**: 18 positivos, Precision 0,833, Recall 0,200, F1 0,323 |
| *Feature Attribution*, contribución **por predicción** | matriz de 56.962 × 8: un vector de contribuciones por cada transacción del test |

**Y el conteo que el enunciado exige textualmente** —*«the total number of samples used
for quantum execution must be explicitly stated in the submission»*— con esas palabras:
soporte estratificado **20.000** (37 fraudes), calibración **20.000**, test **56.962**, **total 96.962 muestras** con ejecución cuántica, sobre **8 qubits** [medido].

> **La probabilidad calibrada no es cosmética, y lo encontramos nosotros antes de
> entregar.** Al comprobar si cumplíamos el `Float [0,1]` que el enunciado pide, vimos que
> nuestros scores eran **márgenes** de la función de decisión, de -1,3810 a 1,0207. El AUPRC y el
> AUC no lo notan —son de ranking— pero el «umbral 0,5» del artefacto original aplicaba
> 0,5 a esa escala, y de ahí salía una Precision de 1,000 con **3** positivos predichos de
> 56.962: el punto ultraconservador de una escala arbitraria, no una propiedad del método.
> Está corregido en la errata `RQ-ERRATA-EXP-HSBC-Q-001`, que **no reescribe el original**
> y deja el veredicto intacto. Con el umbral elegido en el train, Precision 0,833 y Recall 0,200.

### Qué NO responde esta medición

Nada sobre hardware. El brazo corrió en **simulación exacta**, con gasto US$0 y sin
enviar un solo circuito a un dispositivo: un statevector no tiene ruido, ni error de
lectura, ni decoherencia, ni error de transpilación. Por eso este número es un **techo**
[por construcción]: con el mismo mapa, la versión ruidosa no puede superar a la exacta.
Que no haya ventaja acá **cierra el caso**; que la hubiera **no** la probaría en
hardware. Esa asimetría es la razón de que una simulación baste para un negativo y no
bastaría para un positivo.

### Ruido y mitigación: qué aplicaría, y por qué acá no hizo falta

El §4.2 valora documentar las consideraciones de hardware —ruido, mitigación de error, y
la comparación contra el simulador—. Lo decimos con precisión, incluido el hecho de que
**no corrimos hardware**, que es lo que hace que esta sección sea corta y honesta en vez
de larga y especulativa.

**Nuestra simulación es exacta, no ruidosa.** Un statevector no tiene error de lectura ni
decoherencia, así que **no hay nada que mitigar**: aplicar mitigación de error a una
simulación exacta no mejoraría nada, porque no hay error que corregir. El enunciado
recomienda prototipar en los simuladores administrados de Braket (SV1, TN1, DM1) antes de
ir a hardware; nosotros nos quedamos un paso antes, en simulación exacta local, con gasto
US$0.

**Lo que aplicaría si se ejecutara en un dispositivo**, y cuál es el orden de importancia
para *este* circuito en particular [por construcción]:

- **Mitigación de error de lectura**, primero: el kernel de fidelidad se estima de la
  frecuencia del resultado `|0…0⟩`, así que un sesgo en la lectura entra **directo** en
  cada entrada de la matriz. Es el error que más nos afectaría.
- **Extrapolación a ruido cero (ZNE)**, después: con 112 puertas de dos qubits el error de
  compuerta acumulado domina, y ZNE es lo que se usa para esa clase de circuito.
- **Y el que ninguna técnica arregla**: `DM1`, el simulador de matriz de densidad de
  Braket, permite prototipar con ruido **antes** de gastar en hardware. Ése sería el
  paso siguiente natural, y es barato comparado con la QPU.

**La comparación simulador contra hardware no la tenemos, y no la insinuamos.** Es una de
las métricas que el enunciado lista como deseables y **la nuestra está vacía**: para
llenarla hay que ejecutar, y el pre-registro autoriza gasto US$0. Lo que sí podemos decir
es la dirección: nuestro número es un **techo**, así que la versión ruidosa quedaría por
debajo — y ya estamos por debajo del clásico.

## 9 · Lo que nadie le va a decir: el dataset recomendado no puede contestar la pregunta del enunciado

Esto no nos lo pidieron. Lo entregamos porque es lo que más le sirve a un banco que hoy
está evaluando un piloto, y porque lo tenemos **medido y sellado**, no opinado.

**ULB, el dataset que el enunciado recomienda, tiene 48 horas de datos en total.** Nuestra
partición temporal —la que el pre-registro fija— deja **7,7 horas de test** [medido: `ventana_de_test_dias` = 0,32 en `RQ-EXP-HSBC-Q-001`].

Un modelo evaluado ahí está ajustado a **una foto de dos días de septiembre de 2013**. No
hay forma de saber si generaliza a la semana siguiente, porque **no hay semana siguiente
en los datos**. No es un defecto de quien eligió el dataset: es una propiedad del dataset.

**Y tenemos con qué compararlo.** El otro benchmark del track, IEEE-CIS, lo medimos con la
misma regla y está sellado en `RQ-EXP-HSBC-IEEE-001`:

| | ULB | IEEE-CIS |
|---|---|---|
| ventana de test | **7,7 h** | **41,88 días** |
| razón entre ambas | — | **130,9×** más futuro real |
| tasa de fraude | 0,183 % | 3,514 % (**19× más frecuente**) |
| mejor AUPRC | 0,800822 | 0,543791 |

**Lea esas dos últimas filas juntas.** En IEEE-CIS el fraude es **19 veces más frecuente** —o sea, el problema debería ser más fácil— **y aun así se predice peor**: 0,5438 contra 0,8008
[medido]. Que la clase minoritaria sea más abundante y el resultado empeore es
exactamente lo que uno esperaría si el número alto de ULB viene de **la ventana corta** y
no de que el problema sea fácil.

**Qué significa para usted, en una frase:** el número que su equipo le reporta sobre ULB
**no está midiendo robustez temporal**, porque en ULB no hay tiempo suficiente para
medirla. Un benchmark con meses de holdout le va a dar peor — y va a ser más parecido a
lo que le pasa en producción, donde el fraude cambia de forma entre un trimestre y el
siguiente.

**Lo que NO afirmamos** [por construcción]: que ULB no sirva, ni que el enunciado
estuviera equivocado en recomendarlo. Sirve para comparar implementaciones entre sí —es
lo que hacemos en §7— y para eso la ventana corta no molesta. Lo que no puede hacer es
responder «¿esto aguanta el paso del tiempo?», y ésa es la pregunta que un despliegue
hace. **Son dos datasets, no una población**: no extrapolamos más allá de estos dos.

## 10 · Presupuesto de búsqueda: la guardia que adoptamos contra nosotros mismos

De arXiv:2608.15718 [por literatura] tomamos una guardia y la incorporamos al protocolo, porque ataca
la forma más barata de engañarse con un resultado cuántico: **elegir el modelo cuántico
entre más configuraciones que el clásico**. En ese trabajo, la única ventaja
estadísticamente significativa que observaron **quedó explicada por entero por el número
de configuraciones probadas** — dejó de ser un hallazgo y pasó a ser un artefacto del
procedimiento.

**Nuestro presupuesto de búsqueda, medido: una configuración por brazo, en los dos**
[medido]. No hay `GridSearchCV`, `RandomizedSearchCV`, `optuna` ni `param_grid` en el
instrumento: los hiperparámetros de los dos brazos están fijos en el código publicado
(`code/hsbc_harness@a27348cb.py`), y se comprueba leyéndolo. Nuestro negativo no puede ser un
artefacto del presupuesto de búsqueda, porque no hubo búsqueda.

**Y el reverso, que corre en contra nuestra y va dicho igual**: el mismo trabajo reporta
que las elecciones ordinarias de hiperparámetros mueven el desempeño **considerablemente
más que el kernel cuántico**. Si nadie afinó nada, entonces nuestro `C = 1`, el mapa con
`reps = 2` y el escalado a `[0, π]` son exactamente esa clase de elección sin afinar.
**No podemos distinguir «el método no aporta» de «esta configuración no aporta»**, y una
búsqueda emparejada entre los dos brazos es trabajo pendiente, no resultado.

**Pero ese caveat es más chico de lo que nosotros mismos lo habíamos hecho, y decirlo
también corresponde.** `arXiv:2503.05602` muestra que el ajuste óptimo del ancho de banda **acerca**
el kernel cuántico al RBF (§11). Si eso es así, afinar no nos habría alejado del clásico:
nos habría empujado **hacia** él. El caveat sigue en pie —no estamos en ese régimen
porque no afinamos— pero deja de ser «quizá con otra configuración habría ganado» y pasa
a ser «la dirección en que la literatura dice que se mueve al afinar es hacia el kernel
clásico, no lejos de él». **Un caveat inflado es otra forma de no decir lo que se sabe.**

## 11 · Lo que ya se sabía: triangulación en tres ejes

Nuestro resultado no llega a un terreno vacío. **Ninguno de los tres trabajos de abajo
replica nuestra medición** —somos ranking supervisado con AUPRC sobre fraude, y ninguno
es eso— y decirlo importa: presentarlos como réplicas sería la costura que este documento
existe para evitar. Lo que hacen es cerrar por tres lados distintos.

| fuente | eje | qué mide |
|---|---|---|
| `arXiv:2608.15718` | comparte **el dominio** (fraude de tarjeta) y cambia la tarea | clustering **no supervisado**, métrica ARI |
| `arXiv:2607.20168` | comparte **la forma de la tarea** (ranking supervisado) y cambia el dominio | retornos accionarios chinos (A-shares), métrica IC |
| `arXiv:2503.05602` | no compara nada cabeza a cabeza: explica **la causa** | mecanismo; no reporta cifra de efecto |

**`arXiv:2608.15718`** — *Quantum Kernel k-Means for Credit-Card Fraud Detection: A Controlled Benchmark on Real Transaction Data*, M. Faryad, 16 de agosto de 2026 [por literatura].

> We find no robust quantum advantage: the sign of the difference depends on register size, all effect sizes are below 0.013 ARI, and the single significant advantage we observe is fully explained by the number of configurations searched.

*(traducción nuestra: No encontramos ventaja cuántica robusta: el signo de la diferencia depende del tamaño del registro, todos los tamaños de efecto están por debajo de 0,013 ARI, y la única ventaja significativa que observamos queda explicada por entero por el número de configuraciones probadas.)*

**`arXiv:2607.20168`** — *Quantum Kernels and the Cross-Section of Stock Returns: Anatomy of a Vanishing Advantage*, J. Shen, 22 de julio de 2026 [por literatura].

> the fidelity kernel is indistinguishable from its RBF control (ΔIC = +0.005, p = 0.42)

*(traducción nuestra: el kernel de fidelidad es indistinguible de su control RBF.)*

**`arXiv:2503.05602`** — *On the similarity of bandwidth-tuned quantum kernels and classical kernels*, R. Flórez-Ablan, M. Roth y J. Schnabel, v3, 28 de julio de 2025 [por literatura].

> optimal bandwidth tuning results in QKs that closely resemble radial basis function (RBF) kernels, leading to a lack of quantum advantage over classical methods

*(traducción nuestra: el ajuste óptimo del ancho de banda produce kernels cuánticos que se parecen mucho a kernels RBF, lo que lleva a una ausencia de ventaja cuántica frente a los métodos clásicos.)*

**Los dos hallazgos que más nos tocan no son los titulares:**

- **La diferencia geométrica no predice nada.** `arXiv:2607.20168` reporta, textual, que
  *«the geometric difference, while large throughout (g ≫ 1), does not predict
  out-of-sample gains (ρ = −0.20)»*. Esa diferencia es **el diagnóstico estándar** con que
  se sostiene que un kernel cuántico es «suficientemente distinto» del clásico como para
  tener ventaja. Ahí es grande y **correlaciona negativamente** con la ganancia real. Es
  el contraejemplo publicado al argumento de «espacio exponencial ⇒ separa mejor».
- **Una evaluación mal montada fabrica la ventaja.** El mismo trabajo documenta que
  *«a 60-window evaluation on a universe screened with full-sample information makes the
  same quantum kernel appear dominant on stability criteria»*: información del futuro
  filtrándose y produciendo dominancia donde no la hay. **Es el mismo fenómeno que
  medimos nosotros** en §7 con el equilibrado aplicado antes de partir, que satura la
  métrica en 1,0000 con cualquier semilla. Dos equipos, dos mercados, el mismo mecanismo.

**Y el tercero acota un límite nuestro, en contra de la lectura que nos convendría.** En
§10 declaramos que no afinamos hiperparámetros en ningún brazo y que por eso no podemos
separar «el método no aporta» de «esta configuración no aporta». `arXiv:2503.05602` dice que el
ajuste óptimo del ancho de banda **acerca** el kernel cuántico al RBF. Si eso es así, afinar
no lo alejaría del clásico: lo empujaría hacia él. **Nuestro caveat sigue en pie —no
estamos en ese régimen porque no afinamos— pero corta menos de lo que parecía**, y es
coherente con que nuestro kernel cuántico y el RBF **no sean distinguibles** por nuestro
propio criterio (§8).

**Lo que NO afirmamos** [por construcción]: que esto sea una revisión de literatura. Son
**tres fuentes salidas de un barrido nuestro**, abiertas y verificadas frase por frase —
ninguna entró por relevo. Tres papers no son un barrido con denominador, y ese barrido no
está hecho.

## 12 · Qué no podemos afirmar

- **Nada sobre hardware cuántico**: el brazo cuántico corrió en **simulación exacta**,
  con gasto US$0 y sin enviar un solo circuito a un dispositivo. Un statevector no tiene
  ruido, ni error de lectura, ni decoherencia. El resultado es un **techo**: con el mismo
  mapa, la versión ruidosa no puede superar a la exacta. Que no haya ventaja ahí cierra
  el caso; que la hubiera **no** la probaría en hardware.
- **No podemos separar «el método no aporta» de «esta configuración no aporta»**: ningún
  brazo llevó búsqueda de hiperparámetros (§10), y la literatura que citamos reporta que
  esas elecciones mueven más que el propio kernel cuántico.
- **Los controles del brazo cuántico NO están pre-registrados**: se decidieron después de
  ver el resultado primario, el artefacto lo dice en un campo propio, y no modifican el
  primario. No buscamos otra codificación ni otras variables hasta que alguna cruzara:
  eso es justo lo que el pre-registro existe para impedir.
- **Desviación declarada**: el pre-registro decía correr en CI y el brazo cuántico corrió
  en el Mac del laboratorio. Va escrita dentro del sello con su razón; el test es el
  mismo, comprobado por hash, y reproducirlo en CI queda pendiente.
- **Una sola fuente externa verificada** (§11): no hicimos revisión de literatura.
- **Nada contra el 0,871 publicado como número**: nuestro IC lo contiene; la evidencia
  es el Δ intra-implementación, no la resta entre implementaciones.
- **Los hallazgos del ataque son intra-dataset**: 48 horas, un procesador, 2013. Valen
  para ULB por construcción y no se extrapolan — ni siquiera al IEEE-CIS que medimos
  aparte más abajo, donde el ataque no se repitió.
- **El margen del criterio C es estrecho** (1,5 % del umbral) y así viaja.
- **LightGBM sigue abierto** por configuración nuestra; la búsqueda declarada está
  pendiente para ambos modelos.
- **Validez externa, ya no pendiente pero acotada** (REFORMS 8a): el segundo dataset
  del track, IEEE-CIS, está medido y sellado (`RQ-EXP-HSBC-IEEE-001`): el mejor
  modelo llega a **0,5438** [0,5276 – 0,5590] [medido], contra 0,800822 en ULB. El fraude
  ahí es **19 veces más frecuente** y aun así se predice peor — lo que dice que la
  dificultad no es sólo el desbalance. Sigue acotado: **son dos datasets, no una
  población**, y el brazo cuántico corrió sólo sobre ULB.

## 13 · Viabilidad y recursos

**Lo que ya está hecho corrió con gasto US$0**, en un Mac, en menos de un minuto por brazo [medido: 45,2 s el cuántico, 63,4 s el clásico]. No hay infraestructura oculta detrás de estos números: el instrumento es un archivo de Python que va en el paquete y se puede correr.

**Lo que costaría llevarlo a hardware, derivado de la tarifa publicada y no estimado a ojo** [medido, en el pre-registro sellado]: **USD 39.018.970** para el test completo, y **USD 3.425** para una demostración acotada de 200×50 en el backend más barato.

El grueso de ese costo es la **tarifa fija por tarea**: en un kernel cada par
(transacción, punto de soporte) es un circuito distinto y no se amortiza repitiendo
disparos. Consecuencia práctica: **reducir disparos casi no mueve el costo; sólo reducir
pares** — y reducir pares rompe la comparabilidad con el test sellado. La errata
`RQ-ERRATA-PREREG-HSBC-003` acota esa frase: en los backends de disparo caro la cuota se invierte.

**Lo que haría falta para la fase siguiente**, en orden de cuánto cambiaría el resultado:

1. **Una búsqueda de hiperparámetros con presupuesto emparejado** entre los dos brazos.
   Hoy es una configuración por brazo (§10) y es el límite que más nos ata.
2. **Un benchmark con meses de holdout**, por lo que explica §9. IEEE-CIS ya está medido
   y sellado; extenderlo es trabajo, no investigación.
3. **Una demostración acotada en hardware**, sólo si el objetivo es caracterizar ruido —
   no para mejorar el resultado, que en simulación exacta ya es un techo (§8).

## 14 · Impacto esperado

**Seamos precisos sobre qué mejora esto y qué no.** El brazo cuántico no aporta
desempeño: perdió, y §8 explica por qué eso no es un accidente del montaje. Un banco que
adopte este kernel tal cual **detectaría menos fraude**, no más.

**Lo que sí cambia es la calidad de la decisión sobre invertir o no:**

- **Un piloto cuántico de detección de fraude ya tiene evidencia previa negativa**, y
  hasta ahora estaba dispersa en tres trabajos que miden cosas distintas (§11). Juntarla
  con una medición propia e independiente ahorra descubrirlo por cuenta propia.
- **La cifra que hoy se reporta sobre ULB no mide robustez temporal** (§9), y eso afecta
  a cualquier equipo que compare modelos sobre ese benchmark, cuántico o no.
- **El protocolo es lo más transferible de todo esto**: pre-registro anclado antes del
  código, ataque adversarial al propio resultado, presupuesto de búsqueda emparejado, y
  cada cifra recomputable por un tercero. Aplicado a las evaluaciones internas de un
  banco, distingue una mejora real de una de procedimiento — que es el error que §11
  documenta en la literatura y que nosotros medimos en nuestro propio experimento (§7).

## 15 · Equipo

**Equipo:** Rosetta Quantum — **Blue Tuna SpA**, Punta Arenas, Chile (fundador-operador
único). **Responsable:** Nicholas Iakl Freundlich · hello@rosettaquantum.com

**Trayectoria:** fundador y CEO de Sumeria (analítica de conversación con IA, más de 9
años) y fundador de Yu-Track (software de cobranza para servicios financieros). Ingeniero
Comercial y magíster.

**Lo que traemos no es el lado de vender el qubit: es el lado de consumir el veredicto**
— construir sistemas cuya salida alguien tiene que creer para tomar una decisión. Por eso
este documento está escrito para que usted **no tenga que creernos ninguna parte**.

**Ésta es nuestra cuarta postulación cuántica**; Cleveland, E.ON y Airbus salieron antes.

**Por qué esto puede ejecutar una fase siguiente:** la infraestructura de verificación que
haría falta **no es un plan, está corriendo**. En el archivo hay **190 artefactos sellados**
[medido: contados en el commit `afd6f6920b4e` del repositorio de evidencia, para que usted cuente
exactamente lo mismo — el archivo crece, así que un conteo sin commit no se puede
comprobar], repartidos así:

| tipo | cuántos |
|---|---|
| RUN | 149 |
| PREREG | 17 |
| REPORT | 12 |
| MANIFEST | 4 |
| RECIPE | 4 |
| ERRATA | 3 |
| VERDICT | 1 |

*Decimos «artefactos sellados» y no «corridas» a propósito: **149 son corridas** y el resto
son informes, pre-registros, manifiestos y erratas. Un total con la etiqueta equivocada es
una cifra correcta que el lector no puede comprobar — y si la primera no le cuadra, no
revisa las demás.*

Cada uno lleva su hash recomputable y su recibo de OpenTimestamps, espejado en dos
servidores independientes. **Este entregable son 11 de ellos**, y §17 le dice cómo
comprobar cada uno sin pedirnos nada.

## 16 · Qué estamos pidiendo

**Tres cosas, y ninguna es un cheque antes de una conversación.**

1. **Una hora con quien sea dueño del benchmark.** El hallazgo de §9 —que ULB deja **7,7
   horas** de futuro real y por eso no puede medir robustez temporal— o les sirve o está
   equivocado, y las dos cosas valen una hora. Si sirve, la comparación contra IEEE-CIS ya
   está hecha y sellada, y es suya con o sin nosotros.
2. **Un caso que a ustedes les importe de verdad.** Todo esto corre sobre los datasets que
   su enunciado señala. Preferimos **medir** si sus casos reales tienen el problema de la
   ventana corta, en vez de especular sobre si lo tienen.
3. **Una fase siguiente acotada a la medición, no a una promesa.** El mismo método que
   éste: pre-registrado antes de que exista el instrumento, sellado, con marca de tiempo,
   y publicado funcione o no. **Este informe es lo que parece un resultado negativo cuando
   se entrega a propósito.**

## 17 · Reproducción — ejercida por nosotros primero

```
git clone https://github.com/RosettaQuantum/evidence && cd evidence
bash tools/reproducir_hsbc.sh        # descarga+verifica el dato, corre baseline y
                                     # las 4 series, y verifica TODO con denominador
python3 tools/replicar.py verificar --track hsbc   # solo la verificacion
```

- **Los scores crudos están depositados** (`scores_*.npz` por hash): un tercero
  recomputa las curvas exactas. **Lo ejercimos como el tercero** [medido]: desde los
  bytes de origin (`git archive`, sin archivos locales), AUPRC, AUC, F1 y las cuatro
  celdas de la confusión recomputan idénticos (límite declarado: scores en float32 →
  reproducción a ~1e-5).
- **La batería de verificación** corre 7 tramos por artefacto y cada uno termina en
  OK, FALLA o SALTADO — un tramo no ejercido cuenta como saltado, nunca como silencio.
- **Determinismo entre máquinas** [medido]: la partición produce el mismo sha256 de
  test en Mac y en CI; el punto del baseline (corte 80) reproduce al cuarto decimal en
  corridas independientes de CI.
- Alcance del ejercicio propio [por construcción]: cada comando del guion fue ejercido
  — la descarga y verificación localmente, las corridas en CI (5 despachos: el
  baseline y las cuatro series, listados en los artefactos por run id)
  — la batería local y por mutación. El guion como unidad requiere
  xgboost con OpenMP (CI o máquina compatible).

## 18 · Anexos

### A · REFORMS, ítem por ítem

**Recuento al armar este documento: 28 plenos · 4 parciales · 0 ausentes de 32.**
El punto de partida (20-ago, antes del ataque y de este documento) era 15 · 8 · 9 —
consta como trayectoria, no se sobreescribe. Plan de cierre de los 4 parciales:
README dedicado (2d) y búsqueda de hiperparámetros declarada (5e);
3g y 6c son límites del dato que se declaran, no se «cierran».

| ítem | estado | dónde |
|---|---|---|
| 1a | pleno | población de la afirmación: §4 (intra-dataset, declarada) |
| 1b | pleno | motivación del dataset: prereg + §4 |
| 1c | pleno | motivación del método: prereg 001 |
| 2a | pleno | dataset con id, md5, sha256 y manifiesto sellado |
| 2b | pleno | código público, archivado por hash, sha en cada artefacto |
| 2c | pleno | infraestructura declarada (CI, versiones en lib_versions) |
| 2d | parcial | instrucciones en §17; README dedicado pendiente |
| 2e | pleno | tools/reproducir_hsbc.sh |
| 3a | pleno | fuente + fecha de recolección (sept-2013): §4 |
| 3b | pleno | marco muestral descrito: §4 |
| 3c | pleno | justificación del dataset: prereg |
| 3d | pleno | variable de salida + descriptivos: manifiesto |
| 3e | pleno | n en manifiesto |
| 3f | pleno | 0 nulos, trivialmente por clase: §4 |
| 3g | parcial | representatividad NO afirmada a propósito — declarada como límite |
| 4a | pleno | ninguna fila excluida: §4 |
| 4b | pleno | 0 corruptos medidos; política declarada |
| 4c | pleno | sin transformaciones propias: §4 |
| 5a | pleno | configs completas en artefactos |
| 5b | pleno | elección de modelos justificada: prereg |
| 5c | pleno | particiones detalladas y selladas |
| 5d | pleno | modelo reportado = config v1 fijada, sin selección entre alternativas |
| 5e | parcial | búsqueda de hiperparámetros PENDIENTE; LightGBM abierto ahí |
| 5f | pleno | baselines apropiados justificados: prereg §5 |
| 6a | pleno | preprocesamiento sólo-train, guardias probadas por mutación |
| 6b | pleno | duplicados medidos (0); dependencia temporal por diseño |
| 6c | parcial | Time/Amount legítimas; el PCA global heredado se declara (anexo B) |
| 7a | pleno | métricas justificadas y selladas antes |
| 7b | pleno | bootstrap declarado (2.000, semilla) |
| 7c | pleno | Welch + Mann-Whitney concordantes; criterio pre-sellado |
| 8a | pleno | segundo dataset medido y sellado (IEEE-CIS); acotado a dos datasets |
| 8b | pleno | límites y contextos donde NO sostenemos los hallazgos: §4 y §8 |

### B · Model info sheet — las 8 fugas de Kapoor & Narayanan

[por literatura: taxonomía de *Leakage and the reproducibility crisis in ML-based
science*; verificada contra el texto del paper]

| tipo | estado en este trabajo |
|---|---|
| L1.1 sin test set | AUSENTE [por construcción]: partición sellada antes de entrenar |
| L1.2 preprocesamiento sobre train+test | AUSENTE en lo nuestro [medido: sin transformaciones propias]; **HEREDADO del dataset** [por construcción]: el PCA de V1–V28 se ajustó sobre el conjunto completo antes de publicarse — imposible de remover; lo declaramos |
| L1.3 selección de features sobre train+test | AUSENTE [por construcción]: no hay selección de features |
| L1.4 duplicados train-test | MEDIDO: 0 duplicados exactos entre mitades |
| L2 features ilegítimas | Time y Amount son legítimas para la tarea; V1–V28 anónimas por diseño [por construcción] |
| L3.1 fuga temporal | ES EL OBJETO DE ESTUDIO: la serie temporal la evita; las aleatorias la exhiben a propósito y su efecto está medido (Δ=0.0713) |
| L3.2 no-independencia train-test | transacciones del mismo par de días; declarado como límite (§4) |
| L3.3 sesgo de muestreo | un procesador, 48 h: declarado; sin reponderación |

### C · Artefactos y sellos

| pieza | identificador | hash |
|---|---|---|
| prereg diseño | `RQ-PREREG-HSBC-001` | `sha256:b04f214fae845b1c50431d225e6590b0956d8920c24b7c7fa26ed94c58f3f2db` |
| prereg ataque | `RQ-PREREG-HSBC-002-ATAQUE` | `sha256:87c187b48627d52958728365c1e31b08c71a656bfbad14b8f632f89b9fdcf8c4` |
| manifiesto de datos | `RQ-DATA-HSBC-ULB-001` | `sha256:71010a1afbf85a0d831bfdc4dcca75754a439125af7fb680132ba3cf71e4503f` |
| sello del ataque | `RQ-EXP-HSBC-ATAQUE-001` | `sha256:12f18492764f1f7108f14d451f8e9620da7918564c158c13302d77ef4d7b3115` |
| baseline | artefacto | `hsbc_ulb_baseline_lightgbm-xgboost@2072bc53.json` |
| serie S1 | artefacto | `hsbc_ulb_baseline_ataque_S1_n20@ffcf8721.json` |
| serie S2 | artefacto | `hsbc_ulb_baseline_ataque_S2_n20@664575b5.json` |
| serie S3 | artefacto | `hsbc_ulb_baseline_ataque_S3_n20@bf62f223.json` |
| serie S4 | artefacto | `hsbc_ulb_baseline_ataque_S4_n5@25c008b1.json` |

*Los sellos se verifican con `python3 tools/verify_seals.py <archivo>`; el anclaje en*
*Bitcoin (OTS) y las tres copias (GitHub, Codeberg, D1) son del notario.*
