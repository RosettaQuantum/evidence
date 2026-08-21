# El auditor de procedencia no ve las rutas armadas con plantilla

**21 de agosto de 2026 — sesión laboratorio.**

## Qué garantiza el auditor, y qué no

`scripts/check_provenance.py` responde bien la pregunta para la que se escribió: **¿todo
archivo citado por sha256 en un sello está publicado?** Hoy: 111 sellos, 290 referencias,
0 sin publicar.

Lo que **no** responde, y conviene que esté escrito al lado del número:

### 1 · No ve rutas construidas con plantilla

El auditor busca literales de cadena. Un script que abre su insumo así:

```python
pickle.load(open(os.path.join(CACHE, "%s.pkl" % name), "rb"))
```

no declara ningún nombre de archivo que el auditor pueda mirar. **Y ésa es exactamente la
forma que usa `poc_ibm.py`** — el harness que el sello `RQ-POC-QPU-001` declara en su
`harness_sha256`. O sea: el caso que más importaba pasaba en verde, y sólo apareció
buscando `pickle.load` a mano.

Cualquier auditor que analice literales de cadena hereda este agujero.

### 2 · «Publicado» no es lo mismo que «ejecutable»

`code/poc_ibm@db044b45.py` está publicado y su hash calza con el que el sello declara. Y
**no se podía ejecutar**: su insumo vivía sólo en `quantum-run`, que es un repositorio
privado, y además sólo se deserializaba con numpy 2.x.

La cadena tiene un eslabón más del que el auditor mira:

> **publicado → ejecutable → verificable**

El auditor cubre el primer paso. Los otros dos no los cubre nadie hoy.

**Medido el 21-ago-2026:** de los **42** scripts publicados en `code/`, **4** leen un
caché `.pkl` y hay **cero** pickles publicados. Son `poc_ibm@db044b45.py`, `engine.py`,
`iter2_run.py` y `qmargin@ec2340db.py`.

Adyacentes, del mismo día: `allobench_connector.py` baja `AlloBench.csv` de una URL
pública **sin hash fijado y sin declararlo** en `PROCEDENCIA-EN-FUENTE-DE-TERCEROS.md`;
y `build_cache@206011ba.py` lee `.pdb.gz` de un directorio local (recuperables del RCSB
por identificador, así que se declaran en vez de publicarse).

### 3 · Cómo se cierra, y qué NO hace falta

No hace falta publicar los pickles. El patrón que funcionó con KRAS: **que el artefacto
se baste solo**, con números planos en vez de binario.

| | pickle | portable |
|---|---|---|
| tamaño | 260 KB | 37 KB |
| ejecuta código al cargar | sí | no |
| depende de la versión de numpy | sí (2.x) | no |
| legible desde otro lenguaje | no | sí |

Publicado como `code/…` junto al sello que lo necesita, **con una guardia que falla
cerrado**: reconstruye desde el archivo portable y exige que dé el mismo sub-grafo —
mismos índices, mismos pesos, mismo potencial — y además compara los 169 residuos
completos, no sólo los 12 que le interesan al consumidor. Un guardia que sólo cubre la
parte que le importa se lee como si cubriera todo.

## La medición mal hecha, que es parte de la lección

La primera pasada de esta auditoría dijo **30 de 42**. Era falsa: el patrón contaba como
«insumo faltante» los archivos que los scripts **escriben** (`np.save`, `json.dump`) y
fragmentos de nombres de sellos que sí estaban publicados. Se revisó porque 30 de 42 era
demasiado alto para ser cierto — **si un chequeo falla en casi todo, el sospechoso es el
chequeo.** Separando lectura de escritura quedaron 4.

Y el caso central —`poc_ibm.py`— **no lo encontró ninguna de las dos pasadas
automáticas**, por el punto ciego 1. Apareció a mano.

## Qué queda pendiente

- Cerrar los otros 3 scripts con el mismo patrón.
- Declarar `AlloBench.csv` y los `.pdb.gz` en `PROCEDENCIA-EN-FUENTE-DE-TERCEROS.md`.
- Que `check_provenance.py` declare este punto ciego en su propia salida. Un control que
  no declara lo que no cubre se lee como si cubriera todo — y ese archivo es de la sesión
  de coordinación, así que la línea se propone, no se mete.
