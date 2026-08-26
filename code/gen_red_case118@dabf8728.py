#!/usr/bin/env python3
"""Vuelca la topologia de case118 TAL COMO LA CARGA EL HARNESS DE E.ON.

POR QUE EXISTE ESTE ARCHIVO
---------------------------
La visualizacion necesita saber que barra conecta con que barra. Reconstruirlo desde
otra fuente NO sirve: el case118 de MATPOWER trae 175 lineas y este trae 173, asi que
el indice 172 apuntaria a otro corredor. Una red preciosa y equivocada es peor que
ninguna.

El indice de `lineas` ES el indice que usan los candidatos del harness, en el orden en
que pandapower las carga. El censo (118 barras / 173 lineas) calza con el que declara
el sello RQ-EXP-EON-C-K08-003.

NO HAY COORDENADAS: `bus_geodata` viene vacio en esta red. No es que no se buscaran.
Quien dibuje esto calcula la disposicion y DECLARA que es un tendido calculado y no
geografico.
"""
import json, sys
import pandapower as pp
import pandapower.networks as nw

net = nw.case118()
out = {
 "fuente": "pandapower.networks.case118()",
 "pandapower_version": pp.__version__,
 "censo": {"buses": len(net.bus), "lineas": len(net.line), "trafos": len(net.trafo)},
 "ADVERTENCIA": ("El indice de esta lista ES el indice que usan los candidatos del harness. "
                 "NO reconstruir desde MATPOWER case118: da 175 lineas, no 173, y los indices se corren."),
 "coordenadas_de_barras": None,
 "lineas": [{"idx": int(i), "from_bus": int(r.from_bus), "to_bus": int(r.to_bus),
             "length_km": float(r.length_km)} for i, r in net.line.iterrows()],
 "trafos": [{"idx": int(i), "hv_bus": int(r.hv_bus), "lv_bus": int(r.lv_bus)}
            for i, r in net.trafo.iterrows()],
}
json.dump(out, open(sys.argv[1], "w"), indent=1)
print("escrito", sys.argv[1])
