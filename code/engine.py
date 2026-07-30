"""
RQ-ENGINE — motor de iteración de Rosetta Quantum (alosteria).
=============================================================
Convierte el ciclo manual (editar → construir → correr → inspeccionar → registrar)
en UNA llamada: run_experiment(config). Reutiliza la ciencia probada
(allo_challenge, sigo_features, conservation) y agrega:
  - catálogo auto-describible de proteínas (catalog.json)
  - build resumible con caché por proteína
  - features enchufables (grafo, UniProt, ClinVar, conservación, dinámica GNM/ANM)
  - arms parametrizados: A (gestor cuántico), B (ML features), C (ML apilado propagadores)
  - nulo espacial contiguo + Fisher, con ablaciones
  - result.json + reporte.md + fila en ledger.csv (iteraciones comparables)

CLI:
  python engine.py build [name ...]         # construye/cachea (resumible)
  python engine.py run  config.json          # corre un experimento
  python engine.py verify PDB CHAIN ACT ALLO # verifica un candidato (distal check)
  python engine.py ledger                     # muestra el historial
"""
import os, sys, re, json, glob, pickle, hashlib, datetime
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import prody; prody.confProDy(verbosity='none')
from allo_challenge import (ca_network, contacts, idx_of, DISTAL_A, props,
                            gnm_score, betweenness_closeness, percentile)
import sigo_features as SF
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from scipy.stats import chi2 as chi2dist

CATALOG = os.path.join(HERE, "catalog.json")
CACHE   = os.path.join(HERE, "cache")
RESULTS = os.path.join(HERE, "results")
REPORTS = os.path.join(HERE, "reports")
LEDGER  = os.path.join(HERE, "ledger.csv")
for d in (CACHE, RESULTS, REPORTS): os.makedirs(d, exist_ok=True)

# ---- features disponibles (nombre -> de dónde sale en el feature-table) -----
GRAPH_FEATS = ["degree","closeness_to_active","coordination"]
UNIPROT_FEATS = ["uni_active_site","uni_binding_site","uni_domain","uni_ptm","uni_motif",
                 "uni_dna_binding","uni_np_binding","uni_site"]
DYN_FEATS = ["gnm_msf","anm_msf","slow_mode"]
OTHER_FEATS = ["clinvar_density","conservation"]
PROP_FEATS = ["ctqw_bare","ctqw_glifo_fixed","ctqw_glifo_learned","diffusion","gnm","betweenness"]
ALL_RESIDUE_FEATS = GRAPH_FEATS + UNIPROT_FEATS + DYN_FEATS + OTHER_FEATS

def load_catalog():
    return json.load(open(CATALOG))

def save_catalog(cat):
    json.dump(cat, open(CATALOG,"w"), indent=1)

# ---------------------------------------------------------------- BUILD -------
def _get_src(apo, ch, active_src, uniprot=None):
    sel = "protein and name CA and chain %s" % ch
    ca = apo.select(sel); rn = [int(x) for x in ca.getResnums()]
    _, ids, _, seq, _ = ca_network(apo, sel, 8.5); idset = set(ids)
    kind, pat = active_src.get("kind"), active_src.get("pat")
    src, method = [], "sin regla"
    if kind == 'lig':
        c = contacts(apo, "(%s) and chain %s" % (pat, ch), sel)
        src = [(ch, r) for (cc, r) in c if (ch, r) in idset]; method = "lig:%s" % pat
    elif kind == 'motif':
        m = re.search(pat, seq)
        if m:
            src = [(ch, rn[i]) for i in range(m.start(), m.end()) if i < len(rn)]
            method = "motif:%s@%d" % (pat, m.start())
    elif kind == 'uniprot_pos':
        # sitio activo dado como posiciones UniProt (AlloBench) -> mapear por secuencia
        positions = set(int(p) for p in active_src.get("positions", []))
        try:
            uni_seq = SF.uniprot_annotations(uniprot)[0]
        except Exception:
            uni_seq = ""
        items = [(c, r, seq[i]) for i, (c, r) in enumerate(ids)]
        pos_map = SF.align_by_sequence(items, uni_seq) if uni_seq else {}
        src = [(c, r) for (c, r), up in pos_map.items() if up in positions]
        method = "uniprot_pos:%d posiciones" % len(positions)
    if len(src) < 3 and active_src.get("fallback_mg"):
        c = contacts(apo, "resname MG and chain %s" % ch, sel)
        src = [(ch, r) for (cc, r) in c if (ch, r) in idset]; method = "fallback_mg"
    return sorted(set(src)), method

