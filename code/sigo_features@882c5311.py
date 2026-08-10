"""
GLIFO — capa reutilizable de VARIABLES por residuo (SIGO ⇄ Cleveland).
================================================================
"Glifo": como la Piedra de Rosetta se descifro por sus glifos, Glifo le da a cada
residuo su glifo — su vector de variables sacadas de 1.277 fuentes catalogadas en
SIGO — para que el modelo pueda "leer" la proteina. (pipe v1)

El harness (allo_challenge.py) corre la caminata cuantica sobre una adyacencia
CA-CA BINARIA y PELADA: cada residuo es un puntito, cada arista es contacto<cutoff.
Sin atributos. El veredicto nulo (nada significativo) es sobre esa topologia cruda.

Este modulo es la CANERIA reutilizable que le mete "mas o mejores variables" al
grafo, jalando atributos por residuo de las fuentes ya catalogadas en SIGO
(sigo-db.source_evaluations, 1.277 fuentes con API+tier). Corre igual para las 4
dianas del reto o para 400 proteinas nuevas: la entrada es {uniprot, gene, pdb,
chain}; la salida es una tabla de features por residuo + un Hamiltoniano anotado
que reemplaza a la adyacencia pelada, drop-in para allo_challenge.props().

NO sella ni ancla nada (eso es del lab/notario). Solo produce INSUMOS.
NO toca datos de suscriptores de SIGO. Solo lee el catalogo de fuentes.

Fuentes usadas (nombre en SIGO → rol):
  PDB / PDBe      estructura 3D y ligando (grafo + verdad-terreno)   tier 3, API
  UniProt         sitios funcionales/de union, dominios, PTM          tier 3, API
  ClinVar         densidad de variantes clinicas por residuo          tier 2, API (ncbi_eutils)
  InterPro/Pfam   dominio por residuo                                 tier 3, API   [hook]
  COSMIC          hotspots somaticos de cancer                        tier 3, API/0.5 [hook: SIGO]
  (conservacion)  MSA/ortologos                                       [hook: SIGO harvester]

Cada feature que NO se pudo jalar queda como None (nunca se inventa un valor).
"""
import os, sys, re, json, time, urllib.request, urllib.parse
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prody
prody.confProDy(verbosity='none')

# Reutilizamos las primitivas del harness (import SEGURO: allo_challenge solo
# define funciones/constantes, no ejecuta corridas al importar).
from allo_challenge import ca_network, contacts, idx_of, GT_RADIUS

AA3TO1 = {
 'ALA':'A','ARG':'R','ASN':'N','ASP':'D','CYS':'C','GLN':'Q','GLU':'E','GLY':'G',
 'HIS':'H','ILE':'I','LEU':'L','LYS':'K','MET':'M','PHE':'F','PRO':'P','SER':'S',
 'THR':'T','TRP':'W','TYR':'Y','VAL':'V','MSE':'M','SEC':'U'}

# ---------------------------------------------------------------- catalogo SIGO
# Subconjunto del catalogo real (sigo-db.source_evaluations) relevante al modelo.
SOURCES = {
  "pdb":     {"name":"Protein Data Bank (PDB)", "tier":3, "api":"rest",
              "base":"https://files.rcsb.org/", "role":"structure+groundtruth"},
  "uniprot": {"name":"UniProt", "tier":3, "api":"rest",
              "base":"https://rest.uniprot.org/uniprotkb/", "role":"residue-annotation"},
  "clinvar": {"name":"ClinVar", "tier":2, "api":"ncbi_eutils",
              "base":"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/", "role":"mutation-density"},
  "interpro":{"name":"InterPro", "tier":3, "api":"rest",
              "base":"https://www.ebi.ac.uk/interpro/api/", "role":"domain"},
  "cosmic":  {"name":"COSMIC", "tier":3, "api":"sigo-harvest", "role":"somatic-hotspot"},
}

UA = {"User-Agent": "RosettaQuantum-SIGO-pipe/1.0 (lab@rosettacuantum.com)"}


