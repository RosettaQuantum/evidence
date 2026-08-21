# Nota — dos archivos de coeficientes de case118, y cuál leer

**Lee `coef_case118@42d5faec.json`.** El anterior, `coef_case118@ce470472.json`, queda
publicado y no se toca.

## Qué cambió, y qué NO cambió

**No cambió ni un coeficiente.** Los 14 `relief_i`, los 91 `q_ij` y los 14 `cost` son
idénticos en los dos archivos. La medición es la misma.

Lo que cambió es **la afirmación que el archivo hace sobre su propia prueba**.

## El defecto

`@ce470472` publicaba `desviacion: 0.0` y `reproduce: true`, comparando con `==`. Era
verdad — en el numpy del CI, y sólo ahí. Ejercido desde afuera con numpy 1.23.5, el mismo
archivo da `-3,6e-12` en el mínimo, y quien lo ejerce lee que la prueba falla.

La suma de 21 términos que rondan `1e5` **no es asociativa en punto flotante**: el
resultado depende del orden de los sumandos y ningún orden es más correcto que otro. Tres
órdenes razonables dan tres últimos bits distintos:

| orden | mínimo |
|---|---|
| bucles `i` y luego `j` | `4295,4187275270815` |
| numpy `x @ Q @ x` | `4295,418727527089` |
| por magnitud creciente | `4295,418727527085` |

`0.0` era una afirmación más fuerte de la que el dato aguanta — y en un archivo que existe
justamente para que un tercero lo recompute, esa es la peor clase de afirmación de más.

## Cómo lo encontramos

Lo encontró la sesión **«Rosetta y tecnologías complementarias»** haciendo con un artefacto
nuestro exactamente lo que le pedimos al mundo que haga: bajarlo y recomputarlo. Se verificó
aquí antes de creerlo, en una tercera máquina, y reprodujo.

Vale registrar el mecanismo: **el defecto no lo encontró ningún guardia nuestro, lo encontró
el primer tercero que ejerció la promesa.** Un guardia que compara con `==` contra el
resultado de su propia máquina no puede detectar que no es portable: por construcción,
siempre se da la razón.

## Qué hace ahora `@42d5faec`

1. **Evalúa en tres órdenes y publica los tres**, para que el que lo ejerza vea cuánto se
   mueven los últimos bits en vez de creer que encontró un error.
2. **Compara contra una tolerancia derivada, no elegida**: `n · eps · Σ|términos|`, la cota
   clásica del redondeo de una suma de `n` términos. Da `4,5e-10`, contra una desviación
   peor observada de `7,3e-12` — dos órdenes de margen.
3. **Separa las dos afirmaciones, porque una es portable y la otra no:**
   - el **argmin** —cuál de los 2002 subconjuntos gana— reproduce **exacto** en los tres
     órdenes y en las dos máquinas;
   - el **valor** reproduce **dentro de la tolerancia**, que es lo máximo que se puede
     afirmar de una suma de punto flotante.

Y el propio artefacto lo dice, en `prueba.que_significa_el_veredicto`: si lo ejerces y
obtienes una diferencia de orden `1e-12`, no encontraste un error, encontraste esto.
