"""Pruebas de integracion contra el conjunto de datos real.

Anclan los resultados del analizador a cifras conocidas del entorno de ejemplo,
incluida la validacion frente a la guia original: el usuario de referencia
alcanza exactamente cuatro objetos de alto valor.
"""

import os
import unittest

from grafo_ad.modelo import cargar_json, OBJECTID_DOMAIN_ADMINS
from grafo_ad.consultas import alto_valor_alcanzable, una_ruta_de_acceso
from grafo_ad.cortes import plan_de_defensa
from grafo_ad.riesgo import exposicion, exposicion_tras_corte

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "data", "cybersecurity-json-data.json")
USUARIO = "PiedadFlatley255@TestCompany.Local"


@unittest.skipUnless(os.path.exists(DATOS), "Falta el archivo de datos del grafo")
class PruebaDatosReales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = cargar_json(DATOS)

    def test_tamanio_del_grafo(self):
        self.assertEqual(len(self.g), 953)
        self.assertEqual(len(self.g.aristas), 4698)
        self.assertEqual(len(self.g.altos_valores()), 6)

    def test_usuario_ejemplo_alcanza_cuatro_altos_valores(self):
        # Coincide con el resultado que reporta la guia del ejemplo original.
        alcanzables = alto_valor_alcanzable(self.g, USUARIO)
        self.assertEqual(len(alcanzables), 4)

    def test_ruta_a_enterprise_domain_controllers(self):
        ruta = una_ruta_de_acceso(self.g, USUARIO, "TestCompany.Local-S-1-5-9")
        self.assertIsNotNone(ruta)
        self.assertTrue(any("ENTERPRISE DOMAIN CONTROLLERS" in paso for paso in ruta))

    def test_defensa_aisla_domain_admins(self):
        objetivo = self.g.buscar_por_objectid(OBJECTID_DOMAIN_ADMINS)
        fuentes = [n.id for n in self.g.por_tipo("User")]
        plan = plan_de_defensa(self.g, fuentes, [objetivo.id])
        self.assertTrue(plan["verificado"])
        self.assertGreater(plan["tamanio_corte"], 0)

        cortados = {(a["origen"], a["destino"], a["tipo"])
                    for a in plan["accesos_a_revocar"]}
        antes = exposicion(self.g, [objetivo.id], fuentes)
        despues = exposicion_tras_corte(self.g, [objetivo.id], cortados, fuentes)
        self.assertGreater(antes["fuentes_expuestas"], 0)
        self.assertEqual(despues["fuentes_expuestas"], 0)


if __name__ == "__main__":
    unittest.main()
