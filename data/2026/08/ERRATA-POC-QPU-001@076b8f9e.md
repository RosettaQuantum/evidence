# Errata — RQ-POC-QPU-001 (CTQW de KRAS en ibm_kingston)

**Qué corrige:** una afirmación del sello `RQ-POC-QPU-001`,
`content_hash sha256:d026eddc617f2ccdc631d20a01ca5694fa327daf7e6e357e308e50c2c952cbfb`,
anclado el 2026-08-04.

**Qué NO hace:** tocar ese sello. Publicado es publicado — el archivo original queda
como está, con su hash y su ancla intactos. Esta errata es un documento nuevo que se
encadena a él. Quien verifique el sello original lo encontrará idéntico y encontrará
esta corrección al lado.

**Dónde llegó el defecto:** al archivo y a notas internas. **No viajó al paquete
entregado a Cleveland**: se revisaron **los 5 archivos** de la postulación —los dos PDF,
el CSV de corridas selladas, el harness y el artefacto JSON— y ninguno menciona esta
corrida ni esta cifra. El CSV lista 12 corridas, todas de la serie EXP-0007; ninguna es
`RQ-POC-QPU-001`.

---

## 1 · La afirmación que se retracta

El sello dice, textual, en `w6/que/outcome`:

> «de lo que sobrevive, 62.6% de la masa cae en el bolsillo alosterico (**estructura, no
> ruido blanco**)»

Se retracta el paréntesis. La cifra que lo acompaña tiene dos problemas independientes.

## 2 · Defecto A — el número está mal calculado (etiquetas espejadas)

El bolsillo y la fuente se leyeron de la cadena de bits **sin invertirla**. En Qiskit el
carácter más a la izquierda de una cadena de conteos es el bit **más alto**, así que el
índice del nodo se obtiene invirtiendo: `b[::-1].index("1")`.

**El argumento se apoya en el harness que el propio sello declara**, y por eso no
depende de nada que el lector no pueda bajar: `ideal_probs` de `poc_ibm.py` —publicado
como `code/poc_ibm@db044b45.py`, el mismo sha256 que el sello registra en
`harness_sha256`— invierte la cadena antes de indexar. **El sello contradice a su propio
harness declarado.** El circuito mapea nodo = qubit = bit clásico (`qc.x(s)` y
`qc.measure(range(m), range(m))`), en ese mismo archivo.

Como evidencia concurrente se publica junto a esta errata `poc_ibm_run.py`, la otra
rutina de análisis del proyecto, cuyo `counts_to_p1` invierte y lo documenta en el
código: «qiskit: bit string little-endian».

**Un límite que hay que declarar:** el sello nombra al recolector `fetch_job.py` pero
**no registra su sha256**, así que no se puede fijar qué versión bajó estos conteos. Se
publica la versión actual como referencia, y se deja dicho que el argumento no depende de
ella: la contradicción se establece entre el archivo crudo publicado y el harness que el
sello declara, ambos verificables. Esa ausencia de hash es, en sí misma, una segunda
lección de la corrida — y es la que el paso 3 del plan viene a cerrar.

El efecto es un espejo exacto, nodo *i* ↔ nodo 11−*i*.

| magnitud | en el sello | corregido |
|---|---|---|
| masa en el bolsillo alostérico | 0,6262 | **0,3534** |
| masa en la fuente | 0,0358 | **0,1515** |

Lo demás del sello **se reprodujo exacto** desde el archivo crudo publicado: 2.000
disparos, 1.228 válidos one-hot, 301 cadenas distintas, supervivencia 0,614.

## 3 · Defecto B — el estadístico citado no sostiene la conclusión

El bolsillo son **8 de 12 nodos**, así que **ruido uniforme daría 0,6667**. Las dos
cifras —la sellada y la corregida— están **por debajo** de lo que daría el azar.

Con n = 1.228 (los válidos, que es la n efectiva: la masa es condicional a ellos) e
intervalo de Wilson al 95 %, calculado sobre los conteos enteros del archivo crudo:

| cifra | k | proporción | IC95 Wilson | ¿contiene el 0,6667? |
|---|---|---|---|---|
| sellada | 769 | 0,6262 | **[0,5988 – 0,6528]** | no — queda por encima |
| corregida | 434 | 0,3534 | **[0,3272 – 0,3806]** | no — queda muy por encima |

El estadístico que se citó como prueba de estructura apunta en la dirección contraria a
la frase que sostiene.

## 4 · Qué sí muestran los datos, y qué no

**La distribución no es plana.** χ² contra uniforme = **1.167,0 con 11 grados de
libertad** (crítico al 5 % = 19,7). Eso descarta ruido blanco.

**Pero su forma no es la de la caminata.** Reconstruimos la distribución ideal sin ruido
del mismo circuito y la publicamos junto a esta errata para que se pueda comprobar
(`dist_ideal_KRAS_G12C.json`). Contra ella:

| prueba | resultado | lee |
|---|---|---|
| Spearman ideal vs medido (etiquetas corregidas) | **+0,266** (p = 0,40) | sin señal |
| Spearman ideal vs medido (etiquetas del sello) | **−0,196** (p = 0,54) | sin señal |
| distancia total de variación | medido↔uniforme **0,408** vs medido↔ideal **0,616** | más cerca del uniforme |
| χ² del medido | contra uniforme **1.167**, contra ideal **18.804** | los dos se rechazan; el ideal, dieciséis veces más fuerte |

**La conclusión no depende de qué convención de bits se use**, que es lo que la vuelve
sólida: bajo las dos, la desviación respecto del uniforme no apunta hacia la física del
caminante. Una distribución no uniforme también la produce un sesgo dependiente del
dispositivo.

## 5 · Una explicación que probamos y descartamos

Con las etiquetas corregidas, la masa del bolsillo (0,3534) cae **entre** la ideal
(0,1874) y la uniforme (0,6667) — exactamente lo que produciría una caminata real
parcialmente lavada por ruido. Ajustamos ese modelo:

> medido = λ · ideal + (1 − λ) · uniforme

Resultado: **λ = 0,015**, con χ² 1.166,7 (10 gl) contra 1.167,0 del uniforme puro.
**Cero mejora** (los tres χ² sobre los mismos conteos enteros). La coincidencia estaba en el agregado; nodo por nodo no hay nada. Se
deja escrito porque era la lectura favorable y no sobrevivió a la prueba.

## 6 · Qué queda intacto

El propósito declarado de la corrida. `w6/porque/question` pregunta cuánto presupuesto
de coherencia consume hoy un CTQW de 12 nodos en hardware, y la respuesta —**61,4 % de
disparos sobreviven como física válida**— es correcta y se reprodujo exacta desde el
crudo. `w6/que/cruce_ventaja_cuantica = 0` también sigue siendo cierto: esta corrida
nunca afirmó ventaja.

**La afirmación corregida es:** el circuito se ejecuta en hardware real y el 61,4 % de
los disparos sobrevive como física válida; la estructura del caminante **no** sobrevive
al ruido — medido contra la caminata ideal, publicada aquí.

## 7 · Cómo comprobarlo usted mismo

**Sin nuestro código y sin nuestros repositorios.** El archivo
`dist_ideal_KRAS_G12C.json` —5 KB— trae adentro la matriz de adyacencia del sub-grafo
(`W`), el potencial on-site (`v`) y la fuente. Con eso se rehace la caminata entera:

```python
import json, numpy as np
from scipy.linalg import expm
d  = json.load(open("dist_ideal_KRAS_G12C.json"))["subgrafo_portable"]
W  = np.array(d["W"]);  v = np.array(d["v"])
p0 = np.zeros(len(v), complex);  p0[d["source_nodes"][0]] = 1.0
p  = np.abs(expm(-1j*(W + np.diag(v))*d["t"]) @ p0)**2
print(p/p.sum())        # == dist_exacta_por_nodo del mismo archivo
```

**Por qué va así y no como «corra nuestro script»:** el sub-grafo se derivaba de un
archivo `.pkl` que vive en un repositorio **privado** y que además sólo se deserializa
con numpy 2.x. Una receta que exige un archivo inalcanzable y una versión de librería no
declarada no es una receta verificable. El generador comprueba esto antes de emitir:
recomputa la distribución usando **sólo** los números que van dentro del artefacto y
aborta si difieren.

Quien además quiera regenerarlo desde el origen puede correr
`evidence-staging/ideal_ctqw_kras.py`, que aborta si no reproduce
`exact_pocket_mass` = 0,479934690883 e `ideal_pocket_mass` = 0,187374747761 del archivo
ya publicado `code/poc_result_KRAS_G12C@68aada40.json`, con tolerancia 1e-9. Publica
también `subgraph_node_ids`, para comprobar que se reconstruyó **el mismo** sub-grafo
antes de comparar distribuciones.

Los conteos crudos están en `code/poc_job_d9mu2bmij12s73ft86t0@3b45dd49.json`. La masa
corregida sale de contar con `b[::-1].index("1")`; la sellada, sin invertir.

**Todo archivo que esta errata cita se publica en el mismo acto que su sello** — la
distribución ideal, el script que la produce, `poc_ibm_run.py` y `fetch_job.py` —, de
modo que la comprobación no requiera pedirnos nada.

**Todas las cifras de esta errata se calculan sobre los conteos enteros del archivo
crudo, no sobre la distribución redondeada a cuatro decimales que guarda el sello.** La
diferencia es de la tercera cifra —χ² 1.167,0 contra 1.167,2— pero se declara porque un
número que depende de cómo se midió no se cita sin el cómo.

## 8 · Qué NO afirma esta errata

No afirma que el hardware sea incapaz de sostener una CTQW de 12 nodos: afirma que **en
esta corrida, con este circuito y este ruido**, la estructura no sobrevivió. No afirma
saber qué produce la no-uniformidad observada; sólo que no es la caminata. Y no revisa
las demás corridas del archivo — esta errata cubre `RQ-POC-QPU-001` y nada más.
