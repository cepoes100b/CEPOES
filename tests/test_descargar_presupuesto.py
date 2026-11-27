"""Regression for the malformed BA Data budget CSV URL."""
import unittest

from descargar_presupuesto import choose_executed, meta, resource_url


class BudgetResourceURLTests(unittest.TestCase):
    url = (
        "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
        "ministerio-de-economia-y-finanzas/presupuesto-ejecutado-2026/"
        "presupuesto-ejecutado-2026-3.csv"
    )

    def test_published_third_quarter_keeps_its_period_and_download_url(self):
        latest = {
            "name": "Presupuesto Ejecutado 2026 Tercer Trimestre (CSV)",
            "format": "CSV",
            "url": "None" + self.url,
        }
        older = {**latest, "name": "Presupuesto Ejecutado 2026 Segundo Trimestre (CSV)"}
        resource, year, quarter = choose_executed({"resources": [older, latest]})
        self.assertEqual((year, quarter), (2026, 3))
        self.assertEqual(resource_url(resource), self.url)
        self.assertEqual(meta(resource)["url"], self.url)

    def test_preserves_valid_absolute_and_relative_urls(self):
        self.assertEqual(resource_url({"url": self.url}), self.url)
        self.assertEqual(resource_url({"url": "/foo.csv"}), "https://data.buenosaires.gob.ar/foo.csv")

    def test_preserves_official_id_fallback(self):
        self.assertEqual(
            resource_url({"id": "r1"}),
            "https://data.buenosaires.gob.ar/dataset/recurso/resource/r1/download",
        )

    def test_does_not_rewrite_other_hosts(self):
        malformed = "Nonehttps://cdn.buenosaires.gob.ar.example.org/datosabiertos/file.csv"
        self.assertEqual(resource_url({"url": malformed}), malformed)


if __name__ == "__main__":
    unittest.main()
