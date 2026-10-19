"use strict";

// ── Utilidades ──────────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (v, d = 1) => (v == null ? "—" : `${(v * 100).toFixed(d)}%`);
const pct100 = (v, d = 1) => (v == null ? "—" : `${Number(v).toFixed(d)}%`);
const num = (v, d = 2) => (v == null ? "—" : Number(v).toFixed(d));
const signo = (v, d = 1) => (v == null ? "—" : `${v > 0 ? "+" : ""}${Number(v).toFixed(d)}`);
const clase = (v) => (v > 0 ? "positivo" : v < 0 ? "negativo" : "");

// En la versión publicada (GitHub Pages) no hay servidor: los datos están precalculados en archivos JSON
const ESTATICO = window.MODO_ESTATICO || null;
const slug = (n) => String(n ?? "").replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "_";

function rutaEstatica(ruta, p) {
  const [deporte, que] = ruta.split("/");
  if (que === "opciones") return ruta;
  if (deporte === "futbol") {
    const liga = p.liga || "SP1";
    if (["equipos", "liga", "ranking", "pronosticos"].includes(que)) return `futbol/${que}/${liga}`;
    if (que === "tabla") return `futbol/tabla/${liga}${p.condicion ? "-" + p.condicion : ""}`;
    if (que === "equipo") return `futbol/equipo/${liga}/${slug(p.equipo)}`;
    if (que === "predecir") return `futbol/predecir/${liga}/${slug(p.local)}__${slug(p.visitante)}`;
    if (que === "h2h") { const [a, b] = [p.a, p.b].sort(); return `futbol/h2h/${liga}/${slug(a)}__${slug(b)}`; }
  } else if (deporte === "nba") {
    const t = p.temporada;
    if (["clasificacion", "ranking", "liga", "simular", "estadisticas"].includes(que)) return `nba/${que}/${t}`;
    if (que === "pronosticos") return `nba/pronosticos/${t}${p.fecha ? "-" + p.fecha : ""}`;
    if (que === "equipo") return `nba/equipo/${t}/${p.equipo}`;
    if (que === "predecir") return `nba/predecir/${t}/${p.local}__${p.visitante}`;
  } else {
    const t = p.temporada;
    if (["clasificacion", "ranking", "liga", "simular", "estadisticas"].includes(que)) return `nfl/${que}/${t}`;
    if (que === "pronosticos") return `nfl/pronosticos/${t}${p.semana ? "-" + p.semana : ""}`;
    if (que === "equipo") return `nfl/equipo/${t}/${p.equipo}`;
    if (que === "predecir") return `nfl/predecir/${t}/${p.local}__${p.visitante}`;
  }
  return null;
}

async function api(ruta, params = {}) {
  if (ESTATICO) {
    const archivo = rutaEstatica(ruta, params);
    const r = archivo && (await fetch(`api/${archivo}.json`));
    if (!r || !r.ok) throw new Error("Esta consulta no está disponible en la versión web (solo temporada actual de las ligas principales).");
    const datos = await r.json();
    if (ruta === "futbol/h2h" && datos.a !== params.a) {  // el archivo está en orden alfabético: se da la vuelta
      [datos.a, datos.b, datos.victorias_a, datos.victorias_b, datos.goles_a, datos.goles_b] =
        [datos.b, datos.a, datos.victorias_b, datos.victorias_a, datos.goles_b, datos.goles_a];
    }
    return datos;
  }
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ""));
  const r = await fetch(`/api/${ruta}?${q}`);
  const datos = await r.json();
  if (!r.ok) throw new Error(datos.error || `Error ${r.status}`);
  return datos;
}

const avisoEstatico = () => (ESTATICO
  ? `<p class="nota" style="align-self:center;margin:0 0 8px">Versión web · temporada actual · actualizada ${esc(ESTATICO.actualizado)}</p>` : "");

function forma(texto) {
  return `<span class="forma">${[...(texto || "")].map((c) => `<b class="${c}">${c}</b>`).join("")}</span>`;
}

function cifra(valor, etiqueta) {
  return `<div class="cifra"><div class="valor">${valor}</div><div class="etiqueta">${esc(etiqueta)}</div></div>`;
}

function tarjeta(titulo, cuerpo, extra = "") {
  return `<div class="tarjeta ${extra}">${titulo ? `<h2>${esc(titulo)}</h2>` : ""}${cuerpo}</div>`;
}

function selector(id, etiqueta, opciones, valor) {
  const ops = opciones.map((o) => {
    if (o.grupo) return `<optgroup label="${esc(o.grupo)}">${o.opciones.map((x) => op(x, valor)).join("")}</optgroup>`;
    return op(o, valor);
  }).join("");
  return `<div class="campo"><label for="${id}">${esc(etiqueta)}</label><select id="${id}">${ops}</select></div>`;
}
function op(o, valor) {
  const v = typeof o === "object" ? o.valor : o;
  const t = typeof o === "object" ? o.texto : o;
  return `<option value="${esc(v)}" ${String(v) === String(valor) ? "selected" : ""}>${esc(t)}</option>`;
}

// Tabla con columnas ordenables. columnas: [{clave, titulo, fmt?, texto?, ordenable?}]
function tablaHTML(id, columnas, filas, { clicable = false, corteTras = null } = {}) {
  const cab = columnas.map((c) =>
    `<th class="${c.texto ? "texto" : ""} ${c.ordenable ? "ordenable" : ""} ${c.oculta ? "ocultar-movil" : ""}" data-clave="${c.clave}" ${c.ayuda ? `title="${esc(c.ayuda)}"` : ""}>${esc(c.titulo)}</th>`).join("");
  const cuerpo = filas.map((f, i) =>
    `<tr class="${clicable ? "clicable" : ""} ${corteTras === i + 1 ? "corte" : ""}" data-i="${i}">${columnas.map((c) =>
      `<td class="${c.texto ? "texto" : ""} ${c.oculta ? "ocultar-movil" : ""} ${c.claseCelda ? c.claseCelda(f) : ""}">${c.fmt ? c.fmt(f[c.clave], f) : esc(f[c.clave])}</td>`).join("")}</tr>`).join("");
  return `<div class="tabla-scroll"><table id="${id}"><thead><tr>${cab}</tr></thead><tbody>${cuerpo}</tbody></table></div>`;
}

function hacerOrdenable(id, columnas, filas, alOrdenar) {
  const tabla = document.getElementById(id);
  if (!tabla) return;
  tabla.querySelectorAll("th.ordenable").forEach((th) => {
    th.addEventListener("click", () => {
      const clave = th.dataset.clave;
      const col = columnas.find((c) => c.clave === clave);
      const desc = th.dataset.dir !== "desc";
      filas.sort((a, b) => {
        const x = a[clave], y = b[clave];
        if (typeof x === "string") return desc ? y.localeCompare(x) : x.localeCompare(y);
        return desc ? (y ?? -Infinity) - (x ?? -Infinity) : (x ?? Infinity) - (y ?? Infinity);
      });
      alOrdenar(clave, desc ? "desc" : "asc", col);
    });
  });
}

// ── Gráficos (SVG/HTML, con tooltip al pasar el ratón) ─────────────────────
// Barra apilada de probabilidades: segmentos [{valor, etiqueta, color}]
function barraProb(segmentos) {
  const barra = segmentos.map((s) =>
    `<div style="flex:${Math.max(s.valor, 0.001)};background:${s.color}" data-tip="${esc(s.etiqueta)}: ${pct(s.valor)}"></div>`).join("");
  const leyenda = segmentos.map((s) =>
    `<span><i style="background:${s.color}"></i>${esc(s.etiqueta)} <strong>${pct(s.valor)}</strong></span>`).join("");
  return `<div class="barra-prob">${barra}</div><div class="leyenda">${leyenda}</div>`;
}

// Barras horizontales de una sola serie: items [{nombre, valor, texto?}]
function barras(items, { max = null, fmt = (v) => num(v, 1) } = {}) {
  const tope = max ?? Math.max(...items.map((i) => i.valor), 0.0001);
  return `<div class="barras">${items.map((i) => `
    <div class="fila" data-tip="${esc(i.nombre)}: ${esc(i.texto ?? fmt(i.valor))}">
      <div class="nombre">${esc(i.nombre)}</div>
      <div class="pista"><div class="relleno" style="width:${Math.max(0, (i.valor / tope) * 100)}%"></div></div>
      <div class="num">${esc(i.texto ?? fmt(i.valor))}</div>
    </div>`).join("")}</div>`;
}

// Columnas verticales con 1 o 2 series: etiquetas[], series [{nombre, valores[], clase}]
function columnas(etiquetas, series, { fmt = (v) => v, alto = 170 } = {}) {
  const ancho = 400, m = { i: 30, d: 8, s: 10, b: 24 };
  const w = ancho - m.i - m.d, h = alto - m.s - m.b;
  const max = Math.max(...series.flatMap((s) => s.valores), 0.0001);
  const grupo = w / etiquetas.length;
  const barra = Math.min(28, (grupo - 8) / series.length - 2);
  let svg = "";
  for (let k = 0; k <= 4; k++) {
    const y = m.s + h - (h * k) / 4;
    svg += `<line class="rejilla-linea" x1="${m.i}" x2="${ancho - m.d}" y1="${y}" y2="${y}"/>`;
    svg += `<text x="${m.i - 6}" y="${y + 4}" text-anchor="end">${fmt((max * k) / 4)}</text>`;
  }
  etiquetas.forEach((et, i) => {
    const x0 = m.i + i * grupo + (grupo - series.length * (barra + 2)) / 2;
    series.forEach((s, j) => {
      const v = s.valores[i], bh = (v / max) * h;
      const x = x0 + j * (barra + 2), y = m.s + h - bh;
      const r = Math.min(4, bh / 2, barra / 2);
      svg += `<path class="${s.clase}" d="M${x},${m.s + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + barra - r} Q${x + barra},${y} ${x + barra},${y + r} V${m.s + h} Z"/>`;
      svg += `<rect class="zona" x="${x - 1}" y="${m.s}" width="${barra + 2}" height="${h}" data-tip="${esc(s.nombre ? s.nombre + " · " : "")}${esc(et)}: ${esc(fmt(v))}"/>`;
    });
    svg += `<text x="${m.i + i * grupo + grupo / 2}" y="${alto - 6}" text-anchor="middle">${esc(et)}</text>`;
  });
  svg += `<line class="eje" x1="${m.i}" x2="${ancho - m.d}" y1="${m.s + h}" y2="${m.s + h}"/>`;
  return `<svg class="grafico" viewBox="0 0 ${ancho} ${alto}" role="img">${svg}</svg>`;
}

