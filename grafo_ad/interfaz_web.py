"""Pagina unica de la aplicacion web (HTML, CSS y JavaScript).

La define como una constante de texto que el servidor entrega en la raiz. La
pagina pide al backend la traza de cada algoritmo y la reproduce paso a paso
sobre el grafo, con controles de reproduccion y ajustes.

La misma pagina sirve al visor offline: pagina() admite un script que define
window.backendLocal, una funcion que responde las rutas /api/... sin red. Si
existe, la pagina la usa en lugar de pedir los datos al servidor.
"""

import base64
from pathlib import Path
from urllib.parse import quote

_MARCA_BACKEND = "<!--__BACKEND_LOCAL__-->"
_MARCA_FUENTE = "/*__BEBAS_NEUE__*/"
_MARCA_ICONOS = "<!--__ICONOS__-->"
_MARCA_FAVICON = "__FAVICON__"

# Iconos propios de la herramienta. Todos se construyen con el lenguaje del
# grafo: nodos (circulos llenos) unidos por aristas (trazos de 1.9 con puntas
# redondeadas) sobre una reticula de 24 x 24, y toman el color del texto.
_TRAZO = ('<g fill="none" stroke="currentColor" stroke-width="1.9" '
          'stroke-linecap="round" stroke-linejoin="round">')
_NODOS = '<g fill="currentColor">'

ICONOS = {
    "bfs": ("Ruta más corta (BFS): un nodo y su primer nivel de vecinos",
            _TRAZO + '<path d="M12 12V5.2M12 12l5.9 3.4M12 12l-5.9 3.4"/>'
            '<circle cx="12" cy="12" r="9.4" stroke-width="1.3" stroke-dasharray="1.4 2.6"/></g>'
            + _NODOS + '<circle cx="12" cy="12" r="2.6"/><circle cx="12" cy="5.2" r="1.9"/>'
            '<circle cx="17.9" cy="15.4" r="1.9"/><circle cx="6.1" cy="15.4" r="1.9"/></g>'),
    "dijkstra": ("Ruta de menor esfuerzo (Dijkstra): tramos de distinto peso",
                 _TRAZO + '<path d="M4.5 18.5 10 8.5" stroke-width="3"/><path d="M10 8.5l5 6.5" stroke-width="1.2"/>'
                 '<path d="M15 15l4.5-9.5" stroke-width="2"/></g>'
                 + _NODOS + '<circle cx="4.5" cy="18.5" r="2.3"/><circle cx="10" cy="8.5" r="2"/>'
                 '<circle cx="15" cy="15" r="2"/><circle cx="19.5" cy="5.5" r="2.3"/></g>'),
    "defensa": ("Plan de defensa: un corte interrumpe los accesos hacia el objetivo",
                _TRAZO + '<path d="M4.5 6.5 9.9 8.85M13.1 10.25l2.2.95M4.5 17.5l6.3-2.74M13.9 13.4l1.4-.6"/>'
                '<circle cx="18.5" cy="12" r="3.2"/><path d="M10.5 3.5l3 17" stroke-width="2.4"/></g>'
                + _NODOS + '<circle cx="4.5" cy="6.5" r="2"/><circle cx="4.5" cy="17.5" r="2"/>'
                '<circle cx="18.5" cy="12" r="1.2"/></g>'),
    "ejecutar": ("Ejecutar: el origen lanza la exploración hacia sus vecinos",
                 _TRAZO + '<path d="M5 12l13.5-6M5 12h14.5M5 12l13.5 6"/></g>'
                 + _NODOS + '<circle cx="5" cy="12" r="2.6"/><circle cx="18.5" cy="6" r="1.8"/>'
                 '<circle cx="19.5" cy="12" r="1.8"/><circle cx="18.5" cy="18" r="1.8"/></g>'),
    "buscar": ("Buscar: mira que fija un nodo",
               _TRAZO + '<circle cx="12" cy="12" r="6.5"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3"/></g>'
               + _NODOS + '<circle cx="12" cy="12" r="2.2"/></g>'),
    "panel": ("Mostrar u ocultar el panel: columna con los pasos",
              _TRAZO + '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M9.5 4v16"/></g>'
              + _NODOS + '<circle cx="6.25" cy="8.5" r="1.2"/><circle cx="6.25" cy="12" r="1.2"/>'
              '<circle cx="6.25" cy="15.5" r="1.2"/></g>'),
    "atajos": ("Atajos de teclado: tecla con una hilera de nodos",
               _TRAZO + '<rect x="2.5" y="6" width="19" height="12" rx="2.5"/><path d="M7 12h10"/></g>'
               + _NODOS + '<circle cx="7" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/>'
               '<circle cx="17" cy="12" r="1.6"/></g>'),
    "acercar": ("Acercar: estrella de cuatro aristas en forma de más",
                _TRAZO + '<path d="M12 4.5v15M4.5 12h15"/></g>'
                + _NODOS + '<circle cx="12" cy="12" r="2.6"/><circle cx="12" cy="4.5" r="1.7"/>'
                '<circle cx="12" cy="19.5" r="1.7"/><circle cx="4.5" cy="12" r="1.7"/>'
                '<circle cx="19.5" cy="12" r="1.7"/></g>'),
    "alejar": ("Alejar: una sola arista en forma de menos",
               _TRAZO + '<path d="M5 12h14"/></g>'
               + _NODOS + '<circle cx="5" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></g>'),
    "ajustar": ("Ajustar a la vista: un grafo pequeño entre esquinas",
                _TRAZO + '<path d="M3.5 8.5v-5h5M15.5 3.5h5v5M20.5 15.5v5h-5M8.5 20.5h-5v-5M12 8.5l-3.5 6.5h7z"/></g>'
                + _NODOS + '<circle cx="12" cy="8.5" r="1.6"/><circle cx="8.5" cy="15" r="1.6"/>'
                '<circle cx="15.5" cy="15" r="1.6"/></g>'),
    "cerrar": ("Cerrar o quitar: dos aristas cruzadas",
               _TRAZO + '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/></g>'
               + _NODOS + '<circle cx="6.5" cy="6.5" r="1.8"/><circle cx="17.5" cy="17.5" r="1.8"/>'
               '<circle cx="17.5" cy="6.5" r="1.8"/><circle cx="6.5" cy="17.5" r="1.8"/></g>'),
    "chevron": ("Desplegar: dos aristas que se unen en un nodo",
                _TRAZO + '<path d="M5.5 9l6.5 6.5L18.5 9"/></g>'
                + _NODOS + '<circle cx="12" cy="15.5" r="2"/></g>'),
    "reproducir": ("Reproducir: triángulo de tres nodos",
                   _TRAZO + '<path d="M8 5.5 18 12 8 18.5z"/></g>'
                   + _NODOS + '<circle cx="8" cy="5.5" r="2.3"/><circle cx="8" cy="18.5" r="2.3"/>'
                   '<circle cx="18" cy="12" r="2.3"/></g>'),
    "pausa": ("Pausa: dos aristas verticales",
              _TRAZO + '<path d="M8.5 6.5v11M15.5 6.5v11" stroke-width="2.4"/></g>'
              + _NODOS + '<circle cx="8.5" cy="6.5" r="2.2"/><circle cx="8.5" cy="17.5" r="2.2"/>'
              '<circle cx="15.5" cy="6.5" r="2.2"/><circle cx="15.5" cy="17.5" r="2.2"/></g>'),
    "siguiente": ("Paso siguiente: un nodo que avanza por su arista",
                  _TRAZO + '<path d="M7.5 12H18M13.5 7.5 18 12l-4.5 4.5"/></g>'
                  + _NODOS + '<circle cx="5.5" cy="12" r="2.3"/></g>'),
    "anterior": ("Paso anterior: el mismo recorrido en sentido inverso",
                 _TRAZO + '<path d="M16.5 12H6M10.5 7.5 6 12l4.5 4.5"/></g>'
                 + _NODOS + '<circle cx="18.5" cy="12" r="2.3"/></g>'),
    "inicio": ("Ir al inicio: retroceso hasta el primer nivel",
               _TRAZO + '<path d="M5.5 6v12M17.5 7 11 12l6.5 5"/></g>'
               + _NODOS + '<circle cx="5.5" cy="6" r="1.7"/><circle cx="5.5" cy="18" r="1.7"/>'
               '<circle cx="11" cy="12" r="2"/></g>'),
    "fin": ("Ir al resultado: avance hasta el último nivel",
            _TRAZO + '<path d="M18.5 6v12M6.5 7 13 12l-6.5 5"/></g>'
            + _NODOS + '<circle cx="18.5" cy="6" r="1.7"/><circle cx="18.5" cy="18" r="1.7"/>'
            '<circle cx="13" cy="12" r="2"/></g>'),
}

# Logo: tres objetos con accesos hacia un objetivo (diana roja) y el corte
# minimo (barra ambar) que los interrumpe. Reticula de 48 x 48.
LOGO = (
    '<rect width="48" height="48" rx="12" fill="#2e5aac"/>'
    '<g fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round">'
    '<path d="M13 14l4.6 2.09M21.6 17.91l6.1 2.79M11 24h7.8M23.2 24h3.8'
    'M13 34l7.17-3.26M24.17 28.92l3.53-1.62"/></g>'
    '<path d="M18.6 12l4.8 24" stroke="#ffd37a" stroke-width="3.2" stroke-linecap="round"/>'
    '<g fill="#fff"><circle cx="13" cy="14" r="3"/><circle cx="11" cy="24" r="3"/>'
    '<circle cx="13" cy="34" r="3"/></g>'
    '<circle cx="35" cy="24" r="6.5" fill="#c0392b" stroke="#fff" stroke-width="2.5"/>'
    '<circle cx="35" cy="24" r="2" fill="#fff"/>'
)


def logo_svg() -> str:
    """Logo como documento SVG independiente."""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">{LOGO}</svg>'


def _sprite() -> str:
    """Simbolos SVG de los iconos y el logo, referenciados con <use>."""
    simbolos = "".join(f'<symbol id="ic-{nombre}" viewBox="0 0 24 24">{interior}</symbol>'
                       for nombre, (_, interior) in ICONOS.items())
    simbolos += f'<symbol id="ic-logo" viewBox="0 0 48 48">{LOGO}</symbol>'
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" aria-hidden="true" '
            f'style="position:absolute">{simbolos}</svg>')

# Fuente de los titulos (Bebas Neue, SIL Open Font License 1.1). Se incrusta en
# la pagina para que se vea igual sin internet y sin tenerla instalada.
_RUTA_FUENTE = Path(__file__).resolve().parent / "recursos" / "BebasNeue-Regular.ttf"


def pagina(script_local: str = "") -> str:
    """Devuelve la pagina, con un script de backend local opcional incrustado."""
    fuente = base64.b64encode(_RUTA_FUENTE.read_bytes()).decode("ascii")
    favicon = "data:image/svg+xml," + quote(logo_svg())
    bloque = f"<script>\n{script_local}\n</script>" if script_local else ""
    return (_PLANTILLA.replace(_MARCA_FUENTE, fuente, 1)
                      .replace(_MARCA_FAVICON, favicon, 1)
                      .replace(_MARCA_ICONOS, _sprite(), 1)
                      .replace(_MARCA_BACKEND, bloque, 1))


