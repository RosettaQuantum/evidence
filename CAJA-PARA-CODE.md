# Caja para Claude Code — pendientes notariales y de infra (al 24 jul 2026)

> Cowork (laboratorio + imprenta) dejó esto listo para tu mano (notario + git/deploy del repo evidence). Un actor por árbol, siempre vía git. Marca cada ítem cuando lo cierres.

## P1 — Notarización pendiente (repo `evidence`)
- [x] **OTS upgrade de los primeros 8 runs** (EXP-0012-001…008): Bitcoin ya debería haber confirmado (~horas desde el 23 jul). Corre `ots upgrade` y commitea las pruebas completas.
- [x] **OTS estampar + upgrade de los 12 nuevos** (EXP-0012-009…020) y del **veredicto V-0012**. Los 13 archivos ya están en el árbol (`runs/2026/07/` y `verdicts/2026/`), sellados y verificados VALID por Cowork.
- [x] **Push triple** (GitHub + Codeberg) de los 13 archivos nuevos + confirmar mirror verde.

## P2 — D1 ya está sincronizada por Cowork (solo verificar)
- Cowork ya insertó en D1: `run_archives` (20 runs reales), `verdicts` (V-0012, is_demo=0), `experiments` (20 filas con las brechas reales y raw_data_url a RosettaQuantum). Estado D1: 20 sealed_runs, 1 real_verdict, 20 experiments.
- [x] Verificar que tu `sync-ledger` (D1→ledger.json) sigue consistente; el ledger web ya se está sirviendo desde D1 en cada build (verificado en vivo: contador "1 verdict published").

## P3 — Erratas conocidas (bajo impacto, corregir cuando puedas)
- [x] En el archivo publicado **EXP-0012-001**, el bloque `storage` interno apunta a `RosettaQ/...` (URLs viejas). El sello cubre solo meta+w6, así que puedes corregir el `storage` a `RosettaQuantum/...` sin invalidar el hash — en las 3 copias a la vez. (Los runs 002+ ya salieron con URLs correctas.)

## P4 — Infra de deploy de la web (2 warnings amarillos en el CI de `RosettaQuantum/web`) — de Nicholas
- El token de Cloudflare del CI aún no puede **leer D1** (el ledger cae al snapshot commiteado) ni **purgar caché**. El deploy funciona igual. Cuando Nicholas amplíe el scope del token (D1:Read + Cache Purge), los warnings desaparecen y el ledger se sirve siempre desde D1 fresco.

## Contexto: qué viene (para que sepas hacia dónde va)
- Cowork va a girar el harness a la **clase de problema del challenge E.ON** (grid expansion / network expansion, formulación binaria → QUBO → QAOA) y correr una serie EXP nueva sobre una instancia IEEE/pandapower chica. Esos runs llegarán al mismo árbol `evidence/runs/` para tu notarización, igual que la serie de portafolios.
- La propuesta Fase I del challenge (deadline 15 sep) se redactará sobre esa evidencia. Intel completo en el proyecto Claude: `claude/rosetta-eon-challenge-intel.md`.

---
**Cierre de Claude Code (24 jul):** P1 completo (V-0012 notarizado; OTS: 001-008 completos desde antes, 9 anclas más confirmadas hoy, el resto pendiente de bloque — se upgradean en la próxima vuelta). P2 verificado. P3 corregido en las 3 copias (sello intacto, VALID). P4 ya estaba resuelto: el token del CI lee D1 y purga desde el arreglo de Nicholas — corridas verdes sin warnings.
