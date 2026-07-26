"""
Cuantas dianas haria falta para que el efecto observado fuera detectable.
El efecto pareado (cuantico - clasico) por diana tiene tamano d = delta/sd_null.
Combinando K dianas independientes por Stouffer, z_K = d*sqrt(K).
"""
import json, numpy as np
P = json.load(open("paired_null.json"))
print("%-16s %8s %8s %8s %8s" % ("diana","delta","sd_null","d","K p<0.05"))
ds=[]
for name,R in P.items():
    rows=R["rows"]
    d=np.mean([r["delta_obs"]/max(r["null_sd"],1e-9) for r in rows])
    sd=np.mean([r["null_sd"] for r in rows]); dl=np.mean([r["delta_obs"] for r in rows])
    K=int(np.ceil((1.645/abs(d))**2)) if d!=0 else None
    ds.append(d)
    print("%-16s %+8.2f %8.2f %+8.3f %8s" % (name,dl,sd,d,K))
d=np.mean(ds)
print("\nefecto medio d = %+.3f  ->  z con 3 dianas = %+.2f" % (d, d*np.sqrt(3)))
for K in (3,6,12,20,30,50):
    print("   K=%-3d  z=%+5.2f  p(una cola)=%.3f" % (K, d*np.sqrt(K),
        0.5*(1-np.math.erf(abs(d)*np.sqrt(K)/np.sqrt(2))) if d>0 else float('nan')))
# solo miosina (la unica con senal consistente)
m=P["CARDIAC_MYOSIN"]; dm=np.mean([r["delta_obs"]/r["null_sd"] for r in m["rows"]])
print("\nsolo miosina: d=%+.3f -> K para p<0.05 = %d ; K para p<0.01 = %d"
      % (dm, int(np.ceil((1.645/dm)**2)), int(np.ceil((2.326/dm)**2))))
