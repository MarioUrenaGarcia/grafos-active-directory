"""Puntos de corte y plan de defensa minimo.

Este modulo contiene el aporte central del trabajo: en lugar de solo mostrar las
rutas de acceso, calcula cual es el conjunto minimo de accesos que hay que
revocar para que ningun objeto de entrada pueda llegar a un objetivo de alto
valor, y lo demuestra.

Dos herramientas:

1. Nodos de corte: objetos que aparecen en todas las rutas de un origen a los
   objetivos. Quitar uno de ellos rompe el alcance. Se detectan por el metodo
   directo de quitar el nodo y recomputar la alcanzabilidad.

2. Corte minimo de aristas (plan de defensa): se modela como un problema de
   flujo maximo. Una superfuente S se conecta a todos los objetos de entrada y
   todos los objetivos se conectan a un supersumidero T. Cada acceso revocable
   aporta capacidad; los accesos estructurales (que no se revocan) tienen
   capacidad infinita. Por el teorema de flujo maximo - corte minimo, el valor
   del flujo maximo iguala el tamanio del corte minimo, y por el teorema de
   Menger ese numero es la cantidad maxima de rutas disjuntas en aristas. El
   corte da la lista concreta de accesos a revocar, y el teorema garantiza que
   no existe una lista mas corta.
"""

from __future__ import annotations

from collections import defaultdict, deque

from .modelo import Arista, Grafo
from .recorridos import alcanzan_a, bfs_arbol

# Accesos que reflejan la estructura del directorio (contencion y vinculo de
# politicas), no permisos que un administrador revoque. Se tratan como no
# cortables para que el plan de defensa proponga solo cambios realizables.
TIPOS_ESTRUCTURALES = frozenset({"CONTAINS", "GP_LINK"})

# Capacidad que representa "no se puede cortar". Mayor que cualquier suma de
# accesos revocables posibles en el dataset.
INFINITO = 1 << 30


def nodos_de_corte(grafo: Grafo, origen: str, objetivos: list[str]) -> list[str]:
    """Objetos cuya eliminacion desconecta al origen de todos los objetivos.

    Son los cuellos de botella: estan en toda ruta del origen a los objetivos.
    Se prueban solo los candidatos que estan en alguna ruta (alcanzables desde
    el origen y que a su vez alcanzan algun objetivo), lo que acota el costo.
    """
    nodo_origen = grafo.resolver(origen)
    if nodo_origen is None:
        raise KeyError(f"No existe el objeto {origen!r}")
    ids_objetivo = _resolver_ids(grafo, objetivos)

    alcance_base = set(bfs_arbol(grafo, nodo_origen.id).keys())
    objetivos_alcanzables = alcance_base & ids_objetivo
    if not objetivos_alcanzables:
        return []

    # Candidatos: nodos intermedios que participan en alguna ruta.
    que_alcanzan_objetivo: set[str] = set()
    for oid in objetivos_alcanzables:
        que_alcanzan_objetivo |= alcanzan_a(grafo, oid)
    candidatos = (alcance_base & que_alcanzan_objetivo) - {nodo_origen.id} - ids_objetivo

    cortes: list[str] = []
    for candidato in candidatos:
        alcance = _bfs_excluyendo(grafo, nodo_origen.id, excluido=candidato)
        if not (alcance & objetivos_alcanzables):
            cortes.append(candidato)
    return cortes


def _bfs_excluyendo(grafo: Grafo, origen: str, excluido: str) -> set[str]:
    """Nodos alcanzables desde el origen omitiendo un nodo del grafo."""
    visitados = {origen}
    cola: deque[str] = deque([origen])
    while cola:
        actual = cola.popleft()
        for arista in grafo.salida(actual):
            destino = arista.destino
            if destino == excluido or destino in visitados:
                continue
            visitados.add(destino)
            cola.append(destino)
    visitados.discard(excluido)
    return visitados


# ----------------------------------------------------------------------
# Flujo maximo y corte minimo
# ----------------------------------------------------------------------
def _edmonds_karp(capacidad: dict[str, dict[str, int]], fuente: str, sumidero: str) -> int:
    """Flujo maximo entre fuente y sumidero (Edmonds-Karp).

    Edmonds-Karp es BFS repetido buscando caminos de aumento con la menor
    cantidad de aristas. Modifica la red residual en sitio y devuelve el valor
    del flujo. La red residual resultante se usa despues para extraer el corte.
    """
    flujo = 0
    while True:
        # BFS para hallar un camino de aumento en la red residual.
        padre: dict[str, str] = {fuente: fuente}
        cola: deque[str] = deque([fuente])
        while cola and sumidero not in padre:
            u = cola.popleft()
            for v, cap in capacidad[u].items():
                if cap > 0 and v not in padre:
                    padre[v] = u
                    cola.append(v)
        if sumidero not in padre:
            break
        # Cuello de botella del camino encontrado.
        cuello = INFINITO
        v = sumidero
        while v != fuente:
            u = padre[v]
            cuello = min(cuello, capacidad[u][v])
            v = u
        # Actualizacion de capacidades residuales.
        v = sumidero
        while v != fuente:
            u = padre[v]
            capacidad[u][v] -= cuello
            capacidad[v][u] += cuello
            v = u
        flujo += cuello
    return flujo


