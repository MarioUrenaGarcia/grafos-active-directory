"""Cerradura transitiva de la pertenencia a grupos (algoritmo de Warshall).

La pertenencia a grupos es una relacion binaria R sobre el conjunto de objetos:
x R y si x es miembro directo del grupo y. Como los grupos se anidan, los
permisos efectivos dependen de la cerradura transitiva R+ de esa relacion.

Warshall calcula R+ en tiempo O(n^3) sobre la matriz de adyacencia booleana.
Para que sea tratable en Python se reduce el universo a los grupos (la parte de
la relacion que puede encadenarse) y se representa cada fila de la matriz como
un entero usado de mapa de bits, de modo que la union de filas es un unico OR
sobre enteros. La pertenencia efectiva de un principal cualquiera se obtiene
uniendo las filas de sus grupos directos.
"""

from __future__ import annotations

from .modelo import Grafo

RELACION_PERTENENCIA = "MEMBER_OF"


def _cerradura_grupos(grafo: Grafo) -> tuple[list[str], dict[str, int], list[int]]:
    """Cerradura transitiva de MEMBER_OF restringida a grupos (Warshall).

    Devuelve el orden de los grupos, el mapa grupo -> indice y las filas de la
    matriz de cerradura como mapas de bits.
    """
    grupos = [n.id for n in grafo.por_tipo("Group")]
    indice = {gid: i for i, gid in enumerate(grupos)}
    n = len(grupos)

    # Matriz de adyacencia booleana como mapas de bits: el bit j de fila[i] vale
    # 1 si el grupo i es miembro directo del grupo j.
    fila = [0] * n
    for arista in grafo.aristas:
        if arista.tipo != RELACION_PERTENENCIA:
            continue
        i = indice.get(arista.origen)
        j = indice.get(arista.destino)
        if i is not None and j is not None:
            fila[i] |= 1 << j

    # Warshall: para cada k, si i alcanza k entonces i hereda lo que alcanza k.
    for k in range(n):
        bit_k = 1 << k
        fila_k = fila[k]
        for i in range(n):
            if fila[i] & bit_k:
                fila[i] |= fila_k
    return grupos, indice, fila


def grupos_efectivos(grafo: Grafo, principal: str) -> set[str]:
    """Grupos a los que un principal pertenece directa o indirectamente.

    Combina la cerradura transitiva entre grupos con las pertenencias directas
    del principal. Funciona para usuarios, equipos o grupos.
    """
    nodo = grafo.resolver(principal)
    if nodo is None:
        raise KeyError(f"No existe el objeto {principal!r}")

    grupos, indice, fila = _cerradura_grupos(grafo)

    acumulado = 0
    for arista in grafo.salida(nodo.id):
        if arista.tipo != RELACION_PERTENENCIA:
            continue
        j = indice.get(arista.destino)
        if j is None:
            continue
        # El grupo directo y todos los que ese grupo alcanza por anidamiento.
        acumulado |= 1 << j
        acumulado |= fila[j]

    resultado: set[str] = set()
    for j, gid in enumerate(grupos):
        if acumulado & (1 << j):
            resultado.add(gid)
    resultado.discard(nodo.id)
    return resultado
