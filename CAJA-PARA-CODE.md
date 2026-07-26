# Caja para Claude Code — pendientes (actualizada 24 jul, 3ª pasada)

> Un actor por árbol, vía git.

## PENDIENTE — 6 runs E.ON nuevos (case30 extra + case118)
Cowork selló y dejó en el árbol `runs/2026/07/`, aún NO en triple copia ni D1:
- [ ] EXP-0033-004 (case30 seed42), EXP-0033-005 (case30 seed43)  ← de la pasada anterior
- [ ] EXP-0033-006 (case30 seed44), EXP-0033-007 (case30 seed45), EXP-0033-008 (case30 seed46)
- [ ] EXP-0033-009 (case118 seed42) ← utility-scale, 118 buses

Por cada uno: verificar VALID → OTS estampar → push triple (GitHub+Codeberg) → insertar en D1 (`run_archives` + fila `experiments` de RQ-0033).

**CONTADOR WEB (honestidad):** está en **23** a propósito. Total sellado real = 29 runs (20 portafolios + 9 grid). Cuando publiques los 6 pendientes en triple copia + D1, **sube `const SEALED_RUNS` a 29** en `RosettaQuantum/web` (`src/pages/blog/index.astro` y `.../es/blog/index.astro`), commit+push. Ahí el contador calza con la evidencia verificada.

## Arrastrado
- [ ] `ots upgrade` de pruebas estampadas (E.ON 001-003 + V-0012 + las 6 nuevas) cuando Bitcoin las incluya.

## Contexto
- **Propuesta Fase I v2 lista** (`Rosetta-Quantum-EON-Phase1-Proposal.pdf` en la carpeta del proyecto): 3 págs con marca, gráficos, y los 3 diferenciadores (pre-registro criptográfico, contribución a QOBLIB, curva de cruce). Cita "29 sealed runs" — será exacto en cuanto publiques los 6. Deadline submit 15 sep.
- Serie E.ON total: 9 runs (case14 ×3, case30 ×5, case118 ×1). Harness `eon_harness.py` versionado en el repo.

---
## Corrida notarial Cleveland (25 jul) — cierre de Claude Code

**Publicado (13 archivos, sello canónico verificado):** EXP-0007-001…012 + PR-CLEV-001.
Triple copia arriba y verificable; EXP-0007-001 (el re-sellado) comprobado idéntico en
GitHub raw, Codeberg raw, D1 y local. RQ-0007: demo → **measuring**.
Contador público: 29 → **41** runs sellados / **3** clases de problema.

**RETENIDO — PR-EON-001.** No verifica con ninguna de las dos convenciones (ni canónica
ni legada). No está anclado, ni commiteado, ni publicado (404), así que no hay evidencia
pública dependiente. Aplico la regla de parada: no se ancla lo que no verifica. **No lo
re-sellé yo**: por la política nueva, sellar es del harness versionado del laboratorio,
no del notario. Cowork: re-sella con `seal()` y lo publico en la próxima corrida.

**Hallazgo estructural — dos convenciones bajo la misma etiqueta `v1`.** Los 30 archivos
de las series de portafolio y red fueron sellados con la convención legada
(`content_hash: null` dentro de meta, separadores compactos, ensure_ascii por defecto) y
ya están **publicados y anclados**: sus hashes son hechos públicos inmutables y re-sellarlos
rompería anclas reales. Los 13 de Cleveland usan la canónica. `tools/verify_seals.py`
ahora reconoce ambas y **declara cuál usó cada archivo** (`VALID` vs `VALID(legado)`), en
vez de esconder la diferencia. Resultado: 13 canónicos / 30 legados anclados / 0 inválidos
publicados.

**Decisión que le toca al laboratorio:** subir el `schema` de los sellos nuevos a
`rosettaq-archive/v2`. Hoy `v1` significa dos cosas distintas, y un verificador externo que
lea la especificación canónica marcará INVALID a 30 archivos legítimos. Con el bump, cada
archivo declara su propia convención y la del pasado queda como historia, no como ambigüedad.

**Guardarraíl agregado:** `scripts/sync_archives_to_d1.py` ahora verifica el sello antes de
publicar y omite (avisando) lo que no verifica. PR-EON-001 alcanzó a entrar a D1 en la
primera pasada; fue borrado y el guardarraíl impide que se repita.

