#!/usr/bin/env python3
"""Build the verified Censo 2022 indicator from the original INDEC XLSX.

Read-only source parsing with Python standard library; no workbook code is run.
The reviewed source is pinned by SHA-256. Changed inputs fail before output writes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

SOURCE_URL = 'https://www.indec.gob.ar/ftp/cuadros/poblacion/c2022_caba_salud_c1_1.xlsx'
SOURCE_SHA = '3b2c0cc40de697431ba15ccb02c96539a70be2925cce02b34c3ac4fc1131e5a9'
PDF_URL = 'https://www.estadisticaciudad.gob.ar/eyc/wp-content/uploads/2024/07/anuario_estadistico_2023.pdf'
PDF_SHA = '581f9c3991f0e0c77b5c5ed252850bbc428b559a41af559d3a1b8a2dc153e4e2'
CHECKED_AT = '2026-10-09'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
NAME = 'Sin obra social, prepaga ni plan estatal'
UNIVERSE = 'Personas censadas en viviendas particulares de la Ciudad Autónoma de Buenos Aires. Censo 2022. Excluye viviendas colectivas y personas en situación de calle.'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_cells(path):
    require(sha(path) == SOURCE_SHA, 'La fuente cambió: revisar versión y metodología antes de regenerar.')
    with zipfile.ZipFile(path) as z:
        require(sum(x.file_size for x in z.infolist()) < 2_000_000, 'XLSX inesperadamente grande.')
        strings = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        sheets = wb.findall('s:sheets/s:sheet', NS)
        require(len(sheets) == 1 and sheets[0].get('name') == 'Cuadro 1.1', 'Hoja inesperada.')
        cells = {}
        for c in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:c', NS):
            require(c.find('s:f', NS) is None, 'No se admiten fórmulas en el insumo verificado.')
            value = c.find('s:v', NS)
            if value is None:
                continue
            raw = value.text
            cells[c.get('r')] = strings[int(raw)] if c.get('t') == 's' else int(raw)
    return cells


def extract(cells):
    title = cells.get('A2', '')
    require('Población total en viviendas particulares' in title and 'Año 2022' in title, 'Universo o período inesperado.')
    require(cells.get('F3') == 'No tiene obra social, prepaga ni plan estatal', 'Cambió la categoría del numerador.')
    require(cells.get('E4') == 'Programas o planes estatales de salud', 'Cambió la partición de categorías.')
    require('situación de calle' in cells.get('A21', ''), 'Falta nota de exclusión.')
    require('INDEC' in cells.get('A23', '') and 'Resultados definitivos' in cells.get('A23', ''), 'Falta atribución de fuente.')
    raw = []
    for row in range(5, 21):
        values = [cells.get(f'{col}{row}') for col in 'CDEF']
        require(all(type(v) is int and v >= 0 for v in values), f'Conteo inválido en fila {row}.')
        total, obra, planes, sin = values
        require(total > 0 and obra + planes + sin == total, f'Partición inconsistente en fila {row}.')
        if row == 5:
            require(cells.get('A5') == '02' and cells.get('B5') == 'Ciudad Autónoma de Buenos Aires', 'Total geográfico inesperado.')
            raw.append({'id': 'ciudad', 'official_code': '02', 'counts': values})
        else:
            comuna = row - 5
            require(cells.get(f'B{row}') == f'Comuna {comuna}', f'Comuna ausente o duplicada: {comuna}.')
            require(cells.get(f'A{row}') == f'02{comuna * 7:03}', 'Código territorial inesperado.')
            raw.append({'id': f'comuna:{comuna}', 'official_code': cells[f'A{row}'], 'counts': values})
    require(raw[0]['counts'] == [3095454, 2523833, 66703, 504918], 'Los totales no coinciden con la versión revisada.')
    for col in range(4):
        require(sum(row['counts'][col] for row in raw[1:]) == raw[0]['counts'][col], 'La suma comunal no coincide con la Ciudad.')
    return raw


def verify_pdf(path, raw):
    require(sha(path) == PDF_SHA, 'Cambió el PDF de corroboración.')
    text = subprocess.run(['pdftotext', '-f', '86', '-l', '86', '-layout', str(path), '-'], check=True, capture_output=True, text=True).stdout
    require('6.C.3' in text and '6.C.4' in text and 'Año 2022' in text, 'Página de corroboración inesperada.')
    pattern = r'^ {0,4}(Total|[1-9]|1[0-5])\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$'
    rows = [m.groups() for line in text.splitlines() if (m := re.match(pattern, line))]
    require(len(rows) == 16, 'La tabla PDF debe contener total y 15 comunas.')
    for index, (row, expected) in enumerate(zip(rows, raw)):
        require(row[0] == ('Total' if index == 0 else str(index)), 'Orden de filas PDF inesperado.')
        require([int(v.replace('.', '')) for v in row[1:]] == expected['counts'], 'Diferencia entre XLSX y PDF.')


def payload(raw):
    source = {
        'id': 'indec-censo2022-caba-salud-c1-1',
        'name': 'INDEC. Censo 2022. Cuadro 1.1: cobertura de salud por comuna',
        'url': SOURCE_URL, 'publisher': 'Instituto Nacional de Estadística y Censos (INDEC)',
        'license': 'CC BY-SA 4.0', 'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/',
        'license_evidence_url': 'https://www.indec.gob.ar/indec/web/Nivel4-Tema-2-41-165?lang=es',
        'license_policy_url': 'https://www.indec.gob.ar/ftp/cuadros/publicaciones/politica_difusion_indec.pdf',
        'checked_at': CHECKED_AT, 'scope': UNIVERSE, 'sha256': SOURCE_SHA,
        'locator': 'Hoja Cuadro 1.1; C6:F20. Total de Ciudad: C5:F5. Notas: A21:A23.',
        'attribution': 'Fuente: INDEC, Censo Nacional de Población, Hogares y Viviendas 2022. Resultados definitivos. Porcentajes calculados por CEPOES a partir de conteos oficiales.',
    }
    rows = [{'id': r['id'], 'numerator': r['counts'][3], 'denominator': r['counts'][0], 'value': r['counts'][3] / r['counts'][0] * 100} for r in raw[1:]]
    total = raw[0]['counts']
    return {
        'schema': 'cepoes-territorial-analysis-v1', 'sources': [source],
        'indicators': [{
            'id': 'sin-cobertura-salud', 'status': 'verified', 'level': 'comuna',
            'name': NAME, 'unit': '% de población en viviendas particulares', 'unit_short': '%',
            'digits': 1, 'period': 'Censo 2022', 'universe': UNIVERSE,
            'method': 'Personas sin obra social, prepaga ni plan estatal divididas por el total de personas en viviendas particulares de la misma comuna, multiplicado por 100. Porcentajes derivados sin redondeo interno. No mide ausencia de atención ni de acceso al sistema público.',
            'numerator_label': 'Personas sin obra social, prepaga ni plan estatal',
            'denominator_label': 'Personas en viviendas particulares', 'multiplier': 100,
            'source_ids': [source['id']], 'rows': rows,
            'city': {'numerator': total[3], 'denominator': total[0], 'value': total[3] / total[0] * 100},
            'limits': ['Dato censal de 2022; no describe la situación actual.', 'Sólo disponible a escala comunal en este insumo; no imputar valores a barrios.', 'No equivale a demanda efectiva, cobertura de equipamientos ni accesibilidad a servicios.', 'La comparación entre territorios es descriptiva; no demuestra causalidad.'],
        }],
        'update_policy': 'Corte censal versionado. Una nueva fuente o revisión exige verificar esquema, universos y conteos; mantener la versión previa ante falla y conservar historial. No sustituir silenciosamente Censo 2022 por encuestas anuales ni extrapolar a barrios.',
        'derived_data_license': 'CC BY-SA 4.0',
    }


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-pdf', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    raw = extract(read_cells(args.source))
    if args.verify_pdf:
        verify_pdf(args.verify_pdf, raw)
    result = payload(raw)
    evidence = {'checked_at': CHECKED_AT, 'source_url': SOURCE_URL, 'source_sha256': sha(args.source), 'rows': 15, 'partition_and_city_totals': 'passed', 'pdf_crosscheck': 'passed' if args.verify_pdf else 'not-run', 'pdf_url': PDF_URL, 'pdf_sha256': PDF_SHA, 'pdf_page': 86, 'printed_page': 84, 'table': '6.C.3', 'raw_counts': raw}
    atomic_json(args.output, result)
    if args.evidence:
        atomic_json(args.evidence, evidence)
    print(json.dumps({'output': str(args.output), 'rows': 15, 'city': result['indicators'][0]['city'], 'pdf_crosscheck': evidence['pdf_crosscheck']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
