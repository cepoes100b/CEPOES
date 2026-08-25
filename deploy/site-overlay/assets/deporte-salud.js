(function(){
  'use strict';
  const DATA='/assets/data/deporte-salud.json?v=2';
  const ACCESS='/assets/data/deporte-accesibilidad.json?v=1';
  const GEO='/assets/data/estructura-productiva/comunas.geojson?v=260';
  const state={data:null,access:null,geo:null,metric:'clubes',comuna:'all',q:'',layers:new Set(['clubes','polideportivos','estaciones','cesac']),accessUniverse:'red_deportiva',accessDistance:'800'};
  const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=n=>new Intl.NumberFormat('es-AR').format(Number(n)||0);
  const dec=n=>n==null?'—':new Intl.NumberFormat('es-AR',{minimumFractionDigits:0,maximumFractionDigits:2}).format(n);
  const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const metricMeta={
    clubes:{label:'Clubes por 10.000 habitantes',key:'clubes'},
    sedes_clubes:{label:'Sedes de clubes por 10.000 habitantes',key:'sedes_clubes'},
    polideportivos:{label:'Polideportivos por 10.000 habitantes',key:'polideportivos'},
    estaciones_saludables:{label:'Estaciones Saludables por 10.000 habitantes',key:'estaciones_saludables'},
    cesac:{label:'CeSAC por 10.000 habitantes',key:'cesac'}
  };
  const allItems=()=>Object.entries(state.data.capas||{}).flatMap(([layer,obj])=>(obj.items||[]).map(x=>({...x,capa:layer})));
  function itemVisible(x){
    if(!state.layers.has(x.capa)) return false;
    if(state.comuna!=='all' && String(x.comuna)!==state.comuna) return false;
    if(!state.q) return true;
    const hay=norm([x.nombre,x.barrio,x.direccion,x.tipo,(x.actividades||[]).join(' '),x.sede].join(' '));
    return state.q.split(/\s+/).filter(Boolean).every(w=>hay.includes(w));
  }
  function sourceDate(){
    const dates=(state.data.fuentes||[]).map(x=>x.generado_cepoes).filter(Boolean).sort();
    dates.push(state.access?.generado||'');
    return dates.filter(Boolean).sort().at(-1)||state.data.generado||'—';
  }
  function renderKpis(){
    const r=state.data.resumen;
    $('#ds-kpi-clubes').textContent=fmt(r.clubes);
    $('#ds-kpi-sedes').textContent=`${fmt(r.sedes_clubes)} sedes/puntos registrados`;
    $('#ds-kpi-poli').textContent=fmt(r.polideportivos);
    $('#ds-kpi-poli-sub').textContent=`${fmt(r.polideportivos_geolocalizados)} ubicados en el mapa`;
    $('#ds-kpi-est').textContent=fmt(r.estaciones_saludables);
    $('#ds-kpi-cesac').textContent=fmt(r.cesac);
    $('#ds-updated').textContent=sourceDate();
    const a=state.data.alertas||{};
    if(a.programas_desactualizados){
      const el=$('#ds-program-warning'); el.hidden=false;
      const year=String(a.programas_recurso_modificado||'').slice(0,10)||'sin fecha';
      el.innerHTML=`<b>Programas Deportivos: usar como referencia.</b> El catálogo de BA Data tiene metadata actualizada, pero el recurso que llega al pipeline registra modificación ${esc(year)}. CEPOES no lo presenta como agenda vigente.`;
      $$('[data-layer="programas"]').forEach(b=>{b.title='Referencia; no se presume vigencia';});
    }
  }
  function comunaProp(f){
    const p=f.properties||{};
    const raw=p.comuna??p.COMUNA??p.Comuna??p.id??p.ID;
    const m=String(raw||'').match(/\d+/); return m?Number(m[0]):null;
  }
  function metricValue(cid){
    const c=state.data.comunas[String(cid)]||{}; return (c.tasas_10k||{})[metricMeta[state.metric].key]??0;
  }
  function colorScale(){
    const vals=Object.keys(state.data.comunas).map(Number).map(metricValue);
    const max=Math.max(...vals,1);
    return d3.scaleSequential().domain([0,max]).interpolator(d3.interpolateBlues);
  }
  function renderMap(){
    const root=$('#ds-map'), svg=d3.select('#ds-map svg'), tt=$('#ds-tooltip');
    svg.selectAll('*').remove();
    const W=760,H=650, projection=d3.geoMercator().fitExtent([[28,24],[W-28,H-24]],state.geo), path=d3.geoPath(projection), scale=colorScale();
    const g=svg.append('g');
    g.selectAll('path').data(state.geo.features||[]).join('path')
      .attr('class',f=>'ds-comuna'+(String(comunaProp(f))===state.comuna?' active':''))
      .attr('d',path).attr('fill',f=>scale(metricValue(comunaProp(f))))
      .on('click',(ev,f)=>{const cid=comunaProp(f);state.comuna=String(cid);$('#ds-comuna').value=state.comuna;renderAll();})
      .on('mousemove',(ev,f)=>{const cid=comunaProp(f);showTip(ev,`Comuna ${cid}`,`${metricMeta[state.metric].label}: ${dec(metricValue(cid))}`);})
      .on('mouseleave',hideTip);
    const pts=allItems().filter(itemVisible).filter(x=>Array.isArray(x.coord));
    const pg=svg.append('g');
    pg.selectAll('circle').data(pts,d=>`${d.capa}-${d.id}`).join('circle')
      .attr('class',d=>`ds-point ds-${d.capa}`).attr('r',d=>d.capa==='polideportivos'?5.2:3.8)
      .attr('cx',d=>projection(d.coord)[0]).attr('cy',d=>projection(d.coord)[1])
      .on('mousemove',(ev,d)=>showTip(ev,d.nombre,[d.barrio,d.direccion,(d.actividades||[]).slice(0,4).join(' · ')].filter(Boolean).join(' · ')))
      .on('mouseleave',hideTip);
    $('#ds-map-status').textContent=`${fmt(pts.length)} puntos visibles · ${metricMeta[state.metric].label}`;
    function showTip(ev,title,body){tt.style.display='block';tt.innerHTML=`<strong>${esc(title)}</strong><small>${esc(body)}</small>`;const box=root.getBoundingClientRect();tt.style.left=Math.min(ev.clientX-box.left+12,box.width-300)+'px';tt.style.top=Math.max(8,ev.clientY-box.top-20)+'px';}
    function hideTip(){tt.style.display='none';}
  }
  function accessBlock(){
    return state.access.cobertura[state.accessUniverse].distancias[state.accessDistance];
  }
  function renderSelected(){
    const el=$('#ds-selected');
    if(state.comuna==='all'){
      el.innerHTML='<span class="eyebrow">Lectura territorial</span><h3>Toda la Ciudad</h3><p>Seleccioná una comuna en el mapa o en el filtro para comparar su dotación y proximidad territorial.</p>';
      return;
    }
    const c=state.data.comunas[state.comuna];
    const ab=accessBlock().comunas[state.comuna];
    const alabel=state.access.cobertura[state.accessUniverse].label;
    el.innerHTML=`<span class="eyebrow">Comuna ${esc(state.comuna)}</span><h3>${fmt(c.poblacion)} habitantes</h3><div class="ds-selected-grid">
      <div class="ds-mini"><b>${fmt(c.clubes)}</b><span>clubes</span></div><div class="ds-mini"><b>${fmt(c.polideportivos)}</b><span>polideportivos</span></div>
      <div class="ds-mini"><b>${fmt(c.estaciones_saludables)}</b><span>estaciones saludables</span></div><div class="ds-mini"><b>${fmt(c.cesac)}</b><span>CeSAC</span></div></div>
      <p class="small-muted">${metricMeta[state.metric].label}: <b>${dec(c.tasas_10k[metricMeta[state.metric].key])}</b>.</p>
      <p class="small-muted">${esc(alabel)} a ${fmt(state.accessDistance)} m: <b>${dec(ab.cobertura_pct)}%</b> de cobertura estimada.</p>`;
  }
  function renderRanking(){
    const meta=metricMeta[state.metric];
    const rows=Object.entries(state.data.comunas).map(([cid,c])=>({cid,c,v:(c.tasas_10k||{})[meta.key]??0})).sort((a,b)=>b.v-a.v);
    $('#ds-rank-title').textContent=meta.label;
    $('#ds-ranking tbody').innerHTML=rows.map((x,i)=>`<tr><td>${i+1}</td><td><button class="ds-rank-link" data-cid="${x.cid}">Comuna ${x.cid}</button></td><td class="num"><b>${dec(x.v)}</b></td><td class="num">${fmt(x.c[meta.key]??0)}</td></tr>`).join('');
    $$('#ds-ranking [data-cid]').forEach(b=>b.addEventListener('click',()=>selectComuna(b.dataset.cid)));
  }
  function renderAccess(){
    const coverage=state.access.cobertura;
    const red800=coverage.red_deportiva.distancias['800'].ciudad;
    const club800=coverage.clubes.distancias['800'].ciudad;
    const poli800=coverage.polideportivos.distancias['800'].ciudad;
    $('#ds-access-red800').textContent=`${dec(red800.cobertura_pct)}%`;
    $('#ds-access-club800').textContent=`${dec(club800.cobertura_pct)}%`;
    $('#ds-access-poli800').textContent=`${dec(poli800.cobertura_pct)}%`;
    $('#ds-access-out800').textContent=fmt(red800.poblacion_fuera_cobertura_estimada);
    const universe=coverage[state.accessUniverse];
    const block=universe.distancias[state.accessDistance];
    $('#ds-access-title').textContent=`${universe.label} · ${fmt(state.accessDistance)} m`;
    $('#ds-access-city').textContent=`${dec(block.ciudad.cobertura_pct)}%`;
    $('#ds-access-out').textContent=fmt(block.ciudad.poblacion_fuera_cobertura_estimada);
    $('#ds-access-points').textContent=fmt(universe.puntos_georreferenciados);
    const base=state.access.base_poblacional;
    $('#ds-access-base').textContent=`Base: ${fmt(base.poblacion_radios)} habitantes en ${fmt(base.radios)} radios censales · cálculo ${state.access.generado}`;
    $('#ds-access-pop').textContent=fmt(base.poblacion_radios);
    $('#ds-access-gap').textContent=`${fmt(base.diferencia_personas)} personas (${dec(base.diferencia_pct)}%)`;
    const rows=Object.entries(block.comunas).map(([cid,c])=>({cid,...c})).sort((a,b)=>a.cobertura_pct-b.cobertura_pct);
    $('#ds-access-table tbody').innerHTML=rows.map((x,i)=>`<tr><td>${i+1}</td><td><button class="ds-rank-link" data-access-cid="${x.cid}">Comuna ${x.cid}</button></td><td class="num"><b>${dec(x.cobertura_pct)}%</b></td><td class="num">${fmt(x.poblacion_fuera_cobertura_estimada)}</td></tr>`).join('');
    $$('#ds-access-table [data-access-cid]').forEach(b=>b.addEventListener('click',()=>selectComuna(b.dataset.accessCid)));
  }
  function selectComuna(cid){
    state.comuna=String(cid);$('#ds-comuna').value=state.comuna;renderAll();document.querySelector('#mapa').scrollIntoView({behavior:'smooth'});
  }
  function renderActivities(){
    const rows=(state.data.actividades||[]).filter(x=>x.sedes_clubes>0).slice(0,14), max=Math.max(...rows.map(x=>x.sedes_clubes),1);
    $('#ds-activities').innerHTML=rows.map(x=>`<div class="ds-bar-row"><div class="top"><b>${esc(x.nombre)}</b><span>${fmt(x.sedes_clubes)} sedes de clubes</span></div><div class="ds-track"><i style="width:${Math.max(3,x.sedes_clubes/max*100)}%"></i></div></div>`).join('');
  }
  function renderSources(){
    $('#ds-sources').innerHTML=(state.data.fuentes||[]).map(x=>`<div class="ds-source"><div><b>${esc(x.nombre)}</b><small>${x.recurso_modificado?`Recurso: ${esc(String(x.recurso_modificado).slice(0,10))}`:`Procesado: ${esc(x.generado_cepoes||'—')}`}</small></div>${x.url?`<a href="${esc(x.url)}" target="_blank" rel="noopener">Fuente ↗</a>`:''}</div>`).join('');
    $('#ds-access-sources').innerHTML=(state.access.fuentes||[]).map(x=>`<div class="ds-source"><div><b>${esc(x.nombre)}</b><small>${esc(x.detalle||'')}</small></div>${x.url?`<a href="${esc(x.url)}" target="_blank" rel="noopener">Fuente ↗</a>`:''}</div>`).join('');
  }
  function renderBridge(){
    $('#ds-bridge-est').textContent=fmt(state.data.resumen.estaciones_saludables); $('#ds-bridge-cesac').textContent=fmt(state.data.resumen.cesac);
  }
  function renderAll(){renderMap();renderSelected();renderRanking();renderAccess();}
  function bind(){
    $('#ds-metric').addEventListener('change',e=>{state.metric=e.target.value;renderAll();});
    $('#ds-comuna').addEventListener('change',e=>{state.comuna=e.target.value;renderAll();});
    $('#ds-search').addEventListener('input',e=>{state.q=norm(e.target.value.trim());renderMap();});
    $('#ds-access-universe').addEventListener('change',e=>{state.accessUniverse=e.target.value;renderAccess();renderSelected();});
    $('#ds-access-distance').addEventListener('change',e=>{state.accessDistance=e.target.value;renderAccess();renderSelected();});
    $$('.ds-layer').forEach(b=>b.addEventListener('click',()=>{const l=b.dataset.layer;if(state.layers.has(l))state.layers.delete(l);else state.layers.add(l);b.classList.toggle('active',state.layers.has(l));renderMap();}));
  }
  async function init(){
    try{
      const [dr,ar,gr]=await Promise.all([fetch(DATA,{cache:'no-store'}),fetch(ACCESS,{cache:'no-store'}),fetch(GEO)]); if(!dr.ok||!ar.ok||!gr.ok)throw new Error('No se pudieron cargar los datos');
      state.data=await dr.json(); state.access=await ar.json(); state.geo=await gr.json();
      renderKpis();renderActivities();renderSources();renderBridge();bind();renderAll();
      $('#ds-loading').hidden=true;
    }catch(err){console.error(err);$('#ds-loading').innerHTML='<div class="ds-error"><b>No pudimos cargar el tablero.</b> El pipeline evita publicar archivos inválidos. Probá recargar la página.</div>';}
  }
  document.addEventListener('DOMContentLoaded',init);
})();
