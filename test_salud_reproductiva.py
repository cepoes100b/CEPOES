"""Regresiones del monitor: sin red ni cambios a los datos del repositorio."""
import copy
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import actualizar_salud_reproductiva as monitor


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / 'data.json'
        self.root = Path(self.tmp.name) / 'root.json'
        self.report = Path(self.tmp.name) / 'report.json'
        self.original = {
            'generated_at': '2026-10-26T17:24:05Z',
            'monitoring': {'last_checked_at': '2026-10-26T17:24:05Z',
                           'source_hashes': {'a': monitor.fingerprint(b'old', 'a.pdf'),
                                             'b': 'prior-b'},
                           'review_required': False},
            'sources': [{'id': 'a', 'url': 'https://example.test/a.pdf'},
                        {'id': 'b', 'url': 'https://example.test/b.pdf'},
                        {'id': 'proyecto_control', 'url': 'https://example.test/skip'}],
            'ive_ile': {'xlsx': 'https://example.test/c.xlsx'},
            'transparency_matrix': [{'unchanged': True}],
        }
        self.before = json.dumps(self.original).encode()
        self.data.write_bytes(self.before)
        self.root.write_bytes(self.before)
        for name, value in [('DATA', self.data), ('ROOT', self.root)]:
            p = patch.object(monitor, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.sleep = patch.object(monitor.time, 'sleep').start()
        self.addCleanup(patch.stopall)

    def run_monitor(self, effects):
        with patch.object(monitor, 'get', side_effect=effects) as get:
            status = monitor.main(self.report)
        return status, json.loads(self.report.read_text()), get

    def test_success_preserves_content_and_synchronizes_outputs(self):
        status, report, get = self.run_monitor([b'old', b'new', b'xlsx'])
        self.assertEqual(status, 0)
        self.assertEqual(report['status'], 'complete')
        self.assertEqual(get.call_count, 3)
        self.assertEqual(self.data.read_bytes(), self.root.read_bytes())
        result = json.loads(self.data.read_text())
        self.assertNotEqual(result['monitoring']['last_checked_at'], self.original['monitoring']['last_checked_at'])
        self.assertTrue(result['monitoring']['review_required'])
        for key in ('sources', 'ive_ile', 'transparency_matrix'):
            self.assertEqual(result[key], self.original[key])

    def test_timeout_keeps_hashes_and_dates_but_checks_remaining_sources(self):
        status, report, get = self.run_monitor([TimeoutError('slow')] * 3 + [b'new', b'xlsx'])
        self.assertEqual(status, 1)
        self.assertEqual(get.call_count, 5)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['sources'][0]['attempts'], 3)
        self.assertEqual(len(report['sources'][0]['errors']), 3)
        self.assertEqual(report['source_hashes']['a'], self.original['monitoring']['source_hashes']['a'])
        self.assertEqual(report['source_hashes']['b'], monitor.fingerprint(b'new', 'b.pdf'))
        self.assertEqual(report['last_complete_checked_at'], self.original['monitoring']['last_checked_at'])
        self.assertEqual(self.data.read_bytes(), self.before)
        self.assertEqual(self.root.read_bytes(), self.before)
        self.assertTrue(report['review_required'])

    def test_transient_failure_recovers_within_attempt_limit(self):
        status, report, _ = self.run_monitor([urllib.error.URLError(TimeoutError('slow')), b'old', b'new', b'xlsx'])
        self.assertEqual(status, 0)
        self.assertEqual(report['sources'][0]['attempts'], 2)
        self.assertEqual(len(report['sources'][0]['errors']), 1)
        self.sleep.assert_called_once_with(1)

    def test_partial_recovery_does_not_claim_complete(self):
        status, report, _ = self.run_monitor([TimeoutError(), b'old'] + [TimeoutError()] * 3 + [b'xlsx'])
        self.assertEqual(status, 1)
        self.assertEqual([s['status'] for s in report['sources']], ['ok', 'failed', 'ok'])
        self.assertEqual(self.data.read_bytes(), self.before)
        self.assertEqual(self.root.read_bytes(), self.before)

    def test_permanent_http_error_is_not_retried(self):
        error = urllib.error.HTTPError('https://example.test/a.pdf', 403, 'Forbidden', {}, None)
        status, report, get = self.run_monitor([error, b'new', b'xlsx'])
        self.assertEqual(status, 1)
        self.assertEqual(get.call_count, 3)
        self.assertEqual(report['sources'][0]['attempts'], 1)
        self.sleep.assert_not_called()

    def test_http_503_retries_and_review_flag_stays_true(self):
        original = copy.deepcopy(self.original)
        original['monitoring']['review_required'] = True
        self.data.write_text(json.dumps(original))
        error = urllib.error.HTTPError('https://example.test/a.pdf', 503, 'Unavailable', {}, None)
        status, report, _ = self.run_monitor([error, b'old', b'new', b'xlsx'])
        self.assertEqual(status, 0)
        self.assertTrue(report['review_required'])
        self.assertEqual(report['sources'][0]['attempts'], 2)

    def test_download_applies_explicit_timeout(self):
        with patch.object(monitor.urllib.request, 'urlopen', side_effect=TimeoutError()) as urlopen:
            with self.assertRaises(TimeoutError):
                monitor.get('https://example.test/a.pdf')
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 90)


if __name__ == '__main__':
    unittest.main()
