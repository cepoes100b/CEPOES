"""Regresiones de formato oficial con datos sintéticos, sin descargas."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from bs4 import BeautifulSoup

import actualizar_estructura_legislativa as parser


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


if __name__ == "__main__":
    unittest.main()