def build_protein(name, entry, force=False):
    cp = os.path.join(CACHE, "%s.pkl" % name)
    if os.path.exists(cp) and not force:
        return pickle.load(open(cp, "rb")), "cache"
    apo = SF.load_pdb(entry["apo"]); ch = entry["chain"]
    src_res, method = _get_src(apo, ch, entry["active_src"], entry.get("uniprot"))
    if len(src_res) < 3:
        return None, "SIN FUENTE (%s)" % method
    tgt = {"apo": entry["apo"], "chain": ch, "uniprot": entry["uniprot"], "gene": entry["gene"]}
    ft = SF.build_feature_table(tgt, cutoff=8.5)
    A, ids, coords, feats = ft["A"], ft["ids"], ft["coords"], ft["features"]
    src = idx_of(ids, src_res)
    holo = SF.load_pdb(entry["holo"])
    gt_sel = entry.get("gt_sel") or ("resname %s" % entry["gt_ligand"])
    gt = [(ch, r) for (c, r) in contacts(holo, gt_sel, "protein")]
    allo = idx_of(ids, gt)
    if len(allo) < 5 or not src:
        return None, "GT<5 o src vacio"
    Dm = np.linalg.norm(coords[:, None, :] - coords[src][None, :, :], axis=-1)
    mask = Dm.min(axis=1) > DISTAL_A
    obj = {"name": name, "ids": ids, "coords": coords, "A": A, "features": feats,
           "src": src, "allo": allo, "mask": mask, "src_method": method,
           "n": len(ids), "n_distal": int(mask.sum()), "k": int(sum(mask[a] for a in allo)),
           "area": entry.get("area", "onco")}
    pickle.dump(obj, open(cp, "wb"))
    return obj, "OK src=%d allo=%d distal=%d k=%d" % (len(src), len(allo), obj["n_distal"], obj["k"])

def build_all(names=None, force=False):
    cat = load_catalog(); names = names or list(cat["proteins"].keys())
    built, failed = [], []
    for name in names:
        e = cat["proteins"].get(name)
        if not e: print("%-20s NO EN CATALOGO" % name); continue
        # asegurar conservación cacheada
        _ensure_conservation(e["uniprot"])
        try:
            obj, msg = build_protein(name, e, force)
            print("%-20s %s" % (name, msg)); (built if obj else failed).append(name)
        except Exception as ex:
            print("%-20s ERROR %s: %s" % (name, type(ex).__name__, str(ex)[:60])); failed.append(name)
    return built, failed

def _ensure_conservation(acc):
    fp = os.path.join(ROOT, "conservation_cache", "%s.json" % acc)
    if os.path.exists(fp): return
    try:
        import conservation as C
        os.makedirs(os.path.join(ROOT, "conservation_cache"), exist_ok=True)
        cons, meta = C.conservation(acc)
        payload = {"acc": acc, "ref": C.ref_sequence(acc),
                   "cons": None if cons is None else [None if np.isnan(x) else round(float(x),4) for x in cons],
                   "meta": meta}
        json.dump(payload, open(fp, "w")); print("  (conservación %s: %s)" % (acc, meta))
    except Exception as ex:
        print("  (conservación %s FALLÓ: %s)" % (acc, ex))

# ---------------------------------------------------------------- METRICS -----
def contiguous_null(coords, distal, k, nperm, seed):
    rs = np.random.RandomState(seed); C = coords[distal]; out = []
    for _ in range(nperm):
        s = rs.randint(len(distal)); dd = np.linalg.norm(C - C[s], axis=1)
        out.append(distal[np.argsort(dd)[:k]])
    return out

def pct(vec, d):
    allo_d = [a for a in d["allo"] if d["mask"][a]]
    return percentile(vec, allo_d, d["mask"])

def null_p(vec, d):
    obs = pct(vec, d)
    null = np.array([percentile(vec, list(p), d["mask"]) for p in d["pockets"]])
    p = max(float((null >= obs).mean()), 1.0/(len(d["pockets"])+1))
    return obs, p

def fisher(ps):
    ps = np.array([max(p, 1e-6) for p in ps]); stat = -2*np.sum(np.log(ps))
    return float(chi2dist.sf(stat, 2*len(ps)))

# ---------------------------------------------------------------- ARMS --------
WEIGHTS_FIXED = {"uni_binding_site":1.0,"uni_active_site":1.0,"clinvar_density":0.5,"coordination":0.3}
METHODS_A = ["ctqw_bare","ctqw_glifo_fixed","ctqw_glifo_learned","diffusion","gnm"]