// Línea con puntos: puntos [{x: etiqueta, y: valor, tip}]; invertir = valores pequeños arriba
function linea(puntos, { invertir = false, alto = 180, fmtY = (v) => v, min = null, max = null } = {}) {
  if (!puntos.length) return "";
  const ancho = 400, m = { i: 36, d: 10, s: 10, b: 24 };
  const w = ancho - m.i - m.d, h = alto - m.s - m.b;
  const ys = puntos.map((p) => p.y);
  let lo = min ?? Math.min(...ys), hi = max ?? Math.max(...ys);
  if (lo === hi) { lo -= 1; hi += 1; }
  const X = (i) => m.i + (puntos.length === 1 ? w / 2 : (i * w) / (puntos.length - 1));
  const Y = (v) => (invertir ? m.s + ((v - lo) / (hi - lo)) * h : m.s + h - ((v - lo) / (hi - lo)) * h);
  let svg = "";
  for (let k = 0; k <= 3; k++) {
    const v = lo + ((hi - lo) * k) / 3, y = Y(v);
    svg += `<line class="rejilla-linea" x1="${m.i}" x2="${ancho - m.d}" y1="${y}" y2="${y}"/>`;
    svg += `<text x="${m.i - 6}" y="${y + 4}" text-anchor="end">${fmtY(v)}</text>`;
  }
  svg += `<polyline class="serie" points="${puntos.map((p, i) => `${X(i)},${Y(p.y)}`).join(" ")}"/>`;
  const paso = Math.max(1, Math.ceil(puntos.length / 6));
  puntos.forEach((p, i) => {
    if (i % paso === 0 || i === puntos.length - 1)
      svg += `<text x="${X(i)}" y="${alto - 6}" text-anchor="middle">${esc(p.x)}</text>`;
    if (puntos.length <= 40) svg += `<circle class="punto" cx="${X(i)}" cy="${Y(p.y)}" r="4"/>`;
    const zw = puntos.length === 1 ? w : w / (puntos.length - 1);
    svg += `<rect class="zona" x="${X(i) - zw / 2}" y="${m.s}" width="${zw}" height="${h}" data-tip="${esc(p.tip ?? `${p.x}: ${fmtY(p.y)}`)}"/>`;
  });
  return `<svg class="grafico" viewBox="0 0 ${ancho} ${alto}" role="img">${svg}</svg>`;
}

function chispa(valores) {
  if (!valores || valores.length < 2) return "";
  const lo = Math.min(...valores), hi = Math.max(...valores), r = hi - lo || 1;
  const pts = valores.map((v, i) => `${(i * 88) / (valores.length - 1) + 1},${21 - ((v - lo) / r) * 19}`).join(" ");
  return `<svg class="chispa" viewBox="0 0 90 22" data-tip="De ${lo} a ${hi}"><polyline points="${pts}"/></svg>`;
}

const COLOR = { local: "var(--series-1)", empate: "var(--neutral-mark)", visitante: "var(--series-2)" };

// ── Tooltip global ──────────────────────────────────────────────────────────
const tip = $("#tip");
document.addEventListener("mousemove", (e) => {
  const el = e.target.closest?.("[data-tip]");
  if (!el) { tip.classList.remove("visible"); return; }
  tip.textContent = el.dataset.tip;
  tip.classList.add("visible");
  const x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
  tip.style.left = `${x}px`;
  tip.style.top = `${e.clientY + 16}px`;
});

// ── Estado y navegación (guardado en la URL para poder compartir enlaces) ─
const VISTAS = {
  futbol: [["tabla", "Clasificación"], ["equipo", "Equipo"], ["predecir", "Predicción"], ["pronosticos", "Pronósticos"],
           ["liga", "Liga"], ["h2h", "Cara a cara"], ["ranking", "Ranking"], ["goleadores", "Goleadores"]],
  nfl: [["clasificacion", "Clasificación"], ["equipo", "Equipo"], ["predecir", "Predicción"], ["pronosticos", "Pronósticos"],
        ["simular", "Playoffs"], ["ranking", "Ranking"], ["estadisticas", "Estadísticas"], ["liga", "Liga"]],
  nba: [["clasificacion", "Clasificación"], ["equipo", "Equipo"], ["predecir", "Predicción"], ["pronosticos", "Pronósticos"],
        ["simular", "Playoffs"], ["ranking", "Ranking"], ["estadisticas", "Estadísticas"], ["liga", "Liga"]],
};
let estado = { deporte: "futbol", vista: "tabla", p: {} };
let opciones = { futbol: null, nfl: null, nba: null };
let cacheEquipos = {};

function leerHash() {
  const [ruta, query] = location.hash.slice(1).split("?");
  const [deporte, vista] = (ruta || "").split("/");
  if (VISTAS[deporte]) {
    estado.deporte = deporte;
    estado.vista = VISTAS[deporte].some(([v]) => v === vista) ? vista : VISTAS[deporte][0][0];
  }
  estado.p = Object.fromEntries(new URLSearchParams(query || ""));
}
function escribirHash() {
  const q = new URLSearchParams(Object.entries(estado.p).filter(([, v]) => v !== "" && v != null)).toString();
  const nuevo = `#${estado.deporte}/${estado.vista}${q ? "?" + q : ""}`;
  if (location.hash !== nuevo) history.replaceState(null, "", nuevo);
}
function ir(cambios = {}, params = null) {
  Object.assign(estado, cambios);
  if (params) estado.p = { ...estado.p, ...params };
  escribirHash();
  render();
}

// ── Controles comunes ───────────────────────────────────────────────────────
function compSeleccionada() {
  if (estado.p.torneo) return `torneo:${estado.p.torneo}`;
  return `liga:${estado.p.liga || "SP1"}`;
}

function controlesFutbol() {
  const o = opciones.futbol;
  const paises = {};
  o.competiciones.forEach((c) => (paises[c.pais] ??= []).push({ valor: `liga:${c.codigo}`, texto: `${c.nombre} (${c.codigo})` }));
  const grupos = Object.entries(paises).map(([pais, ops]) => ({ grupo: pais, opciones: ops }));
  if (o.torneos.length) grupos.push({ grupo: "Selecciones", opciones: [{ valor: "liga:selecciones", texto: "Todas las selecciones" },
    ...o.torneos.map((t) => ({ valor: `torneo:${t.alias}`, texto: t.nombre }))] });
  const sel = compSeleccionada();
  let temporadas = [];
  if (sel.startsWith("torneo:")) {
    const t = o.torneos.find((x) => x.alias === estado.p.torneo);
    temporadas = [{ valor: "", texto: "Última edición" }, { valor: "todas", texto: "Todas las ediciones" },
      ...(t?.ediciones || []).map((a) => ({ valor: a, texto: a }))];
  } else if (sel === "liga:selecciones") {
    const [desde, hasta] = o.anios_selecciones.map(Number);
    temporadas = [{ valor: "", texto: "Últimos 4 años" }, { valor: "todas", texto: "Toda la historia" }];
    for (let a = hasta; a >= Math.max(desde, hasta - 30); a--) temporadas.push({ valor: String(a), texto: String(a) });
  } else {
    const c = o.competiciones.find((x) => x.codigo === (estado.p.liga || "SP1"));
    temporadas = ESTATICO ? [{ valor: "", texto: c?.temporadas?.[0] || "Actual" }]
      : [{ valor: "", texto: "Más reciente" }, ...(c?.temporadas || []).map((t) => ({ valor: t, texto: t })),
        { valor: "todas", texto: "Todas las temporadas" }];
  }
  $("#controles").innerHTML = selector("c-comp", "Competición", grupos, sel) +
    selector("c-temp", "Temporada", temporadas, estado.p.temporada || "") + avisoEstatico();
  $("#c-comp").onchange = (e) => {
    const [tipo, valor] = e.target.value.split(":");
    estado.p = tipo === "torneo" ? { torneo: valor } : { liga: valor };
    ir();
  };
  $("#c-temp").onchange = (e) => ir({}, { temporada: e.target.value, equipo: "", local: "", visitante: "", a: "", b: "" });
}

function controlesNFL() {
  const o = opciones.nfl;
  $("#controles").innerHTML = selector("c-temp", "Temporada", o.temporadas.map(String), estado.p.temporada || o.temporadas[0]) + avisoEstatico();
  $("#c-temp").onchange = (e) => ir({}, { temporada: e.target.value, semana: "" });
}

function controlesNBA() {
  const o = opciones.nba;
  $("#controles").innerHTML = selector("c-temp", "Temporada", o.temporadas, estado.p.temporada || o.temporadas[0].valor) + avisoEstatico();
  $("#c-temp").onchange = (e) => ir({}, { temporada: e.target.value, fecha: "" });
}

