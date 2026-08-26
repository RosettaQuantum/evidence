#!/bin/bash
# Las variables van DENTRO del script a proposito: relanzar esto a mano sin ellas caeria
# en silencio al brazo clasico y produciria un resultado que se ve bien y responde otra
# pregunta. Ya paso una vez con RQ_DATASET.
cd "$(dirname "$0")"
export RQ_DATASET=ulb
export RQ_BRAZO=cuantico
export RQ_QFEAT=8
export RQ_QSOP=20000
export RQ_QREPS=2
export RQ_QC=1.0
export RQ_OUT=resultado_hsbc_cuantico.json
export RQ_SCORES_PREFIX=scores_q_
export RQ_CONTROLES=1
exec "/Users/nicholasiakl/Documents/Claude/Projects/Rosetta Quantum/.venv-lab/bin/python3" \
     ../evidence/harness/hsbc_harness.py
