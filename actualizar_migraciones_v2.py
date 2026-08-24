#!/usr/bin/env python3
"""Adaptador robusto para la tabla M01 de IDECBA.

La planilla apila bloques anuales en orden descendente. Este lector toma
exclusivamente el primer bloque (el más reciente), identifica las columnas
por su encabezado y exige Total + 15 comunas antes de entregar datos al
actualizador general.
"""
import re
import requests
import actualizar_migraciones as base


def parse_commune_eah(content: bytes):
    rows = base.rows_from_workbook(content)
    aliases = {
        'nacida_caba_pct': ['ciudad de buenos aires', 'en esta ciudad', 'caba'],
        'prov_ba_pct': ['provincia de buenos aires', 'pcia. de buenos aires', 'prov. de buenos aires', 'prov. buenos aires', 'prov buenos aires'],
        'otra_provincia_pct': ['otra provincia', 'otras provincias'],
        'pais_limitrofe_pct': ['pais limitrofe', 'país limítrofe', 'paises limitrofes'],
        'pais_no_limitrofe_pct': ['pais no limitrofe', 'otro pais', 'otros paises', 'resto de paises'],
    }

    header_idx = None
    cols = {}
    commune_col = None
    for ri, row in enumerate(rows):
        mapped = {}
        ccol = None
        for ci, value in enumerate(row):
            nv = base.norm(value)
            if nv in {'comuna', 'comunas'}:
                ccol = ci
            for key, names in aliases.items():
                if any(base.norm(name) in nv for name in names):
                    mapped.setdefault(key, ci)
        if ccol is not None and len(mapped) == len(aliases):
            header_idx, cols, commune_col = ri, mapped, ccol
            break
    if header_idx is None:
        raise RuntimeError('M01: no se encontró el encabezado completo del bloque anual más reciente')

    # El título inmediatamente anterior al encabezado declara el año del bloque.
    latest_year = None
    for row in reversed(rows[max(0, header_idx-6):header_idx]):
        text = ' '.join(str(v) for v in row if v not in (None, ''))
        years = [int(x) for x in re.findall(r'(?<!\d)((?:19|20)\d{2})(?!\d)', text)]
        if years:
            latest_year = max(years)
            break
    if latest_year is None:
        years = []
        for row in rows:
            for value in row:
                if isinstance(value, (int, float)) and 2000 <= float(value) <= 2100:
                    years.append(int(value))
                else:
                    s = str(value).strip() if value is not None else ''
                    if re.fullmatch(r'(?:19|20)\d{2}', s):
                        years.append(int(s))
        if not years:
            raise RuntimeError('M01: no se pudo determinar el año del bloque más reciente')
        latest_year = max(years)

    def values_from(row):
        vals = {k: base.number(row[ci]) if ci < len(row) else None for k, ci in cols.items()}
        if not all(vals.get(k) is not None and 0 <= vals[k] <= 100 for k in aliases):
            return None
        vals = {k: round(float(vals[k]), 2) for k in aliases}
        vals['migracion_interna_pct'] = round(vals['prov_ba_pct'] + vals['otra_provincia_pct'], 2)
        vals['migracion_internacional_pct'] = round(vals['pais_limitrofe_pct'] + vals['pais_no_limitrofe_pct'], 2)
        return vals

    total = {}
    communes = {}
    for row in rows[header_idx + 1:]:
        cell = row[commune_col] if commune_col < len(row) else None
        label = base.norm(cell)
        if label == 'total' and not total:
            total = values_from(row) or {}
            continue
        commune = None
        if isinstance(cell, (int, float)) and float(cell).is_integer() and 1 <= int(cell) <= 15:
            commune = str(int(cell))
        else:
            m = re.fullmatch(r'(?:comuna\s*)?(1[0-5]|[1-9])', label)
            if m:
                commune = m.group(1)
        if commune:
            vals = values_from(row)
            if vals:
                communes[commune] = vals
            if len(communes) == 15:
                break
        elif communes and ('fuente:' in label or label.startswith('distribucion porcentual')):
            break

    if not total:
        raise RuntimeError(f'M01 {latest_year}: no se pudo leer el total Ciudad')
    if set(communes) != {str(i) for i in range(1, 16)}:
        raise RuntimeError(f'M01 {latest_year}: comunas incompletas: {sorted(communes)}')

    # Control de suma: las diferencias pequeñas se explican por lugar de nacimiento ignorado.
    for key, vals in [('Total', total), *[(f'Comuna {c}', communes[c]) for c in sorted(communes, key=int)]]:
        s = vals['nacida_caba_pct'] + vals['prov_ba_pct'] + vals['otra_provincia_pct'] + vals['pais_limitrofe_pct'] + vals['pais_no_limitrofe_pct']
        if not 97 <= s <= 103:
            raise RuntimeError(f'M01 {latest_year}: suma fuera de rango en {key}: {s}')

    return latest_year, communes, total


base.parse_commune_eah = parse_commune_eah

if __name__ == '__main__':
    base.main()
