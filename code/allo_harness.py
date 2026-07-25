"""
RosettaQ harness — track Cleveland Clinic (allosteric site identification).
Protocolo Juez v1 aplicado a: ¿la propagacion de senal por CAMINATA CUANTICA
identifica sitios alostericos mejor que la DIFUSION CLASICA?

- Proteina -> red de residuos (nodos=residuos CA, aristas=contacto < cutoff A).
- Fuente de senal = sitio activo (residuos catalicos/documentados).
- Lado CUANTICO: continuous-time quantum walk (CTQW), U(t)=exp(-iAt).
  Propagacion a residuo j = |<j|U(t)|source>|^2, integrada en t. Correlaciones
  no-locales e interferencia (justo lo que el brief pide).
- Lado CLASICO: continuous-time random walk / difusion, p(t)=exp(-L t).
- ARBITRO (ground truth): sitios alostericos EXPERIMENTALMENTE documentados.
  Ninguno de los dos lados los define.
- Metrica: ranking-percentil de los residuos alostericos verdaderos en cada
  mapa de propagacion. Gana quien los rankea mas alto (mas cerca del top).
"""
import os, json, time, platform
import numpy as np
from scipy.linalg import expm
import prody

prody.confProDy(verbosity='none')

PDB = os.environ.get("RQ_PDB", "2HHB")           # hemoglobina — alosterico canonico
CUTOFF = float(os.environ.get("RQ_CUTOFF", 8.5)) # A, red de contacto de residuos
CHAIN = os.environ.get("RQ_CHAIN", "")           # opcional: restringir cadena

# --- ground truth documentado (residuos), por proteina ---
# 2HHB hemoglobina: sitio activo = His proximal coordinante del hemo (F8);
# sitio alosterico = bolsillo de 2,3-BPG en la cavidad central de cadenas beta.
GROUND_TRUTH = {
  "2HHB": {
    "active_site": [("A",87),("C",87),("B",92),("D",92)],   # His F8 proximal (alpha87, beta92)
    "allosteric": [("B",2),("B",82),("B",143),("D",2),("D",82),("D",143)],  # bolsillo 2,3-BPG (His2,Lys82,His143 en cadenas beta)
    "ref": "Arnone 1972; textbook 2,3-BPG allosteric pocket of deoxyhemoglobin"
  },
}

def load_network(pdb):
    atoms = prody.parsePDB(pdb, subset='ca')
    if CHAIN: atoms = atoms.select(f'chain {CHAIN}')
    coords = atoms.getCoords()
    chains = atoms.getChids(); resnums = atoms.getResnums()
    n = len(coords)
    # matriz de adyacencia por contacto CA-CA
    d = np.linalg.norm(coords[:,None,:]-coords[None,:,:], axis=-1)
    A = ((d < CUTOFF) & (d > 0)).astype(float)
    ids = [(chains[i], int(resnums[i])) for i in range(n)]
    return A, ids, coords

def idx_of(ids, targets):
    s=set(targets); return [i for i,k in enumerate(ids) if k in s]

t0=time.time()
A, ids, coords = load_network(PDB)
n=len(ids)
gt = GROUND_TRUTH[PDB]
src = idx_of(ids, gt["active_site"])
allo = idx_of(ids, gt["allosteric"])
assert src and allo, f"faltan residuos ground-truth (src={len(src)}, allo={len(allo)})"

# distancia (en A) de cada residuo al sitio activo mas cercano -> excluir vecinos triviales
dmin = np.min(np.linalg.norm(coords[:,None,:]-coords[src][None,:,:],axis=-1),axis=1)

# estado fuente uniforme sobre el sitio activo
psi0=np.zeros(n); psi0[src]=1.0/np.sqrt(len(src))
p0=np.zeros(n); p0[src]=1.0/len(src)

# Laplaciano para difusion clasica
deg=A.sum(1); L=np.diag(deg)-A

TS=np.linspace(0.5, 8.0, 16)   # ventana de tiempos, integrada
q_prop=np.zeros(n); c_prop=np.zeros(n)
tq=time.time()
for t in TS:
    Uq=expm(-1j*A*t); q_prop += np.abs(Uq@psi0)**2
q_rt=round(time.time()-tq,3)
tc=time.time()
for t in TS:
    Pc=expm(-L*t*0.15); c_prop += Pc@p0     # difusion (escala de tiempo ~ acorde)
c_rt=round(time.time()-tc,3)

# excluir el propio sitio activo y su vecindad inmediata (<6A) del scoring alosterico:
# un sitio alosterico es DISTAL por definicion
mask = dmin > 6.0
def percentile_rank(prop):
    order=np.argsort(-prop)  # mayor propagacion primero
    rank=np.empty(n,dtype=float); rank[order]=np.arange(n)
    # percentil de los residuos alostericos entre los residuos distales (mask)
    distal_idx=np.where(mask)[0]
    distal_order=distal_idx[np.argsort(-prop[distal_idx])]
    pos={idx:k for k,idx in enumerate(distal_order)}
    pcts=[100.0*(1 - pos[a]/max(1,len(distal_order)-1)) for a in allo if a in pos]
    return float(np.mean(pcts)) if pcts else 0.0

q_score=percentile_rank(q_prop)   # 100 = alosterico en el top de propagacion
c_score=percentile_rank(c_prop)

outcome = ("quantum win — CTQW ranks allosteric sites higher" if q_score>c_score+1e-6
           else ("not yet — classical diffusion ranks them as well or better" if c_score>=q_score else "tie"))

result={
  "track":"Cleveland Clinic — allosteric site identification",
  "instance":f"{PDB}_ca_cutoff{CUTOFF}",
  "params":{"pdb":PDB,"cutoff_A":CUTOFF,"n_residues":n,"time_window":[float(TS[0]),float(TS[-1])],"n_times":len(TS)},
  "ground_truth":{"active_site":gt["active_site"],"allosteric":gt["allosteric"],"ref":gt["ref"],
                  "n_active_matched":len(src),"n_allosteric_matched":len(allo)},
  "quantum_side":{"method":"continuous-time quantum walk, U(t)=exp(-iAt), integrated","allosteric_percentile":round(q_score,2),"runtime_s":q_rt},
  "classical_side":{"method":"continuous-time diffusion, p(t)=exp(-Lt), integrated","allosteric_percentile":round(c_score,2),"runtime_s":c_rt},
  "verdict":{"protocol":"juez-v1: misma red de residuos + mismo par fuente/tiempos; sitios alostericos documentados como arbitro (ninguno los define)",
             "metric":"percentil medio de residuos alostericos verdaderos en el mapa de propagacion (entre residuos distales, >6A del sitio activo); 100=top",
             "quantum_allosteric_percentile":round(q_score,2),"classical_allosteric_percentile":round(c_score,2),"outcome":outcome},
  "lib_versions":{"prody":prody.__version__,"numpy":np.__version__,"scipy":__import__("scipy").__version__,"python":platform.python_version()},
}
out=os.environ.get("RQ_OUT","/home/claude/rosettaq/runs/result_allo.json")
json.dump(result,open(out,"w"),indent=2)
print(json.dumps(result["verdict"],indent=1))
print(f"n={n} residues | active matched={len(src)} allo matched={len(allo)} | quantum pct={q_score:.1f} classical pct={c_score:.1f}")
