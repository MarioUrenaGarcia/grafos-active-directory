"""Reconstruccion en Python de las consultas del ejemplo original.

El ejemplo de referencia resuelve sus preguntas con consultas Cypher sobre
Neo4j. Aqui cada una se reimplementa como un recorrido sobre el grafo cargado en
memoria, sin motor de base de datos, para dejar explicito el algoritmo que hay
detras de cada consulta.
"""

from __future__ import annotations

from .modelo import Grafo, OBJECTID_DOMAIN_ADMINS
from .recorridos import bfs_arbol, reconstruir_camino


def sesiones_activas(grafo: Grafo) -> list[tuple[str, str]]:
    """Pares (equipo, usuario) con una sesion activa.

    Consulta original: MATCH (:Computer)-[:HAS_SESSION]->(:User).
    """
    resultado = []
    for arista in grafo.aristas:
        if arista.tipo == "HAS_SESSION":
            resultado.append((grafo.nodos[arista.origen].nombre,
                              grafo.nodos[arista.destino].nombre))
    return sorted(resultado)


def acceso_directo_a_alto_valor(grafo: Grafo) -> list[tuple[str, str, str]]:
    """Usuarios o grupos con acceso directo a un objeto de alto valor.

    Consulta original: MATCH (o:HighValue)<--(a) WHERE a:User OR a:Group.
    Devuelve (objeto_alto_valor, principal, tipo_de_acceso).
    """
    resultado = []
    for objetivo in grafo.altos_valores():
        for arista in grafo.entrada(objetivo.id):
            principal = grafo.nodos[arista.origen]
            if principal.tipo in {"User", "Group"}:
                resultado.append((objetivo.nombre, principal.nombre, arista.tipo))
    return sorted(resultado)


def equipos_con_sesiones_multiples(grafo: Grafo) -> list[tuple[str, list[str]]]:
    """Equipos con sesiones activas de mas de un usuario distinto.

    Consulta original: agrupa HAS_SESSION por equipo y filtra sessions > 1.
    """
    por_equipo: dict[str, set[str]] = {}
    for arista in grafo.aristas:
        if arista.tipo == "HAS_SESSION":
            equipo = grafo.nodos[arista.origen].nombre
            usuario = grafo.nodos[arista.destino].nombre
            por_equipo.setdefault(equipo, set()).add(usuario)
    resultado = [(equipo, sorted(usuarios))
                 for equipo, usuarios in por_equipo.items() if len(usuarios) > 1]
    return sorted(resultado)


def acceso_rdp(grafo: Grafo, max_niveles_grupo: int = 2) -> list[tuple[str, str, bool]]:
    """Usuarios con acceso RDP directo o heredado por grupos anidados.

    Consulta original: union de CAN_RDP directo y CAN_RDP a traves de cadenas de
    MEMBER_OF de hasta dos niveles. Devuelve (usuario, equipo, heredado).
    """
    resultado: set[tuple[str, str, bool]] = set()

    # Acceso directo usuario -> equipo.
    for arista in grafo.aristas:
        if arista.tipo == "CAN_RDP" and grafo.nodos[arista.origen].tipo == "User":
            resultado.add((grafo.nodos[arista.origen].nombre,
                           grafo.nodos[arista.destino].nombre, False))

    # Grupos que conceden RDP y los equipos a los que dan acceso.
    rdp_de_grupo: dict[str, list[str]] = {}
    for arista in grafo.aristas:
        if arista.tipo == "CAN_RDP" and grafo.nodos[arista.origen].tipo == "Group":
            rdp_de_grupo.setdefault(arista.origen, []).append(arista.destino)

    # Para cada usuario, grupos alcanzables por MEMBER_OF hasta el limite.
    for usuario in grafo.por_tipo("User"):
        alcanzados = _grupos_hasta_nivel(grafo, usuario.id, max_niveles_grupo)
        for gid in alcanzados:
            for equipo in rdp_de_grupo.get(gid, []):
                resultado.add((usuario.nombre, grafo.nodos[equipo].nombre, True))
    return sorted(resultado)


def _grupos_hasta_nivel(grafo: Grafo, usuario: str, max_niveles: int) -> set[str]:
    """Grupos alcanzables desde un usuario por cadenas de MEMBER_OF acotadas."""
    alcanzados: set[str] = set()
    # El primer salto usuario -> grupo mas hasta max_niveles saltos grupo-grupo.
    frontera = {arista.destino for arista in grafo.salida(usuario)
                if arista.tipo == "MEMBER_OF"}
    alcanzados |= frontera
    for _ in range(max_niveles):
        siguiente: set[str] = set()
        for gid in frontera:
            for arista in grafo.salida(gid):
                if arista.tipo == "MEMBER_OF" and arista.destino not in alcanzados:
                    siguiente.add(arista.destino)
        alcanzados |= siguiente
        frontera = siguiente
    return alcanzados


def alto_valor_alcanzable(grafo: Grafo, usuario: str) -> list[tuple[str, int]]:
    """Objetos de alto valor que un usuario alcanza y su distancia en saltos.

    Consulta original: shortestPath de un usuario a cada HighValue. Para el
    usuario de ejemplo del dataset el resultado tiene cuatro objetos.
    """
    nodo = grafo.resolver(usuario)
    if nodo is None:
        raise KeyError(f"No existe el usuario {usuario!r}")
    arbol = bfs_arbol(grafo, nodo.id)
    resultado = []
    for objetivo in grafo.altos_valores():
        if objetivo.id in arbol and objetivo.id != nodo.id:
            camino = reconstruir_camino(arbol, nodo.id, objetivo.id)
            resultado.append((objetivo.nombre, len(camino)))
    return sorted(resultado, key=lambda x: (x[1], x[0]))


def una_ruta_de_acceso(grafo: Grafo, usuario: str, objetivo_objectid: str) -> list[str] | None:
    """Describe un camino mas corto de un usuario a un objetivo por objectid.

    Devuelve la secuencia legible de pasos "origen -[TIPO]-> destino", o None si
    el objetivo no es alcanzable.
    """
    nodo = grafo.resolver(usuario)
    objetivo = grafo.buscar_por_objectid(objetivo_objectid)
    if nodo is None or objetivo is None:
        return None
    arbol = bfs_arbol(grafo, nodo.id)
    camino = reconstruir_camino(arbol, nodo.id, objetivo.id)
    if camino is None:
        return None
    return [
        f"{grafo.nodos[a.origen].nombre} -[{a.tipo}]-> {grafo.nodos[a.destino].nombre}"
        for a in camino
    ]
