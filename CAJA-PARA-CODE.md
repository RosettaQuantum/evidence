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
