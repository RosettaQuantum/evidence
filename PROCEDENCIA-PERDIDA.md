# Procedencia declarada PERDIDA de forma permanente

Este archivo existe para que un hueco conocido deje de parecer un pendiente. Cada entrada
es una referencia de procedencia que **algún sello cita por sha256 y que no vamos a poder
publicar nunca**, con la búsqueda que lo determinó — el denominador, no sólo la conclusión.

Un hueco declarado es honesto; un hueco que se arrastra sin nombre no lo es. La diferencia
práctica: el auditor de procedencia cuenta estas referencias aparte, así que el número de
«sin publicar» vuelve a significar «pendiente de publicar» en vez de mezclar lo pendiente
con lo imposible.

---

## `sigo_features.py` — `sha256:0460d1f638c1244e…`

**Lo declaran**: `EXP-0007-020`, `EXP-0008-001`, `PR-ITER2-001` (3 referencias).

**Estado**: perdido de forma permanente. Ese blob nunca entró a ninguno de los dos
repositorios, así que el truco que sí funcionó con `rosettaq_seal@0965542a` —recuperar la
versión exacta del historial de git por su hash— aquí no aplica.

**Dónde se buscó** (búsqueda de la sesión de laboratorio, 2026-08-11):

| Dónde | Qué se encontró |
|---|---|
| Historial git de `quantum-run` | sólo `882c5311` |
| Historial git de `evidence` | `882c5311` y `5ad5e838` |
| Suelto en `~/Documents` y `~/Desktop` | los mismos dos |
| Dentro de **todo** lo comprimido bajo `~/Documents/Claude` (`tar.gz`, `tgz`, `zip`) | un solo archivo lo contiene: `traspaso/rosetta-engine-selfcontained-20260807.tar.gz`, y su `sigo_features.py` es `882c5311` |

**Qué significa para quien verifica.** Los tres sellos que lo citan siguen verificando
perfecto: su hash reproduce, su contenido no cambió. Lo que **no** se puede hacer con ellos
es el paso extra que ofrecemos —bajar el archivo de procedencia y recomputar su hash— para
esa referencia en particular. Las otras referencias de esos mismos sellos sí resuelven.

**Qué NO se hizo, y por qué.** No se sustituyó por una versión parecida (`882c5311` o
`5ad5e838`). Publicar otra versión bajo el nombre del hash perdido convertiría un hueco
declarado en una afirmación falsa, que es estrictamente peor: el verificador diría «resuelto»
sobre un archivo que no es el que se usó.

## `eon_estocastico.py` — `sha256:da73c313…`

**Lo declara**: `RQ-EXP-EON-ESTOCASTICO-001` (1 referencia).

**Estado**: perdido de forma permanente. El archivo se selló el 14-ago citando la versión
que corría ese día; el 17-ago se editó en el árbol de trabajo (51 KB → 97 KB, el trabajo
del mapa de dureza) **sin que la versión sellada se hubiera commiteado nunca**. El archivo
vivo actual es `2e0b6478…` — otra versión, no la citada.

**Dónde se buscó** (búsqueda de la sesión de laboratorio, 2026-08-18):

| Dónde | Qué se encontró |
|---|---|
| Historial git de `evidence` (todas las ramas) | sólo versiones con otro hash |
| Por hash en todo `~/Documents/Claude` | el vivo (`2e0b6478…`), nunca `da73c313…` |
| Snapshots de Time Machine | los locales son del 18-ago, posteriores a la edición |

**Qué significa para quien verifica.** El sello que lo cita sigue verificando perfecto: su
hash reproduce, su contenido no cambió. Lo que no se puede hacer es el paso extra —bajar
el archivo de procedencia y recomputar su hash— para esa referencia. Las demás referencias
del mismo sello (`barrido_eon_estocastico@525520d3.csv`, `pruebas_eon_estocastico@239d36ba.log`)
sí resuelven: se publicaron el 18-ago.

