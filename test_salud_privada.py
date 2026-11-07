"""Regresión del adaptador BA Data de centros de salud privados."""
import unittest
import generar_oferta_ampliada as E

class SaludPrivadaTest(unittest.TestCase):
    def setUp(self):
        self.cfg = next(c for c in E.LAYERS if c["id"] == "salud-privada")
        self.official, self.barrios = E.official_territory()

    def item(self, row):
        return E.normalized_item(row, self.cfg, self.official, self.barrios, 1)

    def test_esquema_oficial_y_clave_estable(self):
        row = {"nombre": "Centro", "calle": "SOLER", "altura": 3945,
               "telefonos": "4821-1200", "lat": -34.59162999, "long": -58.41733346}
        item = self.item(row)
        self.assertEqual(item["direccion"], "SOLER 3945")
        self.assertEqual(item["telefono"], "4821-1200")
        self.assertEqual(item["coord"], [-58.417333, -34.59163])
        self.assertEqual(item["id"], "salud-privada-centro")

    def test_prioridad_direccion_y_ausencia_sin_inventar(self):
        self.assertEqual(self.item({"nombre": "Centro", "direccion": "Original 1",
            "calle": "Otra", "altura": 2})["direccion"], "Original 1")
        item = self.item({"nombre": "Centro"})
        self.assertEqual(item["direccion"], "")
        self.assertEqual(item["telefono"], "")
        self.assertIsNone(item["coord"])

    def test_fuente_preserva_universo_y_campos_disponibles(self):
        rows = E.read_source("salud_privada")
        self.assertTrue(rows)
        for row in rows:
            item = self.item(row)
            if row.get("calle"):
                self.assertTrue(item["direccion"])
            if row.get("telefonos"):
                self.assertTrue(item["telefono"])
            if row.get("lat") and row.get("long"):
                self.assertIsNotNone(item["coord"])

if __name__ == "__main__":
    unittest.main()
