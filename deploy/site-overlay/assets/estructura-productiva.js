(function(){
'use strict';
const BASE='/assets/data/estructura-productiva/';
const COMUNAS_URL='https://cdn.buenosaires.gob.ar/datosabiertos/datasets/innovacion-transformacion-digital/comunas/comunas.geojson';
const nf=new Intl.NumberFormat('es-AR');
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=(v,d=1)=>Number(v||0).toLocaleString('es-AR',{minimumFractionDigits:d,maximumFractionDigits:d})+'%';
const signed=(v,d=1)=>`${v>0?'+':''}${Number(v||0).toLocaleString('es-AR',{minimumFractionDigits:d,maximumFractionDigits:d})}`;
const state={actual:null,dyn:null,manifest:null,mapData:null,communes:null,map:null,communeLayer:null,labelLayer:null,metric:'ocupacion',rubro:'',selected:'',compare:['1','7'],detailMap:null,detailLayer:null,detailMode:'flow',year:'',cache:new Map()};
document.addEventListener('DOMContentLoaded',init);

async function json(url){const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw new Error(`${url}: ${r.status}`);return r.json()}
function date(s){try{return new Intl.DateTimeFormat('es-AR',{day:'2-digit',month:'short',year:'numeric'}).format(new Date(s))}catch(e){return s||'—'}}
function ejes(){return state.actual.panorama.ejes_comerciales}
function rubros(){return ejes().rubros}
function comuna(id){return ejes().comunas[String(id)]}
function rubroObj(name){return rubros().find(x=>x.rubro===name)}
function rubroCount(name,id){const r=rubroObj(name);return r?+(r.comunas?.[String(id)]||0):0}
function cityShare(name){const r=rubroObj(name);return r&&ejes().locales_ocupados?100*r.total/ejes().locales_ocupados:0}
function communeShare(name,id){const c=comuna(id);return c?.ocupados?100*rubroCount(name,id)/c.ocupados:0}
function specialization(name,id){const city=cityShare(name);return city?communeShare(name,id)/city:0}

async function init(){
  try{
    const [actual,dyn,manifest,mapData,communes]=await Promise.all([json(BASE+'actual.json'),json(BASE+'dinamica.json'),json(BASE+'manifest.json'),json(BASE+'mapa.json'),json(COMUNAS_URL)]);
    Object.assign(state,{actual,dyn,manifest,mapData,communes});
    state.rubro=rubros()[0]?.rubro||'';
    hydrate();initAnalyticMap();initDetailMap();
  }catch(err){
    console.error(err);
    ['prod-map-status','prod-detail-status'].forEach(id=>{if($(id))$(id).textContent='No pudimos cargar el conjunto completo de datos. Se conserva la última versión validada.'});
  }
}

function hydrate(){
  const o=state.actual.panorama.empresas_registradas,e=ejes();
  $('prod-kpi-companies').textContent=nf.format(o.empresas);$('prod-kpi-companies-sub').textContent=`OEDE/SIPA · ${o.periodo}`;
  $('prod-kpi-shops').textContent=nf.format(e.locales_ocupados);$('prod-kpi-shops-sub').textContent=`48 ejes comerciales · ${e.periodo.anio}`;
  $('prod-kpi-rate').textContent=pct(e.tasa_ocupacion);$('prod-kpi-rate-sub').textContent=`${nf.format(e.locales_relevados)} locales relevados`;
  const total=Object.values(state.dyn.anios||{}).reduce((a,x)=>a+(+x.total||0),0);
  $('prod-kpi-flow').textContent=nf.format(total);$('prod-kpi-flow-sub').textContent='habilitaciones aprobadas · 2024–2026';
  $('prod-generated').textContent=date(state.actual.generado);
  renderCompanySectors();renderCityRubros();buildAnalyticControls();renderCompareSelector();renderComparison();renderMatrix();renderEvolution();buildDetailControls();renderFlowYears();
}

function bar(label,n,max,formatter=nf.format.bind(nf)){return `<div class="productive-bar-row"><span>${esc(label)}</span><div class="productive-bar-track"><div class="productive-bar-fill" style="width:${(n/max*100).toFixed(1)}%"></div></div><b>${formatter(n)}</b></div>`}
function renderCompanySectors(){const items=state.actual.panorama.empresas_registradas.sectores.slice(0,9),max=Math.max(...items.map(x=>x.empresas),1);$('prod-company-bars').innerHTML=items.map(x=>bar(x.sector,x.empresas,max)).join('')}
function renderCityRubros(){const items=rubros().slice().sort((a,b)=>b.total-a.total).slice(0,10),max=Math.max(...items.map(x=>x.total),1);$('prod-city-rubro-bars').innerHTML=items.map(x=>bar(x.rubro,x.total,max)).join('')}

function buildAnalyticControls(){
  const rs=$('prod-map-rubro');rs.innerHTML=rubros().slice().sort((a,b)=>b.total-a.total).map(r=>`<option value="${esc(r.rubro)}">${esc(r.rubro)}</option>`).join('');rs.value=state.rubro;
  rs.addEventListener('change',()=>{state.rubro=rs.value;refreshAnalyticMap();renderProfile(state.selected);renderRanking()});
  const ms=$('prod-map-metric');ms.value=state.metric;ms.addEventListener('change',()=>{state.metric=ms.value;toggleRubroControl();refreshAnalyticMap();renderProfile(state.selected);renderRanking()});
  toggleRubroControl();renderRanking();
}
function toggleRubroControl(){const disabled=state.metric==='ocupacion';$('prod-map-rubro').disabled=disabled;$('prod-map-rubro-field').classList.toggle('disabled',disabled)}
function metricValue(id){
  const c=comuna(id);if(!c)return 0;
  if(state.metric==='ocupacion')return +c.tasa_ocupacion||0;
  if(state.metric==='cantidad')return rubroCount(state.rubro,id);
  if(state.metric==='participacion')return communeShare(state.rubro,id);
  return specialization(state.rubro,id);
}
function metricLabel(){
  if(state.metric==='ocupacion')return 'Tasa de ocupación comercial';
  if(state.metric==='cantidad')return `Locales · ${state.rubro}`;
  if(state.metric==='participacion')return `Participación · ${state.rubro}`;
  return `Especialización relativa · ${state.rubro}`;
}
function metricFormat(v){if(state.metric==='ocupacion'||state.metric==='participacion')return pct(v);if(state.metric==='especializacion')return `${Number(v).toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2})}×`;return nf.format(Math.round(v))}

function initAnalyticMap(){
  if(!window.L)throw new Error('Leaflet no disponible');
  state.map=L.map('productive-map',{zoomControl:true,minZoom:10,maxZoom:15,preferCanvas:true,scrollWheelZoom:false}).setView([-34.615,-58.445],11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(state.map);
  state.labelLayer=L.layerGroup().addTo(state.map);
  state.communeLayer=L.geoJSON(state.communes,{style:analyticStyle,onEachFeature:(f,l)=>{l.bindTooltip(()=>analyticTooltip(f),{sticky:true});l.on('click',()=>selectComuna(featureComuna(f),true))}}).addTo(state.map);
  addCommuneLabels();
  if(state.communeLayer.getBounds().isValid())state.map.fitBounds(state.communeLayer.getBounds(),{padding:[12,12]});
  refreshAnalyticMap();selectComuna('1',false);
}
function featureComuna(f){return String(f.properties?.comuna??f.properties?.COMUNA??f.properties?.id??'')}
function addCommuneLabels(){state.labelLayer.clearLayers();state.communeLayer.eachLayer(l=>{const id=featureComuna(l.feature);if(!id)return;const center=l.getBounds().getCenter();L.marker(center,{interactive:false,icon:L.divIcon({className:'productive-comuna-label',html:`<span>C${esc(id)}</span>`,iconSize:[34,24],iconAnchor:[17,12]})}).addTo(state.labelLayer)})}
function analyticStyle(f){
  const id=featureComuna(f),v=metricValue(id),selected=state.selected===id,comp=state.compare.includes(id);
  let fill='#b32645',opacity=.5;
  if(state.metric==='especializacion'){
    if(v<.75){fill='#75838d';opacity=.48}else if(v<1){fill='#b4a27c';opacity=.52}else if(v<1.25){fill='#d9a14a';opacity=.58}else if(v<1.75){fill='#c65363';opacity=.7}else{fill='#8f1933';opacity=.82}
  }else{
    const vals=Object.keys(ejes().comunas).map(metricValue),min=Math.min(...vals),max=Math.max(...vals);opacity=max===min?.58:.25+.62*((v-min)/(max-min));
  }
  return{weight:selected?4:comp?2.8:1.8,color:selected?'#16232f':comp?'#8f1933':'#ffffff',fillColor:fill,fillOpacity:opacity,opacity:1};
}
function analyticTooltip(f){const id=featureComuna(f),c=comuna(id);return `<div class="productive-tooltip"><strong>Comuna ${esc(id)}</strong><small>${esc(metricLabel())}: ${esc(metricFormat(metricValue(id)))}</small><small>${nf.format(c?.ocupados||0)} locales ocupados en los ejes relevados</small></div>`}
function refreshAnalyticMap(){if(!state.communeLayer)return;state.communeLayer.setStyle(analyticStyle);renderLegend();renderMapStatus();renderRanking()}
function renderLegend(){
  const el=$('prod-map-legend');if(state.metric==='especializacion'){
    el.innerHTML='<strong>Índice de especialización</strong><div class="productive-legend-cats"><span><i data-c="1"></i>&lt;0,75×</span><span><i data-c="2"></i>0,75–0,99×</span><span><i data-c="3"></i>1,00–1,24×</span><span><i data-c="4"></i>1,25–1,74×</span><span><i data-c="5"></i>≥1,75×</span></div>';return;
  }
  const vals=Object.keys(ejes().comunas).map(metricValue),min=Math.min(...vals),max=Math.max(...vals);el.innerHTML=`<strong>${esc(metricLabel())}</strong><div class="productive-legend-scale"></div><div class="productive-legend-range"><span>${esc(metricFormat(min))}</span><span>${esc(metricFormat(max))}</span></div>`;
}
function renderMapStatus(){$('prod-map-status').textContent=`15 comunas · ${metricLabel()} · IDECBA ${ejes().periodo.anio} · 48 ejes comerciales`}
function selectComuna(id,zoom){state.selected=String(id);refreshAnalyticMap();renderProfile(state.selected);if(zoom){state.communeLayer.eachLayer(l=>{if(featureComuna(l.feature)===state.selected)state.map.fitBounds(l.getBounds(),{padding:[35,35],maxZoom:13})})}}

function rankFor(id,fn,desc=true){const xs=Object.keys(ejes().comunas).map(c=>[c,fn(c)]).sort((a,b)=>desc?b[1]-a[1]:a[1]-b[1]);return 1+xs.findIndex(x=>x[0]===String(id))}
function profileData(id){
  const c=comuna(id);if(!c)return null;
  const sectors=rubros().map(r=>({name:r.rubro,n:rubroCount(r.rubro,id),share:communeShare(r.rubro,id),spec:specialization(r.rubro,id)})).filter(x=>x.n>0);
  const top=sectors.slice().sort((a,b)=>b.n-a.n),spec=sectors.filter(x=>cityShare(x.name)>=1).sort((a,b)=>b.spec-a.spec);
  return{c,top,spec,top3:top.slice(0,3).reduce((a,x)=>a+x.share,0),rateDiff:c.tasa_ocupacion-ejes().tasa_ocupacion,rank:rankFor(id,x=>comuna(x).tasa_ocupacion)};
}
function renderProfile(id){
  const el=$('prod-selection');if(!id){el.innerHTML='<span class="eyebrow">Perfil comunal</span><h3>Elegí una comuna</h3><p>El mapa trabaja con los límites administrativos reales de las 15 comunas.</p>';return}
  const p=profileData(id),top=p.top[0],spec=p.spec[0];
  el.innerHTML=`<span class="eyebrow">Comuna ${esc(id)} · perfil comercial 2026</span><h3>${esc(top?.name||'Perfil comercial')}</h3><p class="productive-insight">${top?`El principal rubro representa <b>${pct(top.share)}</b> de los locales ocupados relevados.`:''} ${spec?`La mayor especialización relativa es <b>${esc(spec.name)}</b> (${spec.spec.toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2})}× el peso medio de CABA).`:''}</p><div class="productive-profile-kpis"><div><span>Ocupación</span><b>${pct(p.c.tasa_ocupacion)}</b><small>${signed(p.rateDiff)} p.p. vs. CABA</small></div><div><span>Ranking ocupación</span><b>#${p.rank}</b><small>entre 15 comunas</small></div><div><span>Top 3 rubros</span><b>${pct(p.top3)}</b><small>de los locales ocupados</small></div></div><h4>Principales rubros</h4><div class="productive-mini-list">${p.top.slice(0,5).map(x=>`<button data-profile-rubro="${esc(x.name)}"><span>${esc(x.name)}</span><b>${pct(x.share)}</b><small>${x.spec.toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2})}×</small></button>`).join('')}</div><p class="source">Universo: 48 ejes comerciales de alta densidad. No equivale al total de establecimientos de la comuna.</p>`;
  el.onclick=e=>{const b=e.target.closest('[data-profile-rubro]');if(!b)return;state.rubro=b.dataset.profileRubro;state.metric='especializacion';$('prod-map-rubro').value=state.rubro;$('prod-map-metric').value=state.metric;toggleRubroControl();refreshAnalyticMap();renderProfile(state.selected)};
}
function renderRanking(){
  const el=$('prod-map-ranking');if(!el)return;const xs=Object.keys(ejes().comunas).map(id=>({id,v:metricValue(id)})).sort((a,b)=>b.v-a.v).slice(0,5);
  el.innerHTML=`<span class="eyebrow">Ranking</span><h3>${esc(metricLabel())}</h3><div class="productive-rank-list">${xs.map((x,i)=>`<button data-rank-comuna="${x.id}"><span>${i+1}. Comuna ${x.id}</span><b>${esc(metricFormat(x.v))}</b></button>`).join('')}</div>`;
  el.onclick=e=>{const b=e.target.closest('[data-rank-comuna]');if(b)selectComuna(b.dataset.rankComuna,true)};
}

