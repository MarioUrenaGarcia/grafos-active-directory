"""Pruebas unitarias de los algoritmos sobre grafos sinteticos pequenios.

Cada grafo se construye a mano para conocer el resultado esperado de antemano y
poder comprobar que el algoritmo lo reproduce.
"""

import unittest

from grafo_ad.modelo import Grafo, Nodo, Arista
from grafo_ad.recorridos import camino_mas_corto, alcanzables, alcanzan_a
from grafo_ad.caminos import camino_mas_facil
from grafo_ad.componentes import componentes_no_triviales, grafo_condensado
from grafo_ad.transitiva import grupos_efectivos
from grafo_ad.centralidad import betweenness
from grafo_ad.cortes import plan_de_defensa, nodos_de_corte


def construir(nodos, aristas):
    """Crea un grafo a partir de ids y triples (origen, destino, tipo)."""
    g = Grafo()
    for nid, etiquetas in nodos:
        g.agregar_nodo(Nodo(id=nid, etiquetas=tuple(etiquetas),
                            propiedades={"name": nid}))
    for i, (o, d, t) in enumerate(aristas):
        g.agregar_arista(Arista(id=str(i), origen=o, destino=d, tipo=t))
    return g


class PruebaRecorridos(unittest.TestCase):
    def test_camino_mas_corto_cuenta_saltos(self):
        g = construir(
            [("a", []), ("b", []), ("c", []), ("d", [])],
            [("a", "b", "X"), ("b", "c", "X"), ("a", "d", "X"), ("d", "c", "X")],
        )
        camino = camino_mas_corto(g, "a", "c")
        self.assertEqual(len(camino), 2)

    def test_alcanzables_y_alcanzan_a_son_inversos(self):
        g = construir(
            [("a", []), ("b", []), ("c", [])],
            [("a", "b", "X"), ("b", "c", "X")],
        )
        self.assertEqual(alcanzables(g, "a"), {"b", "c"})
        self.assertEqual(alcanzan_a(g, "c"), {"a", "b"})

    def test_sin_camino_devuelve_none(self):
        g = construir([("a", []), ("b", [])], [])
        self.assertIsNone(camino_mas_corto(g, "a", "b"))


class PruebaDijkstra(unittest.TestCase):
    def test_prefiere_el_camino_de_menor_peso(self):
        # Ruta directa con un acceso costoso (HAS_SESSION, peso 4) frente a un
        # rodeo con dos accesos baratos (MEMBER_OF, peso 1 cada uno).
        g = construir(
            [("a", []), ("b", []), ("t", [])],
            [("a", "t", "HAS_SESSION"),
             ("a", "b", "MEMBER_OF"), ("b", "t", "MEMBER_OF")],
        )
        aristas, peso = camino_mas_facil(g, "a", "t")
        self.assertEqual(peso, 2)
        self.assertEqual(len(aristas), 2)


class PruebaComponentes(unittest.TestCase):
    def test_detecta_ciclo_de_control_mutuo(self):
        g = construir(
            [("a", []), ("b", []), ("c", [])],
            [("a", "b", "X"), ("b", "a", "X"), ("b", "c", "X")],
        )
        no_triviales = componentes_no_triviales(g)
        self.assertEqual(len(no_triviales), 1)
        self.assertEqual(set(no_triviales[0]), {"a", "b"})

    def test_condensado_es_aciclico(self):
        g = construir(
            [("a", []), ("b", []), ("c", [])],
            [("a", "b", "X"), ("b", "a", "X"), ("b", "c", "X")],
        )
        componentes, de_nodo, aristas = grafo_condensado(g)
        # Dos supernodos: el ciclo {a,b} y {c}, con una arista entre ellos.
        self.assertEqual(len(componentes), 2)
        self.assertEqual(len(aristas), 1)


class PruebaTransitiva(unittest.TestCase):
    def test_pertenencia_heredada_por_grupos_anidados(self):
        g = construir(
            [("u", ["User"]), ("g1", ["Group"]), ("g2", ["Group"]), ("g3", ["Group"])],
            [("u", "g1", "MEMBER_OF"),
             ("g1", "g2", "MEMBER_OF"), ("g2", "g3", "MEMBER_OF")],
        )
        self.assertEqual(grupos_efectivos(g, "u"), {"g1", "g2", "g3"})


class PruebaCentralidad(unittest.TestCase):
    def test_nodo_puente_concentra_la_centralidad(self):
        aristas = {("a", "b"), ("b", "c")}
        puntajes = betweenness(aristas)
        self.assertEqual(puntajes["b"], 1.0)
        self.assertEqual(puntajes["a"], 0.0)
        self.assertEqual(puntajes["c"], 0.0)


class PruebaCorteMinimo(unittest.TestCase):
    def test_un_solo_cuello_de_botella(self):
        # Dos fuentes convergen en m y de ahi al objetivo: basta cortar m -> t.
        g = construir(
            [("u1", []), ("u2", []), ("m", []), ("t", [])],
            [("u1", "m", "X"), ("u2", "m", "X"), ("m", "t", "X")],
        )
        plan = plan_de_defensa(g, ["u1", "u2"], ["t"])
        self.assertEqual(plan["tamanio_corte"], 1)
        self.assertTrue(plan["verificado"])

    def test_dos_rutas_disjuntas_exigen_dos_cortes(self):
        g = construir(
            [("u", []), ("a", []), ("b", []), ("t", [])],
            [("u", "a", "X"), ("a", "t", "X"), ("u", "b", "X"), ("b", "t", "X")],
        )
        plan = plan_de_defensa(g, ["u"], ["t"])
        self.assertEqual(plan["tamanio_corte"], 2)
        self.assertTrue(plan["verificado"])

    def test_accesos_estructurales_no_se_cortan(self):
        # El unico acceso al objetivo es estructural (CONTAINS): no se revoca y
        # por lo tanto no existe plan de corte finito.
        g = construir(
            [("u", []), ("t", [])],
            [("u", "t", "CONTAINS")],
        )
        plan = plan_de_defensa(g, ["u"], ["t"])
        self.assertEqual(plan["accesos_a_revocar"], [])
        self.assertFalse(plan["verificado"])

    def test_nodos_de_corte(self):
        g = construir(
            [("u", []), ("m", []), ("t", [])],
            [("u", "m", "X"), ("m", "t", "X")],
        )
        self.assertEqual(nodos_de_corte(g, "u", ["t"]), ["m"])


if __name__ == "__main__":
    unittest.main()
