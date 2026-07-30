"""Conector AlloBench -> pool de candidatos del motor.
Baja/parsea AlloBench.csv (ASD curado: 2034 estructuras / 418 proteinas), filtra
humanas/mamiferas con modulador de molecula pequena y sitio activo+alosterico
etiquetados, deduplica por gen vs el catalogo, y escribe entradas de candidato.
El motor las VERIFICA geometricamente (prody) antes de agregarlas: este conector
solo propone; la verdad la pone la geometria."""
import os, sys, csv, json, ast, urllib.request
HERE=os.path.dirname(os.path.abspath(__file__))
CSV=os.path.join(HERE,"AlloBench.csv")
URL="https://raw.githubusercontent.com/djmaity/allobench/main/AlloBench.csv"
CATALOG=os.path.join(HERE,"catalog.json")
POOL=os.path.join(HERE,"candidates_pool.json")
MAMMAL={"Human","Rat","Mouse","Bovine","Pig","Rabbit"}
IONS={"MG","MN","ZN","CA","NA","K","CL","FE","NI","CO","CD","HG","SO4","PO4","GOL","EDO","ACT","HOH"}

def ensure_csv():
    if os.path.exists(CSV): return
    req=urllib.request.Request(URL, headers={"User-Agent":"RosettaQ/1.0"})
    open(CSV,"wb").write(urllib.request.urlopen(req,timeout=60).read())

def _parse_list(s):
    try: return ast.literal_eval(s) if s and s.strip().startswith("[") else []
    except Exception: return []

def catalog_genes():
    if not os.path.exists(CATALOG): return set()
    return {v["gene"].upper() for v in json.load(open(CATALOG))["proteins"].values()}

def build_candidates(cap=40, min_allo=5):
    ensure_csv()
    rows=list(csv.DictReader(open(CSV)))
    have=catalog_genes()
    best={}   # gen -> mejor fila
    for r in rows:
        if r.get("organism") not in MAMMAL: continue
        if r.get("modulator_class")!="Lig": continue
        gene=(r.get("target_gene") or "").upper()
        if not gene or gene in have: continue
        lig=(r.get("modulator_alias") or "").strip()
        if not (2<=len(lig)<=4) or lig.upper() in IONS: continue
        allo=_parse_list(r.get("allosteric_site_residue","")); act=_parse_list(r.get("active_site_residue",""))
        if len(allo)<min_allo or len(act)<3: continue
        uni=(r.get("pdb_uniprot") or "").strip()
        if not uni: continue
        # cadena del sitio alosterico (primer residuo 'A-PHE-157')
        try: ch=allo[0].split("-")[0]
        except Exception: ch="A"
        score=len(allo)+ (5 if r["organism"]=="Human" else 0)
        cand={"name":"%s_ALLO"%gene,"apo":r["allosteric_pdb"],"holo":r["allosteric_pdb"],
              "chain":ch,"uniprot":uni,"gene":gene,"gt_ligand":lig,
              "active_src":{"kind":"uniprot_pos","positions":[int(x) for x in act]},
              "area":"onco","source":"AlloBench %s"%r.get("target_id","")}
        if gene not in best or score>best[gene][0]:
            best[gene]=(score,cand)
    cands=[c for _,c in sorted(best.values(), key=lambda x:-x[0])][:cap]
    return cands

def write_pool(cands, merge=True):
    pool={"_doc":"pool auto-generado por allobench_connector","candidates":[]}
    if merge and os.path.exists(POOL):
        pool=json.load(open(POOL)); pool.setdefault("candidates",[])
        have={c["name"] for c in pool["candidates"]}
        cands=[c for c in cands if c["name"] not in have]
    pool["candidates"].extend(cands)
    json.dump(pool, open(POOL,"w"), indent=1)
    return len(cands)

if __name__=="__main__":
    cap=int(sys.argv[1]) if len(sys.argv)>1 else 40
    cands=build_candidates(cap=cap)
    n=write_pool(cands)
    print("candidatos nuevos de AlloBench:", n, "(de %d unicos)"%len(cands))
    for c in cands[:n]: print("  %-16s %s %s gt=%s act=%d"%(c["gene"],c["apo"],c["chain"],c["gt_ligand"],len(c["active_src"]["positions"])))
