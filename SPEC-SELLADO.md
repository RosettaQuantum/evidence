# Especificación de sellado — RosettaQ

> **Addendum (2026-08-10):** a fourth, newer seal convention exists — **v3**
> (`rosettaq-archive/v3`, RFC 8785 / JCS canonicalization, reproducible from any
> language). The first v3-sealed file is `RQ-REPORT-CLEV-METHOD-001`; every v3 seal
> **describes its own convention** in `sealed_by.convention`, so it can be verified
> without this document. This spec predates v3 and covers only v1/v2; the updated
> edition (regenerated from the archive, not written by hand) is pending review and
> will replace this note. Verify counts yourself: `tools/verify_seals.py`.

> Cómo se calcula el `content_hash` de cada archivo de este repositorio, por qué
> hay tres convenciones, y cómo verificar cualquiera de ellas.

Verificador de referencia: [`tools/verify_seals.py`](tools/verify_seals.py).
Librería de sellado: [`harness/rosettaq_seal.py`](harness/rosettaq_seal.py).
Manifiesto archivo-por-archivo: [`manifests/RosettaQ__MANIFEST__SEAL-001__seal-conventions.json`](manifests/RosettaQ__MANIFEST__SEAL-001__seal-conventions.json).

```bash
python3 tools/verify_seals.py 'runs/**/*.json' 'prereg/**/*.json' \
                              'verdicts/**/*.json' 'recipes/**/*.json' 'manifests/*.json'
```

## Convención vigente — `rosettaq-archive/v2`

```
content_hash = "sha256:" + sha256(
    json.dumps({"meta": meta_reducido, **cuerpo},
               sort_keys=True, ensure_ascii=False)     # separadores por defecto
)
```

`meta_reducido` es `meta` sin `content_hash` y sin `schema`. `cuerpo` son todas las
claves de nivel superior salvo `meta` y `storage`.

Cada exclusión, con su razón: `content_hash` es autorreferencia y no puede estar dentro
de lo que resume; `schema` es el puntero a la convención de hash, no contenido medido;
`storage` describe dónde vive la copia, no qué dice el archivo, así que espejar una copia
en un cuarto sitio no debe cambiar el sello. Todo lo demás —incluido `seal_correction`—
entra al hash.

## Por qué existe el bump a v2

En `v1` el campo `schema` vive dentro de `meta`, y `meta` entra al payload hasheado.
De ahí sale un lazo cerrado: **cambiarle a un archivo la etiqueta que declara cómo fue
hasheado le cambia el hash y le rompe el ancla OpenTimestamps.** El campo que existe para
identificar la convención es justamente el que no se puede corregir nunca.

v2 saca la etiqueta del payload. El sello sigue atado a todo el contenido; sólo el puntero
de convención queda corregible. Esto no debilita la prueba: la convención es auto-evidente,
porque sólo una reproduce el hash almacenado, y el verificador las prueba todas. La etiqueta
es una pista para el lector, no la prueba.

## Convenciones históricas

`v1-canónica` es idéntica a v2 salvo que `schema` sí entra al payload. La usan los 13
archivos de la serie Cleveland (`EXP-0007-001…012` y `PR-CLEV-001`).

`v1-legada` es:

```
content_hash = sha256(
    json.dumps({"meta": {**meta, "content_hash": None}, "w6": w6},
               sort_keys=True, separators=(",", ":"))   # ensure_ascii por defecto = True
)
```

Tres diferencias con la canónica: `content_hash` se anula en vez de quitarse, los
separadores son compactos, y `ensure_ascii` queda en `True`. La usan 34 archivos: las
series de portafolio (`EXP-0012-*`), de red (`EXP-0033-*`), las cuatro recetas y el
veredicto `V-0012`. Las primeras series además guardaron el hash sin el prefijo `sha256:`;
el verificador acepta ambas formas.

## Qué no se hace hacia atrás

Los archivos ya publicados están anclados en OpenTimestamps. Sus hashes son hechos públicos
inmutables que cualquiera puede citar: re-sellarlos invalidaría anclas reales. Reetiquetarlos
tampoco es una opción, por el lazo cerrado descrito arriba. Así que no se toca nada de lo
anclado. La ambigüedad se resuelve por los dos extremos: hacia adelante con v2, y hacia atrás
con el manifiesto `SEAL-001`, que declara archivo por archivo qué convención usa y si tiene
ancla. El manifiesto está sellado bajo v2 y anclado él mismo, para que la desambiguación
quede fechada y no pueda leerse como una reescritura posterior.

## Regla de proceso

Todo sello nuevo pasa por `seal()` de una librería versionada que se archiva junto al run.
Sellar inline está prohibido: las dos anomalías conocidas de este archivo (`EXP-0007-001` y
`PR-EON-001`, ambas selladas sobre una serialización irrecuperable) vienen de ahí, y las dos
quedan registradas en su propio `meta.seal_correction` en vez de borradas. `verify_seals.py`
corre antes de cualquier anclaje OTS y no se estampa nada si algo sale INVALID.
