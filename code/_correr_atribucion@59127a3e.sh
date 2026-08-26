#!/bin/bash
# Las tres salidas del §5.2 del enunciado + la importancia por permutacion.
# Corrida APARTE de la sellada: escribe en su propio artefacto y NO toca
# resultado_hsbc_cuantico.json. El runner cuantico ya no deja que eso pase.
set -euo pipefail
cd "$(dirname "$0")"
for v in RQ_DATASET RQ_BRAZO RQ_QFEAT RQ_QSOP RQ_QREPS RQ_QC RQ_CONTROLES RQ_ATRIBUCION; do
  if [ -n "${!v:-}" ]; then echo "ABORTA: $v viene del entorno" >&2; exit 1; fi
done
export RQ_DATASET=ulb RQ_BRAZO=cuantico RQ_QFEAT=8 RQ_QSOP=20000 RQ_QREPS=2 RQ_QC=1.0
export RQ_CONTROLES=0 RQ_ATRIBUCION=1
export RQ_PERM_REPS="${RQ_PERM_REPS:-10}"
export RQ_OUT="${RQ_OUT:-resultado_hsbc_atribucion.json}"
export RQ_SCORES_PREFIX="${RQ_SCORES_PREFIX:-scores_atr_}"
exec "/Users/nicholasiakl/Documents/Claude/Projects/Rosetta Quantum/.venv-lab/bin/python3" \
     ../evidence/harness/hsbc_harness.py
