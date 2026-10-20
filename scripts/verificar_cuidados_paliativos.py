"""Verifica conservación del texto y enlaces del documento versionado en la web."""
import json
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.text = []; self.links = []; self.ids = []
    def handle_data(self, data): self.text.append(data)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs: self.links.append(attrs["href"])
        if "id" in attrs: self.ids.append(attrs["id"])

def main():
    data = json.loads((ROOT / "datos/salud/cuidados-paliativos-texto.json").read_text())
    page = Page(); page.feed((ROOT / "deploy/site-overlay/salud/cuidados-paliativos/index.html").read_text())
    text = "".join(page.text); cursor = 0
    for block in data["blocks"]:
        parts = [block["text"]] if block["type"] == "paragraph" else [c["text"] for row in block["rows"] for c in row]
        for part in parts:
            at = text.find(part, cursor)
            assert at >= 0, "Texto faltante o fuera de orden: " + part
            cursor = at + len(part)
        runs = block.get("runs", []) if block["type"] == "paragraph" else [r for row in block["rows"] for c in row for p in c["paragraphs"] for r in p]
        for run in runs:
            if run.get("href"): assert run["href"] in page.links, run["href"]
    for link in page.links:
        if link.startswith("#"): assert link[1:] in page.ids, link
    assert len(page.ids) == len(set(page.ids)), "Anclas duplicadas"
    print("Texto íntegro y en orden, enlaces de fuentes y anclas: OK")

if __name__ == "__main__": main()
