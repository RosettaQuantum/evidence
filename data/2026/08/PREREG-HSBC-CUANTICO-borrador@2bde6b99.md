# Borrador de pre-registro — brazo cuántico del track HSBC (RQ-PREREG-HSBC-003-CUANTICO)

**Redactado por el laboratorio para revisión de la coordinación, ANTES de escribir una
línea del brazo cuántico.** **Gasto autorizado: US$0** — Nicholas evaluó el presupuesto
de una corrida en hardware y lo rechazó por elevado, así que este track es enteramente
simulación y el costo del hardware entra como resultado medido (§8). Las condiciones de
orden y declaración las pone el notario y están incorporadas abajo.

## 1 · Por qué existe

El statement §4.1 pide *«develop a quantum or quantum-inspired fraud detection model and
evaluate it against established classical baselines»* y el §5.2 exige describir enfoque,
codificación y diseño de circuito, más *«discussion of any observed quantum improvement and
under what conditions»*. **El track hoy es enteramente clásico** — el propio entregable lo
declara. Esto lo cierra.

## 2 · Qué NO se toca

- **El árbitro es el baseline ya sellado** `RQ-EXP-HSBC-BASE-001` (`sha256:2cc73ac7…`),
  AUPRC 0,8008 [IC95 0,705–0,883]. **No se re-corre.**
- **El test es el completo y sellado**: 56.962 filas, 75 fraudes, sha256 declarado en el
  artefacto. Ningún brazo lo submuestrea.
- **La métrica que manda sigue siendo AUPRC**, sellada en `RQ-PREREG-HSBC-001`.

## 3 · El submuestreo: del entrenamiento, nunca de la evaluación

El brief permite aplicar circuitos a un subconjunto reducido con estratificación declarada.
**Medido**: con la tasa del train (0,183 %), un submuestreo ingenuo de n=1.000 deja
**1,8 fraudes esperados** — entrenar un clasificador de fraude con dos positivos no es una
comparación, es ruido con forma de resultado.

**Diseño**: los **417 fraudes completos** del train + negativos estratificados, en tres
tamaños — **n = 2.000 / 5.000 / 10.000**. El artefacto declara, por corrida: número exacto,
semilla, y la razón fraude/no-fraude **antes y después**. El barrido es además la respuesta
al «under what conditions» del §4.2.

## 4 · Familia, codificación y circuito

**Brazo 1 — kernel cuántico de fidelidad** (primero, por determinista: no tiene optimizador
que se trunque, que es lo que nos costó dos puntos en E.ON).
- Codificación: `AngleEmbedding` sobre **8–12 qubits**, entrelazamiento CZ en cadena.
- Features: reducción por PCA **ajustado sólo sobre el train** (guardia de fuga).
- Clasificador: SVM con kernel precomputado.

**Brazo 2 — clasificador variacional**, después. Comparte instrumento con el QAOA que ya
dominamos, y su modo de fallo típico (mesetas de gradiente) ya sabemos declararlo.

## 5 · El costo, medido antes de prometer

**En simulación el kernel NO requiere n² evaluaciones.** `|⟨φ(a)|φ(b)⟩|²` sale del producto
de los vectores de estado: **n preparaciones**, y la matriz de Gram es un producto matricial.

| | par a par | por vectores de estado |
|---|---|---|
| puntuar el test completo, 8 qubits | 56,8 h | **0,8 min** |
| puntuar el test completo, 12 qubits | 132 h | **1,8 min** |

[medido en este Mac: 1,795 ms/evaluación y 0,864 ms/preparación a 8 qubits]

### 5 bis · Los 0,8 minutos NO son velocidad cuántica

Esto se declara aquí para que no pueda leerse mal, y es material del entregable, no una
nota al pie.

**El atajo existe PORQUE estamos simulando.** El statevector es un objeto accesible en el
simulador, y la matriz de Gram sale de un producto en numpy. En un computador cuántico real
ese objeto **no existe**: hay que volver a las n² evaluaciones, cada par es un circuito
distinto, y los disparos son finitos.

Las tres cosas van juntas o ninguna:

1. **Qué modelo es**: el kernel cuántico de fidelidad en su límite sin ruido y con disparos
   infinitos. El modelo es el mismo en las dos vías — **lo que cambia es el costo de
   obtenerlo**, no lo que se calcula.
2. **De qué es la cifra de tiempo**: 0,8 min es **simulación exacta**, no ejecución.
3. **Cuánto costaría en hardware, medido**: puntuar el test completo × 2.000 soportes son
   1,14×10⁸ pares = **USD 39.018.970** en Rigetti Cepheus, con tarifa leída de AWS el
   2026-08-21 y derivada por `costo_braket_hsbc.py`. **El 88 % es la tarifa por tarea**
   (USD 0,30, idéntica en los seis QPU), porque cada par es un circuito distinto: no se
   amortiza con disparos ni cambiando de proveedor.

Presentar sólo el «0,8 minutos» sería vender una ventaja que no medimos — y con nuestras
propias herramientas cualquiera nos desmentiría en un minuto.

**Y esto responde literalmente al «under what conditions» del §4.2**: *el kernel cuántico es
barato de simular y caro de ejecutar, y aquí está la medición de ambos.*

## 6 · El criterio de cruce, con su gatillo escrito

Con 75 fraudes en el test el IC del AUPRC es ancho: el del baseline va de 0,705 a 0,883.
**Un brazo cuántico que dé 0,82 no supera nada — cae dentro.** Comparar puntos o intervalos
separados permitiría leer cualquier resultado a gusto.