function renderCompareSelector(){
  const el=$('prod-compare-selector');el.innerHTML=Object.keys(ejes().comunas).map(id=>`<button type="button" class="productive-compare-chip ${state.compare.includes(id)?'active':''}" data-compare-comuna="${id}">Comuna ${id}</button>`).join('');
  el.onclick=e=>{const b=e.target.closest('[data-compare-comuna]');if(!b)return;const id=b.dataset.compareComuna,ix=state.compare.indexOf(id);if(ix>=0)state.compare.splice(ix,1);else if(state.compare.length<4)state.compare.push(id);else{$('prod-compare-note').textContent='Podés comparar hasta cuatro comunas a la vez.';return}$('prod-compare-note').textContent='Seleccioná entre 2 y 4 comunas. El promedio CABA se incluye siempre como referencia.';renderCompareSelector();renderComparison();refreshAnalyticMap()};
}
function renderComparison(){
  const box=$('prod-compare-table');if(!state.compare.length){box.innerHTML='<div class="productive-empty">Seleccioná al menos una comuna.</div>';return}
  const topRubros=rubros().slice().sort((a,b)=>b.total-a.total).slice(0,10);
  box.innerHTML=`<div class="productive-table-scroll"><table class="productive-analysis-table"><thead><tr><th>Rubro</th><th>CABA</th>${state.compare.map(id=>`<th>Comuna ${id}</th>`).join('')}</tr></thead><tbody>${topRubros.map(r=>`<tr><th>${esc(r.rubro)}</th><td>${pct(cityShare(r.rubro))}</td>${state.compare.map(id=>{const s=communeShare(r.rubro,id),sp=specialization(r.rubro,id);return `<td><b>${pct(s)}</b><small>${sp.toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2})}× CABA</small></td>`}).join('')}</tr>`).join('')}</tbody></table></div>`;
  const cards=$('prod-compare-cards');cards.innerHTML=state.compare.map(id=>{const p=profileData(id),top=p.top[0],spec=p.spec[0];return `<article class="productive-compare-card"><span>Comuna ${id}</span><strong>${pct(p.c.tasa_ocupacion)} ocupación</strong><p><b>${esc(top?.name||'—')}</b> es el principal rubro (${pct(top?.share||0)}). ${spec?`Mayor especialización: ${esc(spec.name)} (${spec.spec.toLocaleString('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2})}×).`:''}</p></article>`}).join('');
}

function renderMatrix(){
  const top=rubros().slice().sort((a,b)=>b.total-a.total).slice(0,10),el=$('prod-matrix');
  el.innerHTML=`<div class="productive-table-scroll"><table class="productive-matrix"><thead><tr><th>Comuna</th>${top.map((r,i)=>`<th title="${esc(r.rubro)}">${i+1}</th>`).join('')}</tr></thead><tbody>${Object.keys(ejes().comunas).map(id=>`<tr><th>C${id}</th>${top.map(r=>{const s=specialization(r.rubro,id),band=s<.75?1:s<1?2:s<1.25?3:s<1.75?4:5;return `<td><button data-matrix-comuna="${id}" data-matrix-rubro="${esc(r.rubro)}" data-band="${band}" title="Comuna ${id} · ${esc(r.rubro)} · ${s.toFixed(2)}×">${s.toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1})}×</button></td>`}).join('')}</tr>`).join('')}</tbody></table></div><div class="productive-matrix-key">${top.map((r,i)=>`<span><b>${i+1}</b> ${esc(r.rubro)}</span>`).join('')}</div>`;
  el.onclick=e=>{const b=e.target.closest('[data-matrix-comuna]');if(!b)return;state.rubro=b.dataset.matrixRubro;state.metric='especializacion';$('prod-map-rubro').value=state.rubro;$('prod-map-metric').value=state.metric;toggleRubroControl();selectComuna(b.dataset.matrixComuna,true);document.getElementById('perfil-comercial').scrollIntoView({behavior:'smooth',block:'start'})};
}

function renderEvolution(){
  const el=$('prod-evolution'),cs=Object.entries(ejes().comunas).filter(([,x])=>Number.isFinite(+x.variacion_interanual_pp)&&Number.isFinite(+x.tasa_ocupacion_anterior));
  if(cs.length!==15){el.innerHTML='<div class="productive-warning">La comparación interanual comunal no está disponible en la versión validada del tabulado.</div>';return}
  const sorted=cs.map(([id,x])=>({id,prev:+x.tasa_ocupacion_anterior,now:+x.tasa_ocupacion,delta:+x.variacion_interanual_pp})).sort((a,b)=>b.delta-a.delta),best=sorted[0],worst=sorted[sorted.length-1];
  $('prod-evolution-summary').innerHTML=`<div><span>CABA</span><strong>91,6% → ${pct(ejes().tasa_ocupacion)}</strong><small>-1,6 p.p. interanual</small></div><div><span>Mayor mejora</span><strong>Comuna ${best.id}</strong><small>${signed(best.delta)} p.p.</small></div><div><span>Mayor caída</span><strong>Comuna ${worst.id}</strong><small>${signed(worst.delta)} p.p.</small></div>`;
  el.innerHTML=sorted.map(x=>`<button class="productive-evolution-row" data-evo-comuna="${x.id}"><span>Comuna ${x.id}</span><div><small>2025</small><b>${pct(x.prev)}</b></div><i>→</i><div><small>2026</small><b>${pct(x.now)}</b></div><strong class="${x.delta>=0?'up':'down'}">${signed(x.delta)} p.p.</strong></button>`).join('');
  el.onclick=e=>{const b=e.target.closest('[data-evo-comuna]');if(b){state.metric='ocupacion';$('prod-map-metric').value='ocupacion';toggleRubroControl();selectComuna(b.dataset.evoComuna,true);document.getElementById('perfil-comercial').scrollIntoView({behavior:'smooth',block:'start'})}};
}

function buildDetailControls(){document.querySelectorAll('[data-prod-detail-layer]').forEach(b=>b.addEventListener('click',()=>setDetailMode(b.dataset.prodDetailLayer)));const s=$('prod-year');s.innerHTML='<option value="">2024–2026</option>'+Object.keys(state.dyn.anios||{}).sort().map(y=>`<option value="${y}">${y}</option>`).join('');s.addEventListener('change',()=>{state.year=s.value;refreshDetailMap();renderDetailEmpty()});setDetailMode('flow')}
function initDetailMap(){state.detailMap=L.map('productive-detail-map',{zoomControl:true,minZoom:10,maxZoom:19,preferCanvas:true,scrollWheelZoom:false}).setView([-34.615,-58.445],11);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(state.detailMap);state.detailLayer=L.geoJSON(state.mapData,{style:detailStyle,onEachFeature:(f,l)=>{l.bindTooltip(()=>detailTooltip(f),{sticky:true});l.on('click',()=>selectDetail(f,l))}}).addTo(state.detailMap);if(state.detailLayer.getBounds().isValid())state.detailMap.fitBounds(state.detailLayer.getBounds(),{padding:[12,12]});refreshDetailMap()}
function setDetailMode(mode){state.detailMode=mode;document.querySelectorAll('[data-prod-detail-layer]').forEach(b=>b.classList.toggle('active',b.dataset.prodDetailLayer===mode));$('prod-year-field').style.display=mode==='flow'?'flex':'none';renderDetailNote();refreshDetailMap();renderDetailEmpty()}
function flowEvents(sm){const xs=state.dyn.manzanas?.[sm]?.e||[];return state.year?xs.filter(x=>String(x[0])===state.year):xs}
function detailStyle(f){const p=f.properties||{};if(state.detailMode==='flow'){const n=flowEvents(p.sm).length;if(!n)return{weight:.18,color:'#7d8790',fillColor:'#bfc6cc',fillOpacity:.015,opacity:.1};return{weight:.45,color:'#8b5a13',fillColor:'#d98b2b',fillOpacity:Math.min(.86,.16+Math.log1p(n)/Math.log(18)*.62),opacity:.55}}const n=+p.t||0;if(!n)return{weight:.18,color:'#78828c',fillColor:'#bfc6cc',fillOpacity:.015,opacity:.1};return{weight:.4,color:'#76233a',fillColor:'#b32645',fillOpacity:Math.min(.84,.12+Math.log1p(n)/Math.log(60)*.62),opacity:.5}}
function detailTooltip(f){const p=f.properties||{};if(state.detailMode==='flow')return `<div class="productive-tooltip"><strong>${esc(p.b||'Manzana')} · C${esc(p.c)}</strong><small>${nf.format(flowEvents(p.sm).length)} habilitaciones localizadas${state.year?' · '+esc(state.year):''}</small></div>`;return `<div class="productive-tooltip"><strong>${esc(p.b||'Manzana')} · C${esc(p.c)}</strong><small>${nf.format(p.t||0)} actividades RUS 2017 · SM ${esc(p.sm)}</small></div>`}
function refreshDetailMap(){if(!state.detailLayer)return;state.detailLayer.setStyle(detailStyle);renderDetailNote();updateDetailStatus()}
function renderDetailNote(){const n=$('prod-detail-note');if(!n)return;n.innerHTML=state.detailMode==='flow'?'<b>Dinámica reciente.</b> Habilitaciones aprobadas 2024–2026; sólo se ubican a manzana los registros con clave territorial suficiente.':'<b>Archivo histórico.</b> RUS 2017 conserva resolución por manzana y no se presenta como fotografía vigente.'}
function updateDetailStatus(){if(!$('prod-detail-status'))return;if(state.detailMode==='flow'){let m=0,n=0;for(const f of state.mapData.features){const x=flowEvents(f.properties?.sm).length;if(x){m++;n+=x}}$('prod-detail-status').textContent=`${state.year||'2024–2026'} · ${nf.format(m)} manzanas · ${nf.format(n)} habilitaciones localizadas`;return}let m=0,n=0;for(const f of state.mapData.features){const x=+f.properties?.t||0;if(x){m++;n+=x}}$('prod-detail-status').textContent=`RUS 2017 · ${nf.format(m)} manzanas · ${nf.format(n)} actividades relevadas`}
function renderDetailEmpty(){$('prod-detail-selection').innerHTML=state.detailMode==='flow'?'<span class="eyebrow">Dinámica reciente</span><h3>Elegí una manzana</h3><p>La capa muestra habilitaciones localizadas; es un flujo administrativo y no un stock de establecimientos.</p>':'<span class="eyebrow">Archivo histórico · RUS 2017</span><h3>Elegí una manzana</h3><p>Explorá la estructura económica histórica relevada manzana por manzana.</p>'}
async function selectDetail(f,l){state.detailMap.fitBounds(l.getBounds(),{padding:[40,40],maxZoom:16});if(state.detailMode==='flow')renderFlowSelection(f);else await renderHistoricalSelection(f)}
function renderFlowSelection(f){const p=f.properties||{},all=flowEvents(p.sm);$('prod-detail-selection').innerHTML=`<span class="eyebrow">Habilitaciones · manzana</span><h3>${esc(p.b||'')} · Comuna ${esc(p.c)}</h3><div class="selection-meta">SM ${esc(p.sm)} · ${nf.format(all.length)} habilitaciones localizadas ${state.year||'2024–2026'}</div><p class="source">Una habilitación aprobada no demuestra que el establecimiento continúe activo hoy.</p><div class="productive-place-list">${all.slice(0,100).map(e=>`<div class="productive-place"><strong>${esc(e[2]||e[3]||'Habilitación')}</strong><small>${esc([e[3],e[4]].filter(Boolean).join(' · '))}</small><small>${esc([e[1],e[0]].filter(Boolean).join(' · '))}</small></div>`).join('')||'<div class="productive-empty">Sin registros para el filtro actual.</div>'}</div>`}
async function historicalData(c){if(state.cache.has(c))return state.cache.get(c);const d=await json(BASE+`comuna-${String(c).padStart(2,'0')}.json`);state.cache.set(c,d);return d}
async function renderHistoricalSelection(f){const p=f.properties||{},d=await historicalData(+p.c),b=d.manzanas?.[p.sm];if(!b){renderDetailEmpty();return}const sectors=Object.entries(b.s||{}).sort((a,b)=>b[1]-a[1]).slice(0,6);$('prod-detail-selection').innerHTML=`<span class="eyebrow">RUS 2017 · manzana</span><h3>${esc(b.b||p.b||'')} · Comuna ${p.c}</h3><div class="selection-meta">SM ${esc(p.sm)} · ${nf.format(b.t||0)} actividades relevadas</div><div class="productive-sector-pills">${sectors.map(([id,n])=>`<span class="productive-sector-pill"><b>${nf.format(n)}</b> ${esc(state.manifest.sectores.find(x=>x.id===id)?.nombre||id)}</span>`).join('')}</div><div class="productive-place-list">${(b.e||[]).slice(0,80).map(e=>`<div class="productive-place"><strong>${esc(e[0]||e[6]||e[5]||'Actividad económica')}</strong><small>${esc(e[7]||e[6]||e[5]||'')}</small><small>${esc([e[1],e[2]].filter(Boolean).join(' '))}</small></div>`).join('')}</div><p class="source">Capa histórica. No se suma a habilitaciones recientes para estimar un stock actual.</p>`}
function renderFlowYears(){const years=Object.entries(state.dyn.anios||{}).sort(([a],[b])=>a.localeCompare(b));$('prod-flow-years').innerHTML=years.map(([y,x])=>`<div class="productive-flow-year"><span>${y}</span><strong>${nf.format(x.total||0)}</strong><span>${pct((+x.precision_manzana||0)*100)} con manzana exacta</span></div>`).join('')}
})();
