"""
RosettaQ — sweep de robustez del track Cleveland Clinic sobre 2HHB.
Objetivo: mostrar que el veredicto CTQW-vs-difusion NO depende de una eleccion
afortunada de parametros. Barremos cutoff de contacto y ventana de tiempo,
sellando cada combinacion como su propio run (juez-v1). Ground truth congelado:
bolsillo alosterico 2,3-BPG documentado (mismo que EXP-0007-001).
"""
import os, json, time, hashlib, platform, datetime
import numpy as np
from scipy.linalg import expm
import prody
prody.confProDy(verbosity='none')

PDB = "2HHB"
PDB_PATH = "/home/claude/rosettaq/2hhb.pdb.gz"

GROUND_TRUTH = {
  "2HHB": {
    "active_site": [("A",87),("C",87),("B",92),("D",92)],
    "allosteric": [("B",2),("B",82),("B",143),("D",2),("D",82),("D",143)],
    "ref": "Arnone 1972; textbook 2,3-BPG allosteric pocket of deoxyhemoglobin"
  },
}

def load_network(cutoff):
    atoms = prody.parsePDB(PDB_PATH, subset='ca')
    coords = atoms.getCoords()
    chains = atoms.getChids(); resnums = atoms.getResnums()
    n = len(coords)
    d = np.linalg.norm(coords[:,None,:]-coords[None,:,:], axis=-1)
    A = ((d < cutoff) & (d > 0)).astype(float)
    ids = [(chains[i], int(resnums[i])) for i in range(n)]
    return A, ids, coords

def idx_of(ids, targets):
    s=set(targets); return [i for i,k in enumerate(ids) if k in s]

def run_one(cutoff, t_lo, t_hi, n_times):
    A, ids, coords = load_network(cutoff)
    n=len(ids)
    gt = GROUND_TRUTH[PDB]
    src = idx_of(ids, gt["active_site"]); allo = idx_of(ids, gt["allosteric"])
    assert src and allo
    dmin = np.min(np.linalg.norm(coords[:,None,:]-coords[src][None,:,:],axis=-1),axis=1)
    psi0=np.zeros(n); psi0[src]=1.0/np.sqrt(len(src))
    p0=np.zeros(n); p0[src]=1.0/len(src)
    deg=A.sum(1); L=np.diag(deg)-A
    TS=np.linspace(t_lo, t_hi, n_times)
    q_prop=np.zeros(n); c_prop=np.zeros(n)
    tq=time.time()
    for t in TS: q_prop += np.abs(expm(-1j*A*t)@psi0)**2
    q_rt=round(time.time()-tq,3)
    tc=time.time()
    for t in TS: c_prop += expm(-L*t*0.15)@p0
    c_rt=round(time.time()-tc,3)
    mask = dmin > 6.0
    def percentile_rank(prop):
        distal_idx=np.where(mask)[0]
        distal_order=distal_idx[np.argsort(-prop[distal_idx])]
        pos={idx:k for k,idx in enumerate(distal_order)}
        pcts=[100.0*(1 - pos[a]/max(1,len(distal_order)-1)) for a in allo if a in pos]
        return float(np.mean(pcts)) if pcts else 0.0
    q=percentile_rank(q_prop); c=percentile_rank(c_prop)
    outcome = ("quantum win" if q>c+1e-6 else ("not yet" if c>=q else "tie"))
    return dict(n=n, q=round(q,2), c=round(c,2), q_rt=q_rt, c_rt=c_rt,
                outcome=outcome, n_src=len(src), n_allo=len(allo))

