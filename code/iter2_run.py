"""Iteracion 2 — Stage 2: A/B sobre el set cacheado.
Brazo A = gestor cuantico (elige propagador por proteina, a ciegas, por k-NN de
descriptores, leave-one-protein-out). Brazo B = ML clasico (regresion logistica,
leave-one-protein-out). Nulo espacial + p combinada (Fisher). Reporte honesto."""
import os, glob, pickle, json, numpy as np
from scipy.stats import chi2 as chi2dist
import sys; sys.path.insert(0, ".")
from allo_challenge import props, gnm_score, betweenness_closeness, percentile
from sigo_features import annotated_hamiltonian
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

CACHE = "/home/claude/rosettaq/iter2_cache"
WIN = (0.5, 8.0); NPERM = 2000; RS = np.random.RandomState(20260717)
WEIGHTS = {"uni_binding_site":1.0,"uni_active_site":1.0,"clinvar_density":0.5,"coordination":0.3}
METHODS = ["ctqw_bare", "ctqw_glifo", "diffusion", "gnm"]
FEATCOLS = ["degree","closeness_to_active","coordination","uni_binding_site","uni_active_site",
            "uni_domain","uni_ptm","uni_motif","clinvar_density","diffusion","gnm","betweenness"]

def ctqw(M, src):
    n=M.shape[0]; TS=np.linspace(*WIN,16); w,V=np.linalg.eigh(M)
    psi=np.zeros(n); psi[src]=1/np.sqrt(len(src)); c=V.T@psi; q=np.zeros(n)
    for t in TS: q+=np.abs(V@(np.exp(-1j*w*t)*c))**2
    return q

def contiguous_null(coords, distal, k):
    C=coords[distal]; out=[]
    for _ in range(NPERM):
        s=RS.randint(len(distal)); dd=np.linalg.norm(C-C[s],axis=1); out.append(distal[np.argsort(dd)[:k]])
    return out

def pct(vec, d):
    allo_d=[a for a in d["allo"] if d["mask"][a]]
    return percentile(vec, allo_d, d["mask"])

def null_p(vec, d):
    obs=pct(vec,d)
    null=np.array([percentile(vec,list(p),d["mask"]) for p in d["pockets"]])
    p=float((null>=obs).mean()); p=max(p, 1.0/(NPERM+1))
    return obs, p

def fisher(ps):
    ps=np.array([max(p,1e-6) for p in ps]); stat=-2*np.sum(np.log(ps))
    return stat, float(chi2dist.sf(stat, 2*len(ps)))

# ---- cargar y precomputar ----
D=[pickle.load(open(f,"rb")) for f in sorted(glob.glob("%s/*.pkl"%CACHE))]
print("proteinas:", len(D))
for d in D:
    A,coords,src,feats=d["A"],d["coords"],d["src"],d["features"]
    P,_,_=props(A,src,*WIN)
    H,_=annotated_hamiltonian(A,coords,feats,WEIGHTS,edge_mode="gaussian")
    btw=betweenness_closeness(A,src)[0]
    d["scores"]={"ctqw_bare":P["ctqw"][0],"ctqw_glifo":ctqw(H,src),
                 "diffusion":P["diffusion"][0],"gnm":gnm_score(A,src)}
    d["btw"]=btw
    cols={}
    for c in FEATCOLS:
        if c=="diffusion": cols[c]=d["scores"]["diffusion"]
        elif c=="gnm": cols[c]=d["scores"]["gnm"]
        elif c=="betweenness": cols[c]=btw
        else:
            v=feats.get(c); cols[c]=np.asarray(v,float) if v is not None else np.zeros(d["n"])
    d["X"]=np.column_stack([cols[c] for c in FEATCOLS])
    d["y"]=np.zeros(d["n"]); d["y"][d["allo"]]=1.0
    d["pockets"]=contiguous_null(coords, np.where(d["mask"])[0], max(1,d["k"]))
    # descriptor de proteina (rasgos, NUNCA la respuesta)
    d["desc"]=np.array([np.log(d["n"]), d["n_distal"]/d["n"], float(np.mean(d["scores"]["gnm"])),
                        float(np.mean(cols["coordination"])), float(np.mean(cols["uni_binding_site"]))])

