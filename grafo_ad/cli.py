"""Interfaz de linea de comandos del analizador.

Expone cada analisis como un subcomando. El patron comun es: cargar el grafo
desde el JSON y ejecutar el algoritmo pedido mostrando el resultado en texto.
"""

from __future__ import annotations

import argparse
import os
import sys

from . import consultas
from .caminos import camino_mas_facil
from .centralidad import betweenness, subgrafo_rutas_ataque
from .componentes import componentes_no_triviales, grafo_condensado
from .cortes import nodos_de_corte, plan_de_defensa
from .modelo import Grafo, OBJECTID_DOMAIN_ADMINS, cargar_json
from .recorridos import alcanzables, camino_mas_corto
from .reporte import generar_reporte
from .riesgo import exposicion, exposicion_tras_corte
from .transitiva import grupos_efectivos
from .visor import generar_visor

USUARIO_EJEMPLO = "PiedadFlatley255@TestCompany.Local"


def _ruta_datos_por_omision() -> str:
    # El JSON se distribuye junto al proyecto en la carpeta data.
    aqui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(aqui, "data", "cybersecurity-json-data.json")


def _cargar(args) -> Grafo:
    return cargar_json(args.datos)


# ----------------------------------------------------------------------
# Subcomandos
# ----------------------------------------------------------------------
def cmd_resumen(args) -> int:
    grafo = _cargar(args)
    tipos: dict[str, int] = {}
    for nodo in grafo.nodos.values():
        tipos[nodo.tipo] = tipos.get(nodo.tipo, 0) + 1
    rels: dict[str, int] = {}
    for arista in grafo.aristas:
        rels[arista.tipo] = rels.get(arista.tipo, 0) + 1

    print(f"Vértices: {len(grafo)}")
    print(f"Aristas:  {len(grafo.aristas)}")
    print(f"Objetivos de alto valor: {len(grafo.altos_valores())}")
    print("\nObjetos por tipo:")
    for tipo, n in sorted(tipos.items(), key=lambda x: -x[1]):
        print(f"  {tipo:<10} {n}")
    print("\nAccesos por tipo:")
    for tipo, n in sorted(rels.items(), key=lambda x: -x[1]):
        print(f"  {tipo:<22} {n}")
    print("\nObjetivos de alto valor:")
    for nodo in grafo.altos_valores():
        print(f"  {nodo.nombre}")
    return 0


def cmd_consultas(args) -> int:
    grafo = _cargar(args)

    print("== Sesiones activas (equipo -> usuario) ==")
    for equipo, usuario in consultas.sesiones_activas(grafo)[:args.limite]:
        print(f"  {equipo} -> {usuario}")

    print("\n== Acceso directo a objetos de alto valor ==")
    for objetivo, principal, tipo in consultas.acceso_directo_a_alto_valor(grafo)[:args.limite]:
        print(f"  {principal} -[{tipo}]-> {objetivo}")

    print("\n== Equipos con sesiones de varios usuarios ==")
    for equipo, usuarios in consultas.equipos_con_sesiones_multiples(grafo)[:args.limite]:
        print(f"  {equipo}: {', '.join(usuarios)}")

    print("\n== Acceso RDP (directo o heredado) ==")
    for usuario, equipo, heredado in consultas.acceso_rdp(grafo)[:args.limite]:
        via = "heredado" if heredado else "directo"
        print(f"  {usuario} -> {equipo} ({via})")

    print(f"\n== Alto valor alcanzable por {USUARIO_EJEMPLO} ==")
    for objetivo, saltos in consultas.alto_valor_alcanzable(grafo, USUARIO_EJEMPLO):
        print(f"  {objetivo} ({_saltos(saltos)})")
    return 0


def _saltos(n: int) -> str:
    return f"{n} salto" if n == 1 else f"{n} saltos"


