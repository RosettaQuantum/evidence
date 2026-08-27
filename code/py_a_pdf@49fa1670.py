#!/usr/bin/env python3
"""Convierte un .py a PDF legible, para paquetes donde el revisor lee en vez de ejecutar.

El codigo va TAL CUAL: mismos bytes, mismo orden, sin reformatear. El PDF declara en su
cabecera el sha256 del archivo fuente, para que quien lo lea pueda comprobar que el .py del
repositorio publico es exactamente este y no una version limpiada para la ocasion.
"""
import hashlib, html, os, subprocess, sys
SRC, DST, TIT = sys.argv[1], sys.argv[2], sys.argv[3]
b = open(SRC, "rb").read()
sha = hashlib.sha256(b).hexdigest()
lineas = b.decode("utf-8").split("\n")
cuerpo = "\n".join('<tr><td class="n">%d</td><td class="c">%s</td></tr>'
                   % (i, html.escape(l) or "&nbsp;") for i, l in enumerate(lineas, 1))
HTML = """<!doctype html><meta charset="utf-8"><title>%s</title><style>
@page { size: A4; margin: 14mm 12mm 15mm 12mm; }
body { font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 7.4pt; line-height: 1.34;
       color: #1a1714; background: #fff; }
h1 { font-family: Georgia, serif; font-size: 13pt; font-weight: 400; margin: 0 0 2mm; }
.meta { font-size: 7pt; color: #6b6259; border-bottom: 1px solid #d8d0c4;
        padding-bottom: 2.5mm; margin-bottom: 3.5mm; line-height: 1.6; }
.meta b { color: #1a1714; }
table { border-collapse: collapse; width: 100%%; }
td.n { width: 9mm; text-align: right; padding-right: 3mm; color: #b4aa9c;
       user-select: none; vertical-align: top; }
td.c { white-space: pre-wrap; word-break: break-word; }
</style><h1>%s</h1>
<div class="meta"><b>%s</b> · %d lines · sha256 <b>%s</b><br>
The source file is published verbatim at
<b>github.com/RosettaQuantum/vw-spectral-screen</b>. Recompute the hash above on the file in
that repository: it must match. This PDF is a reading copy — the runnable file is the one in
the repository.</div>
<table>%s</table>""" % (html.escape(TIT), html.escape(TIT), html.escape(os.path.basename(SRC)),
                        len(lineas), sha, cuerpo)
tmp = DST[:-4] + ".html"
open(tmp, "w", encoding="utf-8").write(HTML)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
r = subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=" + DST, "file://" + os.path.abspath(tmp)],
                   capture_output=True, text=True)
os.remove(tmp)
if not os.path.exists(DST) or os.path.getsize(DST) < 1000:
    raise SystemExit("ABORTA: el PDF no salio.\n" + r.stderr[-300:])
print("%s  ·  %d lineas  ·  sha del fuente %s" % (os.path.basename(DST), len(lineas), sha[:16]))
