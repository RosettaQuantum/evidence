"""
RosettaQ — verificador de sellos del archivo.

Hay CUATRO convenciones en circulacion. No es desorden escondido: es historia
declarada. Un archivo se verifica contra la convencion con la que fue sellado,
y el verificador dice cual uso, en vez de disimular la diferencia.

  v3  (RFC 8785 / JCS — la unica que se puede recomputar fuera de Python)
      sha256(JCS({"meta": meta sin {content_hash, schema},
                  <cuerpo sin storage>}))
      MISMO payload que v2; cambia solo la serializacion. Existe porque v2 se
      calculaba sobre `json.dumps` de Python, que escribe un float `6.0` donde
      JavaScript, Go y Rust escriben `6`: 64 de 69 archivos sellados tenian al
      menos un literal asi, y un verificador en otro lenguaje fallaba en
      silencio, con la misma cara que tendria una manipulacion.
      OJO: v3 le cambia el hash a TODOS los archivos, no solo a los que traen
      esos flotantes — v2 usa los separadores por defecto de json.dumps (`, ` y
      `: `) y JCS es compacto. Por eso v3 va solo hacia adelante.

  v2  (la que llevan los sellos ya anclados; sigue siendo valida para ellos)
      sha256(json.dumps({"meta": meta sin {content_hash, schema},
                         <cuerpo sin storage>},
                        sort_keys=True, ensure_ascii=False))
      Diferencia con la canonica v1: `schema` queda FUERA del payload, para que
      el puntero de convencion se pueda corregir sin romper el ancla. Ver
      harness/rosettaq_seal.py.

  v1-canonica  (historica; 13 archivos de la serie Cleveland)
      igual que v2 pero `schema` SI entra al payload.

  v1-legada    (historica; 30 archivos de portafolio y red, YA ANCLADOS)
      sha256(json.dumps({"meta": {**meta, "content_hash": None}, "w6": w6},
                        sort_keys=True, separators=(",",":")))   # ensure_ascii por defecto
      Tres diferencias: content_hash se anula en vez de quitarse, separadores
      compactos, y ensure_ascii=True.

POR QUE NO SE RE-SELLA LO VIEJO
-------------------------------
Los 43 archivos publicados estan anclados en OpenTimestamps. Sus hashes son
hechos publicos inmutables que terceros ya pueden citar: re-sellarlos invalidaria
anclas reales. Y reetiquetarlos tampoco sirve —en v1 el campo `schema` esta
dentro del payload, asi que cambiarle la etiqueta a un archivo le cambia el hash.
La ambiguedad se resuelve hacia adelante (v2) mas `manifests/seal-manifest.json`,
publicado y sellado, que declara la convencion de cada archivo.

Sellos nuevos: solo v2. Un archivo nuevo que verifique como v1 (cualquiera de las
dos) es un error de harness, no una variante aceptable.

Uso:  python3 tools/verify_seals.py 'runs/**/*.json' 'prereg/**/*.json' 'manifests/*.json'
Exit code 1 si algo no verifica con ninguna convencion.
"""
import sys, json, hashlib, glob, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "harness"))
import jcs                                    # RFC 8785, stdlib puro

V3 = "v3"
V2 = "v2"
V1C = "v1-canonica"
V1L = "v1-legada"


def _payload(d):
    meta = {k: v for k, v in d["meta"].items() if k not in ("content_hash", "schema")}
    body = {k: v for k, v in d.items() if k not in ("meta", "storage")}
    return {"meta": meta, **body}


