#!/usr/bin/env node
/**
 * Una version identifica un codigo, o no identifica nada.
 *
 * EL DEFECTO (medido en el archivo el 2026-08-27, y ya esta sellado adentro):
 *
 *     lib_version 2.0.0  ->  0965542a9532    22 artefactos
 *     lib_version 3.0.0  ->  e5c5d5c3b1e0    61 artefactos
 *                        ->  bbe3ffcd5a52     1 artefacto    <- MISMA version, otro codigo
 *
 * (La primera version de este guardia contaba 19 y 59 porque recorria tres carpetas escritas a
 * mano —`runs`, `reports`, `prereg`— y el archivo tiene cinco: faltaban `manifests` y
 * `predictions`. **Decia «el archivo» y media una parte.** Ahora recorre todo el arbol.)
 *
 * `rosettaq_seal.py` se edito en el sitio sin subir `LIB_VERSION`. Desde entonces **dos
 * librerias distintas se llaman 3.0.0**, y el campo que viaja dentro de cada sello para
 * identificar a su productor **dejo de identificarlo**.
 *
 * POR QUE ES LA PEOR COMBINACION POSIBLE, y no una molestia de versionado: `lib_sha256` SI
 * distingue los dos codigos. O sea que **el campo legible por un humano miente y el ilegible
 * dice la verdad** — exactamente al reves de lo que necesita un archivo que se vende como
 * auditable, porque **el que audita lee la version**. Un revisor que compare dos sellos
 * «3.0.0» concluye que salieron del mismo productor, y no es cierto.
 *
 * DOS COMPROBACIONES, y la primera es la que no se le ocurre a nadie:
 *
 *   1. **En el ARCHIVO**: ninguna `lib_version` puede apuntar a mas de un `lib_sha256`. Esto
 *      caza el defecto **donde ya ocurrio**, no solo cuando alguien vuelve a editar. Y no
 *      depende de que exista un arbol de git: se contesta desde los artefactos publicados.
 *   2. **En el ARBOL**: si el sha de la libreria difiere del commiteado, `LIB_VERSION` tiene
 *      que diferir tambien. Caza el defecto **antes** de que llegue a un sello.
 *
 * LO QUE NO PUEDE HACER, declarado: los artefactos ya publicados con el par ambiguo se quedan
 * asi. Publicado es publicado — **la unica ventana para evitarlo es antes del push**, y por eso
 * esto tiene que correr antes de notarizar y no despues.
 *
 * CONSUMIDOR: la sesion que mantiene el archivo. Cuando grita, sube `LIB_VERSION` y vuelve a
 * sellar lo que **todavia no se publico**. Nunca re-sella lo publicado.
 *
 * Uso:
 *   node check-version-identifica.mjs --self-test
 *   node check-version-identifica.mjs            # desde la raiz de `evidence`
 */
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";
import { execSync } from "node:child_process";
import { createHash } from "node:crypto";

export const CONSUMIDOR = {
  quien: "la sesion que mantiene el archivo (Rosetta Q Main)",
  hace: "sube LIB_VERSION y vuelve a sellar SOLO lo que no se ha publicado; lo publicado no se toca",
  bloquea: "no se notariza mientras una version apunte a dos codigos: el sello nuevo heredaria la ambiguedad",
};

/**
 * Anomalias que YA tienen su explicacion sellada al lado, con el sello que la explica.
 *
 * POR QUE ESTA LISTA EXISTE, y es una decision del archivo que mejora este guardia:
 *
 *     **Un archivo auditable no es uno sin anomalias: es uno donde cada anomalia tiene su
 *     explicacion sellada al lado.**
 *
 * El artefacto con `3.0.0`/`bbe3ffcd` **no se va a re-sellar**, y la razon es la correcta: es un
 * pre-registro, y **un pre-registro re-sellado despues de ver los resultados deja de serlo**
 * aunque no le cambies una coma. Lo que un tercero verifica no es el texto: es que esos bytes
 * existian ANTES que los datos. Re-anclarlo arreglaria la etiqueta legible **rompiendo la
 * garantia real** — que es exactamente el defecto que este proyecto persigue en otros.
 *
 * Entonces la anomalia se queda, y la errata la explica. **Lo que NO puede pasar es que este
 * guardia quede en rojo permanente por ella**: un rojo que nadie puede apagar se aprende a
 * ignorar, y es como se llega a doscientas alertas. Declarada aqui **con el sello de su errata**,
 * pasa de bloqueo a aviso — y si la errata desaparece, vuelve a bloquear.
 */
