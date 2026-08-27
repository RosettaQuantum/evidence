# Pre-registro · calibración del instrumento contra desenlaces publicados

**Escrito ANTES de correr el instrumento sobre LLaMA-7B.** Fija qué papers, qué cifras y qué
cuenta como acierto o fallo, para que la curva no pueda validarse sola. Si el instrumento
falla, falla con testigo — y un instrumento que falla con su pre-registro publicado sigue
siendo mejor material que uno que acierta sin él.

## Por qué este contraste y no el de CompactifAI

CompactifAI valida un desenlace de **otra operación**: MPO reshapeado **más sanación**. La
nuestra es **truncamiento de la SVD 2D**. Validar contra su resultado dejaría un hueco obvio.
La familia de bajo rango sobre LLaMA-7B —SVD, FWSVD, ASVD, SVD-LLM— hace **nuestra misma
operación** y publica precisión a razones declaradas. Ése es el conjunto correcto.

## La definición que hubo que resolver antes, y cómo

Los papers dicen «compression ratio 0.2» sin definirlo en el texto que pudimos leer.
**Se resolvió con un dato objetivo, no suponiendo**: reportan 10,2 GB para razón 0,2, y
LLaMA-7B en fp16 son 13,5 GB teóricos. Fracción retenida daría 2,7 GB (no calza); fracción
**quitada** da 10,8 GB (calza). Por lo tanto:

| razón publicada | compresión real |
|---|---|
| 0,2 | 1,25× |
| 0,4 | 1,67× |
| 0,6 | 2,50× |

## Las cifras contra las que se compara — FIJADAS AQUÍ

Fuente: tabla comparativa de `arXiv:2602.03051` (SAES-SVD), leída de su HTML.
Perplejidad WikiText-2 sobre **LLaMA-7B**. Base sin comprimir: **5,68**.

| compresión | SVD simple | FWSVD | ASVD | SVD-LLM |
|---|---|---|---|---|
| 1,25× (razón 0,2) | — | 2e5 | 11,14 | 7,94 |
| 1,67× (razón 0,4) | — | 2e4 | 1e3 | 13,11 |
| 2,50× (razón 0,6) | — | 3e4 | 6e4 | 53,74 |

*La columna de SVD simple no trae valores en esta tabla; otra fuente los da como 20.061 /
52.489 / 105.474 y **no se usan hasta abrirla**. Si no se abre, no entran.*

## Lo que el instrumento calcula

Error relativo de Frobenius al truncar cada matriz de pesos al χ que da esa compresión,
sobre los pesos reales bajados por rango HTTP. Sin GPU. **Ninguna evaluación de precisión:
el instrumento no ejecuta el modelo.**

## LA PREDICCIÓN, escrita antes de correr

1. **El error de Frobenius a 2,50× será alto** —del orden de 0,4 a 0,6, como en LLaVA— y la
   perplejidad publicada a esa compresión es **53,74 contra 5,68: degradación de 9,5×**.
   Predicción: **error alto ↔ degradación catastrófica**.
2. **A 1,25× el error será notablemente menor** y la perplejidad publicada es 7,94 contra
   5,68: degradación de 1,4×. Predicción: **error bajo ↔ degradación tolerable**.
3. **La relación será monótona**: más error, más degradación, sin cruces.

## Qué cuenta como que el instrumento NO sirve

- Si el error a 1,25× resulta **mayor o igual** que a 2,50× — no ordena.
- Si el error a 2,50× es **bajo** (< 0,15) mientras la perplejidad publicada se multiplica
  por 9,5 — el instrumento no ve el desastre.
- Si la relación **no es monótona** entre los tres puntos.

Cualquiera de las tres y se reporta que **no calibra**, con estos números al lado.

## Lo que esta calibración NO demuestra aunque salga bien

- **No demuestra causalidad**: el error de Frobenius y la perplejidad pueden moverse juntos
  sin que uno prediga al otro fuera de este régimen.
- **Es un modelo, tres puntos.** No es una curva: son tres puntos de un modelo.
- **No dice nada sobre la sanación**: los métodos comparados no la usan, CompactifAI sí, y
  el instrumento no la modela.
- **No dice nada sobre otras topologías** (TTNS contra MPO) ni sobre combinar con
  cuantización, que es lo que hace el paper que el enunciado cita.

## Gasto autorizado

**US$0. Cero GPU.** Sólo descargas por rango HTTP y SVD en CPU.