def ctqw(M, src, win):
    n=M.shape[0]; TS=np.linspace(*win,16); w,V=np.linalg.eigh(M)
    psi=np.zeros(n); psi[src]=1/np.sqrt(len(src)); c=V.T@psi; q=np.zeros(n)
    for t in TS: q+=np.abs(V@(np.exp(-1j*w*t)*c))**2
    return q

def _col(d, name):
    v = d["features"].get(name)
    return np.asarray(v, float) if v is not None else np.zeros(d["n"])

def norm01(x):
    x=np.asarray(x,float); rng=x.max()-x.min()
    return (x-x.min())/rng if rng>1e-12 else x*0.0

def learn_weights(train, glifo_feats):
    Xs, ys = [], []
    for d in train:
        G = np.column_stack([norm01(_col(d,c)) for c in glifo_feats]); m = d["mask"]
        Xs.append(G[m]); ys.append(d["y"][m])
    X=np.vstack(Xs); y=np.concatenate(ys)
    clf=LogisticRegression(max_iter=2000,class_weight="balanced",C=1.0).fit(X,y)
    return {glifo_feats[i]: float(clf.coef_[0][i]) for i in range(len(glifo_feats))}

def run_experiment(config):
    cat = load_catalog()
    names = config.get("proteins","all")
    if names == "all": names = list(cat["proteins"].keys())
    win = tuple(config.get("window",[0.5,8.0])); nperm=config.get("nperm",2000); seed=config.get("seed",20260717)
    glifo_feats = config.get("glifo_feats",
        ["uni_binding_site","uni_active_site","uni_domain","uni_ptm","uni_motif",
         "clinvar_density","coordination","degree","closeness_to_active","conservation","gnm_msf","anm_msf"])
    feat_cols = config.get("feat_cols",
        ["degree","closeness_to_active","coordination","uni_binding_site","uni_active_site",
         "uni_domain","uni_ptm","uni_motif","clinvar_density","conservation","gnm_msf","anm_msf",
         "diffusion","gnm","betweenness"])
    arms = config.get("arms", ["A","B","C"])
    # cargar caches (build si falta)
    D=[]
    for name in names:
        cp=os.path.join(CACHE,"%s.pkl"%name)
        if not os.path.exists(cp):
            e=cat["proteins"].get(name)
            if e: _ensure_conservation(e["uniprot"]); build_protein(name,e)
        if os.path.exists(cp): D.append(pickle.load(open(cp,"rb")))
    print("proteínas cargadas:", len(D))
    # precompute determinista + propagadores
    for d in D:
        A,coords,src,feats=d["A"],d["coords"],d["src"],d["features"]
        P,_,_=props(A,src,*win)
        Hf,_=SF.annotated_hamiltonian(A,coords,feats,WEIGHTS_FIXED,edge_mode="gaussian")
        d["btw"]=betweenness_closeness(A,src)[0]
        d["det"]={"ctqw_bare":P["ctqw"][0],"ctqw_glifo_fixed":ctqw(Hf,src,win),
                  "diffusion":P["diffusion"][0],"gnm":gnm_score(A,src)}
        d["y"]=np.zeros(d["n"]); d["y"][d["allo"]]=1.0
        cols={}
        for c in feat_cols:
            if c in ("diffusion","gnm"): cols[c]=d["det"][c]
            elif c=="betweenness": cols[c]=d["btw"]
            else: cols[c]=_col(d,c)
        d["X"]=np.column_stack([cols[c] for c in feat_cols])
        d["pockets"]=contiguous_null(coords, np.where(d["mask"])[0], max(1,d["k"]), nperm, seed)
        d["desc"]=np.array([np.log(d["n"]), d["n_distal"]/d["n"], float(np.mean(d["det"]["gnm"])),
                            float(np.mean(cols.get("coordination",_col(d,"coordination")))),
                            float(np.mean(_col(d,"uni_binding_site")))])
    DSC=StandardScaler().fit_transform(np.array([d["desc"] for d in D]))
    # caminata cuántica de pesos aprendidos LOPO
    learned=[]
    for i,d in enumerate(D):
        w=learn_weights([D[j] for j in range(len(D)) if j!=i], glifo_feats)
        H,_=SF.annotated_hamiltonian(d["A"],d["coords"],d["features"],w,edge_mode="gaussian")
        learned.append(ctqw(H,d["src"],win))
    permethod=[]; pmnull={}
    for i,d in enumerate(D):
        sig={"ctqw_bare":d["det"]["ctqw_bare"],"ctqw_glifo_fixed":d["det"]["ctqw_glifo_fixed"],
             "ctqw_glifo_learned":learned[i],"diffusion":d["det"]["diffusion"],"gnm":d["det"]["gnm"],
             "betweenness":d["btw"]}
        permethod.append({m:pct(sig[m],d) for m in METHODS_A})
        pmnull[i]={m:null_p(sig[m],d) for m in METHODS_A}
        d["Prop"]=np.column_stack([norm01(sig[c]) for c in PROP_FEATS])
    # arms
    pA,pB,pC,choice,rows=[],[],[],[],[]
    for i,d in enumerate(D):
        others=[j for j in range(len(D)) if j!=i]
        row={"name":d["name"],"n":d["n"],"k":d["k"]}
        if "A" in arms:
            dist=np.linalg.norm(DSC[others]-DSC[i],axis=1); knn=[others[j] for j in np.argsort(dist)[:3]]
            bm=max(METHODS_A,key=lambda m:np.mean([permethod[j][m] for j in knn])); choice.append(bm)
            o,p=pmnull[i][bm]; pA.append(p); row["A_pick"]=bm; row["A_pct"]=round(o,1); row["A_p"]=round(p,3)
        ytr=np.concatenate([D[j]["y"][D[j]["mask"]] for j in others])
        if "B" in arms:
            Xtr=np.vstack([D[j]["X"][D[j]["mask"]] for j in others])
            sc=StandardScaler().fit(Xtr); clf=LogisticRegression(max_iter=2000,class_weight="balanced",C=1.0).fit(sc.transform(Xtr),ytr)
            prob=np.zeros(d["n"]); prob[d["mask"]]=clf.predict_proba(sc.transform(d["X"][d["mask"]]))[:,1]
            o,p=null_p(prob,d); pB.append(p); row["B_pct"]=round(o,1); row["B_p"]=round(p,3)
        if "C" in arms:
            Ptr=np.vstack([D[j]["Prop"][D[j]["mask"]] for j in others])
            sc=StandardScaler().fit(Ptr); clf=LogisticRegression(max_iter=2000,class_weight="balanced",C=1.0).fit(sc.transform(Ptr),ytr)
            prob=np.zeros(d["n"]); prob[d["mask"]]=clf.predict_proba(sc.transform(d["Prop"][d["mask"]]))[:,1]
            o,p=null_p(prob,d); pC.append(p); row["C_pct"]=round(o,1); row["C_p"]=round(p,3)
        rows.append(row)
    res={"exp_id":config.get("exp_id","EXP"),"note":config.get("note",""),
         "n_proteins":len(D),"proteins":[d["name"] for d in D],
         "config":{"glifo_feats":glifo_feats,"feat_cols":feat_cols,"arms":arms,"nperm":nperm,"seed":seed,"window":list(win)},
         "fisher_p":{}, "n_sig_p05":{}, "mean_pct":{},
         "per_protein":rows,
         "mean_pct_by_method":{m:round(float(np.mean([permethod[i][m] for i in range(len(D))])),1) for m in METHODS_A},
         "manager_choices":{m:choice.count(m) for m in METHODS_A} if "A" in arms else {}}
    if "A" in arms: res["fisher_p"]["armA_manager"]=round(fisher(pA),4); res["n_sig_p05"]["armA"]=sum(p<0.05 for p in pA); res["mean_pct"]["armA"]=round(float(np.mean([r["A_pct"] for r in rows])),1)
    if "B" in arms: res["fisher_p"]["armB_ml"]=round(fisher(pB),4); res["n_sig_p05"]["armB"]=sum(p<0.05 for p in pB); res["mean_pct"]["armB"]=round(float(np.mean([r["B_pct"] for r in rows])),1)
    if "C" in arms: res["fisher_p"]["armC_stacked"]=round(fisher(pC),4); res["n_sig_p05"]["armC"]=sum(p<0.05 for p in pC); res["mean_pct"]["armC"]=round(float(np.mean([r["C_pct"] for r in rows])),1)
    # ablaciones opcionales de features del brazo B
    for ab in config.get("ablations", []):
        drop=set(ab["drop"]); cols=[c for c in feat_cols if c not in drop]; ps=[]
        for i,d in enumerate(D):
            others=[j for j in range(len(D)) if j!=i]
            def Xof(dd): return np.column_stack([(dd["det"][c] if c in("diffusion","gnm") else dd["btw"] if c=="betweenness" else _col(dd,c)) for c in cols])
            Xtr=np.vstack([Xof(D[j])[D[j]["mask"]] for j in others]); ytr=np.concatenate([D[j]["y"][D[j]["mask"]] for j in others])
            sc=StandardScaler().fit(Xtr); clf=LogisticRegression(max_iter=2000,class_weight="balanced",C=1.0).fit(sc.transform(Xtr),ytr)
            prob=np.zeros(d["n"]); prob[d["mask"]]=clf.predict_proba(sc.transform(Xof(d)[d["mask"]]))[:,1]
            ps.append(null_p(prob,d)[1])
        res.setdefault("ablations",{})[ab["name"]]={"fisher_p":round(fisher(ps),4),"n_sig":int(sum(p<0.05 for p in ps)),"dropped":sorted(drop)}
    _write_result(res); return res

