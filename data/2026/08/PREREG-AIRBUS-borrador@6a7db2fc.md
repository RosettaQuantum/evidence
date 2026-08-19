# Borrador de pre-registro — track Airbus (RQ-PREREG-AIRBUS-001)

Redactado por la sesión de coordinación el 20-ago-2026, ANTES de escribir una línea del
instrumento. Para que el laboratorio lo selle con su maquinaria (patrón `seal_prereg_dicke.py`:
el sello en ASCII, este texto como fuente, el commit del sello anterior en el historial a todo
artefacto del track). El statement oficial se ancla por sha256:
`Airbus-Challenge-Statement-vF.pdf` = `4a2e084dd25d4934…` (recomputar completo al sellar).

## 1 · Pregunta pre-registrada

Sobre el vórtice de Taylor-Green convectivo 2D (Navier-Stokes incompresible, el caso del
statement): **¿dónde, sobre el eje del número de Reynolds, se cruzan — si se cruzan — las curvas
de tiempo-y-error de un solver cuántico de PDEs y de los solvers clásicos de referencia,
midiendo el error contra la solución analítica exacta?**

## 2 · Los dos desenlaces son entregables — declarado ANTES de medir

- **Si el retador cuántico cruza en algún punto del eje**: el cruce es incuestionable porque el
  árbitro es una fórmula cerrada, no una estimación.
- **Si no cruza en ningún punto**: la curva completa tiempo-y-error vs Reynolds ES el entregable
  que el statement pide («a plot characterizing the obtained (or estimated) time-to-solution and
  the numerical error across a range of Reynolds»). No hay plan B: hay dos resultados posibles y
  ambos se publican sellados.

## 3 · Riesgo conocido, declarado aquí y no descubierto después

El obstáculo lo admite el propio brief (§3.2): la física es **no-lineal y no-unitaria**, el
hardware cuántico es lineal y unitario. La linealización de Carleman trunca, y el orden de
truncamiento acota qué Reynolds son honestamente alcanzables por el brazo cuántico en un piloto.
**Expectativa pre-declarada**: el piloto cuántico será competitivo, si lo es, sólo en Reynolds
bajos y mallas chicas; el valor del track no depende de que gane — depende de que la curva sea
exacta y reproducible.

## 4 · Protocolo de comparación

- **Árbitro**: la solución analítica del statement (§5.3), evaluada en la malla en el tiempo
  final T. El error es L2 relativo del campo de velocidad contra la fórmula. Sin árbitro
  aprendido, sin árbitro numérico: fórmula.
- **Brazos clásicos** (los dos, para no comparar contra un espantapájaros): (a) espectral
  (calidad de referencia en malla periódica); (b) diferencias finitas de 2.º orden (el método
  de ingeniería). Presupuesto de pared idéntico por punto, declarado en el artefacto.
- **Brazo cuántico v1**: linealización de Carleman (orden declarado en cada artefacto) +
  evolución del sistema lineal por método variacional en statevector. Sin QPU en esta fase
  (cero gasto de cuota; hardware sólo con OK explícito de Nicholas).
- **Eje**: Reynolds creciente con la malla acoplada según el statement («grid resolution must
  increase with Reynolds number»); la regla de acople se fija en el instrumento y viaja en cada
  artefacto.
- **El rango de Reynolds no se elige a mano**: arranca donde los tres brazos resuelven con
  error < 1 % y sube hasta que el brazo de diferencias finitas degrada visiblemente (error
  > 10 % en el presupuesto declarado) o el brazo cuántico agota memoria — **el punto de corte
  se mide y se declara, no se decide** (la lección del K=20).

## 5 · Guardias del instrumento (fallan cerrado; se prueban por mutación antes de correr)

1. En t=0 el campo inicial reproduce la analítica al epsilon de máquina, o aborta.
2. Cada artefacto declara lo que OCURRIÓ, no lo que se pidió (§4 sexies): malla real, pasos
   reales, orden de Carleman real, `harness_sha256`.
3. Un `nan` o un campo vacío en cualquier brazo aborta la corrida entera — la ausencia no viaja
   como valor (§5 quater).
4. La procedencia se publica en el mismo acto que el sello (la lección de eon_estocastico).

## 6 · Qué NO afirma este track

No se afirma ventaja cuántica salvo cruce medido con el protocolo de arriba. No se extrapola la
curva más allá del último Reynolds medido. No se compara contra solvers comerciales de CFD que
no corrimos.
