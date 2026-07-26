# -*- coding: utf-8 -*-
"""Genera el visor 3D autocontenido (sin dependencias externas)."""
import json

P = json.load(open("/home/claude/rosettaq/viz_payload.json"))
NULL = json.load(open("/home/claude/rosettaq/spatial_null.json"))
PAIR = json.load(open("/home/claude/rosettaq/paired_null.json"))
REQ = json.load(open("/home/claude/rosettaq/required_deliverables.json"))

stats = {}
for k in P:
    s = {}
    if k in NULL:
        s["null"] = {m: NULL[k][m] for m in NULL[k] if m != "config"}
    if k in PAIR:
        s["pair"] = {"delta": PAIR[k]["delta_medio"], "z": PAIR[k]["z_medio"],
                     "pos": PAIR[k]["configs_delta_positivo"], "n": PAIR[k]["n_configs"],
                     "p": PAIR[k]["p_mediano"]}
    if k in REQ:
        s["req"] = REQ[k]
    stats[k] = s

HTML = u"""<!DOCTYPE html>
<meta charset="utf-8">
<title>Rosetta Quantum — Cleveland Clinic: conectividad cuantica y sitios predichos</title>
<style>
 :root{--bg:#0b0f14;--pan:#121821;--ln:#1f2a37;--tx:#e6edf3;--mu:#8b98a5;--ac:#5eead4}
 *{box-sizing:border-box}
 body{margin:0;background:var(--bg);color:var(--tx);
      font:14px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
 header{padding:18px 24px;border-bottom:1px solid var(--ln)}
 h1{margin:0;font-size:17px;letter-spacing:.2px}
 h1 span{color:var(--mu);font-weight:400}
 .sub{color:var(--mu);font-size:12.5px;margin-top:5px}
 .wrap{display:flex;gap:0;height:calc(100vh - 74px);min-height:560px}
 .left{flex:1 1 auto;position:relative;background:radial-gradient(60% 60% at 50% 45%,#101722,#0b0f14)}
 canvas{display:block;width:100%;height:100%;cursor:grab}
 canvas:active{cursor:grabbing}
 .right{width:392px;flex:none;border-left:1px solid var(--ln);background:var(--pan);
        overflow:auto;padding:16px 18px}
 .bar{position:absolute;top:12px;left:12px;right:12px;display:flex;gap:8px;flex-wrap:wrap}
 select,button{background:#182231;color:var(--tx);border:1px solid var(--ln);
   border-radius:7px;padding:6px 10px;font:inherit;font-size:12.5px;cursor:pointer}
 button.on{border-color:var(--ac);color:var(--ac)}
 .leg{position:absolute;bottom:12px;left:12px;font-size:11.5px;color:var(--mu)}
 .ramp{width:180px;height:9px;border-radius:5px;margin:5px 0 3px;
   background:linear-gradient(90deg,#2b1f52,#2b6ea8,#25a58a,#a8c93a,#f9e04b)}
 .k{display:flex;gap:14px;margin-top:7px;align-items:center}
 .d{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:5px}
 h2{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--mu);
    margin:20px 0 8px;font-weight:600}
 h2:first-child{margin-top:0}
 table{width:100%;border-collapse:collapse;font-size:12.5px}
 td,th{padding:4px 6px;border-bottom:1px solid var(--ln);text-align:right}
 th:first-child,td:first-child{text-align:left}
 th{color:var(--mu);font-weight:500}
 .big{font-size:26px;font-weight:600;letter-spacing:-.5px}
 .neg{color:#f9a8a8}.pos{color:var(--ac)}.mu{color:var(--mu)}
 .note{font-size:12px;color:var(--mu);margin-top:8px}
 .pill{display:inline-block;font-size:11px;padding:2px 8px;border-radius:99px;
   border:1px solid var(--ln);color:var(--mu);margin-right:5px}
 footer{padding:10px 24px;border-top:1px solid var(--ln);color:var(--mu);font-size:11.5px}
</style>
<header>
 <h1>Rosetta Quantum <span>· Cleveland Clinic · caminata cuantica sobre la red de contactos</span></h1>
 <div class="sub">Rejilla congelada en PR-CLEV-001 (corte 8.5 A, ventana 0.5-8.0, 16 muestras).
   Ningun parametro ajustado por proteina. Estructura de entrada = apo; el sitio verdadero
   se lee del farmaco co-cristalizado en la holo y nunca entra al calculo.</div>
</header>
<div class="wrap">
 <div class="left">
  <canvas id="c"></canvas>
  <div class="bar">
   <select id="t"></select>
   <button id="mq" class="on">caminata cuantica</button>
   <button id="md">difusion clasica</button>
   <button id="ms" class="on">sitio verdadero</button>
   <button id="mp" class="on">top-5 predicho</button>
   <button id="spin" class="on">girar</button>
  </div>
  <div class="leg">
   <div>puntaje de propagacion (percentil entre residuos distales)</div>
   <div class="ramp"></div>
   <div style="display:flex;justify-content:space-between;width:180px"><span>bajo</span><span>alto</span></div>
   <div class="k">
     <span><i class="d" style="background:#e5484d"></i>sitio alosterico verdadero</span>
     <span><i class="d" style="background:#8b98a5"></i>fuente (sitio activo)</span>
   </div>
  </div>
 </div>
 <div class="right" id="p"></div>
</div>
<footer>Evidencia sellada y anclada · las cifras de esta pagina se generan del mismo JSON que las corridas del ledger</footer>
<script>
const DATA=__DATA__, ST=__STATS__;
const keys=Object.keys(DATA);
const sel=document.getElementById('t');
keys.forEach(k=>{const o=document.createElement('option');o.value=k;o.textContent=DATA[k].label;sel.appendChild(o)});
let cur=keys[0], mode='ctqw', showSite=true, showPred=true, spin=true;
let rx=0.3, ry=0.6, drag=null, zoom=1;

const cv=document.getElementById('c'), cx=cv.getContext('2d');
function ramp(v){ // 0..1 -> color
 const s=[[43,31,82],[43,110,168],[37,165,138],[168,201,58],[249,224,75]];
 const x=Math.max(0,Math.min(1,v))*(s.length-1), i=Math.floor(x), f=x-i;
 const a=s[i], b=s[Math.min(i+1,s.length-1)];
 return `rgb(${a[0]+(b[0]-a[0])*f|0},${a[1]+(b[1]-a[1])*f|0},${a[2]+(b[2]-a[2])*f|0})`;
}
function ranks(v,distal){ // percentil dentro de los distales
 const idx=[];for(let i=0;i<v.length;i++)if(distal[i])idx.push(i);
 idx.sort((a,b)=>v[b]-v[a]);
 const r=new Array(v.length).fill(null);
 idx.forEach((id,k)=>r[id]=1-k/Math.max(idx.length-1,1));
 return r;
}
function draw(){
 const D=DATA[cur], N=D.n, W=cv.width=cv.clientWidth*devicePixelRatio,
       H=cv.height=cv.clientHeight*devicePixelRatio;
 cx.clearRect(0,0,W,H);
 const co=D.coords, v=D[mode==='ctqw'?'ctqw':'diff'], pr=ranks(v,D.distal);
 let cxm=0,cym=0,czm=0; for(const p of co){cxm+=p[0];cym+=p[1];czm+=p[2]}
 cxm/=N;cym/=N;czm/=N;
 const ca=Math.cos(rx),sa=Math.sin(rx),cb=Math.cos(ry),sb=Math.sin(ry);
 const pts=[];let rad=1;
 for(let i=0;i<N;i++){
  let x=co[i][0]-cxm,y=co[i][1]-cym,z=co[i][2]-czm;
  let y2=y*ca-z*sa, z2=y*sa+z*ca;
  let x2=x*cb+z2*sb, z3=-x*sb+z2*cb;
  pts.push([x2,y2,z3]); rad=Math.max(rad,Math.hypot(x2,y2));
 }
 const S=Math.min(W,H)/(2.35*rad)*zoom, ox=W/2, oy=H/2;
 const site=new Set(D.allo), src=new Set(D.src);
 const pred=new Set(); if(showPred) D.sites.forEach(s=>s.residues.forEach(r=>{
   const j=D.resnum.indexOf(r[1]); if(j>=0)pred.add(j)}));
 const ord=pts.map((p,i)=>i).sort((a,b)=>pts[a][2]-pts[b][2]);
 // traza de la cadena, segmento a segmento con profundidad
 const K=Math.max(1.0,Math.min(2.6,900/N));
 cx.lineCap='round';
 for(let i=1;i<N;i++){
  const a=pts[i-1],b=pts[i];
  if(Math.hypot(co[i][0]-co[i-1][0],co[i][1]-co[i-1][1],co[i][2]-co[i-1][2])>4.6)continue;
  const dep=((a[2]+b[2])/2/rad+1)/2;
  cx.globalAlpha=0.10+0.34*dep;
  cx.strokeStyle='#9fb4cc';
  cx.lineWidth=(1.0+2.2*dep)*K*devicePixelRatio;
  cx.beginPath();cx.moveTo(ox+a[0]*S,oy-a[1]*S);cx.lineTo(ox+b[0]*S,oy-b[1]*S);cx.stroke();
 }
 for(const i of ord){
  const p=pts[i], X=ox+p[0]*S, Y=oy-p[1]*S;
  const dep=(p[2]/rad+1)/2;
  let r=2.9*K*devicePixelRatio*(0.62+0.55*dep), col;
  if(src.has(i)){col='#97a4b2'; r*=1.3}
  else if(pr[i]===null){col='#5d6b7d'}
  else {col=ramp(pr[i]); if(pred.has(i))r*=1.55}
  cx.globalAlpha=0.42+0.58*dep;
  cx.beginPath();cx.arc(X,Y,r,0,7);cx.fillStyle=col;cx.fill();
  if(pred.has(i)&&!src.has(i)){
   cx.globalAlpha=0.30+0.35*dep;cx.lineWidth=1.1*devicePixelRatio;cx.strokeStyle='#f9e04b';
   cx.beginPath();cx.arc(X,Y,r+1.4*devicePixelRatio,0,7);cx.stroke();
  }
  if(showSite&&site.has(i)){
   cx.globalAlpha=0.55+0.45*dep;cx.lineWidth=1.9*devicePixelRatio;cx.strokeStyle='#e5484d';
   cx.beginPath();cx.arc(X,Y,r+2.6*K*devicePixelRatio,0,7);cx.stroke();
  }
 }
 cx.globalAlpha=1;
}
function panel(){
 const D=DATA[cur], S=ST[cur]||{}, h=[];
 h.push(`<h2>${D.label} · ${D.n} residuos</h2>`);
 if(S.pair){
  const p=S.pair, cls=p.delta>0?'pos':'neg';
  h.push(`<div class="big ${cls}">${p.delta>0?'+':''}${p.delta} <span class="mu" style="font-size:13px;font-weight:400">percentiles</span></div>
   <div class="note">ventaja cuantica sobre difusion clasica, promediada sobre las ${p.n} celdas
   de la rejilla congelada. Positiva en ${p.pos}/${p.n}. Contra el null de bolsillos contiguos:
   z = ${p.z}, p = ${p.p} &rarr; <b>${p.p<0.05?'significativa':'no significativa'}</b>.</div>`);
 }
 if(S.null){
  h.push('<h2>Contra el null correcto</h2><table><tr><th>metodo</th><th>obs</th><th>null</th><th>z ingenuo</th><th>z real</th><th>p</th></tr>');
  for(const m in S.null){const x=S.null[m];
   h.push(`<tr><td>${m}</td><td>${x.percentil_observado}</td><td>${x.null_media}&plusmn;${x.null_sd}</td>
   <td class="mu">${x.z_aparente_si_iid}</td><td>${x.z_real_contiguo}</td><td>${x.p_mejor_que_azar}</td></tr>`)}
  h.push('</table><div class="note">"z ingenuo" supone residuos independientes, que es lo que hace implicitamente la literatura. "z real" compara contra bolsillos <i>contiguos</i> del mismo tamano. La diferencia entre ambas columnas es el tamano del espejismo.</div>');
 }
 if(S.req){
  const R=S.req;
  h.push('<h2>Resiliencia al ruido</h2><table><tr><th>canal</th><th>magnitud</th><th>Spearman</th><th>percentil</th></tr>');
  R.desfase_hardware.forEach(x=>h.push(`<tr><td>desfase cuantico</td><td>&gamma;=${x.gamma}</td><td>${x.spearman_vs_ideal}</td><td>${x.percentil}</td></tr>`));
  R.ruido_coordenadas.forEach(x=>h.push(`<tr><td>coordenadas</td><td>&sigma;=${x.sigma_A} A</td><td>${x.spearman_medio}</td><td>${x.percentil_medio}</td></tr>`));
  R.perdida_aristas.forEach(x=>h.push(`<tr><td>contactos perdidos</td><td>${(x.p*100).toFixed(0)}%</td><td>${x.spearman_medio}</td><td>${x.percentil_medio}</td></tr>`));
  h.push('</table><div class="note">El ranking aguanta el ruido <i>cuantico</i> mucho mejor que el ruido <i>estructural</i>. El cuello de botella no es el hardware: es la estructura de entrada.</div>');
  h.push('<h2>Escalabilidad por grano grueso</h2><table><tr><th>bloque</th><th>super-nodos</th><th>percentil</th><th>aceleracion</th></tr>');
  R.coarse_graining.forEach(x=>h.push(`<tr><td>${x.bloque}</td><td>${x.n_supernodos}</td><td>${x.percentil}</td><td>${x.aceleracion}&times;</td></tr>`));
  h.push('</table>');
  const c=R.circuito;
  h.push(`<h2>Costo de circuito medido</h2><table>
   <tr><td>qubits (codificacion binaria)</td><td>${c.qubits_codificacion_binaria}</td></tr>
   <tr><td>aristas del grafo</td><td>${c.aristas}</td></tr>
   <tr><td>grado maximo</td><td>${c.grado_maximo}</td></tr>
   <tr><td>clases de color (capas por paso)</td><td>${c.clases_de_color}</td></tr>
   <tr><td>pasos de Trotter para rango fiel</td><td>${c.r_para_spearman_099}</td></tr>
   <tr><td>profundidad total (capas 2q)</td><td>${c.profundidad_total_2q}</td></tr>
   </table><div class="note">La profundidad se midio, no se cito: es el numero de pasos de Trotter
   con el que el <i>ranking</i> converge (Spearman &ge; 0.99), no el estado.</div>`);
 }
 h.push('<h2>Top-5 sitios predichos (caminata cuantica)</h2><table><tr><th>#</th><th>residuos</th><th>n</th></tr>');
 D.sites.forEach((s,i)=>h.push(`<tr><td>${i+1}</td><td class="mu">${s.residues.slice(0,6).map(r=>r[1]).join(', ')}${s.residues.length>6?'…':''}</td><td>${s.n_residues}</td></tr>`));
 h.push('</table>');
 if(!D.allo.length) h.push('<div class="note"><span class="pill">sin verdad de referencia</span>El reto declara que esta diana se evalua por consenso entre equipos. Esta prediccion queda sellada y fechada <b>antes</b> de que ese consenso exista.</div>');
 document.getElementById('p').innerHTML=h.join('');
}
sel.onchange=e=>{cur=e.target.value;panel();draw()};
function tog(id,f){const b=document.getElementById(id);b.onclick=()=>{f();draw();
  b.classList.toggle('on')}}
document.getElementById('mq').onclick=()=>{mode='ctqw';
 document.getElementById('mq').classList.add('on');document.getElementById('md').classList.remove('on');draw()};
document.getElementById('md').onclick=()=>{mode='diff';
 document.getElementById('md').classList.add('on');document.getElementById('mq').classList.remove('on');draw()};
tog('ms',()=>showSite=!showSite); tog('mp',()=>showPred=!showPred);
tog('spin',()=>spin=!spin);
cv.onmousedown=e=>drag=[e.clientX,e.clientY];
addEventListener('mouseup',()=>drag=null);
addEventListener('mousemove',e=>{if(!drag)return;
 ry+=(e.clientX-drag[0])*0.008; rx+=(e.clientY-drag[1])*0.008; drag=[e.clientX,e.clientY]; draw()});
cv.onwheel=e=>{e.preventDefault();zoom*=e.deltaY>0?0.92:1.08;draw()};
addEventListener('resize',draw);
(function loop(){ if(spin&&!drag){ry+=0.0035;draw()} requestAnimationFrame(loop)})();
panel();draw();
</script>
"""

out = HTML.replace("__DATA__", json.dumps(P, separators=(",", ":"))) \
          .replace("__STATS__", json.dumps(stats, separators=(",", ":")))
open("/home/claude/rosettaq/cleveland_viz.html", "w").write(out)
print("cleveland_viz.html  %.1f KB" % (len(out) / 1024.0))
