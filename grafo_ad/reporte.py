"""Generacion de un reporte HTML autocontenido del analisis.

Produce una pagina sin dependencias externas (CSS en linea) que reune el resumen
del grafo, las consultas reconstruidas, una ruta de acceso de ejemplo dibujada
en SVG y el plan de defensa minimo con su comparacion de riesgo. Sirve como
entregable visual del proyecto.
"""

from __future__ import annotations

import html
from datetime import date

from . import consultas
from .modelo import Grafo, OBJECTID_DOMAIN_ADMINS
from .centralidad import betweenness, subgrafo_rutas_ataque
from .cortes import plan_de_defensa
from .riesgo import exposicion, exposicion_tras_corte


def _e(texto: object) -> str:
    return html.escape(str(texto))


def _svg_ruta(pasos: list[str]) -> str:
    """Dibuja una ruta de acceso como una columna de cajas enlazadas."""
    if not pasos:
        return "<p>No hay ruta para mostrar.</p>"

    # Cada paso tiene la forma "A -[TIPO]-> B". Se extrae la secuencia de nodos.
    nodos: list[str] = []
    etiquetas: list[str] = []
    for paso in pasos:
        izquierda, resto = paso.split(" -[", 1)
        tipo, derecha = resto.split("]-> ", 1)
        if not nodos:
            nodos.append(izquierda)
        nodos.append(derecha)
        etiquetas.append(tipo)

    alto_caja, salto = 44, 86
    ancho, alto = 620, salto * len(nodos) + 20
    piezas = [f'<svg viewBox="0 0 {ancho} {alto}" xmlns="http://www.w3.org/2000/svg" '
              f'role="img" class="ruta">']
    for i, nombre in enumerate(nodos):
        y = 10 + i * salto
        piezas.append(
            f'<rect x="60" y="{y}" width="500" height="{alto_caja}" rx="8" '
            f'class="nodo"/>'
            f'<text x="310" y="{y + 28}" text-anchor="middle" class="etiqueta-nodo">'
            f'{_e(nombre)}</text>'
        )
        if i < len(etiquetas):
            y1 = y + alto_caja
            y2 = y + salto
            piezas.append(
                f'<line x1="310" y1="{y1}" x2="310" y2="{y2}" class="flecha" '
                f'marker-end="url(#punta)"/>'
                f'<text x="320" y="{y1 + 26}" class="etiqueta-arista">'
                f'{_e(etiquetas[i])}</text>'
            )
    piezas.append(
        '<defs><marker id="punta" markerWidth="10" markerHeight="10" refX="8" '
        'refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" class="punta"/>'
        '</marker></defs></svg>'
    )
    return "".join(piezas)


def _tabla(encabezados: list[str], filas: list[tuple]) -> str:
    cabecera = "".join(f"<th>{_e(h)}</th>" for h in encabezados)
    cuerpo = "".join(
        "<tr>" + "".join(f"<td>{_e(c)}</td>" for c in fila) + "</tr>"
        for fila in filas
    )
    return f"<table><thead><tr>{cabecera}</tr></thead><tbody>{cuerpo}</tbody></table>"


def generar_reporte(grafo: Grafo, usuario_ejemplo: str,
                    objetivo_objectid: str = OBJECTID_DOMAIN_ADMINS) -> str:
    """Construye el documento HTML completo y lo devuelve como texto."""
    objetivo = grafo.buscar_por_objectid(objetivo_objectid)
    nombre_objetivo = objetivo.nombre if objetivo else objetivo_objectid

    # Resumen del grafo.
    conteo_tipos: dict[str, int] = {}
    for nodo in grafo.nodos.values():
        conteo_tipos[nodo.tipo] = conteo_tipos.get(nodo.tipo, 0) + 1
    conteo_rel: dict[str, int] = {}
    for arista in grafo.aristas:
        conteo_rel[arista.tipo] = conteo_rel.get(arista.tipo, 0) + 1

    # Consultas reconstruidas.
    alcanzables = consultas.alto_valor_alcanzable(grafo, usuario_ejemplo)
    pasos = consultas.una_ruta_de_acceso(grafo, usuario_ejemplo, objetivo_objectid) or []

    # Centralidad sobre el subgrafo de rutas de acceso al objetivo.
    rutas = subgrafo_rutas_ataque(grafo, objetivo_objectid)
    puntajes = betweenness(rutas)
    top = sorted(puntajes.items(), key=lambda x: x[1], reverse=True)[:12]
    filas_top = [
        (grafo.nodos[nid].nombre, grafo.nodos[nid].tipo, f"{valor:.1f}")
        for nid, valor in top if valor > 0
    ]

    # Plan de defensa: fuentes = usuarios; objetivo = nodo de alto valor.
    fuentes = [n.id for n in grafo.por_tipo("User")]
    plan = plan_de_defensa(grafo, fuentes, [objetivo.id] if objetivo else [objetivo_objectid])
    cortados = {(a["origen"], a["destino"], a["tipo"]) for a in plan["accesos_a_revocar"]}
    antes = exposicion(grafo, [objetivo.id] if objetivo else [objetivo_objectid], fuentes)
    despues = exposicion_tras_corte(grafo, [objetivo.id] if objetivo else [objetivo_objectid],
                                    cortados, fuentes)

    filas_plan = [
        (a["origen_nombre"], a["tipo"], a["destino_nombre"])
        for a in plan["accesos_a_revocar"]
    ]

    estilo = """
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body { font-family: system-ui, Segoe UI, Roboto, sans-serif; margin: 0;
           background: #f4f6fb; color: #1b2430; line-height: 1.5; }
    header { background: #11263f; color: #fff; padding: 32px 40px; }
    header h1 { margin: 0 0 6px; font-size: 26px; }
    header p { margin: 0; opacity: .85; }
    main { max-width: 960px; margin: 0 auto; padding: 24px 40px 64px; }
    section { background: #fff; border: 1px solid #e1e6ef; border-radius: 12px;
              padding: 24px 28px; margin: 20px 0; }
    h2 { margin-top: 0; font-size: 20px; color: #11263f; }
    table { border-collapse: collapse; width: 100%; font-size: 14px; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #edf0f6; }
    th { background: #f0f3fa; }
    .metricas { display: flex; gap: 16px; flex-wrap: wrap; }
    .tarjeta { flex: 1 1 160px; background: #f7f9fe; border: 1px solid #e1e6ef;
               border-radius: 10px; padding: 16px; }
    .tarjeta .numero { font-size: 28px; font-weight: 700; color: #11263f; }
    .tarjeta .texto { font-size: 13px; color: #5a6676; }
    .ok { color: #1a7f43; font-weight: 600; }
    .ruta { width: 100%; height: auto; }
    .nodo { fill: #eef2fb; stroke: #4068b0; stroke-width: 1.5; }
    .etiqueta-nodo { font-size: 13px; fill: #1b2430; }
    .etiqueta-arista { font-size: 12px; fill: #7a3b12; }
    .flecha { stroke: #4068b0; stroke-width: 2; }
    .punta { fill: #4068b0; }
    .pie { color: #7a8597; font-size: 13px; }
    """

    fraccion_antes = f"{antes['fraccion'] * 100:.1f}%"
    fraccion_despues = f"{despues['fraccion'] * 100:.1f}%"

    documento = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Análisis de rutas de acceso y defensa en Active Directory</title>
