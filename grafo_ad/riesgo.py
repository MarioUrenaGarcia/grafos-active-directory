"""Metricas de riesgo y comparacion antes y despues de la defensa.

Convierte el analisis en numeros comparables: cuantos objetos de entrada
alcanzan los objetivos antes de aplicar el plan de defensa y cuantos despues.
Permite cuantificar la reduccion de exposicion que logra el corte minimo.
"""

from __future__ import annotations

from collections import deque

from .modelo import Grafo
from .recorridos import alcanzan_a


def exposicion(grafo: Grafo, objetivos: list[str], universo_fuentes: list[str] | None = None) -> dict:
    """Mide cuantos objetos de entrada alcanzan los objetivos.

    Si no se da un universo de fuentes, se consideran todos los objetos que no
    son objetivo. Devuelve el total de fuentes, cuantas alcanzan algun objetivo
    y la fraccion que representan.
    """
    ids_objetivo = set()
    for clave in objetivos:
        nodo = grafo.resolver(clave)
        if nodo is None:
            raise KeyError(f"No existe el objetivo {clave!r}")
        ids_objetivo.add(nodo.id)

    if universo_fuentes is None:
        fuentes = {n.id for n in grafo.nodos.values()} - ids_objetivo
    else:
        fuentes = set()
        for clave in universo_fuentes:
            nodo = grafo.resolver(clave)
            if nodo is None:
                raise KeyError(f"No existe la fuente {clave!r}")
            fuentes.add(nodo.id)

    expuestas: set[str] = set()
    for oid in ids_objetivo:
        expuestas |= alcanzan_a(grafo, oid)
    expuestas &= fuentes

    total = len(fuentes)
    return {
        "total_fuentes": total,
        "fuentes_expuestas": len(expuestas),
        "fraccion": (len(expuestas) / total) if total else 0.0,
    }


def exposicion_tras_corte(grafo: Grafo, objetivos: list[str],
                          accesos_cortados: set[tuple[str, str, str]],
                          universo_fuentes: list[str] | None = None) -> dict:
    """Exposicion recalculada tras revocar un conjunto de accesos.

    Reusa la logica de alcance pero ignorando las aristas del corte, sin
    modificar el grafo original.
    """
    ids_objetivo = set()
    for clave in objetivos:
        nodo = grafo.resolver(clave)
        if nodo is None:
            raise KeyError(f"No existe el objetivo {clave!r}")
        ids_objetivo.add(nodo.id)

    if universo_fuentes is None:
        fuentes = {n.id for n in grafo.nodos.values()} - ids_objetivo
    else:
        fuentes = set()
        for clave in universo_fuentes:
            nodo = grafo.resolver(clave)
            if nodo is None:
                raise KeyError(f"No existe la fuente {clave!r}")
            fuentes.add(nodo.id)

    expuestas: set[str] = set()
    for oid in ids_objetivo:
        expuestas |= _alcanzan_a_sin(grafo, oid, accesos_cortados)
    expuestas &= fuentes

    total = len(fuentes)
    return {
        "total_fuentes": total,
        "fuentes_expuestas": len(expuestas),
        "fraccion": (len(expuestas) / total) if total else 0.0,
    }


def _alcanzan_a_sin(grafo: Grafo, destino: str,
                    accesos_cortados: set[tuple[str, str, str]]) -> set[str]:
    """Nodos que alcanzan el destino ignorando las aristas del corte."""
    visitados = {destino}
    cola: deque[str] = deque([destino])
    while cola:
        actual = cola.popleft()
        for arista in grafo.entrada(actual):
            if (arista.origen, arista.destino, arista.tipo) in accesos_cortados:
                continue
            if arista.origen not in visitados:
                visitados.add(arista.origen)
                cola.append(arista.origen)
    visitados.discard(destino)
    return visitados
