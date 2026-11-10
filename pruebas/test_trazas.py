"""Pruebas de los algoritmos instrumentados y de la disposicion radial.

Verifican que la traza producida para la aplicacion web coincide en su resultado
con los algoritmos de analisis, sobre grafos pequenios de resultado conocido.
"""

import unittest

from grafo_ad.cortes import TIPOS_ESTRUCTURALES
from grafo_ad.modelo import Grafo, Nodo, Arista
from grafo_ad.trazas import (bfs_traza, defensa_traza, dijkstra_traza,
                             layout_radial, subgrafo_objetivo)


def construir(nodos, aristas):
    g = Grafo()
    for nid, etiquetas in nodos:
        g.agregar_nodo(Nodo(id=nid, etiquetas=tuple(etiquetas),
                            propiedades={"name": nid}))
    for i, (o, d, t) in enumerate(aristas):
        g.agregar_arista(Arista(id=str(i), origen=o, destino=d, tipo=t))
    return g


def indices(g):
    return {nid: i for i, nid in enumerate(g.nodos)}


class PruebaTrazaBusqueda(unittest.TestCase):
    def setUp(self):
        self.g = construir(
            [("a", []), ("b", []), ("c", []), ("t", [])],
            [("a", "b", "MEMBER_OF"), ("b", "t", "MEMBER_OF"),
             ("a", "c", "HAS_SESSION"), ("c", "t", "MEMBER_OF")],
        )
        self.idx = indices(self.g)
        self.perm = subgrafo_objetivo(self.g, "t")

    def test_bfs_encuentra_camino_y_registra_pasos(self):
        tr = bfs_traza(self.g, self.idx, self.perm, "a", "t")
        self.assertTrue(tr["encontrado"])
        self.assertEqual(tr["saltos"], 2)
        self.assertTrue(len(tr["pasos"]) >= 1)

    def test_dijkstra_usa_pesos_para_elegir_camino(self):
        # La ruta por b (dos MEMBER_OF, peso 2) vence a la ruta por c
        # (HAS_SESSION peso 4 mas MEMBER_OF peso 1).
        tr = dijkstra_traza(self.g, self.idx, self.perm, "a", "t")
        self.assertEqual(tr["peso"], 2)
        tipos = [a[2] for a in tr["camino"]]
        self.assertEqual(tipos, ["MEMBER_OF", "MEMBER_OF"])

    def test_dijkstra_respeta_pesos_personalizados(self):
        # Si MEMBER_OF se encarece, puede cambiar el camino de menor esfuerzo.
        caro = {"MEMBER_OF": 10}
        tr = dijkstra_traza(self.g, self.idx, self.perm, "a", "t", caro)
        self.assertTrue(tr["encontrado"])


class PruebaTrazaDefensa(unittest.TestCase):
    def test_corte_minimo_en_un_cuello_de_botella(self):
        g = construir(
            [("u1", []), ("u2", []), ("m", []), ("t", [])],
            [("u1", "m", "MEMBER_OF"), ("u2", "m", "MEMBER_OF"),
             ("m", "t", "MEMBER_OF")],
        )
        idx = indices(g)
        perm = subgrafo_objetivo(g, "t")
        tr = defensa_traza(g, idx, perm, "t", ["u1", "u2"], TIPOS_ESTRUCTURALES)
        self.assertEqual(tr["flujo"], 1)
        self.assertEqual(len(tr["corte"]), 1)
        self.assertEqual(tr["despues"], 0)
        self.assertEqual(len(tr["caminos"]), 1)

    def test_accesos_estructurales_no_entran_al_corte(self):
        g = construir([("u", []), ("t", [])], [("u", "t", "CONTAINS")])
        idx = indices(g)
        perm = subgrafo_objetivo(g, "t")
        tr = defensa_traza(g, idx, perm, "t", ["u"], TIPOS_ESTRUCTURALES)
        self.assertEqual(tr["corte"], [])
        self.assertEqual(tr["flujo"], 0)


class PruebaLayout(unittest.TestCase):
    def test_todas_las_posiciones_existen(self):
        g = construir(
            [("a", []), ("b", []), ("t", [])],
            [("a", "b", "X"), ("b", "t", "X")],
        )
        perm = subgrafo_objetivo(g, "t")
        pos = layout_radial(g, "t", perm)
        for nid in perm:
            self.assertIn(nid, pos)
        # El objetivo queda en el centro.
        self.assertEqual(pos["t"], (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
