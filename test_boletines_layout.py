"""Contract for compact newsletter covers, without network or browser dependencies."""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
tree = ast.parse((ROOT / "deploy/preparar_sitio_publico.py").read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compact_newsletter_hero")
namespace = {"re": re}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "compact_newsletter_hero", "exec"), namespace)
compact = namespace["compact_newsletter_hero"]

class NewsletterLayout(unittest.TestCase):
    def test_archive_and_future_legacy_template(self):
        pages = list((ROOT / "deploy/site-overlay/publicaciones/boletines").glob("*/index.html"))
        self.assertGreaterEqual(len(pages), 5)
        for path in pages:
            with self.subTest(edition=path.parent.name):
                source = path.read_text()
                self.assertIn('<details class="bol-sumario-toggle">', source)
                self.assertEqual(compact(source), source)
                self.assertNotIn('open', source.split('<details class="bol-sumario-toggle"', 1)[1].split('>', 1)[0])
                # Simulate a future edition copied from the old template.
                details = re.search(r'<details class="bol-sumario-toggle">.*?</details>', source, re.S)
                nav = re.search(r'<nav class="bol-sumario".*?</nav>', details.group(), re.S).group()
                legacy = source.replace(details.group(), '')
                cover = re.search(r'<img class="bol-hero__cover"[^>]*>', legacy).group()
                legacy = legacy.replace(cover, cover + nav, 1)
                result = compact(legacy)
                self.assertEqual(compact(result), result)
                self.assertEqual(source[source.index('<main>'):], result[result.index('<main>'):])
                self.assertEqual(sorted(re.findall(r'href="([^"]+)"', legacy)),
                                 sorted(re.findall(r'href="([^"]+)"', result)))
                hero = re.search(r'<header class="bol-hero">.*?</header>', result, re.S).group()
                self.assertEqual(hero.count('class="bol-sumario-toggle"'), 1)
                self.assertEqual(hero.count('class="bol-sumario"'), 1)

    def test_other_products_unchanged(self):
        source = '<article class="bol inf"><header>Informe</header><main>Contenido</main></article>'
        self.assertEqual(compact(source), source)

if __name__ == "__main__":
    unittest.main()
