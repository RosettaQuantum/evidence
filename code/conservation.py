"""Conservacion evolutiva por residuo (real, autocontenida).
Baja miembros del cluster UniRef50 del accession, los alinea de a pares contra la
secuencia de referencia (Biopython, sin aligner externo), y calcula por posicion de
referencia la conservacion = 1 - entropia_Shannon_normalizada. Honestidad: si no se
puede jalar, devuelve None; nunca inventa."""
import urllib.request, json, numpy as np
from Bio import Align
from Bio.Align import substitution_matrices

AA = "ACDEFGHIKLMNPQRSTVWY"

def _fetch(url, timeout=30):
    req=urllib.request.Request(url, headers={"User-Agent":"RosettaQ/1.0"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode()

def ref_sequence(acc):
    try:
        fa=_fetch("https://rest.uniprot.org/uniprotkb/%s.fasta"%acc)
        return "".join(fa.split("\n")[1:]).strip()
    except Exception: return None

def _seq_from_fasta(fa):
    return "".join(l.strip() for l in fa.split("\n")[1:] if not l.startswith(">"))

def uniref_members(acc, ident="0.5", cap=50):
    """IDs de miembros del cluster UniRef -> secuencias via UniProtKB fasta."""
    try:
        url=("https://rest.uniprot.org/uniref/search?query=uniprot_id:%s+AND+identity:%s"
             "&fields=id&format=json&size=1"%(acc,ident))
        cid=json.loads(_fetch(url))["results"][0]["id"]
        ids=[x for x in _fetch("https://rest.uniprot.org/uniref/%s/members?format=list&size=%d"%(cid,cap)).split("\n") if x.strip()][:cap]
        from concurrent.futures import ThreadPoolExecutor
        def one(mid):
            try:
                s=_seq_from_fasta(_fetch("https://rest.uniprot.org/uniprotkb/%s.fasta"%mid, timeout=15))
                return s if 30<len(s)<3000 else None
            except Exception: return None
        with ThreadPoolExecutor(max_workers=12) as ex:
            return [s for s in ex.map(one, ids) if s]
    except Exception: return []

def conservation(acc, ref=None, ident="0.5", cap=60):
    ref = ref or ref_sequence(acc)
    if not ref: return None, {"error":"no ref seq"}
    members=uniref_members(acc, ident, cap)
    if len(members)<8: return None, {"error":"too few homologs (%d)"%len(members)}
    aln=Align.PairwiseAligner(); aln.substitution_matrix=substitution_matrices.load("BLOSUM62")
    aln.open_gap_score=-11; aln.extend_gap_score=-1; aln.mode="global"
    L=len(ref); counts=[dict() for _ in range(L)]; depth=np.zeros(L)
    used=0
    for m in members:
        m="".join(c for c in m.upper() if c in AA)
        if len(m)<30: continue
        try: a=aln.align(ref, m)[0]
        except Exception: continue
        used+=1
        # mapear columnas alineadas a posiciones de referencia
        idx=a.indices  # 2xN: fila0=ref, fila1=member (-1 = gap)
        for k in range(idx.shape[1]):
            ri=idx[0,k]; mi=idx[1,k]
            if ri<0: continue
            aa = m[mi] if mi>=0 else "-"
            counts[ri][aa]=counts[ri].get(aa,0)+1; 
        for ri in range(L): 
            pass
    # profundidad y conservacion por posicion
    cons=np.zeros(L)
    for i in range(L):
        c=counts[i]; tot=sum(c.values())
        if tot<4: cons[i]=np.nan; continue
        p=np.array([v/tot for k,v in c.items() if k in AA])
        if p.sum()<=0: cons[i]=np.nan; continue
        p=p/p.sum(); H=-(p*np.log(p)).sum(); Hmax=np.log(20)
        cons[i]=1.0 - H/Hmax
    return cons, {"acc":acc,"n_homologs":used,"L":L,"frac_covered":float(np.mean(~np.isnan(cons)))}

if __name__=="__main__":
    import sys
    acc=sys.argv[1] if len(sys.argv)>1 else "P01116"
    cons,meta=conservation(acc)
    print(meta)
    if cons is not None:
        # KRAS: P-loop G10-S17 (GAGGVGKS) muy conservado; probar
        ref=ref_sequence(acc)
        top=np.argsort(-np.nan_to_num(cons))[:15]
        print("top-15 conservados (pos1, aa):", sorted([(int(i+1),ref[i],round(float(cons[i]),2)) for i in top]))
        print("media conservacion:", round(float(np.nanmean(cons)),3))
