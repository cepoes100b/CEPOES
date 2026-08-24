(function(){
'use strict';
const BASE='/assets/data/estructura-productiva/';
const nf=new Intl.NumberFormat('es-AR');
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state={actual:null,dyn:null,manifest:null,mapData:null,map:null,layer:null,mode:'actual',year:'',comuna:'',cache:new Map(),selected:null};
document.addEventListener('DOMContentLoaded',init);

async function json(url){const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw new Error(`${url}: ${r.status}`);return r.json()}
function date(s){try{return new Intl.DateTimeFormat('es-AR',{day:'2-digit',month:'short',year:'numeric'}).format(new Date(s))}catch(e){return s||'—'}}
function pct(v){return Number(v||0).toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1})+'%'}

async function init(){
  try{
    const [actual,dyn,manifest,mapData]=await Promise.all([json(BASE+'actual.json'),json(BASE+'dinamica.json'),json(BASE+'manifest.json'),json(BASE+'mapa.json')]);
    Object.assign(state,{actual,dyn,manifest,mapData});
    hydrate();buildTabs();buildYear();initMap();renderCurrent();
  }catch(err){
    console.error(err);$('prod-status').textContent='No pudimos cargar el conjunto completo de datos. CEPOES no publica una combinación parcial de fuentes.';
    $('prod-selection').innerHTML='<span class="eyebrow">Estado</span><h3>Datos temporalmente no disponibles</h3><p>La última versión validada se conserva hasta que todas las fuentes y controles estén disponibles.</p>';
  }
}

function hydrate(){
  const o=state.actual.panorama.empresas_registradas,e=state.actual.panorama.ejes_comerciales;
  $('prod-kpi-companies').textContent=nf.format(o.empresas);$('prod-kpi-companies-sub').textContent=`OEDE/SIPA · ${o.periodo}`;
  $('prod-kpi-shops').textContent=nf.format(e.locales_ocupados);$('prod-kpi-shops-sub').textContent=`48 ejes comerciales · ${e.periodo.anio}`;
  $('prod-kpi-rate').textContent=pct(e.tasa_ocupacion);$('prod-kpi-rate-sub').textContent=`${nf.format(e.locales_relevados)} locales relevados`;
  const total=Object.values(state.dyn.anios||{}).reduce((a,x)=>a+(+x.total||0),0);
  $('prod-kpi-flow').textContent=nf.format(total);$('prod-kpi-flow-sub').textContent='habilitaciones aprobadas · 2024–2026';
  $('prod-generated').textContent=date(state.actual.generado);
  renderCompanySectors();renderComunaCards();renderRubros();renderFlowYears();
}

function renderCompanySectors(){
  const items=state.actual.panorama.empresas_registradas.sectores.slice(0,9),max=Math.max(...items.map(x=>x.empresas),1);
  $('prod-company-bars').innerHTML=items.map(x=>bar(x.sector,x.empresas,max)).join('');
}
function bar(label,n,max){return `<div class="productive-bar-row"><span>${esc(label)}</span><div class="productive-bar-track"><div class="productive-bar-fill" style="width:${(n/max*100).toFixed(1)}%"></div></div><b>${nf.format(n)}</b></div>`}

function renderComunaCards(){
  const c=state.actual.panorama.ejes_comerciales.comunas;
  $('prod-comuna-cards').innerHTML=Object.entries(c).map(([id,x])=>`<button type="button" class="productive-comuna-card ${state.comuna===id?'active':''}" data-current-comuna="${id}"><span>Comuna ${id}</span><strong>${pct(x.tasa_ocupacion)}</strong><small>${nf.format(x.ocupados)} ocupados / ${nf.format(x.relevados)} relevados</small></button>`).join('');
  $('prod-comuna-cards').onclick=e=>{const b=e.target.closest('[data-current-comuna]');if(!b)return;state.comuna=b.dataset.currentComuna;renderComunaCards();renderRubros();renderCurrentSelection();if(state.mode==='actual'){refreshMap();zoomComuna(+state.comuna)}};
}

