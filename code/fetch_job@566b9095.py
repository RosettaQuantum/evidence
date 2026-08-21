#!/usr/bin/env python3
"""Recoge el resultado de un trabajo de IBM Quantum que ya fue enviado.

POR QUE EXISTE
--------------
La primera corrida se hizo con el patron ingenuo: un solo proceso que envia el trabajo
y se queda bloqueado esperando el resultado. En la cola del plan abierto ese proceso
espero 4 h 30 min sin que el trabajo llegara siquiera a ejecutarse, y GitHub Actions mata
cualquier job a las 6 h. O sea: el runner habria muerto sin resultado, despues de quemar
~360 minutos de cuota, mientras el trabajo cuantico seguia intacto en el servidor de IBM.

La clave es esa ultima parte: **el trabajo vive en IBM, no en el runner.** Se envia, se
suelta, y se recoge despues por su ID. La espera deja de costar nada.

Este script es solo la mitad de "recoger". La mitad de "enviar" vive en el harness del
laboratorio, que debe imprimir el job_id y salir en vez de esperar.

USO
---
    export IBM_TOKEN='...'; export IBM_CRN='...'
    python3 fetch_job.py                 # el trabajo mas reciente
    python3 fetch_job.py <job_id>        # uno especifico
    python3 fetch_job.py --list          # que hay y en que estado

Escribe `poc_job_<id>.json` con el resultado crudo y la metadata de procedencia. No
interpreta la ciencia: eso es del laboratorio, que sella.
"""
import json, os, sys, datetime

try:
    from qiskit_ibm_runtime import QiskitRuntimeService
except ImportError:
    sys.exit("falta qiskit-ibm-runtime: pip install qiskit-ibm-runtime")


def servicio():
    tok = os.environ.get("IBM_TOKEN")
    if not tok:
        # Igual que en el workflow: mejor caerse fuerte que operar sin credencial y
        # devolver algo que parezca un resultado sin serlo.
        sys.exit("IBM_TOKEN vacio o ausente — abortando en vez de fingir una corrida")
    kw = {"channel": "ibm_quantum_platform", "token": tok}
    if os.environ.get("IBM_CRN"):
        kw["instance"] = os.environ["IBM_CRN"]
    return QiskitRuntimeService(**kw)


svc = servicio()

if "--list" in sys.argv:
    print(f"{'job_id':<26} {'estado':<12} {'backend':<16} creado")
    for j in svc.jobs(limit=10):
        try:
            creado = j.creation_date.strftime("%Y-%m-%d %H:%M")
        except Exception:
            creado = "?"
        print(f"{j.job_id():<26} {str(j.status()):<12} {str(j.backend().name):<16} {creado}")
    sys.exit(0)

def extraer(v):
    """Saca los datos de un campo del PubResult.

    La primera version hacia `v.tolist() if hasattr(v,'tolist') else str(v)`. Un
    BitArray de SamplerV2 no tiene `.tolist()`, asi que caia al `str(v)` — que existia
    para "no descartar nada en silencio" y termino guardando exactamente eso: la cadena
    `BitArray(<shape=(), num_shots=2000, num_bits=12>)`, la DESCRIPCION del objeto sin
    una sola medicion adentro. El archivo pesaba, tenia forma de resultado, y estaba
    vacio. Por eso ahora cada tipo se extrae explicitamente y lo que no se reconoce se
    marca NO_EXTRAIDO para que el chequeo de abajo lo vea y falle fuerte.
    """
    if hasattr(v, "get_counts"):                       # BitArray (SamplerV2)
        cuentas = {str(k): int(n) for k, n in v.get_counts().items()}
        return {"tipo": "BitArray",
                "num_shots": int(getattr(v, "num_shots", 0)),
                "num_bits": int(getattr(v, "num_bits", 0)),
                "counts": cuentas}
    if hasattr(v, "tolist"):                           # ndarray (EstimatorV2)
        return {"tipo": "array", "valores": v.tolist()}
    return {"NO_EXTRAIDO": str(v)}