def _v3_hash(d):
    """v3: MISMO payload que v2, serializado con JCS (RFC 8785).

    Le cambia el hash a todos los archivos, no solo a los que traen flotantes de valor
    entero: v2 usa los separadores por defecto de json.dumps (`, ` y `: `) y JCS es
    compacto. Por eso v3 va solo hacia adelante.
    """
    try:
        texto = jcs.canonico(_payload(d))
    except jcs.NoCanonizable:
        return None                            # un documento que JCS no puede escribir
    return "sha256:" + hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _v2_hash(d):
    meta = {k: v for k, v in d["meta"].items() if k not in ("content_hash", "schema")}
    body = {k: v for k, v in d.items() if k not in ("meta", "storage")}
    return "sha256:" + hashlib.sha256(
        json.dumps({"meta": meta, **body}, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def _v1_canonical_hash(d):
    meta = {k: v for k, v in d["meta"].items() if k != "content_hash"}
    body = {k: v for k, v in d.items() if k not in ("meta", "storage")}
    return "sha256:" + hashlib.sha256(
        json.dumps({"meta": meta, **body}, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def _v1_legacy_hash(d):
    if "w6" not in d:
        return None
    meta = {**d["meta"], "content_hash": None}
    return hashlib.sha256(
        json.dumps({"meta": meta, "w6": d["w6"]},
                   sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def identify(d):
    """Devuelve (convencion, hash_reproducido) o (None, hash_v2_esperado).

    Se prueban TODAS y se declara cual reprodujo: la convencion es auto-evidente porque
    solo una da el hash almacenado, y la etiqueta es una pista para el lector, no la
    prueba. Es lo mismo que ya valia para v1 y v2, ahora con v3 adentro.
    """
    stored = d["meta"].get("content_hash")
    h = _v2_hash(d)
    if stored == h:
        return V2, h
    h3 = _v3_hash(d)
    if h3 and stored == h3:
        return V3, h3
    h1 = _v1_canonical_hash(d)
    if stored == h1:
        return V1C, h1
    hl = _v1_legacy_hash(d)
    if hl and stored in (hl, "sha256:" + hl):
        return V1L, "sha256:" + hl
    return None, h


LABEL = {V3: "VALID(v3)     ", V2: "VALID(v2)     ",
         V1C: "VALID(v1-canon)", V1L: "VALID(v1-legado)"}


def main(argv):
    paths = []
    # La lista por omision estaba escrita aqui a mano y cubria 63 de 69 archivos: se
    # olvidaba de recipes/, verdicts/ y predictions/, y reportaba el total como si
    # fueran todos. En el VERIFICADOR DE REFERENCIA eso es lo peor posible — es el
    # programa cuyo unico trabajo es decir que todo verifica. Ahora la lista sale del
    # mismo modulo que usan el notario y el sync; agregar una carpeta al archivo la
    # mete sola en los tres.
    if not argv:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "scripts"))
        from notarize_globs import ARCHIVE_GLOBS
        argv = list(ARCHIVE_GLOBS)
    for a in argv:
        paths.extend(sorted(glob.glob(a, recursive=True)))
    counts = {V3: 0, V2: 0, V1C: 0, V1L: 0}
    bad = 0
    mislabeled = []
    for p in paths:
        d = json.load(open(p))
        conv, h = identify(d)
        fid = d["meta"].get("file_id", "?")
        if conv is None:
            bad += 1
            print(f"INVALID          {fid:<16} {h}")
            print(f"                 almacenado: {d['meta'].get('content_hash')}")
            continue
        counts[conv] += 1
        print(f"{LABEL[conv]} {fid:<16} {h}")
        declared = d["meta"].get("schema", "")
        expected = {V3: "rosettaq-archive/v3", V2: "rosettaq-archive/v2"}.get(
            conv, "rosettaq-archive/v1")
        if declared != expected:
            mislabeled.append((fid, declared, conv))

    print(f"\n{counts[V3]} v3 / {counts[V2]} v2 / {counts[V1C]} v1-canonica / "
          f"{counts[V1L]} v1-legada (ancladas) / {bad} INVALID / {len(paths)} archivos")
    for fid, declared, conv in mislabeled:
        print(f"AVISO etiqueta: {fid} declara `{declared}` pero verifica como {conv}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