export const ANOMALIAS_DECLARADAS = {
  // Sellada el 27-ago-2026. Lleva tres cosas, no una: esta anomalia de version, dos criterios
  // de falsacion que el propio laboratorio descubrio incapaces de fallar (el error de truncar
  // una SVD es no negativo y Eckart-Young garantiza la monotonia: no lo garantizaba el
  // instrumento, lo garantizaba el algebra), y una conclusion sobre el reshape que era falsa
  // por medirse con n=1. Las tres CITAN el sello sin tocarlo.
  "3.0.0|bbe3ffcd5a52": "RQ-ERRATA-VW-001",
};

/**
 * sha256 de **los bytes crudos**. Es la unica cantidad que este guardia puede imprimir.
 *
 * EL DEFECTO, que lo encontro Main leyendo la salida y no el codigo. Los dos ejes de este
 * guardia hablaban de cantidades distintas con el mismo nombre:
 *
 *     eje de archivo   lib_sha256 del sello   =  sha256 de los BYTES del archivo
 *     eje de arbol     lo que yo imprimia     =  sha256 del archivo SIN saltos finales
 *
 * La culpa era del ayudante: `printf '%s' "$(cat archivo)"`. **La sustitucion de comandos come
 * todos los saltos de linea finales**, asi que hasheaba un archivo normalizado. Medido sobre
 * `rosettaq_seal.py`: normalizado da `296b691cd071`, crudo da `de1928a7d29d`, y **es el crudo
 * el que aparece en el sello**.
 *
 * POR QUE IMPORTA MAS QUE EL NUMERO: un lector ve «el codigo cambio (X -> Y)» arriba y «este
 * artefacto declara Z» abajo, y **supone que son comparables**. No lo eran, y nada lo decia.
 * Es §4 ter dentro del guardia escrito para §4 ter — **un guardia que imprime una cantidad que
 * nadie puede cruzar contra el archivo ensena a no cruzar.**
 *
 * Por eso no se calcula por shell: se leen los bytes y se hashean aqui, sin intermediario que
 * pueda normalizar sin avisar. Si algun dia hay razon para normalizar, **tiene que decirlo en
 * la salida**.
 */
export function sha256De(buf) {
  return createHash("sha256").update(buf).digest("hex");
}

/** Normaliza `sha256:abc...` y `abc...` al mismo valor. */
export const limpiarSha = (s) => String(s ?? "").replace(/^sha256:/i, "").trim().toLowerCase();

/**
 * ¿Alguna version apunta a mas de un codigo?
 *
 * @param {{version:string, sha:string}[]} sellos
 */
export function evaluarArchivo(sellos, declaradas = ANOMALIAS_DECLARADAS) {
  const mapa = new Map();
  for (const { version, sha } of sellos) {
    if (!version || !sha) continue;
    const s = limpiarSha(sha);
    if (!mapa.has(version)) mapa.set(version, new Map());
    const m = mapa.get(version);
    m.set(s, (m.get(s) ?? 0) + 1);
  }
  const todas = [...mapa.entries()]
    .filter(([, m]) => m.size > 1)
    .map(([version, m]) => ({ version, shas: [...m.entries()].map(([sha, n]) => ({ sha: sha.slice(0, 12), n })) }));

  // Una ambiguedad esta EXPLICADA si cada uno de sus codigos, salvo el mayoritario, tiene su
  // errata declarada. El mayoritario es el legitimo; los demas son las anomalias.
  const explicada = (a) => {
    const orden = [...a.shas].sort((x, y) => y.n - x.n);
    return orden.slice(1).every((s) => declaradas[`${a.version}|${s.sha}`]);
  };
  const ambiguas = todas.filter((a) => !explicada(a));
  const avisadas = todas.filter(explicada);

  return {
    versiones: mapa.size,
    sellos: sellos.length,
    ambiguas, avisadas,
    estado: ambiguas.length ? "ambigua" : "ok",
  };
}

