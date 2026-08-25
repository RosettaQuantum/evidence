#!/usr/bin/env python3
"""¿Cuanto puede DETECTAR el benchmark del enunciado? Medido, no opinado.

LA PREGUNTA
-----------
Un caso de prueba sirve si distingue un solver correcto de uno equivocado. La pregunta
concreta: **un solver que omita por completo el termino no lineal, ¿da una respuesta
distinta sobre este caso?** Si no la da, el caso no puede detectar el error que existe
para detectar.

COMO SE MIDE, Y POR QUE ASI
---------------------------
Solucion manufacturada (MMS), la tecnica estandar de VERIFICACION DE CODIGO en CFD: se
elige el campo objetivo w*, se calcula el forzamiento f = -(A1 w* + A2(w* (x) w*)) y con
eso w* es solucion estacionaria EXACTA del sistema completo, por construccion — con la
no-linealidad genuinamente activa, no anulada.

Un solver que OMITA el termino cuadratico ya no tiene w* como solucion. Su estacionario
satisface A1 w = A1 w* + A2(w* (x) w*), asi que se corre en

    e = A1^-1 A2(w* (x) w*)

y ||e||/||w*|| es la CAPACIDAD DE DETECCION del caso: cuanto se equivoca, en unidades del
campo, quien ignora la fisica que el desafio dice querer probar.

EL PRECIO, DECLARADO Y NO EN UN ANEXO
-------------------------------------
MMS anade un TERMINO FUENTE. No es decaimiento libre: es verificacion de codigo, no
validacion fisica. Y mide OTRO EJE que el del enunciado — precision con la no-linealidad
activa, no tiempo-a-solucion contra Reynolds. No reemplaza aquel eje: lo complementa en la
dimension que su caso no puede tocar.

SALVEDAD MENOR: A1 es singular en el modo constante (es un laplaciano periodico), asi que
e se resuelve por minimos cuadrados. Se declara aunque no cambie ninguna conclusion.

Simulacion local. Costo US$0.
"""
import hashlib, json, os, sys, numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
import nolinealidad_donde_vive as nl, airbus_carleman as ac, airbus_harness as ah
import _procedencia as _proc

N, RE = nl.N_TABLA, nl.RE_TABLA
TOL_CIEGO = 1e-9          # umbral declarado para llamar «ciego» a un caso
A1, A2, m = ac.matrices_fd(N, RE)
A1d = A1.toarray() if hasattr(A1, "toarray") else np.asarray(A1)

def deteccion(campo):
    w = np.asarray(campo(N), float)
    w = w * (float(np.linalg.norm(nl.f_tgv_statement(N))) / float(np.linalg.norm(w)))
    wv = w.ravel()
    q = A2 @ np.kron(wv, wv)
    e, *_ = np.linalg.lstsq(A1d, q, rcond=None)
    _, capas = nl.capas_laplaciano(w, N)
    return {"capas_autovalor": capas,
            "norma_termino_no_lineal": float(np.linalg.norm(q)),
            "error_del_solver_sin_no_linealidad": float(np.linalg.norm(e)) / float(np.linalg.norm(wv)),
            "norma_w": float(np.linalg.norm(wv))}

filas = []
for nom, f, desc in nl.VARIANTES:
    d = deteccion(f)
    d.update(variante=nom, descripcion=desc,
             detecta=bool(d["error_del_solver_sin_no_linealidad"] > TOL_CIEGO))
    filas.append(d)

# LA CLASE DEGENERADA NO ES «EL VORTICE»: es la vorticidad confinada a UNA capa.
# Ejemplo con RANGO 2 para que no se lea como «es que era rango 1».
X, Y, _h, _ = ah._malla(N, ah.PARAMS_STATEMENT); L = ah.PARAMS_STATEMENT["L"]
def f_dos_modos_misma_capa(n, _X=X, _Y=Y, _L=L):
    return np.sin(_X/_L)*np.sin(2*_Y/_L) + np.sin(2*_X/_L)*np.sin(_Y/_L)
d = deteccion(f_dos_modos_misma_capa)
d.update(variante="dos_modos_de_la_MISMA_capa",
         descripcion="sin(x)sin(2y) + sin(2x)sin(y): una sola capa, RANGO 2. Muestra que "
                     "la clase degenerada no es «el vortice» ni «rango 1», sino la "
                     "vorticidad confinada a una sola capa de autovalores.",
         detecta=bool(d["error_del_solver_sin_no_linealidad"] > TOL_CIEGO))
caracterizacion = d

