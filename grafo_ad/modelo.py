"""Modelo de datos del grafo de Active Directory.

El conjunto de datos es un export JSON de Neo4j con un objeto por linea. Cada
objeto es un nodo o una relacion dirigida. Aqui se representa como un grafo
dirigido G = (V, E) con listas de adyacencia directa e inversa, mas indices por
nombre y por identificador de objeto para resolver consultas por clave.

Semantica del grafo: una arista A -> B significa "quien controla A puede llegar
a controlar B". Por eso todo el analisis posterior se reduce a preguntas de
alcanzabilidad, caminos y cortes sobre este grafo dirigido.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field


# Etiqueta que marca un objetivo de alto valor (las "joyas de la corona").
ETIQUETA_ALTO_VALOR = "HighValue"

# Identificador del grupo de administradores del dominio en el dataset de
# ejemplo. Es un objetivo natural para el analisis de rutas de acceso.
OBJECTID_DOMAIN_ADMINS = "S-1-5-21-883232822-274137685-4173207997-512"


@dataclass(frozen=True)
class Nodo:
    """Objeto del directorio: usuario, equipo, grupo, dominio, GPO u OU."""

    id: str
    etiquetas: tuple[str, ...]
    propiedades: dict

    @property
    def nombre(self) -> str:
        return self.propiedades.get("name", self.id)

    @property
    def tipo(self) -> str:
        # La primera etiqueta distinta del marcador de alto valor define el
        # tipo real del objeto en el directorio.
        for etiqueta in self.etiquetas:
            if etiqueta != ETIQUETA_ALTO_VALOR:
                return etiqueta
        return self.etiquetas[0] if self.etiquetas else "Desconocido"

    @property
    def alto_valor(self) -> bool:
        return ETIQUETA_ALTO_VALOR in self.etiquetas


@dataclass(frozen=True)
class Arista:
    """Relacion dirigida entre dos objetos del directorio.

    El tipo corresponde a la clase de acceso o pertenencia (por ejemplo
    MEMBER_OF o ADMIN_TO). Las propiedades guardan metadatos del export, como
    si la relacion proviene de una lista de control de acceso (isacl).
    """

    id: str
    origen: str
    destino: str
    tipo: str
    propiedades: dict = field(default_factory=dict)


class Grafo:
    """Grafo dirigido con indices de apoyo para el analisis."""

    def __init__(self) -> None:
        self.nodos: dict[str, Nodo] = {}
        self.aristas: list[Arista] = []
        self._salida: dict[str, list[Arista]] = defaultdict(list)
        self._entrada: dict[str, list[Arista]] = defaultdict(list)
        self._por_nombre: dict[str, str] = {}
        self._por_objectid: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Construccion
    # ------------------------------------------------------------------
    def agregar_nodo(self, nodo: Nodo) -> None:
        self.nodos[nodo.id] = nodo
        nombre = nodo.propiedades.get("name")
        if nombre is not None:
            self._por_nombre[nombre.lower()] = nodo.id
        objectid = nodo.propiedades.get("objectid")
        if objectid is not None:
            self._por_objectid[objectid] = nodo.id

    def agregar_arista(self, arista: Arista) -> None:
        if arista.origen not in self.nodos or arista.destino not in self.nodos:
            raise ValueError(
                f"La arista {arista.id} referencia un nodo inexistente "
                f"({arista.origen} -> {arista.destino})"
            )
        self.aristas.append(arista)
        self._salida[arista.origen].append(arista)
        self._entrada[arista.destino].append(arista)

    # ------------------------------------------------------------------
    # Adyacencia
    # ------------------------------------------------------------------
    def salida(self, nid: str) -> list[Arista]:
        """Aristas que salen del nodo (sucesores)."""
        return self._salida.get(nid, [])

    def entrada(self, nid: str) -> list[Arista]:
        """Aristas que entran al nodo (predecesores)."""
        return self._entrada.get(nid, [])

    def grado_salida(self, nid: str) -> int:
        return len(self._salida.get(nid, []))

    def grado_entrada(self, nid: str) -> int:
        return len(self._entrada.get(nid, []))

    # ------------------------------------------------------------------
    # Consultas por clave
    # ------------------------------------------------------------------
    def buscar_por_nombre(self, nombre: str) -> Nodo | None:
        nid = self._por_nombre.get(nombre.lower())
        return self.nodos.get(nid) if nid is not None else None

    def buscar_por_objectid(self, objectid: str) -> Nodo | None:
        nid = self._por_objectid.get(objectid)
        return self.nodos.get(nid) if nid is not None else None

    def resolver(self, clave: str) -> Nodo | None:
        """Resuelve un nodo por id interno, nombre o identificador de objeto."""
        if clave in self.nodos:
            return self.nodos[clave]
        nodo = self.buscar_por_nombre(clave)
        if nodo is not None:
            return nodo
        return self.buscar_por_objectid(clave)

    # ------------------------------------------------------------------
    # Selecciones
    # ------------------------------------------------------------------
    def por_etiqueta(self, etiqueta: str) -> list[Nodo]:
        return [n for n in self.nodos.values() if etiqueta in n.etiquetas]

    def por_tipo(self, tipo: str) -> list[Nodo]:
        return [n for n in self.nodos.values() if n.tipo == tipo]

    def altos_valores(self) -> list[Nodo]:
        return [n for n in self.nodos.values() if n.alto_valor]

    def tipos_de_arista(self) -> set[str]:
        return {a.tipo for a in self.aristas}

    def __len__(self) -> int:
        return len(self.nodos)


def cargar_json(ruta: str) -> Grafo:
    """Construye el grafo a partir del export JSON de Neo4j.

    El formato tiene un objeto JSON por linea. Los nodos se cargan primero
    aunque el archivo los intercale con relaciones, para garantizar que toda
    arista referencie nodos ya existentes.
    """
    nodos_crudos: list[dict] = []
    aristas_crudas: list[dict] = []

    with open(ruta, encoding="utf-8") as archivo:
        for numero, linea in enumerate(archivo, start=1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                objeto = json.loads(linea)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON inválido en la línea {numero} de {ruta}: {exc}"
                ) from exc
            tipo = objeto.get("type")
            if tipo == "node":
                nodos_crudos.append(objeto)
            elif tipo == "relationship":
                aristas_crudas.append(objeto)
            else:
                raise ValueError(
                    f"Tipo de objeto desconocido en la línea {numero}: {tipo!r}"
                )

    grafo = Grafo()
    for objeto in nodos_crudos:
        grafo.agregar_nodo(
            Nodo(
                id=objeto["id"],
                etiquetas=tuple(objeto.get("labels", [])),
                propiedades=objeto.get("properties", {}),
            )
        )
    for objeto in aristas_crudas:
        grafo.agregar_arista(
            Arista(
                id=objeto["id"],
                origen=objeto["start"]["id"],
                destino=objeto["end"]["id"],
                tipo=objeto["label"],
                propiedades=objeto.get("properties", {}),
            )
        )
    return grafo
