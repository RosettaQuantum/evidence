#!/usr/bin/env python3
"""Compara la corrida nueva del barrido contra el artefacto original, punto por punto.

Tres preguntas distintas, que no hay que mezclar:
  1. ¿los ERRORES reproducen exacto?  -> deben ser identicos, son deterministas
  2. ¿cuanto se mueven los TIEMPOS?   -> van a moverse; la pregunta es cuanto
  3. ¿las RAZONES entre brazos son mas estables que los tiempos que las componen?
     Esa es la afirmacion del §8 y aqui se MIDE en vez de afirmarse.

Salvedad que hay que decir con el numero: las dos corridas son de la MISMA maquina.
Esto es una cota INFERIOR de la inestabilidad entre computadores distintos, no una
medicion de portabilidad. Lo que prueba es la direccion, no la magnitud.
"""
import json, sys, statistics as st

ORIG = "/Users/nicholasiakl/Documents/Claude/Projects/Rosetta Quantum/evidence-staging/airbus/barrido_airbus.json"
NUEVO = sys.argv[1] if len(sys.argv) > 1 else "airbus-wt/barrido_airbus.json"
a = json.load(open(ORIG)); b = json.load(open(NUEVO))

print("=== 1 · los errores (deterministas) ===")
sa, sb = a["serie"], b["serie"]
print("  puntos: original %d, nuevo %d  %s" % (len(sa), len(sb),
      "OK" if len(sa) == len(sb) else "<<< DISTINTO NUMERO DE PUNTOS"))
malos = 0; comparados = 0
for pa, pb in zip(sa, sb):
    for nom in pa["brazos"]:
        if nom not in pb["brazos"]: print("  falta el brazo %s en Re=%s" % (nom, pa["Re"])); malos += 1; continue
        ea = pa["brazos"][nom].get("error_l2_rel"); eb = pb["brazos"][nom].get("error_l2_rel")
        if ea is None and eb is None: continue
        comparados += 1
        if ea != eb:
            malos += 1
            print("  DIFIERE Re=%-8s %-12s %.6e -> %.6e" % (pa["Re"], nom, ea, eb))
print("  %d errores comparados, %d difieren  => %s" % (comparados, malos,
      "REPRODUCEN EXACTO" if malos == 0 else "NO REPRODUCEN"))

print("\n=== 2 · los tiempos (medicion de esta maquina) ===")
desv = []
for pa, pb in zip(sa, sb):
    for nom in pa["brazos"]:
        ta = pa["brazos"][nom].get("tiempo_pared_s"); tb = pb["brazos"].get(nom, {}).get("tiempo_pared_s")
        if ta and tb: desv.append(abs(tb-ta)/ta)
if desv:
    print("  %d tiempos comparados | desviacion relativa: mediana %.1f%%  max %.1f%%"
          % (len(desv), 100*st.median(desv), 100*max(desv)))

print("\n=== 3 · las razones entre brazos: ¿mas estables? ===")
rz = []
for pa, pb in zip(sa, sb):
    nombres = [n for n in pa["brazos"] if pa["brazos"][n].get("tiempo_pared_s")
               and pb["brazos"].get(n, {}).get("tiempo_pared_s")]
    if len(nombres) < 2: continue
    base = nombres[0]
    for n in nombres[1:]:
        ra = pa["brazos"][n]["tiempo_pared_s"]/pa["brazos"][base]["tiempo_pared_s"]
        rb = pb["brazos"][n]["tiempo_pared_s"]/pb["brazos"][base]["tiempo_pared_s"]
        rz.append(abs(rb-ra)/ra)
if rz:
    print("  %d razones comparadas | desviacion relativa: mediana %.1f%%  max %.1f%%"
          % (len(rz), 100*st.median(rz), 100*max(rz)))
    print("  => la razon es %s que el tiempo suelto (mediana %.1f%% vs %.1f%%)"
          % ("MAS estable" if st.median(rz) < st.median(desv) else "NO mas estable",
             100*st.median(rz), 100*st.median(desv)))
    print("  SALVEDAD: misma maquina. Es cota inferior, no medicion de portabilidad.")

print("\n=== 4 · el hash reproducible ===")
print("  contenido_sha256 nuevo:", b.get("contenido_sha256", "(ausente)")[:34])
print("  excluidos (medidos):")
for x in b.get("campos_no_reproducibles", {}).get("excluidos", []): print("     ", x)
print("  procedencia:")
for k, v in b.get("producido_por_sha256", {}).items(): print("      %-26s %s" % (k, v[:26]))
