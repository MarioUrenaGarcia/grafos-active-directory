"""Analisis de un grafo de Active Directory con teoria de grafos.

El paquete carga un entorno de directorio activo modelado como grafo dirigido y
expone los algoritmos clasicos de matematicas discretas que permiten pasar del
analisis de rutas de acceso al calculo de un plan de defensa minimo.
"""

from .modelo import Grafo, Nodo, Arista, cargar_json

__all__ = ["Grafo", "Nodo", "Arista", "cargar_json"]
