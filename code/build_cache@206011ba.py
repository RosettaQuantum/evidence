#!/usr/bin/env python3
"""Construye los caches CIEGOS del challenge Cleveland desde las estructuras oficiales.

POR QUE EXISTE
--------------
Los caches del motor (cache/*.pkl) derivan de estructuras del ASD y ademas traen `allo`
adentro: el bolsillo conocido, leido de la estructura CON farmaco. Para el challenge eso
es inadmisible dos veces: (1) el input obligatorio son las apo oficiales (Tabla 1 del
statement), y (2) la prediccion es CIEGA — un cache que ya sabe donde esta el bolsillo
contamina todo lo que se calcule con el. Este builder produce caches SIN `allo`: las holo
no se abren aqui; se abren recien en la etapa de scoring, con la prediccion ya comprometida.

Autocontenido a proposito (numpy y stdlib): el motor completo necesita prody + descargas
de UniProt, y ninguna de esas dependencias hace falta para la red de contactos que usan la
caminata y el corredor. Menos dependencias = menos superficie donde un cambio ajeno nos
cambie el grafo sin avisar.

CONVENCIONES — las mismas selladas del motor, no inventadas aqui:
  cutoff de contacto CA-CA  8.5 A      (engine.build_protein: build_feature_table(cutoff=8.5))
  fuente (src)              residuos con algun atomo a < 4.5 A del ligando activo (GT_RADIUS)
  distal (mask)             residuos a > 6.0 A de toda fuente (DISTAL_A)
  MODEL                     solo el primero; altLoc ' ' o 'A'

Uso:  python3 build_cache.py          # construye los 4 y escribe cache_blind/RESUMEN.json
"""
import gzip, hashlib, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EST = os.path.join(HERE, "structures")
OUT = os.path.join(HERE, "cache_blind")
CUTOFF, GT_RADIUS, DISTAL_A = 8.5, 4.5, 6.0

# Cada blanco declara SU regla de fuente, porque las estructuras no son uniformes:
#  - 4OBE trae GDP+MG (el sitio activo de una GTPasa).
#  - 1OPL trae P16 (inhibidor en el sitio ATP) y ademas MYR — miristato — que marca
#    EXACTAMENTE el bolsillo alosterico que hay que predecir. MYR se excluye de la red y
#    de la fuente, y se deja registrado: si la prediccion cae ahi, nadie puede decir que
#    el ligando nos soplo la respuesta (la red es solo de CAs de proteina).
#  - 5TBY no trae ningun HETATM (apo de verdad): la fuente sale del motivo P-loop
#    GESGAGKT del sitio ATP de la miosina, detectado en la secuencia.
#  - 1NKP es c-Myc/Max sobre ADN: la funcion ES unir ADN, asi que la fuente son los
#    residuos de Myc en contacto con el ADN.
TARGETS = {
    "KRAS_4OBE":    {"pdb": "4obe", "chain": "A", "src_kind": "ligand",
                     "src_sel": ("GDP", "MG"), "nota": "GTPasa; fuente = sitio GDP/Mg"},
    "ABL1_1OPL":    {"pdb": "1opl", "chain": "A", "src_kind": "ligand",
                     "src_sel": ("P16",), "excluir": ("MYR",),
                     "nota": "quinasa; fuente = sitio ATP (P16). MYR excluido: marca el "
                             "bolsillo miristoilo que se predice a ciegas"},
    "MYOSIN_5TBY":  {"pdb": "5tby", "chain": "A", "src_kind": "motif",
                     "src_sel": "GESGAGKT", "nota": "miosina; sin HETATM — fuente = P-loop "
                                                    "(sitio ATP) por motivo de secuencia"},
    "MYC_1NKP":     {"pdb": "1nkp", "chain": "A", "src_kind": "dna",
                     "src_sel": None, "nota": "c-Myc bHLH-LZ; fuente = residuos en "
                                              "contacto con el ADN (la funcion es unirlo)"},
}

AA3 = {"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E","GLY":"G",
       "HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F","PRO":"P","SER":"S",
       "THR":"T","TRP":"W","TYR":"Y","VAL":"V","MSE":"M"}
