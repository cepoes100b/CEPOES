"""Offline checks for the first analytical indicator and fail-closed parser."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import build_health_indicator as H
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'snapshots/c2022_caba_salud_c1_1.xlsx'
class HealthIndicator(unittest.TestCase):
    def test_official_totals_and_exact_rates(self):
        raw=H.extract(H.read_cells(SOURCE));data=H.payload(raw);ind=data['indicators'][0]
        self.assertEqual(len(ind['rows']),15)
        self.assertEqual(sum(r['numerator'] for r in ind['rows']),504918)
        self.assertEqual(sum(r['denominator'] for r in ind['rows']),3095454)
        self.assertEqual(ind['city']['value'],504918/3095454*100)
        self.assertEqual(ind['rows'][7]['value'],84747/203888*100)
        self.assertEqual(data['derived_data_license'],'CC BY-SA 4.0')
        self.assertIn('particulares',ind['universe'])
    def test_schema_period_categories_partition_and_coverage_rejected(self):
        original=H.read_cells(SOURCE)
        for field,bad in [('A2','wrong period'),('F3','wrong category'),('B7','Comuna 1'),('C6',0),('F6',0),('A21','missing universe')]:
            cells=copy.deepcopy(original);cells[field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):H.extract(cells)
    def test_changed_bytes_leave_previous_output_intact(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);bad=p/'bad.xlsx';bad.write_bytes(SOURCE.read_bytes()+b'changed');output=p/'data.json';output.write_text('last-valid')
            result=subprocess.run([sys.executable,str(HERE/'build_health_indicator.py'),'--source',str(bad),'--output',str(output)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual(output.read_text(),'last-valid')
    def test_payload_matches_versioned_output(self):
        expected=H.payload(H.extract(H.read_cells(SOURCE)))
        actual=json.loads((HERE.parent/'public/assets/mapa-territorial/data/analysis/indicators.json').read_text())
        self.assertEqual(actual,expected)
if __name__=='__main__':unittest.main()
