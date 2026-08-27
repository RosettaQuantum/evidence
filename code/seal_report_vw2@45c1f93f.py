#!/usr/bin/env python3
"""Sella el ENTREGABLE de VW. El PDF es el archivo que viaja; el markdown es su fuente.

QUE SE SELLA Y POR QUE CUATRO HASHES
------------------------------------
Un sello que dijera solo «este PDF» seria inauditable: nadie podria rehacerlo. Aqui viajan los
CUATRO eslabones de la cadena, de modo que un tercero pueda reconstruirla entera:

    esperados.json  ->  literatura.json  ->  markdown  ->  PDF
    (lo que medimos)    (lo que citamos)     (fuente)     (lo que viaja)

GUARDIA: antes de sellar se recomputan los cuatro hashes contra el disco Y se vuelve a correr
la guardia de requisitos SOBRE EL PDF. Si un archivo cambio o si aparece un requisito duro sin
cubrir, aborta. No se sella un entregable cuyo estado no se verifica en el momento de sellarlo.

Costo US$0. Sin GPU.
"""
import hashlib, json, os, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
EV = os.path.join(RAIZ, "evidence"); LAB = os.path.join(RAIZ, "lab-vw-2026-08-26")
sys.path.insert(0, os.path.join(EV, "harness"))
import rosettaq_seal as rs
from reloj_sello import ahora_stamp, ahora_iso, coherentes
from guardia_requisitos import cargar, comprobar

def sha(p): return "sha256:" + hashlib.sha256(open(p, "rb").read()).hexdigest()

ARCHIVOS = {
    "esperados.json":  os.path.join(LAB, "esperados.json"),
    "literatura.json": os.path.join(LAB, "literatura.json"),
    "ENTREGABLE-VW-EN.md": os.path.join(AQUI, "ENTREGABLE-VW-EN.md"),
    "1_Rosetta-Quantum-VW-Deliverable.pdf":
        os.path.join(AQUI, "PAQUETE-VW", "1_Rosetta-Quantum-VW-Deliverable.pdf"),
}
ESPERADOS = {
    "esperados.json": "sha256:155a35f93d721392f37aa8f9729546c5cbcfe294b68f389dea0ed06838ed6021",
    "literatura.json": "sha256:c02fcb07c986871d605c07de2942942b4059af7a6f42cb2f9cec8706f6df7a4a",
    "ENTREGABLE-VW-EN.md": "sha256:a3016488356c256340af9bc00bad8f8628a752f41ff07652d56c7cc477ed4bbc",
    "1_Rosetta-Quantum-VW-Deliverable.pdf":
        "sha256:47de9280695cb7b3f5c6066c275058de0d4cebb9bd908352ec6527cd1671eb20",
}
# ------------------------------------------------------------------ GUARDIA 1
hashes = {}
for nombre, ruta in ARCHIVOS.items():
    h = sha(ruta); hashes[nombre] = h
    if h != ESPERADOS[nombre]:
        raise SystemExit("ABORTA: %s cambio desde que se congelo.\n  esperado %s\n  medido   %s\n"
                         "Un sello sobre un archivo movido no vale nada." % (nombre, ESPERADOS[nombre], h))

# ------------------------------------------------------------------ GUARDIA 2
import pypdf
paginas = pypdf.PdfReader(ARCHIVOS["1_Rosetta-Quantum-VW-Deliverable.pdf"]).pages
texto_pdf = "\n".join((p.extract_text() or "") for p in paginas)
if not (4 <= len(paginas) <= 8):
    raise SystemExit("ABORTA: el PDF trae %d paginas y el R6 exige 4 a 8." % len(paginas))
for otro in ("E.ON", "Grid Expansion", "HSBC", "Airbus", "Cleveland"):
    if otro in texto_pdf:
        raise SystemExit("ABORTA: «%s» aparece en el PDF de VW. Asi viajo el titulo de E.ON "
                         "dentro del paquete de Airbus." % otro)