permethod=[{m:pct(d["scores"][m],d) for m in METHODS} for d in D]
DESC=np.array([d["desc"] for d in D]); DSC=StandardScaler().fit_transform(DESC)

# ---- Brazo A: gestor k-NN leave-one-out ----
# ---- Brazo B: ML leave-one-out ----
rows=[]; pA=[]; pB=[]; choiceA=[]
for i,d in enumerate(D):
    others=[j for j in range(len(D)) if j!=i]
    dist=np.linalg.norm(DSC[others]-DSC[i],axis=1); knn=[others[j] for j in np.argsort(dist)[:3]]
    best_m=max(METHODS, key=lambda m: np.mean([permethod[j][m] for j in knn]))
    choiceA.append(best_m)
    obsA,ppA=null_p(d["scores"][best_m], d); pA.append(ppA)
    # brazo B
    Xtr=np.vstack([D[j]["X"][D[j]["mask"]] for j in others]); ytr=np.concatenate([D[j]["y"][D[j]["mask"]] for j in others])
    sc=StandardScaler().fit(Xtr); clf=LogisticRegression(max_iter=2000,class_weight="balanced",C=1.0).fit(sc.transform(Xtr),ytr)
    probB=np.zeros(d["n"]); probB[d["mask"]]=clf.predict_proba(sc.transform(d["X"][d["mask"]]))[:,1]
    obsB,ppB=null_p(probB, d); pB.append(ppB)
    rows.append((d["name"], d["n"], d["k"], best_m, round(obsA,1), round(ppA,3), round(obsB,1), round(ppB,3)))

print("\n%-15s %5s %3s %-11s | A_pct A_p  | B_pct B_p"%("proteina","n","k","gestor->"))
for r in rows: print("%-15s %5d %3d %-11s | %5.1f %.3f | %5.1f %.3f"%r)
sA,fA=fisher(pA); sB,fB=fisher(pB)
# mejor metodo fijo unico (secundario)
fixed={m:np.mean([permethod[i][m] for i in range(len(D))]) for m in METHODS}
bestfixed=max(fixed,key=fixed.get)
nA=sum(1 for p in pA if p<0.05); nB=sum(1 for p in pB if p<0.05)
print("\n== AGREGADO ==")
print("Fisher p combinada  |  A (gestor cuantico): %.4f   |  B (ML clasico): %.4f"%(fA,fB))
print("proteinas con p<0.05|  A: %d/%d   B: %d/%d"%(nA,len(D),nB,len(D)))
print("percentil medio     |  A: %.1f   B: %.1f   | mejor metodo fijo (%s): %.1f"%(np.mean([r[4] for r in rows]),np.mean([r[6] for r in rows]),bestfixed,fixed[bestfixed]))
print("elecciones del gestor:", {m:choiceA.count(m) for m in METHODS})
out={"n_proteins":len(D),"proteins":[d["name"] for d in D],"dropped":["HEMOGLOBIN_B","GLS"],
     "per_protein":[dict(zip(["name","n","k","manager_pick","A_pct","A_p","B_pct","B_p"],r)) for r in rows],
     "fisher_p":{"armA_quantum":round(fA,4),"armB_ml":round(fB,4)},
     "n_sig_p05":{"armA":nA,"armB":nB},"best_fixed_method":bestfixed,
     "mean_pct":{"armA":round(float(np.mean([r[4] for r in rows])),1),"armB":round(float(np.mean([r[6] for r in rows])),1)},
     "manager_choices":{m:choiceA.count(m) for m in METHODS},"weights":WEIGHTS,"nperm":NPERM}
json.dump(out, open("/home/claude/rosettaq/iter2_result.json","w"), indent=1)
print("\nguardado iter2_result.json")