_PLANTILLA = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Analizador de rutas de acceso y defensa</title>
<link rel="icon" href="__FAVICON__">
<style>
  /* Bebas Neue (Dharma Type, SIL Open Font License 1.1) para titulos y cifras.
     La licencia acompania al archivo en grafo_ad/recursos/OFL-BebasNeue.txt. */
  @font-face { font-family: "Bebas Neue"; font-style: normal; font-weight: 400; font-display: swap;
               src: url(data:font/ttf;base64,/*__BEBAS_NEUE__*/) format("truetype"); }

  /* Paleta original de la aplicacion expresada como variables, para que cada
     componente reutilice los mismos tonos sin repetir valores sueltos. */
  :root {
    color-scheme: light;
    /* Tipografia: Bebas Neue en titulos y cifras, Bahnschrift (incluida en
       Windows) en el texto y una monoespaciada para los tipos de acceso. */
    --f-titulo: "Bebas Neue", "Bahnschrift Condensed", "Arial Narrow", sans-serif;
    --f-texto: Bahnschrift, "DIN Alternate", "Segoe UI", system-ui, sans-serif;
    --f-mono: ui-monospace, Consolas, "Cascadia Mono", monospace;
    --navy-900: #11263f;   /* barra lateral */
    --navy-800: #17304f;   /* paneles */
    --navy-700: #1c3350;   /* campos */
    --navy-600: #33496b;   /* bordes y controles */
    --navy-500: #3d567f;   /* hover de controles */
    --azul: #2e5aac;   --azul-osc: #274d93;
    --verde: #1a7f43;  --verde-osc: #166e39;
    --rojo: #c0392b;   --naranja: #e67e22;
    --morado: #8e44ad; --morado-claro: #b9a7d6;
    --turquesa: #16a085; --gris: #7f8c8d;
    --ambar: #ffd37a;  --enlace: #8fb4ee;
    --fondo: #e9edf4;  --texto: #1b2430; --texto-claro: #e8edf5;
    --texto-tenue: #9fb0c7; --arista: #c2ccda;
    --radio: 10px; --radio-sm: 7px;
    --suave: cubic-bezier(.2, .7, .2, 1);
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body { margin: 0; font: 13px/1.5 var(--f-texto);
         color: var(--texto); background: var(--fondo); overflow: hidden;
         -webkit-font-smoothing: antialiased; }
  /* El panel se pliega con un margen negativo: su contenido conserva el ancho
     y no se reacomoda durante la animacion. */
  #app { display: flex; height: 100vh; overflow: hidden; }
  aside { flex: none; width: 340px; background: var(--navy-900); color: var(--texto-claro);
          padding: 20px 20px 24px; overflow-y: auto; scrollbar-width: thin;
          scrollbar-color: var(--navy-600) transparent; transition: margin-left .35s var(--suave); }
  #app.sin-panel aside { margin-left: -340px; }
  aside h1 { font: 400 25px/1 var(--f-titulo); letter-spacing: .03em; margin: 0 0 4px; }
  aside .sub { font-size: 12px; color: var(--texto-tenue); margin-bottom: 18px; line-height: 1.5; }
  aside h2 { font: 400 15px/1 var(--f-titulo); letter-spacing: .08em; color: #8094ae; margin: 22px 0 9px; }
  label { font-size: 12.5px; display: block; margin-bottom: 6px; color: #c3cfdf; }
  select, button, input { font: inherit; border-radius: var(--radio-sm); }
  :focus-visible { outline: 2px solid var(--enlace); outline-offset: 2px; }
  select { appearance: none; -webkit-appearance: none; width: 100%; cursor: pointer;
           padding: 9px 34px 9px 11px; color: #fff; border: 1px solid var(--navy-600);
           background: var(--navy-700) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2.8 4.5 6 7.8l3.2-3.3' fill='none' stroke='%238fb4ee' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3Ccircle cx='6' cy='7.8' r='1.3' fill='%238fb4ee'/%3E%3C/svg%3E") no-repeat right 12px center;
           transition: border-color .15s, background-color .15s; }
  select:hover { border-color: var(--navy-500); }
  select option { background: var(--navy-700); }
  button { padding: 9px 12px; border: 0; cursor: pointer; font-weight: 600; color: #fff;
           transition: background-color .15s, color .15s, opacity .15s, transform .1s; }
  button:active:not(:disabled) { transform: scale(.97); }
  button:disabled { opacity: .4; cursor: default; }
  .b-run { background: var(--azul); width: 100%; margin-top: 14px; padding: 11px 12px; font-size: 13.5px; }
  .b-run:hover { background: var(--azul-osc); }
  .rango { width: 100%; appearance: none; -webkit-appearance: none; height: 4px;
           border-radius: 2px; background: var(--navy-600); cursor: pointer; }
  .rango::-webkit-slider-thumb { -webkit-appearance: none; width: 14px; height: 14px;
           border-radius: 50%; background: var(--azul); border: 2px solid #fff; }
  .rango::-moz-range-thumb { width: 12px; height: 12px; border-radius: 50%;
           background: var(--azul); border: 2px solid #fff; }
  .panel { background: var(--navy-800); border-radius: var(--radio); padding: 12px 14px;
           margin-top: 10px; font-size: 12.5px; line-height: 1.55; min-height: 64px; }
  .panel strong { color: var(--ambar); }
  .panel .tit { display: block; margin-bottom: 3px; font: 400 18px/1.1 var(--f-titulo);
                letter-spacing: .04em; }
  .met { display: flex; gap: 8px; margin-top: 12px; }
  .met div { flex: 1; background: var(--navy-800); border-radius: var(--radio); padding: 9px 4px;
             text-align: center; }
  .met .n { font: 400 30px/1.05 var(--f-titulo); letter-spacing: .03em; font-variant-numeric: tabular-nums; }
  .met .t { font-size: 10px; color: var(--texto-tenue); text-transform: uppercase; letter-spacing: .05em; }
  /* Encabezado */
  .marca { display: flex; gap: 12px; align-items: center; margin-bottom: 10px; }
  .logo { width: 44px; height: 44px; flex: none; }
  .logo svg { width: 44px; height: 44px; display: block; }
  .marca h1 { margin: 0; }
  .marca .sub { margin: 0; }
  .intro { font-size: 12px; color: var(--texto-tenue); margin: 0; line-height: 1.5; }
  aside h2 { display: flex; align-items: center; gap: 8px; }
  aside h2 .num { width: 18px; height: 18px; border-radius: 50%; background: var(--navy-600);
                  color: #fff; font: 600 10px/1 var(--f-texto); letter-spacing: 0; display: grid;
                  place-items: center; }

  /* Tarjetas de algoritmo: cada una toma su color de la variable --c */
  .algos { display: flex; flex-direction: column; gap: 6px; }
  .algo { display: flex; gap: 12px; align-items: center; width: 100%; text-align: left;
          padding: 10px 12px; background: var(--navy-800); border: 1px solid transparent;
          color: var(--texto-claro); font-weight: 400; border-radius: var(--radio); }
  .algo:hover { background: var(--navy-700); border-color: var(--navy-600); }
  .algo .ico { width: 34px; height: 34px; border-radius: 8px; background: var(--navy-600);
               color: var(--texto-claro); display: grid; place-items: center; flex: none;
               transition: background-color .2s, color .2s; }
  .algo .ico svg { width: 18px; height: 18px; }
  .algo b { display: block; font: 400 17px/1.1 var(--f-titulo); letter-spacing: .04em; }
  .algo small { display: block; font-size: 11.5px; color: var(--texto-tenue); line-height: 1.35; }
  .algo.activo { background: var(--navy-700); border-color: var(--c); }
  .algo.activo .ico { background: var(--c); color: #fff; }

  /* Origen elegido */
  .chip-origen { display: flex; align-items: center; gap: 10px; min-height: 46px;
                 padding: 8px 8px 8px 12px; background: var(--navy-800); border-radius: var(--radio);
                 border: 1px dashed var(--navy-600); font-size: 12.5px;
                 transition: border-color .2s, background-color .2s; }
  .chip-origen.vacio { color: var(--texto-tenue); }
  .chip-origen.vacio .punto, .chip-origen.vacio .quitar { display: none; }
  .chip-origen:not(.vacio) { border-style: solid; border-color: var(--azul);
                             animation: aparecer .3s var(--suave); }
  .chip-origen .nom { flex: 1; min-width: 0; }
  .chip-origen .nom span, .chip-origen .nom small { display: block; overflow: hidden;
                 text-overflow: ellipsis; white-space: nowrap; }
  .chip-origen .nom small { color: var(--texto-tenue); font-size: 11px; }
  .quitar { padding: 6px; background: transparent; color: var(--texto-tenue);
            display: grid; place-items: center; }
  .quitar:hover { background: var(--navy-600); color: #fff; }
  .quitar svg { width: 16px; height: 16px; }
  @keyframes aparecer { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

  /* Control segmentado */
  .segmentado { display: flex; gap: 3px; padding: 3px; background: var(--navy-800);
                border-radius: var(--radio-sm); }
  .segmentado button { flex: 1; background: transparent; color: var(--texto-tenue);
                       padding: 7px 8px; font-size: 12.5px; border-radius: 5px; }
  .segmentado button:hover { color: #fff; }
  .segmentado button.activo { background: var(--navy-600); color: #fff; }

  /* Pesos plegables: la fila de la rejilla pasa de 0fr a 1fr para animar la altura */
  .enlace { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; padding: 4px 0;
            background: none; color: var(--enlace); font-size: 12px; font-weight: 600; }
  .enlace:hover { color: #fff; }
  .enlace svg { width: 14px; height: 14px; transition: transform .25s var(--suave); }
  .enlace[aria-expanded="true"] svg { transform: rotate(180deg); }
  .pesos { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .3s var(--suave); }
  .pesos.visible { grid-template-rows: 1fr; }
  .pesos > div { overflow: hidden; }
  .pesos-int { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; padding-top: 8px; }
  .pesos .pw { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin: 0;
               font: 10.5px var(--f-mono); color: #c3cfdf; }
  .pesos .pw span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pesos input { width: 44px; padding: 3px 5px; border: 1px solid var(--navy-600); flex: none;
                 background: var(--navy-700); color: #fff; text-align: right; font: 12px inherit; }
  .pesos input:focus { border-color: var(--azul); outline: none; }
  .pesos .restablecer { grid-column: 1 / -1; justify-self: start; margin-top: 4px; padding: 4px 0;
                        background: none; color: var(--enlace); font-size: 11.5px; }

  /* Boton principal con estado de espera */
  .b-run { display: flex; align-items: center; justify-content: center; gap: 8px; }
  .b-run svg { width: 18px; height: 18px; }
  .b-run.ocupado { pointer-events: none; opacity: .8; }
  .b-run.ocupado svg { display: none; }
  .b-run.ocupado::before { content: ""; width: 14px; height: 14px; border-radius: 50%;
                           border: 2px solid rgba(255,255,255,.35); border-top-color: #fff;
                           animation: girar .7s linear infinite; }
  .punto { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex: none; }
  main { position: relative; overflow: hidden; flex: 1; min-width: 0; }
  #lienzo { width: 100%; height: 100%; display: block; cursor: grab; background: var(--fondo);
            touch-action: none; }
  #lienzo.arrastrando { cursor: grabbing; }
  /* Controles flotantes sobre el lienzo: superficies blancas con borde fino */
  .hud { position: absolute; display: flex; gap: 8px; z-index: 5; }
  .arriba-izq { top: 16px; left: 16px; align-items: flex-start; }
  .arriba-der { top: 16px; right: 16px; flex-direction: column; align-items: flex-end; }
  .arriba-der .fila-hud { display: flex; gap: 8px; }
  .abajo-der { right: 16px; bottom: 16px; flex-direction: column; gap: 0; background: #fff;
               border: 1px solid #d5dce7; border-radius: var(--radio); overflow: hidden; }
  .hud-btn { width: 38px; height: 38px; padding: 0; display: grid; place-items: center;
             background: #fff; color: var(--navy-900); border: 1px solid #d5dce7;
             border-radius: var(--radio); font-weight: 600; }
  .hud-btn:hover { background: #f3f6fa; border-color: #b9c4d4; }
  .hud-btn svg { width: 18px; height: 18px; }
  .abajo-der .hud-btn { border: 0; border-radius: 0; }
  .abajo-der .hud-btn + .hud-btn { border-top: 1px solid #e3e8f0; }

  .buscador { position: relative; width: 280px; }
  .buscador .lupa { position: absolute; left: 12px; top: 11px; width: 16px; height: 16px;
                    color: #7b8aa0; pointer-events: none; }
  .buscador input { width: 100%; height: 38px; padding: 0 38px 0 36px; background: #fff;
                    border: 1px solid #d5dce7; border-radius: var(--radio); color: var(--texto);
                    outline: none; transition: border-color .15s; }
  .buscador input:focus { border-color: var(--azul); }
  .buscador input::-webkit-search-cancel-button { display: none; }
  .buscador kbd { position: absolute; right: 9px; top: 9px; pointer-events: none; }
  .buscador input:focus ~ kbd { opacity: 0; }
  kbd { display: inline-block; min-width: 20px; text-align: center; padding: 2px 6px;
        font: 600 11px var(--f-mono); border-radius: 5px;
        background: #eef2f8; color: #5b6b80; border: 1px solid #d5dce7; }
  .resultados { position: absolute; top: 44px; left: 0; right: 0; margin: 0; padding: 4px;
                list-style: none; background: #fff; border: 1px solid #d5dce7;
                border-radius: var(--radio); max-height: 330px; overflow-y: auto; opacity: 0;
                transform: translateY(-4px); pointer-events: none;
                transition: opacity .15s, transform .15s var(--suave); }
  .resultados.abierto { opacity: 1; transform: none; pointer-events: auto; }
  .resultados li { display: flex; align-items: center; gap: 10px; padding: 7px 10px;
                   border-radius: 6px; cursor: pointer; font-size: 12.5px; }
  .resultados li.activo { background: #eef2f8; }
  .resultados li .nom { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .resultados li small { color: #7b8aa0; font-size: 11px; }
  .resultados li.nada { color: #7b8aa0; cursor: default; }
  .resultados mark { background: none; color: var(--azul); font-weight: 700; }

  .segmentado.claro { background: #fff; border: 1px solid #d5dce7; }
  .segmentado.claro button { color: #5b6b80; }
  .segmentado.claro button:hover { color: var(--navy-900); }
  .segmentado.claro button.activo { background: var(--navy-900); color: #fff; }

  .leyenda { background: #fff; border: 1px solid #d5dce7; border-radius: var(--radio); padding: 6px;
             display: flex; flex-direction: column; gap: 1px; min-width: 176px; }
  .leyenda .titulo { font: 400 14px/1 var(--f-titulo); letter-spacing: .08em; color: #7b8aa0;
                     padding: 8px 8px 4px; }
  .leyenda button { display: flex; align-items: center; gap: 8px; padding: 5px 8px; background: none;
                    color: var(--texto); font-weight: 400; font-size: 12px; text-align: left; }
  .leyenda button:hover, .leyenda button:focus-visible { background: #eef2f8; }
  .leyenda .cnt { margin-left: auto; color: #7b8aa0; font-variant-numeric: tabular-nums; }
  .leyenda { width: 250px; max-height: calc(100vh - 220px); overflow-y: auto; scrollbar-width: thin; }
  .leyenda .segmentado { margin-bottom: 4px; }
  .ley-cuerpo { display: flex; flex-direction: column; gap: 1px; }
  .ley-cuerpo[hidden] { display: none; }
  .estilo-ar { display: flex; align-items: center; gap: 10px; padding: 4px 8px; font-size: 11.5px;
               color: #44515f; line-height: 1.35; }
  /* Muestra de linea con punta de flecha, del color de cada estilo */
  .muestra-ar { position: relative; flex: none; width: 24px; height: 0; border-top: 2px solid currentColor; }
  .muestra-ar::after { content: ""; position: absolute; right: -3px; top: -6px; border: 5px solid transparent;
                       border-right: 0; border-left: 7px solid currentColor; }
  .muestra-ar.base { color: var(--arista); }
  .muestra-ar.base::after { display: none; }
  .muestra-ar.cursor { color: var(--azul); }
  .muestra-ar.camino { color: var(--naranja); border-top-width: 3px; }
  .muestra-ar.aumento { color: var(--morado); border-top-width: 3px; }
  .muestra-ar.corte { color: var(--rojo); border-top: 3px dashed currentColor; }
  .leyenda code { font: 600 10.5px var(--f-mono); color: var(--navy-900); }
  .ley-desc { margin: 2px 4px 6px; padding: 7px 9px; border-radius: 6px; background: #eef2f8;
              font-size: 11.5px; color: #44515f; line-height: 1.4; min-height: 48px; }

  /* Linea de estado del algoritmo, sobre el reproductor */
  .barra { position: absolute; left: 50%; bottom: 84px; transform: translate(-50%, 8px);
           max-width: calc(100% - 140px); background: var(--navy-900); color: #fff;
           padding: 8px 16px; border-radius: 999px; font-size: 12.5px; white-space: nowrap;
           overflow: hidden; text-overflow: ellipsis; opacity: 0; pointer-events: none; z-index: 5;
           transition: opacity .25s, transform .3s var(--suave); }
  .barra.visible { opacity: 1; transform: translate(-50%, 0); }
  .barra.cambio { animation: latido .3s var(--suave); }
  .barra b { color: var(--ambar); font-weight: 600; }
  @keyframes latido { from { opacity: .55; transform: translate(-50%, 3px); }
                      to { opacity: 1; transform: translate(-50%, 0); } }

  /* Reproductor */
  .reproductor { position: absolute; left: 50%; bottom: 16px; z-index: 5; display: flex;
                 align-items: center; gap: 2px; width: min(620px, calc(100% - 140px));
                 padding: 6px 8px 6px 6px; background: var(--navy-900); color: #fff;
                 border-radius: 14px; transform: translate(-50%, 160%);
                 transition: transform .4s var(--suave); }
  .reproductor.visible { transform: translate(-50%, 0); }
  .reproductor button { width: 34px; height: 34px; padding: 0; flex: none; display: grid;
                        place-items: center; background: transparent; color: #c3cfdf; }
  .reproductor button:hover:not(:disabled) { background: var(--navy-600); color: #fff; }
  .reproductor button svg { width: 18px; height: 18px; }
  .reproductor .play { width: 40px; height: 40px; margin: 0 4px; border-radius: 50%;
                       background: var(--verde); color: #fff; }
  .reproductor .play:hover:not(:disabled) { background: var(--verde-osc); }
  .reproductor .play svg { width: 20px; height: 20px; }
  .reproductor .play .i-pausa, .reproductor .play.activo .i-play { display: none; }
  .reproductor .play.activo .i-pausa { display: block; }
  .linea-tiempo { flex: 1; min-width: 60px; margin: 0 10px;
                  background: linear-gradient(to right, var(--azul) var(--p, 0%), var(--navy-600) var(--p, 0%)); }
  .contador { min-width: 54px; text-align: center; font-size: 12px; color: #c3cfdf;
              font-variant-numeric: tabular-nums; }
  .velocidades { display: flex; gap: 2px; padding: 2px; margin-left: 6px; border-radius: 8px;
                 background: var(--navy-800); }
  .reproductor .velocidades button { width: auto; height: 26px; padding: 0 7px; font-size: 11.5px;
                                     font-weight: 600; color: var(--texto-tenue); border-radius: 6px; }
  .reproductor .velocidades button.activo { background: var(--navy-600); color: #fff; }

  /* Avisos breves */
  .avisos { position: absolute; top: 66px; left: 50%; transform: translateX(-50%); z-index: 8;
            display: flex; flex-direction: column; align-items: center; gap: 8px; pointer-events: none; }
  .aviso { max-width: 420px; padding: 10px 14px; background: var(--navy-900); color: #fff;
           border-left: 4px solid var(--rojo); border-radius: var(--radio-sm); font-size: 12.5px;
           animation: entraAviso .3s var(--suave); }
  .aviso.info { border-left-color: var(--azul); }
  .aviso.sale { animation: saleAviso .25s ease forwards; }
  @keyframes entraAviso { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: none; } }
  @keyframes saleAviso { to { opacity: 0; transform: translateY(-8px); } }

  /* Ayuda de atajos */
  .ayuda { position: absolute; top: 62px; right: 16px; z-index: 7; width: 270px; padding: 14px 16px;
           background: var(--navy-900); color: #fff; border-radius: var(--radio); font-size: 12.5px;
           opacity: 0; transform: translateY(-6px); pointer-events: none;
           transition: opacity .18s, transform .18s var(--suave); }
  .ayuda.abierta { opacity: 1; transform: none; pointer-events: auto; }
  .ayuda b { font: 400 18px/1 var(--f-titulo); letter-spacing: .05em; }
  .ayuda dl { display: grid; grid-template-columns: auto 1fr; gap: 7px 12px; margin: 10px 0 0;
              align-items: center; }
  .ayuda dd { margin: 0; color: #c3cfdf; }
  .ayuda kbd { background: var(--navy-600); color: #fff; border-color: var(--navy-500); }

  /* Estado vacio: nadie alcanza el objetivo */
  .sin-rutas { position: absolute; left: 50%; top: 50%; transform: translate(-50%, 58px); z-index: 4;
               width: min(360px, calc(100% - 40px)); text-align: center; color: #44515f;
               animation: aparecer .4s var(--suave); }
  .sin-rutas b { display: block; font: 400 22px/1.1 var(--f-titulo); letter-spacing: .04em;
                 color: var(--navy-900); margin-bottom: 4px; }
  .sin-rutas[hidden] { display: none; }

  /* Resultados en el panel lateral */
  .panel.cambio { animation: aparecer .25s var(--suave); }
  .estados { display: grid; gap: 6px; margin-top: 10px; font-size: 11.5px; color: #c3cfdf; }
  .estados span { display: flex; align-items: center; gap: 9px; }
  .muestra { width: 12px; height: 12px; border-radius: 50%; flex: none; display: inline-block; }
  .muestra.anillo-n { background: var(--azul); outline: 2px solid var(--naranja); outline-offset: 2px;
                      margin: 0 3px; width: 9px; height: 9px; }
  .muestra.hueca { background: #fff; border: 2px solid var(--turquesa); }
  .muestra.solida { background: var(--turquesa); }
  .muestra.insignia { width: auto; height: 15px; padding: 0 5px; border-radius: 8px; background: #fff;
                      color: var(--navy-900); font-size: 10px; font-weight: 700; line-height: 15px;
                      font-style: normal; text-align: center; }
  .muestra.linea-m, .muestra.linea-c, .muestra.guion { width: 16px; height: 3px; border-radius: 2px; }
  .muestra.linea-m { background: var(--morado); }
  .muestra.linea-c { background: var(--morado-claro); }
  .muestra.guion { height: 0; border-radius: 0; border-top: 3px dashed var(--rojo); }
  .muestra.verde { background: var(--verde); }
  .ruta { list-style: none; margin: 10px 0 0; padding: 0; }
  .ruta li { animation: aparecer .35s var(--suave) both; animation-delay: calc(var(--i) * 70ms); }
  .ruta .nodo-ruta { display: flex; align-items: center; gap: 9px; padding: 6px 9px; cursor: pointer;
                     border-radius: var(--radio-sm); background: var(--navy-700); transition: background-color .15s; }
  .ruta .nodo-ruta:hover { background: var(--navy-600); }
  .ruta .nodo-ruta span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ruta .nodo-ruta small { color: var(--texto-tenue); font-size: 11px; }
  .ruta .salto { margin-left: 13px; padding: 4px 0 4px 14px; border-left: 2px solid var(--naranja);
                 font: 10.5px var(--f-mono); color: var(--ambar); }
  .ruta .salto small { display: block; margin-top: 2px; font: 11px/1.4 var(--f-texto);
                       color: var(--texto-tenue); }
  .subtitulo { margin: 14px 0 7px; font: 400 14px/1 var(--f-titulo); letter-spacing: .08em; color: #8094ae; }
  .cortes { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; max-height: 280px;
            overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--navy-600) transparent; }
  .cortes li { padding: 6px 9px; background: var(--navy-700); border-left: 3px solid var(--rojo);
               border-radius: 6px; cursor: pointer; font-size: 12px; transition: background-color .15s;
               animation: aparecer .3s var(--suave) both; animation-delay: calc(var(--i) * 35ms); }
  .cortes li:hover { background: var(--navy-600); }
  .cortes .tipo { display: block; font: 10.5px var(--f-mono); color: #f0a59c; }
  .exposicion { margin-top: 12px; }
  .exposicion .cifras { display: flex; justify-content: space-between; gap: 8px; font-size: 11.5px;
                        color: #c3cfdf; }
  .exposicion .cifras span:last-child { color: #fff; font-weight: 600; white-space: nowrap; }
  .barra-exp { height: 8px; margin-top: 6px; border-radius: 4px; background: var(--navy-600); overflow: hidden; }
  .barra-exp .relleno { width: 100%; height: 100%; background: var(--rojo); border-radius: 4px;
                        transition: width 1s var(--suave) .3s; }

  /* Tarjeta de detalle del objeto seleccionado */
  .detalle { position: absolute; top: 62px; right: 16px; z-index: 6; width: 300px;
             max-height: calc(100% - 150px); display: flex; flex-direction: column; background: #fff;
             border: 1px solid #d5dce7; border-radius: var(--radio); overflow: hidden; opacity: 0;
             transform: translateX(calc(100% + 24px)); pointer-events: none;
             transition: transform .35s var(--suave), opacity .25s; }
  .detalle.abierto { opacity: 1; transform: none; pointer-events: auto; }
  main.con-detalle .leyenda { opacity: 0; pointer-events: none; }
  .leyenda { transition: opacity .2s; }
  .detalle .cab { display: flex; gap: 10px; align-items: flex-start; padding: 14px 10px 10px 14px; }
  .detalle .cab .punto { width: 12px; height: 12px; margin-top: 5px; }
  .detalle .cab div { flex: 1; min-width: 0; }
  .detalle .cab b { display: block; font-size: 14px; color: var(--navy-900); overflow-wrap: anywhere; }
  .detalle .cab small { display: block; color: #7b8aa0; font-size: 11px; overflow-wrap: anywhere; }
  .detalle .quitar { color: #7b8aa0; }
  .detalle .quitar:hover { background: #eef2f8; color: var(--navy-900); }
  .chips { display: flex; flex-wrap: wrap; gap: 5px; padding: 0 14px; }
  .chip { font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #eef2f8; color: #44515f; }
  .chip.hv { background: #fcefe2; color: #a4560f; }
  .chip.obj { background: #f8e4e2; color: var(--rojo); }
  .acciones { display: flex; gap: 6px; padding: 12px 14px; }
  .acciones button { flex: 1; padding: 7px 8px; font-size: 12px; background: #eef2f8; color: var(--navy-900); }
  .acciones button:hover:not(:disabled) { background: #e1e7f0; }
  .acciones .prim { background: var(--azul); color: #fff; }
  .acciones .prim:hover:not(:disabled) { background: var(--azul-osc); }
  .detalle .segmentado { margin: 0 14px; }
  .detalle .segmentado, .leyenda .segmentado { background: #eef2f8; }
  .detalle .segmentado button, .leyenda .segmentado button { color: #5b6b80; }
  .detalle .segmentado button:hover, .leyenda .segmentado button:hover { color: var(--navy-900); }
  .detalle .segmentado button.activo, .leyenda .segmentado button.activo { background: var(--navy-900); color: #fff; }
  .conexiones { list-style: none; margin: 8px 0 0; padding: 0 8px 10px; overflow-y: auto; flex: 1;
                min-height: 60px; scrollbar-width: thin; }
  .conexiones li { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px;
                   cursor: pointer; font-size: 12.5px; animation: aparecer .25s var(--suave) both;
                   animation-delay: calc(var(--i) * 22ms); }
  .conexiones li:hover { background: #eef2f8; }
  .conexiones .nom { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .conexiones .tipos { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
                       font: 10px var(--f-mono); color: #7b8aa0; }
  .conexiones li.vacia { color: #7b8aa0; cursor: default; }

  .plegar { display: none; margin-left: auto; align-self: flex-start; }
  .plegar svg { transform: rotate(90deg); }
  .chip-origen.sacudir { animation: sacudir .4s; }
  @keyframes sacudir { 20%, 60% { transform: translateX(-4px); } 40%, 80% { transform: translateX(4px); } }

  @media (max-width: 760px) {
    aside { position: absolute; inset: 0 auto 0 0; z-index: 20; width: min(340px, 88vw); }
    #app.sin-panel aside { margin-left: calc(-1 * min(340px, 88vw)); }
    .plegar { display: grid; }
    .buscador { width: calc(100vw - 86px); }
    .arriba-der { top: 62px; }
    .arriba-der .leyenda { display: none; }
    .detalle { top: 108px; right: 12px; width: calc(100% - 24px); max-height: calc(100% - 200px); }
    .reproductor { width: calc(100% - 24px); bottom: 12px; }
    .velocidades, .contador { display: none; }
    .abajo-der { bottom: 76px; right: 12px; }
    .barra { max-width: calc(100% - 24px); bottom: 70px; }
  }
  .etq { position: absolute; left: 0; top: 0; background: var(--navy-900); color: #fff;
         padding: 8px 12px; border-radius: var(--radio-sm); font-size: 12px; line-height: 1.45;
         pointer-events: none; opacity: 0; white-space: nowrap; z-index: 6; max-width: 360px;
         transition: opacity .15s; }
  .etq.visible { opacity: 1; }
  .etq strong { display: block; font-weight: 600; overflow: hidden; text-overflow: ellipsis; }
  .etq span { display: block; color: var(--texto-tenue); font-size: 11.5px; }
  .etq.ancha { white-space: normal; width: 300px; }
  .etq.ancha strong + .acc, .etq .acc + strong { margin-top: 2px; }
  .etq .acc { color: #dfe7f3; margin: 3px 0 6px; }
  .etq .acc b { display: block; font: 600 10.5px var(--f-mono); color: var(--ambar); }
  .etq .nota { margin-top: 4px; padding-top: 6px; border-top: 1px solid var(--navy-600); }
  .cargando { position: absolute; inset: 0; display: flex; flex-direction: column; gap: 12px;
              align-items: center; justify-content: center; font-size: 14px; color: #44515f;
              background: var(--fondo); transition: opacity .3s; }
  .cargando::before { content: ""; width: 30px; height: 30px; border-radius: 50%;
              border: 3px solid var(--arista); border-top-color: var(--azul);
              animation: girar .8s linear infinite; }
  .cargando.oculto { opacity: 0; pointer-events: none; }
  @keyframes girar { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; }
  }
</style>
</head>
<body>
<!--__ICONOS__-->
<div id="app">
  <aside>
    <header class="marca">
      <div class="logo" aria-hidden="true">
        <svg viewBox="0 0 48 48"><use href="#ic-logo"/></svg>
      </div>
      <div>
        <h1>Analizador de rutas y defensa</h1>
        <div class="sub">Active Directory como grafo dirigido</div>
      </div>
      <button class="quitar plegar" id="btnPlegar" title="Ocultar el panel (P)" aria-label="Ocultar el panel">
        <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-chevron"/></svg></button>
    </header>
    <p class="intro" id="intro">El backend en Python ejecuta cada algoritmo y la página reproduce
      su ejecución paso a paso sobre el grafo.</p>

    <h2><span class="num">1</span>Objetivo a proteger</h2>
    <select id="selObjetivo" aria-label="Objetivo a proteger"></select>

    <h2><span class="num">2</span>Algoritmo</h2>
    <div class="algos" id="algos" role="radiogroup" aria-label="Algoritmo">
      <button class="algo activo" role="radio" aria-checked="true" data-alg="bfs" style="--c: var(--azul)">
        <span class="ico"><svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-bfs"/></svg></span>
        <span><b>Ruta más corta</b><small>BFS por niveles, mínimo de saltos</small></span>
      </button>
      <button class="algo" role="radio" aria-checked="false" data-alg="dijkstra" style="--c: var(--naranja)">
        <span class="ico"><svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-dijkstra"/></svg></span>
        <span><b>Ruta de menor esfuerzo</b><small>Dijkstra con pesos por tipo de acceso</small></span>
      </button>
      <button class="algo" role="radio" aria-checked="false" data-alg="defensa" style="--c: var(--verde)">
        <span class="ico"><svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-defensa"/></svg></span>
        <span><b>Plan de defensa</b><small>Flujo máximo y corte mínimo</small></span>
      </button>
    </div>

    <div id="bloqueOrigen">
      <h2><span class="num">3</span>Origen</h2>
      <div class="chip-origen vacio" id="panelOrigen">
        <i class="punto" id="origenPunto"></i>
        <div class="nom"><span id="origenNombre">Haz clic en un nodo del grafo</span>
          <small id="origenTipo"></small></div>
        <button class="quitar" id="btnQuitarOrigen" aria-label="Quitar origen" title="Quitar origen">
          <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-cerrar"/></svg></button>
      </div>
    </div>

    <div id="bloqueFuentes" style="display:none">
      <h2><span class="num">3</span>Objetos de entrada</h2>
      <div class="segmentado" id="segFuentes" role="radiogroup" aria-label="Objetos de entrada">
        <button class="activo" data-v="usuarios" role="radio" aria-checked="true">Usuarios</button>
        <button data-v="todos" role="radio" aria-checked="false">Todos los no críticos</button>
      </div>
    </div>

    <button class="enlace" id="togglerPesos" aria-expanded="false" aria-controls="pesos">
      Ajustar pesos de Dijkstra
      <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-chevron"/></svg></button>
    <div class="pesos" id="pesos"><div><div class="pesos-int" id="pesosInt"></div></div></div>

    <button class="b-run" id="btnEjecutar">
      <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-ejecutar"/></svg>Ejecutar</button>

    <h2>Resultado</h2>
    <div class="met">
      <div><div class="n" id="mPaso">0</div><div class="t">paso</div></div>
      <div><div class="n" id="mA">-</div><div class="t" id="mAT">visitados</div></div>
      <div><div class="n" id="mB">-</div><div class="t" id="mBT">objetivo</div></div>
    </div>
    <div class="panel" id="panel">Elige un objetivo, un algoritmo y pulsa Ejecutar.</div>

  </aside>
  <main>
    <canvas id="lienzo" aria-label="Grafo de rutas de acceso hacia el objetivo"></canvas>

    <div class="hud arriba-izq">
      <button class="hud-btn" id="btnPanel" title="Mostrar u ocultar el panel (P)" aria-label="Mostrar u ocultar el panel">
        <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-panel"/></svg></button>
      <div class="buscador">
        <svg viewBox="0 0 24 24" class="glifo lupa" aria-hidden="true"><use href="#ic-buscar"/></svg>
        <input id="txtBuscar" type="search" placeholder="Buscar objeto..." autocomplete="off"
               spellcheck="false" aria-label="Buscar objeto en el grafo" aria-controls="resultados">
        <kbd>/</kbd>
        <ul class="resultados" id="resultados" role="listbox"></ul>
      </div>
    </div>

    <div class="hud arriba-der">
      <div class="fila-hud">
        <div class="segmentado claro" id="segDisposicion" role="radiogroup" aria-label="Disposición del grafo">
          <button class="activo" data-v="fuerzas" role="radio" aria-checked="true" title="Disposición por fuerzas (R)">Fuerzas</button>
          <button data-v="radial" role="radio" aria-checked="false" title="Anillos por distancia en saltos al objetivo (R)">Radial</button>
        </div>
        <button class="hud-btn" id="btnAyuda" title="Atajos de teclado (?)" aria-label="Atajos de teclado">
          <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-atajos"/></svg></button>
      </div>
      <div class="leyenda" id="leyenda" aria-label="Tipos de objeto"></div>
    </div>

    <div class="hud abajo-der">
      <button class="hud-btn" id="btnAcercar" title="Acercar (+)" aria-label="Acercar">
        <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-acercar"/></svg></button>
      <button class="hud-btn" id="btnAlejar" title="Alejar (-)" aria-label="Alejar">
        <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-alejar"/></svg></button>
      <button class="hud-btn" id="btnAjustar" title="Ajustar a la vista (F)" aria-label="Ajustar a la vista">
        <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-ajustar"/></svg></button>
    </div>

    <section class="detalle" id="detalle" aria-label="Objeto seleccionado">
      <div class="cab">
        <i class="punto" id="detPunto"></i>
        <div><b id="detNombre"></b><small id="detCompleto"></small></div>
        <button class="quitar" id="btnCerrarDetalle" title="Cerrar (Esc)" aria-label="Cerrar detalle">
          <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-cerrar"/></svg></button>
      </div>
      <div class="chips" id="detChips"></div>
      <div class="acciones">
        <button class="prim" id="btnUsarOrigen">Usar como origen</button>
        <button id="btnCentrar">Centrar en el grafo</button>
      </div>
      <div class="segmentado" id="segConexiones" role="tablist" aria-label="Conexiones">
        <button class="activo" data-v="salen" role="tab" aria-selected="true">Controla <span id="detSalen"></span></button>
        <button data-v="entran" role="tab" aria-selected="false">Lo controlan <span id="detEntran"></span></button>
      </div>
      <ul class="conexiones" id="detLista"></ul>
    </section>

    <div class="barra" id="barra" aria-live="polite"></div>

    <div class="reproductor" id="reproductor" aria-label="Reproducción del algoritmo">
      <button id="btnInicio" title="Inicio (Inicio)" aria-label="Ir al inicio">
        <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-inicio"/></svg></button>
      <button id="btnAtras" title="Paso anterior (flecha izquierda)" aria-label="Paso anterior">
        <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-anterior"/></svg></button>
      <button class="play" id="btnPlay" title="Reproducir o pausar (Espacio)" aria-label="Reproducir">
        <svg viewBox="0 0 24 24" class="glifo i-play" aria-hidden="true"><use href="#ic-reproducir"/></svg>
        <svg viewBox="0 0 24 24" class="glifo i-pausa" aria-hidden="true"><use href="#ic-pausa"/></svg></button>
      <button id="btnPaso" title="Paso siguiente (flecha derecha)" aria-label="Paso siguiente">
        <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-siguiente"/></svg></button>
      <button id="btnFin" title="Resultado final (Fin)" aria-label="Ir al resultado final">
        <svg viewBox="0 0 24 24" class="glifo" aria-hidden="true"><use href="#ic-fin"/></svg></button>
      <input type="range" class="rango linea-tiempo" id="rngFrame" min="0" max="0" value="0" aria-label="Línea de tiempo">
      <span class="contador" id="contador">0 / 0</span>
      <div class="velocidades" id="velocidades" role="radiogroup" aria-label="Velocidad">
        <button class="activo" data-v="1" role="radio" aria-checked="true">1x</button>
        <button data-v="2" role="radio" aria-checked="false">2x</button>
        <button data-v="4" role="radio" aria-checked="false">4x</button>
        <button data-v="8" role="radio" aria-checked="false">8x</button>
      </div>
    </div>

    <div class="ayuda" id="ayuda" role="dialog" aria-label="Atajos de teclado">
      <b>Atajos de teclado</b>
      <dl>
        <dt><kbd>/</kbd></dt><dd>Buscar un objeto</dd>
        <dt><kbd>Espacio</kbd></dt><dd>Reproducir o pausar</dd>
        <dt><kbd>&larr;</kbd> <kbd>&rarr;</kbd></dt><dd>Paso anterior o siguiente</dd>
        <dt><kbd>Inicio</kbd> <kbd>Fin</kbd></dt><dd>Primer paso o resultado</dd>
        <dt><kbd>E</kbd></dt><dd>Ejecutar el algoritmo</dd>
        <dt><kbd>F</kbd></dt><dd>Ajustar el grafo a la vista</dd>
        <dt><kbd>+</kbd> <kbd>-</kbd></dt><dd>Acercar o alejar</dd>
        <dt><kbd>R</kbd></dt><dd>Cambiar disposición</dd>
        <dt><kbd>P</kbd></dt><dd>Mostrar u ocultar el panel</dd>
        <dt><kbd>Esc</kbd></dt><dd>Cerrar y quitar resaltados</dd>
      </dl>
    </div>

    <div class="avisos" id="avisos" aria-live="assertive"></div>
    <div class="sin-rutas" id="sinRutas" hidden></div>
    <div class="etq" id="etq"></div>
    <div class="cargando" id="cargando">Cargando grafo...</div>
  </main>
</div>
<!--__BACKEND_LOCAL__-->
<script>
const COLOR = { User: "#2e5aac", Computer: "#16a085", Group: "#8e44ad",
                GPO: "#7f8c8d", OU: "#7f8c8d", Domain: "#7f8c8d" };
const PESOS_DEF = { MEMBER_OF:1, CONTAINS:1, ADMIN_TO:1, GENERIC_ALL:1, DC_SYNC:1,
  GET_CHANGES:1, GET_CHANGES_ALL:1, GP_LINK:2, OWNS:2, WRITE_DACL:2, WRITE_OWNER:2,
  GENERIC_WRITE:2, CAN_RDP:3, EXECUTE_DCOM:3, ALLOWED_TO_DELEGATE:3, HAS_SESSION:4 };
let pesos = Object.assign({}, PESOS_DEF);

let grafo = null;           // payload del grafo actual
let posPorId = new Map();   // i -> nodo del lienzo {x, y, nombre, tipo, hv, ...}
let objetivo = null;
let origen = null;
let traza = null;           // traza devuelta por el backend
let frames = 0;             // numero de cuadros de animacion
let frameActual = 0;
let temporizador = null;
let algSel = "bfs";         // algoritmo elegido en las tarjetas
let fuentesSel = "usuarios"; // objetos de entrada del plan de defensa

const lienzo = document.getElementById("lienzo");
const ctx = lienzo.getContext("2d");
const etq = document.getElementById("etq");
const MOV_REDUCIDO = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const FONDO = "#e9edf4", ARISTA = "#c2ccda", TEXTO = "#33414f", TEXTO_FUERTE = "#11263f";
const FUENTE = 'Bahnschrift, "Segoe UI", system-ui, sans-serif';
const FUENTE_TITULO = '"Bebas Neue", "Bahnschrift Condensed", sans-serif';

let nodos = [];             // nodos del subgrafo con posicion, velocidad y estado de animacion
let pares = new Map();      // "s,d" -> {s, t, tipos}: accesos dirigidos agrupados por par
let enlaces = [];           // pares sin direccion: resortes de la simulacion y trazo base
let paresPorTipo = new Map(); // tipo de acceso -> pares que lo incluyen
let filtroTipo = null, nodosFiltroTipo = new Set(); // tipo resaltado desde la leyenda
let hoverArista = null;     // par dirigido bajo el cursor
let cam = { x: 0, y: 0, k: 1 };
let ancho = 0, alto = 0, dpr = 1;
let disposicion = "fuerzas";
let autoAjuste = true;      // la camara sigue al grafo mientras se acomoda
let vuelo = null;           // transicion de camara en curso
let hover = null, ultimoHover = null, hoverMezcla = 0;
let gesto = null;           // arrastre de nodo o desplazamiento del lienzo
let sucio = true;           // obliga a redibujar aunque nada este en movimiento
// Estado visual que fija cada cuadro de un algoritmo. El lazo de dibujo
// interpola hacia el, de modo que los cambios se ven como transiciones.
let vis = visVacio(false);

// Parametros de la simulacion de fuerzas (integracion de Verlet por velocidad).
const sim = { alfa: 1, alfaObjetivo: 0, decaimiento: 1 - Math.pow(0.001, 1 / 300) };
const DIST_RESORTE = 46, CARGA = -210, DIST_MAX2 = 520 * 520, GRAVEDAD = 0.05, FRICCION = 0.6;

const ESTILO_ARISTA = {
  descubre: { color: "#2e5aac", ancho: 2.2, alfa: 1 },
  relaja:   { color: "#2e5aac", ancho: 1.8, alfa: .8 },
  explorada: { color: "#2e5aac", ancho: 1.2, alfa: .22, sinFlecha: true },
  camino:   { color: "#e67e22", ancho: 3.4, alfa: 1, flujo: true },
  aumento:  { color: "#8e44ad", ancho: 3, alfa: 1, flujo: true },
  corte:    { color: "#c0392b", ancho: 3.4, alfa: 1, guion: true },
  hover:    { color: "#2e5aac", ancho: 1.6, alfa: 1, flujo: true },
  foco:     { color: "#11263f", ancho: 2.6, alfa: 1, flujo: true },
};

// Significado de cada tipo de acceso en una arista {a} -> {b}. La arista se lee
// siempre igual: quien controla el origen puede llegar a controlar el destino.
const ACCESOS = {
  MEMBER_OF: "{a} es miembro del grupo {b} y hereda sus permisos.",
  CONTAINS: "{b} está dentro de {a} (OU o dominio). Acceso estructural, no se revoca.",
  GP_LINK: "La política {a} se aplica sobre {b}. Acceso estructural, no se revoca.",
  ADMIN_TO: "{a} es administrador local del equipo {b}.",
  HAS_SESSION: "{b} tiene una sesión abierta en el equipo {a}; quien controla {a} puede robar sus credenciales.",
  GENERIC_ALL: "{a} tiene control total sobre {b}.",
  GENERIC_WRITE: "{a} puede modificar los atributos de {b}.",
  WRITE_DACL: "{a} puede cambiar los permisos de {b} y concederse cualquier derecho.",
  WRITE_OWNER: "{a} puede cambiar el propietario de {b} y apropiarse de él.",
  OWNS: "{a} es propietario de {b} y puede cambiar sus permisos.",
  CAN_RDP: "{a} puede iniciar sesión por escritorio remoto en el equipo {b}.",
  EXECUTE_DCOM: "{a} puede ejecutar código de forma remota en {b} mediante DCOM.",
  ALLOWED_TO_DELEGATE: "{a} puede suplantar usuarios ante el equipo {b} por delegación.",
  DC_SYNC: "{a} puede replicar el dominio {b} y extraer sus credenciales (DCSync).",
  GET_CHANGES: "{a} puede replicar cambios del dominio {b}; junto con GET_CHANGES_ALL permite DCSync.",
  GET_CHANGES_ALL: "{a} puede replicar todos los cambios del dominio {b}, incluidos los secretos.",
};
function significado(tipo, a = "A", b = "B") {
  const plantilla = Object.prototype.hasOwnProperty.call(ACCESOS, tipo)
    ? ACCESOS[tipo] : "{a} tiene un acceso de tipo " + tipo + " sobre {b}.";
  return plantilla.replace(/\{a\}/g, a).replace(/\{b\}/g, b);
}

// Con un backend local incrustado (visor offline) las rutas se resuelven en el
// navegador; si no, se piden al servidor.
function api(path) {
  if (typeof window.backendLocal === "function") return Promise.resolve().then(() => window.backendLocal(path));
  return fetch(path).then(r => r.json());
}
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
function colorNodo(i) {
  if (i === objetivo) return "#c0392b";
  const d = posPorId.get(i);
  if (d.hv) return "#e67e22";
  return COLOR[d.tipo] || "#7f8c8d";
}

// ------------------------------------------------------------------
// Modelo del grafo (una sola vez por objetivo)
// ------------------------------------------------------------------
function construir() {
  nodos = []; pares = new Map(); enlaces = []; paresPorTipo = new Map();
  filtroTipo = null; hoverArista = null;
  posPorId = new Map();
  for (const nd of grafo.nodos) {
    // Arranca cerca del centro sobre la disposicion radial, de modo que el grafo
    // se despliega desde el objetivo mientras la simulacion lo acomoda.
    const n = { i: nd.i, nombre: nd.nombre, tipo: nd.tipo, hv: nd.hv, rx: nd.x, ry: nd.y,
                x: nd.x * 0.12 + (Math.random() - .5) * 8, y: nd.y * 0.12 + (Math.random() - .5) * 8,
                vx: 0, vy: 0, fx: null, fy: null, arrastrado: false,
                alfaVis: 0, escala: 1, salen: [], entran: [], vecinos: new Set() };
    if (n.i === objetivo) { n.x = n.y = 0; n.fx = n.fy = 0; }
    nodos.push(n); posPorId.set(n.i, n);
  }
  const porEnlace = new Map();
  for (const a of grafo.aristas) {
    const s = posPorId.get(a[0]), t = posPorId.get(a[1]);
    if (!s || !t || s === t) continue;
    const k = a[0] + "," + a[1];
    let p = pares.get(k);
    if (!p) {
      p = { s, t, tipos: [], semilla: Math.random() };
      pares.set(k, p); s.salen.push(p); t.entran.push(p);
    }
    p.tipos.push(a[2]);
    if (!paresPorTipo.has(a[2])) paresPorTipo.set(a[2], new Set());
    paresPorTipo.get(a[2]).add(p);
    s.vecinos.add(t.i); t.vecinos.add(s.i);
    const ku = Math.min(a[0], a[1]) + "," + Math.max(a[0], a[1]);
    if (!porEnlace.has(ku)) { const e = { a: s, b: t }; porEnlace.set(ku, e); enlaces.push(e); }
  }
  // Fuerza y sesgo de cada resorte segun el grado, para que los nodos muy
  // conectados no dominen la disposicion.
  const cuenta = new Map();
  for (const e of enlaces) {
    cuenta.set(e.a, (cuenta.get(e.a) || 0) + 1);
    cuenta.set(e.b, (cuenta.get(e.b) || 0) + 1);
  }
  for (const e of enlaces) {
    const ca = cuenta.get(e.a), cb = cuenta.get(e.b);
    e.fuerza = 1 / Math.min(ca, cb);
    e.sesgo = ca / (ca + cb);
  }
  for (const n of nodos) {
    n.radio = n.i === objetivo ? 11 : (n.hv ? 7.5 : 4 + Math.min(4, Math.sqrt(n.vecinos.size) * 0.8));
    n.prof = Infinity;
  }
  // Distancia en saltos hasta el objetivo (BFS sobre aristas invertidas); se
  // usa para escalonar animaciones que parten del objetivo hacia afuera.
  const raiz = posPorId.get(objetivo);
  if (raiz) {
    raiz.prof = 0;
    const cola = [raiz];
    for (let h = 0; h < cola.length; h++) {
      for (const p of cola[h].entran) {
        if (p.s.prof === Infinity) { p.s.prof = cola[h].prof + 1; cola.push(p.s); }
      }
    }
  }
  hover = ultimoHover = null; hoverMezcla = 0; gesto = null; vuelo = null;
  // La camara empieza centrada en el objetivo; el ajuste automatico la abre
  // a medida que el grafo se expande.
  cam = { k: 1, x: ancho / 2, y: alto / 2 };
  vis = visVacio(false);
  sim.alfa = 1; sim.alfaObjetivo = 0; autoAjuste = true;
  prepararRadial();
  if (MOV_REDUCIDO) {
    for (let k = 0; k < 300; k++) pasoSimulacion();
    sim.alfa = 0;
    for (const n of nodos) n.alfaVis = 1;
    ajustarVista(false);
  }
  sucio = true;
}

function visVacio(dim, previo) {
  return { atenuar: dim, nodos: new Map(), aristas: new Map(), extra: [], insignias: new Map(),
           retrasos: new Map(), aparicion: new Map(), hasta: 0,
           previoN: previo ? previo.nodos : new Map(), previoA: previo ? previo.aristas : new Map() };
}
function resetVisual(dim) {
  vis = visVacio(dim, vis);
  sucio = true;
}
function pinta(i, opts) {
  const previo = vis.nodos.get(i) || {};
  vis.nodos.set(i, Object.assign(previo, opts || {}));
  sucio = true;
}
function pintaArista(s, d, t, cls, retraso) {
  const k = s + "," + d;
  vis.aristas.set(k, cls);
  if (retraso) vis.retrasos.set(k, retraso);
  sucio = true;
}
// Compara el cuadro recien construido con el anterior y programa la animacion
// de aparicion solo para lo que cambio, de modo que avanzar un paso anima lo
// nuevo sin repetir lo que ya estaba en pantalla.
function cerrarCuadro() {
  const ahora = performance.now();
  for (const [i, v] of vis.nodos) {
    const a = vis.previoN.get(i);
    const cambia = !a || a.anillo !== v.anillo || a.fill !== v.fill || !!a.frontera !== !!v.frontera;
    v.t0 = cambia ? ahora + (v.retraso || 0) : -Infinity;
    if (cambia) vis.hasta = Math.max(vis.hasta, v.t0 + 500);
  }
  for (const [k, cls] of vis.aristas) {
    if (vis.previoA.get(k) === cls) continue;
    const t0 = ahora + (vis.retrasos.get(k) || 0);
    vis.aparicion.set(k, t0);
    vis.hasta = Math.max(vis.hasta, t0 + 400);
  }
  for (const c of vis.extra) {
    c.t0 = c.estilo.flujo ? ahora : -Infinity;
    if (c.estilo.flujo) vis.hasta = Math.max(vis.hasta, ahora + c.ids.length * 110 + 100);
  }
  sucio = true;
}
function progreso(t, t0, ms) { return t0 === -Infinity ? 1 : Math.max(0, Math.min(1, (t - t0) / ms)); }

// ------------------------------------------------------------------
// Reproduccion de la traza
// ------------------------------------------------------------------
function prepararTraza(t) {
  traza = t;
  soltarFijado();
  // Indice del ultimo cuadro: uno por paso o camino de aumento, mas el cuadro
  // final que muestra el resultado (camino hallado o corte minimo).
  frames = t.algoritmo === "defensa" ? t.caminos.length : t.pasos.length;
  frameActual = 0;
  document.getElementById("rngFrame").max = frames;
  document.getElementById("reproductor").classList.add("visible");
  mostrarFrame(0);
  // La reproduccion arranca sola; el reproductor queda visible para pausar,
  // retroceder o cambiar la velocidad en cualquier momento.
  play();
}

function mostrarFrame(f) {
  frameActual = Math.max(0, Math.min(f, frames));
  metrica("mPaso", frameActual);
  if (traza.algoritmo === "defensa") renderDefensa(frameActual);
  else renderBusqueda(frameActual);
  cerrarCuadro();
  // Linea de tiempo y botones del reproductor.
  const rng = document.getElementById("rngFrame");
  rng.value = frameActual;
  rng.style.setProperty("--p", (frames ? frameActual / frames * 100 : 100) + "%");
  document.getElementById("contador").textContent = `${frameActual} / ${frames}`;
  document.getElementById("btnInicio").disabled = document.getElementById("btnAtras").disabled = frameActual === 0;
  document.getElementById("btnPaso").disabled = document.getElementById("btnFin").disabled = frameActual >= frames;
}

function renderBusqueda(f) {
  resetVisual(true);
  const esDij = traza.algoritmo === "dijkstra";
  const n = traza.pasos.length;
  // En el cuadro final la exploracion pasa a segundo plano para que destaque el camino.
  const final = f >= n && traza.encontrado;
  const cls = final ? "explorada" : (esDij ? "relaja" : "descubre");
  // Estado acumulado: nodos cerrados antes del cuadro f, frontera (descubiertos
  // sin expandir) y la mejor distancia conocida de cada nodo.
  const cerrados = new Set(), frontera = new Set();
  const dist = new Map([[origen, 0]]);
  for (let k = 0; k < Math.min(f + 1, n); k++) {
    const p = traza.pasos[k];
    if (k < f) cerrados.add(p.nodo);
    for (const a of (esDij ? p.relaja : p.descubre)) {
      if (k < f) pintaArista(a[0], a[1], a[2], cls);
      frontera.add(a[1]);
      dist.set(a[1], esDij ? a[3] : (dist.get(a[0]) || 0) + 1);
    }
  }
  for (const c of cerrados) pinta(c, {});
  if (!final) for (const i of frontera) if (!cerrados.has(i)) pinta(i, { frontera: true });
  // Cuadro final: el camino se ilumina tramo a tramo desde el origen.
  if (final) {
    const enCamino = new Set([origen]);
    traza.camino.forEach((a, j) => {
      pintaArista(a[0], a[1], a[2], "camino", j * 120);
      enCamino.add(a[1]);
      if (a[1] !== objetivo) pinta(a[1], { anillo: "#e67e22", frontera: false, retraso: (j + 1) * 120 });
    });
    for (const i of enCamino) if (dist.has(i)) vis.insignias.set(i, String(dist.get(i)));
    if (origen !== null) pinta(origen, { anillo: "#11263f", frontera: false });
    pinta(objetivo, { anillo: "#c0392b", frontera: false, pulso: true, retraso: traza.camino.length * 120 });
    barra(`Camino ${esDij ? "de menor esfuerzo" : "más corto"} hallado` +
      (esDij ? `: peso <b>${traza.peso}</b>, ` : `: `) + `<b>${traza.saltos}</b> ${traza.saltos === 1 ? "salto" : "saltos"}`);
    panelTexto(panelCamino(esDij));
    metrica("mA", cerrados.size, esDij ? "cerrados" : "expandidos");
    metrica("mB", esDij ? traza.peso : traza.saltos, esDij ? "peso" : "saltos");
    return;
  }
  // Cuadro intermedio: el nodo que se expande pulsa y sus aristas crecen
  // hacia los vecinos que descubre o relaja.
  if (f < n) {
    for (const [i, d] of dist) if (cerrados.has(i) || frontera.has(i) || i === origen) vis.insignias.set(i, String(d));
    const p = traza.pasos[f];
    pinta(p.nodo, { anillo: "#e67e22", frontera: false, pulso: true });
    const aristas = esDij ? p.relaja : p.descubre;
    for (const a of aristas) { pintaArista(a[0], a[1], a[2], cls); pinta(a[1], { anillo: "#2e5aac" }); }
    const nom = esc(corto(posPorId.get(p.nodo).nombre));
    if (esDij) barra(`Cierra <b>${nom}</b> (dist ${p.dist}), relaja <b>${p.relaja.length}</b> ${p.relaja.length === 1 ? "arista" : "aristas"}`);
    else barra(`Expande <b>${nom}</b>, descubre <b>${p.descubre.length}</b> ${p.descubre.length === 1 ? "objeto" : "objetos"}`);
    panelTexto((esDij
      ? `<strong class="tit">Dijkstra</strong>Cierra en cada paso el nodo de menor distancia acumulada y relaja sus aristas, actualizando las distancias hacia el objetivo.`
      : `<strong class="tit">BFS</strong>Explora por niveles: expande un nodo y descubre sus vecinos no visitados. El primer camino que llega al objetivo es el más corto en saltos.`) +
      leyendaEstados([
        ["anillo-n", esDij ? "Nodo que se cierra en este paso" : "Nodo que se expande en este paso"],
        ["hueca", "Frontera: descubierto y pendiente"],
        ["solida", esDij ? "Cerrado, con distancia definitiva" : "Ya expandido"],
        ["insignia", esDij ? "Distancia acumulada (peso)" : "Saltos desde el origen"],
      ]));
  }
  let pendientes = 0;
  for (const i of frontera) if (!cerrados.has(i)) pendientes++;
  metrica("mA", cerrados.size, esDij ? "cerrados" : "expandidos");
  metrica("mB", pendientes, "en frontera");
}

function renderDefensa(f) {
  resetVisual(false);
  const t = traza;
  // Caminos de aumento hallados hasta el cuadro f.
  const hasta = Math.min(f, t.caminos.length);
  for (let k = 0; k < hasta; k++) dibujaCamino(t.caminos[k], "#b9a7d6");
  if (f < t.caminos.length) {
    dibujaCamino(t.caminos[f], "#8e44ad", true);
    pinta(t.caminos[f][0], { anillo: "#8e44ad", pulso: true });
    barra(`Camino de aumento <b>${f + 1}</b> de ${t.caminos.length} (rutas disjuntas en aristas)`);
    panelTexto(`<strong class="tit">Edmonds-Karp</strong>Cada camino de aumento es una ruta ` +
      `independiente de un objeto de entrada al objetivo. El número de estos caminos es ` +
      `el flujo máximo.` + leyendaEstados([
        ["linea-m", "Camino de aumento actual, de la fuente al objetivo"],
        ["linea-c", "Caminos de aumento ya encontrados"],
      ]));
    metrica("mA", f + 1, "caminos");
    metrica("mB", t.antes, "alcanzan");
  } else {
    // Cuadro final: el corte minimo.
    // Primero aparece el corte; luego los objetos aislados se vuelven verdes en
    // una ola que se aleja del objetivo segun su distancia en saltos.
    t.corte.forEach((a, j) => pintaArista(a[0], a[1], a[2], "corte", j * 40));
    const inicio = Math.min(t.corte.length * 40, 600) + 150;
    for (const i of t.seguros) {
      const nd = posPorId.get(i);
      const prof = nd && isFinite(nd.prof) ? nd.prof : 1;
      pinta(i, { fill: "#1a7f43", anillo: "#1a7f43", retraso: inicio + prof * 140 + (i % 7) * 15 });
    }
    pinta(objetivo, { anillo: "#c0392b", pulso: true });
    barra(`Corte mínimo: <b>${t.flujo}</b> accesos. Exposición <b>${t.antes}</b> &rarr; <b>${t.despues}</b>`);
    panelTexto(panelCorte(t));
    metrica("mA", t.flujo, "a revocar");
    metrica("mB", t.despues, "alcanzan");
  }
}

function dibujaCamino(ids, color, fuerte) {
  vis.extra.push({ ids, estilo: { color, ancho: fuerte ? 3.2 : 1.8, alfa: fuerte ? 1 : 0.5,
                                  flujo: !!fuerte, sinFlecha: !fuerte } });
  if (fuerte) for (const i of ids) pinta(i, { anillo: "#8e44ad" });
  sucio = true;
}

function leyendaEstados(filas) {
  return `<div class="estados">` + filas.map(([clase, texto]) =>
    `<span><i class="muestra ${clase}">${clase === "insignia" ? "3" : ""}</i>${texto}</span>`).join("") + `</div>`;
}
function nombreDe(i) { return esc(corto(posPorId.get(i).nombre)); }

// Camino final como lista de pasos: cada objeto es clicable y cada salto
// muestra el tipo de acceso (y su peso en Dijkstra).
function panelCamino(esDij) {
  const nodoLi = (i, j) => `<li class="nodo-ruta" data-i="${i}" style="--i:${j}">` +
    `<i class="punto" style="background:${colorNodo(i)}"></i><span>${nombreDe(i)}</span>` +
    `<small>${esc(posPorId.get(i).tipo)}</small></li>`;
  const pesosUsados = traza.pesosUsados || {};
  let j = 0;
  const items = [nodoLi(traza.camino[0][0], j++)];
  for (const a of traza.camino) {
    const peso = esDij && a[2] in pesosUsados ? ` &middot; peso ${pesosUsados[a[2]]}` : "";
    const explica = significado(a[2], corto(posPorId.get(a[0]).nombre), corto(posPorId.get(a[1]).nombre));
    items.push(`<li class="salto" style="--i:${j++}">${esc(a[2])}${peso}<small>${esc(explica)}</small></li>`);
    items.push(nodoLi(a[1], j++));
  }
  const s = traza.saltos;
  return `<strong class="tit">Camino ${esDij ? "de menor esfuerzo" : "más corto"}</strong>` +
    `${s} ${s === 1 ? "salto" : "saltos"}${esDij ? `, peso total ${traza.peso}` : ""}. ` +
    `Haz clic en un objeto para ubicarlo en el grafo.<ol class="ruta">${items.join("")}</ol>`;
}

function panelCorte(t) {
  const pct = t.antes ? t.despues / t.antes * 100 : 0;
  const filas = t.corte.map((a, j) => `<li data-i="${a[0]}" style="--i:${Math.min(j, 14)}" ` +
    `title="${esc(significado(a[2], corto(posPorId.get(a[0]).nombre), corto(posPorId.get(a[1]).nombre)))}">` +
    `${nombreDe(a[0])} &rarr; ${nombreDe(a[1])}<span class="tipo">${esc(a[2])}</span></li>`).join("");
  return `<strong class="tit">Corte mínimo = flujo máximo = ${t.flujo}</strong>` +
    `Por el teorema de flujo máximo y corte mínimo, revocar estos ${t.flujo} accesos es el plan ` +
    `con menos accesos que aísla el objetivo, y ningún plan más corto lo consigue.` +
    `<div class="exposicion"><div class="cifras"><span>Objetos que alcanzan el objetivo</span>` +
    `<span>${t.antes} &rarr; ${t.despues}</span></div>` +
    `<div class="barra-exp"><div class="relleno" data-w="${pct}"></div></div></div>` +
    leyendaEstados([["guion", "Acceso a revocar"], ["verde", "Objeto que queda aislado"]]) +
    `<div class="subtitulo">Accesos a revocar (${t.corte.length})</div><ul class="cortes">${filas}</ul>`;
}

// Actualiza una metrica; los valores numericos cuentan hasta el nuevo valor.
function metrica(id, valor, etiqueta) {
  const el = document.getElementById(id);
  if (etiqueta !== undefined) document.getElementById(id + "T").textContent = etiqueta;
  const num = typeof valor === "number" && isFinite(valor);
  const previo = el.dataset.v === undefined || el.dataset.v === "" ? NaN : Number(el.dataset.v);
  el.dataset.v = num ? valor : "";
  if (!num || MOV_REDUCIDO || isNaN(previo)) { el.textContent = valor; return; }
  if (previo === valor) { el.textContent = valor; return; }
  const t0 = performance.now(), ms = 380;
  const tick = t => {
    if (el.dataset.v !== String(valor)) return;  // otro valor tomo su lugar
    const p = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(previo + (valor - previo) * e);
    if (p < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// Nombre visible: sin el dominio tras la arroba y, en los equipos (FQDN como
// COMP00218.TestCompany.Local), solo la primera etiqueta. El dominio mismo
// (TestCompany.Local) se conserva completo.
function corto(n) {
  const base = n.split("@")[0];
  const punto = base.indexOf(".");
  return punto > 0 && base.indexOf(".", punto + 1) > 0 ? base.slice(0, punto) : base;
}
function barra(html) {
  const b = document.getElementById("barra");
  if (b.innerHTML !== html) {
    b.innerHTML = html;
    b.classList.remove("cambio"); void b.offsetWidth; b.classList.add("cambio");
  }
  b.classList.add("visible");
}
function ocultarBarra() { document.getElementById("barra").classList.remove("visible"); }
// Solo reemplaza (y anima) el panel cuando su contenido cambia de verdad, para
// que avanzar pasos con el mismo texto no lo haga parpadear.
function panelTexto(html) {
  const p = document.getElementById("panel");
  if (p.dataset.fuente === html) return;
  p.dataset.fuente = html;
  p.innerHTML = html;
  p.classList.remove("cambio"); void p.offsetWidth; p.classList.add("cambio");
  const r = p.querySelector(".relleno");
  if (r) requestAnimationFrame(() => requestAnimationFrame(() => { r.style.width = r.dataset.w + "%"; }));
}

// ------------------------------------------------------------------
// Tarjeta de detalle del objeto seleccionado
// ------------------------------------------------------------------
let seleccionado = null, pestana = "salen";
let fijado = null;   // nodo cuyas conexiones quedan encendidas tras un clic
function abrirDetalle(n) {
  seleccionado = n;
  sucio = true;
  document.getElementById("detPunto").style.background = colorNodo(n.i);
  document.getElementById("detNombre").textContent = corto(n.nombre);
  document.getElementById("detCompleto").textContent = n.nombre;
  const chips = [`<span class="chip">${esc(n.tipo)}</span>`];
  if (n.i === objetivo) chips.push(`<span class="chip obj">Objetivo</span>`);
  else if (n.hv) chips.push(`<span class="chip hv">Alto valor</span>`);
  if (n.i !== objetivo && isFinite(n.prof)) {
    chips.push(`<span class="chip">A ${n.prof} ${n.prof === 1 ? "salto" : "saltos"} del objetivo</span>`);
  }
  document.getElementById("detChips").innerHTML = chips.join("");
  document.getElementById("detSalen").textContent = n.salen.length;
  document.getElementById("detEntran").textContent = n.entran.length;
  actualizarBotonOrigen();
  pintarConexiones();
  document.getElementById("detalle").classList.add("abierto");
  document.querySelector("main").classList.add("con-detalle");
}
function cerrarDetalle() {
  soltarFijado();
  if (!seleccionado) return;
  seleccionado = null;
  sucio = true;
  document.getElementById("detalle").classList.remove("abierto");
  document.querySelector("main").classList.remove("con-detalle");
}
function actualizarBotonOrigen() {
  if (!seleccionado) return;
  const b = document.getElementById("btnUsarOrigen");
  const esOrigen = seleccionado.i === origen;
  b.disabled = esOrigen || seleccionado.i === objetivo;
  b.textContent = esOrigen ? "Es el origen" : (seleccionado.i === objetivo ? "Es el objetivo" : "Usar como origen");
}
function elegirPestana(v) {
  pestana = v;
  document.querySelectorAll("#segConexiones button").forEach(b => {
    const activo = b.dataset.v === v;
    b.classList.toggle("activo", activo); b.setAttribute("aria-selected", activo);
  });
  pintarConexiones();
}
// Lista de conexiones en el sentido elegido; el objetivo y los objetos de alto
// valor van primero porque son los que importan para el analisis.
function pintarConexiones() {
  const n = seleccionado, ul = document.getElementById("detLista");
  if (!n) return;
  const lista = (pestana === "salen" ? n.salen.map(p => ({ otro: p.t, tipos: p.tipos }))
                                     : n.entran.map(p => ({ otro: p.s, tipos: p.tipos })));
  const peso = o => (o.i === objetivo ? 2 : 0) + (o.hv ? 1 : 0);
  lista.sort((a, b) => peso(b.otro) - peso(a.otro) || corto(a.otro.nombre).localeCompare(corto(b.otro.nombre)));
  ul.innerHTML = "";
  if (!lista.length) {
    ul.innerHTML = `<li class="vacia">${pestana === "salen" ? "No controla ningún objeto del subgrafo."
                                                            : "Ningún objeto del subgrafo lo controla."}</li>`;
    return;
  }
  lista.forEach(({ otro, tipos }, j) => {
    const li = document.createElement("li");
    li.style.setProperty("--i", Math.min(j, 14));
    const unicos = [...new Set(tipos)];
    const [a, b] = pestana === "salen" ? [n, otro] : [otro, n];
    const explica = unicos.map(t => t + ": " + significado(t, corto(a.nombre), corto(b.nombre))).join("\n");
    li.title = explica;
    li.innerHTML = `<i class="punto" style="background:${colorNodo(otro.i)}"></i>` +
      `<span class="nom">${esc(corto(otro.nombre))}</span><span class="tipos">${esc(unicos.join(", "))}</span>`;
    li.addEventListener("mouseenter", () => ponerHover(otro));
    li.addEventListener("mouseleave", () => ponerHover(null));
    li.addEventListener("click", () => {
      ponerHover(null); enfocarNodo(otro); abrirDetalle(otro);
      if (fijado) fijado = otro;
    });
    ul.appendChild(li);
  });
}
function alClicNodo(n) {
  if (algSel !== "defensa") seleccionar(n.i);
  abrirDetalle(n);
  fijado = n;
  sucio = true;
}

function aviso(texto, tipo = "error") {
  const el = document.createElement("div");
  el.className = "aviso " + tipo;
  el.textContent = texto;
  document.getElementById("avisos").appendChild(el);
  setTimeout(() => {
    el.classList.add("sale");
    el.addEventListener("animationend", () => el.remove());
  }, 3800);
}

// ------------------------------------------------------------------
// Controles de reproduccion
// ------------------------------------------------------------------
let velocidad = 1;
function play() {
  if (!traza) return;
  if (temporizador) { pausa(); return; }
  soltarFijado();
  if (frameActual >= frames) mostrarFrame(0);
  const b = document.getElementById("btnPlay");
  b.classList.add("activo"); b.setAttribute("aria-label", "Pausar");
  programarReproduccion();
}
function programarReproduccion() {
  clearInterval(temporizador);
  temporizador = setInterval(() => {
    if (frameActual >= frames) { pausa(); return; }
    mostrarFrame(frameActual + 1);
  }, 900 / velocidad);
}
function pausa() {
  clearInterval(temporizador); temporizador = null;
  const b = document.getElementById("btnPlay");
  b.classList.remove("activo"); b.setAttribute("aria-label", "Reproducir");
}
function irA(f) { if (!traza) return; pausa(); soltarFijado(); mostrarFrame(f); }
function paso() { irA(frameActual + 1); }
function atras() { irA(frameActual - 1); }
function reiniciar() { irA(0); }
function alFinal() { irA(frames); }
function elegirVelocidad(v) {
  velocidad = v;
  document.querySelectorAll("#velocidades button").forEach(b => {
    const activo = Number(b.dataset.v) === v;
    b.classList.toggle("activo", activo); b.setAttribute("aria-checked", activo);
  });
  if (temporizador) programarReproduccion();
}

// ------------------------------------------------------------------
// Busqueda de objetos
// ------------------------------------------------------------------
const txtBuscar = document.getElementById("txtBuscar");
const listaRes = document.getElementById("resultados");
let resultados = [], resActivo = 0;
let destello = null;   // anillo que marca el objeto elegido en la busqueda

function buscar() {
  const q = txtBuscar.value.trim().toLowerCase();
  if (!q) { cerrarBusqueda(); return; }
  const empieza = n => corto(n.nombre).toLowerCase().startsWith(q) ? 0 : 1;
  resultados = nodos.filter(n => n.nombre.toLowerCase().includes(q))
    .sort((a, b) => empieza(a) - empieza(b) || corto(a.nombre).localeCompare(corto(b.nombre)))
    .slice(0, 8);
  resActivo = 0;
  listaRes.innerHTML = "";
  if (!resultados.length) {
    listaRes.innerHTML = `<li class="nada">Sin coincidencias en este subgrafo</li>`;
  }
  resultados.forEach((n, j) => {
    const li = document.createElement("li");
    li.setAttribute("role", "option");
    const nom = corto(n.nombre), pos = nom.toLowerCase().indexOf(q);
    const marcado = pos < 0 ? esc(nom) : esc(nom.slice(0, pos)) + "<mark>" +
      esc(nom.slice(pos, pos + q.length)) + "</mark>" + esc(nom.slice(pos + q.length));
    li.innerHTML = `<i class="punto" style="background:${colorNodo(n.i)}"></i>` +
      `<span class="nom">${marcado}</span><small>${esc(n.tipo)}</small>`;
    li.addEventListener("mouseenter", () => { resActivo = j; marcarResultado(); });
    li.addEventListener("mouseleave", () => ponerHover(null));
    li.addEventListener("mousedown", e => { e.preventDefault(); elegirResultado(n); });
    listaRes.appendChild(li);
  });
  marcarResultado();
  listaRes.classList.add("abierto");
}
// Marca la opcion activa y la resalta en el grafo, como un hover remoto.
function marcarResultado() {
  [...listaRes.children].forEach((li, j) => li.classList.toggle("activo", j === resActivo));
  const n = resultados[resActivo];
  if (n) ponerHover(n);
}
function cerrarBusqueda() { listaRes.classList.remove("abierto"); }
function elegirResultado(n) {
  cerrarBusqueda();
  txtBuscar.value = "";
  txtBuscar.blur();
  ponerHover(null);
  enfocarNodo(n, Math.max(cam.k, 1.8));
  destello = { n, t0: performance.now() };
  alClicNodo(n);
}
txtBuscar.addEventListener("input", buscar);
txtBuscar.addEventListener("focus", () => { if (txtBuscar.value.trim()) buscar(); });
txtBuscar.addEventListener("blur", () => { cerrarBusqueda(); ponerHover(null); });
txtBuscar.addEventListener("keydown", e => {
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    const d = e.key === "ArrowDown" ? 1 : -1;
    resActivo = Math.max(0, Math.min(resultados.length - 1, resActivo + d));
    marcarResultado();
  } else if (e.key === "Enter") {
    if (resultados[resActivo]) elegirResultado(resultados[resActivo]);
  } else if (e.key === "Escape") {
    txtBuscar.value = ""; txtBuscar.blur();
  }
});

// ------------------------------------------------------------------
// Leyenda, disposicion, zoom y panel
// ------------------------------------------------------------------
let filtroCat = null;  // categoria resaltada desde la leyenda
const CATEGORIAS = [
  ["objetivo", "Objetivo", "#c0392b"], ["hv", "Alto valor", "#e67e22"],
  ["User", "Usuario", "#2e5aac"], ["Computer", "Equipo", "#16a085"],
  ["Group", "Grupo", "#8e44ad"], ["otros", "GPO, OU y dominio", "#7f8c8d"],
];
function categoria(n) {
  if (n.i === objetivo) return "objetivo";
  if (n.hv) return "hv";
  return ["User", "Computer", "Group"].includes(n.tipo) ? n.tipo : "otros";
}
let pestanaLeyenda = "objetos";
const ESTILOS_ARISTA_LEYENDA = [
  ["base", "Acceso A &rarr; B: quien controla A puede llegar a controlar B"],
  ["cursor", "Accesos del objeto enfocado o explorados por la búsqueda"],
  ["camino", "Camino hallado por BFS o Dijkstra"],
  ["aumento", "Camino de aumento del flujo máximo"],
  ["corte", "Acceso a revocar (corte mínimo)"],
];
// Boton de la leyenda que resalta su grupo mientras tiene el cursor o el foco.
function botonLeyenda(html, activar) {
  const b = document.createElement("button");
  b.innerHTML = html;
  const fijar = on => { activar(on); sucio = true; };
  b.addEventListener("mouseenter", () => fijar(true));
  b.addEventListener("mouseleave", () => fijar(false));
  b.addEventListener("focus", () => fijar(true));
  b.addEventListener("blur", () => fijar(false));
  return b;
}
function construirLeyenda() {
  const cont = document.getElementById("leyenda");
  cont.innerHTML = `<div class="segmentado" role="tablist" aria-label="Leyenda">` +
    `<button data-v="objetos" role="tab">Objetos</button><button data-v="accesos" role="tab">Accesos</button></div>` +
    `<div class="ley-cuerpo" data-v="objetos"><div class="titulo">Tipos de objeto</div></div>` +
    `<div class="ley-cuerpo" data-v="accesos"></div>`;
  const [cuerpoObj, cuerpoAcc] = cont.querySelectorAll(".ley-cuerpo");

  const cuenta = {};
  for (const n of nodos) cuenta[categoria(n)] = (cuenta[categoria(n)] || 0) + 1;
  for (const [cat, nombre, color] of CATEGORIAS) {
    const b = botonLeyenda(`<i class="punto" style="background:${color}"></i>${nombre}` +
      `<span class="cnt">${cuenta[cat] || 0}</span>`, on => { filtroCat = on ? cat : null; });
    b.title = "Resaltar " + nombre.toLowerCase();
    cuerpoObj.appendChild(b);
  }

  cuerpoAcc.innerHTML = `<div class="titulo">Cómo leer las aristas</div>` +
    ESTILOS_ARISTA_LEYENDA.map(([clase, texto]) =>
      `<div class="estilo-ar"><i class="muestra-ar ${clase}"></i><span>${texto}</span></div>`).join("") +
    `<div class="titulo">Tipos de acceso</div>`;
  const textoBase = "Pasa el cursor sobre un tipo para ver qué permite y resaltarlo en el grafo. " +
    "Sobre una arista del grafo verás su tipo.";
  const desc = document.createElement("div");
  desc.className = "ley-desc";
  desc.textContent = textoBase;
  cuerpoAcc.appendChild(desc);
  const porTipo = new Map();
  for (const a of grafo.aristas) porTipo.set(a[2], (porTipo.get(a[2]) || 0) + 1);
  if (!porTipo.size) desc.textContent = "No hay accesos en este subgrafo.";
  [...porTipo.entries()].sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0])).forEach(([tipo, c]) => {
    const b = botonLeyenda(`<code>${esc(tipo)}</code><span class="cnt">${c}</span>`, on => {
      filtroTipo = on ? tipo : null;
      nodosFiltroTipo = new Set();
      if (on) for (const p of paresPorTipo.get(tipo) || []) { nodosFiltroTipo.add(p.s.i); nodosFiltroTipo.add(p.t.i); }
      desc.textContent = on ? significado(tipo) : textoBase;
    });
    cuerpoAcc.appendChild(b);
  });

  cont.querySelectorAll(".segmentado button").forEach(b =>
    b.addEventListener("click", () => mostrarPestanaLeyenda(b.dataset.v)));
  mostrarPestanaLeyenda(pestanaLeyenda);
}
function mostrarPestanaLeyenda(v) {
  pestanaLeyenda = v;
  const cont = document.getElementById("leyenda");
  cont.querySelectorAll(".segmentado button").forEach(b => {
    const activo = b.dataset.v === v;
    b.classList.toggle("activo", activo); b.setAttribute("aria-selected", activo);
  });
  cont.querySelectorAll(".ley-cuerpo").forEach(c => { c.hidden = c.dataset.v !== v; });
}

function cambiarDisposicion(v) {
  if (v === disposicion) return;
  disposicion = v;
  // En la vista radial el objetivo es el centro de los anillos.
  const obj = posPorId.get(objetivo);
  if (obj && v === "radial") { obj.fx = 0; obj.fy = 0; }
  // La simulacion se recalienta y lleva los nodos a la nueva disposicion.
  sim.alfa = Math.max(sim.alfa, v === "radial" ? 1 : 0.6);
  if (MOV_REDUCIDO) {
    for (let k = 0; k < 300; k++) pasoSimulacion();
    sim.alfa = 0;
  }
  autoAjuste = true; vuelo = null; sucio = true;
  document.querySelectorAll("#segDisposicion button").forEach(b => {
    const activo = b.dataset.v === v;
    b.classList.toggle("activo", activo); b.setAttribute("aria-checked", activo);
  });
}
function zoomAnimado(f) {
  const k = Math.max(0.12, Math.min(6, cam.k * f));
  const cx = (ancho / 2 - cam.x) / cam.k, cy = (alto / 2 - cam.y) / cam.k;
  volar({ k, x: ancho / 2 - cx * k, y: alto / 2 - cy * k }, 260);
}
function alternarPanel() { document.getElementById("app").classList.toggle("sin-panel"); }
function alternarAyuda(abrir) {
  const a = document.getElementById("ayuda");
  a.classList.toggle("abierta", abrir === undefined ? !a.classList.contains("abierta") : abrir);
}

// Atajos de teclado; se ignoran mientras se escribe en un campo.
document.addEventListener("keydown", e => {
  const activo = document.activeElement;
  const enCampo = activo && /^(INPUT|SELECT|TEXTAREA)$/.test(activo.tagName);
  if (e.key === "Escape") {
    alternarAyuda(false); ponerHover(null); ponerHoverArista(null); cerrarDetalle();
    filtroCat = null; filtroTipo = null; sucio = true;
    return;
  }
  if (enCampo || e.ctrlKey || e.metaKey || e.altKey) return;
  const sobreBoton = activo && activo.tagName === "BUTTON";
  switch (e.key) {
    case "/": e.preventDefault(); txtBuscar.focus(); break;
    case " ": if (!sobreBoton && traza) { e.preventDefault(); play(); } break;
    case "ArrowRight": e.preventDefault(); paso(); break;
    case "ArrowLeft": e.preventDefault(); atras(); break;
    case "Home": e.preventDefault(); reiniciar(); break;
    case "End": e.preventDefault(); alFinal(); break;
    case "e": case "E": ejecutar(); break;
    case "f": case "F": ajustarVista(true); break;
    case "+": case "=": zoomAnimado(1.3); break;
    case "-": case "_": zoomAnimado(1 / 1.3); break;
    case "r": case "R": cambiarDisposicion(disposicion === "fuerzas" ? "radial" : "fuerzas"); break;
    case "p": case "P": alternarPanel(); break;
    case "?": alternarAyuda(); break;
  }
});

// ------------------------------------------------------------------
// Carga de datos y acciones
// ------------------------------------------------------------------
async function cargarObjetivos() {
  const d = await api("/api/objetivos");
  const sel = document.getElementById("selObjetivo");
  d.objetivos.forEach(o => {
    const op = document.createElement("option");
    op.value = o.i; op.textContent = o.nombre;
    if (o.i === d.porOmision) op.selected = true;
    sel.appendChild(op);
  });
  await cargarGrafo(d.porOmision);
}

async function cargarGrafo(obj) {
  pausa();
  const carga = document.getElementById("cargando");
  carga.classList.remove("oculto");
  let d;
  try {
    d = await api("/api/grafo?objetivo=" + obj);
  } catch (e) {
    carga.classList.add("oculto");
    aviso("No se pudo cargar el grafo: " + e);
    return;
  }
  if (d.error) { carga.classList.add("oculto"); aviso("Error: " + d.error); return; }
  cerrarDetalle();
  grafo = d; objetivo = obj; origen = null; traza = null;
  construir();
  construirLeyenda();
  carga.classList.add("oculto");
  metrica("mPaso", 0);
  metrica("mA", d.totalNodos - 1, "alcanzan");
  metrica("mB", "-", "objetivo");
  mostrarOrigen();
  document.getElementById("reproductor").classList.remove("visible");
  ocultarBarra();
  const sinRutas = d.totalNodos <= 1;
  const caja = document.getElementById("sinRutas");
  caja.hidden = !sinRutas;
  caja.innerHTML = sinRutas ? `<b>Ningún objeto alcanza este objetivo</b>No hay rutas de acceso ` +
    `hacia ${esc(corto(d.objetivoNombre))} en el directorio, así que no hay nada que recorrer ni que defender.` : "";
  document.getElementById("btnEjecutar").disabled = sinRutas;
  panelTexto(sinRutas
    ? `Objetivo: <strong>${esc(d.objetivoNombre)}</strong>. Ningún objeto puede alcanzarlo.`
    : `Objetivo: <strong>${esc(d.objetivoNombre)}</strong>. ${d.totalNodos - 1} objetos ` +
      `pueden alcanzarlo. Elige un algoritmo y pulsa Ejecutar.`);
}

function seleccionar(i) {
  if (i === objetivo) return;
  origen = i;
  sucio = true;
  mostrarOrigen();
  actualizarBotonOrigen();
}

function mostrarOrigen() {
  const chip = document.getElementById("panelOrigen");
  if (origen === null) {
    chip.classList.add("vacio");
    document.getElementById("origenNombre").textContent = "Haz clic en un nodo del grafo";
    document.getElementById("origenTipo").textContent = "";
    return;
  }
  const d = posPorId.get(origen);
  chip.classList.remove("vacio");
  // Reinicia la animacion de aparicion al cambiar de origen.
  chip.style.animation = "none"; void chip.offsetWidth; chip.style.animation = "";
  document.getElementById("origenPunto").style.background = colorNodo(origen);
  document.getElementById("origenNombre").textContent = corto(d.nombre);
  document.getElementById("origenTipo").textContent = d.tipo + (d.hv ? " de alto valor" : "");
}

async function ejecutar() {
  const alg = algSel;
  const btn = document.getElementById("btnEjecutar");
  if (btn.disabled || btn.classList.contains("ocupado") || objetivo === null) return;
  if (alg !== "defensa" && origen === null) {
    aviso("Primero elige un origen: haz clic en un nodo del grafo o búscalo.", "info");
    const chip = document.getElementById("panelOrigen");
    chip.classList.remove("sacudir"); void chip.offsetWidth; chip.classList.add("sacudir");
    return;
  }
  pausa();
  btn.classList.add("ocupado");
  try {
    let d;
    if (alg === "defensa") {
      d = await api(`/api/defensa?objetivo=${objetivo}&fuentes=${fuentesSel}`);
    } else {
      let url = `/api/${alg}?objetivo=${objetivo}&origen=${origen}`;
      if (alg === "dijkstra") url += "&pesos=" + encodeURIComponent(JSON.stringify(pesos));
      d = await api(url);
      // Copia de los pesos con que se calculo, por si se editan despues.
      if (alg === "dijkstra") d.pesosUsados = Object.assign({}, pesos);
    }
    if (d.error) { aviso("Error: " + d.error); return; }
    if ((alg !== "defensa") && !d.encontrado) { aviso("El origen no alcanza el objetivo."); return; }
    prepararTraza(d);
  } catch (e) {
    aviso("Error de red: " + e);
  } finally {
    btn.classList.remove("ocupado");
  }
}

function elegirAlgoritmo(alg) {
  algSel = alg;
  document.querySelectorAll("#algos .algo").forEach(b => {
    const activo = b.dataset.alg === alg;
    b.classList.toggle("activo", activo);
    b.setAttribute("aria-checked", activo);
  });
  ajustarInterfazAlgoritmo();
}

function ajustarInterfazAlgoritmo() {
  const alg = algSel;
  document.getElementById("bloqueOrigen").style.display = (alg === "defensa") ? "none" : "block";
  document.getElementById("bloqueFuentes").style.display = (alg === "defensa") ? "block" : "none";
  document.getElementById("togglerPesos").style.display = (alg === "dijkstra") ? "inline-flex" : "none";
  if (alg !== "dijkstra") alternarPesos(false);
}

function alternarPesos(abrir) {
  const caja = document.getElementById("pesos");
  const abierto = abrir === undefined ? !caja.classList.contains("visible") : abrir;
  caja.classList.toggle("visible", abierto);
  document.getElementById("togglerPesos").setAttribute("aria-expanded", abierto);
}

function construirPesos() {
  const cont = document.getElementById("pesosInt");
  cont.innerHTML = "";
  Object.keys(PESOS_DEF).forEach(tipo => {
    const fila = document.createElement("label"); fila.className = "pw";
    const et = document.createElement("span"); et.textContent = tipo; et.title = tipo;
    const inp = document.createElement("input");
    inp.type = "number"; inp.min = 0; inp.max = 99; inp.value = pesos[tipo];
    inp.addEventListener("change", () => {
      pesos[tipo] = Math.min(99, Math.max(0, Math.round(Number(inp.value)) || 0));
      inp.value = pesos[tipo];
    });
    fila.append(et, inp); cont.appendChild(fila);
  });
  const rest = document.createElement("button");
  rest.className = "restablecer"; rest.textContent = "Restablecer pesos";
  rest.addEventListener("click", () => { pesos = Object.assign({}, PESOS_DEF); construirPesos(); });
  cont.appendChild(rest);
}

// ------------------------------------------------------------------
// Simulacion de fuerzas
// ------------------------------------------------------------------
// En la disposicion radial cada nodo queda en el anillo de su distancia en
// saltos al objetivo. El radio de cada anillo crece con la cantidad de objetos
// que contiene, para que quepan sin encimarse, y el angulo de partida es el del
// arbol radial del backend, que mantiene juntos los subarboles.
const SEPARACION_ANILLO = 70, ESPACIO_POR_NODO = 34;
let radiosAnillo = [], mezclaRadial = 0;
function prepararRadial() {
  const cuenta = [];
  for (const n of nodos) if (isFinite(n.prof)) cuenta[n.prof] = (cuenta[n.prof] || 0) + 1;
  const radios = radiosAnillo = [0];
  for (let d = 1; d < cuenta.length; d++) {
    radios[d] = Math.max(radios[d - 1] + SEPARACION_ANILLO, (cuenta[d] || 0) * ESPACIO_POR_NODO / (2 * Math.PI));
  }
  for (const n of nodos) {
    n.anillo = isFinite(n.prof) ? radios[n.prof] : 0;
    const ang = Math.atan2(n.ry, n.rx);
    n.ax = Math.cos(ang) * n.anillo; n.ay = Math.sin(ang) * n.anillo;
  }
}

function pasoSimulacion() {
  sim.alfa += (sim.alfaObjetivo - sim.alfa) * sim.decaimiento;
  const a = sim.alfa;
  const radial = disposicion === "radial";
  // Resortes: cada enlace tiende a la distancia de reposo. En la vista radial
  // son debiles, para que no arrastren los nodos fuera de su anillo.
  const fResorte = radial ? 0.06 : 1;
  for (const e of enlaces) {
    const s = e.a, t = e.b;
    let dx = t.x + t.vx - s.x - s.vx, dy = t.y + t.vy - s.y - s.vy;
    let l = Math.hypot(dx, dy) || 1e-6;
    l = (l - DIST_RESORTE) / l * a * e.fuerza * fResorte;
    dx *= l; dy *= l;
    t.vx -= dx * e.sesgo; t.vy -= dy * e.sesgo;
    s.vx += dx * (1 - e.sesgo); s.vy += dy * (1 - e.sesgo);
  }
  // Repulsion entre todos los pares (el subgrafo es pequenio, O(n^2) basta) y,
  // en la vista radial, colision para que ningun par quede encimado.
  for (let i = 0; i < nodos.length; i++) {
    const p = nodos[i];
    for (let j = i + 1; j < nodos.length; j++) {
      const q = nodos[j];
      let dx = q.x - p.x, dy = q.y - p.y, l2 = dx * dx + dy * dy;
      if (l2 > DIST_MAX2) continue;
      if (l2 < 1) { dx = Math.random() - .5; dy = Math.random() - .5; l2 = 1; }
      const w = CARGA * a / l2;
      p.vx += dx * w; p.vy += dy * w;
      q.vx -= dx * w; q.vy -= dy * w;
      if (radial) {
        const minimo = p.radio + q.radio + 12;
        if (l2 < minimo * minimo) {
          const l = Math.sqrt(l2), m = (minimo - l) / l * 0.35;
          p.vx -= dx * m; p.vy -= dy * m;
          q.vx += dx * m; q.vy += dy * m;
        }
      }
    }
  }
  for (const n of nodos) {
    if (radial) {
      // Atraccion hacia el radio del anillo y, suave, hacia el angulo del arbol.
      const r = Math.hypot(n.x, n.y) || 1e-6;
      const kr = (n.anillo - r) / r * 0.5 * a;
      n.vx += n.x * kr; n.vy += n.y * kr;
      n.vx += (n.ax - n.x) * 0.04 * a; n.vy += (n.ay - n.y) * 0.04 * a;
    } else {
      n.vx -= n.x * GRAVEDAD * a; n.vy -= n.y * GRAVEDAD * a;
    }
    if (n.fx !== null) { n.x = n.fx; n.y = n.fy; n.vx = n.vy = 0; }
    else {
      n.vx *= FRICCION; n.vy *= FRICCION; n.x += n.vx; n.y += n.vy;
      if (radial) {
        // Proyeccion sobre el anillo: las fuerzas solo reparten los nodos a lo
        // largo de su circulo y la distancia al centro siempre es su nivel.
        const r = Math.hypot(n.x, n.y) || 1e-6;
        n.x += (n.x / r * n.anillo - n.x) * 0.25;
        n.y += (n.y / r * n.anillo - n.y) * 0.25;
      }
    }
  }
}

// Nodo cuyas conexiones se resaltan: el que esta bajo el cursor o, si no hay
// ninguno, el fijado con un clic. El fijado se suelta al ejecutar o reproducir
// para que la animacion del algoritmo se vea completa.
function nodoEnfocado() { return hover || fijado; }
function soltarFijado() { if (fijado) { fijado = null; sucio = true; } }

function alfaObjetivo(n) {
  const f = nodoEnfocado();
  if (f) return (n === f || f.vecinos.has(n.i)) ? 1 : 0.12;
  if (filtroTipo) return nodosFiltroTipo.has(n.i) ? 1 : 0.12;
  if (filtroCat) return categoria(n) === filtroCat ? 1 : 0.12;
  if (vis.atenuar) return vis.nodos.has(n.i) ? 1 : 0.3;
  return 1;
}

function suavizar(actual, meta, f) {
  return Math.abs(meta - actual) < 0.002 ? meta : actual + (meta - actual) * f;
}

// Avanza simulacion, transiciones y camara. Devuelve si algo se movio.
function actualizar(dt) {
  let mov = false;
  if (sim.alfa >= 0.001 || sim.alfaObjetivo > 0) { pasoSimulacion(); mov = true; }

  const f = 1 - Math.exp(-dt * 10);
  for (const n of nodos) {
    const a0 = n.alfaVis, e0 = n.escala;
    n.alfaVis = suavizar(n.alfaVis, alfaObjetivo(n), f);
    n.escala = suavizar(n.escala, n === nodoEnfocado() ? 1.35 : 1, f);
    if (a0 !== n.alfaVis || e0 !== n.escala) mov = true;
  }
  const h0 = hoverMezcla, r0 = mezclaRadial;
  hoverMezcla = suavizar(hoverMezcla, nodoEnfocado() ? 1 : 0, f);
  mezclaRadial = suavizar(mezclaRadial, disposicion === "radial" ? 1 : 0, 1 - Math.exp(-dt * 4));
  if (h0 !== hoverMezcla || r0 !== mezclaRadial) mov = true;

  if (vuelo) {
    const p = Math.min(1, (performance.now() - vuelo.t0) / vuelo.ms);
    const e = p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
    // Interpola el centro del mundo y el zoom (en escala logaritmica).
    const k = Math.exp(Math.log(vuelo.desde.k) + (Math.log(vuelo.hasta.k) - Math.log(vuelo.desde.k)) * e);
    const cx = vuelo.desde.cx + (vuelo.hasta.cx - vuelo.desde.cx) * e;
    const cy = vuelo.desde.cy + (vuelo.hasta.cy - vuelo.desde.cy) * e;
    cam = { k, x: ancho / 2 - cx * k, y: alto / 2 - cy * k };
    if (p >= 1) vuelo = null;
    mov = true;
  } else if (autoAjuste) {
    const v = vistaAjustada(), g = 1 - Math.exp(-dt * 4);
    cam.k += (v.k - cam.k) * g; cam.x += (v.x - cam.x) * g; cam.y += (v.y - cam.y) * g;
    mov = true;
    const quieto = sim.alfa < 0.02;
    if (quieto && Math.abs(v.k - cam.k) < 0.002) autoAjuste = false;
  }
  return mov;
}

// ------------------------------------------------------------------
// Dibujo en el lienzo
// ------------------------------------------------------------------
function dibujar(t) {
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.globalAlpha = 1;
  ctx.fillStyle = FONDO;
  ctx.fillRect(0, 0, ancho, alto);
  dibujarRejilla();
  if (!nodos.length) return;
  const k = cam.k;
  const foco = nodoEnfocado() || (hoverMezcla > 0.01 ? ultimoHover : null);
  const apagar = 1 - 0.9 * hoverMezcla;
  ctx.setTransform(dpr * k, 0, 0, dpr * k, dpr * cam.x, dpr * cam.y);
  ctx.lineCap = "round";
  if (mezclaRadial > 0.01) dibujarAnillos(k);

  // Trazo base de todos los enlaces.
  ctx.strokeStyle = ARISTA;
  ctx.lineWidth = 1 / k;
  for (const e of enlaces) {
    let a = Math.min(e.a.alfaVis, e.b.alfaVis);
    if (foco && e.a !== foco && e.b !== foco) a *= apagar;
    else if (!foco && filtroTipo) a *= 0.3;
    if (a < 0.02) continue;
    ctx.globalAlpha = a;
    ctx.beginPath(); ctx.moveTo(e.a.x, e.a.y); ctx.lineTo(e.b.x, e.b.y); ctx.stroke();
  }
  // Recorridos superpuestos (caminos de aumento del plan de defensa). El
  // camino activo se dibuja tramo a tramo, de la fuente hacia el objetivo.
  for (const c of vis.extra) {
    const m = c.ids.length - 1;
    const avance = progreso(t, c.t0, Math.max(1, m) * 110) * m;
    for (let j = 0; j < m; j++) {
      const s = posPorId.get(c.ids[j]), d = posPorId.get(c.ids[j + 1]);
      const tramo = Math.max(0, Math.min(1, avance - j));
      if (tramo <= 0) break;
      if (s && d) trazoResaltado(s, d, c.estilo, t, j * 0.17, 1, tramo);
    }
  }
  // Aristas marcadas por el algoritmo; las nuevas crecen desde su origen.
  for (const [clave, cls] of vis.aristas) {
    const p = pares.get(clave);
    if (!p) continue;
    const t0 = vis.aparicion.has(clave) ? vis.aparicion.get(clave) : -Infinity;
    const prog = progreso(t, t0, 350);
    if (prog <= 0) {
      // Aun en espera: se mantiene el aspecto del cuadro anterior.
      const antes = ESTILO_ARISTA[vis.previoA.get(clave)];
      if (antes) trazoResaltado(p.s, p.t, antes, t, p.semilla, 1);
      continue;
    }
    const est = ESTILO_ARISTA[cls];
    if (est) trazoResaltado(p.s, p.t, est, t, p.semilla, 1, prog);
  }
  // Conexiones del nodo bajo el cursor o del fijado con un clic.
  if (foco && hoverMezcla > 0.01) {
    for (const p of foco.salen) trazoResaltado(p.s, p.t, ESTILO_ARISTA.hover, t, p.semilla, hoverMezcla);
    for (const p of foco.entran) trazoResaltado(p.s, p.t, ESTILO_ARISTA.hover, t, p.semilla, hoverMezcla);
  } else if (filtroTipo) {
    // Accesos del tipo resaltado desde la leyenda.
    for (const p of paresPorTipo.get(filtroTipo) || []) trazoResaltado(p.s, p.t, ESTILO_ARISTA.hover, t, p.semilla, 1);
  }
  // Arista bajo el cursor (y su inversa, si existe), sobre todo lo demas.
  if (hoverArista) {
    const inversa = pares.get(hoverArista.t.i + "," + hoverArista.s.i);
    trazoResaltado(hoverArista.s, hoverArista.t, ESTILO_ARISTA.foco, t, hoverArista.semilla, 1);
    if (inversa) trazoResaltado(inversa.s, inversa.t, ESTILO_ARISTA.foco, t, inversa.semilla, 1);
  }
  for (const n of nodos) dibujarNodo(n, k, t);
  if (destello) {
    // Tres ondas que se abren sobre el objeto elegido en la busqueda.
    const p = (t - destello.t0) / 1400;
    if (p >= 1) destello = null;
    else {
      const n = destello.n;
      ctx.strokeStyle = TEXTO_FUERTE; ctx.lineWidth = 2 / k;
      for (let j = 0; j < 3; j++) {
        const q = p * 1.6 - j * .3;
        if (q <= 0 || q >= 1) continue;
        ctx.globalAlpha = (1 - q) * .8;
        ctx.beginPath(); ctx.arc(n.x, n.y, n.radio + (4 + q * 34) / k, 0, Math.PI * 2); ctx.stroke();
      }
    }
  }
  dibujarEtiquetas(foco);
  dibujarInsignias(foco);
  ctx.globalAlpha = 1;
}

// Guias de la vista radial: un circulo por distancia en saltos al objetivo.
function dibujarAnillos(k) {
  ctx.strokeStyle = "#cfd7e3";
  ctx.lineWidth = 1 / k;
  ctx.setLineDash([4 / k, 5 / k]);
  ctx.globalAlpha = mezclaRadial;
  for (let d = 1; d < radiosAnillo.length; d++) {
    ctx.beginPath(); ctx.arc(0, 0, radiosAnillo[d], 0, Math.PI * 2); ctx.stroke();
  }
  ctx.setLineDash([]);
  ctx.fillStyle = "#8a98ad";
  ctx.font = `${12 / k}px ${FUENTE_TITULO}`;
  ctx.textAlign = "center"; ctx.textBaseline = "bottom";
  for (let d = 1; d < radiosAnillo.length; d++) {
    ctx.fillText(d === 1 ? "1 salto" : d + " saltos", 0, -radiosAnillo[d] - 3 / k);
  }
}

function dibujarRejilla() {
  let s = 26 * cam.k;
  while (s < 16) s *= 2;
  while (s > 52) s /= 2;
  const ox = ((cam.x % s) + s) % s, oy = ((cam.y % s) + s) % s;
  ctx.fillStyle = "#d8dee8";
  ctx.beginPath();
  for (let x = ox; x < ancho; x += s) for (let y = oy; y < alto; y += s) ctx.rect(x - .7, y - .7, 1.4, 1.4);
  ctx.fill();
}

// Arista con punta de flecha y, si corresponde, una particula que viaja en el
// sentido del acceso para mostrar la direccion del control.
function trazoResaltado(s, d, est, tiempo, semilla, mult, prog = 1) {
  const k = cam.k;
  const a = (est.alfa ?? 1) * mult * Math.min(s.alfaVis, d.alfaVis);
  if (a < 0.02) return;
  const dx = d.x - s.x, dy = d.y - s.y, L = Math.hypot(dx, dy) || 1;
  const ux = dx / L, uy = dy / L;
  const largo = est.sinFlecha ? 0 : (6 + est.ancho * 1.3) / k;
  const rd = est.sinFlecha ? 0 : d.radio * d.escala + 1.5 / k;
  // Mientras la arista crece, la punta avanza desde el origen.
  const alcance = (L - rd) * (1 - Math.pow(1 - prog, 3));
  const ex = s.x + ux * alcance, ey = s.y + uy * alcance;
  const bx = ex - ux * largo, by = ey - uy * largo;
  if (prog < 1) {
    ctx.globalAlpha = a; ctx.strokeStyle = ctx.fillStyle = est.color; ctx.lineWidth = est.ancho / k;
    ctx.beginPath(); ctx.moveTo(s.x, s.y); ctx.lineTo(ex, ey); ctx.stroke();
    if (!est.sinFlecha && alcance > largo) {
      const ax = -uy * largo * .5, ay = ux * largo * .5;
      ctx.beginPath(); ctx.moveTo(ex, ey); ctx.lineTo(bx + ax, by + ay); ctx.lineTo(bx - ax, by - ay);
      ctx.closePath(); ctx.fill();
    }
    return;
  }
  ctx.globalAlpha = a;
  ctx.strokeStyle = ctx.fillStyle = est.color;
  ctx.lineWidth = est.ancho / k;
  if (est.guion) {
    ctx.setLineDash([7 / k, 5 / k]);
    ctx.lineDashOffset = MOV_REDUCIDO ? 0 : -tiempo / 1000 * 24 / k;
  }
  ctx.beginPath(); ctx.moveTo(s.x, s.y);
  ctx.lineTo(bx + ux * largo * .3, by + uy * largo * .3);
  ctx.stroke();
  if (est.guion) ctx.setLineDash([]);
  if (!est.sinFlecha) {
    const ax = -uy * largo * .5, ay = ux * largo * .5;
    ctx.beginPath(); ctx.moveTo(ex, ey); ctx.lineTo(bx + ax, by + ay); ctx.lineTo(bx - ax, by - ay);
    ctx.closePath(); ctx.fill();
  }
  if (est.flujo && !MOV_REDUCIDO && L > rd + largo) {
    const f = ((tiempo / 1000) * 70 / L + semilla) % 1;
    const px = s.x + (bx - s.x) * f, py = s.y + (by - s.y) * f;
    ctx.beginPath(); ctx.arc(px, py, (est.ancho * .7 + 1.6) / k, 0, Math.PI * 2); ctx.fill();
  }
}

function dibujarNodo(n, k, t) {
  if (n.alfaVis < 0.01) return;
  const v = vis.nodos.get(n.i);
  const base = colorNodo(n.i);
  // p va de 0 a 1 durante la aparicion del nuevo aspecto del nodo.
  const p = v ? progreso(t, v.t0, 420) : 1;
  const rebote = p < 1 ? 1 + 0.45 * Math.sin(Math.PI * p) : 1;
  const r = n.radio * n.escala * rebote;
  const nuevo = v && p > 0;
  const fill = nuevo && v.fill ? v.fill : null;
  const hueco = nuevo && v.frontera;
  ctx.globalAlpha = n.alfaVis;
  if (n === nodoEnfocado()) {
    // Halo plano del nodo enfocado.
    ctx.globalAlpha = 0.22 * n.alfaVis;
    ctx.fillStyle = fill || base;
    ctx.beginPath(); ctx.arc(n.x, n.y, r + 7 / k, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = n.alfaVis;
  }
  ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
  if (hueco) {
    // Nodo en la frontera de la busqueda: descubierto pero aun sin expandir.
    ctx.fillStyle = "#fff"; ctx.fill();
    ctx.lineWidth = 2.2 / k; ctx.strokeStyle = base; ctx.stroke();
  } else {
    ctx.fillStyle = base; ctx.fill();
    if (fill) { ctx.globalAlpha = n.alfaVis * p; ctx.fillStyle = fill; ctx.fill(); ctx.globalAlpha = n.alfaVis; }
    ctx.lineWidth = 1.5 / k; ctx.strokeStyle = "#fff"; ctx.stroke();
  }
  const anillo = (nuevo && v.anillo) || (n.i === origen ? TEXTO_FUERTE : null);
  if (anillo) {
    // El anillo se cierra sobre el nodo al aparecer.
    const ra = r + (2.8 + (1 - p) * 8) / k;
    ctx.globalAlpha = n.alfaVis * (nuevo && v.anillo ? p : 1);
    ctx.lineWidth = 2.5 / k; ctx.strokeStyle = anillo;
    ctx.beginPath(); ctx.arc(n.x, n.y, ra, 0, Math.PI * 2); ctx.stroke();
  }
  if (n === seleccionado) {
    // Anillo punteado del objeto abierto en la tarjeta de detalle.
    ctx.globalAlpha = n.alfaVis;
    ctx.lineWidth = 1.6 / k; ctx.strokeStyle = TEXTO_FUERTE;
    ctx.setLineDash([3 / k, 3 / k]);
    ctx.beginPath(); ctx.arc(n.x, n.y, r + (anillo ? 7 : 4) / k, 0, Math.PI * 2); ctx.stroke();
    ctx.setLineDash([]);
  }
  if (v && v.pulso && !MOV_REDUCIDO && p > 0) {
    // Dos ondas desfasadas, como un sonar, sobre el nodo activo.
    ctx.lineWidth = 2 / k; ctx.strokeStyle = v.anillo || base;
    for (const desfase of [0, .5]) {
      const f = ((t / 1000) * 0.9 + desfase) % 1;
      ctx.globalAlpha = n.alfaVis * (1 - f) * .7;
      ctx.beginPath(); ctx.arc(n.x, n.y, r + (4 + f * 18) / k, 0, Math.PI * 2); ctx.stroke();
    }
  }
}

// Insignias con la distancia conocida de cada nodo (saltos en BFS, peso en Dijkstra).
function dibujarInsignias(foco) {
  if (!vis.insignias.size) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.font = "700 10px " + FUENTE;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  for (const [i, txt] of vis.insignias) {
    const n = posPorId.get(i);
    if (!n) continue;
    let a = n.alfaVis;
    if (foco && n !== foco && !foco.vecinos.has(n.i)) a *= 1 - hoverMezcla * .9;
    if (a < 0.04) continue;
    const r = n.radio * n.escala * cam.k;
    const w = Math.max(16, ctx.measureText(txt).width + 8), h = 15;
    const x = n.x * cam.k + cam.x + r * .7, y = n.y * cam.k + cam.y - r * .7 - h;
    ctx.globalAlpha = a;
    ctx.fillStyle = TEXTO_FUERTE;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(x, y, w, h, 7.5); else ctx.rect(x, y, w, h);
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.fillText(txt, x + w / 2, y + h / 2 + .5);
  }
}

// Etiquetas en coordenadas de pantalla: tamanio fijo y legibles a cualquier zoom.
function dibujarEtiquetas(foco) {
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.lineJoin = "round";
  const porZoom = Math.max(0, Math.min(1, (cam.k - 1.25) / 0.6));
  const etiqueta = (n, grande) => {
    const extremo = hoverArista && (n === hoverArista.s || n === hoverArista.t);
    const importante = n.i === objetivo || n.hv || n.i === origen || extremo;
    let a = importante ? 1 : porZoom;
    if (foco) {
      const cerca = n === foco || foco.vecinos.has(n.i);
      a = cerca ? Math.max(a, hoverMezcla) : a * (1 - hoverMezcla * .9);
    }
    a *= n.alfaVis;
    if (a < 0.04) return;
    const sx = n.x * cam.k + cam.x, sy = n.y * cam.k + cam.y;
    if (sx < -120 || sx > ancho + 120 || sy < -40 || sy > alto + 40) return;
    const y = sy + n.radio * n.escala * cam.k + 5;
    const txt = corto(n.nombre);
    ctx.font = (grande ? "600 12.5px " : (importante ? "600 11px " : "11px ")) + FUENTE;
    ctx.globalAlpha = a;
    ctx.lineWidth = 4; ctx.strokeStyle = FONDO; ctx.strokeText(txt, sx, y);
    ctx.fillStyle = grande || importante ? TEXTO_FUERTE : TEXTO; ctx.fillText(txt, sx, y);
  };
  for (const n of nodos) if (n !== foco) etiqueta(n, false);
  if (foco) etiqueta(foco, true);
}

// ------------------------------------------------------------------
// Camara
// ------------------------------------------------------------------
function vistaAjustada() {
  let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
  for (const n of nodos) {
    minx = Math.min(minx, n.x - n.radio); maxx = Math.max(maxx, n.x + n.radio);
    miny = Math.min(miny, n.y - n.radio); maxy = Math.max(maxy, n.y + n.radio);
  }
  if (!nodos.length) { minx = miny = -1; maxx = maxy = 1; }
  const margen = 70;
  const w = Math.max(maxx - minx, 1), h = Math.max(maxy - miny, 1);
  const k = Math.max(0.12, Math.min((ancho - margen * 2) / w, (alto - margen * 2) / h, 2.2));
  return { k, x: ancho / 2 - (minx + maxx) / 2 * k, y: alto / 2 - (miny + maxy) / 2 * k };
}
function volar(hasta, ms = 650) {
  if (MOV_REDUCIDO) { cam = hasta; sucio = true; return; }
  const centro = v => ({ k: v.k, cx: (ancho / 2 - v.x) / v.k, cy: (alto / 2 - v.y) / v.k });
  vuelo = { desde: centro(cam), hasta: centro(hasta), t0: performance.now(), ms };
  autoAjuste = false;
}
function ajustarVista(animado = true) {
  const v = vistaAjustada();
  if (animado) volar(v); else { cam = v; sucio = true; }
}
function enfocarNodo(n, k) {
  const z = k || Math.max(cam.k, 1.8);
  volar({ k: z, x: ancho / 2 - n.x * z, y: alto / 2 - n.y * z });
}
function zoomEn(f, mx = ancho / 2, my = alto / 2) {
  const k = Math.max(0.12, Math.min(6, cam.k * f)), r = k / cam.k;
  cam = { k, x: mx - (mx - cam.x) * r, y: my - (my - cam.y) * r };
  autoAjuste = false; vuelo = null; sucio = true;
}

function redimensionar() {
  const r = lienzo.getBoundingClientRect();
  const w0 = ancho, h0 = alto;
  dpr = window.devicePixelRatio || 1;
  ancho = r.width; alto = r.height;
  lienzo.width = Math.round(ancho * dpr); lienzo.height = Math.round(alto * dpr);
  // Conserva el punto central de la vista al cambiar el tamanio.
  if (w0) { cam.x += (ancho - w0) / 2; cam.y += (alto - h0) / 2; }
  sucio = true;
}
new ResizeObserver(redimensionar).observe(lienzo);

let tPrevio = performance.now();
function lazo(t) {
  const dt = Math.min(0.05, Math.max(0, (t - tPrevio) / 1000));
  tPrevio = t;
  const mov = nodos.length ? actualizar(dt) : false;
  if (mov || sucio || animacionContinua()) { dibujar(t); sucio = false; }
  requestAnimationFrame(lazo);
}
// Hay que redibujar cada fotograma mientras haya particulas o guiones en marcha.
function animacionContinua() {
  if (MOV_REDUCIDO) return false;
  if (hoverMezcla > 0.01 || destello || filtroTipo || hoverArista || performance.now() < vis.hasta) return true;
  for (const v of vis.nodos.values()) if (v.pulso) return true;
  for (const cls of vis.aristas.values()) {
    const e = ESTILO_ARISTA[cls];
    if (e && (e.flujo || e.guion)) return true;
  }
  return vis.extra.some(c => c.estilo.flujo);
}

// ------------------------------------------------------------------
// Interaccion con el puntero
// ------------------------------------------------------------------
function puntoLocal(e) {
  const r = lienzo.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
}
function nodoEn(sx, sy) {
  const wx = (sx - cam.x) / cam.k, wy = (sy - cam.y) / cam.k;
  let mejor = null, md = Infinity;
  for (const n of nodos) {
    const d = Math.hypot(n.x - wx, n.y - wy);
    if (d < n.radio * n.escala + 5 / cam.k && d < md) { mejor = n; md = d; }
  }
  return mejor;
}
function ponerHover(n, e) {
  if (n !== hover) {
    if (hover) ultimoHover = hover;
    hover = n;
    lienzo.style.cursor = n ? "pointer" : "";
    if (n && e) mostrarEtq(e, n); else etq.classList.remove("visible");
    sucio = true;
  } else if (n && e) moverEtq(e);
}
// Arista dirigida mas cercana al punto, dentro de una tolerancia en pixeles.
function aristaEn(sx, sy) {
  const wx = (sx - cam.x) / cam.k, wy = (sy - cam.y) / cam.k;
  let mejor = null, md = 5 / cam.k;
  for (const p of pares.values()) {
    if (Math.min(p.s.alfaVis, p.t.alfaVis) < 0.3) continue;
    const dx = p.t.x - p.s.x, dy = p.t.y - p.s.y, l2 = dx * dx + dy * dy || 1;
    const u = Math.max(0, Math.min(1, ((wx - p.s.x) * dx + (wy - p.s.y) * dy) / l2));
    const d = Math.hypot(wx - (p.s.x + u * dx), wy - (p.s.y + u * dy));
    if (d < md) { md = d; mejor = p; }
  }
  return mejor;
}
function ponerHoverArista(p, e) {
  if (p === hoverArista) { if (p && e) moverEtq(e); return; }
  hoverArista = p;
  sucio = true;
  if (p && e) mostrarEtqArista(e, p);
  else if (!hover) etq.classList.remove("visible");
}
// Etiqueta de una arista: que acceso representa en cada sentido.
function mostrarEtqArista(e, p) {
  const inversa = pares.get(p.t.i + "," + p.s.i);
  const bloque = q => {
    const a = corto(q.s.nombre), b = corto(q.t.nombre);
    return `<strong>${esc(a)} &rarr; ${esc(b)}</strong>` + [...new Set(q.tipos)].map(t =>
      `<span class="acc"><b>${esc(t)}</b>${esc(significado(t, a, b))}</span>`).join("");
  };
  etq.innerHTML = bloque(p) + (inversa ? bloque(inversa) : "") +
    `<span class="nota">Quien controla el origen puede llegar a controlar el destino.</span>`;
  etq.classList.add("visible", "ancha");
  moverEtq(e);
}

function mostrarEtq(e, n) {
  etq.classList.remove("ancha");
  etq.innerHTML = `<strong>${esc(n.nombre)}</strong>` +
    `<span>${esc(n.tipo)}${n.hv ? " de alto valor" : ""}</span>` +
    `<span>Controla ${n.salen.length} &middot; lo controlan ${n.entran.length}</span>`;
  etq.classList.add("visible");
  moverEtq(e);
}
function moverEtq(e) {
  const p = puntoLocal(e);
  const w = etq.offsetWidth, h = etq.offsetHeight;
  const x = p.x + 16 + w > ancho ? p.x - w - 12 : p.x + 16;
  const y = p.y + 14 + h > alto ? p.y - h - 10 : p.y + 14;
  etq.style.transform = `translate(${x}px, ${y}px)`;
}

lienzo.addEventListener("pointerdown", e => {
  if (e.button !== 0) return;
  const p = puntoLocal(e);
  lienzo.setPointerCapture(e.pointerId);
  gesto = { nodo: nodoEn(p.x, p.y), x0: p.x, y0: p.y, movido: false, camx: cam.x, camy: cam.y };
});
lienzo.addEventListener("pointermove", e => {
  const p = puntoLocal(e);
  if (!gesto) {
    // Los nodos tienen prioridad; fuera de ellos se busca la arista mas cercana.
    const n = nodoEn(p.x, p.y);
    if (n) { ponerHoverArista(null); ponerHover(n, e); }
    else { ponerHover(null); ponerHoverArista(aristaEn(p.x, p.y), e); }
    return;
  }
  if (!gesto.movido && Math.hypot(p.x - gesto.x0, p.y - gesto.y0) > 4) {
    gesto.movido = true;
    if (gesto.nodo) {
      gesto.nodo.arrastrado = true;
      sim.alfaObjetivo = 0.3;
    } else {
      autoAjuste = false; vuelo = null;
      lienzo.classList.add("arrastrando");
    }
  }
  if (!gesto.movido) return;
  if (gesto.nodo) {
    gesto.nodo.fx = (p.x - cam.x) / cam.k;
    gesto.nodo.fy = (p.y - cam.y) / cam.k;
    moverEtq(e);
  } else {
    cam.x = gesto.camx + p.x - gesto.x0;
    cam.y = gesto.camy + p.y - gesto.y0;
  }
  sucio = true;
});
function soltar(e, cancelado) {
  if (!gesto) return;
  const g = gesto;
  gesto = null;
  lienzo.classList.remove("arrastrando");
  if (g.nodo && g.movido) {
    g.nodo.arrastrado = false;
    // El objetivo queda fijo donde se suelta; los demas vuelven a la simulacion.
    if (g.nodo.i !== objetivo) g.nodo.fx = g.nodo.fy = null;
    sim.alfaObjetivo = 0;
  } else if (g.nodo && !cancelado) {
    alClicNodo(g.nodo);
  } else if (!g.nodo && !g.movido && !cancelado) {
    cerrarDetalle();
  }
}
lienzo.addEventListener("pointerup", e => soltar(e, false));
lienzo.addEventListener("pointercancel", e => soltar(e, true));
lienzo.addEventListener("pointerleave", () => { if (!gesto) { ponerHover(null); ponerHoverArista(null); } });
lienzo.addEventListener("dblclick", e => {
  const p = puntoLocal(e), n = nodoEn(p.x, p.y);
  if (n) enfocarNodo(n, Math.max(cam.k * 1.6, 2));
});
lienzo.addEventListener("wheel", e => {
  e.preventDefault();
  const p = puntoLocal(e);
  const delta = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
  zoomEn(Math.exp(-delta * 0.0016), p.x, p.y);
}, { passive: false });

// ------------------------------------------------------------------
// Conexiones de la interfaz
// ------------------------------------------------------------------
document.getElementById("selObjetivo").addEventListener("change", e => cargarGrafo(Number(e.target.value)));
document.querySelectorAll("#algos .algo").forEach(b =>
  b.addEventListener("click", () => elegirAlgoritmo(b.dataset.alg)));
document.querySelectorAll("#segFuentes button").forEach(b =>
  b.addEventListener("click", () => {
    fuentesSel = b.dataset.v;
    document.querySelectorAll("#segFuentes button").forEach(o => {
      o.classList.toggle("activo", o === b);
      o.setAttribute("aria-checked", o === b);
    });
  }));
document.getElementById("btnQuitarOrigen").addEventListener("click", () => { origen = null; sucio = true; mostrarOrigen(); });
document.getElementById("btnEjecutar").addEventListener("click", ejecutar);
document.getElementById("btnPlay").addEventListener("click", play);
document.getElementById("btnPaso").addEventListener("click", paso);
document.getElementById("btnAtras").addEventListener("click", atras);
document.getElementById("btnInicio").addEventListener("click", reiniciar);
document.getElementById("btnFin").addEventListener("click", alFinal);
document.getElementById("rngFrame").addEventListener("input", e => irA(Number(e.target.value)));
document.querySelectorAll("#velocidades button").forEach(b =>
  b.addEventListener("click", () => elegirVelocidad(Number(b.dataset.v))));
document.querySelectorAll("#segDisposicion button").forEach(b =>
  b.addEventListener("click", () => cambiarDisposicion(b.dataset.v)));
document.getElementById("btnAcercar").addEventListener("click", () => zoomAnimado(1.3));
document.getElementById("btnAlejar").addEventListener("click", () => zoomAnimado(1 / 1.3));
document.getElementById("btnAjustar").addEventListener("click", () => ajustarVista(true));
document.getElementById("btnPanel").addEventListener("click", alternarPanel);
document.getElementById("btnPlegar").addEventListener("click", alternarPanel);
document.getElementById("btnAyuda").addEventListener("click", e => { e.stopPropagation(); alternarAyuda(); });
document.addEventListener("click", e => {
  if (!e.target.closest("#ayuda")) alternarAyuda(false);
});
document.getElementById("togglerPesos").addEventListener("click", () => alternarPesos());
document.getElementById("btnCerrarDetalle").addEventListener("click", cerrarDetalle);
document.getElementById("btnCentrar").addEventListener("click", () => { if (seleccionado) enfocarNodo(seleccionado); });
document.getElementById("btnUsarOrigen").addEventListener("click", () => {
  if (!seleccionado) return;
  if (algSel === "defensa") elegirAlgoritmo("bfs");
  seleccionar(seleccionado.i);
});
document.querySelectorAll("#segConexiones button").forEach(b =>
  b.addEventListener("click", () => elegirPestana(b.dataset.v)));
// Los pasos del camino y los accesos del corte ubican su objeto en el grafo.
const panel = document.getElementById("panel");
panel.addEventListener("click", e => {
  const li = e.target.closest("[data-i]");
  const n = li && posPorId.get(Number(li.dataset.i));
  if (n) { ponerHover(null); enfocarNodo(n); abrirDetalle(n); }
});
panel.addEventListener("mouseover", e => {
  const li = e.target.closest("[data-i]");
  ponerHover((li && posPorId.get(Number(li.dataset.i))) || null);
});
panel.addEventListener("mouseleave", () => ponerHover(null));

if (typeof window.backendLocal === "function") {
  document.getElementById("intro").textContent = "Versión offline: los algoritmos se ejecutan " +
    "en el navegador sobre los datos incrustados y la página reproduce su ejecución paso a paso.";
}
// En pantallas estrechas el panel arranca oculto para dejar ver el grafo.
if (window.matchMedia("(max-width: 760px)").matches) document.getElementById("app").classList.add("sin-panel");
// El lienzo se redibuja cuando la fuente incrustada termina de cargar.
if (document.fonts) document.fonts.ready.then(() => { sucio = true; });
construirPesos();
ajustarInterfazAlgoritmo();
requestAnimationFrame(lazo);
cargarObjetivos();
</script>
</body>
</html>"""

PAGINA = pagina()
