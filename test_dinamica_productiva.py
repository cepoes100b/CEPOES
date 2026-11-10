import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import requests
import generar_dinamica_productiva as g

RID = g.RESOURCES[2026]
CDN = 'https://cdn.buenosaires.gob.ar/datosabiertos/datasets/agencia-gubernamental-de-control/habilitaciones-aprobadas/habilitaciones-aprobadas2026.csv'


def response(status=200, content=b'rubro,domicilio\nCOMERCIO,CALLE 1\n', metadata=None, mime='text/csv'):
    r = requests.Response()
    r.status_code = status
    r._content = content
    r.headers['content-type'] = mime
    if metadata is not None:
        r.json = Mock(return_value=metadata)
    return r


def metadata(**changes):
    resource = {'id': RID, 'format': 'CSV', 'url': CDN}
    resource.update(changes)
    return {'success': True, 'result': resource}


class DownloadTests(unittest.TestCase):
    @patch.object(g.requests, 'get')
    def test_resolves_same_resource_and_downloads_cdn(self, get):
        get.side_effect = [response(metadata=metadata()), response()]
        self.assertEqual(g.download(2026), response().content)
        self.assertIn('resource_show?id=' + RID, get.call_args_list[0].args[0])
        self.assertEqual(get.call_args_list[1].args[0], CDN)
        self.assertFalse(get.call_args.kwargs['allow_redirects'])

    @patch.object(g.time, 'sleep')
    @patch.object(g.requests, 'get')
    def test_transient_error_retried(self, get, sleep):
        get.side_effect = [response(503), response(502), response()]
        self.assertEqual(g.get_source(CDN).status_code, 200)
        self.assertEqual(get.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch.object(g.time, 'sleep')
    @patch.object(g.requests, 'get')
    def test_timeout_retries_are_bounded(self, get, sleep):
        get.side_effect = requests.Timeout('timeout')
        with self.assertRaises(requests.Timeout):
            g.get_source(CDN)
        self.assertEqual(get.call_count, 3)

    @patch.object(g.requests, 'get', return_value=response(404))
    def test_non_transient_error_not_retried(self, get):
        with self.assertRaises(requests.HTTPError):
            g.get_source(CDN)
        self.assertEqual(get.call_count, 1)

    @patch.object(g, 'get_source')
    def test_unavailable_catalog_falls_back_to_canonical_resource(self, get):
        get.side_effect = [requests.ConnectionError('unavailable'), response()]
        self.assertEqual(g.download(2026), response().content)
        self.assertTrue(get.call_args.args[0].endswith('/' + RID + '/download'))

    @patch.object(g, 'get_source')
    def test_non_json_catalog_falls_back_to_same_resource(self, get):
        broken = response()
        broken.json = Mock(side_effect=requests.exceptions.JSONDecodeError('invalid', '', 0))
        get.side_effect = [broken, response()]
        self.assertEqual(g.download(2026), response().content)
        self.assertTrue(get.call_args.args[0].endswith('/' + RID + '/download'))

    @patch.object(g, 'get_source')
    def test_invalid_catalog_is_not_silently_bypassed(self, get):
        for change in ({'id': 'other'}, {'format': 'XLSX'}, {'url': 'https://example.com/a.csv'}, {'url': CDN + '?token=x'}, {'url': CDN.replace('https:', 'http:')}):
            with self.subTest(change=change):
                get.reset_mock()
                get.return_value = response(metadata=metadata(**change))
                with self.assertRaises(ValueError):
                    g.download(2026)
                self.assertEqual(get.call_count, 1)

    @patch.object(g, 'get_source')
    def test_html_and_empty_download_rejected(self, get):
        for bad in (response(content=b''), response(mime='text/html'), response(content=b'<!doctype html>error')):
            with self.subTest(content=bad.content):
                get.side_effect = [response(metadata=metadata()), bad]
                with self.assertRaises(ValueError):
                    g.download(2026)

    @patch.object(g.requests, 'get', return_value=response(302))
    def test_redirect_is_not_followed(self, get):
        with self.assertRaises(ValueError):
            g.get_source(CDN)

    @patch.object(g.requests, 'get')
    def test_canonical_redirect_to_official_csv_is_followed(self, get):
        redirect = response(302)
        redirect.headers['location'] = CDN
        get.side_effect = [redirect, response()]
        self.assertEqual(g.get_source('https://data.buenosaires.gob.ar/download').status_code, 200)
        self.assertEqual(get.call_args.args[0], CDN)

    @patch.object(g, 'download')
    def test_late_failure_preserves_output(self, download):
        raw = b'DescripcionRubro,Calles,Seccion,Manzana\n' + b'COMERCIO,CALLE 1,1,1\n' * 60
        download.side_effect = [raw, raw, requests.ConnectionError('third resource failed')]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'dinamica.json'
            out.write_text('last valid', encoding='utf-8')
            with patch.object(g, 'OUT', out):
                with self.assertRaises(requests.ConnectionError):
                    g.main()
            self.assertEqual(out.read_text(encoding='utf-8'), 'last valid')
            self.assertEqual(download.call_count, 3)

    @patch.object(g, 'download', side_effect=requests.ConnectionError('unavailable'))
    def test_failure_preserves_last_valid_output(self, download):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'dinamica.json'
            out.write_text('last valid', encoding='utf-8')
            with patch.object(g, 'OUT', out):
                with self.assertRaises(requests.ConnectionError):
                    g.main()
            self.assertEqual(out.read_text(encoding='utf-8'), 'last valid')


if __name__ == '__main__':
    unittest.main()