<style>{estilo}</style>
</head>
<body>
<header>
  <h1>Análisis de rutas de acceso y plan de defensa mínimo</h1>
  <p>Entorno de Active Directory modelado como grafo dirigido. Generado el {date.today().isoformat()}.</p>
</header>
<main>

  <section>
    <h2>Resumen del grafo</h2>
    <div class="metricas">
      <div class="tarjeta"><div class="numero">{len(grafo)}</div><div class="texto">objetos (vértices)</div></div>
      <div class="tarjeta"><div class="numero">{len(grafo.aristas)}</div><div class="texto">accesos (aristas dirigidas)</div></div>
      <div class="tarjeta"><div class="numero">{len(grafo.altos_valores())}</div><div class="texto">objetivos de alto valor</div></div>
      <div class="tarjeta"><div class="numero">{len(conteo_rel)}</div><div class="texto">tipos de acceso</div></div>
    </div>
    <h3>Objetos por tipo</h3>
    {_tabla(["Tipo", "Cantidad"], sorted(conteo_tipos.items(), key=lambda x: -x[1]))}
    <h3>Accesos por tipo</h3>
    {_tabla(["Tipo de acceso", "Cantidad"], sorted(conteo_rel.items(), key=lambda x: -x[1]))}
  </section>

  <section>
    <h2>Alcance del usuario de ejemplo</h2>
    <p>Objetos de alto valor que <strong>{_e(usuario_ejemplo)}</strong> puede alcanzar y su distancia en saltos:</p>
    {_tabla(["Objetivo de alto valor", "Saltos"], alcanzables)}
  </section>

  <section>
    <h2>Una ruta de acceso hasta {_e(nombre_objetivo)}</h2>
    {_svg_ruta(pasos)}
  </section>

  <section>
    <h2>Objetos puente (centralidad de intermediación)</h2>
    <p>Objetos que participan como puente en la mayor cantidad de rutas de acceso hacia el objetivo.</p>
    {_tabla(["Objeto", "Tipo", "Centralidad"], filas_top)}
  </section>

  <section>
    <h2>Plan de defensa mínimo</h2>
    <p>Conjunto mínimo de accesos a revocar para que ningún usuario alcance <strong>{_e(nombre_objetivo)}</strong>.
       El tamaño del corte coincide con el flujo máximo, por lo que no existe un plan más pequeño.</p>
    <div class="metricas">
      <div class="tarjeta"><div class="numero">{plan['tamanio_corte']}</div><div class="texto">accesos a revocar (corte mínimo)</div></div>
      <div class="tarjeta"><div class="numero">{antes['fuentes_expuestas']}</div><div class="texto">usuarios que alcanzan el objetivo (antes)</div></div>
      <div class="tarjeta"><div class="numero">{despues['fuentes_expuestas']}</div><div class="texto">usuarios que lo alcanzan (después)</div></div>
      <div class="tarjeta"><div class="numero">{fraccion_antes} &rarr; {fraccion_despues}</div><div class="texto">exposición</div></div>
    </div>
    <p class="{'ok' if plan['verificado'] else ''}">
      Verificación por recorrido tras revocar los accesos:
      {'ningún usuario alcanza el objetivo.' if plan['verificado'] else 'el corte no aísla el objetivo (revisar).'}
    </p>
    {_tabla(["Objeto origen", "Acceso a revocar", "Objeto destino"], filas_plan)}
  </section>

  <p class="pie">Datos de un entorno ficticio de demostración basado en el proyecto BloodHound,
     distribuidos por el conjunto de ejemplos de cybersecurity de Neo4j. Uso académico.</p>
</main>
</body>
</html>"""
    return documento
