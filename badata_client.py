"""Cliente resiliente para el catálogo público de BA Data.

Primero usa la API CKAN. Si el portal devuelve HTML u otra respuesta no JSON,
reconstruye el listado de recursos desde la página pública del dataset.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

API = "https://data.buenosaires.gob.ar/api/3/action/package_show"
BASE_URL = "https://data.buenosaires.gob.ar/"
DATASET_URL = urljoin(BASE_URL, "dataset/")
HEADERS = {
    "User-Agent": "CEPOES-data-pipeline/1.1 (+https://cepoes.org)",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}
TIMEOUT = (10, 90)


def _resource_from_item(item, dataset_url: str) -> dict | None:
    heading = item.select_one("a.heading")
    if heading is None:
        return None
    name = (heading.get("title") or heading.get_text(" ", strip=True) or "").strip()
    if not name:
        return None

    download = item.select_one('a.resource-url-analytics[href]')
    if download is None:
        download = item.select_one('a[href*="/download"]')
    href = (download.get("href") if download else "") or ""
    if not href:
        return None
    url = urljoin(dataset_url, href)

    fmt_el = item.select_one(".format-label")
    fmt = ""
    if fmt_el is not None:
        fmt = (fmt_el.get("data-format") or fmt_el.get_text(" ", strip=True) or "").strip()
    if not fmt:
        low = url.lower().split("?", 1)[0]
        for ext in ("csv", "xlsx", "xls", "geojson", "zip", "json"):
            if low.endswith("." + ext):
                fmt = ext
                break

    rid = None
    for candidate in (heading.get("href") or "", href):
        m = re.search(r"/resource/([^/?#]+)", candidate)
        if m:
            rid = m.group(1)
            break

    return {
        "id": rid,
        "name": name,
        "url": url,
        "format": fmt,
        "mimetype": "",
        "last_modified": None,
        "metadata_modified": None,
    }


def _package_from_html(dataset: str, response: requests.Response) -> dict:
    soup = BeautifulSoup(response.text, "html.parser")
    resources = []
    seen = set()
    for item in soup.select("li.resource-item"):
        resource = _resource_from_item(item, response.url)
        if resource and resource["url"] not in seen:
            seen.add(resource["url"])
            resources.append(resource)

    if not resources:
        raise RuntimeError(
            f"BA Data no expuso recursos reconocibles para {dataset} "
            f"(HTTP {response.status_code}, content-type {response.headers.get('content-type','')})"
        )

    title = soup.select_one("h1")
    return {
        "name": title.get_text(" ", strip=True) if title else dataset,
        "resources": resources,
        "metadata_modified": None,
        "_cepoes_catalog_mode": "html",
        "_cepoes_dataset_url": response.url,
    }


def package_show(dataset: str) -> dict:
    api_error = None
    try:
        r = requests.get(API, params={"id": dataset}, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        try:
            payload = r.json()
        except ValueError as exc:
            api_error = exc
        else:
            if payload.get("success") and payload.get("result"):
                result = payload["result"]
                result["_cepoes_catalog_mode"] = "ckan-api"
                result["_cepoes_dataset_url"] = urljoin(DATASET_URL, dataset)
                return result
            api_error = RuntimeError(f"CKAN no devolvió el dataset {dataset}")
    except requests.RequestException as exc:
        api_error = exc

    page_url = urljoin(DATASET_URL, dataset)
    page = requests.get(page_url, timeout=TIMEOUT, headers=HEADERS, allow_redirects=True)
    page.raise_for_status()
    package = _package_from_html(dataset, page)
    package["_cepoes_api_error"] = type(api_error).__name__ if api_error else None
    return package
