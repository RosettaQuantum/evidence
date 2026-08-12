# Apuestas registradas ANTES de ver el N=90 con la conservación viva

Corrida `31548450381`, lanzada desde un worktree sobre `origin/main` con el guardia
`exigir_features` cableado. Este archivo se escribe **antes** de que exista el artefacto.

**Por qué existe.** Una predicción dicha después del dato no se puede distinguir de una
racionalización. La coordinadora ofreció la suya sin que nadie se la pidiera y propuso
contrastarla; queda escrita con la mía al lado, y las dos se comparan contra el resultado
gane quien gane. Es el mismo mecanismo del pre-registro, en chico y sin ceremonia.

## Contra qué se compara

Del sello `RQ-EXP-N90-LOPO-002`, que es la corrida con la conservación **muerta**:

| | |
|---|---|
| armA (gestor cuántico) | `0,1066` · 2 de 90 significativas |
| armB (ML de features) | `5,056e-09` · 10 de 90 |
| armC (ML apilado) | `1,343e-07` · 11 de 90 |
| percentil medio por método | ctqw_bare 53,9 · glifo_fixed 55,3 · glifo_learned 57,7 · **diffusion 60,5** · gnm 46,4 |
| elecciones del gestor | diffusion 50 de 90 |

## Las apuestas

**Coordinadora**: el brazo A **no se mueve**. Si B o C se mueven, va a ser poco.

**Laboratorio**: coincido en A, y agrego dos que se pueden fallar por separado.

1. **armA no cambia de veredicto**: sigue sin alcanzar significancia. Es el brazo que elige
   entre propagadores, y la conservación no entra en ninguno de los cinco — entra en el
   *potencial* de `ctqw_glifo_learned`, que es sólo uno de los cinco candidatos y hoy gana
   en 21 de 90.
2. **armB se mueve más que armC.** La conservación es 1 de 15 columnas directas en B, y en
   C entra indirecta, a través de un propagador que después compite con otros cinco. Una
   feature directa pesa más que una filtrada por dos capas.
3. **`ctqw_glifo_learned` sube su percentil medio** desde 57,7 — es el único método al que
   la conservación llega — **pero no alcanza a la difusión (60,5)**. Si lo alcanzara, sería
   el primer resultado del proyecto que mueve la aguja a favor de lo cuántico, y habría que
   mirarlo con más desconfianza que entusiasmo: llegaría justo cuando lo necesitábamos.

## Cómo se resuelve

Se recomputa desde los conteos crudos con `analyze_n90.py`, se comparan las cinco cifras de
arriba, y **se reporta lo que salga**, incluidas las apuestas falladas. Una apuesta que se
falla y se cuenta vale más que una que se acierta y se celebra.