/**
 * ¿El arbol esta por crear una nueva ambiguedad?
 *
 * @param {{shaTrabajo:string|null, shaCommit:string|null, verTrabajo:string|null, verCommit:string|null}} ctx
 */
export function evaluarArbol({ shaTrabajo, shaCommit, verTrabajo, verCommit }) {
  if (!shaTrabajo || !shaCommit) return { estado: "sin_comparacion", motivo: "no hay version commiteada con que comparar" };
  if (limpiarSha(shaTrabajo) === limpiarSha(shaCommit)) return { estado: "ok", motivo: "la libreria no cambio" };
  if (verTrabajo && verCommit && verTrabajo !== verCommit) return { estado: "ok", motivo: `cambio el codigo y la version subio a ${verTrabajo}` };
  return {
    estado: "version_estancada",
    motivo: `el codigo cambio (${limpiarSha(shaCommit).slice(0, 8)} -> ${limpiarSha(shaTrabajo).slice(0, 8)}) y LIB_VERSION sigue en ${verTrabajo}`,
  };
}

// ── self-test ────────────────────────────────────────────────────────────────────────────
const _esPrincipal = process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href;

if (_esPrincipal && process.argv.includes("--self-test")) {
  // EL CASO REAL, con los pares que hoy estan en el archivo.
  const REAL = [
    ...Array(22).fill({ version: "2.0.0", sha: "sha256:0965542a9532" }),
    ...Array(61).fill({ version: "3.0.0", sha: "sha256:e5c5d5c3b1e0" }),
    { version: "3.0.0", sha: "sha256:bbe3ffcd5a52" },
  ];

  const casos = [
    // ── el archivo ──
    // NINGUN caso se ata al inventario de hoy: cada uno inyecta la lista de erratas que
    // necesita. La primera version SI se ataba —usaba `ANOMALIAS_DECLARADAS` por defecto— y
    // **tres casos se pusieron rojos en cuanto Main sello la errata**, sin que nada estuviera
    // mal. Un caso que depende de lo que hay hoy mide el calendario, no la regla.
    ["grita: el caso REAL, con la anomalia SIN declarar — 3.0.0 apunta a dos codigos", () => {
      const r = evaluarArchivo(REAL, {});
      return r.estado === "ambigua" && r.ambiguas[0].version === "3.0.0";
    }],

    ["grita: dice cuantos artefactos cuelgan de cada codigo", () => {
      const a = evaluarArchivo(REAL, {}).ambiguas[0].shas;
      return a.find((x) => x.n === 61) && a.find((x) => x.n === 1);
    }],

    // Y el estado de HOY, con la errata puesta: el mismo archivo queda verde con aviso.
    ["CALLA: el archivo de hoy, con RQ-ERRATA-VW-001 sellada", () => {
      const r = evaluarArchivo(REAL, ANOMALIAS_DECLARADAS);
      return r.estado === "ok" && r.avisadas.length === 1;
    }],

    ["la errata declarada apunta al codigo minoritario, no al de las 61", () =>
      ANOMALIAS_DECLARADAS["3.0.0|bbe3ffcd5a52"] === "RQ-ERRATA-VW-001" &&
      ANOMALIAS_DECLARADAS["3.0.0|e5c5d5c3b1e0"] === undefined],

    ["CALLA: cada version con un solo codigo", () =>
      evaluarArchivo([{ version: "2.0.0", sha: "a" }, { version: "3.0.0", sha: "b" }]).estado === "ok"],

    // Un mismo codigo bajo dos versiones NO es el defecto: es un renombre, y no engana a nadie.
    ["CALLA: dos versiones que comparten codigo — no confunde a quien audita", () =>
      evaluarArchivo([{ version: "3.0.0", sha: "a" }, { version: "3.0.1", sha: "a" }]).estado === "ok"],

    ["CALLA: sin sellos no se inventa un veredicto", () =>
      evaluarArchivo([]).estado === "ok"],

    ["el prefijo sha256: no crea una falsa ambiguedad", () =>
      evaluarArchivo([{ version: "3.0.0", sha: "sha256:ABC" }, { version: "3.0.0", sha: "abc" }]).estado === "ok"],

    // La anomalia con errata sellada pasa de BLOQUEO a aviso. Sin esto el guardia quedaria en
    // rojo permanente por algo que se decidio NO arreglar — y un rojo que nadie puede apagar
    // se aprende a ignorar.
    ["CALLA: la anomalia declarada con su errata se informa y no bloquea", () => {
      const r = evaluarArchivo(REAL, { "3.0.0|bbe3ffcd5a52": "RQ-ERRATA-VW-001" });
      return r.estado === "ok" && r.avisadas.length === 1;
    }],

    ["grita igual: declarar el codigo MAYORITARIO no tapa la anomalia", () => {
      const r = evaluarArchivo(REAL, { "3.0.0|e5c5d5c3b1e0": "errata-equivocada" });
      return r.estado === "ambigua";
    }],

    // ── que cantidad imprime el eje de arbol ──
    // El defecto que encontro Main: los dos ejes decian «sha» y eran cantidades distintas.
    ["sha256De hashea BYTES: un salto final cambia el resultado", () =>
      sha256De(Buffer.from("hola\n")) !== sha256De(Buffer.from("hola"))],

    // MUTACION: reproduce lo que hacia el ayudante viejo —comerse los saltos finales— y
    // comprueba que produce OTRA cantidad. Si algun dia coincidieran, este caso avisa que la
    // normalizacion volvio y nadie lo noto.
    ["MUTACION: normalizar los saltos finales da un sha que NO esta en ningun sello", () => {
      const crudo = Buffer.from("codigo\n\n");
      const comoElAyudanteViejo = Buffer.from(crudo.toString("utf8").replace(/\n+$/, ""));
      return sha256De(crudo) !== sha256De(comoElAyudanteViejo);
    }],

    ["sha256De produce 64 hex, comparable con lib_sha256 sin su prefijo", () =>
      /^[0-9a-f]{64}$/.test(sha256De(Buffer.from("x")))],

    // ── el arbol ──
    ["grita: el codigo cambio y la version no", () =>
      evaluarArbol({ shaTrabajo: "bbe3", shaCommit: "e5c5", verTrabajo: "3.0.0", verCommit: "3.0.0" }).estado === "version_estancada"],

    ["CALLA: cambio el codigo y subio la version", () =>
      evaluarArbol({ shaTrabajo: "bbe3", shaCommit: "e5c5", verTrabajo: "3.1.0", verCommit: "3.0.0" }).estado === "ok"],

    ["CALLA: la libreria no cambio", () =>
      evaluarArbol({ shaTrabajo: "e5c5", shaCommit: "e5c5", verTrabajo: "3.0.0", verCommit: "3.0.0" }).estado === "ok"],

    ["grita distinto: sin nada commiteado es sin_comparacion, no ok", () =>
      evaluarArbol({ shaTrabajo: "x", shaCommit: null, verTrabajo: "3.0.0", verCommit: null }).estado === "sin_comparacion"],

    // ── mutacion ──
    ["MUTACION: si solo mirara el arbol, un defecto YA SELLADO y sin errata pasaria", () => {
      const soloArbol = evaluarArbol({ shaTrabajo: "e5c5", shaCommit: "e5c5", verTrabajo: "3.0.0", verCommit: "3.0.0" }).estado;
      const conArchivo = evaluarArchivo(REAL, {}).estado;
      return soloArbol === "ok" && conArchivo === "ambigua";
    }],
  ];

  let fallos = 0;
  for (const [nombre, fn] of casos) {
    let paso; try { paso = fn(); } catch { paso = false; }
    console.log(`${paso ? "ok   " : "FALLA"}  ${nombre}`);
    if (!paso) fallos++;
  }
  console.log(`\n[version-identifica] self-test: ${casos.length - fallos} de ${casos.length} pasaron.`);
  process.exit(fallos ? 1 : 0);
}