ciegos = [f for f in filas if not f["detecta"]]
tgv = [f for f in filas if f["variante"] == "tgv_statement"][0]

# ------------------------------------------------------------------ GUARDIA
# Si el caso del enunciado dejara de ser ciego, la tesis entera del entregable se cae y
# no se publica una tabla que diga lo contrario de lo que mide.
if tgv["detecta"]:
    raise SystemExit("ABORTA: el TGV del enunciado detecta un solver sin no-linealidad "
                     "(error %.2e). La tesis del entregable no se sostiene."
                     % tgv["error_del_solver_sin_no_linealidad"])
if not all(f["capas_autovalor"] == 1 for f in ciegos):
    raise SystemExit("ABORTA: hay casos ciegos que NO son de una sola capa — la "
                     "caracterizacion que se publica seria falsa")
if caracterizacion["detecta"]:
    raise SystemExit("ABORTA: el ejemplo de dos modos en la misma capa SI detecta; la "
                     "caracterizacion por capas no se sostiene")

detectables = [f for f in filas if f["detecta"]]
out = {
    "file_id": "RQ-MEAS-AIRBUS-DETECCION-001",
    "pregunta": "un solver que omita por completo el termino no lineal, ¿da una respuesta "
                "distinta sobre el caso del enunciado?",
    "metodo": "solucion manufacturada (MMS): f = -(A1 w* + A2(w*(x)w*)) hace de w* una "
              "solucion estacionaria exacta del sistema completo. El error de un solver "
              "que omite el termino cuadratico es e = A1^-1 A2(w*(x)w*).",
    "el_precio_declarado": {
        "anade_termino_fuente": True,
        "que_es": "verificacion de codigo, no validacion fisica. No es decaimiento libre.",
        "que_eje_mide": "precision con la no-linealidad activa. NO mide tiempo-a-solucion "
                        "contra Reynolds, que es el eje del enunciado y que ya entregamos "
                        "aparte sobre el decaimiento libre con su formula cerrada. No lo "
                        "reemplaza: lo complementa en la dimension que su caso no toca.",
        "salvedad_numerica": "A1 es singular en el modo constante (laplaciano periodico); "
                             "e se resuelve por minimos cuadrados. No cambia ninguna "
                             "conclusion y se declara igual.",
        "umbral_declarado_para_ciego": TOL_CIEGO,
    },
    "RESULTADO": ("sobre el vortice del enunciado, un solver que ignora POR COMPLETO el "
                  "termino no lineal se equivoca en %.2e — cero de maquina. El caso no "
                  "puede distinguirlo de un solver correcto. Sobre la familia reparada el "
                  "mismo solver se equivoca entre %.2e y %.2e: el umbral es graduable en "
                  "%.1f ordenes de magnitud."
                  % (tgv["error_del_solver_sin_no_linealidad"],
                     min(f["error_del_solver_sin_no_linealidad"] for f in detectables),
                     max(f["error_del_solver_sin_no_linealidad"] for f in detectables),
                     np.log10(max(f["error_del_solver_sin_no_linealidad"] for f in detectables) /
                              min(f["error_del_solver_sin_no_linealidad"] for f in detectables)))),
    "malla_N": N, "Re": RE,
    "tabla": filas,
    "caracterizacion_de_la_clase_degenerada": caracterizacion,
    "resumen": {"ciegas": len(ciegos), "total": len(filas),
                "cuales": [f["variante"] for f in ciegos],
                "todas_de_una_capa": True},
    "producido_por_sha256": _proc.procedencia(__file__),
    "entorno": {"numpy": np.__version__, "python": sys.version.split()[0]},
}
_ch, _fuera = _proc.contenido(out)
out["contenido_sha256"] = _ch
out["campos_no_reproducibles"] = {"excluidos": _fuera, "por_que": "dependen de la maquina"}
dst = os.path.join(os.environ.get("RQ_OUT_DIR", AQUI), "umbral_de_deteccion.json")
json.dump(out, open(dst, "w"), indent=1, ensure_ascii=False)
print(out["RESULTADO"])
print("\nciegas: %d de %d — %s" % (len(ciegos), len(filas), ", ".join(f["variante"] for f in ciegos)))
print("todas de una sola capa:", out["resumen"]["todas_de_una_capa"])
print("y el ejemplo de RANGO 2 en una capa tambien es ciego: %.2e"
      % caracterizacion["error_del_solver_sin_no_linealidad"])
print("sha256:", hashlib.sha256(open(dst, "rb").read()).hexdigest()[:16])