def _write_result(res):
    eid=res["exp_id"]
    json.dump(res, open(os.path.join(RESULTS,"%s.json"%eid),"w"), indent=1)
    _write_report(res); _append_ledger(res)

def _write_report(res):
    L=["# %s — %s"%(res["exp_id"],res.get("note","")), "",
       "**N = %d proteínas** · nperm=%d · seed=%d"%(res["n_proteins"],res["config"]["nperm"],res["config"]["seed"]), "",
       "## Fisher p combinada"]
    for k,v in res["fisher_p"].items():
        sig="✅" if v<0.05 else ("🟡" if v<0.1 else "❌")
        L.append("- %s: **%.4f** %s (%d/%d con p<0.05)"%(k,v,sig,res["n_sig_p05"].get(k.split('_')[0].replace('arm',''),0) if False else res["n_sig_p05"].get({'armA_manager':'armA','armB_ml':'armB','armC_stacked':'armC'}.get(k,k),0),res["n_proteins"]))
    if res.get("ablations"):
        L+=["","## Ablaciones"]
        for n,a in res["ablations"].items():
            sig="✅" if a["fisher_p"]<0.05 else "❌"
            L.append("- **%s** (sin %s): Fisher p=%.4f %s"%(n,", ".join(a["dropped"]),a["fisher_p"],sig))
    L+=["","## Método fijo (percentil medio)","- "+", ".join("%s=%.1f"%(m,v) for m,v in res["mean_pct_by_method"].items())]
    if res.get("manager_choices"): L.append("- Elecciones del gestor: "+str(res["manager_choices"]))
    L+=["","## Por proteína","","| proteína | n | k | A_pick | A_p | B_p | C_p |","|---|---|---|---|---|---|---|"]
    for r in res["per_protein"]:
        L.append("| %s | %d | %d | %s | %s | %s | %s |"%(r["name"],r["n"],r["k"],r.get("A_pick","-"),r.get("A_p","-"),r.get("B_p","-"),r.get("C_p","-")))
    open(os.path.join(REPORTS,"%s.md"%res["exp_id"]),"w").write("\n".join(L))

