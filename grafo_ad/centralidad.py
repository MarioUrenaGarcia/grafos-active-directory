"""Rutas de acceso materializadas y centralidad de intermediacion.

Reproduce el analisis del ejemplo original: a partir de cada objeto normal se
toma el camino mas corto hasta un objetivo de alto valor y se materializa como
un subgrafo de rutas de acceso. Sobre ese subgrafo se calcula la centralidad de
intermediacion (betweenness) para identificar los objetos que actuan como
puente en la mayor cantidad de rutas.

La centralidad se calcula con el algoritmo de Brandes para grafos dirigidos sin
pesos, que corre en O(V * E).
"""

from __future__ import annotations

from collections import deque

from .modelo import Grafo, OBJECTID_DOMAIN_ADMINS
from .recorridos import bfs_arbol


def subgrafo_rutas_ataque(grafo: Grafo, objetivo_objectid: str = OBJECTID_DOMAIN_ADMINS,
                          incluir_alto_valor: bool = False) -> set[tuple[str, str]]:
    """Aristas (origen, destino) que forman las rutas de acceso al objetivo.

    Para cada objeto que no es de alto valor se reconstruye un camino mas corto
    al objetivo y se agregan sus pares consecutivos de nodos. El resultado es el
    conjunto de aristas del subgrafo de rutas, sin duplicados.
    """
    objetivo = grafo.buscar_por_objectid(objetivo_objectid)
    if objetivo is None:
        raise KeyError(f"No existe un objetivo con objectid {objetivo_objectid!r}")

    # Arbol de alcance inverso: que nodos pueden llegar al objetivo.
    arbol_inverso = bfs_arbol(grafo, objetivo.id, invertido=True)

    rutas: set[tuple[str, str]] = set()
    for nodo in grafo.nodos.values():
        if nodo.id == objetivo.id:
            continue
        if not incluir_alto_valor and nodo.alto_valor:
            continue
        if nodo.id not in arbol_inverso:
            continue
        # En el arbol del BFS inverso, la arista asociada a un nodo sale de ese
        # nodo hacia el objetivo. Se avanza por su destino hasta llegar.
        actual = nodo.id
        while actual != objetivo.id:
            arista = arbol_inverso[actual]
            if arista is None:
                break
            rutas.add((arista.origen, arista.destino))
            actual = arista.destino
    return rutas


def betweenness(aristas: set[tuple[str, str]]) -> dict[str, float]:
    """Centralidad de intermediacion (Brandes) sobre un conjunto de aristas.

    Se construye primero la lista de adyacencia del subgrafo inducido por las
    aristas dadas y luego se acumula la dependencia de cada nodo como puente de
    los caminos mas cortos entre los demas.
    """
    adyacencia: dict[str, list[str]] = {}
    nodos: set[str] = set()
    for origen, destino in aristas:
        adyacencia.setdefault(origen, []).append(destino)
        adyacencia.setdefault(destino, [])
        nodos.add(origen)
        nodos.add(destino)

    centralidad: dict[str, float] = {n: 0.0 for n in nodos}

    for fuente in nodos:
        pila: list[str] = []
        predecesores: dict[str, list[str]] = {n: [] for n in nodos}
        sigma: dict[str, float] = {n: 0.0 for n in nodos}
        sigma[fuente] = 1.0
        distancia: dict[str, int] = {n: -1 for n in nodos}
        distancia[fuente] = 0
        cola: deque[str] = deque([fuente])

        while cola:
            v = cola.popleft()
            pila.append(v)
            for w in adyacencia[v]:
                if distancia[w] < 0:
                    distancia[w] = distancia[v] + 1
                    cola.append(w)
                if distancia[w] == distancia[v] + 1:
                    sigma[w] += sigma[v]
                    predecesores[w].append(v)

        dependencia: dict[str, float] = {n: 0.0 for n in nodos}
        while pila:
            w = pila.pop()
            for v in predecesores[w]:
                if sigma[w] != 0.0:
                    dependencia[v] += (sigma[v] / sigma[w]) * (1.0 + dependencia[w])
            if w != fuente:
                centralidad[w] += dependencia[w]
    return centralidad
