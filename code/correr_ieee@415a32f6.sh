#!/bin/bash
# Las variables se ponen DENTRO del script: si se pasan por `env` o `nohup`, macOS
# borra las DYLD_* y ademas es facil olvidarlas, como acaba de pasar. Aqui viajan con
# el comando y quedan escritas al lado de lo que corren.
cd "/private/tmp/claude-501/-Users-nicholasiakl-Documents-Claude/971233af-117a-4b2c-b9d7-52c52677dd57/scratchpad/hsbc"
export RQ_DATASET=ieee
export RQ_CSV="/Users/nicholasiakl/Documents/Claude/Projects/Rosetta Quantum/lab-hsbc-2026-08-20/ieee-cis/train_transaction.csv"
export RQ_MODELOS=xgboost,lightgbm
export RQ_OUT=ieee_baseline.json
export RQ_SCORES_PREFIX=ieee_
exec "/Users/nicholasiakl/Documents/Claude/Projects/Rosetta Quantum/.venv-lab/bin/python3" harness_refactor.py
