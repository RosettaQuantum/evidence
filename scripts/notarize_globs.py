"""Que carpetas componen el archivo. Una sola definicion, importada por todos.

Existe por un fallo concreto: `notarize.py` incluia `manifests/` y
`sync_archives_to_d1.py` no. Nadie lo noto porque ningun paso comparaba los totales —
la tercera copia iba 63 de 64 y el archivo que faltaba era el MANIFEST que explica
como verificar los sellos. Ninguna copia estaba rota; simplemente una tenia menos, y
eso no se ve a menos que se cuente.

Si se agrega una carpeta nueva al archivo, se agrega aqui y en ningun otro lado.
"""

ARCHIVE_GLOBS = (
    "runs/**/*.json",
    "prereg/**/*.json",
    "verdicts/**/*.json",
    "recipes/*.json",
    "manifests/*.json",
)
