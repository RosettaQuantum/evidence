# Fechas declaradas incoherentes con el historial — mancha conocida y declarada

Este archivo existe por la misma razon que `PROCEDENCIA-PERDIDA.md` y
`PROCEDENCIA-EN-FUENTE-DE-TERCEROS.md`: **un hueco declarado deja de ser un hueco.** Y no
es decorativo — `scripts/notarize.py` lo LEE: las entradas de aqui son las unicas
excepciones que no bloquean un anclaje nuevo. Cualquier sello nuevo con fecha futura para
el anclaje y no se estampa.

## Que paso

El identificador de cada artefacto sellado lleva una marca de tiempo, y **la escribia quien
redactaba, leyendola de su contexto** — no del reloj. El contexto de una sesion de modelo
puede estar corrido respecto del sistema. Resultado: **14 artefactos publicados declaran en
su ID una fecha posterior a su propio commit**, lo que es imposible: el archivo no puede
haberse creado despues de publicarse. Medido el 2026-08-19 contra el reloj del sistema y contra la
fecha de autoria de cada commit (`git log --diff-filter=A --format=%aI`).

| artefacto | ID declara | commit real (autoria) | desfase |
|---|---|---|---|
| `RQ-EXP-HSBC-ATAQUE-001` | 20260821T2000Z | 2026-08-19T15:22Z | +53 h |
| `RQ-PREREG-HSBC-002-ATAQUE` | 20260821T1200Z | 2026-08-19T15:07Z | +45 h |
| `RQ-PREREG-AIRBUS-001` | 20260820T1900Z | 2026-08-19T14:47Z | +28 h |
| `RQ-DATA-HSBC-ULB-001` | 20260820T1700Z | 2026-08-19T14:43Z | +26 h |
| `RQ-PREREG-HSBC-001` | 20260820T1500Z | 2026-08-19T14:35Z | +24 h |
| `RQ-EXP-EON-D-K20-TRUNCADO-004` | 20260819T2200Z | 2026-08-18T23:10Z | +23 h |
| `RQ-EXP-EON-E-K08-005` | 20260819T2000Z | 2026-08-18T22:07Z | +22 h |
| `RQ-EXP-EON-E-K12-005` | 20260819T2000Z | 2026-08-18T22:07Z | +22 h |
| `RQ-EXP-EON-E-K16-005` | 20260819T2000Z | 2026-08-18T22:07Z | +22 h |
| `RQ-EXP-EON-E-REGRESION-X-005` | 20260819T2000Z | 2026-08-18T22:07Z | +22 h |
| `RQ-PREREG-EON-DICKE-001` | 20260819T1400Z | 2026-08-18T21:40Z | +16 h |
| `RQ-EXP-EON-D-K08-004` | 20260818T2100Z | 2026-08-18T18:32Z | +2 h |
| `RQ-EXP-EON-D-K12-004` | 20260818T2100Z | 2026-08-18T18:32Z | +2 h |
| `RQ-EXP-EON-D-K16-004` | 20260818T2100Z | 2026-08-18T18:32Z | +2 h |

## La direccion del error, con la correccion al primer analisis

El primer analisis interno concluyo que el error iba «en la direccion segura» porque las
fechas declaradas son posteriores al commit. **Esa lectura estaba invertida y se corrige
aqui**, porque la distincion importa:

- Para una **corrida**, declarar una fecha ANTERIOR al commit es lo normal y correcto: el
  experimento ocurre y se publica despues. Decenas de artefactos del archivo son asi y no
  tienen defecto alguno.
- El defecto es el contrario: **declarar una fecha POSTERIOR al commit**, que ademas es la
  unica de las dos que resulta fisicamente imposible.

Y donde peor cae es en un **pre-registro**, porque la afirmacion central de esta casa es
«la pregunta quedo fijada antes que el codigo». Caso concreto de este lote:
`RQ-PREREG-AIRBUS-001` declara `20260820T1900Z` mientras su propio borrador fuente se
publico el `2026-08-19T14:47Z` — leido al pie de la letra, el pre-registro «ocurrio» un dia
despues de que se publicara su propia fuente.

## Por que esto NO invalida ninguna afirmacion del archivo

Porque **la fecha autodeclarada nunca fue la evidencia**. El orden que Rosetta afirma lo
prueban dos relojes de terceros que nadie de esta casa controla:

1. **El historial de git** — fecha de autoria de cada commit, en dos remotos independientes.
2. **El ancla OpenTimestamps** — un bloque de Bitcoin, que acota por arriba.

Cuando una fecha autodeclarada contradice a una de tercero, **gana la de tercero**, y las de
tercero situan cada sello ANTES de lo que su propio ID declara. El defecto nos hace ver
desordenados; no mueve un solo veredicto. Verificable por cualquiera con los dos comandos de
arriba.

## Lo que no se hizo, y por que

No se reescribio ningun identificador. Publicado es publicado: los sellos estan anclados y
sus hashes citados; renombrarlos invalidaria anclas reales para maquillar una marca de
tiempo. Se marca, no se reescribe — la misma regla que gobierna las erratas del archivo.

## El arreglo hacia adelante

No es «acordarse de mirar el reloj»: un control que vive en un prompt no es un control
(CLAUDE.md §4). Son dos capas, en dos actores distintos:

1. **El sellador genera el ID desde el reloj del sistema**, nunca desde el contexto de quien
   redacta (lado laboratorio).
2. **El notario falla cerrado**: `notarize.py` compara la fecha del ID de cada artefacto
   contra el momento de anclar y **aborta si alguna es futura** — salvo las declaradas aqui.
   Vive en el notario ademas del sellador a proposito: es la comprobacion que hace **otro
   actor**, y un guardia que solo vive en quien produce es un guardia que se revisa a si mismo.
