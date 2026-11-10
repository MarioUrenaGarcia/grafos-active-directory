"""Algoritmos instrumentados que registran su ejecucion paso a paso.

A diferencia de los modulos de analisis, que solo devuelven el resultado, aqui
cada algoritmo emite una traza: la secuencia de pasos que realiza. La aplicacion
web reproduce esa traza para mostrar como trabaja el algoritmo sobre el grafo.

Tambien se calcula la disposicion radial de los nodos y el subgrafo de trabajo
(los objetos que pueden alcanzar el objetivo), de modo que el servidor solo
traduce estructuras a JSON.

Todas las funciones reciben un mapa idx que asigna a cada identificador de nodo
un indice entero estable, para que el cliente referencie los nodos por indice.
"""

from __future__ import annotations

import heapq
import math
from collections import deque

from .modelo import Grafo
from .pesos import peso as peso_de_tipo
from .recorridos import alcanzan_a


def subgrafo_objetivo(grafo: Grafo, objetivo_id: str) -> set[str]:
    """Objetos que pueden alcanzar el objetivo, mas el objetivo mismo.

    Es el universo de trabajo: todo camino hacia el objetivo vive aqui, asi que
    restringir los algoritmos a este conjunto no cambia ningun resultado y
    mantiene la vista legible.
    """
    permitidos = alcanzan_a(grafo, objetivo_id)
    permitidos.add(objetivo_id)
    return permitidos


def layout_radial(grafo: Grafo, objetivo_id: str, permitidos: set[str]) -> dict[str, tuple[float, float]]:
    """Posiciones (x, y) de los nodos en un arbol radial centrado en el objetivo.

    La profundidad de cada nodo es su distancia al objetivo; el angulo se reparte
    entre los subarboles de forma proporcional a su numero de hojas.
    """
    # BFS inverso desde el objetivo para obtener profundidad y siguiente salto.
    prof = {objetivo_id: 0}
    padre = {objetivo_id: None}
    cola = deque([objetivo_id])
    while cola:
        u = cola.popleft()
        for arista in grafo.entrada(u):
            v = arista.origen
            if v in permitidos and v not in prof:
                prof[v] = prof[u] + 1
                padre[v] = v  # marcador temporal
                cola.append(v)

    # Hijos de cada nodo: los que lo tienen como siguiente salto hacia el objetivo.
    hijos: dict[str, list[str]] = {}
    siguiente: dict[str, str] = {}
    cola = deque([objetivo_id])
    vistos = {objetivo_id}
    while cola:
        u = cola.popleft()
        for arista in grafo.entrada(u):
            v = arista.origen
            if v in permitidos and v not in vistos:
                vistos.add(v)
                siguiente[v] = u
                hijos.setdefault(u, []).append(v)
                cola.append(v)

    hojas: dict[str, int] = {}

    def contar(u: str) -> int:
        hs = hijos.get(u, [])
        if not hs:
            hojas[u] = 1
            return 1
        total = sum(contar(h) for h in hs)
        hojas[u] = total
        return total

    contar(objetivo_id)

    prof_max = max(prof.values()) if prof else 1
    paso = 360.0 / (prof_max + 1)
    pos: dict[str, tuple[float, float]] = {}

    # Recorrido iterativo para repartir angulos sin recursion profunda.
    pila = [(objetivo_id, 0.0, 360.0)]
    while pila:
        u, a0, a1 = pila.pop()
        ang = (a0 + a1) / 2.0
        r = prof[u] * paso
        rad = math.radians(ang)
        pos[u] = (math.cos(rad) * r, math.sin(rad) * r)
        hs = sorted(hijos.get(u, []), key=lambda h: hojas[h], reverse=True)
        total = hojas[u]
        a = a0
        for h in hs:
            frac = hojas[h] / total
            pila.append((h, a, a + (a1 - a0) * frac))
            a += (a1 - a0) * frac
    return pos