def _get_json(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# ---------------------------------------------------------------- estructura
def load_pdb(pdb, subset=None):
    """Baja/parses una estructura del PDB por ID (prody la cachea)."""
    return prody.parsePDB(pdb.lower(), subset=subset)


def residue_ids_and_types(atoms, sel):
    ca = atoms.select(sel)
    ids   = [(c, int(r)) for c, r in zip(ca.getChids(), ca.getResnums())]
    types = [AA3TO1.get(rn, 'X') for rn in ca.getResnames()]
    return ids, types


# ---------------------------------------------------------------- features locales (grafo)
def graph_features(A, coords, src_idx):
    """Atributos que salen del propio grafo/estructura, sin API.
    degree, closeness geodesica al sitio activo, y numero de coordinacion (entierro)."""
    n = A.shape[0]
    deg = A.sum(1)
    # closeness geodesica a la fuente (BFS multi-fuente)
    adj = [np.nonzero(A[i])[0] for i in range(n)]
    INF = 10**9
    dist = np.full(n, INF, dtype=float)
    frontier = list(src_idx)
    for s in src_idx: dist[s] = 0
    d = 0
    while frontier:
        d += 1; nxt = []
        for u in frontier:
            for v in adj[u]:
                if dist[v] == INF:
                    dist[v] = d; nxt.append(v)
        frontier = nxt
    closeness = 1.0 / np.maximum(dist, 1.0)
    # coordinacion = vecinos CA dentro de 10A (proxy de entierro)
    dd = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    coordination = ((dd < 10.0) & (dd > 0)).sum(1).astype(float)
    return {"degree": deg, "closeness_to_active": closeness, "coordination": coordination}


def dynamics_features(ca_atoms, n_modes=20):
    """Modos de vibracion por residuo (dinamica = corazon de la alosteria).
    GNM/ANM sobre los CA: fluctuaciones cuadraticas medias (movilidad) y amplitud
    del modo mas lento (residuos-bisagra mecanicos). Honesto: si falla, ceros."""
    from prody import GNM, ANM, calcSqFlucts
    n = ca_atoms.numAtoms()
    out = {"gnm_msf": np.zeros(n), "anm_msf": np.zeros(n), "slow_mode": np.zeros(n)}
    try:
        gnm = GNM(); gnm.buildKirchhoff(ca_atoms, cutoff=10.0)
        gnm.calcModes(n_modes=min(n_modes, n-1))
        out["gnm_msf"] = np.asarray(calcSqFlucts(gnm), float)
        v0 = np.asarray(gnm.getEigvecs()[:, 0], float)
        out["slow_mode"] = np.abs(v0)   # cruces por cero = bisagras mecanicas
    except Exception:
        pass
    try:
        anm = ANM(); anm.buildHessian(ca_atoms, cutoff=13.0)
        anm.calcModes(n_modes=min(n_modes, 3*n-6))
        out["anm_msf"] = np.asarray(calcSqFlucts(anm), float)
    except Exception:
        pass
    return out


# ---------------------------------------------------------------- UniProt
def uniprot_annotations(accession):
    """Devuelve (seq, por_posicion) donde por_posicion[p] = set(flags) 1-indexado.
    Flags: active_site, binding_site, domain, ptm, motif, dna_binding, np_binding."""
    # entrada completa (sin filtro de campos: los nombres de campo de UniProt son
    # fragiles y un solo invalido da 400; parseamos por tipo de feature).
    url = SOURCES["uniprot"]["base"] + accession + ".json"
    d = _get_json(url)
    seq = d.get("sequence", {}).get("value", "")
    per = {}
    TYPE = {
        "Active site":"active_site", "Binding site":"binding_site", "Domain":"domain",
        "Motif":"motif", "DNA binding":"dna_binding", "Nucleotide binding":"np_binding",
        "Modified residue":"ptm", "Site":"site",
    }
    for f in d.get("features", []):
        flag = TYPE.get(f.get("type"))
        if not flag:
            continue
        loc = f.get("location", {})
        s = loc.get("start", {}).get("value"); e = loc.get("end", {}).get("value")
        if s is None or e is None:
            continue
        for p in range(int(s), int(e) + 1):
            per.setdefault(p, set()).add(flag)
    return seq, per


def align_by_sequence(items, uni_seq, min_block=8, max_passes=5):
    """Alinea residuos de la estructura -> posiciones UniProt POR SECUENCIA
    (inmune a la numeracion: sirve para isoformas 1a/1b de ABL, construcciones y
    modelos por homologia). Mejor que SIFTS aqui porque es autocontenido y no
    depende de que el PDB traiga numeros de autor.
      items = [(chain,resnum,aa), ...] de UNA cadena.
      Estrategia: busca el DESFASE k (upos = resnum + k) que maximiza identidad;
      greedy multi-desfase para cubrir dominios con offsets distintos (SH3/SH2/
      kinasa). Preserva el espaciado (respeta huecos). Devuelve (chain,resnum)->upos.
    """
    Lu = len(uni_seq)
    if not items or Lu == 0:
        return {}
    remaining = list(range(len(items)))
    maxr = max(r for _, r, _ in items)
    out = {}
    for _ in range(max_passes):
        best_k, best_sc = None, 0
        for k in range(1 - maxr, Lu):
            sc = 0
            for o in remaining:
                _, r, aa = items[o]
                u = r + k
                if 0 < u <= Lu and uni_seq[u - 1] == aa:
                    sc += 1
            if sc > best_sc:
                best_sc, best_k = sc, k
        if best_k is None or best_sc < min_block:
            break
        newly = set()
        for o in remaining:
            ch, r, aa = items[o]
            u = r + best_k
            if 0 < u <= Lu and uni_seq[u - 1] == aa:
                out[(ch, r)] = u
                newly.add(o)
        remaining = [o for o in remaining if o not in newly]
        if not remaining:
            break
    return out


def map_uniprot_to_structure(ids, types, chain, uni_seq, uni_per):
    """Traduce cada residuo de la estructura a su posicion UniProt (por secuencia)
    y le adjunta las flags de anotacion. Devuelve dict id->set(flags) + stats."""
    items = [(c, r, t) for (c, r), t in zip(ids, types) if (not chain or c == chain)]
    pos_map = align_by_sequence(items, uni_seq)
    out, matched = {}, 0
    for (c, r) in ids:
        if chain and c != chain:
            continue
        upos = pos_map.get((c, r))
        if upos is None:
            continue
        flags = uni_per.get(upos)
        if flags:
            out[(c, r)] = set(flags)
        matched += 1
    return out, {"aligned_via": "sequence", "n_residues_chain": len(items),
                 "n_aligned_to_uniprot": len(pos_map),
                 "coverage": round(len(pos_map) / max(1, len(items)), 3),
                 "n_with_annotation": len(out)}


# ---------------------------------------------------------------- ClinVar (densidad de mutaciones)
_PCHANGE = re.compile(r'p\.([A-Za-z]{3})(\d+)([A-Za-z]{3}|=|\*|Ter)')

def clinvar_density(gene, ids, chain, retmax=400):
    """Cuenta variantes ClinVar missense por numero de residuo (best-effort).
    Parte de los titulos 'NM_...(GENE):c...(p.Xxx123Yyy)'. Devuelve id->conteo.
    Si falla la red, devuelve {} y una nota (nunca inventa)."""
    base = SOURCES["clinvar"]["base"]
    try:
        term = urllib.parse.quote(f'{gene}[gene] AND "missense variant"[molecular consequence]')
        es = _get_json(f"{base}esearch.fcgi?db=clinvar&retmax={retmax}&retmode=json&term={term}")
        idl = es.get("esearchresult", {}).get("idlist", [])
        if not idl:
            return {}, {"n_variants": 0, "note": "sin resultados ClinVar"}
        counts = {}
        for i in range(0, len(idl), 200):
            chunk = ",".join(idl[i:i+200])
            su = _get_json(f"{base}esummary.fcgi?db=clinvar&retmode=json&id={chunk}")
            res = su.get("result", {})
            for vid in res.get("uids", []):
                title = res.get(vid, {}).get("title", "")
                m = _PCHANGE.search(title)
                if not m:
                    continue
                pos = int(m.group(2))
                key = (chain, pos) if chain else pos
                counts[key] = counts.get(key, 0) + 1
            time.sleep(0.12)  # cortesia NCBI
        # limitar a residuos presentes en la estructura
        present = set(ids)
        dens = {k: v for k, v in counts.items() if (k in present)}
        return dens, {"n_variants_parsed": sum(counts.values()),
                      "n_mapped_to_structure": len(dens)}
    except Exception as e:
        return {}, {"error": f"{type(e).__name__}: {e}",
                    "note": "ClinVar no disponible; feature queda None (no se inventa)"}


# ---------------------------------------------------------------- ensamblado

def load_conservation(accession, ids, types, chain, cache_dir="conservation_cache"):
    """Conservacion por residuo desde conservation_cache/{acc}.json (UniRef50 + entropia
    de Shannon). Alinea por secuencia (align_by_sequence) contra la ref UniProt.
    Honestidad: si no hay cache o no se pudo jalar, devuelve (None, stat). Nunca inventa."""
    import os, json as _json
    fp=os.path.join(cache_dir, "%s.json"%accession)
    if not os.path.exists(fp):
        return None, {"error":"no conservation cache", "acc":accession}
    d=_json.load(open(fp))
    cons=d.get("cons"); ref=d.get("ref")
    if cons is None or not ref:
        return None, {"error":"conservation is None", "acc":accession, "meta":d.get("meta")}
    items=[(c,r,t) for (c,r),t in zip(ids,types) if (not chain or c==chain)]
    pos_map=align_by_sequence(items, ref)
    out=np.full(len(ids), np.nan)
    nmap=0
    for i,(c,r) in enumerate(ids):
        if chain and c!=chain: continue
        u=pos_map.get((c,r))
        if u is None or u>len(cons): continue
        val=cons[u-1]
        if val is not None:
            out[i]=float(val); nmap+=1
    # nan -> 0 (residuos sin conservacion mapeada); honesto: se registra la cobertura
    cov=nmap/max(1,len([1 for (c,_) in ids if (not chain or c==chain)]))
    return np.nan_to_num(out, nan=0.0), {"source":"UniRef50+entropia", "acc":accession,
            "n_mapped":nmap, "coverage":round(cov,3), "n_homologs":d.get("meta",{}).get("n_homologs")}

def build_feature_table(target, cutoff=8.5):
    """target = dict del manifest con apo/chain/uniprot/gene/source_sel.
    Devuelve ids, coords, A binaria, src_idx, y la tabla de features por residuo."""
    apo = load_pdb(target["apo"])
    sel = target.get("sel", "protein and name CA and chain " + target["chain"])
    A, ids, coords, seq, D = ca_network(apo, sel, cutoff)
    types = [AA3TO1.get(rn, 'X') for rn in apo.select(sel).getResnames()]

    # fuente = sitio activo, leido geometricamente del ligando natural (igual que el harness)
    src_res = contacts(apo, target["source_ligsel"], sel) if target.get("source_ligsel") else []
    src_idx = idx_of(ids, src_res)

    feats = {}
    prov = {}

    # 1) grafo/estructura (local)
    gf = graph_features(A, coords, src_idx if src_idx else [0])
    for k, v in gf.items():
        feats[k] = v
    prov["graph"] = {"source": "PDB (local)", "features": list(gf.keys())}

    # 1b) dinamica (modos de vibracion GNM/ANM) — por residuo
    try:
        dyn = dynamics_features(apo.select(sel))
        for k, v in dyn.items():
            feats[k] = v
        prov["dynamics"] = {"source": "GNM/ANM (prody, local)", "features": list(dyn.keys())}
    except Exception as e:
        prov["dynamics"] = {"error": f"{type(e).__name__}: {e}"}
        for k in ("gnm_msf","anm_msf","slow_mode"):
            feats[k] = np.zeros(len(ids))

    # 2) UniProt
    uni_flags = {}
    try:
        useq, uper = uniprot_annotations(target["uniprot"])
        uni_flags, ustats = map_uniprot_to_structure(ids, types, target["chain"], useq, uper)
        prov["uniprot"] = {"source": SOURCES["uniprot"]["name"], "accession": target["uniprot"], **ustats}
    except Exception as e:
        prov["uniprot"] = {"error": f"{type(e).__name__}: {e}"}
    for flag in ("active_site","binding_site","domain","ptm","motif","dna_binding","np_binding","site"):
        feats["uni_"+flag] = np.array([1.0 if flag in uni_flags.get(idc, set()) else 0.0 for idc in ids])

    # 3) ClinVar densidad de mutacion
    dens, cstats = ({}, {"skipped": True})
    if target.get("gene"):
        dens, cstats = clinvar_density(target["gene"], ids, target["chain"])
    prov["clinvar"] = {"source": SOURCES["clinvar"]["name"], **cstats}
    feats["clinvar_density"] = np.array([float(dens.get(idc, 0)) for idc in ids]) if dens else None

    # 4) conservacion evolutiva (REAL, desde conservation_cache: UniRef50 + entropia)
    cons_arr, cstat = load_conservation(target["uniprot"], ids, types, target["chain"])
    feats["conservation"] = cons_arr
    prov["conservation"] = cstat
    # 4b) hooks aun documentados (no jalados aqui): COSMIC requiere licencia
    prov["hooks"] = {"cosmic_hotspot": "COSMIC via SIGO (requiere licencia)",
                     "interpro_domain": SOURCES["interpro"]["base"]}
    feats["cosmic_hotspot"] = None

    return {"ids": ids, "coords": coords, "A": A, "src_idx": src_idx,
            "src_residues": src_res, "types": types, "features": feats,
            "provenance": prov, "cutoff": cutoff}


# ---------------------------------------------------------------- Hamiltoniano anotado
def annotated_hamiltonian(A, coords, feats, weights, edge_mode="binary", sigma=6.0):
    """H = W ⊙ A  +  diag(alpha · potencial_de_sitio).  Hermitiano (real simetrico),
    asi exp(-iHt) sigue siendo unitario -> caminata cuantica valida.
      - weights: dict feature->coef para el potencial diagonal (on-site).
      - edge_mode: 'binary' (=A) o 'gaussian' (w_ij=exp(-d^2/2σ^2), 'mejor variable').
    Drop-in: reemplaza la 'A' que allo_challenge.props() mete en exp(-iAt)."""
    n = A.shape[0]
    # aristas
    if edge_mode == "gaussian":
        d = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
        W = np.exp(-(d**2) / (2*sigma**2)) * (A > 0)
        np.fill_diagonal(W, 0.0)
    else:
        W = A.copy()
    # potencial on-site (diagonal)
    v = np.zeros(n)
    used = {}
    for fname, coef in weights.items():
        x = feats.get(fname)
        if x is None:
            continue
        x = np.asarray(x, dtype=float)
        rng = x.max() - x.min()
        xn = (x - x.min()) / rng if rng > 1e-12 else x*0.0   # normaliza 0..1
        v += coef * xn
        used[fname] = coef
    H = W.copy()
    H[np.diag_indices(n)] += v
    H = 0.5 * (H + H.T)  # forzar simetria numerica
    return H, {"edge_mode": edge_mode, "onsite_weights_used": used,
               "is_symmetric": bool(np.allclose(H, H.T))}


# ---------------------------------------------------------------- CLI
if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = json.load(open(os.path.join(here, "cleveland_manifest.json")))
    which = sys.argv[1] if len(sys.argv) > 1 else "KRAS_G12C"
    tgt = manifest["targets"][which]
    print(f"== {which}  apo={tgt['apo']} chain={tgt['chain']} uniprot={tgt['uniprot']}")
    ft = build_feature_table(tgt, cutoff=8.5)
    n = len(ft["ids"])
    print(f"   residuos={n}  sitio_activo(fuente)={len(ft['src_idx'])}")
    for k, v in ft["provenance"].items():
        print(f"   [{k}] {v}")
    # resumen de cobertura de cada feature
    print("   cobertura de features:")
    for fname, arr in ft["features"].items():
        if arr is None:
            print(f"     {fname:22s} None (hook / no disponible)")
        else:
            arr = np.asarray(arr, dtype=float)
            print(f"     {fname:22s} nz={int((arr>0).sum()):4d}/{n}  max={arr.max():.2f}")
    # ejemplo de Hamiltoniano anotado
    W = {"uni_binding_site": 1.0, "uni_active_site": 1.0, "clinvar_density": 0.5,
         "coordination": 0.3}
    H, meta = annotated_hamiltonian(ft["A"], ft["coords"], ft["features"], W, edge_mode="gaussian")
    print("   Hamiltoniano anotado:", meta)
    # verificacion de unitariedad de exp(-iHt)
    from scipy.linalg import expm
    U = expm(-1j*H*1.0)
    err = np.abs(U.conj().T @ U - np.eye(n)).max()
    print(f"   unitariedad exp(-iHt): max|U*U - I| = {err:.2e}  ({'OK' if err<1e-8 else 'REVISAR'})")
