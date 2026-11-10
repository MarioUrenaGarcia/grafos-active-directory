"""Generador del visor web interactivo.

Produce un unico archivo HTML autocontenido (sin servidor ni librerias) con la
misma interfaz que la aplicacion web. En lugar de pedir las trazas al servidor,
incrusta el grafo completo y un backend en JavaScript que responde las mismas
rutas /api/... en el navegador: subgrafo del objetivo, disposicion radial y las
trazas de BFS, Dijkstra y Edmonds-Karp, calculadas igual que en trazas.py.

El papel de Python aqui es preparar los datos en forma compacta; el calculo y la
reproduccion paso a paso viven en el cliente.
"""

from __future__ import annotations

import json

from .cortes import TIPOS_ESTRUCTURALES
from .interfaz_web import pagina
from .modelo import Grafo, OBJECTID_DOMAIN_ADMINS
from .pesos import PESOS_POR_TIPO, PESO_POR_OMISION


def _datos_compactos(grafo: Grafo) -> dict:
    """Serializa el grafo con indices enteros para reducir el tamanio."""
    ids = list(grafo.nodos)
    indice = {nid: i for i, nid in enumerate(ids)}
    nodos = []
    for nid in ids:
        n = grafo.nodos[nid]
        nodos.append([n.nombre, n.tipo, 1 if n.alto_valor else 0])
    aristas = [[indice[a.origen], indice[a.destino], a.tipo] for a in grafo.aristas]
    objetivos = [
        [indice[n.id], n.nombre]
        for n in grafo.altos_valores()
    ]
    # Posicion de cada identificador en orden lexicografico. Dijkstra en Python
    # desempata el monticulo por el identificador del nodo; el cliente usa este
    # rango para desempatar igual y producir la misma traza.
    rango = [0] * len(ids)
    for r, nid in enumerate(sorted(ids)):
        rango[indice[nid]] = r
    # El objetivo por omision es el grupo de administradores del dominio.
    da = grafo.buscar_por_objectid(OBJECTID_DOMAIN_ADMINS)
    objetivo_inicial = indice[da.id] if da else objetivos[0][0]
    return {
        "nodos": nodos,
        "aristas": aristas,
        "objetivos": objetivos,
        "objetivoInicial": objetivo_inicial,
        "rango": rango,
        "pesos": PESOS_POR_TIPO,
        "pesoOmision": PESO_POR_OMISION,
        "estructurales": sorted(TIPOS_ESTRUCTURALES),
    }


def generar_visor(grafo: Grafo) -> str:
    """Construye el HTML del visor y lo devuelve como texto."""
    datos = json.dumps(_datos_compactos(grafo), ensure_ascii=False)
    # "</" escapado como "<\/" sigue siendo JSON valido y evita que un nombre
    # con "</script>" cierre antes de tiempo el bloque de datos.
    datos = datos.replace("</", "<\\/")
    return pagina(_BACKEND_LOCAL.replace("/*__DATOS__*/", datos, 1))


