"""Caminos de menor esfuerzo con el algoritmo de Dijkstra.

Mientras BFS encuentra el camino con menos saltos, Dijkstra encuentra el camino
de menor peso total usando el modelo de pesos del modulo pesos. Responde la
pregunta de cual es la ruta mas facil de recorrer, no solo la mas corta.
"""

from __future__ import annotations

import heapq

from .modelo import Arista, Grafo
from .pesos import peso as peso_de_tipo


def dijkstra(grafo: Grafo, origen: str) -> tuple[dict[str, int], dict[str, Arista | None]]:
    """Distancias de menor peso desde el origen a todos los nodos alcanzables.

    Devuelve dos diccionarios: la distancia acumulada por nodo y la arista con
    la que se llego a cada nodo, para poder reconstruir el camino.
    """
    if origen not in grafo.nodos:
        raise KeyError(f"El nodo {origen!r} no existe en el grafo")

    distancia: dict[str, int] = {origen: 0}
    previo: dict[str, Arista | None] = {origen: None}
    # La cola de prioridad guarda (distancia, nodo). Se marca el cierre de un
    # nodo al extraerlo con su distancia definitiva.
    monticulo: list[tuple[int, str]] = [(0, origen)]
    cerrados: set[str] = set()

    while monticulo:
        dist_actual, actual = heapq.heappop(monticulo)
        if actual in cerrados:
            continue
        cerrados.add(actual)
        for arista in grafo.salida(actual):
            vecino = arista.destino
            candidata = dist_actual + peso_de_tipo(arista.tipo)
            if vecino not in distancia or candidata < distancia[vecino]:
                distancia[vecino] = candidata
                previo[vecino] = arista
                heapq.heappush(monticulo, (candidata, vecino))
    return distancia, previo


def camino_mas_facil(grafo: Grafo, origen: str, destino: str) -> tuple[list[Arista], int] | None:
    """Camino de menor peso de origen a destino y su peso total.

    Devuelve None si el destino no es alcanzable desde el origen.
    """
    distancia, previo = dijkstra(grafo, origen)
    if destino not in distancia:
        return None
    aristas: list[Arista] = []
    actual = destino
    while actual != origen:
        arista = previo[actual]
        if arista is None:
            break
        aristas.append(arista)
        actual = arista.origen
    aristas.reverse()
    return aristas, distancia[destino]