DNA_RES = {"DA","DT","DG","DC"}


def parse_pdb(pid):
    """Atomos del MODEL 1: (registro, resname, chain, resnum, atomname, xyz)."""
    out = []
    in_model = 0
    for l in gzip.open(os.path.join(EST, pid + ".pdb.gz"), "rt", encoding="latin1"):
        if l.startswith("MODEL"):
            in_model += 1
            if in_model > 1:
                break
            continue
        if l.startswith(("ATOM", "HETATM")):
            alt = l[16]
            if alt not in (" ", "A"):
                continue
            out.append((l[:6].strip(), l[17:20].strip(), l[21], int(l[22:26]),
                        l[12:16].strip(),
                        np.array([float(l[30:38]), float(l[38:46]), float(l[46:54])])))
    return out


def firma(arrays):
    """sha256 del CONTENIDO de un conjunto de arreglos, no del archivo que los guarda.

    El hash del .npz NO sirve como promesa verificable: el contenedor es un zip y su
    compresion depende de la version de numpy. En esta maquina reproducia; en el runner
    de CI, con numpy 2, daba distinto para datos identicos — y el CI lo atrapo en su
    primera corrida. Un archivo de evidencia que declara "recomputa este sha256" tiene
    que declarar un hash que cualquiera pueda recomputar, y eso solo lo cumple el
    contenido: bytes de cada arreglo, en orden de clave, con dtype y forma declarados.
    """
    h = hashlib.sha256()
    for k in sorted(arrays):
        a = np.ascontiguousarray(arrays[k])
        h.update(k.encode())
        h.update(("%s|%s|" % (a.dtype.str, a.shape)).encode())
        h.update(a.tobytes())
    return "sha256:" + h.hexdigest()


def firma_npz(path):
    z = np.load(path, allow_pickle=False)
    return firma({k: z[k] for k in z.files})


def load(name, carpeta=None):
    """Carga un cache ciego. UNICA forma de leerlos — si el formato cambia, cambia aqui.

    Devuelve un dict con la misma forma que producia `build`, para que los consumidores
    (rank_quantum, score_predictions, pruebas) no sepan si por debajo hay npz o cualquier
    otra cosa. Antes cada consumidor hacia su propio `pickle.load` y bastaba una version
    distinta de numpy para romperlos todos a la vez.
    """
    p = os.path.join(carpeta or OUT, name + ".npz")
    z = np.load(p, allow_pickle=False)
    d = json.loads(str(z["meta"][0]))
    d.update({"A": z["A"], "coords": z["coords"], "mask": z["mask"],
              "src": z["src"].tolist(),
              "ids": list(zip(z["ids_chain"].tolist(), z["ids_resnum"].tolist()))})
    return d