**Regla de decisión, fijada aquí**: bootstrap **pareado** sobre el mismo test (mismos
índices remuestreados para ambos brazos), **2.000 remuestreos, semilla 42**.

- **Se afirma mejora** si el **IC95 de la diferencia pareada AUPRC(cuántico) − AUPRC(baseline)
  excluye el cero por el lado positivo**.
- **Se afirma que no mejora** si el IC incluye el cero o lo excluye por el negativo.
- No hay tercera lectura, y ninguna se elige después de ver el número.

## 7 · Los dos desenlaces son entregables

- **Si mejora**: el cruce se mide contra un árbitro ya sellado y anclado antes de que el
  brazo cuántico existiera. Eso es más fuerte que cualquier número suelto.
- **Si no mejora**: la caracterización de **dónde y por qué** —por tamaño de subconjunto,
  por número de qubits, por codificación— es exactamente lo que pide el §4.2. **No hay plan
  B: hay dos resultados y los dos se publican sellados.**

**Expectativa declarada antes de correr**: baja probabilidad de mejora. El baseline es un
XGBoost afinado sobre 227.845 filas; el brazo cuántico entrena sobre 2.000–10.000 con 8–12
features. Si mejora, se mira con más desconfianza que entusiasmo.

## 8 · Hardware: medido y NO ejecutado

**Gasto autorizado: US$0.** Nicholas evaluó el presupuesto de una corrida en hardware y lo
rechazó por elevado. **Ninguna tarea se envía a Braket ni a ningún QPU.** Este track es
enteramente simulación, y eso no lo debilita: el §4.2 del brief dice literalmente que
entrenar o inferir en hardware *«is not expected nor required»*, y el objetivo principal
(§4.1) pide desarrollar y evaluar un modelo cuántico o cuántico-inspirado contra baselines
clásicos — que es exactamente lo que la simulación exacta entrega.

**Y el costo del hardware pasa de presupuesto a RESULTADO.** Lo medimos en vez de gastarlo,
y la tabla es material del entregable:

| escenario en hardware real | pares de kernel | tareas | USD |
|---|---|---|---|
| test completo (56.962) × 2.000 soportes | 1,14×10⁸ | 1,14×10⁸ | **39.018.970** |
| demostración 500 × 100 | 50.000 | 50.000 | **17.125** |
| demostración 200 × 50 | 10.000 | 10.000 | **3.425** |
| 200 × 50 en IonQ Forte | 10.000 | 10.000 | **83.000** |

[derivado por `costo_braket_hsbc.py`; tarifa leída de aws.amazon.com/braket/pricing el
2026-08-21: per-task US$0,30 idéntico en los seis QPU, per-shot 0,000425 (Rigetti Cepheus)
a 0,08 (IonQ Forte)]

**El hallazgo que la tabla contiene, y que es la respuesta al «under what conditions»:**
**el 88 % del costo es la tarifa fija por tarea**, porque en un kernel cada par
(x_test, x_soporte) es un **circuito distinto** y no se amortiza repitiendo disparos.
Consecuencia medida: **ni reducir disparos ni cambiar de proveedor mueve el costo** — sólo
reducir pares, y reducir pares es reducir el test, que rompe la comparabilidad con el
árbitro sellado.

**Lo que este track afirma sobre hardware**: nada sobre su desempeño — no lo corrimos.
Afirma **cuánto costaría ejecutarlo**, medido con la tarifa publicada y derivado del diseño.
Un costo medido y declarado no es un sustituto pobre de una corrida: es la información que
decide si la corrida tiene sentido, y casi nadie la trae.

**Si algún día se autoriza gasto**, el brazo a ejecutar sería el **variacional** —500 tareas
contra las 10.000 del kernel, dos órdenes menos— y el número comparable seguiría saliendo de
la simulación. Queda escrito aquí para que esa decisión no se improvise después.

## 9 · Guardias, todas falla-cerrado y probadas por mutación

1. **Fuga**: el PCA y toda transformación se ajustan **sólo sobre el train** del subconjunto;
   ninguna fila del test participa. Guardia que aborta si un índice cruza.
2. **Estratificación medida**: la razón fraude/no-fraude de cada submuestra se mide y viaja
   al artefacto; desviación fuera de lo declarado aborta.
3. **Mismo test**: ambos brazos declaran el sha256 del test que puntuaron; si difieren, el
   comparador aborta.
4. **La matriz de Gram es un kernel válido**: simétrica, diagonal 1, valores en [0,1] —
   se comprueba, no se asume.
5. `harness_sha256` en cada artefacto, y el sellador publicado en el mismo acto.

## 10 · Declaración heredada que no se re-descubre

Las features V1–V28 del ULB **ya son componentes de un PCA ajustado sobre el dataset
completo** por quienes publicaron el dato [por construcción]. Nuestro PCA sobre train no lo
cambia ni lo empeora, y **el artefacto del brazo cuántico arrastra esta declaración** para
que un lector cuidadoso no la encuentre antes que nosotros.

## 11 · Qué NO afirma este track

Ninguna ventaja cuántica salvo cruce medido con la regla del §6. Nada fuera de este dataset
(48 horas, un procesador, 2013). Nada sobre escalamiento: el barrido caracteriza tres
tamaños, no una tendencia.

**Y nada sobre hardware cuántico: en esta fase no se ejecutó ningún circuito en un
dispositivo real.** Por lo tanto este track no afirma nada sobre ruido, calibración,
fidelidad de dispositivo ni desempeño en hardware. Lo único que afirma sobre hardware es
**cuánto costaría** ejecutarlo (§8), derivado del diseño y de la tarifa publicada.
