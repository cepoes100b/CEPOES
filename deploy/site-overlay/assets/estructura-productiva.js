(function(){
  'use strict';
  const BASE='/assets/data/estructura-productiva/';
  const nf=new Intl.NumberFormat('es-AR');
  const state={manifest:null,mapData:null,map:null,layer:null,comunas:new Map(),comuna:'',barrio:'',sector:'',rama:'',query:'',matches:null,selected:null};
  const $=id=>document.getElementById(id);
  const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sectorName=id=>state.manifest?.sectores?.find(x=>x.id===id)?.nombre||id||'Sin clasificar';

  document.addEventListener('DOMContentLoaded',init);

  async function init(){
    try{
      const [manifest,mapData]=await Promise.all([fetchJSON(BASE+'manifest.json'),fetchJSON(BASE+'mapa.json')]);
      state.manifest=manifest; state.mapData=mapData;
      hydrateMeta(); buildControls(); buildSummaries(); initMap();
      $('prod-status').textContent='Mapa listo · acercate o tocá una manzana para ver su estructura económica.';
    }catch(err){
      console.error(err);
      $('prod-status').textContent='No pudimos cargar los datos del mapa. Conservamos la última versión validada y volveremos a intentar automáticamente.';
      const panel=$('prod-selection'); if(panel) panel.innerHTML='<span class="eyebrow">Estado</span><h3>Datos temporalmente no disponibles</h3><p>La interfaz no publica resultados parciales si falla la validación de las fuentes.</p>';
    }
  }

  async function fetchJSON(url){const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw new Error(`${url}: ${r.status}`);return r.json()}

  function hydrateMeta(){
    const m=state.manifest;
    $('prod-total').textContent=nf.format(m.total||0);
    $('prod-blocks').textContent=nf.format(m.manzanas_actividad||0);
    $('prod-barrios').textContent=nf.format(new Set((m.barrios||[]).map(x=>x.barrio)).size);
    $('prod-join').textContent=((m.join_cartografia||0)*100).toLocaleString('es-AR',{maximumFractionDigits:1})+'%';
    $('prod-generated').textContent=formatDate(m.generado);
    $('prod-period').textContent=m.periodo_rus||'2022–2024';
  }

  function formatDate(s){try{return new Intl.DateTimeFormat('es-AR',{day:'2-digit',month:'short',year:'numeric'}).format(new Date(s))}catch(e){return s||'—'}}

  function buildControls(){
    const mc=$('prod-comuna'), mb=$('prod-barrio'), ms=$('prod-sector'), mr=$('prod-rama'), mq=$('prod-search');
    mc.innerHTML='<option value="">Toda CABA</option>'+state.manifest.comunas.map(x=>`<option value="${x.comuna}">Comuna ${x.comuna}</option>`).join('');
    ms.innerHTML='<option value="">Todos los sectores</option>'+state.manifest.sectores.map(x=>`<option value="${esc(x.id)}">${esc(x.nombre)} (${nf.format(x.total)})</option>`).join('');
    mr.innerHTML='<option value="">Todas las ramas</option>'+state.manifest.ramas.map(([name,n])=>`<option value="${esc(name)}">${esc(name)} (${nf.format(n)})</option>`).join('');
    updateBarrios();
    mc.addEventListener('change',async()=>{state.comuna=mc.value;state.barrio='';state.query='';mq.value='';state.matches=null;updateBarrios();if(state.comuna)await ensureComuna(+state.comuna);refresh();zoomToSelection()});
    mb.addEventListener('change',()=>{state.barrio=mb.value;refresh();zoomToSelection()});
    ms.addEventListener('change',()=>{state.sector=ms.value;refresh()});
    mr.addEventListener('change',()=>{state.rama=mr.value;refresh()});
    let timer;
    mq.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(async()=>{state.query=mq.value.trim();await updateSearchMatches();refresh()},180)});
    $('prod-reset').addEventListener('click',()=>{state.comuna=state.barrio=state.sector=state.rama=state.query='';state.matches=null;state.selected=null;[mc,ms,mr].forEach(x=>x.value='');mq.value='';updateBarrios();refresh();if(state.layer)state.map.fitBounds(state.layer.getBounds(),{padding:[10,10]});renderEmptySelection()});
  }

  function updateBarrios(){
    const mb=$('prod-barrio');
    const c=+state.comuna;
    const items=(state.manifest?.barrios||[]).filter(x=>!c||x.comuna===c);
    const uniq=[...new Set(items.map(x=>x.barrio).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'es'));
    mb.innerHTML='<option value="">Todos los barrios</option>'+uniq.map(b=>`<option value="${esc(b)}">${esc(b)}</option>`).join('');
    mb.value=state.barrio;
  }

  function buildSummaries(){
    const max=Math.max(...state.manifest.sectores.map(x=>x.total),1);
    $('prod-sector-bars').innerHTML=state.manifest.sectores.slice().sort((a,b)=>b.total-a.total).slice(0,12).map(x=>`<div class="productive-bar-row"><span>${esc(x.nombre)}</span><div class="productive-bar-track"><div class="productive-bar-fill" style="width:${(x.total/max*100).toFixed(1)}%"></div></div><b>${nf.format(x.total)}</b></div>`).join('');
    $('prod-comuna-grid').innerHTML=state.manifest.comunas.map(x=>`<button class="productive-comuna-card" type="button" data-comuna="${x.comuna}"><span>Comuna ${x.comuna}</span><strong>${nf.format(x.total)}</strong><small>${nf.format(x.manzanas)} manzanas con actividad</small></button>`).join('');
    $('prod-comuna-grid').addEventListener('click',async e=>{const b=e.target.closest('[data-comuna]');if(!b)return;$('prod-comuna').value=b.dataset.comuna;$('prod-comuna').dispatchEvent(new Event('change'))});
  }

  function initMap(){
    if(!window.L) throw new Error('Leaflet no disponible');
    state.map=L.map('productive-map',{zoomControl:true,minZoom:10,maxZoom:19,preferCanvas:true}).setView([-34.615,-58.445],11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(state.map);
    state.layer=L.geoJSON(state.mapData,{style:featureStyle,onEachFeature:onFeature}).addTo(state.map);
    if(state.layer.getBounds().isValid())state.map.fitBounds(state.layer.getBounds(),{padding:[12,12]});
  }

  function featureCount(f){
    const p=f.properties||{};
    if(state.comuna && +p.c!==+state.comuna)return 0;
    if(state.barrio && p.b!==state.barrio)return 0;
    if(state.matches && !state.matches.has(p.sm))return 0;
    let n=+p.t||0;
    if(state.sector){
      if(p.sc && typeof p.sc==='object')n=+p.sc[state.sector]||0;
      else n=p.s===state.sector?n:0;
    }
    if(state.rama){
      if(p.rc && typeof p.rc==='object')n=Math.min(n,+p.rc[state.rama]||0);
      else n=p.r===state.rama?n:0;
    }
    return n;
  }

  function featureStyle(f){
    const v=featureCount(f); if(v<=0)return {weight:.35,color:'#78828c',fillColor:'#aeb6bd',fillOpacity:.035,opacity:.18};
    const op=Math.min(.88,.18+Math.log1p(v)/Math.log(40)*.62);
    return {weight:.55,color:'#76233a',fillColor:'#b32645',fillOpacity:op,opacity:.62};
  }

  function onFeature(feature,layer){
    const p=feature.properties||{};
    layer.bindTooltip(()=>`<div class="productive-tooltip"><strong>${esc(p.b||'Manzana')} · Comuna ${esc(p.c)}</strong><small>SM ${esc(p.sm)} · ${nf.format(featureCount(feature))} actividades visibles</small><small>${esc(p.r||sectorName(p.s))}</small></div>`,{sticky:true});
    layer.on('click',()=>selectBlock(feature,layer));
  }

  async function selectBlock(feature,layer){
    const p=feature.properties||{}; state.selected=p.sm;
    if(!state.comuna){state.comuna=String(p.c);$('prod-comuna').value=state.comuna;updateBarrios()}
    const data=await ensureComuna(+p.c); renderBlock(p.sm,data,feature);
    state.map.fitBounds(layer.getBounds(),{padding:[40,40],maxZoom:16});
  }

  async function ensureComuna(c){
    if(state.comunas.has(c))return state.comunas.get(c);
    $('prod-status').textContent=`Cargando detalle de Comuna ${c}…`;
    const data=await fetchJSON(BASE+`comuna-${String(c).padStart(2,'0')}.json`);
    state.comunas.set(c,data); $('prod-status').textContent=`Comuna ${c} lista · tocá una manzana para ver establecimientos y actividades.`; return data;
  }

  async function updateSearchMatches(){
    state.matches=null;
    if(state.query.length<2)return;
    if(!state.comuna){$('prod-search-help').textContent='Elegí una comuna para buscar por nombre, dirección o actividad.';return}
    const data=await ensureComuna(+state.comuna); const q=norm(state.query); const set=new Set();
    for(const [sm,b] of Object.entries(data.manzanas||{})){
      const hay=(b.e||[]).some(e=>norm(e.join(' ')).includes(q)); if(hay)set.add(sm);
    }
    state.matches=set;$('prod-search-help').textContent=`${nf.format(set.size)} manzanas coinciden con la búsqueda.`;
  }

  function refresh(){if(state.layer)state.layer.setStyle(featureStyle);updateMapStatus();if(state.selected){const f=state.mapData.features.find(x=>x.properties?.sm===state.selected);if(f)ensureComuna(+f.properties.c).then(d=>renderBlock(state.selected,d,f))}}

  function updateMapStatus(){
    if(!state.mapData)return;let visible=0,total=0;for(const f of state.mapData.features){const n=featureCount(f);if(n>0){visible++;total+=n}}
    const parts=[];if(state.comuna)parts.push(`Comuna ${state.comuna}`);if(state.barrio)parts.push(state.barrio);if(state.sector)parts.push(sectorName(state.sector));if(state.rama)parts.push(state.rama);if(state.query.length>=2)parts.push(`“${state.query}”`);
    $('prod-status').textContent=`${parts.length?parts.join(' · '):'Toda CABA'} · ${nf.format(visible)} manzanas · ${nf.format(total)} registros visibles`;
  }

  function zoomToSelection(){
    if(!state.layer)return;const layers=[];state.layer.eachLayer(l=>{const p=l.feature?.properties||{};if((!state.comuna||+p.c===+state.comuna)&&(!state.barrio||p.b===state.barrio))layers.push(l)});if(layers.length){const fg=L.featureGroup(layers);state.map.fitBounds(fg.getBounds(),{padding:[20,20]})}
  }

  function renderBlock(sm,data,feature){
    const b=data?.manzanas?.[sm]; if(!b){renderEmptySelection();return}
    const records=(b.e||[]).filter(e=>(!state.sector||e[4]===state.sector)&&(!state.rama||e[5]===state.rama)&&(!state.query||norm(e.join(' ')).includes(norm(state.query))));
    const pills=Object.entries(b.s||{}).sort((a,b)=>b[1]-a[1]).map(([id,n])=>`<span class="productive-sector-pill"><b>${nf.format(n)}</b> ${esc(sectorName(id))}</span>`).join('');
    const branches=(b.r||[]).slice(0,6).map(([name,n])=>`<li><span>${esc(name)}</span><b>${nf.format(n)}</b></li>`).join('');
    const places=records.slice(0,120).map(e=>{const name=e[0]||e[6]||e[5]||e[8]||'Actividad económica';const addr=[e[1],e[2]].filter(Boolean).join(' ');const activity=e[7]||e[6]||e[5]||e[8]||'Actividad sin descripción';const codes=[e[9]?`ClaNAE ${e[9]}`:(e[3]?`ClaNAE ${e[3]}`:'')].filter(Boolean).join(' · ');return `<div class="productive-place"><strong>${esc(name)}</strong><small>${esc(activity)}</small><small>${esc([addr,codes].filter(Boolean).join(' · '))}</small></div>`}).join('');
    $('prod-selection').innerHTML=`<span class="eyebrow">Manzana seleccionada</span><h3>${esc(b.b||feature?.properties?.b||'')} · Comuna ${data.comuna}</h3><div class="selection-meta">Sección–manzana ${esc(sm)} · ${nf.format(b.t)} actividades relevadas${records.length!==b.t?` · ${nf.format(records.length)} con los filtros actuales`:''}</div><div class="productive-sector-pills">${pills}</div>${branches?`<h4>Principales ramas</h4><ul class="productive-branch-list">${branches}</ul>`:''}<div class="productive-place-list">${places||'<div class="productive-empty">No hay establecimientos de esta manzana que coincidan con los filtros actuales.</div>'}${records.length>120?`<div class="productive-empty">Se muestran 120 de ${nf.format(records.length)} registros.</div>`:''}</div>`;
  }

  function renderEmptySelection(){$('prod-selection').innerHTML='<span class="eyebrow">Exploración por manzana</span><h3>Elegí una manzana</h3><p>Tocá cualquier polígono del mapa. Al acercarte vas a poder inspeccionar la composición económica y el listado de actividades relevadas en esa manzana.</p>'}
})();