def _append_ledger(res):
    new = not os.path.exists(LEDGER)
    with open(LEDGER,"a") as f:
        if new: f.write("exp_id,n_proteins,armA,armB,armC,ablations,note\n")
        fp=res["fisher_p"]; ab=";".join("%s=%.4f"%(n,a["fisher_p"]) for n,a in res.get("ablations",{}).items())
        f.write("%s,%d,%s,%s,%s,%s,%s\n"%(res["exp_id"],res["n_proteins"],
            fp.get("armA_manager","-"),fp.get("armB_ml","-"),fp.get("armC_stacked","-"),ab,res.get("note","").replace(","," ")))

# ---------------------------------------------------------------- CANDIDATE ---
def verify_candidate(pdb, chain, active_sel, allo_sel):
    """Verifica geométricamente: allo debe tener >=5 residuos distales (>6A del sitio activo)."""
    a=SF.load_pdb(pdb)
    ca=a.select("protein and name CA and chain %s"%chain); coords=ca.getCoords(); rn=ca.getResnums()
    idx={int(r):i for i,r in enumerate(rn)}
    def lig_ca(sel):
        near=a.select("(protein and name CA and chain %s) and within 6 of (%s and chain %s)"%(chain,sel,chain))
        return set(int(x) for x in near.getResnums()) if near is not None else set()
    act=lig_ca(active_sel); allo=lig_ca(allo_sel); amin=[]
    for r in allo:
        if r in act: amin.append(0.0); continue
        amin.append(min(np.linalg.norm(coords[idx[r]]-coords[idx[q]]) for q in act) if act else 99)
    distal=[r for r,dd in zip(allo,amin) if dd>6.0]
    ok = len(distal)>=5 and (min(amin) if amin else 0)>6.0
    return {"ok":ok,"n_active":len(act),"n_allo":len(allo),"n_distal":len(distal),"min_sep":round(min(amin),1) if amin else -1}

