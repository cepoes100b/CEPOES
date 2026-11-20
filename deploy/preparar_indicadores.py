"""Regenera las fichas estáticas y el respaldo parcial desde datos.json canónico."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import math
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .preparar_sitio_publico import element_span, fmt_date, fmt_period, ROOT

# Ruta relativa, campos canónicos (incluidos los que consume el runtime) y
# columnas exportadas en el orden histórico de ambas descargas.
SPECS = {
    "canastas": ("precios/canasta-consumo", ("meses", "ca", "caysh", "total"),
                 ("canasta_alimentaria_pesos", "caysh_pesos", "canasta_total_pesos")),
    "ipcba": ("precios/ipc", ("meses", "var_m", "var_ia"),
              ("variacion_mensual_pct", "variacion_interanual_pct")),
    "empleo": ("trabajo/empleo", ("trimestres", "empleo", "actividad", "desocupacion", "subocupacion"),
               ("empleo_pct", "actividad_pct", "desocupacion_pct")),
    "pobreza": ("condiciones-de-vida/pobreza",
                ("periodos", "pob_per_pct", "ind_per_pct", "pob_per_abs", "ind_per_abs"),
                ("pobreza_personas_pct", "indigencia_personas_pct")),
}
BACKUP = "assets/data/datos.json"
RUNTIME = "assets/indicator.js"
PROVENANCE = "respaldo_generado_por_bloque"
MONTHS = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")


def ordinal(period, key):
    if isinstance(period, str):
        if key == "ipcba" and (m := re.fullmatch(r"([A-Za-z]{3})-([0-9]{2})", period)) and m[1] in MONTHS:
            return (2000 + int(m[2])) * 12 + MONTHS.index(m[1])
        if key == "canastas" and (m := re.fullmatch(r"([0-9]{4})-(0[1-9]|1[0-2])", period)):
            return int(m[1]) * 12 + int(m[2]) - 1
        if key in {"empleo", "pobreza"} and (m := re.fullmatch(r"([0-9]{4})-T([1-4])", period)):
            return int(m[1]) * 4 + int(m[2]) - 1
    raise ValueError(f"{key}: período inválido: {period!r}")


def rows(data, key):
    _, fields, _ = SPECS[key]
    block = data.get(key)
    if not isinstance(block, dict):
        raise ValueError(f"{key}: bloque faltante")
    cols = [block.get(f) for f in fields]
    if not all(isinstance(col, list) for col in cols) or len(cols[0]) < 2 or any(
            len(col) != len(cols[0]) for col in cols):
        raise ValueError(f"{key}: series ausentes o desalineadas")
    out = list(zip(*cols, strict=True))
    periods = [ordinal(row[0], key) for row in out]
    if any(b != a + 1 for a, b in zip(periods, periods[1:])):
        raise ValueError(f"{key}: períodos duplicados, discontinuos o desordenados")
    for period, *values in out:
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError(f"{key}: valor no numérico o no finito en {period}")
        if key == "canastas" and any(v <= 0 for v in values):
            raise ValueError(f"{key}: valor no positivo en {period}")
        if key == "empleo" and any(not 0 <= v <= 100 for v in values):
            raise ValueError(f"{key}: porcentaje fuera de rango en {period}")
        if key == "pobreza" and (not 0 <= values[1] <= values[0] <= 100 or
                                not 0 <= values[3] <= values[2] or
                                not all(v == int(v) for v in values[2:])):
            raise ValueError(f"{key}: tasas o conteos fuera de rango en {period}")
    if key == "ipcba":
        div = block.get("divisiones")
        latest = periods[-1]
        if not isinstance(div, dict) or div.get("periodo") != f"{latest // 12:04d}-{latest % 12 + 1:02d}":
            raise ValueError(f"{key}: divisiones no pertenecen al último período")
    return out


def export_csv(series, key):
    _, _, cols = SPECS[key]
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(("periodo", *cols))
    for period, *values in series:
        writer.writerow((period, *(int(v) if v == int(v) else v for v in values[:len(cols)])))
    return stream.getvalue().removesuffix("\r\n").encode("utf-8-sig")


def ar(value, digits=1):
    rounded = Decimal(str(value)).quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP)
    return f"{rounded:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def pct(value, signed=False):
    return ("+" if signed and value > 0 else "") + ar(value) + "%"


def money(value):
    return "$ " + ar(value, 0)


def direction(value):
    return "aumentó" if value > 0 else "disminuyó" if value < 0 else "no varió"


def delta(current, previous):
    value = current - previous
    suffix = f"{direction(value)} {ar(abs(value))} p.p." if value else "no varió."
    return f"Respecto del período anterior, {suffix}"


def presentation(series, key):
    period, a, b, *extra = series[-1]
    previous = series[-2]
    note = fmt_period(period)
    if key == "ipcba":
        primary, secondary = pct(b, True), pct(a, True)
        reading = f"La inflación interanual se ubica en {pct(b)}. {delta(b, previous[2])}"
        render = lambda row: [pct(v, True) for v in row[1:]]
    elif key == "canastas":
        total = extra[0]
        mom = (total / previous[3] - 1) * 100
        primary, secondary = money(total), pct(mom, True)
        change = (f"El valor {direction(mom)} {ar(abs(mom))}% respecto del mes anterior."
                  if mom else "El valor no varió respecto del mes anterior.")
        reading = f"La canasta total del hogar de referencia alcanza {primary}. {change}"
        render = lambda row: [money(v) for v in row[1:]]
    elif key == "empleo":
        primary, secondary = pct(a), pct(extra[0])
        reading = f"La tasa de empleo es {primary} y la desocupación alcanza {secondary}. {delta(a, previous[1])}"
        render = lambda row: [pct(v) for v in row[1:4]]
    else:
        primary, secondary = pct(a), pct(b)
        note = ar(extra[0], 0) + " personas bajo la línea de pobreza"
        reading = (f"La pobreza por ingresos alcanza al {primary} de las personas y la indigencia al "
                   f"{secondary}. {delta(a, previous[1])}")
        render = lambda row: [pct(v) for v in row[1:3]]
    return {
        "indicator-primary-value": primary, "indicator-primary-period": fmt_period(period),
        "indicator-secondary-value": secondary, "indicator-secondary-note": note,
        "indicator-reading": reading, "indicator-meta-first": fmt_period(series[0][0]),
        "indicator-meta-period": fmt_period(period),
    }, [[fmt_period(row[0]), *render(row)] for row in reversed(series)]


def single_sub(pattern, replacement, source, label):
    updated, count = re.subn(pattern, replacement, source, flags=re.S | re.I)
    if count != 1:
        raise ValueError(f"Se esperaba un único destino {label}; encontrados {count}")
    return updated


def element(source, element_id):
    matches = list(re.finditer(
        rf'<(?P<tag>[a-zA-Z0-9]+)\b[^>]*\sid=["\']{re.escape(element_id)}["\'][^>]*>', source, re.S))
    if len(matches) != 1 or (span := element_span(source, matches[0])) is None:
        raise ValueError(f"Se esperaba un único elemento completo #{element_id}")
    return matches[0], span


def render_html(source, key, series, generated, runtime_revision):
    values, rows_html = presentation(series, key)
    values["data-date"] = fmt_date(generated) + " · Repositorio CEPOES"
    for element_id, value in values.items():
        opening, (_, end) = element(source, element_id)
        closing = re.search(rf'</{opening["tag"]}\s*>$', source[:end], re.I)
        source = source[:opening.end()] + html.escape(value) + source[closing.start():]
    opening, (start, end) = element(source, "indicator-table")
    if opening["tag"].lower() != "table":
        raise ValueError("#indicator-table debe ser una tabla")
    body = "".join('<tr><td>' + html.escape(row[0]) + '</td>' +
                   "".join('<td class="num">' + html.escape(v) + '</td>' for v in row[1:]) + '</tr>'
                   for row in rows_html)
    table = single_sub(r'(<tbody\b[^>]*>).*?(</tbody\s*>)',
                       lambda m: m[1] + body + m[2], source[start:end], "tbody")
    source = source[:start] + table + source[end:]
    anchor, _ = element(source, "indicator-download")
    if anchor["tag"].lower() != "a":
        raise ValueError("#indicator-download debe ser un enlace")
    tagged = single_sub(r'\bhref=["\'][^"\']*["\']', 'href="datos.csv"', anchor[0], "href de descarga")
    source = source[:anchor.start()] + tagged + source[anchor.end():]
    datasets = 0
    def dataset(m):
        nonlocal datasets
        obj = json.loads(m[2])
        if not isinstance(obj, dict) or obj.get("@type") != "Dataset":
            return m[0]
        if obj.get("distribution", {}).get("contentUrl") != (
                "https://cepoes.org/observatorio/" + SPECS[key][0] + "/datos.csv"):
            raise ValueError(f"{key}: distribución Dataset inesperada")
        datasets += 1
        obj["temporalCoverage"] = values["indicator-meta-first"] + "/" + values["indicator-meta-period"]
        return m[1] + json.dumps(obj, ensure_ascii=True) + m[3]
    source = re.sub(r'(<script\b[^>]*\btype=["\']application/ld\+json["\'][^>]*>)(.*?)(</script\s*>)',
                    dataset, source, flags=re.I | re.S)
    if datasets != 1:
        raise ValueError(f"{key}: se esperaba un único Dataset")
    return single_sub(r'(/assets/indicator[.]js)(?:[?][^"\']*)?(?=["\'])',
                      lambda m: f"{m[1]}?v={runtime_revision}", source, "runtime indicador")


def patch_runtime(source):
    """Ajusta sólo los dos puntos de la versión heredada que afecta este cambio."""
    before = (
        "C.set('data-date',C.dateLabel(D.generado)+' · '+C.source);",
        "delta(I.var_m[n],I.var_m[n-1])",
    )
    after = (
        "const block={ipc:'ipcba',canasta:'canastas',empleo:'empleo',pobreza:'pobreza'}[id];\n"
        "  const processing=C.source==='respaldo local'&&block?D.respaldo_generado_por_bloque?.[block]??D.generado:D.generado;\n"
        "  C.set('data-date',C.dateLabel(processing)+' · '+C.source);",
        "delta(I.var_ia[n],I.var_ia[n-1])",
    )
    for old, new in zip(before, after):
        if source.count(new) == 1 and old not in source:
            continue
        if source.count(old) != 1 or new in source:
            raise ValueError("Runtime indicador: no se encontró la versión prevista")
        source = source.replace(old, new, 1)
    return source


def read_json(path):
    def invalid(value):
        raise ValueError(f"JSON no estándar en {path.name}: {value}")
    result = json.loads(path.read_bytes(), parse_constant=invalid)
    if not isinstance(result, dict):
        raise ValueError(f"JSON sin objeto raíz: {path.name}")
    return result


def prepare(site: Path, canonical: Path):
    data, fallback = read_json(canonical), read_json(site / BACKUP)
    generated = data.get("generado")
    if not isinstance(generated, str) or date.fromisoformat(generated).isoformat() != generated:
        raise ValueError("Fecha canónica de procesamiento no válida")
    provenance = fallback.get(PROVENANCE, {})
    if not isinstance(provenance, dict):
        raise ValueError("Metadatos del respaldo incompatibles")
    runtime = patch_runtime((site / RUNTIME).read_text(encoding="utf-8")).encode("utf-8")
    revision = hashlib.sha256(runtime).hexdigest()[:12]
    pending = {RUNTIME: runtime}
    for key, (slug, _, cols) in SPECS.items():
        series = rows(data, key)
        previous = rows(fallback, key)
        old_dates = {row[0] for row in previous}
        coverage = {row[0] for row in series}
        if not old_dates <= coverage or generated < provenance.get(key, fallback["generado"]):
            raise ValueError(f"{key}: la fuente canónica retrocede respecto del respaldo")
        folder = "observatorio/" + slug
        page, table = folder + "/index.html", folder + "/datos.csv"
        with (site / table).open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=";")
            if next(reader, []) != ["periodo", *cols] or any(
                    len(row) != len(cols) + 1 or row[0] not in coverage for row in reader):
                raise ValueError(f"{key}: CSV anterior incompatible o con períodos omitidos")
        pending[page] = render_html((site / page).read_text(encoding="utf-8"), key, series,
                                    generated, revision).encode("utf-8")
        pending[table] = export_csv(series, key)
        fallback[key] = data[key]
        provenance[key] = generated
        print(f"{key}: {series[0][0]} a {series[-1][0]} ({len(series)} períodos)")
    fallback[PROVENANCE] = provenance  # No cambia generado ni los bloques fuera del alcance.
    pending[BACKUP] = (json.dumps(fallback, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    # Verificar todo antes de escribir; la publicación SFTP ocurre mucho después.
    for rel, content in pending.items():
        path = site / rel
        if path.read_bytes() != content:
            path.write_bytes(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    prepare(parser.parse_args().site, ROOT / "datos.json")
