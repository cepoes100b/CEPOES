"""Regresiones de formato oficial con datos sintéticos, sin descargas."""
import contextlib
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup

import actualizar_estructura_legislativa as parser
import actualizar_legislatura as monitor
from verificar_estructura_legislativa import public_structure_status, validate_structure

ROOT = Path(__file__).resolve().parent


def table(header="Diputado/a", count=15, president=True):
    headings = ["", header, "Bloque", "Cargo", "Integrante desde"]
    rows = [["", f"Persona {i}", "Bloque de prueba",
             "Presidente" if i == 0 and president else "Vocal", "01/03/2026"]
            for i in range(count)]
    return headings, rows


def html(headings, rows):
    def row(cells, tag):
        return "<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>"
    return '<table id="data-integrantes">' + row(headings, "th") + "".join(
        row(cells, "td") for cells in rows) + "</table>"


class MemberTableTests(unittest.TestCase):
    def parse(self, headings, rows):
        return parser.parse_member_table(BeautifulSoup(html(headings, rows), "html.parser"))

    def commission(self, headings, rows):
        with patch.object(parser, "request", return_value=SimpleNamespace(text=html(headings, rows))):
            return parser.parse_commission(None, "Asuntos Constitucionales", "asuntosconstitucionales", 15, True)

    def test_old_and_current_headers_preserve_values_and_empty_image_column(self):
        for header in ("Diputado", "Diputado/a"):
            with self.subTest(header=header):
                result = self.commission(*table(header))
                self.assertEqual(len(result["integrantes"]), 15)
                self.assertEqual(result["integrantes"][0], {
                    "nombre": "Persona 0", "bloque": "Bloque de prueba",
                    "cargo": "Presidente", "integrante_desde": "01/03/2026"})
                self.assertEqual(result["autoridades"], [result["integrantes"][0]])

    def test_reordered_columns_are_resolved_by_header(self):
        headings, rows = table()
        order = [3, 0, 4, 2, 1]
        self.assertEqual(self.parse(headings, rows), self.parse(
            [headings[i] for i in order], [[r[i] for i in order] for r in rows]))

    def test_optional_date_column_remains_optional(self):
        headings, rows = table()
        self.assertIsNone(self.parse(headings[:-1], [r[:-1] for r in rows])[0]["integrante_desde"])

    def test_unknown_header_does_not_match_by_substring(self):
        for header in ("Exdiputado", "Diputados", "Diputado/a suplente", "Nombre", ""):
            with self.subTest(header=header), self.assertRaisesRegex(RuntimeError, "encontré 0"):
                self.commission(*table(header))

    def test_required_columns_cannot_be_omitted(self):
        for column in (1, 2, 3):
            headings, rows = table()
            del headings[column]
            for row in rows:
                del row[column]
            with self.subTest(column=column), self.assertRaisesRegex(RuntimeError, "encontré 0"):
                self.commission(headings, rows)

    def test_member_count_remains_exact(self):
        for count in (0, 14, 16):
            with self.subTest(count=count), self.assertRaisesRegex(RuntimeError, f"esperaba 15 integrantes y encontré {count}"):
                self.commission(*table(count=count))

    def test_presidency_remains_required(self):
        with self.assertRaisesRegex(RuntimeError, "no se identificó presidencia"):
            self.commission(*table(president=False))

    def test_short_rows_do_not_shift_columns(self):
        headings, rows = table()
        rows[-1] = rows[-1][:3]
        with self.assertRaisesRegex(RuntimeError, "encontré 14"):
            self.commission(headings, rows)

    def test_missing_name_or_block_rejects_incomplete_composition(self):
        for column in (1, 2):
            headings, rows = table()
            rows[-1][column] = ""
            with self.subTest(column=column), self.assertRaisesRegex(RuntimeError, "encontré 14"):
                self.commission(headings, rows)

    def test_repeated_header_is_not_a_member(self):
        for header in ("Diputado", "Diputado/a"):
            headings, rows = table(header)
            rows.insert(5, headings)
            with self.subTest(header=header):
                self.assertEqual(len(self.commission(headings, rows)["integrantes"]), 15)


class LegislativeRefreshTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        self.output = self.root / "estructura_legislativa.json"
        self.state = self.root / "estado_legislatura.json"
        self.legislature = self.root / "legislatura_publica.json"
        self.summary = self.root / "step-summary.md"
        official = json.loads((ROOT / "estructura_legislativa.json").read_text(encoding="utf-8"))
        self.previous = {k: copy.deepcopy(v) for k, v in official.items() if k != "control_actualizacion"}
        self.previous["actualizado_en"] = "2026-01-01T15:10:00-03:00"
        self.commissions = copy.deepcopy(self.previous["comisiones"])
        self.output.write_text(json.dumps(self.previous, ensure_ascii=False), encoding="utf-8")
        self.agenda_id = 4852
        self.seen = []
        self.block_count = 20

    def commission(self, slug):
        return next(c for c in self.commissions if c["slug"] == slug)

    def remove_known_member(self, slug):
        members = self.commission(slug)["integrantes"]
        index = next(i for i, m in enumerate(members)
                     if parser.person_key(m["nombre"]) == parser.person_key("Noemí Geminiani"))
        return members.pop(index)

    def missing_health_member(self):
        return self.remove_known_member("salud")

    def missing_four(self):
        removals = {slug: self.remove_known_member(slug) for slug in (
            "salud", "ninezadolescenciayjuventud", "turismoydeportes", "personasmayores"
        )}
        self.block_count = 19
        return removals

    def live_response(self, url, **_opts):
        self.seen.append(url)
        if url == parser.BLOCK_URL:
            counter = f"<p>Integrantes {self.block_count}</p>" if self.block_count is not None else ""
            document = "<h1>Fuerza por Buenos Aires</h1>" + counter
        else:
            commission = self.commission(url.rsplit("/", 1)[-1])
            documents = [
                ["", m["nombre"], m["bloque"], m["cargo"], m["integrante_desde"] or ""]
                for m in commission["integrantes"]
            ]
            documents.extend(commission.get("incomplete_rows", []))
            document = "<h1>" + commission["nombre_fuente"] + "</h1>" + html(table()[0], documents)
        return SimpleNamespace(text=document + " " * 1000, raise_for_status=lambda: None)

    def run_structure(self):
        stream = io.StringIO()
        with (patch.object(parser.requests.Session, "get", side_effect=self.live_response),
              patch.object(parser, "OUT", self.output),
              patch.dict(parser.os.environ, {"GITHUB_STEP_SUMMARY": str(self.summary)}),
              contextlib.redirect_stdout(stream)):
            parser.main()
        return stream.getvalue()

    def run_monitor(self):
        import datetime as dt
        today = dt.date.today().isoformat()
        meeting = {
            "id": "reunion-de-prueba", "agenda_id": self.agenda_id, "fecha": today,
            "url": "https://www.legislatura.gob.ar/AgendaLCABADetalle/4852/30847",
            "comision": "Salud", "tipo": "Reunión de Diputados",
            "tipo_reunion": "diputados", "expedientes_anunciados": 0,
        }
        day = {"agenda_id": self.agenda_id, "fecha": today, "reuniones": 0,
               "url": "https://www.legislatura.gob.ar/AgendaLCABA/4852"}
        response = lambda agenda_id: (day.copy(), [meeting]) if agenda_id == self.agenda_id else (None, [])
        with (patch.object(monitor, "OUT", self.legislature),
              patch.object(monitor, "STATE", self.state),
              patch.object(monitor, "STRUCTURE", self.output),
              patch.object(monitor, "discover_anchor_ids", return_value={self.agenda_id}),
              patch.object(monitor, "parse_agenda_page", side_effect=response),
              patch.object(monitor, "parse_detail", return_value=(meeting, [])),
              patch.object(monitor.time, "sleep"),
              contextlib.redirect_stdout(io.StringIO())):
            self.assertEqual(monitor.main(), 0)
        return json.loads(self.legislature.read_text(encoding="utf-8"))

    def staged_site(self, data):
        import shutil
        site = self.root / "site"
        (site / "legislatura").mkdir(parents=True, exist_ok=True)
        (site / "assets").mkdir(exist_ok=True)
        page = site / "legislatura" / "index.html"
        if not page.exists():
            page.write_text("<html><head></head><body><main><h1>Monitor legislativo</h1></main></body></html>",
                            encoding="utf-8")
        shutil.copyfile(ROOT / "deploy/site-overlay/assets/legislatura-public-bridge.js",
                        site / "assets/legislatura-public-bridge.js")
        # Reutilizar el preparador real y sus mínimos de publicación, con universo sintético.
        prep = self.root / "deploy" / "preparar_legislatura_publica.py"
        prep.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / "deploy/preparar_legislatura_publica.py", prep)
        rows = [{"numero": "832-D-2026" if i == 0 else f"{i}-D-2026",
                 "autores": ["Negri, Claudia"] if i < 200 else ["Otra persona"]}
                for i in range(1000)]
        data["universo_consolidado"] = {"total": len(rows), "expedientes": rows}
        data["resumen"]["universo_consolidado_claudia"] = 200
        self.legislature.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        (self.root / "sesiones_publicas.json").write_text("{}", encoding="utf-8")
        subprocess.run([sys.executable, str(prep), str(site)], check=True, capture_output=True)
        subprocess.run([sys.executable, str(ROOT / "deploy/preparar_puente_legislatura.py"), str(site)],
                       check=True, capture_output=True)
        status_builder = self.root / "generar_estado_datos.py"
        shutil.copyfile(ROOT / status_builder.name, status_builder)
        for f in ("equipamientos/resumen-territorial.json", "territorio.json", "presupuesto.json",
                  "deploy/site-overlay/assets/data/salud-mental.json", "deploy/site-overlay/assets/data/migraciones.json"):
            path = self.root / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"total_registros": 0}', encoding="utf-8")
        subprocess.run([sys.executable, str(status_builder), str(site)], check=True, capture_output=True)
        return site, page

    def test_known_mismatch_retains_validated_data_reaches_public_monitor_and_recovers(self):
        removed = self.missing_four()
        # Misma persona/rol/bloque con orden, acentos y mayúsculas distintos.
        health_president = self.commission("salud")["integrantes"][0]
        health_president["nombre"] = "JUAN FACUNDO DEL GAISO"
        health_president["cargo"] = "  PRESIDENTE  "
        log = self.run_structure()
        self.assertIn("::warning::", log)
        self.assertIn("14 de 15", self.summary.read_text(encoding="utf-8"))
        self.assertEqual(len(set(self.seen)), 28)
        retained = json.loads(self.output.read_text(encoding="utf-8"))
        validate_structure(retained)
        degraded = public_structure_status(retained)
        self.assertEqual(degraded["ultimo_validado_en"], self.previous["actualizado_en"])
        self.assertNotEqual(degraded["intentado_en"], degraded["ultimo_validado_en"])
        self.assertEqual({c["slug"]: (c["integrantes_observados"], c["integrantes_normativos"])
                          for c in degraded["comisiones"]},
                         {"salud": (14, 15), "ninezadolescenciayjuventud": (12, 13),
                          "turismoydeportes": (8, 9), "personasmayores": (10, 11)})
        self.assertEqual(degraded["bloque_fuerza_por_buenos_aires"]["integrantes_observados"], 19)
        self.assertEqual({k: v for k, v in retained.items() if k != "control_actualizacion"}, self.previous)

        live = self.run_monitor()
        self.assertNotEqual(live["generado"], retained["actualizado_en"])
        self.assertEqual(live["reuniones"][0]["id"], "reunion-de-prueba")
        self.assertEqual(live["estado_estructura_institucional"], degraded)
        site, page = self.staged_site(live)
        public = json.loads((site / "legislatura_publica.json").read_text(encoding="utf-8"))
        self.assertEqual(len(public["expedientes"]), 1000)
        self.assertEqual(public["reuniones"][0]["id"], "reunion-de-prueba")
        self.assertEqual(public["estado_estructura_institucional"], degraded)
        notice = page.read_text(encoding="utf-8")
        for label in ("Salud (14 de 15)", "Niñez, Adolescencia y Juventud (12 de 13)",
                      "Turismo y Deportes (8 de 9)", "Personas Mayores (10 de 11)",
                      "informó 19 integrantes", "no acredita cambios formales", "01/01/2026"):
            self.assertIn(label, notice)
        self.assertNotIn("Geminiani", notice)
        self.assertIn("última validada el 1 de enero de 2026",
                      (site / "datos/estado/index.html").read_text(encoding="utf-8"))

        self.staged_site(live)
        self.assertEqual(page.read_text(encoding="utf-8").count("cepoes-estado-estructura:inicio"), 1)

        for slug, member in removed.items():
            self.commission(slug)["integrantes"].append(member)
        self.block_count = 20
        self.assertNotIn("::warning::", self.run_structure())
        fresh = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertIsNone(public_structure_status(fresh))
        self.assertNotEqual(fresh["actualizado_en"], self.previous["actualizado_en"])
        self.legislature.unlink()  # instalar sólo entradas nuevas del productor, sin universo de publicación
        current = self.run_monitor()
        self.assertNotIn("estado_estructura_institucional", current)
        self.staged_site(current)
        self.assertNotIn("cepoes-estado-estructura:inicio", page.read_text(encoding="utf-8"))
        self.assertNotIn("Estructura institucional con actualización parcial",
                         (site / "datos/estado/index.html").read_text(encoding="utf-8"))

    def assert_hard_failure(self, message):
        before = self.output.read_bytes() if self.output.exists() else None
        with self.assertRaisesRegex((RuntimeError, AssertionError, OSError, ValueError), message):
            self.run_structure()
        self.assertEqual(self.output.read_bytes() if self.output.exists() else None, before)
        self.assertFalse(self.summary.exists())

    def test_subset_with_recovered_commission_and_matching_block_is_allowed(self):
        removed = self.missing_four()
        self.commission("salud")["integrantes"].append(removed["salud"])
        self.block_count = 20
        self.assertIn("::warning::", self.run_structure())
        retained = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(retained["actualizado_en"], self.previous["actualizado_en"])
        self.assertEqual(len(public_structure_status(retained)["comisiones"]), 3)
        self.assertEqual(public_structure_status(retained)["bloque_fuerza_por_buenos_aires"]["integrantes_observados"], 20)

    def test_later_unrelated_roster_error_still_stops_and_does_not_certify_a_partial_run(self):
        self.missing_health_member()
        self.commission("ambiente")["integrantes"].pop()
        self.assert_hard_failure("Ambiente: esperaba 11 integrantes y encontré 10")

    def test_unrelated_member_absent_from_one_of_four_commissions_is_a_hard_failure(self):
        members = self.commission("personasmayores")["integrantes"]
        members.pop(next(i for i, m in enumerate(members) if parser.norm(m["cargo"]) == "vocal"))
        self.assert_hard_failure("Personas Mayores: los integrantes observados no coinciden con la omisión verificada")

    def test_same_block_count_with_an_unrelated_replacement_is_a_hard_failure(self):
        self.missing_four()
        whom = next(person["nombre"] for person in self.previous["bloques"]["fuerza_por_buenos_aires"]["integrantes"]
                    if not any(x in parser.norm(person["nombre"]) for x in ("claudia", "geminiani")))
        for c in self.commissions:
            for member in c["integrantes"]:
                if parser.person_key(member["nombre"]) == parser.person_key(whom):
                    member["nombre"] = "Apellido, Nueva persona"
        self.assert_hard_failure("composición observada incompatible.*fuente 19, unión 19, esperado 19")

    def test_incompatible_or_missing_block_counter_is_a_hard_failure(self):
        self.missing_four()
        self.block_count = 20
        self.assert_hard_failure("la página oficial informa 20 integrantes")
        self.block_count = None
        self.assert_hard_failure("no se encontró el contador oficial")

    def test_unknown_health_shape_and_unvalidated_snapshot_are_not_published(self):
        self.missing_health_member()
        self.commission("salud")["incomplete_rows"] = [["", "Fila incompleta"]]
        self.assert_hard_failure("Salud: esperaba 15 integrantes y encontré 14")
        del self.commission("salud")["incomplete_rows"]
        self.output.unlink()
        self.assert_hard_failure("estructura_legislativa.json")

    def test_unexpected_replacement_at_same_count_is_not_the_known_absence(self):
        self.missing_health_member()
        self.commission("salud")["integrantes"][-1]["nombre"] = "Persona no presente en la nómina previa"
        self.assert_hard_failure("no coinciden con la omisión verificada")

    def test_another_missing_member_even_at_same_count_is_a_hard_failure(self):
        members = self.commission("salud")["integrantes"]
        members.pop(next(i for i, m in enumerate(members)
                         if parser.norm(m["cargo"]) == "vocal" and "geminiani" not in parser.norm(m["nombre"])))
        self.assert_hard_failure("no coinciden con la omisión verificada")

    def test_duplicate_members_do_not_qualify_for_degradation(self):
        self.missing_health_member()
        members = self.commission("salud")["integrantes"]
        members[-1] = members[-2]
        self.assert_hard_failure("integrantes duplicados")

    def test_health_source_transport_error_is_not_masked(self):
        live_response = self.live_response

        def timeout(url, **kwargs):
            if url.endswith("/salud"):
                raise parser.requests.exceptions.Timeout("problema de red simulado")
            return live_response(url, **kwargs)

        self.live_response = timeout
        self.assert_hard_failure("no se pudo descargar.*salud.*problema de red")

    def test_health_missing_presidency_is_not_the_known_absence(self):
        self.commission("salud")["integrantes"].pop(0)
        self.assert_hard_failure("no se identificó presidencia")

    def test_institutional_block_count_check_still_runs_after_health_discrepancy(self):
        self.missing_health_member()
        other = self.commission("personasmayores")["integrantes"]
        other[-1]["nombre"] = "Bloque de prueba, Nueva persona"
        other[-1]["bloque"] = "Fuerza por Buenos Aires"
        self.assert_hard_failure("la página oficial informa 20 integrantes")


if __name__ == "__main__":
    unittest.main()