def build(name, t):
    atoms = parse_pdb(t["pdb"])
    ch = t["chain"]
    # CAs de la cadena elegida — la red es SOLO proteina; HETATM jamas entra al grafo
    cas = [(rn, np.asarray(x)) for reg, res, c, rn, an, x in atoms
           if reg == "ATOM" and c == ch and an == "CA" and res in AA3]
    seq = "".join(AA3[res] for reg, res, c, rn, an, x in atoms
                  if reg == "ATOM" and c == ch and an == "CA" and res in AA3)
    ids = [(ch, rn) for rn, _ in cas]
    coords = np.vstack([x for _, x in cas])
    D = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    A = ((D < CUTOFF) & (D > 0)).astype(float)

    # atomos de la fuente segun la regla declarada
    if t["src_kind"] == "ligand":
        src_atoms = [x for reg, res, c, rn, an, x in atoms
                     if reg == "HETATM" and res in t["src_sel"] and c == ch]
    elif t["src_kind"] == "dna":
        src_atoms = [x for reg, res, c, rn, an, x in atoms
                     if reg == "ATOM" and res in DNA_RES]
    else:                                             # motif
        i = seq.find(t["src_sel"])
        if i < 0:
            raise SystemExit("%s: motivo %s NO esta en la secuencia — no se adivina, se aborta"
                             % (name, t["src_sel"]))
        src_idx = list(range(i, i + len(t["src_sel"])))
        src_atoms = None

    if src_atoms is not None:
        if not src_atoms:
            raise SystemExit("%s: la regla de fuente no encontro atomos — se aborta" % name)
        L = np.vstack(src_atoms)
        # todos los atomos de la proteina (no solo CA) para el contacto < 4.5 A
        prot = [(rn, x) for reg, res, c, rn, an, x in atoms
                if reg == "ATOM" and c == ch and res in AA3]
        cerca = set()
        P = np.vstack([x for _, x in prot])
        dmin = np.linalg.norm(P[:, None, :] - L[None, :, :], axis=-1).min(axis=1)
        for (rn, _), dm in zip(prot, dmin):
            if dm < GT_RADIUS:
                cerca.add(rn)
        src_idx = [k for k, (c_, rn) in enumerate(ids) if rn in cerca]

    if len(src_idx) < 3:
        raise SystemExit("%s: fuente con %d residuos (<3) — se aborta" % (name, len(src_idx)))

    Dm = np.linalg.norm(coords[:, None, :] - coords[src_idx][None, :, :], axis=-1)
    mask = Dm.min(axis=1) > DISTAL_A

    obj = {"name": name, "pdb_id": t["pdb"].upper(), "chain": ch,
           "pdb_sha256": "sha256:" + hashlib.sha256(
               open(os.path.join(EST, t["pdb"] + ".pdb.gz"), "rb").read()).hexdigest(),
           "ids": ids, "coords": coords, "A": A, "seq": seq,
           "src": sorted(src_idx), "src_method": "%s:%s" % (t["src_kind"], t["src_sel"]),
           "mask": mask, "n": len(ids), "n_distal": int(mask.sum()),
           "excluido": list(t.get("excluir", ())), "nota": t["nota"],
           "convenciones": {"cutoff": CUTOFF, "gt_radius": GT_RADIUS, "distal_a": DISTAL_A},
           "ciego": True}   # SIN 'allo': las holo no se abrieron para construir esto
    return obj


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    resumen = {}
    print("%-14s %5s %6s %6s %8s  %s" % ("blanco", "n", "src", "distal", "aristas", "fuente"))
    for name, t in TARGETS.items():
        o = build(name, t)
        p = os.path.join(OUT, name + ".npz")
        # npz y no pickle: un pickle escrito con numpy 2 no lo lee numpy 1 (se rompio en
        # esta misma maquina al instalar dependencias), y ademas cargarlo ejecuta codigo
        # arbitrario. Un cache es datos, no un programa.
        np.savez_compressed(
            p, A=o["A"], coords=o["coords"], mask=o["mask"],
            src=np.asarray(o["src"], dtype=np.int32),
            ids_chain=np.array([c for c, r in o["ids"]]),
            ids_resnum=np.array([r for c, r in o["ids"]], dtype=np.int32),
            meta=np.array([json.dumps({k: v for k, v in o.items()
                                       if k not in ("A", "coords", "mask", "src", "ids")},
                                      ensure_ascii=False)]))
        resumen[name] = {"contenido_sha256": firma_npz(p),
                         "pdb": o["pdb_id"], "pdb_sha256": o["pdb_sha256"], "chain": o["chain"],
                         "n": o["n"], "src": len(o["src"]), "n_distal": o["n_distal"],
                         "src_method": o["src_method"], "excluido": o["excluido"]}
        print("%-14s %5d %6d %6d %8d  %s" % (name, o["n"], len(o["src"]), o["n_distal"],
                                             int(o["A"].sum() // 2), o["src_method"]))
    json.dump({"_doc": "Caches CIEGOS del challenge (sin allo; holo sin abrir). "
                       "Convenciones del motor sellado: cutoff 8.5, fuente <4.5 A del "
                       "ligando/motivo/ADN, distal >6.0 A.",
               "generado": "build_cache.py", "targets": resumen},
              open(os.path.join(OUT, "RESUMEN.json"), "w"), indent=1, ensure_ascii=False)
    print("\nescrito cache_blind/ (%d caches + RESUMEN.json con hashes)" % len(resumen))
