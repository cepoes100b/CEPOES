import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const root = new URL('../', import.meta.url);
const read = path => readFileSync(new URL(path, root), 'utf8');
const target = 'ley-peridural-12-maternidades-publicas-seguimiento';
const notice = 'Actualización del 9/10/2026: la Ley 6.976, publicada el 5 de octubre, prevé implementación progresiva y condiciones de disponibilidad sujetas a reglamentación. No incluye la exigencia literal de atención las 24 horas, los 365 días. Los plazos de 30 días para su entrada en vigencia y 90 días para reglamentarla se cuentan desde su publicación en el Boletín Oficial.';

test('schooling renders years; activity and poverty retain percentages and bar values', () => {
  const D = JSON.parse(read('deploy/site-overlay/assets/data/migraciones.json'));
  const original = JSON.stringify(D);
  const elements = {};
  const document = { getElementById: id => elements[id] ||= {} };
  const source = read('deploy/site-overlay/assets/migraciones.js');
  // Execute the actual comparison renderer and all three production call sites.
  const section = source.slice(source.indexOf('  function compareBars('), source.indexOf('  const updated='));
  const n1 = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  vm.runInNewContext(section, { D, document, n1, pct: v => n1.format(v) + '%', set: () => {} });
  for (const [id, key, unit] of [['schooling', 'schooling', ' años'], ['activity', 'activity', '%'], ['poverty', 'poverty_multidimensional', '%']]) {
    const html = elements[`mig-${id}-bars`].innerHTML;
    const values = Object.values(D.socioeconomic[key].values);
    assert.deepEqual([...html.matchAll(/<strong>(.*?)<\/strong>/g)].map(m => m[1]), values.map(v => n1.format(v) + unit));
    assert.deepEqual([...html.matchAll(/style="width:(.*?)%"/g)].map(m => Number(m[1])), values.map(v => v / Math.max(...values) * 100));
  }
  assert.equal(JSON.stringify(D), original);
});

async function render(slug, available = true) {
  // Synthetic editorial fixture, not a copy of the published historical note.
  const note = { slug, title: 'Título histórico <original>', summary: 'Bajada histórica intacta', body: ['Texto histórico intacto'], first_published_at: '2026-08-27T12:00:00Z', published_at: '2026-08-27T12:00:00Z', topic: 'Salud', source_label: 'Fuente original', source_section: '/observatorio/', tags: [], facts: [] };
  const before = JSON.stringify(note);
  const elements = {};
  const document = { body: { dataset: {} }, getElementById: id => elements[id] ||= {} };
  vm.runInNewContext(read('deploy/site-overlay/assets/prensa-nota.js'), {
    document, location: { search: '?slug=' + slug }, URLSearchParams,
    fetch: async url => ({ ok: true, json: async () => url.includes('select=*') && available ? [note] : [] })
  });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(JSON.stringify(note), before);
  return elements.article.innerHTML;
}

test('historical notice is exact, linked, and between title and original summary', async () => {
  const html = await render(target);
  assert.equal(html.split(notice).length - 1, 1);
  assert.ok(html.indexOf('</h1>') < html.indexOf(notice));
  assert.ok(html.indexOf(notice) < html.indexOf('Bajada histórica intacta'));
  assert.match(html, /27 de agosto de 2026/);
  assert.match(html, /Texto histórico intacto/);
  assert.match(html, /Título histórico &lt;original&gt;/);
  assert.ok(html.includes('href="https://boletinoficial.buenosaires.gob.ar/normativaba/norma/880789"'));
  assert.ok(html.includes('href="https://cepoes.org/legislatura/seguimiento/analgesia-peridural/"'));
});

test('other slugs receive no notice, including near matches', async () => {
  for (const slug of ['el-dolor-tambien-es-desigual', target + '-otra', 'otra-nota']) {
    assert.ok(!(await render(slug)).includes('press-historical-notice'));
  }
});

test('unavailable historical note stays unavailable without manufacturing a fallback', async () => {
  const html = await render(target, false);
  assert.match(html, /Nota no disponible/);
  assert.ok(!html.includes(notice));
});