# ----------------------------------------------------------------------
# Trazas de los algoritmos
# ----------------------------------------------------------------------
def bfs_traza(grafo: Grafo, idx: dict[str, int], permitidos: set[str],
              origen_id: str, objetivo_id: str) -> dict:
    """Traza de BFS: por cada nodo expandido, que nodos descubre."""
    visitados = {origen_id}
    padre: dict[str, object] = {origen_id: None}
    cola = deque([origen_id])
    pasos = []
    while cola:
        u = cola.popleft()
        descubre = []
        for arista in grafo.salida(u):
            v = arista.destino
            if v not in permitidos or v in visitados:
                continue
            visitados.add(v)
            padre[v] = arista
            cola.append(v)
            descubre.append([idx[u], idx[v], arista.tipo])
        pasos.append({"nodo": idx[u], "descubre": descubre})
        if objetivo_id in visitados:
            break
    camino = _reconstruir(idx, padre, origen_id, objetivo_id)
    return {
        "algoritmo": "bfs",
        "pasos": pasos,
        "camino": camino,
        "encontrado": objetivo_id in visitados,
        "saltos": len(camino),
    }


def dijkstra_traza(grafo: Grafo, idx: dict[str, int], permitidos: set[str],
                   origen_id: str, objetivo_id: str,
                   pesos: dict[str, int] | None = None) -> dict:
    """Traza de Dijkstra: por cada nodo cerrado, que aristas relaja."""
    def peso(tipo: str) -> int:
        if pesos is not None and tipo in pesos:
            return pesos[tipo]
        return peso_de_tipo(tipo)

    distancia = {origen_id: 0}
    previo: dict[str, object] = {origen_id: None}
    monticulo = [(0, origen_id)]
    cerrados: set[str] = set()
    pasos = []
    while monticulo:
        d, u = heapq.heappop(monticulo)
        if u in cerrados:
            continue
        cerrados.add(u)
        relaja = []
        for arista in grafo.salida(u):
            v = arista.destino
            if v not in permitidos:
                continue
            nd = d + peso(arista.tipo)
            if v not in distancia or nd < distancia[v]:
                distancia[v] = nd
                previo[v] = arista
                heapq.heappush(monticulo, (nd, v))
                relaja.append([idx[u], idx[v], arista.tipo, nd])
        pasos.append({"nodo": idx[u], "dist": d, "relaja": relaja})
        if u == objetivo_id:
            break
    camino = _reconstruir(idx, previo, origen_id, objetivo_id)
    return {
        "algoritmo": "dijkstra",
        "pasos": pasos,
        "camino": camino,
        "encontrado": objetivo_id in distancia,
        "peso": distancia.get(objetivo_id),
        "saltos": len(camino),
    }


