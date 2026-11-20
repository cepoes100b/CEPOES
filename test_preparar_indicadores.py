import copy
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from deploy import preparar_indicadores as mod

ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / "datos.json"
JS = """C.set('data-date',C.dateLabel(D.generado)+' · '+C.source);
if(id==='ipc'){ delta(I.var_m[n],I.var_m[n-1]); }"""


def html_fixture(slug):
    data = {"@type": "Dataset", "isBasedOn": "https://example.org/fuente",
            "distribution": {"contentUrl": f"https://cepoes.org/observatorio/{slug}/datos.csv"},
            "temporalCoverage": "Original/Original"}
    return ('<script type="application/ld+json">' + json.dumps(data) +
            '</script><script src="/assets/indicator.js?v=2211"></script><p>Metodología original</p>' +
            "".join('<b id="' + key + '">anterior</b>' for key in (
                "data-date", "indicator-primary-value", "indicator-primary-period",
                "indicator-secondary-value", "indicator-secondary-note", "indicator-reading",
                "indicator-meta-first", "indicator-meta-period")) +
            '<a id="indicator-download" href="https://example.org/old">Descargar</a>' +
            '<table id="indicator-table"><thead><tr><th scope="col">Período</th></tr></thead>' +
            '<tbody><tr><td>anterior</td></tr></tbody></table>')


class PreparationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.site = Path(temp.name)
        self.data = json.loads(CANONICAL.read_bytes())
        self.backup = copy.deepcopy(self.data)
        self.backup["generado"] = "2020-01-01"
        self.backup["censo"] = {"conservar": [1, 2]}
        self.write(mod.RUNTIME, JS)
        for key, (slug, fields, _) in mod.SPECS.items():
            series = mod.rows(self.data, key)
            # El respaldo de Industria y otros módulos no se usa para regenerar.
            # Para IPC se conserva el último mes porque también aloja divisiones.
            removed = 0 if key == "ipcba" else 1
            if removed:
                for field in fields:
                    self.backup[key][field].pop()
            self.write(f"observatorio/{slug}/index.html", html_fixture(slug))
            self.write(f"observatorio/{slug}/datos.csv", mod.export_csv(
                series[:-removed] if removed else series, key))
        self.write(mod.BACKUP, json.dumps(self.backup))

    def write(self, rel, data):
        path = self.site / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())

    def files(self):
        return {p: p.read_bytes() for p in self.site.rglob("*") if p.is_file()}

    def test_preserves_non_target_blocks_and_regenerates_all_rows(self):
        mod.prepare(self.site, CANONICAL)
        fallback = json.loads((self.site / mod.BACKUP).read_bytes())
        self.assertEqual(fallback.pop(mod.PROVENANCE), {k: self.data["generado"] for k in mod.SPECS})
        self.assertEqual({k: v for k, v in fallback.items() if k not in mod.SPECS},
                         {k: v for k, v in self.backup.items() if k not in mod.SPECS})
        for key, (slug, _, cols) in mod.SPECS.items():
            with self.subTest(key=key):
                directory = self.site / "observatorio" / slug
                source = (directory / "index.html").read_text()
                raw = (directory / "datos.csv").read_bytes()
                self.assertTrue(raw.startswith(b'\xef\xbb\xbf"periodo";"'))
                csv_rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";"))
                expected = mod.rows(self.data, key)
                self.assertEqual(csv_rows[0], ["periodo", *cols])
                self.assertEqual([(p, *map(float, v)) for p, *v in csv_rows[1:]],
                                 [row[:1 + len(cols)] for row in expected])
                self.assertEqual(source.count("<tr><td>"), len(expected))
                self.assertIn('<th scope="col">Período</th>', source)
                self.assertIn('id="indicator-download" href="datos.csv"', source)
                self.assertIn('Metodología original', source)
                self.assertIn('"isBasedOn": "https://example.org/fuente"', source)
                self.assertIn('v=' + mod.hashlib.sha256((self.site / mod.RUNTIME).read_bytes()).hexdigest()[:12],
                              source)
        self.assertIn("D.respaldo_generado_por_bloque", (self.site / mod.RUNTIME).read_text())
        self.assertIn("delta(I.var_ia[n],I.var_ia[n-1])", (self.site / mod.RUNTIME).read_text())
        before = self.files()
        mod.prepare(self.site, CANONICAL)
        self.assertEqual(self.files(), before)

    def test_preflight_leaves_site_intact_on_invalid_or_stale_source(self):
        for reason in ("truncado", "nan", "desorden", "sin subocupacion", "retroceso fecha"):
            modified = copy.deepcopy(self.data)
            e = modified["empleo"]
            if reason == "truncado":
                for k in mod.SPECS["empleo"][1]:
                    e[k] = e[k][1:]
            elif reason == "nan":
                e["empleo"][-1] = float("nan")
            elif reason == "desorden":
                e["trimestres"][-1] = e["trimestres"][-2]
            elif reason == "sin subocupacion":
                del e["subocupacion"]
            else:
                modified["generado"] = "2019-12-31"
            path = self.site / "input.json"
            path.write_text(json.dumps(modified))
            before = self.files()
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                mod.prepare(self.site, path)
            self.assertEqual(self.files(), before)

    def test_older_source_cannot_omit_csv_only_history(self):
        _, _, cols = mod.SPECS["pobreza"]
        self.write("observatorio/condiciones-de-vida/pobreza/datos.csv",
                   ";".join(("periodo", *cols)) + "\n1900-T1;1;2")
        before = self.files()
        with self.assertRaisesRegex(ValueError, "CSV anterior incompatible"):
            mod.prepare(self.site, CANONICAL)
        self.assertEqual(self.files(), before)

    def test_layout_mismatch_preserves_full_candidate(self):
        self.write("observatorio/condiciones-de-vida/pobreza/index.html", "<html>puerta de login</html>")
        before = self.files()
        with self.assertRaisesRegex(ValueError, "elemento completo"):
            mod.prepare(self.site, CANONICAL)
        self.assertEqual(self.files(), before)

    def test_ipc_compares_interannual_not_monthly_rates(self):
        readings, _ = mod.presentation([("Sep-26", 1.8, 32.9), ("Oct-26", 1.9, 32.5)], "ipcba")
        self.assertEqual(readings["indicator-reading"],
                         "La inflación interanual se ubica en 32,5%. Respecto del período anterior, disminuyó 0,4 p.p.")
