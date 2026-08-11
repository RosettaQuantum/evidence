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