def cmd_alcance(args) -> int:
    grafo = _cargar(args)
    nodo = grafo.resolver(args.usuario)
    if nodo is None:
        print(f"No existe el objeto {args.usuario!r}", file=sys.stderr)
        return 1
    destinos = alcanzables(grafo, nodo.id)
    alto_valor = [grafo.nodos[d] for d in destinos if grafo.nodos[d].alto_valor]
    print(f"{nodo.nombre} alcanza {len(destinos)} objetos en total.")
    print(f"De ellos, {len(alto_valor)} son de alto valor:")
    for n in sorted(alto_valor, key=lambda x: x.nombre):
        print(f"  {n.nombre}")
    return 0


def cmd_quien_llega(args) -> int:
    grafo = _cargar(args)
    objetivo = grafo.resolver(args.objetivo)
    if objetivo is None:
        print(f"No existe el objetivo {args.objetivo!r}", file=sys.stderr)
        return 1
    from .recorridos import alcanzan_a
    origenes = alcanzan_a(grafo, objetivo.id)
    por_tipo: dict[str, int] = {}
    for oid in origenes:
        t = grafo.nodos[oid].tipo
        por_tipo[t] = por_tipo.get(t, 0) + 1
    print(f"{len(origenes)} objetos pueden llegar a {objetivo.nombre}:")
    for tipo, n in sorted(por_tipo.items(), key=lambda x: -x[1]):
        print(f"  {tipo:<10} {n}")
    return 0


def cmd_camino(args) -> int:
    grafo = _cargar(args)
    origen = grafo.resolver(args.origen)
    destino = grafo.resolver(args.destino)
    if origen is None or destino is None:
        print("Origen o destino inexistente", file=sys.stderr)
        return 1

    corto = camino_mas_corto(grafo, origen.id, destino.id)
    if corto is None:
        print(f"{destino.nombre} no es alcanzable desde {origen.nombre}.")
        return 0
    print(f"Camino más corto ({_saltos(len(corto))}):")
    for a in corto:
        print(f"  {grafo.nodos[a.origen].nombre} -[{a.tipo}]-> {grafo.nodos[a.destino].nombre}")

    facil = camino_mas_facil(grafo, origen.id, destino.id)
    if facil is not None:
        aristas, peso = facil
        print(f"\nCamino de menor esfuerzo (peso {peso}, {_saltos(len(aristas))}):")
        for a in aristas:
            print(f"  {grafo.nodos[a.origen].nombre} -[{a.tipo}]-> {grafo.nodos[a.destino].nombre}")
    return 0


def cmd_scc(args) -> int:
    grafo = _cargar(args)
    no_triviales = componentes_no_triviales(grafo)
    componentes, _, aristas = grafo_condensado(grafo)
    print(f"Componentes fuertemente conexas totales: {len(componentes)}")
    print(f"Componentes con control mutuo (tamaño > 1): {len(no_triviales)}")
    print(f"Aristas en el grafo condensado (DAG): {len(aristas)}")
    for comp in sorted(no_triviales, key=len, reverse=True)[:args.limite]:
        nombres = [grafo.nodos[n].nombre for n in comp]
        print(f"\n  Componente de {len(comp)} objetos:")
        for nombre in nombres[:10]:
            print(f"    {nombre}")
        if len(nombres) > 10:
            print(f"    ... y {len(nombres) - 10} más")
    return 0


def cmd_permisos(args) -> int:
    grafo = _cargar(args)
    nodo = grafo.resolver(args.usuario)
    if nodo is None:
        print(f"No existe el objeto {args.usuario!r}", file=sys.stderr)
        return 1
    grupos = grupos_efectivos(grafo, nodo.id)
    directos = {a.destino for a in grafo.salida(nodo.id) if a.tipo == "MEMBER_OF"}
    print(f"{nodo.nombre} pertenece a {len(grupos)} grupos efectivos "
          f"({len(directos)} directos, {len(grupos) - len(directos)} heredados):")
    for gid in sorted(grupos, key=lambda g: grafo.nodos[g].nombre):
        marca = "directo" if gid in directos else "heredado"
        print(f"  {grafo.nodos[gid].nombre} ({marca})")
    return 0


