/* Construccion de diagramas SVG para las animaciones de la presentacion.

   Todo el dibujo se crea una sola vez al cargar, a partir de datos fijos, y la
   linea de tiempo solo cambia atributos de elementos que ya existen. Asi cada
   fotograma depende unicamente del tiempo y el render es reproducible. */
(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";

  // Paleta de la aplicacion (DISENO.md).
  const C = {
    navy: "#11263f", navy8: "#17304f", navy6: "#33496b", azul: "#2e5aac",
    verde: "#1a7f43", rojo: "#c0392b", naranja: "#e67e22", morado: "#8e44ad",
    moradoClaro: "#b9a7d6", turquesa: "#16a085", gris: "#7f8c8d", ambar: "#ffd37a",
    fondo: "#e9edf4", texto: "#1b2430", tenue: "#7b8aa0", arista: "#c2ccda",
    borde: "#d5dce7", blanco: "#ffffff",
  };
  const COLOR_TIPO = {
    User: C.azul, Computer: C.turquesa, Group: C.morado, GPO: C.gris, OU: C.gris,
    Domain: C.gris, objetivo: C.rojo, hv: C.naranja,
  };

  // Contorno blanco detras del texto de las etiquetas: si una linea pasa por
  // detras, se interrumpe alrededor de las letras y la etiqueta sigue legible.
  const HALO = { "paint-order": "stroke", stroke: C.blanco, "stroke-width": 6, "stroke-linejoin": "round" };

  function el(tag, attrs, padre) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (padre) padre.appendChild(e);
    return e;
  }
  function texto(contenido, attrs, padre) {
    const t = el("text", attrs, padre);
    t.textContent = contenido;
    return t;
  }

  class Diagrama {
    constructor(svg) {
      this.svg = svg;
      this.fondo = el("g", {}, svg);
      this.capaAristas = el("g", {}, svg);
      this.capaNodos = el("g", {}, svg);
      this.capaEncima = el("g", {}, svg);
      this.nodos = {};
      this.aristas = {};
    }

    // Nodo: circulo que crece desde su radio 0 y una etiqueta debajo.
    nodo(id, x, y, o = {}) {
      const color = o.color || COLOR_TIPO[o.tipo] || C.gris;
      const r = o.r || 16;
      const g = el("g", { id }, this.capaNodos);
      const halo = el("circle", { cx: x, cy: y, r: 0, fill: color, opacity: 0.18 }, g);
      const c = el("circle", {
        cx: x, cy: y, r: 0,
        fill: o.hueco ? C.blanco : color,
        stroke: o.hueco ? color : C.blanco, "stroke-width": o.hueco ? 3.5 : 3,
      }, g);
      let etq = null;
      if (o.etiqueta) {
        const dy = o.etqArriba ? -(r + 14) : r + 26;
        etq = texto(o.etiqueta, {
          x: x + (o.etqDx || 0), y: y + dy, "text-anchor": o.etqAncla || "middle",
          class: o.etqClase || "etq", opacity: 0, ...HALO,
        }, g);
      }
      const n = { id, g, c, halo, etq, x, y, r, color };
      this.nodos[id] = n;
      return n;
    }

    // Arista dirigida de a hacia b, recta o curva, con su punta de flecha.
    arista(id, a, b, o = {}) {
      const A = this.nodos[a], B = this.nodos[b];
      const color = o.color || C.arista;
      const ancho = o.ancho || 3;
      const dx = B.x - A.x, dy = B.y - A.y, L = Math.hypot(dx, dy) || 1;
      const curva = o.curva || 0;
      // Punto de control desplazado en perpendicular para las curvas.
      const cx = (A.x + B.x) / 2 - dy / L * curva, cy = (A.y + B.y) / 2 + dx / L * curva;
      const ua = norm(cx - A.x, cy - A.y), ub = norm(B.x - cx, B.y - cy);
      const sx = A.x + ua[0] * (A.r + 5), sy = A.y + ua[1] * (A.r + 5);
      const fin = o.sinFlecha ? B.r + 5 : B.r + 9;
      const ex = B.x - ub[0] * fin, ey = B.y - ub[1] * fin;
      const d = curva ? `M${sx} ${sy} Q${cx} ${cy} ${ex} ${ey}` : `M${sx} ${sy} L${ex} ${ey}`;
      const g = el("g", { id }, o.encima ? this.capaEncima : this.capaAristas);
      const p = el("path", {
        d, fill: "none", stroke: color, "stroke-width": ancho, "stroke-linecap": "round",
      }, g);
      if (o.guion) p.setAttribute("data-guion", o.guion);
      const largo = p.getTotalLength();
      p.style.strokeDasharray = `${largo}`;
      p.style.strokeDashoffset = `${largo}`;
      p.style.opacity = 0;
      let flecha = null;
      if (!o.sinFlecha) {
        const t = 10 + ancho * 1.6, w = t * 0.55;
        const bx = ex - ub[0] * t, by = ey - ub[1] * t;
        flecha = el("polygon", {
          points: `${ex + ub[0] * 4},${ey + ub[1] * 4} ${bx - ub[1] * w},${by + ub[0] * w} ${bx + ub[1] * w},${by - ub[0] * w}`,
          fill: color, opacity: 0,
        }, g);
      }
      let etq = null;
      if (o.etiqueta) {
        const mx = curva ? 0.25 * sx + 0.5 * cx + 0.25 * ex : (sx + ex) / 2;
        const my = curva ? 0.25 * sy + 0.5 * cy + 0.25 * ey : (sy + ey) / 2;
        etq = texto(o.etiqueta, {
          x: mx, y: my, "text-anchor": "middle",
          class: o.etqClase || "etq-ar", opacity: 0, ...HALO,
        }, g);
        // La etiqueta se aleja de la arista en perpendicular lo suficiente para
        // que su caja no toque la linea: en una arista diagonal una etiqueta
        // ancha necesita mas distancia que en una horizontal.
        const nx = -dy / L, ny = dx / L, caja = etq.getBBox();
        const base = o.etqLado === undefined ? 18 : o.etqLado;
        const minimo = 8 + Math.abs(nx) * caja.width / 2 + Math.abs(ny) * caja.height / 2;
        const off = (base < 0 ? -1 : 1) * Math.max(Math.abs(base), minimo);
        etq.setAttribute("x", mx + nx * off);
        etq.setAttribute("y", my + ny * off + 5);
      }
      const ar = { id, g, p, flecha, etq, largo, color, a: A, b: B };
      this.aristas[id] = ar;
      return ar;
    }

    // Construye varios nodos y aristas desde tablas: [id, x, y, opciones].
    desde(nodos, aristas = []) {
      for (const [id, x, y, o] of nodos) this.nodo(id, x, y, o || {});
      for (const [id, a, b, o] of aristas) this.arista(id, a, b, o || {});
      return this;
    }

    // Caja con texto centrado (modulos, listas, mensajes). Empieza invisible.
    caja(id, x, y, w, h, o = {}) {
      const g = el("g", { id, opacity: 0 }, o.capa || this.capaNodos);
      const rect = el("rect", {
        x, y, width: w, height: h, rx: o.rx === undefined ? 12 : o.rx,
        fill: o.relleno || C.blanco, stroke: o.borde || C.borde, "stroke-width": o.grosor || 2,
      }, g);
      const lineas = [].concat(o.texto || []);
      const alto = o.altoLinea || 28;
      const y0 = y + h / 2 - (lineas.length - 1) * alto / 2 + (o.dyTexto || 8);
      const textos = lineas.map((linea, i) => texto(linea, {
        x: x + (o.alinear === "izq" ? 18 : w / 2), y: y0 + i * alto,
        "text-anchor": o.alinear === "izq" ? "start" : "middle",
        class: i === 0 ? (o.clase || "etq-caja") : (o.clase2 || o.clase || "etq-caja2"),
      }, g));
      if (o.tinta) textos.forEach(t => { t.style.fill = o.tinta; });
      return { id, g, rect, textos, x, y, w, h, cx: x + w / 2, cy: y + h / 2 };
    }

    // Trazo libre (una linea entre puntos) que se dibuja como una arista.
    trazo(id, d, o = {}) {
      const g = el("g", { id }, o.encima ? this.capaEncima : this.capaAristas);
      const p = el("path", {
        d, fill: "none", stroke: o.color || C.arista, "stroke-width": o.ancho || 3,
        "stroke-linecap": "round", "stroke-linejoin": "round",
      }, g);
      const largo = p.getTotalLength();
      p.style.strokeDasharray = `${largo}`;
      p.style.strokeDashoffset = `${largo}`;
      p.style.opacity = 0;
      return { id, g, p, largo, flecha: null, etq: null, color: o.color || C.arista };
    }

    // Ficha que puede recorrer un trazo (circulo con texto opcional).
    ficha(id, o = {}) {
      const g = el("g", { id, opacity: 0 }, this.capaEncima);
      if (o.ancho) {
        el("rect", { x: -o.ancho / 2, y: -17, width: o.ancho, height: 34, rx: 17, fill: o.color || C.ambar }, g);
      } else {
        el("circle", { r: o.r || 11, fill: o.color || C.ambar, stroke: C.blanco, "stroke-width": 3 }, g);
      }
      if (o.texto) texto(o.texto, { y: 7, "text-anchor": "middle", class: o.clase || "etq-ficha" }, g);
      return g;
    }
  }

  function norm(x, y) { const l = Math.hypot(x, y) || 1; return [x / l, y / l]; }

  // ---------------------------------------------------------------------
  // Movimientos reutilizables sobre una linea de tiempo
  // ---------------------------------------------------------------------
  const M = {
    // El nodo crece desde su centro con un rebote suave; su etiqueta aparece despues.
    aparecer(tl, n, t, o = {}) {
      tl.fromTo(n.c, { attr: { r: 0 } }, { attr: { r: n.r }, duration: o.dur || 0.55, ease: "back.out(1.7)" }, t);
      if (n.etq) tl.fromTo(n.etq, { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "power2.out" }, t + 0.2);
      return t;
    },
    // La arista se traza desde su origen y la punta aparece al llegar.
    trazar(tl, a, t, o = {}) {
      const dur = o.dur || 0.6;
      tl.fromTo(a.p, { opacity: 0 }, { opacity: o.opacidad || 1, duration: 0.01 }, t);
      tl.fromTo(a.p, { strokeDashoffset: a.largo }, { strokeDashoffset: 0, duration: dur, ease: o.ease || "power2.inOut" }, t);
      if (a.flecha) tl.fromTo(a.flecha, { opacity: 0 }, { opacity: 1, duration: 0.15 }, t + dur * 0.85);
      if (a.etq) tl.fromTo(a.etq, { opacity: 0 }, { opacity: 1, duration: 0.3 }, t + dur * 0.6);
      return t + dur;
    },
    // Cambia el color de una arista ya trazada (resaltar un camino o un corte).
    colorArista(tl, a, color, t, o = {}) {
      const dur = o.dur || 0.35;
      tl.to(a.p, { stroke: color, strokeWidth: o.ancho || 5, duration: dur, ease: "power2.out" }, t);
      if (a.flecha) tl.to(a.flecha, { fill: color, duration: dur }, t);
      return t + dur;
    },
    // Cambia el relleno de un nodo, con un destello del halo.
    colorNodo(tl, n, color, t, o = {}) {
      tl.to(n.c, { fill: color, duration: o.dur || 0.35, ease: "power2.out" }, t);
      M.destello(tl, n, t, color);
      return t;
    },
    // Halo que se abre y se desvanece una vez (marca el nodo activo de un paso).
    // Su estado inicial es invisible, asi no se ve antes de tiempo al buscar.
    destello(tl, n, t, color) {
      if (color) tl.set(n.halo, { attr: { fill: color } }, t);
      tl.fromTo(n.halo, { attr: { r: n.r }, opacity: 0 },
        { attr: { r: n.r * 1.25 }, opacity: 0.4, duration: 0.08, ease: "none" }, t);
      tl.to(n.halo, { attr: { r: n.r * 2.6 }, opacity: 0, duration: 0.75, ease: "expo.out" }, t + 0.08);
      return t;
    },
    // Una ficha recorre un trazo de principio a fin (un mensaje, un token, un flujo).
    viajar(tl, ficha, trazo, t, dur = 0.9, o = {}) {
      const largo = trazo.getTotalLength();
      const prox = { k: 0 };
      const poner = () => {
        const p = trazo.getPointAtLength(largo * prox.k);
        ficha.setAttribute("transform", `translate(${p.x} ${p.y})`);
      };
      tl.fromTo(ficha, { opacity: 0 }, { opacity: 1, duration: 0.12 }, t);
      tl.fromTo(prox, { k: 0 }, { k: 1, duration: dur, ease: o.ease || "power1.inOut", onUpdate: poner }, t);
      if (!o.quedarse) tl.to(ficha, { opacity: 0, duration: 0.15 }, t + dur);
      return t + dur;
    },
    // Aparicion de una caja o grupo: escala desde 0.85 y opacidad.
    caja(tl, g, t, o = {}) {
      tl.fromTo(g, { opacity: 0, scale: 0.85, transformOrigin: "50% 50%" },
        { opacity: 1, scale: 1, duration: o.dur || 0.45, ease: o.ease || "expo.out" }, t);
      return t + (o.dur || 0.45);
    },
    // Aparicion de un elemento cualquiera (rectangulo, grupo) por opacidad.
    mostrar(tl, elemento, t, dur = 0.35) {
      tl.fromTo(elemento, { opacity: 0 }, { opacity: 1, duration: dur, ease: "power2.out" }, t);
      return t + dur;
    },
    ocultar(tl, elemento, t, dur = 0.25) {
      tl.to(elemento, { opacity: 0, duration: dur, ease: "power2.in" }, t);
      return t + dur;
    },
  };

  window.Diagrama = Diagrama;
  window.Mov = M;
  window.PALETA = C;
  window.COLOR_TIPO = COLOR_TIPO;
  window.svgEl = el;
  window.svgTexto = texto;
})();
