"""
RosettaQ — verificador de sellos del archivo (esquema rosettaq-archive/v1).

Convencion CANONICA (vigente, para todo sello nuevo):
    content_hash = sha256( json.dumps({"meta": meta_sin_content_hash, <cuerpo>},
                                      sort_keys=True, ensure_ascii=False) )
donde <cuerpo> son todas las claves de nivel superior del archivo EXCEPTO
"meta" y "storage" (para un RUN eso es "w6"; para un PREREG, su bloque propio).
"storage" queda fuera a proposito: describe donde vive la copia, no que dice.

Convencion LEGADA (historica, NO usar para sellos nuevos):
    sha256( json.dumps({"meta": {**meta, "content_hash": None}, "w6": w6},
                       sort_keys=True, separators=(",",":")) )   # ensure_ascii por defecto
(diferencias con la canonica: content_hash se anula en vez de quitarse, separadores
compactos, y ensure_ascii por defecto)

Por que se aceptan las dos: las series de portafolios (EXP-0012-*) y de red
(EXP-0033-*) se sellaron con la convencion legada y ya estan PUBLICADAS y
ANCLADAS en OpenTimestamps. Sus hashes son hechos publicos inmutables: re-sellarlos
invalidaria anclas reales y evidencia que terceros ya pueden citar. Un archivo se
verifica contra la convencion con la que fue sellado; el verificador declara cual
uso, para que la distincion quede a la vista y no escondida.

Sellos nuevos: solo CANONICA. Un archivo nuevo que solo verifique como LEGADO es
un error de harness, no una variante aceptable.

Uso:  python3 verify_seals.py 'runs/**/*.json' 'prereg/**/*.json'
Salida: una linea por archivo + resumen. Exit code 1 si algo no verifica con ninguna.
"""
import sys, json, hashlib, glob

def canonical_hash(d):
    meta = {k: v for k, v in d["meta"].items() if k != "content_hash"}
    body = {k: v for k, v in d.items() if k not in ("meta", "storage")}
    payload = json.dumps({"meta": meta, **body}, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()

def legacy_hash(d):
    if "w6" not in d:
        return None
    # la legada NO quita content_hash: lo pone en null dentro de meta
    meta = {**d["meta"], "content_hash": None}
    payload = json.dumps({"meta": meta, "w6": d["w6"]},
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()

def main(argv):
    paths = []
    for a in argv or ["runs/**/*.json", "prereg/**/*.json"]:
        paths.extend(sorted(glob.glob(a, recursive=True)))
    ok = legacy = bad = 0
    for p in paths:
        d = json.load(open(p))
        stored = d["meta"].get("content_hash")
        got = canonical_hash(d)
        if stored == got:
            ok += 1
            print(f"VALID          {d['meta'].get('file_id','?'):<16} {got}")
            continue
        leg = legacy_hash(d)
        # el legado se guardo sin prefijo "sha256:" en las primeras series
        if leg and stored in (leg, "sha256:" + leg):
            legacy += 1
            print(f"VALID(legado)  {d['meta'].get('file_id','?'):<16} sha256:{leg}")
            continue
        bad += 1
        print(f"INVALID        {d['meta'].get('file_id','?'):<16} {got}")
        print(f"               almacenado: {stored}")
    print(f"\n{ok} VALID(canonico) / {legacy} VALID(legado, ya anclados) / {bad} INVALID / {ok+legacy+bad} archivos")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
