'use strict';
// Executes the production JS in a minimal, network-free DOM. Does not edit it.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=process.argv[2]||__dirname;
const html=fs.readFileSync(path.join(root,'deploy/site-overlay/territorio/estructura-productiva/index.html'),'utf8');
let js=fs.readFileSync(path.join(root,'deploy/site-overlay/assets/estructura-productiva.js'),'utf8');
assert.match(js,/\}\)\(\);\s*$/);
js=js.replace(/\}\)\(\);\s*$/, 'globalThis.__qa={state,hydrate,renderEvolution};})();');
function verifyCase(actual){
const elements=new Map([...html.matchAll(/\bid=["']([^"']+)["']/g)].map(([,id])=>[id,{id,textContent:'',innerHTML:'',value:'',disabled:false,style:{},classList:{toggle(){}},addEventListener(){}}]));
const context={Intl,console,document:{addEventListener(){},querySelectorAll(){return []},getElementById(id){return elements.get(id)||null}},fetch(){throw Error('Network forbidden')}};
vm.createContext(context);vm.runInContext(js,context,{timeout:3000});
Object.assign(context.__qa.state,{actual,dyn:{anios:{}},manifest:{sectores:[]},mapData:{features:[]}});
context.__qa.hydrate();
const e=actual.panorama.ejes_comerciales,c=e.comparacion_interanual;
const nf=new Intl.NumberFormat('es-AR');
const pct=x=>Number(x).toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1})+'%';
const signed=x=>(x>0?'+':'')+Number(x).toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1});
assert.equal(elements.get('prod-kpi-shops').textContent,nf.format(e.locales_ocupados));
assert.equal(elements.get('prod-kpi-shops-sub').textContent,`48 ejes comerciales · C${e.periodo.cuatrimestre} ${e.periodo.anio}`);
assert.equal(elements.get('prod-kpi-rate').textContent,pct(e.tasa_ocupacion));
assert.equal(elements.get('prod-kpi-rate-sub').textContent,`${nf.format(e.locales_relevados)} locales relevados`);
assert.match(elements.get('prod-rubro-source').textContent,new RegExp(`${{1:'1er',2:'2do',3:'3er'}[e.periodo.cuatrimestre]} cuatrimestre de ${e.periodo.anio}`));
const summary=elements.get('prod-evolution-summary').innerHTML;
assert.ok(summary.includes(`${pct(c.tasa_ocupacion_desde)} → ${pct(e.tasa_ocupacion)}`),summary);
assert.ok(summary.includes(`${signed(c.variacion_total_pp)} p.p. interanual`),summary);
if(Object.values(e.comunas).every(x=>x.variacion_interanual_pp<0)) assert.ok(!summary.includes('Mayor mejora'),summary);
assert.equal(elements.get('prod-evolution-title').textContent,`Ocupación comercial ${c.desde.anio} → ${c.hasta.anio}`);
assert.ok(elements.get('prod-evolution').innerHTML.includes(`${c.desde.anio} C${c.desde.cuatrimestre}`));
assert.ok(elements.get('prod-evolution').innerHTML.includes(`${c.hasta.anio} C${c.hasta.cuatrimestre}`));
return {context,elements,summary};
}
const actual=JSON.parse(fs.readFileSync(path.join(root,'deploy/site-overlay/assets/data/estructura-productiva/actual.json')));
verifyCase(actual);
// Official historical C1 controls; they exercise binding, not regeneration.
const fixtures=JSON.parse(fs.readFileSync(path.join(root,'tests/fixtures/estructura_actual.json')));
const c1=structuredClone(actual),e1=c1.panorama.ejes_comerciales;
e1.periodo={anio:2026,cuatrimestre:1};e1.comunas=fixtures.original_c1_comunas;
e1.locales_ocupados=11605;e1.locales_relevados=12896;e1.tasa_ocupacion=90.0;
e1.comparacion_interanual={desde:{anio:2025,cuatrimestre:1},hasta:{anio:2026,cuatrimestre:1},tasa_ocupacion_desde:91.6,variacion_total_pp:-1.6};
assert.ok(verifyCase(c1).summary.includes('Mayor mejora'));
// Official C2 cell fixture exercises the next period without publishing a JSON.
const c2=structuredClone(actual),e2=c2.panorama.ejes_comerciales;
const sheet=title=>fixtures.indicadores.find(x=>x.title.trim()===title).rows;
const rows=sheet('2do. cuatr. de 2026'),previous=sheet('2do. cuatr. de 2025');
const r1=x=>Math.round(x*10)/10;
e2.periodo={anio:2026,cuatrimestre:2};
e2.locales_relevados=rows[2][1];e2.locales_ocupados=rows[2][2];e2.tasa_ocupacion=r1(rows[2][3]);
e2.comparacion_interanual={desde:{anio:2025,cuatrimestre:2},hasta:{anio:2026,cuatrimestre:2},tasa_ocupacion_desde:r1(previous[2][3]),variacion_total_pp:r1(rows[2][5])};
for(const row of rows.filter(x=>Number.isInteger(x[0])&&x[0]>=1&&x[0]<=15)){
 const old=previous.find(x=>x[0]===row[0]);
 e2.comunas[row[0]]={relevados:row[1],ocupados:row[2],tasa_ocupacion:r1(row[3]),variacion_interanual_pp:r1(row[5]),tasa_ocupacion_anterior:r1(old[3])};
}
const c2Summary=verifyCase(c2).summary;
assert.ok(c2Summary.includes('91,5% → 89,3%')&&c2Summary.includes('-2,2 p.p.'));
assert.ok(c2Summary.includes('Menor caída')&&!c2Summary.includes('Mayor mejora'));
// Deliberately synthetic UI-only inputs verify future periods and sign labels.
for(const delta of [-2.5,0,2.5]){
 const sample=structuredClone(actual),e=sample.panorama.ejes_comerciales;
 e.periodo={anio:2027,cuatrimestre:3};e.tasa_ocupacion=88.5+delta;
 e.comparacion_interanual={desde:{anio:2026,cuatrimestre:3},hasta:{anio:2027,cuatrimestre:3},tasa_ocupacion_desde:88.5,variacion_total_pp:delta};
 for(const row of Object.values(e.comunas)){row.variacion_interanual_pp=delta;row.tasa_ocupacion_anterior=88.5;row.tasa_ocupacion=88.5+delta;}
 const {summary}=verifyCase(sample);
 assert.ok(summary.includes(delta<0?'Menor caída':delta>0?'Mayor mejora':'Sin variación'));
}
const {context,elements}=verifyCase(actual);
context.__qa.state.actual.panorama.ejes_comerciales.comparacion_interanual.tasa_ocupacion_desde=null;
context.__qa.renderEvolution();
assert.equal(elements.get('prod-evolution-summary').innerHTML,'');
assert.ok(elements.get('prod-evolution').innerHTML.includes('no está disponible'));
console.log('Runtime UI: C1/C2, períodos futuros, signos y comparación ausente verificados sin red');