# Backend en JavaScript que responde las rutas de servidor.py. Cada funcion
# sigue a su par en trazas.py, con el mismo orden de recorrido de las aristas,
# para que la pagina reciba las mismas trazas que con el servidor.
_BACKEND_LOCAL = r"""(function () {
"use strict";
const DATA = /*__DATOS__*/;
const N = DATA.nodos.length;
const salida = Array.from({ length: N }, () => []);
const entrada = Array.from({ length: N }, () => []);
for (const a of DATA.aristas) { salida[a[0]].push(a); entrada[a[1]].push(a); }
const ESTRUCTURALES = new Set(DATA.estructurales);
const INF = 1 << 30;
const propio = (obj, clave) => Object.prototype.hasOwnProperty.call(obj, clave);

class ErrorParametro extends Error {}

// Objetos que pueden alcanzar el objetivo, mas el objetivo (BFS en el grafo inverso).
function subgrafoObjetivo(t) {
  const vistos = new Set([t]), cola = [t];
  for (let q = 0; q < cola.length; q++) {
    for (const a of entrada[cola[q]]) {
      if (!vistos.has(a[0])) { vistos.add(a[0]); cola.push(a[0]); }
    }
  }
  return vistos;
}

// Arbol radial centrado en el objetivo: el radio es la distancia en saltos y el
// angulo se reparte segun el numero de hojas de cada subarbol.
function layoutRadial(t, permitidos) {
  const prof = new Map([[t, 0]]), hijos = new Map(), cola = [t];
  for (let q = 0; q < cola.length; q++) {
    const u = cola[q];
    for (const a of entrada[u]) {
      const v = a[0];
      if (permitidos.has(v) && !prof.has(v)) {
        prof.set(v, prof.get(u) + 1);
        if (!hijos.has(u)) hijos.set(u, []);
        hijos.get(u).push(v);
        cola.push(v);
      }
    }
  }
  const hojas = new Map();
  const contar = u => {
    const hs = hijos.get(u) || [];
    let total = hs.length ? 0 : 1;
    for (const h of hs) total += contar(h);
    hojas.set(u, total);
    return total;
  };
  contar(t);
  let profMax = 0;
  for (const p of prof.values()) profMax = Math.max(profMax, p);
  const paso = 360 / (profMax + 1);
  const pos = new Map(), pila = [[t, 0, 360]];
  while (pila.length) {
    const [u, a0, a1] = pila.pop();
    const rad = (a0 + a1) / 2 * Math.PI / 180, r = prof.get(u) * paso;
    pos.set(u, [Math.cos(rad) * r, Math.sin(rad) * r]);
    const hs = (hijos.get(u) || []).slice().sort((x, y) => hojas.get(y) - hojas.get(x));
    const total = hojas.get(u);
    let a = a0;
    for (const h of hs) {
      const frac = hojas.get(h) / total;
      pila.push([h, a, a + (a1 - a0) * frac]);
      a += (a1 - a0) * frac;
    }
  }
  return pos;
}

function grafoPayload(t) {
  const permitidos = subgrafoObjetivo(t);
  const pos = layoutRadial(t, permitidos);
  const redondear = x => Math.round(x * 100) / 100;
  const nodos = [], usuarios = [];
  for (let i = 0; i < N; i++) {
    if (!permitidos.has(i)) continue;
    const [nombre, tipo, hv] = DATA.nodos[i];
    const p = pos.get(i) || [0, 0];
    nodos.push({ i, nombre, tipo, hv, x: redondear(p[0]), y: redondear(p[1]) });
    if (tipo === "User") usuarios.push(i);
  }
  const aristas = DATA.aristas.filter(a => permitidos.has(a[0]) && permitidos.has(a[1]))
                              .map(a => [a[0], a[1], a[2]]);
  return { objetivo: t, objetivoNombre: DATA.nodos[t][0], nodos, aristas, usuarios,
           totalNodos: permitidos.size };
}

// Camino origen -> objetivo como lista de aristas, a partir de los previos.
function reconstruir(previo, o, t) {
  if (!previo.has(t)) return [];
  const camino = [];
  let actual = t;
  while (actual !== o) {
    const a = previo.get(actual);
    if (a === null) break;
    camino.push([a[0], a[1], a[2]]);
    actual = a[0];
  }
  return camino.reverse();
}

function bfsTraza(permitidos, o, t) {
  const visitados = new Set([o]), padre = new Map([[o, null]]), cola = [o], pasos = [];
  for (let q = 0; q < cola.length; q++) {
    const u = cola[q], descubre = [];
    for (const a of salida[u]) {
      const v = a[1];
      if (!permitidos.has(v) || visitados.has(v)) continue;
      visitados.add(v); padre.set(v, a); cola.push(v);
      descubre.push([u, v, a[2]]);
    }
    pasos.push({ nodo: u, descubre });
    if (visitados.has(t)) break;
  }
  const camino = reconstruir(padre, o, t);
  return { algoritmo: "bfs", pasos, camino, encontrado: visitados.has(t), saltos: camino.length };
}

// Monticulo binario de minimos; desempata por el rango del identificador, como
// las tuplas (distancia, id) de heapq en trazas.py.
class Monticulo {
  constructor() { this.d = []; }
  get size() { return this.d.length; }
  static menor(a, b) { return a[0] < b[0] || (a[0] === b[0] && DATA.rango[a[1]] < DATA.rango[b[1]]); }
  push(x) {
    const d = this.d;
    d.push(x);
    let i = d.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (!Monticulo.menor(d[i], d[p])) break;
      [d[i], d[p]] = [d[p], d[i]]; i = p;
    }
  }
  pop() {
    const d = this.d, cima = d[0], ultimo = d.pop();
    if (d.length) {
      d[0] = ultimo;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i;
        if (l < d.length && Monticulo.menor(d[l], d[m])) m = l;
        if (r < d.length && Monticulo.menor(d[r], d[m])) m = r;
        if (m === i) break;
        [d[i], d[m]] = [d[m], d[i]]; i = m;
      }
    }
    return cima;
  }
}

function dijkstraTraza(permitidos, o, t, pesos) {
  const peso = tipo => pesos && propio(pesos, tipo) ? pesos[tipo]
                     : (propio(DATA.pesos, tipo) ? DATA.pesos[tipo] : DATA.pesoOmision);
  const distancia = new Map([[o, 0]]), previo = new Map([[o, null]]);
  const cerrados = new Set(), pasos = [], monticulo = new Monticulo();
  monticulo.push([0, o]);
  while (monticulo.size) {
    const [d, u] = monticulo.pop();
    if (cerrados.has(u)) continue;
    cerrados.add(u);
    const relaja = [];
    for (const a of salida[u]) {
      const v = a[1];
      if (!permitidos.has(v)) continue;
      const nd = d + peso(a[2]);
      if (!distancia.has(v) || nd < distancia.get(v)) {
        distancia.set(v, nd); previo.set(v, a); monticulo.push([nd, v]);
        relaja.push([u, v, a[2], nd]);
      }
    }
    pasos.push({ nodo: u, dist: d, relaja });
    if (u === t) break;
  }
  const camino = reconstruir(previo, o, t);
  return { algoritmo: "dijkstra", pasos, camino, encontrado: distancia.has(t),
           peso: distancia.has(t) ? distancia.get(t) : null, saltos: camino.length };
}

// Edmonds-Karp con superfuente y supersumidero. Los accesos estructurales
// tienen capacidad infinita; el resto, una unidad por acceso revocable.
function defensaTraza(permitidos, t, fuentes) {
  const S = -1, T = -2;
  const revocables = new Map(), estructPar = new Set();
  for (const a of DATA.aristas) {
    if (!permitidos.has(a[0]) || !permitidos.has(a[1])) continue;
    const par = a[0] + "," + a[1];
    if (ESTRUCTURALES.has(a[2])) estructPar.add(par);
    else {
      if (!revocables.has(par)) revocables.set(par, []);
      revocables.get(par).push(a);
    }
  }
  const cap = new Map();
  const add = (u, v, c) => {
    if (!cap.has(u)) cap.set(u, new Map());
    if (!cap.get(u).has(v)) cap.get(u).set(v, 0);
    if (!cap.has(v)) cap.set(v, new Map());
    if (!cap.get(v).has(u)) cap.get(v).set(u, 0);
    cap.get(u).set(v, cap.get(u).get(v) + c);
  };
  const orig = new Map();
  for (const par of new Set([...revocables.keys(), ...estructPar])) {
    const [u, v] = par.split(",").map(Number);
    if (estructPar.has(par)) add(u, v, INF);
    else { const c = revocables.get(par).length; add(u, v, c); orig.set(par, c); }
  }
  for (const f of fuentes) if (permitidos.has(f) && f !== t) add(S, f, INF);
  add(t, T, INF);

  const caminos = [];
  for (;;) {
    const padre = new Map([[S, S]]), cola = [S];
    for (let q = 0; q < cola.length && !padre.has(T); q++) {
      const u = cola[q];
      for (const [v, c] of (cap.get(u) || [])) {
        if (c > 0 && !padre.has(v)) { padre.set(v, u); cola.push(v); }
      }
    }
    if (!padre.has(T)) break;
    const secuencia = [];
    let cuello = INF, v = T;
    while (v !== S) {
      const u = padre.get(v);
      cuello = Math.min(cuello, cap.get(u).get(v));
      secuencia.push(v); v = u;
    }
    secuencia.reverse();
    v = T;
    while (v !== S) {
      const u = padre.get(v);
      cap.get(u).set(v, cap.get(u).get(v) - cuello);
      cap.get(v).set(u, cap.get(v).get(u) + cuello);
      v = u;
    }
    caminos.push(secuencia.filter(n => n !== S && n !== T));
  }
  // Lado de la fuente en la red residual: define el corte minimo.
  const lado = new Set([S]), pend = [S];
  for (let q = 0; q < pend.length; q++) {
    for (const [v, c] of (cap.get(pend[q]) || [])) {
      if (c > 0 && !lado.has(v)) { lado.add(v); pend.push(v); }
    }
  }
  const corte = [], corteIds = new Set();
  for (const par of orig.keys()) {
    const [u, v] = par.split(",").map(Number);
    if (!lado.has(u) || lado.has(v)) continue;
    for (const a of revocables.get(par)) { corte.push([u, v, a[2]]); corteIds.add(u + "," + v + "," + a[2]); }
  }
  const antes = permitidos.size - 1;
  const seguros = segurosTrasCorte(permitidos, t, corteIds);
  return { algoritmo: "defensa", caminos, flujo: corte.length, nCaminos: caminos.length, corte,
           antes, despues: Math.max(antes - seguros.length, 0), seguros };
}

// Objetos del subgrafo que dejan de alcanzar el objetivo tras revocar el corte.
function segurosTrasCorte(permitidos, t, corteIds) {
  const alcanza = new Set([t]), cola = [t];
  for (let q = 0; q < cola.length; q++) {
    for (const a of entrada[cola[q]]) {
      const v = a[0];
      if (!permitidos.has(v) || corteIds.has(a[0] + "," + a[1] + "," + a[2])) continue;
      if (!alcanza.has(v)) { alcanza.add(v); cola.push(v); }
    }
  }
  const seguros = [];
  for (const i of permitidos) if (!alcanza.has(i) && i !== t) seguros.push(i);
  return seguros;
}

function fuentesDe(permitidos, modo) {
  const res = [];
  for (let i = 0; i < N; i++) {
    if (!permitidos.has(i)) continue;
    if (modo === "todos" ? !DATA.nodos[i][2] : DATA.nodos[i][1] === "User") res.push(i);
  }
  return res;
}

// Validacion de parametros equivalente a la del servidor.
function entero(params, clave) {
  const crudo = params.get(clave);
  if (crudo === null || crudo.trim() === "") throw new ErrorParametro("Falta el parámetro " + clave);
  if (!/^[+-]?\d+$/.test(crudo.trim())) throw new ErrorParametro("El parámetro " + clave + " no es un entero");
  const v = Number(crudo);
  if (v < 0 || v > N - 1) throw new ErrorParametro("El parámetro " + clave + " está fuera de rango");
  return v;
}
function pesosDe(params) {
  const crudo = params.get("pesos");
  if (!crudo) return null;
  let datos;
  try { datos = JSON.parse(crudo); } catch (e) { throw new ErrorParametro("El parámetro pesos no es JSON válido"); }
  if (datos === null || typeof datos !== "object" || Array.isArray(datos)) {
    throw new ErrorParametro("El parámetro pesos debe ser un objeto");
  }
  const limpio = Object.create(null);
  for (const [clave, valor] of Object.entries(datos)) {
    if (typeof valor !== "number" || !isFinite(valor) || valor < 0) {
      throw new ErrorParametro("Los pesos deben ser números no negativos");
    }
    limpio[clave] = Math.trunc(valor);
  }
  return limpio;
}

window.backendLocal = function (ruta) {
  const url = new URL(ruta, "http://visor.local/");
  const p = url.searchParams;
  try {
    switch (url.pathname) {
      case "/api/objetivos":
        return { objetivos: DATA.objetivos.map(([i, nombre]) => ({ i, nombre })),
                 porOmision: DATA.objetivoInicial };
      case "/api/grafo":
        return grafoPayload(entero(p, "objetivo"));
      case "/api/bfs":
      case "/api/dijkstra": {
        const t = entero(p, "objetivo"), o = entero(p, "origen");
        const permitidos = subgrafoObjetivo(t);
        if (!permitidos.has(o)) throw new ErrorParametro("El origen no alcanza el objetivo");
        return url.pathname === "/api/bfs" ? bfsTraza(permitidos, o, t)
                                           : dijkstraTraza(permitidos, o, t, pesosDe(p));
      }
      case "/api/defensa": {
        const t = entero(p, "objetivo");
        const modo = p.get("fuentes") === "todos" ? "todos" : "usuarios";
        const permitidos = subgrafoObjetivo(t);
        return defensaTraza(permitidos, t, fuentesDe(permitidos, modo));
      }
    }
    return { error: "ruta no encontrada" };
  } catch (e) {
    if (e instanceof ErrorParametro) return { error: e.message };
    throw e;
  }
};
})();"""


