# El harness del árbol avanzó dentro del mismo commit que lo ancló

**26 de agosto de 2026 — sesión laboratorio.**

Esta nota existe porque el commit `9512fb1`, que ancla el sello `RQ-EXP-HSBC-Q-001` (brazo
cuántico de HSBC, sin ventaja), contiene **un `harness/hsbc_harness.py` que no es el que
produjo ese resultado** — y nada dentro del commit lo dice. Nada se reescribe: el sello es
correcto y verifica. Lo que faltaba era el dato al lado.

## Qué se movió

| objeto | sha256 | qué es |
|---|---|---|
| `code/hsbc_harness@a27348cb.py` | `a27348cb…` | la copia **congelada**, la que el sello declara en `harness_sha256` |
| `harness/hsbc_harness.py` (en el árbol, commit `9512fb1`) | `76bbe0d9…` | el archivo de trabajo, **ya avanzado** |
| `code/_correr_cuantico@3216bb70.sh` | `3216bb70…` | el runner **congelado** que el sello declara |
| `_correr_cuantico.sh` (en el laboratorio) | `f8384a8c…` | el runner de trabajo, avanzado al arreglarlo (abajo) |

**Los dos casos no son la misma cosa y conviene no confundirlos.** Que un archivo de trabajo
avance respecto de su copia congelada es lo normal y lo correcto: las copias congeladas están
congeladas justamente para eso. El defecto del harness no fue que avanzara — fue que avanzó
**en silencio, dentro del commit que lo anclaba**, sin que nada lo dijera. El runner avanzó
después, a propósito, y queda dicho acá: eso es la diferencia entre una deriva y un cambio.

La copia congelada está intacta y calza con su propio nombre. **Quien verifique por la vía
publicada obtiene lo correcto.** La trampa es para quien haga lo obvio: clonar el commit
anclado y correr `harness/hsbc_harness.py`, cuyo sha no cuadra con el sello.

## Por qué se movió

Después de sellar, edité el harness para que `n_vectores_soporte` viajara **dentro del
artefacto**. Venía tecleándolo yo a mano desde la consola a un documento sellado; salió
correcto, pero un número que sólo vive en un log es un número que el siguiente sellador va a
copiar a mano. El arreglo era bueno; el momento, no.

El archivo quedó sin commitear y la cadena notarial —que hace una barrida amplia y **se lleva
lo que encuentre**— lo arrastró al commit del ancla. Es el §3 de `CLAUDE.md` al pie de la
letra: **un actor por árbol**, roto justo en el paso cuyo propósito es congelar el estado.

## Por qué la diferencia es inerte, medido y no supuesto

Se corrió el harness del árbol y se comparó **campo por campo** contra el artefacto sellado,
ignorando sólo los tiempos de ejecución y el propio `harness_sha256`:

```
diferencias entre el artefacto SELLADO y el que produce el harness del árbol:
   /n_vectores_soporte      sellado='<falta>'  arbol=945

AUPRC idéntico: True | IC idéntico: True
```

**Una sola diferencia: el campo nuevo.** El AUPRC (`0,257453`) y el intervalo
(`[0,154578, 0,369107]`) son idénticos. De paso, esto confirma contra un artefacto el `945`
que se había tecleado a mano en el sello.

Sin esta comparación, «el harness cambió» habría obligado a decidir a ciegas si el ancla
servía. Con ella, el alcance queda acotado a un campo añadido.

## El segundo defecto, que salió del primero

`_correr_cuantico.sh` hacía `export RQ_OUT=...` a secas. Las variables viven dentro del script
a propósito —pasadas por fuera se olvidan, y una corrida sin `RQ_BRAZO` cae en silencio al
brazo clásico— pero ese `export` **pisaba cualquier redirección**: la corrida de verificación
sobrescribió el artefacto que iba a verificar. Es el banco de mutación contaminando su propio
artefacto, otra vez y en otra forma.

El arreglo **no** fue volver todo redirigible, porque eso abre la trampa inversa: correr con
otros parámetros y producir un artefacto que dice venir de este runner. Quedó separado:

- **rutas de salida** (`RQ_OUT`, `RQ_SCORES_PREFIX`): `${VAR:-default}` — redirigibles, que es
  lo que permite verificar sin pisar, conservando que nunca falten.
- **parámetros del experimento** (`RQ_DATASET`, `RQ_BRAZO`, `RQ_QFEAT`, `RQ_QSOP`, `RQ_QREPS`,
  `RQ_QC`, `RQ_CONTROLES`): fijos, y el runner **aborta** si alguien intenta pisarlos desde el
  entorno. Un runner es la definición congelada de una corrida; otros parámetros son otra
  corrida y van en otro archivo.

Con las dos pruebas que exige el proyecto para un candado nuevo:

```
grito:    RQ_QSOP=500 ./_correr_cuantico.sh   -> salida=1, aborta nombrando la variable
silencio: RQ_OUT=/tmp/... ./_correr_cuantico.sh -> corre, AUPRC 0,2575, artefacto del
          laboratorio INTACTO (963e4312… antes y después)
```

## Lo que queda pendiente, y de quién es

La cadena notarial no distingue entre «esto es parte del sello» y «esto estaba tirado en el
árbol». **Debería listar lo que va a commitear que no sea un artefacto sellado y pedir
confirmación** — un guardia así habría mostrado el archivo antes de tragárselo. Ese arreglo
es de la sesión que corre el notario, no de ésta, y quedó anotado allá.
