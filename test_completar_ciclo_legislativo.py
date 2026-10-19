"""Regresiones offline: evidencia de hito y detalle tienen contratos distintos."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import completar_ciclo_legislativo as ciclo
import verificar_ciclo_legislativo as verificador


class DictamenTest(unittest.TestCase):
    def setUp(self):
        self.event = {"fecha": "2026-10-19", "tipo": "Dictámen", "subtipo": "UNICO DE COMISION", "documento_url": None}
        self.movement = {"fecha": "2026-10-19", "oficina": "COMISION OFICIAL", "descripcion": "DICTAMEN FIRMADO"}
        self.ficha = {"dictamenes": [], "eventos_documentales": [self.event], "movimientos": []}

    def test_evento_sin_grilla_ni_movimiento_conserva_hito_y_valida(self):
        # 2947-D-2026: el último movimiento es EN COMISION, anterior al evento.
        movement = {"fecha": "2026-09-24", "oficina": "COMISION PREVIA", "descripcion": "EN COMISION"}
        self.ficha.update(movimientos=[movement], ultimo_movimiento=movement,
                          expediente_id=142552, tipo_proyecto="Declaración", fecha_inicio="2026-09-01",
                          estado_actual="en_comision", etapa="en_comision")
        url = "https://parlamentaria.legislatura.gob.ar/pages/expediente.aspx?id=142552"
        project = {"numero": "2947-D-2026", "url_expediente": url, "ficha_oficial": self.ficha,
                   "estado_actual": "en_comision", "etapa": "en_comision"}
        original = copy.deepcopy(self.ficha)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legislatura_publica.json"
            complete = copy.deepcopy(project)
            complete["numero"] = "CASO-COMPLETO"
            complete["ficha_oficial"]["dictamenes"] = [
                {"fecha": "2026-10-19", "tipo": "UNICO", "comision": "COMISION OFICIAL"}]
            summary = {"expedientes_enriquecidos": 2, "expedientes_sancionados": 0,
                       "estados_actuales": {"en_comision": 2}, "etapas_legislativas": {"en_comision": 2}}
            path.write_text(json.dumps({"version": 5, "expedientes": [project, complete], "resumen": summary}))
            with patch.object(ciclo, "DATA_PATH", path), patch.object(verificador, "DATA_PATH", path):
                self.assertEqual(ciclo.main(), 0)
                result = json.loads(path.read_text())["expedientes"][0]["ficha_oficial"]
                self.assertEqual(result["dictamenes"], [])
                self.assertEqual(result["eventos_documentales"], original["eventos_documentales"])
                self.assertEqual(result["movimientos"], original["movimientos"])
                self.assertTrue(result["hitos"]["tuvo_dictamen"])
                self.assertTrue(result["evidencia_dictamen"])
                self.assertEqual(result["etapa_ciclo"], "con_dictamen")
                self.assertEqual(verificador.main(), 0)
                # El validador sigue rechazando exactamente el defecto original.
                data = json.loads(path.read_text())
                data["expedientes"][0]["ficha_oficial"]["dictamenes"] = [dict(fecha="2026-10-19", tipo="UNICO DE COMISION", comision=None)]
                path.write_text(json.dumps(data))
                self.assertEqual(verificador.main(), 1)

    def test_evento_y_movimiento_completos(self):
        self.ficha["movimientos"] = [self.movement]
        detail, = ciclo.fallback_dictamenes(self.ficha)
        self.assertEqual((detail["fecha"], detail["tipo"], detail["comision"]),
                         ("2026-10-19", "UNICO DE COMISION", "COMISION OFICIAL"))
        self.assertEqual(detail["fuente"], "evento_documental_y_movimiento_oficial")

    def test_grilla_oficial_se_preserva(self):
        self.ficha["dictamenes"] = [{"fecha": "2026-10-19", "tipo": "UNICO", "comision": "COMISION OFICIAL"}]
        self.assertIs(ciclo.fallback_dictamenes(self.ficha), self.ficha["dictamenes"])

    def test_movimiento_completo_sin_evento(self):
        self.ficha.update(eventos_documentales=[], movimientos=[self.movement])
        detail, = ciclo.fallback_dictamenes(self.ficha)
        self.assertEqual(detail["comision"], "COMISION OFICIAL")
        self.assertEqual(detail["fuente"], "movimiento_oficial")

    def test_campos_incompletos_no_generan_detalle(self):
        for field in ("fecha", "oficina"):
            for value in (None, "", "   "):
                with self.subTest(field=field, value=value):
                    movement = dict(self.movement, **{field: value})
                    ficha = {"movimientos": [movement]}
                    self.assertEqual(ciclo.fallback_dictamenes(ficha), [])
                    self.assertTrue(ciclo.strict_dictamen_evidence(ficha))
        self.event["fecha"] = None
        self.assertEqual(ciclo.fallback_dictamenes(self.ficha), [])

    def test_notas_libres_no_clasifican_hito(self):
        ficha = {"eventos_documentales": [{"tipo": "Proyecto", "notas": "dictamen"}]}
        self.assertEqual(ciclo.fallback_dictamenes(ficha), [])
        self.assertFalse(ciclo.strict_dictamen_evidence(ficha))


if __name__ == "__main__":
    unittest.main()
