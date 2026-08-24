(function(){
  'use strict';
  const BASE='/assets/data/estructura-productiva/';
  const nf=new Intl.NumberFormat('es-AR');
  const state={manifest:null,mapData:null,dynamics:null,map:null,layer:null,comunas:new Map(),mode:'stock',comuna:'',barrio:'',sector:'',rama:'',year:'',rubro:'',query:'',matches:null,selected:null};
  const $=id=>document.getElementById(id);
  const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sectorName=id=>state.manifest?.sectores?.find(x=>x.id===id)?.nombre||id||'Sin clasificar';

  document.addEventListener('DOMContentLoaded',init);

  async function init(){
    try{
      const [manifest,mapData,dynamics]=await Promise.all([
        fetchJSON(BASE+'manifest.json'),fetchJSON(BASE+'mapa.json'),fetchJSON(BASE+'dinamica.json')
      ]);
      state.manifest=manifest;state.mapData=mapData;state.dynamics=dynamics;
      buildControls();initMap();refreshAll();
    }catch(err){
      console.error(err);
      const status=$('prod-status');if(status)status.textContent='No pudimos cargar el conjunto completo de datos. La página no publica resultados parciales.';
      const panel=$('prod-selection');if(panel)panel.innerHTML='<span class="eyebrow">Estado</span><h3>Datos temporalmente no disponibles</h3><p>CEPOES conserva la última versión validada y no mezcla capas incompletas.</p>';
    }
  }

  async function fetchJSON(url){const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw new Error(`${url}: ${r.status}`);return r.json()}
  function formatDate(s){try{return new Intl.DateTimeFormat('es-AR',{day:'2-digit',month:'short',year:'numeric'}).format(new Date(s))}catch(e){return s||'—'}}

  function buildControls(){
    const mc=$('prod-comuna'),mb=$('prod-barrio'),ms=$('prod-sector'),mr=$('prod-rama'),my=$('prod-year'),mu=$('prod-rubro'),mq=$('prod-search');
    mc.innerHTML='<option value="">Toda CABA</option>'+state.manifest.comunas.map(x=>`<option value="${x.comuna}">Comuna ${x.comuna}</option>`).join('');
    ms.innerHTML='<option value="">Todos los sectores</option>'+state.manifest.sectores.map(x=>`<option value="${esc(x.id)}">${esc(x.nombre)} (${nf.format(x.total)})</option>`).join('');
    mr.innerHTML='<option value="">Todas las ramas</option>'+state.manifest.ramas.map(([name,n])=>`<option value="${esc(name)}">${esc(name)} (${nf.format(n)})</option>`).join('');
    const years=Object.keys(state.dynamics.anios||{}).sort();
    my.innerHTML='<option value="">2024–2026</option>'+years.map(y=>`<option value="${y}">${y}</option>`).join('');
    fillRubros();updateBarrios();

    mc.addEventListener('change',async()=>{state.comuna=mc.value;state.barrio='';state.query='';mq.value='';state.matches=null;updateBarrios();if(state.mode==='stock'&&state.comuna)await ensureComuna(+state.comuna);refresh();zoomToSelection()});
    mb.addEventListener('change',()=>{state.barrio=mb.value;refresh();zoomToSelection()});
    ms.addEventListener('change',()=>{state.sector=ms.value;refresh()});
    mr.addEventListener('change',()=>{state.rama=mr.value;refresh()});
    my.addEventListener('change',()=>{state.year=my.value;state.rubro='';fillRubros();refreshAll()});
    mu.addEventListener('change',()=>{state.rubro=mu.value;refresh()});
    let timer;
    mq.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(async()=>{state.query=mq.value.trim();await updateSearchMatches();refresh()},180)});
    $('prod-reset').addEventListener('click',resetFilters);
    document.querySelectorAll('[data-prod-mode]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.prodMode)));
  }

  function setMode(mode){
    if(!['stock','flow'].includes(mode)||state.mode===mode)return;
    state.mode=mode;state.sector=state.rama=state.year=state.rubro=state.query='';state.matches=null;state.selected=null;
    ['prod-sector','prod-rama','prod-year','prod-rubro','prod-search'].forEach(id=>{const el=$(id);if(el)el.value=''});
    document.querySelectorAll('[data-prod-mode]').forEach(b=>b.classList.toggle('active',b.dataset.prodMode===mode));
    toggleModeControls();renderEmptySelection();refreshAll();
  }

  function toggleModeControls(){
    const stock=state.mode==='stock';
    ['prod-sector-field','prod-rama-field'].forEach(id=>$(id)?.classList.toggle('hidden',!stock));
    ['prod-year-field','prod-rubro-field'].forEach(id=>$(id)?.classList.toggle('hidden',stock));
    $('prod-search')?.setAttribute('placeholder',stock?'Ej.: textil, software, panadería, Rivadavia…':'Ej.: gastronomía, gimnasio, Corrientes…');
    $('prod-mode-note').textContent=stock?'Stock estructural relevado físicamente en 2017.':'Flujo administrativo de nuevas habilitaciones 2024–2026; no equivale al stock de locales activos.';
    const legend=$('prod-legend-scale');if(legend)legend.style.background=stock?'linear-gradient(90deg,rgba(179,38,69,.12),rgba(179,38,69,.95))':'linear-gradient(90deg,rgba(217,139,43,.12),rgba(217,139,43,.96))';
  }

  function resetFilters(){
    state.comuna=state.barrio=state.sector=state.rama=state.year=state.rubro=state.query='';state.matches=null;state.selected=null;
    ['prod-comuna','prod-sector','prod-rama','prod-year','prod-rubro','prod-search'].forEach(id=>{const x=$(id);if(x)x.value=''});updateBarrios();fillRubros();refreshAll();
    if(state.layer&&state.layer.getBounds().isValid())state.map.fitBounds(state.layer.getBounds(),{padding:[10,10]});renderEmptySelection();
  }

  function updateBarrios(){
    const mb=$('prod-barrio'),c=+state.comuna;
    const items=(state.manifest?.barrios||[]).filter(x=>!c||x.comuna===c);
    const uniq=[...new Set(items.map(x=>x.barrio).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'es'));
    mb.innerHTML='<option value="">Todos los barrios</option>'+uniq.map(b=>`<option value="${esc(b)}">${esc(b)}</option>`).join('');mb.value=state.barrio;
  }

  function exactFlowEvents(){
    const out=[];for(const [sm,b] of Object.entries(state.dynamics?.manzanas||{})){for(const e of b.e||[])out.push([sm,e])}return out;
  }

  function fillRubros(){
    const sel=$('prod-rubro');if(!sel)return;const counts=new Map();
    for(const [,e] of exactFlowEvents()){
      if(state.year&&String(e[0])!==String(state.year))continue;
      const r=e[2]||e[3]||'';if(r)counts.set(r,(counts.get(r)||0)+1);
    }
    const items=[...counts.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'es'));
    sel.innerHTML='<option value="">Todos los rubros</option>'+items.map(([r,n])=>`<option value="${esc(r)}">${esc(r)} (${nf.format(n)})</option>`).join('');sel.value=state.rubro;
  }

  function refreshAll(){toggleModeControls();hydrateMeta();buildSummaries();refresh();}

  function hydrateMeta(){
    const m=state.manifest,d=state.dynamics,stock=state.mode==='stock';
    const labels=['prod-kpi1-label','prod-kpi2-label','prod-kpi3-label','prod-kpi4-label'];
    if(stock){
      $(labels[0]).textContent='Actividades relevadas';$('prod-kpi1').textContent=nf.format(m.total||0);$('prod-kpi1-small').textContent='registros con actividad económica identificable';
      $(labels[1]).textContent='Manzanas con actividad';$('prod-kpi2').textContent=nf.format(m.manzanas_actividad||0);$('prod-kpi2-small').textContent='con cruce cartográfico validado';
      $(labels[2]).textContent='Barrios';$('prod-kpi3').textContent=nf.format(new Set((m.barrios||[]).map(x=>x.barrio)).size);$('prod-kpi3-small').textContent='cobertura territorial del relevamiento';
      $(labels[3]).textContent='Cruce cartográfico';$('prod-kpi4').textContent=((m.join_cartografia||0)*100).toLocaleString('es-AR',{maximumFractionDigits:1})+'%';$('prod-kpi4-small').textContent='RUS ↔ manzanas oficiales';
      $('prod-generated').textContent=formatDate(m.generado);$('prod-period').textContent=m.periodo_rus||'2017';$('prod-layer-name').textContent='Base estructural';
    }else{
      const years=Object.entries(d.anios||{});const total=years.reduce((a,[,x])=>a+(+x.total||0),0);const exact=years.reduce((a,[,x])=>a+(+x.manzana_exacta||0),0);const p=total?exact/total:0;
      $(labels[0]).textContent='Habilitaciones aprobadas';$('prod-kpi1').textContent=nf.format(total);$('prod-kpi1-small').textContent='flujo administrativo 2024–2026';
      $(labels[1]).textContent='Manzanas localizadas';$('prod-kpi2').textContent=nf.format(Object.keys(d.manzanas||{}).length);$('prod-kpi2-small').textContent='con sección–manzana disponible';
      $(labels[2]).textContent='Años disponibles';$('prod-kpi3').textContent=nf.format(years.length);$('prod-kpi3-small').textContent='2024, 2025 y 2026';
      $(labels[3]).textContent='Precisión a manzana';$('prod-kpi4').textContent=(p*100).toLocaleString('es-AR',{maximumFractionDigits:1})+'%';$('prod-kpi4-small').textContent='sobre el total del flujo publicado';
      $('prod-generated').textContent=formatDate(d.generado);$('prod-period').textContent='2024–2026';$('prod-layer-name').textContent='Dinámica reciente';
    }
    updatePrecisionWarning();
  }

  function updatePrecisionWarning(){
    const el=$('prod-precision-warning');if(!el)return;
    if(state.mode==='stock'){el.hidden=true;return}
    const y=state.year,info=y?state.dynamics?.anios?.[y]:null;
    if(!info){el.hidden=true;return}
    const p=+info.precision_manzana||0;el.hidden=p>=.95;
    if(!el.hidden)el.innerHTML=`<b>${esc(y)} tiene precisión territorial parcial.</b> ${nf.format(info.manzana_exacta||0)} de ${nf.format(info.total||0)} habilitaciones traen sección–manzana (${(p*100).toLocaleString('es-AR',{maximumFractionDigits:1})}%). Las restantes se mantienen sólo en los totales agregados; CEPOES no les asigna una manzana inferida.`;
  }

  function buildSummaries(){
    if(state.mode==='stock')buildStockSummaries();else buildFlowSummaries();
  }

  function buildStockSummaries(){
    $('prod-summary-title').textContent='Qué actividades estructuran la Ciudad';$('prod-summary-left-title').textContent='Principales sectores';$('prod-summary-left-desc').textContent='Cantidad de actividades del stock estructural según grandes agrupamientos derivados de ClaNAE.';$('prod-summary-right-title').textContent='Explorar por comuna';$('prod-summary-right-desc').textContent='Acceso rápido al total de actividades y manzanas con presencia económica relevada.';
    const items=state.manifest.sectores.slice().sort((a,b)=>b.total-a.total).slice(0,12),max=Math.max(...items.map(x=>x.total),1);
    $('prod-summary-bars').innerHTML=items.map(x=>barRow(x.nombre,x.total,max)).join('');
    $('prod-summary-cards').className='productive-comuna-grid';$('prod-summary-cards').innerHTML=state.manifest.comunas.map(x=>`<button class="productive-comuna-card" type="button" data-comuna="${x.comuna}"><span>Comuna ${x.comuna}</span><strong>${nf.format(x.total)}</strong><small>${nf.format(x.manzanas)} manzanas con actividad</small></button>`).join('');
    $('prod-summary-cards').onclick=e=>{const b=e.target.closest('[data-comuna]');if(!b)return;$('prod-comuna').value=b.dataset.comuna;$('prod-comuna').dispatchEvent(new Event('change'))};
  }

  function buildFlowSummaries(){
    $('prod-summary-title').textContent='La dinámica reciente de aperturas';$('prod-summary-left-title').textContent='Rubros con más habilitaciones localizadas';$('prod-summary-left-desc').textContent='Conteo sobre registros con manzana exacta. El total anual puede ser mayor cuando la fuente no informa esa clave.';$('prod-summary-right-title').textContent='Cobertura por año';$('prod-summary-right-desc').textContent='Total de habilitaciones y porcentaje que puede visualizarse exactamente a nivel manzana.';
    const counts=new Map();for(const [,e] of exactFlowEvents()){const r=e[2]||e[3]||'';if(r)counts.set(r,(counts.get(r)||0)+1)}const items=[...counts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,12),max=Math.max(...items.map(x=>x[1]),1);
    $('prod-summary-bars').innerHTML=items.map(([r,n])=>barRow(r,n,max)).join('')||'<p class="productive-empty">Sin rubros localizados.</p>';
    $('prod-summary-cards').className='productive-year-grid';$('prod-summary-cards').innerHTML=Object.entries(state.dynamics.anios||{}).sort().map(([y,x])=>{const p=+x.precision_manzana||0;return `<button class="productive-year-card ${p<.95?'warn':''}" type="button" data-year="${y}"><span>${y}</span><strong>${nf.format(x.total||0)}</strong><small>${(p*100).toLocaleString('es-AR',{maximumFractionDigits:1})}% con manzana exacta</small></button>`}).join('');
    $('prod-summary-cards').onclick=e=>{const b=e.target.closest('[data-year]');if(!b)return;$('prod-year').value=b.dataset.year;$('prod-year').dispatchEvent(new Event('change'))};
  }

  function barRow(name,n,max){return `<div class="productive-bar-row"><span>${esc(name)}</span><div class="productive-bar-track"><div class="productive-bar-fill" style="width:${(n/max*100).toFixed(1)}%"></div></div><b>${nf.format(n)}</b></div>`}

  function initMap(){
    if(!window.L)throw new Error('Leaflet no disponible');
    state.map=L.map('productive-map',{zoomControl:true,minZoom:10,maxZoom:19,preferCanvas:true}).setView([-34.615,-58.445],11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(state.map);
    state.layer=L.geoJSON(state.mapData,{style:featureStyle,onEachFeature:onFeature}).addTo(state.map);
    if(state.layer.getBounds().isValid())state.map.fitBounds(state.layer.getBounds(),{padding:[12,12]});
  }

  function stockCount(f){
    const p=f.properties||{};let n=+p.t||0;
    if(state.sector)n=p.sc&&typeof p.sc==='object'?+p.sc[state.sector]||0:(p.s===state.sector?n:0);
    if(state.rama)n=p.rc&&typeof p.rc==='object'?Math.min(n,+p.rc[state.rama]||0):(p.r===state.rama?n:0);
    return n;
  }

  function filteredFlowEvents(sm){
    const b=state.dynamics?.manzanas?.[sm];if(!b)return[];const q=norm(state.query);
    return (b.e||[]).filter(e=>(!state.year||String(e[0])===String(state.year))&&(!state.rubro||(e[2]||e[3]||'')===state.rubro)&&(!q||norm(e.join(' ')).includes(q)));
  }

  function featureCount(f){
    const p=f.properties||{};
    if(state.comuna&&+p.c!==+state.comuna)return 0;if(state.barrio&&p.b!==state.barrio)return 0;
    if(state.mode==='stock'){
      if(state.matches&&!state.matches.has(p.sm))return 0;return stockCount(f);
    }
    return filteredFlowEvents(p.sm).length;
  }

  function featureStyle(f){
    const v=featureCount(f);if(v<=0)return{weight:.35,color:'#78828c',fillColor:'#aeb6bd',fillOpacity:.035,opacity:.18};
    const op=Math.min(.88,.18+Math.log1p(v)/Math.log(40)*.62),flow=state.mode==='flow';
    return{weight:.55,color:flow?'#8b5a13':'#76233a',fillColor:flow?'#d98b2b':'#b32645',fillOpacity:op,opacity:.66};
  }

  function onFeature(feature,layer){
    layer.bindTooltip(()=>{const p=feature.properties||{},n=featureCount(feature),unit=state.mode==='stock'?'actividades':'habilitaciones';return `<div class="productive-tooltip"><strong>${esc(p.b||'Manzana')} · Comuna ${esc(p.c)}</strong><small>SM ${esc(p.sm)} · ${nf.format(n)} ${unit} visibles</small></div>`},{sticky:true});
    layer.on('click',()=>selectBlock(feature,layer));
  }

  async function selectBlock(feature,layer){
    const p=feature.properties||{};state.selected=p.sm;
    if(!state.comuna){state.comuna=String(p.c);$('prod-comuna').value=state.comuna;updateBarrios()}
    if(state.mode==='stock'){const data=await ensureComuna(+p.c);renderStockBlock(p.sm,data,feature)}else renderFlowBlock(p.sm,feature);
    state.map.fitBounds(layer.getBounds(),{padding:[40,40],maxZoom:16});
  }

  async function ensureComuna(c){
    if(state.comunas.has(c))return state.comunas.get(c);$('prod-status').textContent=`Cargando detalle de Comuna ${c}…`;
    const data=await fetchJSON(BASE+`comuna-${String(c).padStart(2,'0')}.json`);state.comunas.set(c,data);return data;
  }

  async function updateSearchMatches(){
    state.matches=null;const q=state.query.trim();if(q.length<2){$('prod-search-help').textContent=state.mode==='stock'?'Para búsquedas de texto, elegí primero una comuna.':'La búsqueda filtra rubro, subrubro y dirección.';return}
    if(state.mode==='flow'){$('prod-search-help').textContent='Búsqueda aplicada a las habilitaciones con localización exacta.';return}
    if(!state.comuna){$('prod-search-help').textContent='Elegí una comuna para buscar por nombre, dirección o actividad.';return}
    const data=await ensureComuna(+state.comuna),needle=norm(q),set=new Set();for(const[sm,b]of Object.entries(data.manzanas||{})){if((b.e||[]).some(e=>norm(e.join(' ')).includes(needle)))set.add(sm)}state.matches=set;$('prod-search-help').textContent=`${nf.format(set.size)} manzanas coinciden con la búsqueda.`;
  }

  function refresh(){
    if(state.layer)state.layer.setStyle(featureStyle);updateMapStatus();updatePrecisionWarning();
    if(state.selected){const f=state.mapData.features.find(x=>x.properties?.sm===state.selected);if(f){if(state.mode==='stock')ensureComuna(+f.properties.c).then(d=>renderStockBlock(state.selected,d,f));else renderFlowBlock(state.selected,f)}}
  }

  function updateMapStatus(){
    if(!state.mapData)return;let visible=0,total=0;for(const f of state.mapData.features){const n=featureCount(f);if(n>0){visible++;total+=n}}
    const parts=[];if(state.comuna)parts.push(`Comuna ${state.comuna}`);if(state.barrio)parts.push(state.barrio);
    if(state.mode==='stock'){if(state.sector)parts.push(sectorName(state.sector));if(state.rama)parts.push(state.rama)}else{if(state.year)parts.push(state.year);if(state.rubro)parts.push(state.rubro)}if(state.query.length>=2)parts.push(`“${state.query}”`);
    const unit=state.mode==='stock'?'registros':'habilitaciones localizadas';$('prod-status').textContent=`${parts.length?parts.join(' · '):'Toda CABA'} · ${nf.format(visible)} manzanas · ${nf.format(total)} ${unit}`;
  }

  function zoomToSelection(){if(!state.layer)return;const layers=[];state.layer.eachLayer(l=>{const p=l.feature?.properties||{};if((!state.comuna||+p.c===+state.comuna)&&(!state.barrio||p.b===state.barrio))layers.push(l)});if(layers.length)state.map.fitBounds(L.featureGroup(layers).getBounds(),{padding:[20,20]})}

  function renderStockBlock(sm,data,feature){
    const b=data?.manzanas?.[sm];if(!b){renderEmptySelection();return}
    const records=(b.e||[]).filter(e=>(!state.sector||e[4]===state.sector)&&(!state.rama||e[5]===state.rama)&&(!state.query||norm(e.join(' ')).includes(norm(state.query))));
    const pills=Object.entries(b.s||{}).sort((a,b)=>b[1]-a[1]).map(([id,n])=>`<span class="productive-sector-pill"><b>${nf.format(n)}</b> ${esc(sectorName(id))}</span>`).join('');
    const branches=(b.r||[]).slice(0,6).map(([name,n])=>`<li><span>${esc(name)}</span><b>${nf.format(n)}</b></li>`).join('');
    const places=records.slice(0,120).map(e=>{const name=e[0]||e[6]||e[5]||e[8]||'Actividad económica',addr=[e[1],e[2]].filter(Boolean).join(' '),activity=e[7]||e[6]||e[5]||e[8]||'Actividad sin descripción',code=e[9]?`ClaNAE ${e[9]}`:(e[3]?`ClaNAE ${e[3]}`:'');return `<div class="productive-place"><strong>${esc(name)}</strong><small>${esc(activity)}</small><small>${esc([addr,code].filter(Boolean).join(' · '))}</small></div>`}).join('');
    $('prod-selection').innerHTML=`<span class="eyebrow">Base estructural · manzana</span><h3>${esc(b.b||feature?.properties?.b||'')} · Comuna ${data.comuna}</h3><div class="selection-meta">Sección–manzana ${esc(sm)} · ${nf.format(b.t)} actividades relevadas en RUS 2017${records.length!==b.t?` · ${nf.format(records.length)} con filtros`:''}</div><div class="productive-sector-pills">${pills}</div>${branches?`<h4>Principales ramas</h4><ul class="productive-branch-list">${branches}</ul>`:''}<div class="productive-place-list">${places||'<div class="productive-empty">No hay registros que coincidan con los filtros actuales.</div>'}${records.length>120?`<div class="productive-empty">Se muestran 120 de ${nf.format(records.length)} registros.</div>`:''}</div>`;
  }

  function renderFlowBlock(sm,feature){
    const all=state.dynamics?.manzanas?.[sm]?.e||[],records=filteredFlowEvents(sm);
    const places=records.slice(0,160).map(e=>`<div class="productive-place"><strong>${esc(e[2]||e[3]||'Habilitación')}</strong><small>${esc([e[3],e[4]].filter(Boolean).join(' · '))}</small><small>${esc([e[1],String(e[0])].filter(Boolean).join(' · '))}</small></div>`).join('');
    $('prod-selection').innerHTML=`<span class="eyebrow">Dinámica reciente · manzana</span><h3>${esc(feature?.properties?.b||'')} · Comuna ${esc(feature?.properties?.c||'')}</h3><div class="selection-meta">Sección–manzana ${esc(sm)} · ${nf.format(all.length)} habilitaciones localizadas 2024–2026${records.length!==all.length?` · ${nf.format(records.length)} con filtros`:''}</div><p class="source">Flujo administrativo de habilitaciones aprobadas; no implica que todos los establecimientos continúen activos ni equivale al stock económico.</p><div class="productive-place-list">${places||'<div class="productive-empty">No hay habilitaciones localizadas que coincidan con los filtros actuales.</div>'}${records.length>160?`<div class="productive-empty">Se muestran 160 de ${nf.format(records.length)} registros.</div>`:''}</div>`;
  }

  function renderEmptySelection(){
    const flow=state.mode==='flow';$('prod-selection').innerHTML=`<span class="eyebrow">${flow?'Dinámica reciente':'Base estructural'} · exploración por manzana</span><h3>Elegí una manzana</h3><p>${flow?'Tocá una manzana para ver las nuevas habilitaciones que la fuente permite localizar exactamente.':'Tocá cualquier polígono para ver composición económica, ramas y actividades relevadas en RUS 2017.'}</p>`;
  }
})();
