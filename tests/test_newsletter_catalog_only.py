import contextlib
import io
import json
import unittest
from unittest.mock import patch

from scripts.dispatch_newsletter import main


class CatalogOnlyWorkflowOutputTest(unittest.TestCase):
    def test_reports_catalog_only_without_claiming_distribution(self):
        result = dict(ok=True, mode='catalog-only', cataloged=3,
                      accepted=0, retry=0, cancelled=0)
        output = io.StringIO()
        with patch.dict('os.environ', {'NEWSLETTER_DISPATCH_SECRET': 'local-test-only'}, clear=True), \
             patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(result).encode())), \
             contextlib.redirect_stdout(output):
            main()
        lines = output.getvalue().splitlines()
        self.assertEqual(json.loads(lines[0])['mode'], 'catalog-only')
        self.assertEqual(json.loads(lines[0])['accepted'], 0)
        self.assertIn('despacho de correo inhibido por código', lines[1])
