#!/bin/bash
# Reproduccion completa del track HSBC — el "comando unico" (REFORMS 2e).
# Requisitos: python3.12+ con numpy pandas scikit-learn xgboost imbalanced-learn scipy.
# Cada paso falla cerrado; el ultimo verifica TODO con denominador.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/4 dato: descargar y verificar contra el manifest sellado =="
curl -sL --retry 3 "https://openml.org/data/v1/download/1673544/creditcard.arff" -o creditcard.arff
echo "fdaf12730dc1fc426f318b71349f24f5c5fd00aa1152940be7e7509ae3d89d2a  creditcard.arff" | shasum -a 256 -c -

echo "== 2/4 baseline (xgboost+lightgbm) =="
RQ_ARFF=creditcard.arff RQ_OUT=repro_baseline.json python3 harness/hsbc_harness.py

echo "== 3/4 las cuatro series del ataque =="
for S in S1 S2 S3 S4; do
  RQ_ATAQUE=$S RQ_ARFF=creditcard.arff RQ_OUT=repro_$S.json python3 harness/hsbc_harness.py
done

echo "== 4/4 verificar los artefactos publicados con la bateria (7 tramos, denominador) =="
python3 tools/replicar.py verificar --track hsbc
echo "listo: compара repro_*.json contra resultados_hsbc/*@*.json — con las mismas semillas,"
echo "los verdictos deben calzar al decimal."