// ── CLI ──────────────────────────────────────────────────────────────────────────────────
if (_esPrincipal && !process.argv.includes("--self-test")) {
  const LIB = "harness/rosettaq_seal.py";
  const sellos = [];
  // Se recorre TODO, no una lista de carpetas: la primera version tenia tres escritas a mano y
  // el archivo tiene cinco. Un instrumento que declara «el archivo» y mide una parte es el
  // defecto que este proyecto persigue — y aparecio en el guardia que lo persigue.
  {
    (function rec(d) {
      if (/^(\.git|node_modules)$/.test(d.split("/").pop())) return;
      for (const e of readdirSync(d)) {
        const p = join(d, e);
        if (statSync(p).isDirectory()) rec(p);
        else if (e.endsWith(".json")) {
          try {
            const sb = JSON.parse(readFileSync(p, "utf8"))?.meta?.sealed_by;
            if (sb?.lib_version && sb?.lib_sha256) sellos.push({ version: sb.lib_version, sha: sb.lib_sha256 });
          } catch { /* JSON ilegible: otro guardia */ }
        }
      }
    })(".");
  }

  const a = evaluarArchivo(sellos);
  console.log(`[version-identifica] ${a.sellos} sello(s) con par version+sha · ${a.versiones} version(es)`);

  let arbol = { estado: "sin_comparacion", motivo: "no se pudo leer el arbol" };
  try {
    // Bytes crudos por los dos lados. `encoding: "buffer"` es lo que impide que git o el
    // shell normalicen el contenido sin decirlo.
    const bytesTrabajo = readFileSync(LIB);
    const bytesCommit = execSync(`git show HEAD:${LIB}`, { encoding: "buffer", maxBuffer: 64 * 1024 * 1024 });
    const ver = (buf) => (buf.toString("utf8").match(/LIB_VERSION\s*=\s*"([^"]+)"/) ?? [])[1] ?? null;
    arbol = evaluarArbol({
      shaTrabajo: sha256De(bytesTrabajo), shaCommit: sha256De(bytesCommit),
      verTrabajo: ver(bytesTrabajo), verCommit: ver(bytesCommit),
    });
  } catch { /* queda sin_comparacion */ }
  console.log(`[version-identifica] arbol: ${arbol.estado} — ${arbol.motivo}`);
  console.log(`[version-identifica] la cifra de arriba es sha256 de los bytes de ${LIB}: la MISMA que viaja como lib_sha256 en cada sello.`);

  for (const x of a.avisadas ?? []) {
    console.log(`   ~ anomalia DECLARADA  lib_version ${x.version} — su errata la explica; se informa y no bloquea`);
  }

  if (a.estado === "ambigua") {
    console.error(`\n[version-identifica] BLOQUEADO: ${a.ambiguas.length} version(es) apuntan a mas de un codigo`);
    for (const x of a.ambiguas) {
      console.error(`    lib_version ${x.version}:`);
      for (const s of x.shas) console.error(`       ${s.sha}   ${s.n} artefacto(s)`);
    }
    console.error("[version-identifica] `lib_sha256` distingue y `lib_version` no: el campo que lee un");
    console.error("[version-identifica] humano miente y el que lee una maquina dice la verdad.");
    console.error("[version-identifica] Sube LIB_VERSION y re-sella SOLO lo que no se ha publicado.");
  }
  if (arbol.estado === "version_estancada") console.error(`\n[version-identifica] BLOQUEADO: ${arbol.motivo}`);

  process.exit(a.estado === "ambigua" || arbol.estado === "version_estancada" ? 1 : 0);
}
