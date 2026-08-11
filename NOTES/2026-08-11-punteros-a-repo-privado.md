# Un puntero a un repo privado es una promesa que muere en la mano del que verifica

**El caso.** El sello `RQ-EXP-CLEV-BLIND-001` —la predicción ciega de Cleveland, el resultado
negativo— declara en `w6.como.raw_result_url` la ruta `quantum-run/scoring/RESULTADO.json`.
Ese repositorio es **privado**. El sello verifica perfecto: su hash reproduce y su contenido
no cambió. Lo que no funciona es el paso siguiente, el que ofrecemos nosotros: *«y si quieres,
baja el resultado crudo y míralo tú»*. Quien lo intente llega a un 404.

Es la §1 bis en su forma más incómoda, porque **no hay nada roto**: hay una promesa cuyo
camino se corta, y sólo se descubre si alguien la recorre entera hasta el final.

**Qué se hizo.** El archivo está publicado aquí, anclado por su contenido:

```
data/2026/08/scoring_RESULTADO@17e0360f.json      3.186 bytes
sha256: 17e0360ff4cf606c…
```

Ese hash es el mismo que el archivo tiene en el repo privado — verificado al publicarlo, no
supuesto. Así que la ruta del sello y este archivo son el mismo objeto, y quien recompute el
hash de cualquiera de los dos obtiene lo mismo.

**Qué NO se hizo, y por qué.** No se corrigió el sello. Está anclado y publicado, y la regla
de la casa es que **publicado es publicado: las correcciones son archivos nuevos**, nunca una
reescritura. Un sello reescrito, por más que la corrección sea de buena fe, destruye lo único
que el sello sirve para probar. Esta nota es la corrección.

**La regla que sale de aquí, para lo que viene.** Un campo que dice dónde está algo tiene que
decir dónde está **para quien lo va a buscar**, no para quien lo escribió:

> Toda ruta que aparezca en un sello se escribe desde el punto de vista de un tercero sin
> acceso a nuestras máquinas ni a nuestros repositorios privados. Si el archivo referido no
> está publicado en el momento de sellar, o se publica antes, o el campo dice explícitamente
> que no es alcanzable — pero no se escribe una ruta que sólo funciona adentro.

La forma barata de comprobarlo es la de siempre: **seguir la instrucción propia hasta el
final, como si uno fuera el tercero.** Una ruta relativa a un repo privado se ve exactamente
igual que una que funciona.