function pintarPestanas() {
  const vistas = VISTAS[estado.deporte].filter(([v]) =>
    !(estado.deporte === "futbol" && v === "goleadores" && !estado.p.torneo && estado.p.liga !== "selecciones"));
  $("#pestanas").innerHTML = vistas.map(([v, t]) =>
    `<button role="tab" data-vista="${v}" aria-selected="${v === estado.vista}">${t}</button>`).join("");
  $("#pestanas").querySelectorAll("button").forEach((b) => (b.onclick = () => ir({ vista: b.dataset.vista })));
  document.querySelectorAll("[data-deporte]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.deporte === estado.deporte));
}

function paramsFutbol(extra = {}) {
  return { liga: estado.p.liga, torneo: estado.p.torneo, temporada: estado.p.temporada, ...extra };
}

async function equiposFutbol() {
  const clave = JSON.stringify(paramsFutbol());
  if (!cacheEquipos[clave]) cacheEquipos[clave] = (await api("futbol/equipos", paramsFutbol())).equipos;
  return cacheEquipos[clave];
}

// ── Vistas de fútbol ────────────────────────────────────────────────────────
const vistasFutbol = {
  async tabla() {
    const cond = estado.p.condicion || "";
    const d = await api("futbol/tabla", paramsFutbol({ condicion: cond }));
    const cols = [
      { clave: "pos", titulo: "#" }, { clave: "equipo", titulo: "Equipo", texto: true, fmt: (v) => `<span class="fuerte">${esc(v)}</span>` },
      { clave: "pj", titulo: "PJ" }, { clave: "g", titulo: "G", oculta: true }, { clave: "e", titulo: "E", oculta: true },
      { clave: "p", titulo: "P", oculta: true }, { clave: "gf", titulo: "GF", oculta: true }, { clave: "gc", titulo: "GC", oculta: true },
      { clave: "dg", titulo: "DG", fmt: (v) => signo(v, 0), claseCelda: (f) => clase(f.dg) },
      { clave: "pts", titulo: "Pts", fmt: (v) => `<span class="fuerte">${v}</span>` },
      { clave: "ppp", titulo: "Pts/p", fmt: (v) => num(v), oculta: true },
      { clave: "forma", titulo: "Forma", texto: true, fmt: (v) => forma(v), oculta: true },
    ];
    const filtro = selector("c-cond", "Partidos", [{ valor: "", texto: "Todos" }, { valor: "local", texto: "Como local" },
      { valor: "visitante", texto: "Como visitante" }, { valor: "descanso", texto: "Si acabaran al descanso" }], cond);
    return {
      html: `<h1 class="titulo-vista">Clasificación</h1><p class="descripcion">${esc(d.descripcion)} · ${d.partidos} partidos jugados${d.pendientes ? ` · ${d.pendientes} pendientes` : ""}</p>
        <div class="controles">${filtro}</div>
        ${tarjeta("", tablaHTML("t-tabla", cols, d.filas, { clicable: true }))}
        <p class="nota">Haz clic en un equipo para ver su informe completo.</p>`,
      tras() {
        $("#c-cond").onchange = (e) => ir({}, { condicion: e.target.value });
        document.querySelectorAll("#t-tabla tbody tr").forEach((tr) =>
          (tr.onclick = () => ir({ vista: "equipo" }, { equipo: d.filas[tr.dataset.i].equipo })));
      },
    };
  },

  async equipo() {
    const lista = await equiposFutbol();
    const actual = estado.p.equipo && lista.includes(estado.p.equipo) ? estado.p.equipo : lista[0];
    const d = await api("futbol/equipo", paramsFutbol({ equipo: actual }));
    const b = (x, t) => x ? `<h3>${t}</h3><div class="cifras">${cifra(`${x.g}-${x.e}-${x.p}`, "G-E-P")}${cifra(x.pts, `Puntos (${num(x.ppp)} por partido)`)}${cifra(`${x.gf}-${x.gc}`, "Goles a favor y en contra")}${cifra(pct100(x.pct_victorias, 0), "Victorias")}</div>` : "";
    const nombresRacha = { G: ["victoria", "victorias"], E: ["empate", "empates"], P: ["derrota", "derrotas"] };
    const racha = d.racha.tipo ? `${d.racha.n} ${nombresRacha[d.racha.tipo][d.racha.n === 1 ? 0 : 1]}` : "—";
    let html = `<div class="controles">${selector("c-equipo", "Equipo", lista, actual)}</div>
      <h1 class="titulo-vista">${esc(d.equipo)}</h1>
      <p class="descripcion">${esc(d.descripcion)} · ${d.posicion}º de ${d.equipos_liga}</p><div class="rejilla">`;
    html += tarjeta("Rendimiento", b(d.total, "Total") + b(d.local, "Como local") + b(d.visitante, "Como visitante"));
    html += tarjeta("Forma y rachas", `
      <div class="cifras">${cifra(racha, "Racha actual")}${cifra(d.rachas_max.victorias, "Mejor racha de victorias")}${cifra(d.rachas_max.invicto, "Mayor racha invicto")}</div>
      <h3>Últimos 10 partidos</h3>${forma(d.forma)}
      <h3>Modelos</h3><div class="cifras">${cifra(`${d.elo.rating} <span class="chip">${d.elo.puesto}º</span>`, "Elo")}${cifra(num(d.fuerza.ataque), "Fuerza de ataque (1 = media)")}${cifra(num(d.fuerza.defensa), "Fuerza defensiva (menos es mejor)")}</div>`);
    html += tarjeta("Evolución en la clasificación", linea(d.evolucion.map((e) => ({ x: e.fecha.slice(5), y: e.posicion, tip: `${e.fecha}: ${e.posicion}º · ${e.puntos} pts` })),
      { invertir: true, min: 1, fmtY: (v) => `${Math.round(v)}º` }) + `<p class="nota">Posición tras cada partido (arriba = mejor).</p>`);
    html += tarjeta("Porcentajes de goles (en sus partidos)", barras(Object.entries(d.mercados).map(([n, v]) => ({ nombre: n, valor: v })), { max: 100, fmt: (v) => pct100(v, 0) })
      + `<h3>Marcadores más repetidos</h3><p>${d.marcadores.map((m) => `<span class="chip">${esc(m.marcador)} × ${m.veces}</span>`).join(" ")}</p>`);
    if (d.descanso) {
      const x = d.descanso;
      html += tarjeta("Primera y segunda parte", `<div class="cifras">${cifra(`${x.goles_1t[0]}-${x.goles_1t[1]}`, "Goles 1ª parte")}${cifra(`${x.goles_2t[0]}-${x.goles_2t[1]}`, "Goles 2ª parte")}${cifra(x.remontadas, "Remontadas")}</div>
        <h3>Al descanso iba…</h3>${barras([{ nombre: "Ganando", valor: x.ganando }, { nombre: "Empatando", valor: x.empatando }, { nombre: "Perdiendo", valor: x.perdiendo }], { fmt: (v) => v })}
        <p class="nota">Gana cuando va ganando: ${pct100(x.gana_si_gana, 0)} · Puntúa cuando va perdiendo: ${pct100(x.puntua_si_pierde, 0)}</p>`);
    }
    if (d.juego.length) {
      html += tarjeta("Estadísticas de juego (por partido)", tablaHTML("t-juego",
        [{ clave: "nombre", titulo: "", texto: true }, { clave: "favor", titulo: "A favor", fmt: (v) => num(v) }, { clave: "contra", titulo: "En contra", fmt: (v) => num(v) }], d.juego)
        + (Object.keys(d.ratios).length ? `<h3>Eficacia</h3>${barras(Object.entries(d.ratios).map(([n, v]) => ({ nombre: n, valor: v })), { max: 100, fmt: (v) => pct100(v) })}` : ""));
    }
    if (d.niveles.length) {
      html += tarjeta("Contra rivales según su posición", tablaHTML("t-niv", [
        { clave: "nivel", titulo: "Rivales", texto: true }, { clave: "pj", titulo: "PJ" },
        { clave: "g", titulo: "G-E-P", fmt: (v, f) => `${f.g}-${f.e}-${f.p}` }, { clave: "gf", titulo: "Goles", fmt: (v, f) => `${f.gf}-${f.gc}` },
        { clave: "ppp", titulo: "Pts/p", fmt: (v) => num(v) }], d.niveles));
    }
    html += tarjeta("Últimos partidos", tablaHTML("t-ult", [
      { clave: "fecha", titulo: "Fecha", texto: true }, { clave: "resultado", titulo: "", fmt: (v) => forma(v) },
      { clave: "local", titulo: "Partido", texto: true, fmt: (v, f) => `${esc(f.local)} <b>${f.goles_local}-${f.goles_visitante}</b> ${esc(f.visitante)}` }], d.ultimos));
    if (d.proximos.length) {
      html += tarjeta("Próximos partidos", d.proximos.map((p) => `<p class="fuerte" style="margin:10px 0 0">${esc(p.local)} vs ${esc(p.visitante)} <span class="descripcion">· ${p.fecha}</span></p>`
        + barraProb([{ valor: p.p1, etiqueta: p.local, color: COLOR.local }, { valor: p.px, etiqueta: "Empate", color: COLOR.empate }, { valor: p.p2, etiqueta: p.visitante, color: COLOR.visitante }])).join(""));
    }
    html += "</div>";
    return { html, tras() { $("#c-equipo").onchange = (e) => ir({}, { equipo: e.target.value }); } };
  },

  async predecir() {
    const lista = await equiposFutbol();
    const local = lista.includes(estado.p.local) ? estado.p.local : lista[0];
    const visitante = lista.includes(estado.p.visitante) && estado.p.visitante !== local ? estado.p.visitante : lista.find((e) => e !== local);
    const neutral = estado.p.neutral === "1";
    const d = await api("futbol/predecir", paramsFutbol({ local, visitante, neutral: neutral ? "1" : "" }));
    const fila = (t, si, no) => `<tr><td class="texto">${t}</td><td>${pct(si)}</td><td>${pct(no)}</td></tr>`;
    let html = `<div class="controles">${selector("c-local", "Local", lista, local)}${selector("c-visit", "Visitante", lista, visitante)}
      ${ESTATICO ? "" : `<label class="casilla"><input type="checkbox" id="c-neutral" ${neutral ? "checked" : ""}> Campo neutral</label>`}</div>
      <h1 class="titulo-vista">${esc(d.local)} vs ${esc(d.visitante)}</h1>
      <p class="descripcion">${esc(d.descripcion)} · ${neutral ? "campo neutral" : `en casa de ${esc(d.local)}`}</p><div class="rejilla">`;
    html += tarjeta("Resultado (1X2)", `<div class="cifras">${cifra(`${num(d.goles_local)} - ${num(d.goles_visitante)}`, "Goles esperados")}${cifra(pct(d.elo_local), "Expectativa Elo del local")}</div>`
      + barraProb([{ valor: d.p1, etiqueta: d.local, color: COLOR.local }, { valor: d.px, etiqueta: "Empate", color: COLOR.empate }, { valor: d.p2, etiqueta: d.visitante, color: COLOR.visitante }])
      + `<h3>Cuotas justas (sin margen)</h3><div class="cifras">${cifra(num(1 / d.p1), "1")}${cifra(num(1 / d.px), "X")}${cifra(num(1 / d.p2), "2")}</div>
        <h3>Doble oportunidad</h3><div class="cifras">${cifra(pct(d.p1x), "1X")}${cifra(pct(d.px2), "X2")}${cifra(pct(d.p12), "12")}</div>`);
    html += tarjeta("Marcadores más probables", barras(d.marcadores.map((m) => ({ nombre: m.marcador, valor: m.prob })), { fmt: (v) => pct(v) }));
    html += tarjeta("Goles", `<table><thead><tr><th class="texto"></th><th>Sí / Más</th><th>No / Menos</th></tr></thead><tbody>
      ${Object.entries(d.mas).map(([l, v]) => fila(`Más de ${l} goles`, v, 1 - v)).join("")}
      ${fila("Marcan ambos", d.ambos_marcan, 1 - d.ambos_marcan)}
      ${fila(`Portería a cero ${esc(d.local)}`, d.porteria_cero_local, 1 - d.porteria_cero_local)}
      ${fila(`Portería a cero ${esc(d.visitante)}`, d.porteria_cero_visitante, 1 - d.porteria_cero_visitante)}</tbody></table>`);
    html += tarjeta("Goles de cada equipo", columnas(["0", "1", "2", "3", "4", "5"], [
      { nombre: d.local, valores: d.dist_local, clase: "col-1" }, { nombre: d.visitante, valores: d.dist_visitante, clase: "col-2" }], { fmt: (v) => pct(v, 0) })
      + `<div class="leyenda"><span><i style="background:${COLOR.local}"></i>${esc(d.local)}</span><span><i style="background:${COLOR.visitante}"></i>${esc(d.visitante)}</span></div>`);
    html += tarjeta(`Hándicap de ${d.local}`, `<div class="cifras">${cifra(pct(d.handicap["1.5"]), "-1.5 (gana por 2+)")}${cifra(pct(d.handicap["0.5"]), "-0.5 (gana)")}${cifra(pct(d.handicap["-0.5"]), "+0.5 (no pierde)")}${cifra(pct(d.handicap["-1.5"]), "+1.5 (no pierde por 2+)")}</div>`);
    html += `</div><p class="nota">Modelo Poisson con corrección Dixon-Coles, tiros a puerta y Elo. Orientativo: las casas de apuestas siguen acertando algo más.</p>`;
    return {
      html, tras() {
        $("#c-local").onchange = (e) => ir({}, { local: e.target.value });
        $("#c-visit").onchange = (e) => ir({}, { visitante: e.target.value });
        $("#c-neutral")?.addEventListener("change", (e) => ir({}, { neutral: e.target.checked ? "1" : "" }));
      },
    };
  },

  async pronosticos() {
    const d = await api("futbol/pronosticos", paramsFutbol());
    if (!d.filas.length) return { html: `<div class="error">No hay partidos pendientes en esta competición y temporada. Usa la pestaña Predicción para un partido concreto.</div>` };
    const html = `<h1 class="titulo-vista">Pronósticos</h1><p class="descripcion">${esc(d.descripcion)} · próximos ${d.filas.length} partidos${d.omitidos ? ` · ${d.omitidos} ya disputados aún sin resultado en la fuente` : ""}</p>
      ${tarjeta("", d.filas.map((p) => `<div style="padding:10px 0;border-bottom:1px solid var(--grid)">
        <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><span class="fuerte">${esc(p.local)} vs ${esc(p.visitante)}</span>
        <span class="descripcion" style="margin:0">${p.fecha} · más de 2.5: ${pct(p.mas_2_5, 0)} · ambos marcan: ${pct(p.ambos, 0)} · marcador más probable <b>${esc(p.marcador)}</b></span></div>
        ${barraProb([{ valor: p.p1, etiqueta: p.local, color: COLOR.local }, { valor: p.px, etiqueta: "Empate", color: COLOR.empate }, { valor: p.p2, etiqueta: p.visitante, color: COLOR.visitante }])}</div>`).join(""))}`;
    return { html };
  },

  async liga() {
    const d = await api("futbol/liga", paramsFutbol());
    let html = `<h1 class="titulo-vista">Resumen de la competición</h1><p class="descripcion">${esc(d.descripcion)}</p>
      <div class="cifras" style="margin-bottom:16px">${cifra(d.partidos, "Partidos jugados")}${cifra(d.goles, "Goles")}${cifra(num(d.goles_por_partido), "Goles por partido")}${cifra(`${num(d.ppp_local)} / ${num(d.ppp_visitante)}`, "Pts/partido local / visitante")}</div><div class="rejilla">`;
    html += tarjeta("Resultados", barraProb([{ valor: d.pct_local / 100, etiqueta: "Gana local", color: COLOR.local }, { valor: d.pct_empate / 100, etiqueta: "Empate", color: COLOR.empate }, { valor: d.pct_visitante / 100, etiqueta: "Gana visitante", color: COLOR.visitante }])
      + (d.pct_favorito_gana != null ? `<p class="nota">El favorito de las casas de apuestas ganó el ${pct100(d.pct_favorito_gana)} de los partidos.</p>` : ""));
    html += tarjeta("Goles", barras([["Más de 1.5", d.pct_mas_1_5], ["Más de 2.5", d.pct_mas_2_5], ["Más de 3.5", d.pct_mas_3_5], ["Marcan ambos", d.pct_ambos_marcan], ["0-0", d.pct_0_0]]
      .map(([n, v]) => ({ nombre: n, valor: v })), { max: 100, fmt: (v) => pct100(v) }));
    html += tarjeta("Goles por partido", columnas(d.distribucion_goles.map((x) => String(x.goles)), [{ nombre: "Partidos", valores: d.distribucion_goles.map((x) => x.partidos), clase: "col-1" }], { fmt: (v) => Math.round(v) }));
    html += tarjeta("Marcadores más frecuentes", barras(d.marcadores.map((m) => ({ nombre: m.marcador, valor: m.veces })), { fmt: (v) => v })
      + `<p class="nota">Mayor goleada: ${esc(d.mayor_goleada.texto)} (${d.mayor_goleada.fecha})<br>Más goles: ${esc(d.mas_goles.texto)} (${d.mas_goles.fecha})</p>`);
    if (d.descanso) {
      const m = d.descanso.matriz, et = { 1: "Local", X: "Empate", 2: "Visitante" };
      html += tarjeta("Del descanso al final", `<div class="cifras">${cifra(num(d.descanso.goles_1t_pp), "Goles 1ª parte")}${cifra(num(d.descanso.goles_2t_pp), "Goles 2ª parte")}${cifra(d.descanso.remontadas, "Remontadas")}</div>
        <h3>Partidos según el resultado al descanso (filas) y al final (columnas)</h3>
        <table><thead><tr><th class="texto">Descanso</th>${"1X2".split("").map((f) => `<th>${et[f]}</th>`).join("")}</tr></thead>
        <tbody>${"1X2".split("").map((h) => `<tr><td class="texto">${et[h]}</td>${"1X2".split("").map((f) => `<td class="${h === f ? "fuerte" : ""}">${m[`${h}/${f}`]}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
    }
    if (d.juego.length) {
      html += tarjeta("Estadísticas de juego (media por partido)", tablaHTML("t-lj", [{ clave: "nombre", titulo: "", texto: true },
        { clave: "local", titulo: "Local", fmt: (v) => num(v) }, { clave: "visitante", titulo: "Visitante", fmt: (v) => num(v) }],
        d.juego.map((j) => ({ ...j, nombre: { tiros: "Tiros", tiros_puerta: "Tiros a puerta", corners: "Córners", faltas: "Faltas", amarillas: "Amarillas", rojas: "Rojas" }[j.nombre] || j.nombre }))));
    }
    return { html: html + "</div>" };
  },

  async h2h() {
    const lista = await equiposFutbol();
    const a = lista.includes(estado.p.a) ? estado.p.a : lista[0];
    const b = lista.includes(estado.p.b) && estado.p.b !== a ? estado.p.b : lista.find((e) => e !== a);
    const d = await api("futbol/h2h", { liga: estado.p.liga, torneo: estado.p.torneo, a, b });
    let html = `<div class="controles">${selector("c-a", "Equipo A", lista, a)}${selector("c-b", "Equipo B", lista, b)}</div>
      <h1 class="titulo-vista">${esc(d.a)} vs ${esc(d.b)}</h1><p class="descripcion">${d.n} enfrentamientos · ${esc(d.descripcion)}</p>`;
    if (!d.n) return { html: html + `<div class="error">No hay enfrentamientos entre estos equipos en los datos.</div>`, tras: h2hTras };
    html += `<div class="rejilla">` + tarjeta("Balance", barraProb([{ valor: d.victorias_a / d.n, etiqueta: `Gana ${d.a}`, color: COLOR.local },
      { valor: d.empates / d.n, etiqueta: "Empate", color: COLOR.empate }, { valor: d.victorias_b / d.n, etiqueta: `Gana ${d.b}`, color: COLOR.visitante }])
      + `<div class="cifras" style="margin-top:12px">${cifra(`${d.victorias_a}-${d.empates}-${d.victorias_b}`, "Victorias A - empates - victorias B")}${cifra(`${d.goles_a}-${d.goles_b}`, "Goles")}${cifra(pct100(d.ambos_marcan, 0), "Marcan ambos")}${cifra(pct100(d.mas_2_5, 0), "Más de 2.5 goles")}</div>`);
    html += tarjeta("Partidos", tablaHTML("t-h2h", [{ clave: "fecha", titulo: "Fecha", texto: true },
      { clave: "local", titulo: "Partido", texto: true, fmt: (v, f) => `${esc(f.local)} <b>${f.goles_local}-${f.goles_visitante}</b> ${esc(f.visitante)}${f.penaltis ? ` (penaltis: ${esc(f.penaltis)})` : ""}` }], d.partidos)) + "</div>";
    return { html, tras: h2hTras };
  },

  async ranking() {
    const d = await api("futbol/ranking", paramsFutbol());
    const cols = [{ clave: "pos", titulo: "#" }, { clave: "equipo", titulo: "Equipo", texto: true, fmt: (v) => `<span class="fuerte">${esc(v)}</span>` },
      { clave: "elo", titulo: "Elo", ordenable: true, fmt: (v) => num(v, 0) },
      { clave: "ataque", titulo: "Ataque", ordenable: true, fmt: (v) => num(v), ayuda: "1 = media de la liga; más es mejor" },
      { clave: "defensa", titulo: "Defensa", ordenable: true, fmt: (v) => num(v), ayuda: "1 = media; menos es mejor" },
      { clave: "dg", titulo: "DG esperada", ordenable: true, fmt: (v) => signo(v, 2), claseCelda: (f) => clase(f.dg), ayuda: "Diferencia de goles esperada por partido contra un rival medio" },
      { clave: "historial", titulo: "Tendencia Elo", fmt: (v) => chispa(v), oculta: true }];
    const filas = d.filas.map((f, i) => ({ ...f, pos: i + 1 }));
    return {
      html: `<h1 class="titulo-vista">Ranking de fuerza</h1><p class="descripcion">${esc(d.descripcion)} · haz clic en una columna para ordenar</p>${tarjeta("", tablaHTML("t-rank", cols, filas))}`,
      tras() { ordenarYRepintar("t-rank", cols, filas); },
    };
  },

  async goleadores() {
    const d = await api("futbol/goleadores", paramsFutbol({ n: 30 }));
    let html = `<h1 class="titulo-vista">Máximos goleadores</h1><p class="descripcion">${esc(d.descripcion)} · ${d.goles.toLocaleString("es")} goles con autor registrado</p><div class="rejilla">`;
    html += tarjeta("Goleadores", tablaHTML("t-gol", [{ clave: "pos", titulo: "#" }, { clave: "jugador", titulo: "Jugador", texto: true, fmt: (v) => `<span class="fuerte">${esc(v)}</span>` },
      { clave: "equipo", titulo: "Selección", texto: true }, { clave: "goles", titulo: "Goles" }, { clave: "penaltis", titulo: "Penaltis", oculta: true }, { clave: "partidos", titulo: "Partidos con gol", oculta: true }],
      d.filas.map((f, i) => ({ ...f, pos: i + 1 }))), "ancho");
    html += tarjeta("Goles por tramo de minutos", columnas(d.minutos.map((m) => m.tramo), [{ nombre: "Goles", valores: d.minutos.map((m) => m.goles), clase: "col-1" }], { fmt: (v) => Math.round(v) }));
    return { html: html + `</div><p class="nota">Los goles de amistosos están incompletos en la fuente.</p>` };
  },
};

function h2hTras() {
  $("#c-a").onchange = (e) => ir({}, { a: e.target.value });
  $("#c-b").onchange = (e) => ir({}, { b: e.target.value });
}

function ordenarYRepintar(id, cols, filas) {
  hacerOrdenable(id, cols, filas, (clave, dir) => {
    filas.forEach((f, i) => { if ("pos" in f) f.pos = i + 1; });
    const contenedor = document.getElementById(id).closest(".tabla-scroll");
    contenedor.outerHTML = tablaHTML(id, cols, filas);
    const th = document.querySelector(`#${id} th[data-clave="${clave}"]`);
    th.classList.add("ordenada");
    th.dataset.dir = dir;
    ordenarYRepintar(id, cols, filas);
  });
}

// ── Vistas de la NFL ────────────────────────────────────────────────────────
const nflTemp = () => estado.p.temporada || opciones.nfl.temporadas[0];
const equiposNFL = () => opciones.nfl.equipos.map((e) => ({ valor: e.codigo, texto: `${e.nombre} (${e.codigo})` }))
  .sort((a, b) => a.texto.localeCompare(b.texto));

const colsClasif = [
  { clave: "equipo", titulo: "Equipo", texto: true, fmt: (v, f) => `<span class="fuerte">${esc(v)}</span> <span class="ocultar-movil" style="color:var(--muted)">${esc(f.nombre)}</span>` },
  { clave: "g", titulo: "Récord", fmt: (v, f) => `${f.g}-${f.p}${f.e ? "-" + f.e : ""}` }, { clave: "pct", titulo: "PCT", fmt: (v) => num(v, 3) },
  { clave: "pf", titulo: "PF", oculta: true }, { clave: "pc", titulo: "PC", oculta: true },
  { clave: "dif", titulo: "DIF", fmt: (v) => signo(v, 0), claseCelda: (f) => clase(f.dif) },
  { clave: "local", titulo: "Local", oculta: true }, { clave: "visitante", titulo: "Visit.", oculta: true },
  { clave: "division", titulo: "Div.", oculta: true }, { clave: "conferencia", titulo: "Conf.", oculta: true },
  { clave: "racha", titulo: "Racha" }, { clave: "ultimos", titulo: "Últ. 5", texto: true, fmt: (v) => forma(v), oculta: true },
];

const vistasNFL = {
  async clasificacion() {
    const modo = estado.p.modo || "division";
    const d = await api("nfl/clasificacion", { temporada: nflTemp() });
    const filtro = selector("c-modo", "Vista", [{ valor: "division", texto: "Por divisiones" }, { valor: "playoffs", texto: "Puestos de playoffs" }], modo);
    let html = `<h1 class="titulo-vista">Clasificación ${d.temporada}</h1><div class="controles">${filtro}</div><div class="rejilla">`;
    const filasClic = [];
    if (modo === "playoffs") {
      d.playoffs.forEach((c) => {
        const filas = [...c.dentro, ...c.fuera];
        const cols = [{ clave: "siembra", titulo: "#", fmt: (v) => (v ? `${v}${v <= 4 ? "x" : "*"}` : "") }, ...colsClasif];
        html += tarjeta(c.conferencia, tablaHTML(`t-${c.conferencia}`, cols, filas, { clicable: true, corteTras: c.dentro.length }), "ancho");
        filasClic.push([`t-${c.conferencia}`, filas]);
      });
      html += `</div><p class="nota">x = campeón de división · * = comodín · línea discontinua = corte de playoffs. Desempates simplificados.</p>`;
    } else {
      d.divisiones.forEach((dv, i) => {
        html += tarjeta(dv.division, tablaHTML(`t-div${i}`, colsClasif.filter((c) => !["pf", "pc", "local", "visitante", "conferencia"].includes(c.clave)), dv.filas, { clicable: true }));
        filasClic.push([`t-div${i}`, dv.filas]);
      });
      html += `</div><p class="nota">Haz clic en un equipo para ver su informe. Desempates simplificados.</p>`;
    }
    return {
      html, tras() {
        $("#c-modo").onchange = (e) => ir({}, { modo: e.target.value });
        filasClic.forEach(([id, filas]) => document.querySelectorAll(`#${id} tbody tr`).forEach((tr) =>
          (tr.onclick = () => ir({ vista: "equipo" }, { equipo: filas[tr.dataset.i].equipo }))));
      },
    };
  },

  async equipo() {
    const equipo = estado.p.equipo || "KC";
    const d = await api("nfl/equipo", { temporada: nflTemp(), equipo });
    const r = d.registro;
    let html = `<div class="controles">${selector("c-equipo", "Equipo", equiposNFL(), d.equipo)}</div>
      <h1 class="titulo-vista">${esc(d.nombre)}</h1><p class="descripcion">${esc(d.division)} · temporada ${d.temporada}</p>
      <div class="cifras" style="margin-bottom:16px">${cifra(r.texto, "Récord (temporada regular)")}${cifra(`${num(r.pf_pp, 1)} / ${num(r.pc_pp, 1)}`, "Puntos a favor / en contra por partido")}
      ${cifra(signo(r.dif, 0), "Diferencia de puntos")}${cifra(`${num(r.pitagoricas, 1)} <span class="chip">${signo(r.reales - r.pitagoricas, 1)}</span>`, "Victorias pitagóricas (suerte)")}
      ${cifra(d.racha || "—", "Racha")}</div><div class="rejilla">`;
    html += tarjeta("Ratings", `<div class="cifras">${cifra(`${d.elo.rating} <span class="chip">${d.elo.puesto}º</span>`, "Elo")}${cifra(`${signo(d.srs.valor)} <span class="chip">${d.srs.puesto}º</span>`, "SRS (vs equipo medio)")}${cifra(signo(d.srs.ofensa), "Ofensa ajustada")}${cifra(signo(d.srs.defensa), "Defensa ajustada")}</div>`
      + (d.elo.historial.length > 1 ? `<h3>Evolución del Elo esta temporada</h3>` + linea(d.elo.historial.map((v, i) => ({ x: String(i + 1), y: v, tip: `Partido ${i + 1}: ${v}` })), { fmtY: (v) => Math.round(v) }) : ""));
    if (d.juego) {
      html += tarjeta("Estadísticas de juego (por partido)", tablaHTML("t-jn", [{ clave: "metrica", titulo: "", texto: true },
        { clave: "ataque", titulo: "Ataque", fmt: (v, f) => (f.metrica.includes("EPA") ? signo(v, 3) : num(v, 1)) }, { clave: "puesto_ataque", titulo: "Puesto", fmt: (v) => `${v}º` },
        { clave: "defensa", titulo: "Permite", fmt: (v, f) => (f.metrica.includes("EPA") ? signo(v, 3) : num(v, 1)) }, { clave: "puesto_defensa", titulo: "Puesto", fmt: (v) => `${v}º` }], d.juego.filas)
        + `<p class="nota">Sacks: ${d.juego.sacks} conseguidos y ${d.juego.sacks_recibidos} recibidos por partido · diferencial de pérdidas ${signo(d.juego.dif_perdidas, 0)} · goles de campo ${d.juego.fg}</p>`, "ancho");
    }
    if (d.proximos.length) {
      html += tarjeta("Próximos partidos", d.proximos.map((p) => `<p class="fuerte" style="margin:10px 0 0">Sem. ${p.semana} · ${p.local ? "vs" : "@"} ${esc(p.rival)} <span class="descripcion">· ${p.fecha} · margen esperado ${signo(p.margen)}</span></p>`
        + barraProb([{ valor: p.prob, etiqueta: d.equipo, color: COLOR.local }, { valor: 1 - p.prob, etiqueta: p.rival, color: COLOR.visitante }])).join(""));
    }
    html += tarjeta("Récords por situación", tablaHTML("t-spl", [{ clave: "situacion", titulo: "Situación", texto: true }, { clave: "texto", titulo: "Récord" },
      { clave: "pf_pp", titulo: "PF/p", fmt: (v) => num(v, 1), oculta: true }, { clave: "pc_pp", titulo: "PC/p", fmt: (v) => num(v, 1), oculta: true },
      { clave: "ats", titulo: "ATS", ayuda: "Contra el spread: cubre-no cubre-push" }, { clave: "ou", titulo: "O/U", ayuda: "Over-under del total" }], d.splits), "ancho");
    if (d.qbs.length) html += tarjeta("Récord por quarterback titular", tablaHTML("t-qb", [{ clave: "qb", titulo: "QB", texto: true }, { clave: "texto", titulo: "Récord" }, { clave: "pf_pp", titulo: "Pts/p", fmt: (v) => num(v, 1) }], d.qbs));
    html += tarjeta("Partido a partido", tablaHTML("t-pp", [{ clave: "semana", titulo: "Sem.", texto: true }, { clave: "fecha", titulo: "Fecha", texto: true, oculta: true },
      { clave: "rival", titulo: "Rival", texto: true, fmt: (v, f) => `${f.local ? "vs" : "@"} ${esc(v)}` }, { clave: "resultado", titulo: "", fmt: (v) => forma(v) },
      { clave: "pf", titulo: "Marcador", fmt: (v, f) => `${f.pf}-${f.pc}` }, { clave: "linea", titulo: "Línea", fmt: (v) => (v == null ? "" : signo(v, 1)), ayuda: "Negativa = favorito" },
      { clave: "ats", titulo: "ATS", fmt: (v) => esc(v || "") }, { clave: "total_linea", titulo: "Total", fmt: (v) => (v == null ? "" : v), oculta: true }, { clave: "ou", titulo: "O/U", fmt: (v) => esc(v || ""), oculta: true }], d.partidos), "ancho");
    return { html: html + "</div>", tras() { $("#c-equipo").onchange = (e) => ir({}, { equipo: e.target.value }); } };
  },

  async predecir() {
    const local = estado.p.local || "KC";
    const visitante = estado.p.visitante && estado.p.visitante !== local ? estado.p.visitante : (local === "BUF" ? "KC" : "BUF");
    const d = await api("nfl/predecir", { temporada: nflTemp(), local, visitante, neutral: estado.p.neutral, linea: estado.p.linea, total: estado.p.total });
    const fav = d.margen > 0 ? d.local : d.visitante;
    let html = `<div class="controles">${selector("c-local", "Local", equiposNFL(), d.local)}${selector("c-visit", "Visitante", equiposNFL(), d.visitante)}
      ${ESTATICO ? "" : `<div class="campo"><label for="c-linea">Línea del local</label><input id="c-linea" type="number" step="0.5" placeholder="p. ej. 3" value="${esc(estado.p.linea || "")}" style="width:110px"></div>
      <div class="campo"><label for="c-total">Total</label><input id="c-total" type="number" step="0.5" placeholder="p. ej. 47.5" value="${esc(estado.p.total || "")}" style="width:110px"></div>
      <label class="casilla"><input type="checkbox" id="c-neutral" ${estado.p.neutral ? "checked" : ""}> Campo neutral</label>`}</div>
      <h1 class="titulo-vista">${esc(d.nombre_visitante)} @ ${esc(d.nombre_local)}</h1>
      <p class="descripcion">${d.programado ? `Partido del calendario: semana ${d.programado.semana}, ${d.programado.fecha} (incluye descanso, QB titular y lesionados)` : "Partido hipotético"}</p><div class="rejilla">`;
    html += tarjeta("Probabilidad de victoria", barraProb([{ valor: d.prob_local, etiqueta: d.local, color: COLOR.local }, { valor: 1 - d.prob_local, etiqueta: d.visitante, color: COLOR.visitante }])
      + `<div class="cifras" style="margin-top:12px">${cifra(`${num(d.puntos_local, 1)} - ${num(d.puntos_visitante, 1)}`, `Marcador esperado (${d.local}-${d.visitante})`)}${cifra(`${esc(fav)} -${num(Math.abs(d.margen), 1)}`, "Spread del modelo")}${cifra(num(d.total, 1), "Total de puntos esperado")}</div>
      <p class="nota">Elo: ${signo(d.margen_elo)} · ratings: ${signo(d.margen_ratings)} (ventaja del local en puntos)</p>`
      + textoBajas(d.local, d.bajas_local) + textoBajas(d.visitante, d.bajas_visitante));
    if (d.linea != null || d.total_linea != null) {
      let m = "";
      if (d.linea != null) m += `<p>Mercado: <b>${d.linea > 0 ? d.local : d.visitante} -${Math.abs(d.linea)}</b> · diferencia con el modelo ${signo(d.margen - d.linea)} pts para el local</p>`
        + barraProb([{ valor: d.prob_cubre_local, etiqueta: `${d.local} cubre`, color: COLOR.local }, { valor: 1 - d.prob_cubre_local, etiqueta: `${d.visitante} cubre`, color: COLOR.visitante }]);
      if (d.total_linea != null) m += `<h3>Total ${d.total_linea}</h3>` + barraProb([{ valor: d.prob_over, etiqueta: "Over", color: COLOR.local }, { valor: 1 - d.prob_over, etiqueta: "Under", color: COLOR.visitante }]);
      html += tarjeta("Contra el mercado", m);
    }
    return {
      html: html + `</div><p class="nota">Combina Elo y ratings ajustados por rival, el QB titular y el parte oficial de lesionados (cuánto juega normalmente cada baja). No incluye el clima.</p>`,
      tras() {
        $("#c-local").onchange = (e) => ir({}, { local: e.target.value, linea: "", total: "" });
        $("#c-visit").onchange = (e) => ir({}, { visitante: e.target.value, linea: "", total: "" });
        $("#c-neutral")?.addEventListener("change", (e) => ir({}, { neutral: e.target.checked ? "1" : "" }));
        $("#c-linea")?.addEventListener("change", (e) => ir({}, { linea: e.target.value }));
        $("#c-total")?.addEventListener("change", (e) => ir({}, { total: e.target.value }));
      },
    };
  },

  async pronosticos() {
    const d = await api("nfl/pronosticos", { temporada: nflTemp(), semana: estado.p.semana });
    if (!d.filas.length) return { html: `<div class="error">No hay partidos pendientes en ${d.temporada}.</div>` };
    const html = `<div class="controles">${selector("c-sem", "Semana", d.semanas.map(String), d.semana)}</div>
      <h1 class="titulo-vista">Pronósticos · semana ${d.semana}</h1><p class="descripcion">Temporada ${d.temporada} · spreads desde el punto de vista del local (negativo = favorito)</p>
      ${tarjeta("", d.filas.map((p) => {
        const modelo = -p.margen, mercado = p.linea == null ? null : -p.linea;
        return `<div style="padding:10px 0;border-bottom:1px solid var(--grid)">
          <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><span class="fuerte">${esc(p.visitante)} @ ${esc(p.local)}</span>
          <span class="descripcion" style="margin:0">${p.fecha} · modelo ${signo(modelo)}${mercado != null ? ` · mercado ${signo(mercado)}` : ""} · total ${num(p.total, 1)}${p.total_linea != null ? ` (mercado ${p.total_linea})` : ""}</span></div>
          ${barraProb([{ valor: p.prob_local, etiqueta: p.local, color: COLOR.local }, { valor: 1 - p.prob_local, etiqueta: p.visitante, color: COLOR.visitante }])}
          ${textoBajas(p.visitante, p.bajas_visitante)}${textoBajas(p.local, p.bajas_local)}</div>`;
      }).join(""))}
      <p class="nota">Bajas: jugadores del parte oficial de lesionados (Out, Doubtful o en duda) y los puntos que cuesta cada uno, según cuánto juega normalmente. El parte de cada semana se publica unos días antes del partido.</p>`;
    return { html, tras() { $("#c-sem").onchange = (e) => ir({}, { semana: e.target.value }); } };
  },

  async simular() {
    const d = await api("nfl/simular", { temporada: nflTemp(), n: 5000 });
    let html = `<h1 class="titulo-vista">Probabilidades de playoffs ${d.temporada}</h1>
      <p class="descripcion">${d.simulaciones.toLocaleString("es")} simulaciones de los ${d.pendientes} partidos pendientes${d.pendientes ? "" : " (temporada regular completa)"}</p><div class="rejilla">`;
    d.conferencias.forEach((c) => {
      html += tarjeta(c.conferencia, barras(c.filas.map((f) => ({ nombre: f.nombre, valor: f.playoffs, texto: pct(f.playoffs, 0) })), { max: 1 })
        + tablaHTML(`t-sim-${c.conferencia}`, [{ clave: "equipo", titulo: "Equipo", texto: true }, { clave: "victorias", titulo: "Vict. esp.", fmt: (v) => num(v, 1) },
          { clave: "division", titulo: "Gana división", fmt: (v) => pct(v) }, { clave: "primero", titulo: "1º conferencia", fmt: (v) => pct(v) }], c.filas));
    });
    return { html: html + `</div><p class="nota">Desempates simplificados (victorias, récord divisional, sorteo).</p>` };
  },

  async ranking() {
    const d = await api("nfl/ranking", { temporada: nflTemp() });
    const filas = d.filas.map((f, i) => ({ ...f, pos: i + 1 }));
    const cols = [{ clave: "pos", titulo: "#" }, { clave: "nombre", titulo: "Equipo", texto: true, fmt: (v) => `<span class="fuerte">${esc(v)}</span>` },
      { clave: "registro", titulo: "Récord" }, { clave: "elo", titulo: "Elo", ordenable: true, fmt: (v) => num(v, 0) },
      { clave: "srs", titulo: "SRS", ordenable: true, fmt: (v) => signo(v), claseCelda: (f) => clase(f.srs), ayuda: "Margen esperado frente a un equipo medio" },
      { clave: "ofensa", titulo: "Ofensa", ordenable: true, fmt: (v) => signo(v), oculta: true }, { clave: "defensa", titulo: "Defensa", ordenable: true, fmt: (v) => signo(v), oculta: true },
      { clave: "pitagoricas", titulo: "Pitag.", ordenable: true, fmt: (v) => num(v, 1), oculta: true }, { clave: "historial", titulo: "Elo", fmt: (v) => chispa(v), oculta: true }];
    return {
      html: `<h1 class="titulo-vista">Power ranking ${d.temporada}</h1><p class="descripcion">Ventaja de campo estimada: ${signo(d.ventaja_campo)} pts · haz clic en una columna para ordenar</p>${tarjeta("", tablaHTML("t-nr", cols, filas))}`,
      tras() { ordenarYRepintar("t-nr", cols, filas); },
    };
  },

  async estadisticas() {
    const d = await api("nfl/estadisticas", { temporada: nflTemp() });
    const filas = d.filas.map((f, i) => ({ ...f, pos: i + 1 }));
    const o = (clave, titulo, fmt, ayuda, oculta = false) => ({ clave, titulo, fmt, ayuda, oculta, ordenable: true });
    const cols = [{ clave: "pos", titulo: "#" }, { clave: "equipo", titulo: "Eq.", texto: true, fmt: (v, f) => `<span class="fuerte" title="${esc(f.nombre)}">${esc(v)}</span>` },
      o("epa_of", "EPA/j of.", (v) => signo(v, 3), "Puntos esperados añadidos por jugada en ataque (más es mejor)"),
      o("epa_def", "EPA/j def.", (v) => signo(v, 3), "EPA por jugada que permite (menos es mejor)"),
      o("yardas", "Yds/p", (v) => num(v, 0)), o("yardas_permitidas", "Perm/p", (v) => num(v, 0)),
      o("dif_perdidas", "Dif. pérd.", (v) => signo(v, 0), "Pérdidas provocadas menos propias"),
      o("yardas_jugada", "Yds/jug", (v) => num(v, 2), "", true), o("sacks", "Sacks", (v) => num(v, 1), "", true),
      o("sacks_recibidos", "Sacks rec.", (v) => num(v, 1), "", true), o("pase", "Pase/p", (v) => num(v, 0), "", true),
      o("carrera", "Carrera/p", (v) => num(v, 0), "", true), o("explosivas", "20+/p", (v) => num(v, 1), "Jugadas de 20+ yardas", true),
      o("yardas_penalizacion", "Pen. yds", (v) => num(v, 0), "", true)];
    return {
      html: `<h1 class="titulo-vista">Estadísticas de juego ${d.temporada}</h1><p class="descripcion">Temporada regular, por partido · haz clic en una columna para ordenar</p>${tarjeta("", tablaHTML("t-est", cols, filas))}`,
      tras() { ordenarYRepintar("t-est", cols, filas); },
    };
  },

  async liga() {
    const d = await api("nfl/liga", { temporada: nflTemp() });
    let html = `<h1 class="titulo-vista">Resumen de la NFL ${d.temporada}</h1>
      <div class="cifras" style="margin-bottom:16px">${cifra(d.partidos, "Partidos")}${cifra(num(d.puntos_pp, 1), "Puntos por partido")}${cifra(signo(d.margen_local), "Margen medio del local")}${cifra(pct100(d.pct_prorroga), "Con prórroga")}</div><div class="rejilla">`;
    html += tarjeta("Resultados", barras([["Gana el local", d.pct_gana_local], ["Decididos por ≤8 puntos", d.pct_ajustados], ["Decididos por 17+ puntos", d.pct_palizas],
      ["Gana el favorito", d.pct_favorito_gana], ["El favorito cubre el spread", d.pct_favorito_cubre], ["Se supera el total (over)", d.pct_over]]
      .filter(([, v]) => v != null).map(([n, v]) => ({ nombre: n, valor: v })), { max: 100, fmt: (v) => pct100(v) }));
    if (d.factores.length) html += tarjeta("Qué decide los partidos", barras(d.factores.map((f) => ({ nombre: f.metrica, valor: f.pct })), { max: 100, fmt: (v) => pct100(v) })
      + `<p class="nota">% de partidos que gana el equipo que domina cada estadística.</p>`);
    html += tarjeta("Márgenes finales más frecuentes", columnas(d.margenes_frecuentes.map((m) => String(m.margen)), [{ nombre: "Partidos", valores: d.margenes_frecuentes.map((m) => m.partidos), clase: "col-1" }], { fmt: (v) => Math.round(v) })
      + `<p class="nota">Los "números clave" de la NFL: 3 (un gol de campo) y 7 (un touchdown).</p>`);
    html += tarjeta("Puntos según condiciones", barras(d.condiciones.map((c) => ({ nombre: `${c.condicion} (${c.partidos})`, valor: c.puntos })), { fmt: (v) => num(v, 1) })
      + `<p class="nota">Más puntos: ${esc(d.mas_puntos.texto)} · Menos: ${esc(d.menos_puntos.texto)} · Mayor paliza: ${esc(d.mayor_paliza.texto)}</p>`);
    return { html: html + "</div>" };
  },
};

// ── Vistas de la NBA ────────────────────────────────────────────────────────
const nbaTemp = () => estado.p.temporada || opciones.nba.temporadas[0].valor;
const equiposNBA = () => opciones.nba.equipos.map((e) => ({ valor: e.codigo, texto: `${e.nombre} (${e.codigo})` }))
  .sort((a, b) => a.texto.localeCompare(b.texto));
const textoBajas = (equipo, bajas) => (bajas?.length
  ? `<p class="nota" style="margin:4px 0 0">Bajas ${esc(equipo)}: ${bajas.map((b) => `${esc(b.nombre)} (${signo(b.puntos)})`).join(", ")}</p>` : "");
const avisoNBA = (d) => (d.aviso ? `<p class="nota">${esc(d.aviso)}</p>` : "");

const colsNBA = [
  { clave: "pos", titulo: "#", fmt: (v) => v ?? "" },
  { clave: "equipo", titulo: "Equipo", texto: true, fmt: (v, f) => `<span class="fuerte">${esc(v)}</span> <span class="ocultar-movil" style="color:var(--muted)">${esc(f.nombre)}</span>` },
  { clave: "g", titulo: "Récord", fmt: (v, f) => `${f.g}-${f.p}` }, { clave: "pct", titulo: "PCT", fmt: (v) => num(v, 3) },
  { clave: "pf_pp", titulo: "PF/p", fmt: (v) => num(v, 1), oculta: true }, { clave: "pc_pp", titulo: "PC/p", fmt: (v) => num(v, 1), oculta: true },
  { clave: "dif_pp", titulo: "DIF/p", fmt: (v) => signo(v), claseCelda: (f) => clase(f.dif_pp) },
  { clave: "local", titulo: "Local", oculta: true }, { clave: "visitante", titulo: "Visit.", oculta: true },
  { clave: "conferencia", titulo: "Conf.", oculta: true }, { clave: "racha", titulo: "Racha" },
  { clave: "ultimos", titulo: "Últ. 10", texto: true, fmt: (v) => forma(v), oculta: true },
];

const vistasNBA = {
  async clasificacion() {
    const modo = estado.p.modo || "conferencia";
    const d = await api("nba/clasificacion", { temporada: nbaTemp() });
    const filtro = selector("c-modo", "Vista", [{ valor: "conferencia", texto: "Por conferencias" }, { valor: "division", texto: "Por divisiones" }], modo);
    let html = `<h1 class="titulo-vista">Clasificación ${d.temporada}</h1><div class="controles">${filtro}</div><div class="rejilla">`;
    const filasClic = [];
    if (modo === "division") {
      d.divisiones.forEach((dv, i) => {
        html += tarjeta(dv.division, tablaHTML(`t-div${i}`, colsNBA.filter((c) => !["pos", "pf_pp", "pc_pp", "local", "visitante", "conferencia"].includes(c.clave)), dv.filas, { clicable: true }));
        filasClic.push([`t-div${i}`, dv.filas]);
      });
    } else {
      d.conferencias.forEach((c, i) => {
        html += tarjeta(c.conferencia, tablaHTML(`t-conf${i}`, colsNBA, c.filas, { clicable: true, corteTras: d.playin ? 6 : 8 }), "ancho");
        filasClic.push([`t-conf${i}`, c.filas]);
      });
    }
    html += `</div><p class="nota">${d.playin && modo !== "division" ? "1-6: playoffs directos · 7-10: play-in · " : ""}Haz clic en un equipo para ver su informe. Desempates simplificados.</p>`;
    return {
      html, tras() {
        $("#c-modo").onchange = (e) => ir({}, { modo: e.target.value });
        filasClic.forEach(([id, filas]) => document.querySelectorAll(`#${id} tbody tr`).forEach((tr) =>
          (tr.onclick = () => ir({ vista: "equipo" }, { equipo: filas[tr.dataset.i].equipo }))));
      },
    };
  },

  async equipo() {
    const equipo = estado.p.equipo || "LAL";
    const d = await api("nba/equipo", { temporada: nbaTemp(), equipo });
    const r = d.registro;
    let html = `<div class="controles">${selector("c-equipo", "Equipo", equiposNBA(), d.equipo)}</div>
      <h1 class="titulo-vista">${esc(d.nombre)}</h1><p class="descripcion">${esc(d.division)} · temporada ${d.temporada}</p>`;
    if (r.jugados) {
      html += `<div class="cifras" style="margin-bottom:16px">${cifra(`${r.texto}${r.puesto ? ` <span class="chip">${r.puesto}º conf.</span>` : ""}`, "Récord (temporada regular)")}${cifra(`${num(r.pf_pp, 1)} / ${num(r.pc_pp, 1)}`, "Puntos a favor / en contra por partido")}
        ${cifra(signo(r.dif_pp), "Diferencia por partido")}${cifra(`${num(r.pitagoricas, 1)} <span class="chip">${signo(r.reales - r.pitagoricas, 1)}</span>`, "Victorias pitagóricas (suerte)")}${cifra(d.racha || "—", "Racha")}</div>`;
    } else {
      html += `<p class="nota">Aún no ha jugado esta temporada: los ratings vienen de las temporadas anteriores.</p>`;
    }
    html += `<div class="rejilla">` + tarjeta("Ratings", `<div class="cifras">${cifra(`${d.elo.rating} <span class="chip">${d.elo.puesto}º</span>`, "Elo")}${cifra(`${signo(d.neto.valor)} <span class="chip">${d.neto.puesto}º</span>`, "Rating neto (vs equipo medio)")}${cifra(signo(d.neto.ataque), "Ataque")}${cifra(signo(d.neto.defensa), "Defensa")}</div>`
      + (d.elo.historial.length > 1 ? `<h3>Evolución del Elo esta temporada</h3>` + linea(d.elo.historial.map((v, i) => ({ x: String(i + 1), y: v, tip: `Partido ${i + 1}: ${v}` })), { fmtY: (v) => Math.round(v) }) : ""));
    if (d.proximos.length) {
      html += tarjeta("Próximos partidos", d.proximos.map((p) => `<p class="fuerte" style="margin:10px 0 0">${p.local ? "vs" : "@"} ${esc(p.rival)} <span class="descripcion">· ${p.fecha} · margen esperado ${signo(p.margen)}</span></p>`
        + barraProb([{ valor: p.prob, etiqueta: d.equipo, color: COLOR.local }, { valor: 1 - p.prob, etiqueta: p.rival, color: COLOR.visitante }])).join(""));
    }
    if (d.jugadores) {
      html += tarjeta("Jugadores de rotación", tablaHTML("t-jugb", [{ clave: "nombre", titulo: "Jugador", texto: true },
        { clave: "minutos", titulo: "Min.", fmt: (v) => num(v, 1) }, { clave: "valoracion", titulo: "Valoración/36", fmt: (v) => num(v, 1), ayuda: "Game Score de Hollinger cada 36 minutos (unos 10 es un titular normal)" },
        { clave: "jugo", titulo: "Último", texto: true, fmt: (v) => (v ? "jugó" : `<span class="negativo fuerte">no jugó</span>`) }], d.jugadores.filas)
        + `<p class="nota">Ajuste por plantilla para su próximo partido: ${signo(d.jugadores.ajuste)} puntos frente a lo habitual. Se supone que juegan los mismos que en el último partido (si fue hace menos de 60 días).</p>`);
    }
    if (d.juego) {
      const fmt = (v, f) => (f.metrica.includes("libres por") ? num(v, 2) : num(v, 1));
      html += tarjeta("Estadísticas de juego (temporada regular)", tablaHTML("t-jb", [{ clave: "metrica", titulo: "", texto: true },
        { clave: "ataque", titulo: "Equipo", fmt }, { clave: "puesto_ataque", titulo: "Puesto", fmt: (v) => `${v}º` },
        { clave: "defensa", titulo: "Rival", fmt }, { clave: "puesto_defensa", titulo: "Puesto", fmt: (v) => `${v}º` }], d.juego.filas)
        + `<p class="nota">Rating neto por 100 posesiones: ${signo(d.juego.neto)}. Rival = lo que permite (puesto 1 = el que menos concede).</p>`, "ancho");
    }
    if (d.splits.length) html += tarjeta("Récords por situación", tablaHTML("t-splb", [{ clave: "situacion", titulo: "Situación", texto: true }, { clave: "texto", titulo: "Récord" },
      { clave: "pf_pp", titulo: "PF/p", fmt: (v) => num(v, 1) }, { clave: "pc_pp", titulo: "PC/p", fmt: (v) => num(v, 1) }], d.splits));
    if (d.partidos.length) html += tarjeta("Partidos (del más reciente al más antiguo)", tablaHTML("t-ppb", [{ clave: "fecha", titulo: "Fecha", texto: true },
      { clave: "rival", titulo: "Rival", texto: true, fmt: (v, f) => `${f.local ? "vs" : "@"} ${esc(v)}` }, { clave: "resultado", titulo: "", fmt: (v) => forma(v === "V" ? "G" : "P") },
      { clave: "pf", titulo: "Marcador", fmt: (v, f) => `${f.pf}-${f.pc}${f.prorroga ? " (pró.)" : ""}` }, { clave: "fase", titulo: "Fase", texto: true, oculta: true }], d.partidos), "ancho");
    return { html: html + "</div>", tras() { $("#c-equipo").onchange = (e) => ir({}, { equipo: e.target.value }); } };
  },

  async predecir() {
    const local = estado.p.local || "BOS";
    const visitante = estado.p.visitante && estado.p.visitante !== local ? estado.p.visitante : (local === "LAL" ? "BOS" : "LAL");
    const d = await api("nba/predecir", { temporada: nbaTemp(), local, visitante, neutral: estado.p.neutral });
    const fav = d.margen > 0 ? d.local : d.visitante;
    let html = `<div class="controles">${selector("c-local", "Local", equiposNBA(), d.local)}${selector("c-visit", "Visitante", equiposNBA(), d.visitante)}
      ${ESTATICO ? "" : `<label class="casilla"><input type="checkbox" id="c-neutral" ${estado.p.neutral ? "checked" : ""}> Campo neutral</label>`}</div>
      <h1 class="titulo-vista">${esc(d.nombre_visitante)} @ ${esc(d.nombre_local)}</h1>
      <p class="descripcion">${d.programado ? `Partido del calendario: ${d.programado.fecha} (incluye el descanso de cada equipo)` : "Partido hipotético"}</p><div class="rejilla">`;
    html += tarjeta("Probabilidad de victoria", barraProb([{ valor: d.prob_local, etiqueta: d.local, color: COLOR.local }, { valor: 1 - d.prob_local, etiqueta: d.visitante, color: COLOR.visitante }])
      + `<div class="cifras" style="margin-top:12px">${cifra(`${num(d.puntos_local, 0)} - ${num(d.puntos_visitante, 0)}`, `Marcador esperado (${d.local}-${d.visitante})`)}${cifra(`${esc(fav)} -${num(Math.abs(d.margen), 1)}`, "Spread del modelo")}${cifra(num(d.total, 1), "Total de puntos esperado")}</div>
      <p class="nota">Elo: ${signo(d.margen_elo)} · ratings: ${signo(d.margen_ratings)} · descanso: ${signo(d.ajuste_descanso)} · jugadores: ${signo(d.ajuste_jugadores)} (ventaja del local en puntos) · moneyline justa ${esc(d.moneyline_local)} / ${esc(d.moneyline_visitante)}</p>`
      + textoBajas(d.local, d.bajas_local) + textoBajas(d.visitante, d.bajas_visitante));
    return {
      html: html + `</div><p class="nota">Combina Elo, ratings ajustados por rival, descanso y jugadores disponibles. Sin parte de lesionados, supone que cada equipo juega con los mismos que en su partido anterior.</p>`,
      tras() {
        $("#c-local").onchange = (e) => ir({}, { local: e.target.value });
        $("#c-visit").onchange = (e) => ir({}, { visitante: e.target.value });
        $("#c-neutral")?.addEventListener("change", (e) => ir({}, { neutral: e.target.checked ? "1" : "" }));
      },
    };
  },

  async pronosticos() {
    const d = await api("nba/pronosticos", { temporada: nbaTemp(), fecha: estado.p.fecha });
    if (!d.filas.length) return { html: `<div class="error">No hay partidos pendientes en ${d.temporada}.</div>` };
    const html = `<div class="controles">${selector("c-fecha", "Día", d.fechas, d.fecha)}</div>
      <h1 class="titulo-vista">Pronósticos · ${d.fecha}</h1><p class="descripcion">Temporada ${d.temporada} · spread desde el punto de vista del local (negativo = favorito)</p>
      ${tarjeta("", d.filas.map((p) => `<div style="padding:10px 0;border-bottom:1px solid var(--grid)">
          <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><span class="fuerte">${esc(p.visitante)} @ ${esc(p.local)}</span>
          <span class="descripcion" style="margin:0">spread ${signo(-p.margen)} · total ${num(p.total, 1)} · marcador ${num(p.puntos_visitante, 0)}-${num(p.puntos_local, 0)}${p.ajuste_descanso ? ` · ${p.ajuste_descanso < 0 ? "local" : "visitante"} en días seguidos` : ""}</span></div>
          ${barraProb([{ valor: p.prob_local, etiqueta: p.local, color: COLOR.local }, { valor: 1 - p.prob_local, etiqueta: p.visitante, color: COLOR.visitante }])}
          ${textoBajas(p.visitante, p.bajas_visitante)}${textoBajas(p.local, p.bajas_local)}</div>`).join(""))}
      <p class="nota">Bajas: jugadores importantes que no jugaron el último partido de su equipo (entre paréntesis, los puntos que vale cada uno); se supone que tampoco juegan este.</p>`;
    return { html, tras() { $("#c-fecha").onchange = (e) => ir({}, { fecha: e.target.value }); } };
  },

  async simular() {
    const d = await api("nba/simular", { temporada: nbaTemp(), n: 2000 });
    let html = `<h1 class="titulo-vista">Probabilidades de playoffs y de título ${d.temporada}</h1>
      <p class="descripcion">${d.simulaciones.toLocaleString("es")} simulaciones de los ${d.pendientes} partidos pendientes${d.pendientes ? "" : " (temporada regular completa)"}, del play-in y de los playoffs</p><div class="rejilla">`;
    d.conferencias.forEach((c) => {
      html += tarjeta(c.conferencia, barras(c.filas.map((f) => ({ nombre: f.nombre, valor: f.campeon, texto: pct(f.campeon) })), { max: Math.max(...d.conferencias.flatMap((x) => x.filas.map((f) => f.campeon)), 0.01) })
        + `<p class="nota">Probabilidad de ser campeón</p>`
        + tablaHTML(`t-simb-${c.conferencia}`, [{ clave: "equipo", titulo: "Equipo", texto: true }, { clave: "victorias", titulo: "Vict. esp.", fmt: (v) => num(v, 1) },
          { clave: "playoffs", titulo: "Playoffs", fmt: (v) => pct(v, 0) }, { clave: "top6", titulo: "Top 6", fmt: (v) => pct(v, 0), oculta: !d.playin },
          { clave: "primero", titulo: "1º conf.", fmt: (v) => pct(v), oculta: true }, { clave: "final", titulo: "Final", fmt: (v) => pct(v) }], c.filas));
    });
    return { html: html + `</div><p class="nota">"Playoffs" incluye pasar el play-in (puestos 7-10). Desempates simplificados; no tiene en cuenta lesiones ni traspasos futuros.</p>` };
  },

  async ranking() {
    const d = await api("nba/ranking", { temporada: nbaTemp() });
    const filas = d.filas.map((f, i) => ({ ...f, pos: i + 1 }));
    const cols = [{ clave: "pos", titulo: "#" }, { clave: "nombre", titulo: "Equipo", texto: true, fmt: (v) => `<span class="fuerte">${esc(v)}</span>` },
      { clave: "registro", titulo: "Récord" }, { clave: "elo", titulo: "Elo", ordenable: true, fmt: (v) => num(v, 0) },
      { clave: "neto", titulo: "Neto", ordenable: true, fmt: (v) => signo(v), claseCelda: (f) => clase(f.neto), ayuda: "Margen esperado frente a un equipo medio" },
      { clave: "ataque", titulo: "Ataque", ordenable: true, fmt: (v) => signo(v), oculta: true }, { clave: "defensa", titulo: "Defensa", ordenable: true, fmt: (v) => signo(v), oculta: true },
      { clave: "pitagoricas", titulo: "Pitag.", ordenable: true, fmt: (v) => (v == null ? "" : num(v, 1)), oculta: true }, { clave: "historial", titulo: "Elo", fmt: (v) => chispa(v), oculta: true }];
    return {
      html: `<h1 class="titulo-vista">Power ranking ${d.temporada}</h1><p class="descripcion">Ventaja de campo estimada: ${signo(d.ventaja_campo)} pts · haz clic en una columna para ordenar</p>${tarjeta("", tablaHTML("t-br", cols, filas))}`,
      tras() { ordenarYRepintar("t-br", cols, filas); },
    };
  },

  async estadisticas() {
    const d = await api("nba/estadisticas", { temporada: nbaTemp() });
    const filas = d.filas.map((f, i) => ({ ...f, pos: i + 1 }));
    const o = (clave, titulo, fmt, ayuda, oculta = false) => ({ clave, titulo, fmt, ayuda, oculta, ordenable: true });
    const cols = [{ clave: "pos", titulo: "#" }, { clave: "equipo", titulo: "Eq.", texto: true, fmt: (v, f) => `<span class="fuerte" title="${esc(f.nombre)}">${esc(v)}</span>` },
      o("neto", "Neto", (v) => signo(v), "Puntos de diferencia por 100 posesiones"),
      o("ataque", "Ataque", (v) => num(v, 1), "Puntos anotados por 100 posesiones"), o("defensa", "Defensa", (v) => num(v, 1), "Puntos permitidos por 100 posesiones (menos es mejor)"),
      o("ritmo", "Ritmo", (v) => num(v, 1), "Posesiones por partido"), o("efg", "eFG%", (v) => num(v, 1), "Acierto de tiro contando el triple como 1.5"),
      o("efg_rival", "eFG% rival", (v) => num(v, 1), "", true), o("perdidas", "% pérd.", (v) => num(v, 1), "Posesiones que acaban en pérdida", true),
      o("rebote_of", "% reb. of.", (v) => num(v, 1), "Rebotes ofensivos capturados", true), o("libres", "TL/TC", (v) => num(v, 3), "Tiros libres anotados por tiro de campo", true),
      o("pct_triple", "% triples", (v) => num(v, 1), "", true), o("tasa_triples", "Triples/tiros", (v) => num(v, 1), "% de tiros que son triples", true),
      o("asistencias", "Asist.", (v) => num(v, 1), "", true)];
    return {
      html: `<h1 class="titulo-vista">Estadísticas de juego ${d.temporada}</h1><p class="descripcion">Temporada regular · haz clic en una columna para ordenar</p>${avisoNBA(d)}${tarjeta("", tablaHTML("t-estb", cols, filas))}`,
      tras() { ordenarYRepintar("t-estb", cols, filas); },
    };
  },

  async liga() {
    const d = await api("nba/liga", { temporada: nbaTemp() });
    let html = `<h1 class="titulo-vista">Resumen de la NBA ${d.temporada}</h1>${avisoNBA(d)}
      <div class="cifras" style="margin-bottom:16px">${cifra(d.partidos, "Partidos")}${cifra(num(d.puntos_pp, 1), "Puntos por partido")}${cifra(signo(d.margen_local), "Margen medio del local")}${cifra(pct100(d.pct_prorroga), "Con prórroga")}</div><div class="rejilla">`;
    html += tarjeta("Resultados", barras([["Gana el local", d.pct_gana_local], ["Decididos por ≤5 puntos", d.pct_ajustados], ["Decididos por 15+ puntos", d.pct_palizas],
      ["Gana el que no jugó el día antes", d.pct_gana_descansado]].filter(([, v]) => v != null).map(([n, v]) => ({ nombre: n, valor: v })), { max: 100, fmt: (v) => pct100(v) }));
    if (d.factores.length) html += tarjeta("Qué decide los partidos", barras(d.factores.map((f) => ({ nombre: f.metrica, valor: f.pct })), { max: 100, fmt: (v) => pct100(v) })
      + `<p class="nota">% de partidos que gana el equipo que es mejor en cada estadística.</p>`);
    html += tarjeta("Márgenes finales más frecuentes", columnas(d.margenes_frecuentes.map((m) => String(m.margen)), [{ nombre: "Partidos", valores: d.margenes_frecuentes.map((m) => m.partidos), clase: "col-1" }], { fmt: (v) => Math.round(v) })
      + `<p class="nota">Más puntos: ${esc(d.mas_puntos.texto)} · Menos: ${esc(d.menos_puntos.texto)} · Mayor paliza: ${esc(d.mayor_paliza.texto)}</p>`);
    return { html: html + "</div>" };
  },
};

// ── Render principal ────────────────────────────────────────────────────────
let turno = 0;
async function render() {
  const mio = ++turno;
  const vista = $("#vista");
  try {
    if (!opciones[estado.deporte]) opciones[estado.deporte] = await api(`${estado.deporte}/opciones`);
    ({ futbol: controlesFutbol, nfl: controlesNFL, nba: controlesNBA })[estado.deporte]();
    pintarPestanas();
    vista.innerHTML = `<div class="cargando">Cargando…</div>`;
    const fn = ({ futbol: vistasFutbol, nfl: vistasNFL, nba: vistasNBA })[estado.deporte][estado.vista];
    const res = await fn();
    if (mio !== turno) return; // el usuario ya cambió de vista
    vista.innerHTML = res.html;
    res.tras?.();
  } catch (e) {
    if (mio === turno) vista.innerHTML = `<div class="error">${esc(e.message)}</div>`;
  }
}

document.querySelectorAll("[data-deporte]").forEach((b) => (b.onclick = () => {
  if (b.dataset.deporte === estado.deporte) return;
  estado = { deporte: b.dataset.deporte, vista: VISTAS[b.dataset.deporte][0][0], p: {} };
  escribirHash();
  render();
}));

$("#tema").onclick = () => {
  const oscuro = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
  const nuevo = oscuro ? "light" : "dark";
  document.documentElement.dataset.theme = nuevo;
  try { localStorage.setItem("tema", nuevo); } catch (e) { /* sin almacenamiento: solo esta sesión */ }
};

window.addEventListener("hashchange", () => { leerHash(); render(); });
leerHash();
render();
