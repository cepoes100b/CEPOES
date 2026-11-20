/** Prueba hermética de las fichas, descargas y respaldo generados en CI. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const INPUT = process.argv[2];
const ROOT = process.env.SITE_ROOT && path.resolve(process.env.SITE_ROOT);
const ORIGIN = (process.env.CEPOES_URL || 'https://cepoes.org').replace(/\/$/, '');
const FALLBACK = '/assets/data/datos.json';
const REMOTE = 'https://raw.githubusercontent.com/cepoes100b/CEPOES/HEAD/datos.json';
const spec = [
  ['Canasta', '/observatorio/precios/canasta-consumo/', 'canastas',
    ['meses','ca','caysh','total'], ['periodo','canasta_alimentaria_pesos','caysh_pesos','canasta_total_pesos']],
  ['IPC', '/observatorio/precios/ipc/', 'ipcba',
    ['meses','var_m','var_ia'], ['periodo','variacion_mensual_pct','variacion_interanual_pct']],
  ['Empleo', '/observatorio/trabajo/empleo/', 'empleo',
    ['trimestres','empleo','actividad','desocupacion'], ['periodo','empleo_pct','actividad_pct','desocupacion_pct']],
  ['Pobreza', '/observatorio/condiciones-de-vida/pobreza/', 'pobreza',
    ['periodos','pob_per_pct','ind_per_pct'], ['periodo','pobreza_personas_pct','indigencia_personas_pct']],
];
const money = n => '$ ' + Number(n).toLocaleString('es-AR',{ maximumFractionDigits: 0 });
const formatPct = (n, sign = false) => (sign && n > 0 ? '+' : '') +
  new Intl.NumberFormat('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1}).format(n) + '%';
const text = s => s.replace(/[\s\u00a0\u202f]+/g, ' ').trim();
function formatPeriod(p) {
  const mon = 'Enero Febrero Marzo Abril Mayo Junio Julio Agosto Septiembre Octubre Noviembre Diciembre'.split(' ');
  if (/^\d{4}-T[1-4]$/.test(p)) return [,'1.er','2.º','3.er','4.º'][Number(p.at(-1))]+' trimestre '+p.slice(0,4);
  if (/^\d{4}-\d{2}$/.test(p)) return mon[Number(p.slice(5)) - 1]+' '+p.slice(0,4);
  const index = 'Ene Feb Mar Abr May Jun Jul Ago Sep Oct Nov Dic'.split(' ').indexOf(p.slice(0,3));
  assert(index >= 0, 'período no reconocido: ' + p);
  return mon[index]+' 20'+p.slice(4);
}
function csv(raw) {
  assert(raw.charCodeAt(0) === 0xfeff, 'CSV debe conservar BOM para Excel');
  const [header,...rest] = raw.slice(1).trimEnd().split(/\r?\n/).map(line =>
    line.split(';').map(cell => cell.replace(/^"(.*)"$/, '$1')));
  return [header, rest.map(([p,...nums])=>[p,...nums.map(s=>{
    assert(/^[-+]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(s), 'dato no numérico: '+s);
    return Number(s);
  })])];
}
function views(name, rows) {
  const [period, ...v] = rows.at(-1);
  const m = name === 'Canasta' ? [money(v[2]),formatPct((v[2]/rows.at(-2)[3]-1)*100,true)] :
            name === 'IPC' ? [formatPct(v[1],true),formatPct(v[0],true)] :
            name === 'Empleo' ? [formatPct(v[0]),formatPct(v[2])] :
            [formatPct(v[0]),formatPct(v[1])];
  const rendered = rows.map(([period,...v]) =>
    [formatPeriod(period),...v.map(n=>name==='Canasta'?money(n):formatPct(n,name==='IPC'))]).reverse();
  return [formatPeriod(period), m, rendered];
}
async function main() {
  assert(INPUT, 'uso: node verificar_indicadores_browser.cjs datos.json');
  if (ROOT) assert.match(ORIGIN, /^http:\/\/127[.]0[.]0[.]1:[1-9][0-9]*$/, 'el candidato sólo puede usar loopback');
  const inputBytes = await fs.readFile(INPUT);
  const data = JSON.parse(inputBytes);
  const modes = process.env.CEPOES_QA_MODES?.split(',') || ['no-js','fallback','normal'];
  if (process.env.SCREENSHOTS) await fs.mkdir(process.env.SCREENSHOTS, {recursive:true});
  const launch = { headless: true };
  if (process.env.CHROMIUM_BIN) launch.executablePath = process.env.CHROMIUM_BIN;
  const browser = await chromium.launch(launch);
  try {
    for (const mode of modes) {
      assert(['no-js','fallback','normal'].includes(mode), 'modo desconocido: '+mode);
      const ctx = await browser.newContext({ javaScriptEnabled: mode!=='no-js', viewport: {width:390,height:844},
        acceptDownloads:true, serviceWorkers:'block' });
      try {
        let forced=0;
        await ctx.route('**/*', async r=>{
          const u = new URL(r.request().url());
          if (u.origin+u.pathname===REMOTE) {
            if (mode==='fallback') { forced++; return r.abort(); }
            if (ROOT) return r.fulfill({body:inputBytes,contentType:'application/json',
              headers:{'access-control-allow-origin':'*'}});
          }
          if (ROOT && u.origin===ORIGIN) return r.continue();
          if (ROOT && u.hostname==='cdn.jsdelivr.net' && process.env.CHART_JS && /\.js$/.test(u.pathname)) {
            return r.fulfill({body:await fs.readFile(process.env.CHART_JS),contentType:'application/javascript'});
          }
          if(ROOT) return r.abort(); // hermético: el build local no usa datos de producción
          return r.continue();
        });
        for (const [name, url, key, fields, header] of spec) {
          const d = data[key];
          const rows = d[fields[0]].map((p,i)=>[p,...fields.slice(1).map(k=>d[k][i])]);
          assert(d[fields[0]].length >= 2 && fields.every(k=>d[k].length===rows.length),name+': dataset inválido');
          const [period, metrics, rendered] = views(name,rows);
          const page = await ctx.newPage();
          let remoteHits=0, remoteOk=0, localHits=0;
          const forcedBefore=forced;
          page.on('request', r=>{const u=new URL(r.url()); if(u.origin+u.pathname===REMOTE)remoteHits++;});
          page.on('response', r=>{const u=new URL(r.url()); if(r.ok() && u.origin===ORIGIN && u.pathname===FALLBACK)localHits++; if(r.ok()&&u.origin+u.pathname===REMOTE)remoteOk++;});
          await page.goto(ORIGIN+url,{waitUntil:'domcontentloaded', timeout:45000});
          const link=page.locator('#indicator-download');
          if(mode!=='no-js')await page.waitForFunction(()=>document.getElementById('indicator-download')?.href.startsWith('blob:'),null,{timeout:25000});
          assert.equal(text(await page.locator('#indicator-primary-period').innerText()),period, name+' '+mode+' período');
          assert.deepEqual(await Promise.all(['primary','secondary'].map(async k=>text(await page.locator('#indicator-'+k+'-value').innerText()))),metrics,name+' '+mode+' valores');
          assert.equal(text(await page.locator('#indicator-meta-period').innerText()),period,name+' '+mode+' método/último');
          assert.equal(text(await page.locator('#indicator-meta-first').innerText()),formatPeriod(rows[0][0]),name+' '+mode+' método/primero');
          if (mode === 'no-js') assert(!/cargando/i.test(await page.locator('#data-date').innerText()),name+' sigue anunciando carga sin JS');
          if (name === 'Pobreza') {
            const people = d.pob_per_abs.at(-1).toLocaleString('es-AR');
            assert.equal(text(await page.locator('#indicator-secondary-note').innerText()),people+' personas bajo la línea de pobreza',mode+' Pobreza cobertura');
          }
          const reading = text(await page.locator('#indicator-reading').innerText());
          if(name==='IPC' && period==='Octubre 2026')assert(/disminuyó 0,4 p\.p/.test(reading),mode+' IPC: la lectura de la interanual debe coincidir con la variación en p.p.');
          const table=await page.locator('#indicator-table tbody tr').evaluateAll(trs=>trs.map(tr=>[...tr.cells].map(c=>c.textContent.replace(/\s+/g,' ').trim())));
          assert.deepEqual(table,rendered,name+' '+mode+' tabla completa');
          if (mode!=='no-js' && process.env.REQUIRE_CHART) {
            const chartSize = await page.locator('#indicator-chart').evaluate(el=>globalThis.Chart?.getChart(el)?.data.labels.length);
            assert.equal(chartSize,rows.length,name+' '+mode+' gráfico desactualizado o ausente');
          }
          const rawLink=await link.getAttribute('href');
          assert(mode==='no-js' ? new URL(rawLink,ORIGIN+url).href===ORIGIN+url+'datos.csv' : rawLink.startsWith('blob:'),name+' '+mode+' enlace');
          if (mode==='no-js')assert.equal(remoteHits+localHits,0,'sin JS no debe consultar JSON');
          if (mode==='fallback'){
            assert(remoteHits>=1 && forced>forcedBefore && remoteOk===0 && localHits>=1,name+' fallback no demostrado');
            assert((await page.locator('#data-date').innerText()).includes('respaldo local'),name+' fallback no identificado');
          }
          if (mode==='normal')assert(remoteHits>=1 && remoteOk>=1 && localHits===0,name+' no usó fuente remota');
          const downloadEvent = page.waitForEvent('download',{timeout:15000});
          await link.click({timeout:10000});
          const download = await downloadEvent;
          if (ROOT) {
            if (mode==='no-js') assert.equal(download.url(),ORIGIN+url+'datos.csv',name+' CSV fuera del candidato');
            else assert(download.url().startsWith('blob:'+ORIGIN+'/'),name+' CSV blob fuera del candidato');
          }
          const bytes = await fs.readFile(await download.path(),'utf8');
          assert.deepEqual(csv(bytes),[header,rows],name+' '+mode+' CSV completo');
          if(mode!=='no-js'){
            const toggle = page.locator('#indicator-table-toggle');
            await toggle.click({timeout:10000});
            assert.equal(await toggle.getAttribute('aria-expanded'),'true',name+' '+mode+' mostrar serie');
            await toggle.click({timeout:10000});
            assert.equal(await toggle.getAttribute('aria-expanded'),'false',name+' '+mode+' ocultar serie');
          }
          if(process.env.SCREENSHOTS){
            await page.locator('#indicator-primary-value').scrollIntoViewIfNeeded();
            await page.screenshot({path:path.join(process.env.SCREENSHOTS,mode+'-'+name+'.png')});
          }
          console.log(name, mode, period, metrics.join(' | '), rows.length+' CSV/tabla');
          await page.close();
        }
      } finally { await ctx.close(); }
    }
  } finally { await browser.close(); }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
