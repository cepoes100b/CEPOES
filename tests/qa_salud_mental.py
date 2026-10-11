"""QA real de barras. Uso: python tests/qa_salud_mental.py SITE OUTPUT.

Requiere Playwright y Chromium; SITE es una copia pública local preparada.
Sirve sólo esos archivos por rutas interceptadas, sin acceso a producción.
"""
import argparse
import hashlib
import json
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('site', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--chromium', default='/usr/bin/chromium')
    args = parser.parse_args()
    site = args.site.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    data = json.loads((site / 'assets/data/salud-mental.json').read_text())
    rows = sorted(data['jurisdicciones_2025'], key=lambda r: -r['tasa_100k_mayores_5_2025'])
    assert len(rows) == 24
    maximum = max(r['tasa_100k_mayores_5_2025'] for r in rows)
    results = []
    missing = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, args=['--no-sandbox'])
        def serve(route):
            url = urlsplit(route.request.url)
            path = unquote(url.path).lstrip('/')
            if not path or path.endswith('/'):
                path += 'index.html'
            target = (site / path).resolve()
            if url.netloc != 'preview.test' or not target.is_relative_to(site) or not target.is_file():
                missing.add(route.request.url)
                route.abort()
                return
            route.fulfill(body=target.read_bytes(), content_type=mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
        for width in [320, 390, 1440]:
            for theme in ['light', 'dark']:
                page = browser.new_page(viewport={'width': width, 'height': 900}, device_scale_factor=1)
                page.route('**/*', serve)
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto('https://preview.test/observatorio/salud-mental/')
                page.locator('.sm-jur-fill').nth(23).wait_for(state='attached')
                decline = page.get_by_role('button', name='No aceptar', exact=True)
                if decline.is_visible():
                    decline.click()
                page.evaluate('(theme) => document.documentElement.dataset.theme = theme', theme)
                bars = page.locator('.sm-jur-row').evaluate_all('''els => els.map(row => {
                    const fill = row.querySelector('.sm-jur-fill');
                    const track = row.querySelector('.sm-jur-track');
                    const box = fill.getBoundingClientRect();
                    return {name: row.querySelector('.sm-jur-name').textContent,
                        value: row.querySelector('.sm-jur-value').textContent,
                        percent: parseFloat(fill.style.width), width: box.width, height: box.height,
                        track: track.getBoundingClientRect().width,
                        display: getComputedStyle(fill).display,
                        color: getComputedStyle(fill).backgroundColor};
                })''')
                assert len(bars) == 24
                for actual, expected in zip(bars, rows):
                    assert actual['name'] == expected['provincia']
                    rate = expected['tasa_100k_mayores_5_2025']
                    assert actual['value'] == f'{rate:.2f}'.replace('.', ',')
                    assert abs(actual['percent'] - rate / maximum * 100) <= .051
                    assert actual['width'] > 0 and actual['height'] == 12, actual
                    assert abs(actual['width'] - actual['track'] * actual['percent'] / 100) < .1
                    assert actual['display'] == 'block'
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert not errors, errors
                panel = page.locator('.sm-jur-panel')
                panel.evaluate('(e) => window.scrollTo({top: e.getBoundingClientRect().top + scrollY - 120, behavior: "instant"})')
                screenshot = args.output / f'barras-{width}-{theme}.png'
                page.screenshot(path=str(screenshot))
                page.locator('.sm-jur-row').last.evaluate('(e) => window.scrollTo({top: e.getBoundingClientRect().bottom + scrollY - innerHeight + 80, behavior: "instant"})')
                page.screenshot(path=str(args.output / f'barras-{width}-{theme}-final.png'))
                # Prove this regression detects the original inline-span failure.
                old_style = page.add_style_tag(content='.sm-jur-fill { display: inline !important; }')
                old_widths = page.locator('.sm-jur-fill').evaluate_all('els => els.map(e => e.getBoundingClientRect().width)')
                assert old_widths == [0] * 24
                old_style.evaluate('(e) => e.remove()')
                results.append({'viewport': width, 'theme': theme, 'bars': bars,
                    'original_widths': old_widths, 'screenshot': screenshot.name,
                    'sha256': hashlib.sha256(screenshot.read_bytes()).hexdigest()})
                page.close()
        browser.close()
    evidence = {'results': results, 'unavailable_resources': sorted(missing),
        'data_sha256': hashlib.sha256((site / 'assets/data/salud-mental.json').read_bytes()).hexdigest(),
        'scope': 'Local candidate; no public access or deployment verification'}
    (args.output / 'result.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(f'PASS: {len(results)} variants × 24 proportional nonzero bars; original CSS fails all 24.')
    print('Unavailable resources:', sorted(missing))


if __name__ == '__main__':
    main()
