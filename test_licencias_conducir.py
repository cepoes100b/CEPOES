"""Regresión contra el CSV versionado; no certifica atención actual de las sedes."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import generar_oferta_total_runner as total
import generar_indice_busqueda_equipamientos as search

E = total.R.E
CFG = next(c for c in total.EXTRA_LAYERS if c['id'] == 'licencias-conducir')
ROOT = Path(__file__).resolve().parent


class LicenciasTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        E.DATASETS_TERRITORIO.update(total.EXTRA_DATASETS)
        cls.rows = E.read_source(CFG['source'])
        official, bc = E.official_territory()
        cls.items = [E.normalized_item(row, CFG, official, bc, i)
                     for i, row in enumerate(cls.rows, 1)]
        cls.items.sort(key=lambda x: (x.get('comuna') or 99, E.G.norm(x.get('barrio')), E.G.norm(x.get('nombre'))))
        cls.published = json.loads((ROOT / 'equipamientos/licencias-conducir.json').read_text())

    def test_complete_source_mapping_and_valid_coordinates(self):
        self.assertEqual(len(self.rows), 18)
        source = {f"licencias-conducir-{r['id']}": r for r in self.rows}
        for item in self.items:
            row = source[item['id']]
            with self.subTest(id=item['id']):
                self.assertEqual(item['direccion'], f"{row['calle_nombre']} {row['calle_altura']}")
                self.assertEqual(item['tipo'], row['actividad'])
                self.assertEqual(item['detalle'], row['actividad'])
                self.assertEqual(item['detalle2'], row['observacion'])
                self.assertEqual(item['web'], row['link'])
                self.assertEqual(item['email'], row['email'])
                self.assertEqual(item['coord'], [round(float(row['long']), 6), round(float(row['lat']), 6)])
                self.assertTrue(-58.6 < item['coord'][0] < -58.3)
                self.assertTrue(-34.8 < item['coord'][1] < -34.5)

    def test_ids_order_scope_and_generated_output(self):
        self.assertEqual([x['id'] for x in self.items], [f'licencias-conducir-{n}' for n in (13,12,5,10,6,7,18,4,14,15,1,8,11,16,2,17,3,9)])
        self.assertEqual(self.items, self.published['items'])
        self.assertEqual(self.published['total'], 18)
        for name in ('ACA Flores', 'ACA Libertador', 'Comuna 13'):
            pair = [x for x in self.items if x['nombre'] == name]
            self.assertEqual(len(pair), 2)
            self.assertEqual(len({x['tipo'] for x in pair}), 2)
        self.assertEqual(next(x for x in self.items if x['nombre']=='Comuna 5')['detalle2'], '(Momentáneamente sin servicio)')
        self.assertEqual(self.published['layer']['source_last_modified'], '2019-04-22T14:28:29.976042')

    def test_daily_runner_keeps_all_repaired_records(self):
        # Run the real daily entrypoint, restricting only the layer selection and
        # redirecting every generated artifact to a disposable directory.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'equipamientos'
            shutil.copytree(ROOT / 'equipamientos', out)
            with patch.object(E, 'BASE', root), patch.object(E, 'OUT', out), \
                 patch.object(E, 'LAYERS', []), patch.object(total, 'EXTRA_LAYERS', [CFG]), \
                 patch.object(total.R, 'DIR', out):
                self.assertEqual(total.main(), 0)
            regenerated = json.loads((out / 'licencias-conducir.json').read_text())
            self.assertEqual(regenerated['items'], self.items)
            self.assertEqual(regenerated['layer'], self.published['layer'])

    def test_address_fallback_is_opt_in(self):
        official, bc = E.official_territory()
        row = dict(self.rows[0], direccion='Dirección explícita')
        self.assertEqual(E.normalized_item(row, CFG, official, bc, 1)['direccion'], 'Dirección explícita')
        cfg = dict(CFG); cfg.pop('address_parts')
        self.assertEqual(E.normalized_item(self.rows[0], cfg, official, bc, 1)['direccion'], '')

    def test_both_search_generators_preserve_repaired_fields(self):
        expected = [dict({k: x[k] for k in search.KEEP if x.get(k) not in (None, '', [], {})}, layer=CFG['id']) for x in self.items]
        saved = json.loads((ROOT/'equipamientos/busqueda.json').read_text())
        self.assertEqual([x for x in saved['items'] if x['layer']==CFG['id']], expected)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'equipamientos'; out.mkdir()
            (out/'licencias-conducir.json').write_text(json.dumps(self.published))
            catalog={'layers':[dict(self.published['layer'], file='licencias-conducir.json')]}
            (out/'catalogo.json').write_text(json.dumps(catalog))
            public=Path(tmp)/'deploy/site-overlay/assets/data/equipamientos-busqueda.json'
            with patch.object(search,'OUT',out), patch.object(search,'PUBLIC',public):
                self.assertEqual(search.main(),0)
            self.assertEqual(json.loads(public.read_text())['items'],expected)
            with patch.object(E,'OUT',out), patch.object(E,'BASE',Path(tmp)):
                E.write_search_index(catalog['layers'])
            self.assertEqual(json.loads(public.read_text())['items'],expected)


if __name__ == '__main__':
    unittest.main()
