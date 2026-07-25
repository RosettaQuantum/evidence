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