def defensa_traza(grafo: Grafo, idx: dict[str, int], permitidos: set[str],
                  objetivo_id: str, fuentes_ids: list[str],
                  estructurales: frozenset[str]) -> dict:
    """Traza de Edmonds-Karp: cada camino de aumento y el corte final.

    Devuelve la lista de caminos de aumento hallados (rutas disjuntas en
    aristas), el valor del flujo, las aristas del corte minimo y la exposicion
    antes y despues de revocar esos accesos.
    """
    INF = 1 << 30
    FUENTE, SUMIDERO = "__S__", "__T__"

    # Capacidad agregada por par ordenado; un par estructural es no cortable.
    revocables: dict[tuple[str, str], list] = {}
    estruct_par: set[tuple[str, str]] = set()
    for arista in grafo.aristas:
        if arista.origen not in permitidos or arista.destino not in permitidos:
            continue
        par = (arista.origen, arista.destino)
        if arista.tipo in estructurales:
            estruct_par.add(par)
        else:
            revocables.setdefault(par, []).append(arista)

    cap: dict[str, dict[str, int]] = {}

    def add(u, v, c):
        cap.setdefault(u, {}).setdefault(v, 0)
        cap.setdefault(v, {}).setdefault(u, 0)
        cap[u][v] += c

    orig: dict[tuple[str, str], int] = {}
    for par in set(revocables) | estruct_par:
        u, v = par
        if par in estruct_par:
            add(u, v, INF)
        else:
            c = len(revocables[par])
            add(u, v, c)
            orig[par] = c

    fuentes_validas = [f for f in fuentes_ids if f in permitidos and f != objetivo_id]
    for f in fuentes_validas:
        add(FUENTE, f, INF)
    add(objetivo_id, SUMIDERO, INF)

    # Flujo maximo registrando cada camino de aumento (en nodos reales).
    caminos = []
    while True:
        padre = {FUENTE: FUENTE}
        cola = deque([FUENTE])
        while cola and SUMIDERO not in padre:
            u = cola.popleft()
            for v, c in cap.get(u, {}).items():
                if c > 0 and v not in padre:
                    padre[v] = u
                    cola.append(v)
        if SUMIDERO not in padre:
            break
        # Reconstruir el camino y su cuello de botella.
        secuencia = []
        cuello = INF
        v = SUMIDERO
        while v != FUENTE:
            u = padre[v]
            cuello = min(cuello, cap[u][v])
            secuencia.append(v)
            v = u
        secuencia.reverse()
        v = SUMIDERO
        while v != FUENTE:
            u = padre[v]
            cap[u][v] -= cuello
            cap[v][u] += cuello
            v = u
        nodos_reales = [idx[n] for n in secuencia if n not in (FUENTE, SUMIDERO)]
        caminos.append(nodos_reales)

    # Lado de la fuente en la red residual: el corte.
    lado = {FUENTE}
    cola = deque([FUENTE])
    while cola:
        u = cola.popleft()
        for v, c in cap.get(u, {}).items():
            if c > 0 and v not in lado:
                lado.add(v)
                cola.append(v)

    corte = []
    corte_ids = set()
    for (u, v), c in orig.items():
        if u in lado and v not in lado:
            for arista in revocables[(u, v)]:
                corte.append([idx[u], idx[v], arista.tipo])
                corte_ids.add((u, v, arista.tipo))

    # Exposicion antes y despues dentro del subgrafo de trabajo.
    antes = len(permitidos) - 1
    seguros = _seguros_tras_corte(grafo, permitidos, objetivo_id, corte_ids)
    despues = antes - len(seguros)
    return {
        "algoritmo": "defensa",
        "caminos": caminos,
        # El valor del flujo maximo es igual al tamanio del corte (numero de
        # accesos a revocar); los caminos de aumento pueden ser menos cuando
        # alguno transporta mas de una unidad.
        "flujo": len(corte),
        "nCaminos": len(caminos),
        "corte": corte,
        "antes": antes,
        "despues": max(despues, 0),
        "seguros": [idx[s] for s in seguros],
    }


def _seguros_tras_corte(grafo: Grafo, permitidos: set[str], objetivo_id: str,
                        corte_ids: set[tuple[str, str, str]]) -> set[str]:
    """Nodos del subgrafo que dejan de alcanzar el objetivo tras el corte."""
    alcanza = {objetivo_id}
    cola = deque([objetivo_id])
    while cola:
        u = cola.popleft()
        for arista in grafo.entrada(u):
            v = arista.origen
            if v not in permitidos:
                continue
            if (arista.origen, arista.destino, arista.tipo) in corte_ids:
                continue
            if v not in alcanza:
                alcanza.add(v)
                cola.append(v)
    seguros = (permitidos - alcanza) - {objetivo_id}
    return seguros


def _reconstruir(idx: dict[str, int], previo: dict[str, object],
                 origen_id: str, objetivo_id: str) -> list:
    """Reconstruye el camino origen -> objetivo como lista de aristas."""
    if objetivo_id not in previo:
        return []
    camino = []
    actual = objetivo_id
    while actual != origen_id:
        arista = previo[actual]
        if arista is None:
            break
        camino.append([idx[arista.origen], idx[arista.destino], arista.tipo])
        actual = arista.origen
    camino.reverse()
    return camino
