# Borrador de errata — `RQ-PREREG-HSBC-003-CUANTICO`

**Para que el laboratorio la selle.** No modifica el original: publicado es publicado, y el
archivo, su hash y su ancla quedan intactos. Corrige una afirmación que el propio artefacto
desmiente en su tabla.

---

## Qué corrige

**Sello:** `RQ-PREREG-HSBC-003-CUANTICO`
**Hash del original:** `sha256:e15b1808c03c29a8623eb687c3790c0a00e29cb5ae3ff6848f83d94269c5abb8`

**La frase, textual:**

> «Consecuencia medida: **ni reducir disparos ni cambiar de proveedor mueve el costo** — solo
> reducir pares, y reducir pares rompe la comparabilidad con el test sellado. Esta es la
> respuesta al "under what conditions" del §4.2.»

**La frase es falsa, y el propio artefacto trae los datos que la desmienten** — declara
`per-shot 0,000425 Rigetti Cepheus a 0,08 IonQ Forte`, un factor de **188**.

## Lo medido, recomputado hoy con `costo_braket_hsbc.py`

Demostración acotada de 200 × 50 (10.000 pares × 100 disparos = 1.000.000 de disparos):

| backend | tareas | disparos | **total** |
|---|---|---|---|
| Rigetti Cepheus | 3.000 (87,6 %) | 425 (12,4 %) | **USD 3.425** |
| IQM Garnet | 3.000 (67,4 %) | 1.450 (32,6 %) | **USD 4.450** |
| IQM Emerald | 3.000 (65,2 %) | 1.600 (34,8 %) | **USD 4.600** |
| AQT IBEX-Q1 | 3.000 (11,3 %) | 23.500 (88,7 %) | **USD 26.500** |
| IonQ Forte | 3.000 (3,6 %) | 80.000 (96,4 %) | **USD 83.000** |

**Cambiar de proveedor mueve el costo por un factor de 24,2.**

La tabla lleva **los cinco backends que nuestro instrumento tabula**, no tres. El quinto
—AQT IBEX-Q1, con las tareas en 11,3 %— importa porque muestra que **no es un caso
aislado de IonQ**: la cuota de las tareas recorre un continuo de 87,6 % a 3,6 %, y hay
dos backends por debajo del 50 %, no uno.

## Qué era cierto y qué se afirmó de más

La afirmación **es cierta en el backend más barato y se declaró como general**:

- **«Las tareas dominan el costo»** — cierto en Rigetti (87,6 %), **falso en IonQ** (3,6 %).
- **«Reducir disparos no mueve el costo»** — cierto en Rigetti (12,4 % del total),
  **falso en IonQ**, donde los disparos son el 96,4 %.

Lo único invariante es la **tarifa por tarea**: USD 0,30, idéntica en los seis QPU. Eso es
lo que se midió; «el costo no se mueve» es lo que se escribió.

## La afirmación corregida

> La tarifa por tarea (USD 0,30) es idéntica en los seis backends y no se puede negociar; por
> eso, **en los backends de disparo barato (Rigetti, IQM) el costo lo dominan las tareas** y
> ni reducir disparos ni cambiar entre ellos lo mueve de forma apreciable. **En IonQ Forte no:
> su disparo cuesta 188 veces más, los disparos pasan a ser el 96 % del total, y el mismo
> trabajo sube de USD 3.425 a USD 83.000.** La única palanca que reduce el costo en todos los
> backends es reducir pares, y reducir pares rompe la comparabilidad con el test sellado.

## El mismo defecto estaba en el instrumento, y ahí se arregló

La frase no se inventó al redactar el sello: **la imprimía el propio script.**
`costo_braket_hsbc.py` terminaba con

> `EL COSTO LO DOMINAN LAS TAREAS, no los disparos`

seguida de **un solo ejemplo, el de Rigetti**. Una afirmación general apoyada en el caso
que la cumple. De ahí viajó al artefacto tal cual.

Arreglarlo sólo en el sello habría dejado el instrumento produciendo la misma frase la
próxima vez. El arreglo va en el instrumento, **con un chequeo que falla cerrado**: ahora
imprime la cuota **por backend** y deriva la conclusión de ellas en vez de escribirla de
antemano; si la cuota cruza el 50 % —como ocurre hoy— **se niega a insinuar una frase
general** y dice cuál backend la desmiente. Si algún día todos cayeran del mismo lado, esa
rama dejaría de dispararse sola y recién ahí generalizar sería legítimo.

Fue ejecutar ese arreglo lo que destapó el quinto backend: con la tabla completa a la
vista, AQT IBEX-Q1 aparece también por debajo del 50 %.

## Una tercera cifra que no se sostiene: «los seis QPU»

El artefacto declara `per-task USD 0,30 idéntico en los **seis** QPU`. **Nuestro
instrumento tabula cinco** (IQM Garnet, IQM Emerald, Rigetti Cepheus, IonQ Forte, AQT
IBEX-Q1). El número «seis» **no está respaldado por ninguno de nuestros artefactos**: o
existe un sexto backend que no tabulamos, o es un error de redacción.

No se resuelve aquí porque comprobarlo exige volver a la página de tarifas de AWS, y esta
errata no la consultó. **Lo que sí está medido y se sostiene es lo que importa**: en los
cinco backends que tabulamos, la tarifa por tarea es USD 0,30 y ninguna cifra de este
documento depende de que sean cinco o seis. Queda declarado como pendiente de verificar en
la fuente, no repetido como si estuviera comprobado.

## Qué NO se retracta

La conclusión operativa del pre-registro **se mantiene**: la demostración acotada sobre
Rigetti Cepheus a USD 3.425 sigue siendo la opción elegida, y sigue siendo la respuesta al
«under what conditions» del §4.2. **Lo que se corrige es el alcance de la explicación, no la
decisión.**

## Cómo se encontró

**Quién lo escribió:** la sesión de laboratorio, que redactó y selló
`RQ-PREREG-HSBC-003-CUANTICO`. La frase pasó por una revisión de coordinación y por el OK
de Nicholas sin que ninguno de los tres la contrastara contra la tabla que estaba dos
líneas más abajo, en el mismo artefacto.

**Quién lo encontró:** la sesión `Rosetta · Cuántico`, revisando el SPEC de Laboratorio
Rosetta, **fuera del alcance de esa revisión**. Verificado en la sesión de coordinación recomputando
`costo_braket_hsbc.py` antes de redactar esta errata — ninguna cifra de aquí está tecleada
de memoria.