def cmd_centralidad(args) -> int:
    grafo = _cargar(args)
    rutas = subgrafo_rutas_ataque(grafo, args.objetivo)
    puntajes = betweenness(rutas)
    orden = sorted(puntajes.items(), key=lambda x: x[1], reverse=True)
    print(f"Subgrafo de rutas de acceso: {len(rutas)} aristas.")
    print(f"Objetos puente con mayor centralidad de intermediación:")
    for nid, valor in orden[:args.limite]:
        if valor <= 0:
            break
        n = grafo.nodos[nid]
        print(f"  {valor:8.1f}  {n.tipo:<9} {n.nombre}")
    return 0


def cmd_cortes(args) -> int:
    grafo = _cargar(args)
    objetivo = grafo.resolver(args.objetivo)
    if objetivo is None:
        print(f"No existe el objetivo {args.objetivo!r}", file=sys.stderr)
        return 1
    cortes = nodos_de_corte(grafo, args.origen, [objetivo.id])
    origen = grafo.resolver(args.origen)
    print(f"Objetos cuyo retiro corta todo acceso de {origen.nombre} a {objetivo.nombre}:")
    if not cortes:
        print("  (ninguno: no hay un único cuello de botella)")
    for nid in sorted(cortes, key=lambda n: grafo.nodos[n].nombre):
        n = grafo.nodos[nid]
        print(f"  {n.tipo:<9} {n.nombre}")
    return 0


def _fuentes_por_omision(grafo: Grafo, modo: str) -> list[str]:
    if modo == "usuarios":
        return [n.id for n in grafo.por_tipo("User")]
    # 'todos': todos los objetos que no son de alto valor, como en el ejemplo.
    return [n.id for n in grafo.nodos.values() if not n.alto_valor]


def cmd_defensa(args) -> int:
    grafo = _cargar(args)
    objetivo = grafo.resolver(args.objetivo)
    if objetivo is None:
        print(f"No existe el objetivo {args.objetivo!r}", file=sys.stderr)
        return 1
    fuentes = _fuentes_por_omision(grafo, args.fuentes)
    # El objetivo no puede estar en el conjunto de fuentes.
    fuentes = [f for f in fuentes if f != objetivo.id]

    plan = plan_de_defensa(grafo, fuentes, [objetivo.id])
    cortados = {(a["origen"], a["destino"], a["tipo"]) for a in plan["accesos_a_revocar"]}
    antes = exposicion(grafo, [objetivo.id], fuentes)
    despues = exposicion_tras_corte(grafo, [objetivo.id], cortados, fuentes)

    print(f"Objetivo: {objetivo.nombre}")
    print(f"Fuentes consideradas: {len(fuentes)} ({args.fuentes})")
    print(f"\nCorte mínimo: {plan['tamanio_corte']} accesos a revocar.")
    print("Por el teorema de flujo máximo - corte mínimo este es el plan más "
          "pequeño posible.")
    print(f"\nExposición antes:  {antes['fuentes_expuestas']}/{antes['total_fuentes']} "
          f"({antes['fraccion'] * 100:.1f}%)")
    print(f"Exposición después: {despues['fuentes_expuestas']}/{despues['total_fuentes']} "
          f"({despues['fraccion'] * 100:.1f}%)")
    print(f"Verificación por recorrido: "
          f"{'el objetivo queda aislado.' if plan['verificado'] else 'FALLA, revisar.'}")
    print("\nAccesos a revocar:")
    for a in plan["accesos_a_revocar"]:
        print(f"  {a['origen_nombre']} -[{a['tipo']}]-> {a['destino_nombre']}")
    return 0


def cmd_reporte(args) -> int:
    grafo = _cargar(args)
    html_doc = generar_reporte(grafo, args.usuario, args.objetivo)
    with open(args.salida, "w", encoding="utf-8") as archivo:
        archivo.write(html_doc)
    print(f"Reporte escrito en {args.salida}")
    return 0


