"""Las tres fuentes externas del track HSBC. UN solo lugar para los dos generadores.

Vivian duplicadas en el generador español y en el ingles. Una lista que vive en dos lugares
ya divergio — es la misma razon por la que el harness tiene un adaptador de dataset en vez
de un segundo harness. Aqui la «lista» seria una cita, y una cita que difiere entre dos
idiomas del mismo entregable es un defecto que nadie ve hasta que un lector compara.
"""
# LAS TRES FUENTES EXTERNAS. Cada una se abrio en arxiv.org y se confirmo frase por frase
# antes de escribirla aqui: ninguna entro por relevo. Se citan en INGLES porque son
# textuales — traducir y entrecomillar seria alterarlas; la traduccion va marcada aparte.
FUENTES = [
 {"id": "arXiv:2608.15718", "fecha": "16 de agosto de 2026", "autor": "M. Faryad",
  "tit": "Quantum Kernel k-Means for Credit-Card Fraud Detection: A Controlled Benchmark "
         "on Real Transaction Data",
  "eje": "comparte **el dominio** (fraude de tarjeta) y cambia la tarea",
  "eje_en": "shares **the domain** (card fraud), changes the task",
  "fecha_en": "16 August 2026",
  "mide_en": "**unsupervised** clustering, ARI",
  "mide": "clustering **no supervisado**, métrica ARI",
  "quote": "We find no robust quantum advantage: the sign of the difference depends on "
           "register size, all effect sizes are below 0.013 ARI, and the single significant "
           "advantage we observe is fully explained by the number of configurations searched.",
  "trad": "No encontramos ventaja cuántica robusta: el signo de la diferencia depende del "
          "tamaño del registro, todos los tamaños de efecto están por debajo de 0,013 ARI, "
          "y la única ventaja significativa que observamos queda explicada por entero por "
          "el número de configuraciones probadas."},
 {"id": "arXiv:2607.20168", "fecha": "22 de julio de 2026", "autor": "J. Shen",
  "tit": "Quantum Kernels and the Cross-Section of Stock Returns: Anatomy of a Vanishing "
         "Advantage",
  "eje": "comparte **la forma de la tarea** (ranking supervisado) y cambia el dominio",
  "eje_en": "shares **the shape of the task** (supervised ranking), changes the domain",
  "fecha_en": "22 July 2026",
  "mide_en": "Chinese A-share returns, Information Coefficient",
  "mide": "retornos accionarios chinos (A-shares), métrica IC",
  "quote": "the fidelity kernel is indistinguishable from its RBF control (ΔIC = +0.005, "
           "p = 0.42)",
  "trad": "el kernel de fidelidad es indistinguible de su control RBF."},
 {"id": "arXiv:2503.05602", "fecha": "v3, 28 de julio de 2025",
  "autor": "R. Flórez-Ablan, M. Roth y J. Schnabel",
  "tit": "On the similarity of bandwidth-tuned quantum kernels and classical kernels",
  "eje": "no compara nada cabeza a cabeza: explica **la causa**",
  "eje_en": "compares nothing head-to-head: it explains **the cause**",
  "fecha_en": "v3, 28 July 2025",
  "mide_en": "mechanism; reports no effect size",
  "mide": "mecanismo; no reporta cifra de efecto",
  "quote": "optimal bandwidth tuning results in QKs that closely resemble radial basis "
           "function (RBF) kernels, leading to a lack of quantum advantage over classical "
           "methods",
  "trad": "el ajuste óptimo del ancho de banda produce kernels cuánticos que se parecen "
          "mucho a kernels RBF, lo que lleva a una ausencia de ventaja cuántica frente a "
          "los métodos clásicos."},
]
for _f in FUENTES:
    for _k in ("id", "fecha", "fecha_en", "autor", "tit", "eje", "eje_en",
               "mide", "mide_en", "quote", "trad"):
        if not _f.get(_k):
            raise SystemExit("la fuente %s no tiene %r" % (_f.get("id"), _k))
    if _f["tit"][0].islower() or " sobre " in _f["tit"]:
        raise SystemExit("el «titulo» de %s parece una descripcion y no un titulo: %r. "
                         "Un titulo se copia de la pagina del paper, no se resume."
                         % (_f["id"], _f["tit"]))
    if " et al." in _f["autor"]:
        raise SystemExit("«et al.» en %s: los autores se leen de la pagina. Hoy escribi "
                         "«R. Moussa et al.» para un paper cuyos autores no habia abierto."
                         % _f["id"])

for _f in FUENTES:
    for _k in ("id", "fecha", "fecha_en", "autor", "tit", "eje", "eje_en",
               "mide", "mide_en", "quote", "trad"):
        if not _f.get(_k):
            raise SystemExit("la fuente %s no tiene %r" % (_f.get("id"), _k))
    if _f["tit"][0].islower() or " sobre " in _f["tit"]:
        raise SystemExit("el «titulo» de %s parece una descripcion y no un titulo: %r. "
                         "Un titulo se copia de la pagina del paper, no se resume."
                         % (_f["id"], _f["tit"]))
    if " et al." in _f["autor"]:
        raise SystemExit("«et al.» en %s: los autores se leen de la pagina. Hoy escribi "
                         "«R. Moussa et al.» para un paper cuyos autores no habia abierto."
                         % _f["id"])

