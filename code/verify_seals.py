"""
RosettaQ — verificador canonico de sellos (esquema rosettaq-archive/v1).

Convencion UNICA y oficial:
    content_hash = sha256( json.dumps({"meta": meta_sin_content_hash, <cuerpo>},
                                      sort_keys=True, ensure_ascii=False) )
donde <cuerpo> son todas las claves de nivel superior del archivo EXCEPTO
"meta" y "storage" (para un RUN eso es "w6"; para un PREREG, su bloque propio).
"storage" queda fuera a proposito: describe donde vive la copia, no que dice.

Uso:  python3 verify_seals.py runs/*.json prereg/*.json
Salida: una linea por archivo + resumen. Exit code 1 si algo no verifica.
"""
import sys, json, hashlib, glob

def canonical_hash(d):
    meta = {k: v for k, v in d["meta"].items() if k != "content_hash"}
    body = {k: v for k, v in d.items() if k not in ("meta", "storage")}
    payload = json.dumps({"meta": meta, **body}, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()

def main(argv):
    paths = []
    for a in argv or ["runs/*.json", "prereg/*.json"]:
        paths.extend(sorted(glob.glob(a)))
    ok = bad = 0
    for p in paths:
        d = json.load(open(p))
        stored = d["meta"].get("content_hash")
        got = canonical_hash(d)
        good = (stored == got)
        ok, bad = (ok + 1, bad) if good else (ok, bad + 1)
        print(f"{'VALID  ' if good else 'INVALID'} {d['meta'].get('file_id','?'):<16} {got}")
        if not good:
            print(f"          almacenado: {stored}")
    print(f"\n{ok} VALID / {bad} INVALID / {ok+bad} archivos")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
