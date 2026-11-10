"""Pruebas del visor offline y de la pagina compartida con la aplicacion web.

El visor reutiliza la pagina de la aplicacion web e incrusta un backend en
JavaScript. Estas pruebas verifican el ensamblado: que el servidor entregue la
pagina sin backend local, que el visor lo incruste con los datos y que ningun
nombre del grafo pueda cerrar antes de tiempo un bloque de script.
"""

import json
import re
import unittest

from grafo_ad.interfaz_web import PAGINA, pagina
from grafo_ad.modelo import Arista, Grafo, Nodo
from grafo_ad.visor import _datos_compactos, generar_visor


def construir(nodos, aristas):
    g = Grafo()
    for nid, etiquetas, nombre in nodos:
        g.agregar_nodo(Nodo(id=nid, etiquetas=tuple(etiquetas), propiedades={"name": nombre}))
    for i, (o, d, t) in enumerate(aristas):
        g.agregar_arista(Arista(id=str(i), origen=o, destino=d, tipo=t))
    return g


def bloques_script(html):
    return re.findall(r"<script>\n(.*?)\n</script>", html, re.S)


class PruebaPaginaCompartida(unittest.TestCase):
    def test_servidor_entrega_la_pagina_sin_backend_local(self):
        self.assertNotIn("__BACKEND_LOCAL__", PAGINA)
        self.assertNotIn("window.backendLocal = function", PAGINA)
        self.assertEqual(len(bloques_script(PAGINA)), 1)

    def test_fuente_de_titulos_incrustada(self):
        # "AAEAAA" es la firma TrueType 00 01 00 00 codificada en base64.
        self.assertIn('font-family: "Bebas Neue"', PAGINA)
        self.assertIn("data:font/ttf;base64,AAEAAA", PAGINA)

    def test_cada_icono_usado_esta_definido(self):
        usados = set(re.findall(r'href="#ic-([a-z]+)"', PAGINA))
        definidos = set(re.findall(r'<symbol id="ic-([a-z]+)"', PAGINA))
        self.assertTrue(usados)
        self.assertEqual(usados - definidos, set())
        self.assertIn("logo", definidos)

    def test_pagina_incrusta_el_script_local_antes_del_principal(self):
        html = pagina("window.backendLocal = function () {};")
        bloques = bloques_script(html)
        self.assertEqual(len(bloques), 2)
        self.assertIn("window.backendLocal = function", bloques[0])
        self.assertIn("function api(path)", bloques[1])


class PruebaVisor(unittest.TestCase):
    def setUp(self):
        # La "b" es de alto valor; "c" lleva un nombre que intenta cerrar el script.
        self.g = construir(
            [("b", ("Group", "HighValue"), "ADMINS@X"),
             ("a", ("User",), "ana@X"),
             ("c", ("User",), "</script><b>x</b>@X")],
            [("a", "b", "MEMBER_OF"), ("c", "a", "HAS_SESSION")],
        )

    def test_visor_incrusta_backend_y_datos(self):
        html = generar_visor(self.g)
        self.assertNotIn("/*__DATOS__*/", html)
        self.assertNotIn("__BACKEND_LOCAL__", html)
        bloques = bloques_script(html)
        self.assertEqual(len(bloques), 2)
        self.assertIn("window.backendLocal = function", bloques[0])

    def test_nombre_con_cierre_de_script_no_rompe_el_html(self):
        html = generar_visor(self.g)
        self.assertEqual(html.count("</script>"), 2)
        self.assertIn("<\\/script>", html)

    def test_datos_compactos_conservan_el_grafo(self):
        datos = _datos_compactos(self.g)
        # La serializacion con "</" escapado se lee igual que la original.
        crudo = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
        self.assertEqual(json.loads(crudo), datos)
        self.assertEqual(len(datos["nodos"]), 3)
        self.assertEqual(datos["objetivos"], [[0, "ADMINS@X"]])
        self.assertEqual(datos["estructurales"], ["CONTAINS", "GP_LINK"])
        # El rango ordena los identificadores: a < b < c.
        ids = list(self.g.nodos)
        self.assertEqual([ids[i] for i in sorted(range(3), key=lambda i: datos["rango"][i])],
                         ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