reqs, mapeo, nc = cargar(os.path.join(EV, "desafios", "vw.toml"))
cub, duros, blandos, decl = comprobar(texto_pdf, reqs, mapeo, nc)
if duros:
    raise SystemExit("ABORTA: el PDF que se sella no cubre %d requisito(s) duro(s): %s"
                     % (len(duros), [r[0] for r in duros]))

STAMP, ISO = ahora_stamp(), ahora_iso(); assert coherentes(STAMP, ISO)
NOMBRE = ("RosettaQ__REPORT__RQ-REPORT-VW-002__%s__"
          "lo-que-el-espectro-de-llava-dice-sobre-la-compresion-tensorial.json" % STAMP)

doc = {"meta": {
    "file_name": NOMBRE, "file_id": "RQ-REPORT-VW-002", "type": "REPORT",
    "is_demo": False,
    "scope_note":
        "SEGUNDA version del entregable del track VW. Se re-sello ANTES de publicar (el sello previo de esta misma version nunca salio del disco) porque al ejercer la promesa del §1 bis —seguir uno mismo las instrucciones que uno da— aparecio que el informe citaba tres sellos por su identificador y no decia DONDE encontrarlos. Se descargan sin cuenta desde el archivo publico; ahora el documento lo dice. Y una segunda correccion de la misma clase, tambien antes de publicar: el pre-registro al que la referencia lleva esta en ESPAÑOL y el jurado es internacional. No se traduce —sus bytes son lo que la fecha protege— pero el cuerpo ahora dice en ingles QUE contiene, para que quien siga la referencia sepa que esta verificando aunque no lo lea. Las dos las encontro EJERCER la promesa como si uno fuera el jurado, no un guardia: un guardia comprueba lo que hay, ejercer comprueba lo que falta. Y una tercera, tambien antes de publicar: la URL del repositorio se PARTIA a mitad de palabra al maquetarse, asi que un jurado no podia copiarla. Estaba, y no servia. Ahora va en su propia linea. Sobre el track VW (Compression, Autonomous Driving) del 2026 Global Quantum + "
        "AI Challenge. NO afirma ventaja: el metodo propio queda dominado por el baseline "
        "clasico que el propio enunciado nombra. Lo que aporta es la medicion y siete "
        "requisitos declarados no cumplidos en el cuerpo. Publicacion pendiente de "
        "autorizacion de Nicholas.",
    "cadena_de_produccion": {
        "orden": "esperados.json -> literatura.json -> markdown -> PDF",
        "nota": "los cuatro van para que un tercero pueda rehacer la cadena, no solo "
                "comprobar el ultimo eslabon. El PDF es lo que viaja; el markdown es su "
                "fuente; los dos json son de donde sale cada cifra.",
        "archivos": hashes,
    },
    "prereg": "RQ-PREREG-VW-001", "errata": "RQ-ERRATA-VW-001",
    "sustituye_a": {
        "file_id": "RQ-REPORT-VW-001",
        "por_que": "el repositorio publico se publico DESPUES de sellar el primero "
                   "(github.com/RosettaQuantum/vw-spectral-screen, Apache 2.0, 27-ago-2026). "
                   "Tres afirmaciones del cuerpo dejaron de ser ciertas en ese momento: el R4 "
                   "decia «not yet published», el R16 no podia afirmar replicacion por un "
                   "tercero, y el R22 nombraba «una licencia permisiva» sin decir cual.",
        "regla": "publicado es publicado: el primero NO se reescribe ni se re-ancla. Queda como "
                 "el registro del estado ANTES de publicar el repositorio, que es un estado "
                 "real y fechado, no un borrador.",
    },
}, "w6": {
    "que": {
        "titulo": "What the Spectrum of LLaVA-1.5-7B Says About Tensor-Network Compression",
        "el_resultado_principal":
            "nuestro metodo pierde contra INT8 por fila (bitsandbytes) por 56x en la mediana "
            "sobre 21 matrices a ~2x de compresion, y no gana en NINGUNA. Va en el abstract, "
            "no en la discusion.",
        "lo_que_si_aporta":
            "que la afirmacion del §5.1 del propio enunciado —MPS/TTNS dan 2-10x preservando "
            "precision— no se sostiene por la descomposicion sola sobre su modelo de "
            "referencia; y que NINGUNO de nueve metodos publicados en cuatro comparaciones "
            "entre feb y jul 2026 cruza el umbral, lo que no depende de nada nuestro.",
        "el_hallazgo_sobre_su_propia_rubrica":
            "cumplimos el R18 con ~5x el umbral y pedimos que NO se nos acredite: la "
            "reduccion de FLOPs es una identidad algebraica de la razon de compresion, no "
            "mide calidad y por construccion no puede penalizar su perdida.",
        "declarados_no_cumplidos": [r[0] for r in decl],
        "cobertura_medida_SOBRE_EL_PDF": {
            "cubiertos": len(cub), "de_los_que_decimos_cumplir": len(reqs) - len(decl),
            "duros_sin_cubrir": 0, "blandos_sin_cubrir": [r[0] for r in blandos],
        },
        "paginas": len(paginas),
    },
    "como": {
        "pesos": "peticiones HTTP por rango sobre los safetensors publicados: 32 MB por "
                 "matriz en vez de 14 GB de modelo.",
        "reproducibilidad": "353 valores sellados; reproducen desde cache borrado, 0 fallos. "
                            "NO se cita el tiempo: hay dos cifras ciertas en el repositorio "
                            "(9,5 con cache a medias, 16,5 limpia) y la que quedo DENTRO del "
                            "archivo sellado es justo la que no sirve. Un tiempo se sella con "
                            "su condicion al lado o no se sella.",
        "guardias_al_sellar": "los cuatro hashes recomputados contra el disco; el PDF entre 4 "
                              "y 8 paginas; ningun otro desafio nombrado en el PDF; ningun "
                              "requisito duro sin cubrir, medido SOBRE EL PDF y no sobre el "
                              "markdown.",
        "compute": "CPU. Sin GPU. US$0. Sin shots.",
    },
    "cuando": {"archived_at": ISO, "fase_I_cierra": "2026-09-15"},
    "donde": {"paquete": "evidence-staging/PAQUETE-VW", "codigo": "https://github.com/RosettaQuantum/vw-spectral-screen"},
    "porque": {
        "question": "¿puede la compresion por redes tensoriales llevar un VLAM de 7B a "
                    "hardware embarcado sin perder precision, y se puede saber antes de "
                    "gastar en GPU?",
        "para_que": "el problema declarado de VW es meter un VLAM en un SoC de vehiculo. Hoy "
                    "si una campaña de compresion va a funcionar se descubre despues de "
                    "pagarla.",
    },
    "quien": {"lab": "Rosetta Quantum — sesion laboratorio (medicion y guiones)",
              "coordinacion": "Rosetta Q Main (informe, guardias y sello)",
              "lead": "Nicholas Iakl Freundlich",
              "separacion_de_deberes": "el texto que lee el jurado pasa por Nicholas antes de "
                                       "salir; la publicacion es decision suya."},
}}
_mi = "sha256:" + hashlib.sha256(open(__file__, "rb").read()).hexdigest()
rs.seal(doc, harness=("seal_report_vw.py", "1.0.0", _mi), sealed_at=ISO, schema=rs.SCHEMA_V3)
assert rs.verify(doc)
dst = os.path.join(EV, "reports", "2026", "08", NOMBRE)
assert not os.path.exists(dst)
json.dump(doc, open(dst, "w"), indent=1, ensure_ascii=False)
assert rs.verify(json.load(open(dst)))
print("ENTREGABLE sellado :", doc["meta"]["content_hash"])
print("paginas            :", len(paginas), "· requisitos duros sin cubrir: 0")
print("cadena             : 4 archivos, hashes verificados contra disco")
print("archivo            :", NOMBRE)