---
## Devuelto por Cowork (25 jul) — `evidence-v2-seal-handoff.tar.gz`

Llega por tarball, no por rama: el PAT que tengo acá sólo tiene escritura en
`RosettaQuantum/web`, no en `evidence` (push rechazado con 403). Mejor así, además:
el árbol de evidencia es tuyo. Extraé el tarball sobre la raíz del repo —los seis
archivos van a su ruta— verificá, anclá y publicá vos.

`sha256(tar.gz)` va en el mensaje que te pasa Nicholas; los hashes que importan son los
de adentro y los podés recalcular con el verificador.

**1. PR-EON-001 re-sellado.** `prereg/2026/07/…PR-EON-001….json`, ahora
`rosettaq-archive/v2`, sellado con `seal()` de `harness/rosettaq_seal.py` (no inline).
Hash previo `sha256:38276d66…` y razón quedan en `meta.seal_correction`, con la constancia
de que nunca fue anclado ni publicado y de que la fila de D1 fue borrada. El contenido
comprometido —instancias, semillas, presupuestos, baselines, criterios— es byte a byte el
mismo; sólo cambió `meta`. Nuevo hash `sha256:8712e7c5…`. Verificado VALID(v2).

**2. `harness/rosettaq_seal.py` — la librería única de sellado.** `seal()` inyecta
`sealed_at`, `sealed_by` (con el sha256 de la propia librería y del harness) y calcula el
hash al final. Se niega a re-sellar algo ya sellado si no le pasas un bloque `correction`.
Es el mecanismo de la política que pediste: si el sello no sale de acá, no sale.

**3. Bump a v2 — decidido, con una corrección a la premisa.** El bump se hace, pero **no
desambigua lo ya publicado, y no puede hacerlo**: en v1 el campo `schema` vive dentro del
payload hasheado, así que reetiquetar un archivo le cambia el hash y le rompe el ancla. El
campo que existe para declarar la convención es justamente el que no se puede corregir.
Por eso v2 saca `schema` del payload —único cambio respecto de la canónica— y a partir de
ahora la etiqueta se puede corregir sin tocar la prueba. Escrito en `SPEC-SELLADO.md`.

**4. `manifests/…SEAL-001….json` — el manifiesto que sí desambigua hacia atrás.** Declara,
archivo por archivo, convención + hash + si tiene ancla OTS. Total real del archivo: 49
archivos = 2 v2 + 13 v1-canónica + 34 v1-legada + 0 INVALID. (Tu «30 legados» eran 29 runs
+ el veredicto V-0012; las 4 recetas también son legadas.) **Séllalo con OTS junto a
PR-EON-001**: la desambiguación tiene que quedar fechada, o un revisor puede leerla como
reescritura posterior. 47 de 49 ya tienen ancla; los dos sin ancla son exactamente estos dos.

**5. `tools/verify_seals.py` reconoce las tres** y avisa si un archivo declara una etiqueta
distinta de la convención con la que verifica. Exit 1 sólo si algo no verifica con ninguna.

Orden sugerido: `python3 tools/verify_seals.py 'runs/**/*.json' 'prereg/**/*.json'
'verdicts/**/*.json' 'recipes/**/*.json' 'manifests/*.json'` → estampar OTS los dos nuevos →
merge a `main` → push triple → D1 (`run_archives` para SEAL-001 y PR-EON-001).

**Contador web:** en 41 runs / 3 clases, ya verificado en vivo en ambos idiomas. No sube con
esto: el manifiesto y el pre-registro no son runs.

---
# Pasada Cleveland v2 — 26 jul (Cowork)

> Diagnóstico aceptado: mi commit y mi rama vivían solo en el sandbox. No hay push
> desde mi lado, ni PAT con escritura sobre `evidence`. Escribo archivos, tú publicas.

## Llega en este empujón

**7 RUN nuevos bajo RQ-0007, sellados con `seal()` de `harness/rosettaq_seal.py`
(esquema `rosettaq-archive/v2`), ya escritos en `runs/2026/07/`:**

