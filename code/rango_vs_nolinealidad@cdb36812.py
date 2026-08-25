#!/usr/bin/env python3
"""¿Es el benchmark del enunciado trivial para una red tensorial POR LA MISMA RAZON por
la que no puede exhibir la no-linealidad?

LA HIPOTESIS QUE SE PONE A PRUEBA
---------------------------------
El campo del vortice vive en UNA sola capa de autovalores del laplaciano discreto — eso
ya esta medido y sellado (RQ-EXP-AIRBUS-NOLIN-001): es lo que anula el termino no lineal.
La hipotesis de la sesion de coordinacion es que «una capa» implica ademas RANGO BAJO, y
por tanto que el mismo caso es trivial de comprimir.

LO QUE SE OBJETO ANTES DE MEDIR, y por eso hay un control
---------------------------------------------------------
«Una capa» y «rango bajo» NO son la misma propiedad, y la implicacion falla en una
direccion. De capa a rango se sostiene con matiz: una capa es un autovalor DEGENERADO, y
un campo con multiplicidad m tiene rango <= m — es un techo, no «rango 1». De rango a capa
NO se sostiene: cualquier producto f(x)·g(y) es rango 1 exacto y, si f y g no son modos de
Fourier puros, se reparte por muchisimas capas. Ese es el CONTROL de abajo, y se publica
salga como salga.

DOS DECISIONES DECLARADAS ANTES DE VER NINGUN RESULTADO
-------------------------------------------------------
1. METRICA: espectro de valores singulares de w[x,y]; chi(tol) = minimo k con error
   relativo de Frobenius <= tol. Se publica el ESPECTRO COMPLETO, asi que cualquiera
   recomputa chi a la tolerancia que quiera y no dependemos de la que elegimos. Al lado va
   la entropia de entrelazamiento — la metrica estandar de «cuan dificil para una red
   tensorial»— para no reportar solo la que nos conviene.
2. BIPARTICION: el corte x|y, y se declara por que: es el corte natural del problema y el
   que corresponde a la estructura de modos producto que el enunciado usa. NO se exploran
   varios cortes: reportar el mas favorable seria elegir la metrica despues de ver el
   resultado.

Simulacion local. Ningun backend. Costo US$0.
"""
import hashlib, json, os, sys, numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import airbus_harness as ah
import nolinealidad_donde_vive as nl
import _procedencia as _proc

TOL_CHI = 1e-6          # tolerancia declarada para chi; el espectro completo va publicado
N = nl.N_TABLA
RE = nl.RE_TABLA


def espectro(w):
    """Valores singulares de w[x,y], normalizados a norma 1. Corte x|y, declarado."""
    s = np.linalg.svd(np.asarray(w, float), compute_uv=False)
    n = float(np.linalg.norm(s))
    return s / n if n > 0 else s


def chi(s, tol=TOL_CHI):
    """Minimo k tal que ||w - w_k||_F / ||w||_F <= tol (con s ya normalizado)."""
    cola = np.sqrt(np.cumsum((s[::-1]) ** 2))[::-1]      # error al truncar en k
    for k in range(1, len(s) + 1):
        if (cola[k] if k < len(s) else 0.0) <= tol:
            return k
    return len(s)


def entropia(s):
    """Entropia de entrelazamiento del campo normalizado a traves del corte x|y."""
    p = s ** 2
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def mide(nombre, campo, descripcion):
    r = nl.razon(nombre, campo, N, RE)
    w = np.asarray(campo(N), dtype=float)
    s = espectro(w)
    return {"variante": nombre, "descripcion": descripcion,
            "razon_no_linealidad": r["razon"],
            "capas_autovalor": r["capas_autovalor"],
            "modos_presentes": r["modos_presentes"],
            "rango_numerico_chi": chi(s),
            "entropia_entrelazamiento_bits": round(entropia(s), 6),
            "valores_singulares": [round(float(x), 12) for x in s if x > 1e-15]}


# ------------------------------------------------------- las 18 variantes selladas
filas = [mide(nom, f, d) for nom, f, d in nl.VARIANTES]

# ------------------------------------------------------- EL CONTROL QUE ROMPE LA IDENTIDAD
# Producto de dos von Mises: exactamente periodico, RANGO 1 EXACTO por construccion, y
# NO es un modo de Fourier puro — asi que se reparte por muchas capas. Si su razon no es
# cero, «rango bajo» y «una capa» dejan de ser la misma propiedad. Se publica salga como
# salga: se construyo para intentar refutar la hipotesis, no para confirmarla.
def f_producto_von_mises(kappa=6.0, x0=1.0, y0=2.0):
    def f(n, p=ah.PARAMS_STATEMENT):
        X, Y, _h, _ = ah._malla(n, p)
        L = p["L"] if isinstance(p, dict) and "L" in p else 1.0
        fx = np.exp(kappa * np.cos(X / L - x0))
        fy = np.exp(kappa * np.cos(Y / L - y0))
        w = fx * fy
        return w - w.mean()          # media cero, como los demas campos
    return f

controles = [mide("control_producto_von_mises_k6", f_producto_von_mises(6.0),
                  "producto f(x)*g(y) de von Mises: RANGO 1 exacto y periodico, pero NO "
                  "es un modo de Fourier puro. Construido para refutar la identificacion "
                  "entre «rango bajo» y «una sola capa»."),
             mide("control_producto_von_mises_k12", f_producto_von_mises(12.0),
                  "el mismo, mas estrecho: mas modos de Fourier, mismo rango 1.")]

