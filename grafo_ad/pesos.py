"""Modelo de pesos para los caminos del grafo.

Dijkstra necesita un peso por arista. Aqui el peso representa el esfuerzo
relativo que supone recorrer una relacion: cuanto menor, mas facil de usar. Una
pertenencia heredada (MEMBER_OF) es casi gratuita, mientras que aprovechar una
sesion activa en un equipo (HAS_SESSION) cuesta mas.

Los valores son una escala ordinal construida para este trabajo y son
configurables. Su proposito es doble:

1. Encontrar el camino de menor esfuerzo entre dos objetos (Dijkstra).
2. Priorizar que accesos conviene revisar primero.

Para convertir el problema en una suma (lo que exige Dijkstra) se trabaja con
estos pesos aditivos. Si en lugar de esfuerzo se dispusiera de probabilidades
de exito p por relacion, el camino mas probable maximiza el producto de las p,
y tomando -log(p) como peso ese producto se transforma en una suma minimizable,
de modo que el mismo Dijkstra resuelve ambos planteamientos.
"""

from __future__ import annotations

# Peso por tipo de relacion. Escala 1 (trivial) a 4 (requiere mas trabajo).
PESOS_POR_TIPO: dict[str, int] = {
    "MEMBER_OF": 1,
    "CONTAINS": 1,
    "ADMIN_TO": 1,
    "GENERIC_ALL": 1,
    "DC_SYNC": 1,
    "GET_CHANGES": 1,
    "GET_CHANGES_ALL": 1,
    "GP_LINK": 2,
    "OWNS": 2,
    "WRITE_DACL": 2,
    "WRITE_OWNER": 2,
    "GENERIC_WRITE": 2,
    "CAN_RDP": 3,
    "EXECUTE_DCOM": 3,
    "ALLOWED_TO_DELEGATE": 3,
    "HAS_SESSION": 4,
}

# Peso por omision para un tipo de relacion no catalogado.
PESO_POR_OMISION = 3


def peso(tipo: str) -> int:
    """Peso aditivo de una relacion segun su tipo."""
    return PESOS_POR_TIPO.get(tipo, PESO_POR_OMISION)