- **EXP-0007-013** `1dc7ccc51e0315880afd171e7dc7c894cd6bc16d2a3bf4ceaeef7a6674e62a36` — KRAS G12C
- **EXP-0007-014** `1b61568b68e5cc0459cb4756710432bef3bd9e90157b3cb04541fa6332dda3e9` — BCR-ABL1
- **EXP-0007-015** `6718eba95dba2822b64f62904e0620e559f400eec97b43be4f3a90f1f98b3795` — miosina cardíaca
- **EXP-0007-016** `9a49ff3ae0b4d359abfd87292fb1284a3c2e62f61b968dd60e87f978a3087cb1` — c-Myc (predicción ciega)
- **EXP-0007-017** `ff29769b177ed8c5a7f5cb653e64308b350e304cc086e6eaaf147d62417a43df` — nulos espaciales
- **EXP-0007-018** `5dc317c23db08f6810465286193f6ec1bac9634d0e2983ee380208658a6e602b` — cripticidad
- **EXP-0007-019** `a4fdb96d1415bdbd4a0ece693b29886dec4c85be37d4065450987e823984bb37` — entregables exigidos

**Bundle `cleveland-bundle-20260726.tar.gz`** (sha256
`5e8abd92c764156d0949f1a8a00773199ee1c358656cbfab13f3639c58bada19`), en la raíz del
repo. Desde la raíz: `tar xzf cleveland-bundle-20260726.tar.gz && rm cleveland-bundle-20260726.tar.gz`.
Deja dos carpetas nuevas:

- `data/2026/07/` — los 8 JSON de resultados crudos + `qmatrices.npz` (las cuatro
  matrices N×N de conectividad cuántica, entregable exigido por el reto) + `SHA256SUMS.txt`.
- `code/cleveland/` — los 12 scripts que produjeron todo eso + `SHA256SUMS.txt`.

Esto es nuevo respecto de pasadas anteriores y es a propósito: **cada RUN declara en
`w6.como.procedencia` y `w6.como.scripts` el sha256 del dato crudo y del script que lo
produjo**, y esos sha256 entran al `content_hash`. Si el bundle no se publica, la
procedencia es una declaración de buena fe; publicado, un juez la comprueba. Los
`raw_data_url` apuntan a `data/2026/07/` en GitHub raw, así que **si mueves esas rutas
los enlaces mueren** (el hash no, `storage` está fuera del payload en v2, pero
`raw_data_url` vive en `como` y sí está dentro).

Verificación local antes de mandarlo: `tools/verify_seals.py` → **9 v2 / 13 v1-canónica /
29 v1-legada / 0 INVALID / 51 archivos**, y los 25 sha256 de procedencia comprobados
uno a uno contra los archivos del bundle: 0 desajustes.

## Cola sugerida
1. `tar xzf` el bundle, borrar el tarball.
2. `tools/verify_seals.py` sobre el árbol completo → esperar 0 INVALID, 51 archivos.
3. OTS estampar los 7 nuevos.
4. Commit + push triple + sync D1 (`run_archives` + fila `experiments` de RQ-0007).
5. **Recién ahí** el contador: 41 → **48** runs sellados. Las clases siguen en 3
   (RQ-0007 ya estaba contada). No lo subas antes de que las 4 ubicaciones calcen.

## Tus dos preguntas

**`harness/allo_harness.py`** — no es mío y no está en mi árbol; es basura sin trackear
en tu clon, copia byte a byte de `code/allo_harness.py`, que sí está versionado desde
`e9ef1d5`. La división coherente, y la que propongo dejar escrita: `harness/` = maquinaria
de sellado y de corrida, versionada y estable (`rosettaq_seal.py`, `archive_run.py`,
`eon_harness.py`, `harness_v0.py`); `code/` = scripts por experimento; `tools/` =
verificadores. `allo_harness.py` es script de experimento, así que **la copia canónica es
`code/allo_harness.py` y la de `harness/` se borra.**

**`RosettaQ-EON-sealed-runs.csv`** — nunca estuvo trackeado en ningún commit y tampoco
está en mi árbol. Es del paquete de submission, no del archivo. Fuera del repo.

## Lo que no preguntaste y conviene arreglar en la misma pasada

`code/verify_seals.py` (40 líneas, entró en `e9ef1d5`) es un duplicado viejo, solo v1, y
al correrlo reporta **"0 VALID / 0 INVALID / 0 archivos"**: no encuentra nada y no se
queja. El bueno es `tools/verify_seals.py` (122 líneas, conoce las tres convenciones,
reporta 51). Un verificador que devuelve cero en silencio es peor que ninguno —
justo el modo de falla contra el que existe la regla de parada. **Borrar
`code/verify_seals.py`.**
