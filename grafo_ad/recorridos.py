"""Recorridos y alcanzabilidad sobre el grafo dirigido.

Reune los algoritmos de busqueda que responden las preguntas de alcance:

- BFS y DFS como recorridos base.
- Conjunto de nodos alcanzables desde un origen (que puede controlar X).
- Conjunto de nodos que alcanzan a un destino, usando el grafo inverso (quien
  puede llegar a controlar Y).
- Camino mas corto en numero de saltos (BFS), que es la version en Python del
  shortestPath del ejemplo original.
"""

from __future__ import annotations

from collections import deque

from .modelo import Arista, Grafo


def bfs_arbol(grafo: Grafo, origen: str, invertido: bool = False) -> dict[str, Arista | None]:
    """Arbol de busqueda en anchura desde el origen.

    Devuelve un diccionario nodo -> arista usada para llegar a el. El origen
    apunta a None. Si invertido es verdadero, recorre el grafo con las aristas
    al reves, lo que sirve para preguntar quien alcanza a un nodo.
    """
    if origen not in grafo.nodos:
        raise KeyError(f"El nodo {origen!r} no existe en el grafo")

    vecinos = grafo.entrada if invertido else grafo.salida
    extremo = (lambda a: a.origen) if invertido else (lambda a: a.destino)

    arbol: dict[str, Arista | None] = {origen: None}
    cola: deque[str] = deque([origen])
    while cola:
        actual = cola.popleft()
        for arista in vecinos(actual):
            siguiente = extremo(arista)
            if siguiente not in arbol:
                arbol[siguiente] = arista
                cola.append(siguiente)
    return arbol


def alcanzables(grafo: Grafo, origen: str) -> set[str]:
    """Nodos a los que el origen puede llegar directa o indirectamente."""
    destino = set(bfs_arbol(grafo, origen).keys())
    destino.discard(origen)
    return destino


def alcanzan_a(grafo: Grafo, destino: str) -> set[str]:
    """Nodos que pueden llegar al destino (busqueda en el grafo inverso)."""
    origenes = set(bfs_arbol(grafo, destino, invertido=True).keys())
    origenes.discard(destino)
    return origenes


def dfs_orden(grafo: Grafo, origen: str) -> list[str]:
    """Orden de visita en profundidad desde el origen (iterativo)."""
    if origen not in grafo.nodos:
        raise KeyError(f"El nodo {origen!r} no existe en el grafo")

    visitados: set[str] = set()
    orden: list[str] = []
    pila: list[str] = [origen]
    while pila:
        actual = pila.pop()
        if actual in visitados:
            continue
        visitados.add(actual)
        orden.append(actual)
        # Se apilan los sucesores en orden inverso para visitarlos en el orden
        # natural de las aristas.
        for arista in reversed(grafo.salida(actual)):
            if arista.destino not in visitados:
                pila.append(arista.destino)
    return orden


def reconstruir_camino(arbol: dict[str, Arista | None], origen: str, destino: str,
                       invertido: bool = False) -> list[Arista] | None:
    """Reconstruye la lista de aristas de origen a destino a partir del arbol."""
    if destino not in arbol:
        return None
    aristas: list[Arista] = []
    actual = destino
    while actual != origen:
        arista = arbol[actual]
        if arista is None:
            break
        aristas.append(arista)
        actual = arista.destino if invertido else arista.origen
    aristas.reverse()
    return aristas


def camino_mas_corto(grafo: Grafo, origen: str, destino: str) -> list[Arista] | None:
    """Camino con menos saltos entre origen y destino, o None si no existe."""
    arbol = bfs_arbol(grafo, origen)
    return reconstruir_camino(arbol, origen, destino)


def distancia_en_saltos(grafo: Grafo, origen: str, destino: str) -> int | None:
    """Numero de saltos del camino mas corto, o None si no hay camino."""
    camino = camino_mas_corto(grafo, origen, destino)
    return None if camino is None else len(camino)