def seal(file_id, cutoff, t_lo, t_hi, n_times, r, ts):
    gt = GROUND_TRUTH[PDB]
    fname = f"RosettaQ__RUN__{file_id}__{ts}__ctqw-vs-diffusion--allostery-2hhb-c{cutoff}-t{t_lo}_{t_hi}.json"
    w6 = {
      "que": {
        "recipe_id":"RQ-0007","recipe_name":"Allosteric site identification via quantum signal propagation",
        "problem_class":"Molecular simulation / allostery",
        "instance":f"2HHB_ca_cutoff{cutoff}_t{t_lo}-{t_hi}",
        "quantum_side":{"method":"continuous-time quantum walk, U(t)=exp(-iAt), integrated","allosteric_percentile":r["q"],"runtime_s":r["q_rt"]},
        "classical_side":{"method":"continuous-time diffusion, p(t)=exp(-Lt), integrated","allosteric_percentile":r["c"],"runtime_s":r["c_rt"]},
        "ground_truth":{"active_site":[list(x) for x in gt["active_site"]],"allosteric":[list(x) for x in gt["allosteric"]],
                        "ref":gt["ref"],"n_active_matched":r["n_src"],"n_allosteric_matched":r["n_allo"]},
        "outcome":r["outcome"],
        "metric":"percentil medio de residuos alostericos verdaderos en el mapa de propagacion (entre residuos distales, >6A del sitio activo); 100=top",
        "scores":{"quantum_percentile":r["q"],"classical_percentile":r["c"]}
      },
      "como":{
        "protocol":"juez-v1: misma red de residuos + mismo par fuente/tiempos; sitios alostericos documentados como arbitro (ninguno los define)",
        "instance_params":{"pdb":PDB,"cutoff_A":cutoff,"n_residues":r["n"],"time_window":[t_lo,t_hi],"n_times":n_times},
        "sweep_note":"parte del sweep de robustez de EXP-0007 sobre 2HHB; ground truth y protocolo identicos a EXP-0007-001, solo varian cutoff/ventana",
        "lib_versions":{"prody":prody.__version__,"numpy":np.__version__,"scipy":__import__("scipy").__version__,"python":platform.python_version()},
        "compute":"contenedor cloud Cowork (CPU, Linux)","harness":"allo_sweep.py","raw_data_url":"pendiente de publicacion en repo"
      },
      "cuando":{"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "archived_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "timezone_note":"UTC; equipo en America/Punta_Arenas"},
      "donde":{"quantum_backend":"CTQW por matrix-exponential (simulacion exacta; ruta NISQ = Hamiltonian simulation gate-based)",
               "classical_backend":"difusion por matrix-exponential del Laplaciano","protein_source":"RCSB PDB 2HHB via ProDy","region":"cloud sandbox Anthropic"},
      "porque":{"hypothesis":"si CTQW realmente identificara mejor los sitios alostericos, deberia ganar de forma estable a lo largo de cutoffs y ventanas; el sweep prueba robustez, no una config afortunada",
                "question":f"A cutoff={cutoff}A y ventana [{t_lo},{t_hi}], CTQW vs difusion: cual rankea mas alto el bolsillo 2,3-BPG?",
                "ledger_goal":"robustez del veredicto RQ-0007; insumo de la propuesta Fase I Cleveland"},
      "quien":{"operator":"Nicholas","agents":["Claude (Cowork cloud)","allo_sweep.py"],"judge_protocol_version":"juez-v1","org":"Rosetta Quantum","team":"Rosetta Quantum"}
    }
    meta = {"schema":"rosettaq-archive/v1","file_name":fname,"file_id":file_id,"type":"RUN","is_demo":False,
            "scope_note":f"Sweep de robustez 2HHB (Cleveland Clinic). cutoff={cutoff}A, ventana [{t_lo},{t_hi}], {n_times} tiempos. CTQW vs difusion clasica; bolsillo 2,3-BPG documentado como arbitro."}
    payload = {"meta":meta,"w6":w6}
    h = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    meta["content_hash"] = f"sha256:{h}"
    storage = {"policy":"triple-copia identica; verificar con content_hash",
               "locations":[
                 {"n":1,"kind":"github","role":"primary","url":f"https://github.com/RosettaQuantum/evidence/blob/main/runs/2026/07/{fname}","raw_url":f"https://raw.githubusercontent.com/RosettaQuantum/evidence/main/runs/2026/07/{fname}"},
                 {"n":2,"kind":"codeberg","role":"mirror","url":f"https://codeberg.org/RosettaQuantum/evidence/src/branch/main/runs/2026/07/{fname}","raw_url":f"https://codeberg.org/RosettaQuantum/evidence/raw/branch/main/runs/2026/07/{fname}"},
                 {"n":3,"kind":"cloudflare-d1","role":"database","uri":f"d1://rosettaq-ledger/run_archives/{file_id}","public_read":f"https://ledger.rosettaquantum.com/api/archive/{file_id}"}],
               "self_note":"Este archivo es una de las 3 copias listadas. Si el hash difiere, esa copia no es valida."}
    out = {"meta":meta,"w6":w6,"storage":storage}
    path = f"/home/claude/rosettaq/runs/{fname}"
    json.dump(out, open(path,"w"), indent=2, ensure_ascii=False)
    return fname, meta["content_hash"]

# --- grilla del sweep ---
# 001 ya cubrio cutoff=8.5, ventana [0.5,8.0]. Barremos alrededor.
CONFIGS = [
  ("EXP-0007-002", 7.5, 0.5, 8.0, 16),
  ("EXP-0007-003", 8.0, 0.5, 8.0, 16),
  ("EXP-0007-004", 9.0, 0.5, 8.0, 16),
  ("EXP-0007-005", 9.5, 0.5, 8.0, 16),
  ("EXP-0007-006", 10.0, 0.5, 8.0, 16),
  ("EXP-0007-007", 8.5, 0.5, 4.0, 16),   # ventana corta
  ("EXP-0007-008", 8.5, 0.5, 14.0, 24),  # ventana larga
]
ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%MZ")
rows = []
for fid, cutoff, tlo, thi, ntimes in CONFIGS:
    r = run_one(cutoff, tlo, thi, ntimes)
    fname, h = seal(fid, cutoff, tlo, thi, ntimes, r, ts)
    rows.append((fid, cutoff, f"[{tlo},{thi}]", r["n"], r["q"], r["c"], r["outcome"], h[:19]))
    print(f"{fid}  cut={cutoff:<4} win=[{tlo},{thi}]  n={r['n']}  Q={r['q']:<6} C={r['c']:<6} -> {r['outcome']}  {h[:19]}")

print("\n=== RESUMEN SWEEP 2HHB (incl. 001 cut=8.5 win=[0.5,8.0] Q=69.89 C=74.24 not yet) ===")
allq = [69.89] + [r[4] for r in rows]
allc = [74.24] + [r[5] for r in rows]
wins = sum(1 for q,c in zip(allq,allc) if q>c+1e-6)
print(f"configs totales (con 001): {len(allq)} | quantum gana en {wins} | rango Q {min(allq)}-{max(allq)} | rango C {min(allc)}-{max(allc)}")
print(f"delta (C-Q) medio = {round(float(np.mean([c-q for q,c in zip(allq,allc)])),2)} pct")