function renderRubros(){
  const e=state.actual.panorama.ejes_comerciales,items=e.rubros.map(r=>({label:r.rubro,n:state.comuna?(+r.comunas[state.comuna]||0):r.total})).filter(x=>x.n>0).sort((a,b)=>b.n-a.n).slice(0,12),max=Math.max(...items.map(x=>x.n),1);
  $('prod-rubro-title').textContent=state.comuna?`Rubros en Comuna ${state.comuna}`:'Rubros en los 48 ejes comerciales';
  $('prod-rubro-bars').innerHTML=items.map(x=>bar(x.label,x.n,max)).join('');
}

function renderFlowYears(){
  const years=Object.entries(state.dyn.anios||{}).sort(([a],[b])=>a.localeCompare(b));
  $('prod-flow-years').innerHTML=years.map(([y,x])=>`<div class="productive-flow-year"><span>${y}</span><strong>${nf.format(x.total||0)}</strong><span>${pct((+x.precision_manzana||0)*100)} con manzana exacta</span></div>`).join('');
}

function buildTabs(){document.querySelectorAll('[data-prod-layer]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.prodLayer)))}
function setMode(mode){if(!['actual','flow','historical'].includes(mode))return;state.mode=mode;state.selected=null;document.querySelectorAll('[data-prod-layer]').forEach(b=>b.classList.toggle('active',b.dataset.prodLayer===mode));$('prod-year-field').style.display=mode==='flow'?'flex':'none';renderModeNote();refreshMap();renderEmpty();}
function buildYear(){const s=$('prod-year');s.innerHTML='<option value="">2024–2026</option>'+Object.keys(state.dyn.anios||{}).sort().map(y=>`<option value="${y}">${y}</option>`).join('');s.addEventListener('change',()=>{state.year=s.value;refreshMap();renderEmpty()})}
function renderModeNote(){
  const n=$('prod-layer-note');
  if(state.mode==='actual')n.innerHTML='<b>Actual · resolución comuna.</b> El color representa la tasa de ocupación comercial 2026 en 48 ejes. Las manzanas se usan sólo como soporte cartográfico para dibujar cada comuna.';
  if(state.mode==='flow')n.innerHTML='<b>Dinámica reciente · precisión variable.</b> Habilitaciones aprobadas 2024–2026. Sólo se ubican a manzana los registros que traen esa clave territorial.';
  if(state.mode==='historical')n.innerHTML='<b>Histórico · resolución manzana.</b> RUS 2017. Es la última base detallada validada y no se presenta como fotografía vigente.';
}

function initMap(){
  if(!window.L)throw new Error('Leaflet no disponible');
  state.map=L.map('productive-map',{zoomControl:true,minZoom:10,maxZoom:19,preferCanvas:true}).setView([-34.615,-58.445],11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(state.map);
  state.layer=L.geoJSON(state.mapData,{style:styleFeature,onEachFeature:onFeature}).addTo(state.map);
  if(state.layer.getBounds().isValid())state.map.fitBounds(state.layer.getBounds(),{padding:[12,12]});
}

function currentValue(f){const c=String(f.properties?.c||'');return state.actual.panorama.ejes_comerciales.comunas[c]?.tasa_ocupacion||0}
function flowEvents(sm){const e=state.dyn.manzanas?.[sm]?.e||[];return state.year?e.filter(x=>String(x[0])===state.year):e}
function historicalValue(f){return +f.properties?.t||0}
function styleFeature(f){
  const p=f.properties||{};
  if(state.mode==='actual'){
    const v=currentValue(f),min=84,max=97,t=Math.max(0,Math.min(1,(v-min)/(max-min))),selected=state.comuna&&String(p.c)===state.comuna;
    return{weight:selected?1.25:.22,color:selected?'#62172b':'#74808a',fillColor:'#b32645',fillOpacity:.12+t*.66,opacity:selected?.9:.18};
  }
  if(state.mode==='flow'){
    const n=flowEvents(p.sm).length;if(!n)return{weight:.25,color:'#7d8790',fillColor:'#bfc6cc',fillOpacity:.02,opacity:.14};
    return{weight:.5,color:'#8b5a13',fillColor:'#d98b2b',fillOpacity:Math.min(.86,.16+Math.log1p(n)/Math.log(18)*.62),opacity:.58};
  }
  const n=historicalValue(f);if(!n)return{weight:.2,color:'#78828c',fillColor:'#bfc6cc',fillOpacity:.02,opacity:.12};
  return{weight:.45,color:'#76233a',fillColor:'#b32645',fillOpacity:Math.min(.84,.12+Math.log1p(n)/Math.log(60)*.62),opacity:.55};
}
function onFeature(f,l){l.bindTooltip(()=>tooltip(f),{sticky:true});l.on('click',()=>selectFeature(f,l))}
function tooltip(f){const p=f.properties||{};
  if(state.mode==='actual'){const x=state.actual.panorama.ejes_comerciales.comunas[String(p.c)];return `<div class="productive-tooltip"><strong>Comuna ${esc(p.c)}</strong><small>${pct(x?.tasa_ocupacion)} ocupación · dato comunal 2026</small></div>`}
  if(state.mode==='flow'){return `<div class="productive-tooltip"><strong>${esc(p.b||'Manzana')} · Comuna ${esc(p.c)}</strong><small>${nf.format(flowEvents(p.sm).length)} habilitaciones localizadas${state.year?' · '+esc(state.year):''}</small></div>`}
  return `<div class="productive-tooltip"><strong>${esc(p.b||'Manzana')} · Comuna ${esc(p.c)}</strong><small>${nf.format(p.t||0)} actividades RUS 2017 · SM ${esc(p.sm)}</small></div>`
}
function refreshMap(){if(state.layer)state.layer.setStyle(styleFeature);updateStatus();renderModeNote()}
function updateStatus(){
  if(state.mode==='actual'){$('prod-status').textContent=(state.comuna?`Comuna ${state.comuna}`:'CABA')+' · tasa de ocupación comercial · 1er cuatrimestre 2026 · resolución comuna';$('prod-legend').textContent='Tasa de ocupación';return}
  if(state.mode==='flow'){let m=0,n=0;for(const f of state.mapData.features){const x=flowEvents(f.properties?.sm).length;if(x){m++;n+=x}}$('prod-status').textContent=`${state.year||'2024–2026'} · ${nf.format(m)} manzanas · ${nf.format(n)} habilitaciones localizadas`;$('prod-legend').textContent='Habilitaciones por manzana';return}
  let m=0,n=0;for(const f of state.mapData.features){const x=historicalValue(f);if(x){m++;n+=x}}$('prod-status').textContent=`RUS 2017 · ${nf.format(m)} manzanas · ${nf.format(n)} actividades relevadas`;$('prod-legend').textContent='Actividades por manzana';
}

function zoomComuna(c){const xs=[];state.layer.eachLayer(l=>{if(+l.feature?.properties?.c===c)xs.push(l)});if(xs.length)state.map.fitBounds(L.featureGroup(xs).getBounds(),{padding:[20,20]})}
async function selectFeature(f,l){const p=f.properties||{};state.selected=p.sm;if(state.mode==='actual'){state.comuna=String(p.c);renderComunaCards();renderRubros();renderCurrentSelection();refreshMap();zoomComuna(+p.c);return}state.map.fitBounds(l.getBounds(),{padding:[40,40],maxZoom:16});if(state.mode==='flow')renderFlowSelection(f);else await renderHistoricalSelection(f)}

function renderCurrent(){renderModeNote();renderCurrentSelection();updateStatus()}
function renderCurrentSelection(){
  const e=state.actual.panorama.ejes_comerciales;if(!state.comuna){$('prod-selection').innerHTML='<span class="eyebrow">Actividad comercial actual</span><h3>Elegí una comuna</h3><p>El mapa compara la tasa de ocupación de locales en 48 ejes comerciales relevados por IDECBA. El dato es comunal; no asignamos a cada manzana un valor que la fuente no mide.</p>';return}
  const x=e.comunas[state.comuna],top=e.rubros.map(r=>[r.rubro,+r.comunas[state.comuna]||0]).filter(x=>x[1]).sort((a,b)=>b[1]-a[1]).slice(0,6);
  $('prod-selection').innerHTML=`<span class="eyebrow">Actual · Comuna ${state.comuna}</span><h3>${pct(x.tasa_ocupacion)} de ocupación comercial</h3><div class="selection-meta">${nf.format(x.ocupados)} locales ocupados de ${nf.format(x.relevados)} relevados · 1er cuatrimestre de 2026</div><div class="productive-sector-pills">${top.map(([r,n])=>`<span class="productive-sector-pill"><b>${nf.format(n)}</b> ${esc(r)}</span>`).join('')}</div><p class="source">Universo: 48 ejes comerciales de alta densidad. No equivale al total de locales de la comuna.</p>`;
}
function renderFlowSelection(f){const p=f.properties||{},all=flowEvents(p.sm);$('prod-selection').innerHTML=`<span class="eyebrow">Dinámica reciente · manzana</span><h3>${esc(p.b||'')} · Comuna ${esc(p.c)}</h3><div class="selection-meta">SM ${esc(p.sm)} · ${nf.format(all.length)} habilitaciones localizadas ${state.year||'2024–2026'}</div><p class="source">Flujo administrativo: una habilitación aprobada no demuestra que el establecimiento continúe activo hoy.</p><div class="productive-place-list">${all.slice(0,120).map(e=>`<div class="productive-place"><strong>${esc(e[2]||e[3]||'Habilitación')}</strong><small>${esc([e[3],e[4]].filter(Boolean).join(' · '))}</small><small>${esc([e[1],e[0]].filter(Boolean).join(' · '))}</small></div>`).join('')||'<div class="productive-empty">Sin registros para el filtro actual.</div>'}</div>`}
async function historicalData(c){if(state.cache.has(c))return state.cache.get(c);const d=await json(BASE+`comuna-${String(c).padStart(2,'0')}.json`);state.cache.set(c,d);return d}
async function renderHistoricalSelection(f){const p=f.properties||{},d=await historicalData(+p.c),b=d.manzanas?.[p.sm];if(!b){renderEmpty();return}const sectors=Object.entries(b.s||{}).sort((a,b)=>b[1]-a[1]).slice(0,6);$('prod-selection').innerHTML=`<span class="eyebrow">Histórico · RUS 2017 · manzana</span><h3>${esc(b.b||p.b||'')} · Comuna ${p.c}</h3><div class="selection-meta">SM ${esc(p.sm)} · ${nf.format(b.t||0)} actividades relevadas</div><div class="productive-sector-pills">${sectors.map(([id,n])=>`<span class="productive-sector-pill"><b>${nf.format(n)}</b> ${esc(state.manifest.sectores.find(x=>x.id===id)?.nombre||id)}</span>`).join('')}</div><div class="productive-place-list">${(b.e||[]).slice(0,100).map(e=>`<div class="productive-place"><strong>${esc(e[0]||e[6]||e[5]||'Actividad económica')}</strong><small>${esc(e[7]||e[6]||e[5]||'')}</small><small>${esc([e[1],e[2]].filter(Boolean).join(' '))}</small></div>`).join('')}</div><p class="source">Esta capa describe la estructura relevada en 2017. Se conserva por su resolución territorial y no se usa como stock vigente.</p>`}
function renderEmpty(){if(state.mode==='actual')return renderCurrentSelection();if(state.mode==='flow')$('prod-selection').innerHTML='<span class="eyebrow">Dinámica reciente</span><h3>Elegí una manzana</h3><p>Se muestran únicamente habilitaciones que la fuente permite localizar con sección–manzana.</p>';else $('prod-selection').innerHTML='<span class="eyebrow">Histórico · RUS 2017</span><h3>Elegí una manzana</h3><p>Explorá la composición económica del relevamiento histórico. Esta capa no representa la estructura vigente.</p>'}
})();