def recoger(job):
    """Escribe poc_job_<id>.json. Devuelve (ok, mensaje). No sale del proceso."""
    estado = str(job.status())
    if estado not in ("DONE", "JobStatus.DONE"):
        return None, f"{job.job_id()}  {estado} — aun no termina"

    res = job.result()
    salida = {
        "job_id": job.job_id(),
        "backend": str(job.backend().name),
        "estado": estado,
        "recogido_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "metrics": getattr(job, "metrics", lambda: {})(),
        "resultado_crudo": None,
    }
    try:
        salida["resultado_crudo"] = [
            {"data": {k: extraer(v)
                      for k, v in (r.data.__dict__ if hasattr(r, "data") else {}).items()},
             "metadata": getattr(r, "metadata", {})}
            for r in res
        ]
    except Exception as e:
        salida["resultado_crudo"] = {"no_serializable": repr(res)[:4000], "error": str(e)}

    # ---- comprobar que lo escrito TIENE mediciones --------------------------------
    # No basta con que el archivo se escriba: un JSON de 600 bytes sin cuentas adentro
    # pasa por resultado en todos los pasos siguientes y solo se descubre cuando alguien
    # intenta analizarlo. Se verifica aqui y se falla en vez de publicar algo hueco.
    campos, shots, faltantes = 0, 0, []
    for pub in (salida["resultado_crudo"] if isinstance(salida["resultado_crudo"], list) else []):
        for nombre_campo, d in pub.get("data", {}).items():
            campos += 1
            if not isinstance(d, dict) or "NO_EXTRAIDO" in d:
                faltantes.append(nombre_campo); continue
            if d.get("tipo") == "BitArray":
                n = sum(d["counts"].values())
                shots += n
                # Las cuentas deben sumar exactamente los shots declarados; si no, se
                # perdio parte de la medicion en el camino.
                if n != d["num_shots"]:
                    faltantes.append(f"{nombre_campo} (suman {n}, declara {d['num_shots']})")

    nombre = f"poc_job_{job.job_id()}.json"
    with open(nombre, "w") as f:
        json.dump(salida, f, indent=2, default=str)

    if faltantes or campos == 0:
        detalle = ", ".join(faltantes) or "el PubResult no trajo ningun campo de datos"
        return False, (f"{job.job_id()}  RECOGIDO SIN MEDICIONES: {detalle}\n"
                       "  no se declara recogido — arregla la extraccion antes de sellar")
    return True, (f"{job.job_id()}  {job.backend().name}  ->  {nombre} "
                  f"({os.path.getsize(nombre)} bytes, {shots} mediciones)")


# ---- que recoger -----------------------------------------------------------------
# Sin argumentos se recogia SOLO el trabajo mas reciente. En un cron eso es una trampa:
# con una bateria de tres circuitos enviados juntos, cada corrida recoge el mismo y los
# otros dos no se recogen nunca — y el workflow queda verde igual. `--todos` recorre los
# trabajos recientes y recoge todos los que terminaron, saltando los que ya estan en
# disco. Es lo correcto para desatendido; el modo de un solo id se conserva para manual.
pedido = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
if pedido:
    trabajos = [svc.job(pedido)]
elif "--todos" in sys.argv:
    trabajos = list(svc.jobs(limit=20))
else:
    trabajos = [j for j in [next(iter(svc.jobs(limit=1)), None)] if j]

if not trabajos:
    sys.exit("no hay trabajos en esta cuenta")

recogidos, pendientes, rotos = [], [], []
for j in trabajos:
    if "--todos" in sys.argv and os.path.exists(f"poc_job_{j.job_id()}.json"):
        continue                                  # ya recogido en una corrida anterior
    ok, msg = recoger(j)
    print(("  " if len(trabajos) > 1 else "") + msg)
    (recogidos if ok else pendientes if ok is None else rotos).append(j.job_id())

print(f"\nrecogidos {len(recogidos)} · pendientes {len(pendientes)} · sin mediciones {len(rotos)}")

# Un artefacto hueco es peor que ninguno: se falla fuerte aunque otros hayan salido bien.
if rotos:
    sys.exit(3)
# 2 = "todavia no", distinto de fallo. Solo si NADA se pudo recoger.
if not recogidos:
    print("ningun trabajo termino todavia — los trabajos siguen vivos en IBM.")
    sys.exit(2)

print("siguiente paso: el laboratorio lo sella; el notario lo ancla y publica.")