# ---------------------------------------------------------------- EXPAND/LOOP -
def add_candidate(name, entry):
    """Verifica geométricamente y, si pasa, agrega al catálogo + construye. Idempotente."""
    cat=load_catalog()
    if name in cat["proteins"]: return {"ok":True,"status":"ya_en_catalogo"}
    allo_sel = entry.get("gt_sel") or ("resname %s"%entry["gt_ligand"])
    act_sel  = entry["active_src"]["pat"] if entry["active_src"]["kind"]=="lig" else None
    if act_sel:  # sólo verificamos geometría cuando el sitio activo es por ligando
        v=verify_candidate(entry["holo"], entry["chain"], act_sel, allo_sel)
        if not v["ok"]: return {"ok":False,"status":"rechazado","verify":v}
    cat["proteins"][name]=entry; save_catalog(cat)
    _ensure_conservation(entry["uniprot"])
    obj,msg=build_protein(name,entry)
    def _revert():
        c=load_catalog(); c["proteins"].pop(name,None); save_catalog(c)
        cp=os.path.join(CACHE,"%s.pkl"%name);
        if os.path.exists(cp): os.remove(cp)
    if obj is None:
        _revert(); return {"ok":False,"status":"build_fallo","msg":msg}
    if obj["k"] < 5:   # exige bolsillo alosterico DISTAL (>=5 residuos distales) — honestidad
        _revert(); return {"ok":False,"status":"rechazado_no_distal","k":obj["k"]}
    return {"ok":True,"status":"agregada","build":msg}

def expand_from_pool(pool_path):
    """Recorre un pool de candidatos {name,apo,holo,chain,uniprot,gene,gt_ligand|gt_sel,active_src}
    y agrega los que verifican. Devuelve resumen."""
    pool=json.load(open(pool_path)); added,rejected=[],[]
    for c in pool.get("candidates",[]):
        r=add_candidate(c["name"], c)
        print("  %-22s %s"%(c["name"], r["status"]))
        (added if r["ok"] and r["status"]=="agregada" else rejected).append((c["name"],r.get("status")))
    return {"added":added,"rejected":rejected}

def loop(config_path, pool_path=None, cycles=1):
    """Iteración continua: (opcional) expandir desde el pool, luego correr el experimento.
    Cada ciclo genera un exp_id con timestamp de config y agrega fila al ledger."""
    cfg=json.load(open(config_path)); base=cfg.get("exp_id","RQ-EXP")
    for c in range(cycles):
        if pool_path:
            print("== ciclo %d: expandir =="%(c+1)); print(expand_from_pool(pool_path))
        cfg["exp_id"]="%s-c%d"%(base,c+1)
        print("== ciclo %d: correr =="%(c+1)); r=run_experiment(cfg)
        print("  Fisher:",r["fisher_p"])
    return "loop completo (%d ciclos)"%cycles

# ---------------------------------------------------------------- CLI ---------
if __name__=="__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "help"
    if cmd=="build":
        build_all(sys.argv[2:] or None)
    elif cmd=="run":
        cfg=json.load(open(sys.argv[2])); r=run_experiment(cfg)
        print("\n== %s =="%r["exp_id"]); print("Fisher:",r["fisher_p"])
        if r.get("ablations"): print("Ablaciones:",{n:a["fisher_p"] for n,a in r["ablations"].items()})
        print("reporte:",os.path.join(REPORTS,"%s.md"%r["exp_id"]))
    elif cmd=="verify":
        pdb,ch,act,allo=sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5]
        print(verify_candidate(pdb,ch,act,allo))
    elif cmd=="expand":
        print(expand_from_pool(sys.argv[2]))
    elif cmd=="loop":
        cfg=sys.argv[2]; pool=sys.argv[3] if len(sys.argv)>3 else None
        cyc=int(sys.argv[4]) if len(sys.argv)>4 else 1
        print(loop(cfg,pool,cyc))
    elif cmd=="ledger":
        print(open(LEDGER).read() if os.path.exists(LEDGER) else "(ledger vacío)")
    else:
        print(__doc__)
