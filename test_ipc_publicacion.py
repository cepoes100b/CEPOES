"""IPC: identidad de serie, lectura interanual y fallbacks de publicación."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from deploy.preparar_sitio_publico import (
    normalize_html, patch_ipc_indicator, prepare_ipc_publication,
    prepare_public_revalidation,
)

IDS = ('data-date', 'indicator-primary-label', 'indicator-primary-value',
       'indicator-primary-period', 'indicator-secondary-label',
       'indicator-secondary-value', 'indicator-secondary-note',
       'indicator-meta-first', 'indicator-meta-period', 'indicator-reading')
RUNTIME = """function pct(v){return Number(v).toFixed(1).replace('.',',')+'%'}
function delta(a,b){return (a>=b?'aumentó ':'disminuyó ')+Math.abs(a-b).toFixed(1).replace('.',',')+' p.p.'}
function extract(D,id){
  if(id==='ipc'){
    const I=D.ipcba,n=I.meses.length-1;
    return `La inflación interanual se ubica en ${pct(I.var_ia[n])}. ${n?delta(I.var_m[n],I.var_m[n-1]):''}`;
  }
  if(id==='empleo'){return delta(D.empleo[1],D.empleo[0]);}
}
"""
DATA = {'generado': '2026-10-08', 'ipcba': {
    'meses': ['Ago-26', 'Sep-26'], 'var_m': [1.7, 1.8], 'var_ia': [33.3, 32.9]}}


class IpcPublicationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.site = Path(self.directory.name)
        self.page = self.site / 'observatorio/precios/ipc/index.html'
        self.page.parent.mkdir(parents=True)
        metadata = {'@type': 'Dataset', 'temporalCoverage': 'Enero 2024/Junio 2026'}
        source = ('<!doctype html><html><head><title>IPC</title>'
                  '<script src="/assets/indicator.js?v=2211"></script>'
                  '<script type="application/ld+json">' + json.dumps(metadata) + '</script>'
                  '</head><body data-indicator="ipc">'
                  + ''.join(f'<span id="{i}">anterior</span>' for i in IDS)
                  + '<table id="indicator-table"><tbody><tr><td>Viejo</td></tr></tbody></table>'
                  '<p id="editorial">Texto metodológico aprobado</p></body></html>')
        self.page.write_text(source)
        self.runtime = self.site / 'assets/indicator.js'
        self.runtime.parent.mkdir()
        self.runtime.write_text(RUNTIME)

    def build(self, data=None):
        prepare_ipc_publication(self.site, DATA if data is None else data)
        return self.page.read_text()

    def test_annual_reading_opposes_monthly_movement(self):
        html = self.build()
        self.assertIn('32,9%. Respecto del período anterior, disminuyó 0,4 p.p.', html)
        self.assertIn('>+1,8%<', html)
        self.assertNotIn('aumentó 0,1 p.p.', html)

    def test_static_table_csv_metadata_and_period_match(self):
        html = self.build()
        self.assertIn('>Septiembre 2026<', html)
        self.assertIn('Agosto 2026/Septiembre 2026', html)
        self.assertNotIn('>Viejo<', html)
        rows = list(csv.reader(io.StringIO((self.page.parent/'datos.csv').read_text(encoding='utf-8-sig')), delimiter=';'))
        self.assertEqual(rows[1:], [['Ago-26','1.7','33.3'], ['Sep-26','1.8','32.9']])
        self.assertEqual(html.count('<tr>'), 3)

    def test_idempotent_and_no_data_or_editorial_mutation(self):
        original = copy.deepcopy(DATA)
        first = self.build()
        csv_first = (self.page.parent/'datos.csv').read_bytes()
        runtime_first = self.runtime.read_bytes()
        self.assertEqual(first, self.build())
        self.assertEqual(csv_first, (self.page.parent/'datos.csv').read_bytes())
        self.assertEqual(runtime_first, self.runtime.read_bytes())
        self.assertEqual(original, DATA)
        self.assertIn('<p id="editorial">Texto metodológico aprobado</p>', first)

    def test_runtime_only_changes_ipc_comparison(self):
        new = patch_ipc_indicator(RUNTIME)
        self.assertEqual(new, RUNTIME.replace('delta(I.var_m[n],I.var_m[n-1])', 'delta(I.var_ia[n],I.var_ia[n-1])'))
        self.assertEqual(new, patch_ipc_indicator(new))
        self.assertIn("if(id==='empleo'){return delta(D.empleo[1],D.empleo[0]);}", new)

    def test_runtime_execution_and_other_indicator_unchanged(self):
        new = patch_ipc_indicator(RUNTIME)
        program = new + '\nconsole.log(JSON.stringify([extract('+json.dumps(DATA)+',"ipc"),extract({empleo:[51,52]},"empleo")]));'
        result = subprocess.run(['node','-e',program], text=True, capture_output=True, check=True)
        ipc, employment = json.loads(result.stdout)
        self.assertIn('disminuyó 0,4 p.p.', ipc)
        self.assertEqual(employment, 'aumentó 1,0 p.p.')

    def test_increasing_annual_and_decreasing_monthly(self):
        data = copy.deepcopy(DATA)
        data['ipcba'].update(var_m=[2,1], var_ia=[30,31])
        self.assertIn('aumentó 1,0 p.p.', self.build(data))

    def test_one_period_has_no_comparison(self):
        data = copy.deepcopy(DATA)
        data['ipcba'] = {k: v[-1:] for k,v in data['ipcba'].items()}
        self.assertNotIn('Respecto del período anterior', self.build(data))

    def test_invalid_data_preserves_build(self):
        for mutation in ({'var_m':[1]}, {'var_ia':[33.3,float('nan')]}, {'meses':[]}, {'meses':['Ago-26','Septiembre']}):
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(DATA)
                data['ipcba'].update(mutation)
                before = (self.page.read_bytes(), self.runtime.read_bytes())
                with self.assertRaises(ValueError): self.build(data)
                self.assertEqual(before, (self.page.read_bytes(), self.runtime.read_bytes()))
                self.assertFalse((self.page.parent/'datos.csv').exists())

    def test_unknown_runtime_fails_before_any_output(self):
        self.runtime.write_text('unrecognized runtime')
        before = self.page.read_bytes()
        with self.assertRaises(ValueError): self.build()
        self.assertEqual(before, self.page.read_bytes())

    def test_missing_or_duplicate_html_contract_is_rejected(self):
        source = self.page.read_text()
        for changed in (source.replace('id="indicator-reading"','id="missing"'), source.replace('</body>','<p id="indicator-reading">extra</p></body>')):
            self.page.write_text(changed)
            with self.assertRaises(ValueError): self.build()
            self.assertEqual(changed, self.page.read_text())
            self.assertEqual(RUNTIME, self.runtime.read_text())

    def test_cache_revision_tracks_runtime_bytes(self):
        self.build()
        with patch('deploy.preparar_sitio_publico.apply_fallbacks', side_effect=lambda s, r:s):
            normalize_html(self.page, self.site)
        expected = hashlib.sha256(self.runtime.read_bytes()).hexdigest()[:12]
        self.assertIn('/assets/indicator.js?v='+expected, self.page.read_text())
        self.assertNotIn('/assets/indicator.js?v=2211', self.page.read_text())

    def test_revalidation_is_limited_and_idempotent(self):
        rules = prepare_public_revalidation('# existing rule\n')
        self.assertIn('^/observatorio/precios/ipc/(index[.]html|datos[.]csv)?$', rules)
        self.assertIn('^/assets/indicator[.]js$', rules)
        self.assertEqual(rules, prepare_public_revalidation(rules))
        self.assertTrue(rules.startswith('# existing rule\n'))

    def test_complete_current_series_is_preserved(self):
        data = json.loads((Path(__file__).parent/'datos.json').read_text())
        self.build(data)
        rows = list(csv.reader(io.StringIO((self.page.parent/'datos.csv').read_text(encoding='utf-8-sig')), delimiter=';'))[1:]
        ipc = data['ipcba']
        self.assertEqual([r[0] for r in rows], ipc['meses'])
        self.assertEqual([float(r[1]) for r in rows], ipc['var_m'])
        self.assertEqual([float(r[2]) for r in rows], ipc['var_ia'])


if __name__ == '__main__': unittest.main()
