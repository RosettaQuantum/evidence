# Dos cambios al reporte de Cleveland — APROBADOS por Nicholas el 2026-08-12

Texto exacto a aplicar. No se parafrasea: se aplica tal cual o se pregunta.

---

## CAMBIO 1 — §9: devolver los siete `job_id` a la tabla

**Por qué.** El reporte anterior traía una tabla con los siete identificadores de los
trabajos enviados a IBM. El actual **no trae ninguno** y sin embargo sigue afirmando que
*«The seven job identifiers and their roles were sealed before any result existed, so the
analysis could not choose which jobs to count»*. Hacemos una afirmación verificable y le
quitamos al lector la manera de verificarla — nuestra propia §1 bis, cometida por nosotros.
Lo encontró Nicholas leyendo, comparando contra el reporte anterior.

**Qué hacer.** La tabla del §9 gana una columna `job_id`, entre `Role` y
`Measured pocket mass`. Los valores, leídos de `voyage2_manifest.json` (no de memoria):

| Role | job_id |
|---|---|
| positive control | `d9t16s7tfhrs73dtb550` |
| secondary control | `d9t16s8pdb6s73e6jh9g` |
| long-corridor exploration | `d9t16sgpdb6s73e6jha0` |
| repetition | `d9t16svpemts73cu9fhg` |
| replica of run 1 | `d9t16t7tfhrs73dtb580` |
| transport, BCR-ABL1 | `d9t16tftfhrs73dtb58g` |
| negative control | `d9t16tfpemts73cu9fig` |

El orden de las filas es el que ya tiene la tabla y coincide con éste. **Si al maquetar la
tabla de cinco columnas se parte o se estrecha demasiado**, la alternativa aceptable es
dejar la tabla como está y poner los siete identificadores en una lista debajo, encabezada
por la frase que ya existe. Lo que NO es aceptable es dejar la afirmación sin los datos.

---

## CAMBIO 2 — §8: el primer punto, reescrito entero

**Por qué.** Hoy dice que el brazo apilado quedó fuera *porque la conservación estaba rota*.
Eso era cierto de la máquina y no era toda la verdad del experimento: la columna llegaba
muerta en **todas** las corridas ya selladas, por una segunda causa (la ruta del caché), y
cuando por fin se midió, la conservación **restaba**.

**Reemplazar el primer punto del §8 por este texto, tal cual:**

> **The leakage-free stacked arm — and why the reason we gave was wrong.** We reported this
> arm as blocked by the environment: the conservation module requires Biopython ≥ 1.80 and
> the laboratory machine had 1.79, so the conservation feature would silently become a column
> of zeros. That was true of the machine. It was not the whole truth about the experiment.
>
> When we moved the run to CI and measured it, we found that the conservation feature had
> been a column of zeros **in every N=90 run already sealed** — for a second, independent
> reason: the cache was written to one directory and read from another. A guard written for
> exactly this failure existed, was tested, and was never called from the engine. It is now
> wired in and fails closed, and the column census is printed on every run whether or not
> anything is wrong.
>
> With the column finally alive in 90 of 90 targets, the feature-based arm scores
> **8.33 × 10⁻⁹ with conservation and 4.57 × 10⁻⁹ without it** — 1.8× better without the real
> feature in the model. The quantum manager arm remains non-significant (p = 0.104), classical
> diffusion remains the strongest single propagator, and the manager still selects it in 50 of
> 90 targets. Every sealed number in this report is unchanged.
>
> So the stacked arm was not held back by a missing signal. It was held back by a broken
> environment, and by a claim about that environment that we could not check until we built
> the check. Three seals record the sequence — the wrong reading, the retraction, and the
> measurement — and all three are public.

Los otros dos puntos del §8 (*Other groupings and other sizes*, *A truly prospective null*)
**no se tocan**.

---

## Comprobado antes de entregar esto

Las siete cifras del texto del §8 se ejercieron contra `RQ-EXP-N90-LOPO@63e389a4.json`, el
artefacto de la corrida con la conservación viva: 7 de 7 calzan. Los siete `job_id` salen de
`voyage2_manifest.json`, que es el archivo sellado antes de que existieran los resultados.

Nada más del reporte cambia. El resto del §9 —titular, tabla de resultados, el hallazgo de
las dos vidas, los cuatro límites— queda como Nicholas lo aprobó.
