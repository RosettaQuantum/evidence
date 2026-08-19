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