**Qué NO se hizo, y por qué.** No se sustituyó por la versión viva (`2e0b6478…`): publicar
otra versión bajo el nombre del hash perdido convertiría un hueco declarado en una
afirmación falsa. Y la lección quedó cerrada como regla el mismo día: **la procedencia se
publica en el mismo acto que el sello, o el sello nace con una promesa a plazo** — los
lotes D y E ya se sellaron con todo publicado antes.

---

## Seis mas, del 19-ago-2026 — todas de la misma causa estructural

Aparecieron al arreglar el alcance del auditor el 19-ago-2026 (miraba 95 de 108 sellos).
De las 10 referencias que la zona ciega ocultaba, **4 se recuperaron y ya están publicadas**;
estas 6 no. **La búsqueda está agotada, y eso es parte de la declaración** — no es «no las
encontramos», es que se buscaron por CONTENIDO en todos los blobs de la historia completa
de los dos repositorios (1.177 objetos en `evidence`, 295 en `quantum-run`), más los
archivos vivos de todo el proyecto, la Papelera y `/tmp`. Ninguno de los cinco hashes
aparece; `git log --all` confirma además que `build_methodology_en.py` y `predict.py`
nunca vivieron versionados. **Ninguna se sustituye por una versión parecida.**

| archivo | sha256 | lo declara | por qué se perdió |
|---|---|---|---|
| `build_methodology_en.py` | `sha256:b99c136c1ee39ea1…` | RQ-REPORT-CLEV-METHOD-001 | el generador se editó entre revisiones sin publicar cada versión |
| `build_methodology_en.py` | `sha256:66e1c953565c351c…` | RQ-REPORT-CLEV-METHOD-002 | ídem |
| `build_methodology_en.py` | `sha256:160307455737aacd…` | RQ-REPORT-CLEV-METHOD-003 | ídem |
| `build_methodology_en.py` | `sha256:7b570fc61f2b6e70…` | RQ-REPORT-CLEV-METHOD-004 | ídem |
| `predict.py` | `sha256:3fb3750bed019d89…` | RQ-PRED-PARP1_ALLO | versión de julio, nunca publicada |
| `seal_data_ulb.py` | `sha256:d3ed02821b136f5c…` | RQ-DATA-HSBC-ULB-001 | el laboratorio lo modificó al migrarlo al reloj nuevo, sin que la versión sellada estuviera publicada |

**La quinta versión de `build_methodology_en.py` (`1ecb4c43…`, la de METHOD-005) SÍ se
recuperó** — estaba viva en `evidence-staging/` — y ya está publicada. O sea: de las cinco
revisiones del reporte de Cleveland, la última es reproducible y las cuatro anteriores no.

**Qué significa para quien verifica.** Los seis sellos siguen verificando perfecto: su hash
reproduce, su contenido no cambió. Lo que no se puede hacer con ellos es el paso extra que
ofrecemos —bajar el generador y re-correrlo— para esa referencia. Las demás referencias de
esos mismos sellos sí resuelven.

**La causa es una sola, es ESTRUCTURAL, y ya está cerrada por dos vías.** Las seis no son
un descuido repetido seis veces: son herramientas que nacen en `evidence-staging/`, que
**estaba fuera de control de versiones**. Un sello declara el sha256 de su productor; el
productor se edita después; los bytes declarados dejan de existir, sin que nadie haga nada
mal. Lo diagnosticó el laboratorio al agotar la búsqueda.

Cerrada por dos capas, ambas ya operando:
1. **Publicar en `code/` es parte del acto de sellar** (capa 1, del laboratorio) — nació el
   18-ago y ya opera en los lotes D, E y HSBC.
2. **`evidence-staging/` ahora tiene historial propio** (commit inicial `9fa4cf2`,
   19-ago): desde ahí, cualquier edición deja rastro y la recuperación por hash desde los
   blobs de git funciona siempre. Es el respaldo para cuando alguien olvide la capa 1 —
   exactamente lo que pasó con estas seis.