def _resolver_ids(grafo: Grafo, claves: list[str]) -> set[str]:
    ids: set[str] = set()
    for clave in claves:
        nodo = grafo.resolver(clave)
        if nodo is None:
            raise KeyError(f"No existe el objeto {clave!r}")
        ids.add(nodo.id)
    return ids


def plan_de_defensa(grafo: Grafo, fuentes: list[str], objetivos: list[str],
                    tipos_estructurales: frozenset[str] = TIPOS_ESTRUCTURALES) -> dict:
    """Conjunto minimo de accesos a revocar para aislar los objetivos.

    Construye la red de flujo, calcula el flujo maximo y extrae el corte minimo.
    Devuelve un diccionario con el tamanio del corte, los accesos a revocar
    (cada uno con su par de objetos y el tipo de relacion) y una verificacion de
    que tras revocarlos ninguna fuente alcanza ningun objetivo.
    """
    ids_fuente = _resolver_ids(grafo, fuentes)
    ids_objetivo = _resolver_ids(grafo, objetivos)
    solapan = ids_fuente & ids_objetivo
    if solapan:
        raise ValueError("Las fuentes y los objetivos no pueden solaparse")

    FUENTE, SUMIDERO = "__S__", "__T__"
    capacidad: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    # Capacidad agregada por par ordenado de objetos. Un par con algun acceso
    # estructural es no cortable (capacidad infinita); de lo contrario, su
    # capacidad es el numero de accesos revocables entre ambos.
    revocables_por_par: dict[tuple[str, str], list[Arista]] = defaultdict(list)
    estructural_por_par: set[tuple[str, str]] = set()
    for arista in grafo.aristas:
        par = (arista.origen, arista.destino)
        if arista.tipo in tipos_estructurales:
            estructural_por_par.add(par)
        else:
            revocables_por_par[par].append(arista)

    pares = set(revocables_por_par) | estructural_por_par
    for origen, destino in pares:
        if (origen, destino) in estructural_por_par:
            capacidad[origen][destino] = INFINITO
        else:
            capacidad[origen][destino] = len(revocables_por_par[(origen, destino)])
        capacidad[destino].setdefault(origen, 0)

    # Conexiones de la superfuente y el supersumidero (no cortables).
    for fid in ids_fuente:
        capacidad[FUENTE][fid] = INFINITO
        capacidad[fid].setdefault(FUENTE, 0)
    for oid in ids_objetivo:
        capacidad[oid][SUMIDERO] = INFINITO
        capacidad[SUMIDERO].setdefault(oid, 0)

    # Copia de las capacidades originales para distinguir despues las aristas
    # reales de las inversas creadas por el algoritmo.
    original = {u: dict(vs) for u, vs in capacidad.items()}

    valor = _edmonds_karp(capacidad, FUENTE, SUMIDERO)

    # Lado de la fuente en la red residual: nodos aun alcanzables desde S.
    lado_fuente = {FUENTE}
    cola: deque[str] = deque([FUENTE])
    while cola:
        u = cola.popleft()
        for v, cap in capacidad[u].items():
            if cap > 0 and v not in lado_fuente:
                lado_fuente.add(v)
                cola.append(v)

    # Aristas del corte: van del lado de la fuente al lado del sumidero y eran
    # arcos reales con capacidad finita. Se expanden a los accesos concretos.
    accesos: list[dict] = []
    for origen in lado_fuente:
        for destino, cap in original.get(origen, {}).items():
            if cap <= 0 or cap >= INFINITO:
                continue
            if destino in lado_fuente:
                continue
            for arista in revocables_por_par.get((origen, destino), []):
                accesos.append({
                    "origen": origen,
                    "destino": destino,
                    "origen_nombre": grafo.nodos[origen].nombre,
                    "destino_nombre": grafo.nodos[destino].nombre,
                    "tipo": arista.tipo,
                })

    verificado = _verificar_corte(grafo, ids_fuente, ids_objetivo,
                                  {(a["origen"], a["destino"], a["tipo"]) for a in accesos})

    return {
        "tamanio_corte": valor,
        "accesos_a_revocar": accesos,
        "fuentes": sorted(ids_fuente),
        "objetivos": sorted(ids_objetivo),
        "verificado": verificado,
    }


def _verificar_corte(grafo: Grafo, ids_fuente: set[str], ids_objetivo: set[str],
                     accesos_cortados: set[tuple[str, str, str]]) -> bool:
    """Comprueba empiricamente que tras revocar los accesos nadie llega.

    Recorre el grafo desde todas las fuentes ignorando las aristas del corte y
    confirma que ningun objetivo queda alcanzable. Es la comprobacion practica
    que acompania a la garantia teorica del teorema de corte minimo.
    """
    visitados = set(ids_fuente)
    cola: deque[str] = deque(ids_fuente)
    while cola:
        actual = cola.popleft()
        for arista in grafo.salida(actual):
            if (arista.origen, arista.destino, arista.tipo) in accesos_cortados:
                continue
            if arista.destino not in visitados:
                visitados.add(arista.destino)
                cola.append(arista.destino)
    return not (visitados & ids_objetivo)