def cmd_visor(args) -> int:
    grafo = _cargar(args)
    html_doc = generar_visor(grafo)
    with open(args.salida, "w", encoding="utf-8") as archivo:
        archivo.write(html_doc)
    print(f"Visor interactivo escrito en {args.salida}")
    print("Ábrelo con doble clic en el navegador.")
    return 0


def cmd_servir(args) -> int:
    # Importacion diferida: solo se necesita al levantar el servidor.
    from .servidor import iniciar
    iniciar(args.datos, puerto=args.puerto, abrir=not args.sin_abrir)
    return 0


# ----------------------------------------------------------------------
# Construccion del parser
# ----------------------------------------------------------------------
def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grafo_ad",
        description="Análisis de rutas de acceso y defensa en un grafo de "
                    "Active Directory.",
    )
    parser.add_argument("--datos", default=_ruta_datos_por_omision(),
                        help="Ruta al export JSON del grafo.")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("resumen", help="Estadísticas del grafo.")
    p.set_defaults(func=cmd_resumen)

    p = sub.add_parser("consultas", help="Ejecuta las consultas reconstruidas.")
    p.add_argument("--limite", type=int, default=15)
    p.set_defaults(func=cmd_consultas)

    p = sub.add_parser("alcance", help="Qué alcanza un objeto.")
    p.add_argument("--usuario", required=True)
    p.set_defaults(func=cmd_alcance)

    p = sub.add_parser("quien-llega", help="Quién alcanza un objetivo.")
    p.add_argument("--objetivo", default=OBJECTID_DOMAIN_ADMINS)
    p.set_defaults(func=cmd_quien_llega)

    p = sub.add_parser("camino", help="Camino más corto y de menor esfuerzo.")
    p.add_argument("--origen", required=True)
    p.add_argument("--destino", required=True)
    p.set_defaults(func=cmd_camino)

    p = sub.add_parser("scc", help="Componentes fuertemente conexas.")
    p.add_argument("--limite", type=int, default=5)
    p.set_defaults(func=cmd_scc)

    p = sub.add_parser("permisos", help="Grupos efectivos por cerradura transitiva.")
    p.add_argument("--usuario", required=True)
    p.set_defaults(func=cmd_permisos)

    p = sub.add_parser("centralidad", help="Objetos puente (betweenness).")
    p.add_argument("--objetivo", default=OBJECTID_DOMAIN_ADMINS)
    p.add_argument("--limite", type=int, default=15)
    p.set_defaults(func=cmd_centralidad)

    p = sub.add_parser("cortes", help="Cuellos de botella de un origen al objetivo.")
    p.add_argument("--origen", required=True)
    p.add_argument("--objetivo", default=OBJECTID_DOMAIN_ADMINS)
    p.set_defaults(func=cmd_cortes)

    p = sub.add_parser("defensa", help="Plan de defensa mínimo (corte mínimo).")
    p.add_argument("--objetivo", default=OBJECTID_DOMAIN_ADMINS)
    p.add_argument("--fuentes", choices=["usuarios", "todos"], default="usuarios")
    p.set_defaults(func=cmd_defensa)

    p = sub.add_parser("reporte", help="Genera un reporte HTML.")
    p.add_argument("--usuario", default=USUARIO_EJEMPLO)
    p.add_argument("--objetivo", default=OBJECTID_DOMAIN_ADMINS)
    p.add_argument("--salida", default="reporte.html")
    p.set_defaults(func=cmd_reporte)

    p = sub.add_parser("visor", help="Genera el visor web interactivo (archivo offline).")
    p.add_argument("--salida", default="visor.html")
    p.set_defaults(func=cmd_visor)

    p = sub.add_parser("servir", help="Levanta la aplicación web interactiva.")
    p.add_argument("--puerto", type=int, default=8000)
    p.add_argument("--sin-abrir", action="store_true",
                   help="No abrir el navegador automáticamente.")
    p.set_defaults(func=cmd_servir)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (KeyError, ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