# ------------------------------------------------------- ¿suben juntas las dos curvas?
import math
prueba = [f for f in filas if f["razon_no_linealidad"] is not None]
xs = [math.log10(max(f["razon_no_linealidad"], 1e-18)) for f in prueba]
ys = [f["rango_numerico_chi"] for f in prueba]
def spearman(a, b):
    """Spearman CON empates. La primera version usaba argsort(argsort(...)), que asigna
    rangos secuenciales a valores iguales segun el orden en que aparecen — y con chi
    constante en 2 a lo largo de una serie entera devolvia **+1,000**: correlacion
    perfecta donde no hay ninguna variacion. Un numero citable y falso, producido por mi
    propio instrumento. Se usa scipy, que promedia los empates, y si la desviacion de
    cualquiera de las dos series es cero se devuelve None en vez de un numero inventado.
    """
    from scipy.stats import spearmanr
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.std() == 0 or b.std() == 0:
        return None
    r = spearmanr(a, b)
    return float(r.statistic)
rho_chi = spearman(xs, ys)
rho_ent = spearman(xs, [f["entropia_entrelazamiento_bits"] for f in prueba])

# ------------------------------------------------------- veredicto, DERIVADO
una_capa = [f for f in prueba if f["capas_autovalor"] == 1]
varias = [f for f in prueba if f["capas_autovalor"] > 1]
rompe = [c for c in controles
         if c["rango_numerico_chi"] <= 2 and c["capas_autovalor"] > 1
         and c["razon_no_linealidad"] and c["razon_no_linealidad"] > 1e-12]

out = {
    "file_id": "RQ-MEAS-AIRBUS-RANGO-001",
    "pregunta": "¿el rango necesario para representar el campo sube junto con su "
                "no-linealidad, en la familia del enunciado? ¿y son «rango bajo» y «una "
                "sola capa» la misma propiedad?",
    "decisiones_declaradas_antes_de_medir": {
        "metrica": "valores singulares de w[x,y]; chi(tol)=minimo k con error relativo de "
                   "Frobenius <= %g. Se publica el espectro completo para que cualquiera "
                   "recompute chi a otra tolerancia." % TOL_CHI,
        "biparticion": "corte x|y, por ser el corte natural del problema y el que "
                       "corresponde a la estructura de modos producto del enunciado. NO "
                       "se exploraron varios cortes: reportar el mas favorable seria "
                       "elegir la metrica despues de ver el resultado.",
        "metrica_de_contraste": "entropia de entrelazamiento, la estandar para «cuan "
                                "dificil para una red tensorial», reportada al lado de "
                                "chi para no publicar solo la que nos conviene.",
    },
    "malla_N": N, "Re": RE, "tolerancia_chi": TOL_CHI,
    "familia_del_enunciado": filas,
    "control_que_intenta_refutar": controles,
    "correlacion": {
        "spearman_log10_razon_vs_chi": (round(rho_chi, 4) if rho_chi is not None else None),
        "spearman_log10_razon_vs_entropia": (round(rho_ent, 4) if rho_ent is not None else None),
        "n": len(prueba)},
    "resumen_por_capas": {
        "una_capa": {"n": len(una_capa),
                     "chi": sorted({f["rango_numerico_chi"] for f in una_capa}),
                     "razon_max": max((f["razon_no_linealidad"] for f in una_capa), default=None)},
        "varias_capas": {"n": len(varias),
                         "chi": sorted({f["rango_numerico_chi"] for f in varias}),
                         "razon_min": min((f["razon_no_linealidad"] for f in varias), default=None)}},
    "LA_IDENTIFICACION_SE_ROMPE": bool(rompe),
    "como_se_rompe": ("existe al menos un campo de rango <= 2 que vive en varias capas y "
                      "cuya no-linealidad NO es cero: %s. Por lo tanto «rango bajo» y «una "
                      "sola capa» NO son la misma propiedad, y la afirmacion que se "
                      "sostiene es la mas debil: en LA FAMILIA DEL ENUNCIADO las dos "
                      "coinciden porque esta construida a partir de un solo modo producto."
                      % ", ".join(c["variante"] for c in rompe)) if rompe else
                     ("ningun control de rango bajo con varias capas dio no-linealidad "
                      "distinta de cero: la objecion no se pudo demostrar con estos "
                      "controles, y eso se dice asi en vez de concluir lo contrario."),
    "producido_por_sha256": _proc.procedencia(__file__),
    "entorno": {"numpy": np.__version__, "python": sys.version.split()[0]},
}
_ch, _fuera = _proc.contenido(out)
out["contenido_sha256"] = _ch
out["campos_no_reproducibles"] = {"excluidos": _fuera, "por_que": "dependen de la maquina"}
dst = os.path.join(os.environ.get("RQ_OUT_DIR", AQUI), "rango_vs_nolinealidad.json")
json.dump(out, open(dst, "w"), indent=1, ensure_ascii=False)

print("%-34s %-6s %-6s %-8s %s" % ("variante", "capas", "chi", "entropia", "razon"))
for f in filas + controles:
    print("%-34s %-6d %-6d %-8.4f %.3e"
          % (f["variante"][:33], f["capas_autovalor"], f["rango_numerico_chi"],
             f["entropia_entrelazamiento_bits"],
             f["razon_no_linealidad"] if f["razon_no_linealidad"] is not None else float("nan")))
print("\nSpearman log10(razon) vs chi      : %s  (n=%d)" % (("%+.3f"%rho_chi) if rho_chi is not None else "sin variacion", len(prueba)))
print("Spearman log10(razon) vs entropia : %s" % (("%+.3f"%rho_ent) if rho_ent is not None else "sin variacion"))
print("\nLA IDENTIFICACION SE ROMPE:", out["LA_IDENTIFICACION_SE_ROMPE"])
print(" ", out["como_se_rompe"][:200])
