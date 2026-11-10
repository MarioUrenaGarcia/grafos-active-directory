"""Componentes fuertemente conexas y grafo condensado.

Dos objetos estan en la misma componente fuertemente conexa (SCC) si cada uno
puede llegar al otro. En este dominio eso significa un ciclo de control mutuo:
si cae uno, caen todos los de la componente. Detectarlas resume el grafo y
revela nucleos de riesgo.

Se usa el algoritmo de Tarjan, que calcula todas las SCC en una sola pasada en
tiempo lineal O(V + E). La version es iterativa para no depender del limite de
recursion de Python en grafos grandes.
"""

from __future__ import annotations

from .modelo import Grafo


def componentes_fuertemente_conexas(grafo: Grafo) -> list[list[str]]:
    """Lista de SCC; cada una es una lista de identificadores de nodo."""
    indice: dict[str, int] = {}
    bajo: dict[str, int] = {}
    en_pila: set[str] = set()
    pila: list[str] = []
    contador = 0
    componentes: list[list[str]] = []

    # Pila explicita de marcos (nodo, iterador de aristas de salida) para
    # simular la recursion de Tarjan.
    for inicio in grafo.nodos:
        if inicio in indice:
            continue
        trabajo: list[tuple[str, int]] = [(inicio, 0)]
        while trabajo:
            nodo, pos = trabajo[-1]
            if pos == 0:
                indice[nodo] = contador
                bajo[nodo] = contador
                contador += 1
                pila.append(nodo)
                en_pila.add(nodo)
            salientes = grafo.salida(nodo)
            if pos < len(salientes):
                trabajo[-1] = (nodo, pos + 1)
                vecino = salientes[pos].destino
                if vecino not in indice:
                    trabajo.append((vecino, 0))
                elif vecino in en_pila:
                    bajo[nodo] = min(bajo[nodo], indice[vecino])
            else:
                # Se termino de explorar el nodo: si es raiz de una SCC, se
                # extrae la componente completa de la pila.
                if bajo[nodo] == indice[nodo]:
                    componente: list[str] = []
                    while True:
                        w = pila.pop()
                        en_pila.discard(w)
                        componente.append(w)
                        if w == nodo:
                            break
                    componentes.append(componente)
                trabajo.pop()
                if trabajo:
                    padre = trabajo[-1][0]
                    bajo[padre] = min(bajo[padre], bajo[nodo])
    return componentes


def componentes_no_triviales(grafo: Grafo) -> list[list[str]]:
    """SCC con mas de un nodo, es decir, ciclos de control mutuo reales."""
    return [c for c in componentes_fuertemente_conexas(grafo) if len(c) > 1]


def grafo_condensado(grafo: Grafo) -> tuple[list[list[str]], dict[str, int], set[tuple[int, int]]]:
    """Condensa el grafo colapsando cada SCC en un supernodo.

    Devuelve la lista de componentes, un mapa nodo -> indice de componente y el
    conjunto de aristas entre componentes. El grafo condensado es siempre un
    DAG (grafo dirigido aciclico), propiedad util para razonar sobre el flujo
    de control sin ciclos.
    """
    componentes = componentes_fuertemente_conexas(grafo)
    de_nodo: dict[str, int] = {}
    for i, componente in enumerate(componentes):
        for nodo in componente:
            de_nodo[nodo] = i
    aristas: set[tuple[int, int]] = set()
    for arista in grafo.aristas:
        ci = de_nodo[arista.origen]
        cj = de_nodo[arista.destino]
        if ci != cj:
            aristas.add((ci, cj))
    return componentes, de_nodo, aristas
