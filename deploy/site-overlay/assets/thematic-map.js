const GEO_BARRIOS_THEME=[
  'https://cdn.buenosaires.gob.ar/datosabiertos/datasets/innovacion-transformacion-digital/barrios/barrios.geojson',
  'https://raw.githubusercontent.com/OpenDataCordoba/barrios/refs/heads/main/caba_barrios.geojson'
];
document.addEventListener('DOMContentLoaded',async()=>{try{
  const C=CEPOES,S=await C.territorySummary();
  const $=s=>document.querySelector(s),mode=$('#thematic-mode'),indicator=$('#thematic-indicator'),measure=$('#thematic-measure'),tip=$('#thematic-tooltip'),status=$('#thematic-map-status');
  const pageDate=$('#data-date');if(pageDate)pageDate.textContent=S?.generado?C.dateLabel(String(S.generado).slice(0,10)):'Fecha no informada';
  if(!S){status.textContent='El resumen territorial todavía no está disponible.';return}
  const params=new URLSearchParams(location.search),highlight=params.get('barrio')||'';
  const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  const slug=s=>norm(s).replace(/ /g,'-');
  const aliases={'paternal':'la-paternal','la-paternal':'la-paternal','villa-gral-mitre':'villa-general-mitre','villa-general-mitre':'villa-general-mitre','montserrat':'monserrat','monserrat':'monserrat','boca':'la-boca','la-boca':'la-boca'};
  const keyFor=name=>{const k=aliases[slug(name)]||slug(name);if(S.barrios[k])return k;return Object.keys(S.barrios).find(x=>norm(S.barrios[x].nombre)===norm(name))||k};
  const featuredOrder=['educacion','salud','mayores','infancias','cultura','deporte','seguridad','movilidad','servicios','ambiente'];
  const categories={educacion:'Educación',salud:'Salud y bienestar',cultura:'Cultura y comunidad',deporte:'Deporte',cuidados:'Cuidados y desarrollo social',seguridad:'Seguridad y emergencias',movilidad:'Movilidad',ambiente:'Ambiente y espacio público',abastecimiento:'Abastecimiento',gestion:'Gestión pública y trabajo',mayores:'Personas mayores',genero:'Género y acompañamiento',infancias:'Infancias y familias',animales:'Animales y bienestar animal',patrimonio:'Patrimonio y memoria',servicios:'Servicios y trámites',conectividad:'Conectividad'};
  let geo=null;
  async function loadGeo(){for(const u of GEO_BARRIOS_THEME){try{const g=await d3.json(u);if(g&&g.features?.length===48)return g}catch(e){}}throw new Error('cartografía no disponible')}
  function featuredOptions(){const first=Object.values(S.barrios)[0]?.destacados||{};indicator.innerHTML=featuredOrder.filter(id=>first[id]).map(id=>`<option value="${id}">${first[id].label||id}</option>`).join('')}
  function layerOptions(){const xs=Object.entries(S.layers||{}).sort((a,b)=>(categories[a[1].category]||a[1].category||'').localeCompare(categories[b[1].category]||b[1].category||'','es')||String(a[1].label).localeCompare(String(b[1].label),'es'));indicator.innerHTML=xs.map(([id,x])=>`<option value="${id}">${categories[x.category]||x.category} · ${x.label}</option>`).join('')}
  function populate(){const prev=indicator.value;if(mode.value==='featured')featuredOptions();else layerOptions();if([...indicator.options].some(o=>o.value===prev))indicator.value=prev;const p=mode.value==='featured'?params.get('dimension'):params.get('capa');if(p&&[...indicator.options].some(o=>o.value===p))indicator.value=p;render()}
  function valueFor(b){const id=indicator.value;if(mode.value==='featured'){const x=b.destacados?.[id];if(!x)return null;if(id==='ambiente')return measure.value==='rate'?Number(x.m2_hab):Number(x.valor);return measure.value==='rate'?Number(x.tasa_10k):Number(x.valor)}const n=Number(b.capas?.[id]||0);return measure.value==='rate'?(b.poblacion?n/b.poblacion*10000:0):n}
  function labelFor(v){if(v==null||!Number.isFinite(v))return 's/d';if(mode.value==='featured'&&indicator.value==='ambiente'&&measure.value==='rate')return C.n1.format(v)+' m²/hab.';if(measure.value==='rate')return C.n1.format(v)+' cada 10.000 hab.';return C.n.format(Math.round(v))}
  function currentMeta(){if(mode.value==='featured'){const x=Object.values(S.barrios)[0]?.destacados?.[indicator.value]||{};return {label:x.label||indicator.value,description:'Dimensión sintética construida con una selección de capas afines.',historico:false,last:null,category:indicator.value}}const x=S.layers[indicator.value]||{};return {label:x.label||indicator.value,description:`Capa individual · ${categories[x.category]||x.category||'Oferta territorial'}.`,historico:!!x.historico,last:x.source_last_modified,source:x.source_url,category:x.category}}
  function syncUrl(){const p=new URLSearchParams();p.set(mode.value==='featured'?'dimension':'capa',indicator.value);p.set('medida',measure.value);if(highlight)p.set('barrio',highlight);history.replaceState(null,'',location.pathname+'?'+p.toString())}
  function render(){if(!geo)return;const meta=currentMeta(),rows=Object.entries(S.barrios).map(([key,b])=>({key,b,value:valueFor(b)})).filter(x=>Number.isFinite(x.value));const max=d3.max(rows,d=>d.value)||1,min=d3.min(rows,d=>d.value)||0,scale=d3.scaleLinear().domain([min,max===min?min+1:max]).range([0,1]);const color=v=>d3.interpolateRgb('#D9F1FB','#0079A8')(scale(v));
    const svg=d3.select('#thematic-map svg'),projection=d3.geoMercator().fitExtent([[25,25],[735,620]],geo),path=d3.geoPath(projection);svg.selectAll('*').remove();
    svg.selectAll('path').data(geo.features).join('path').attr('class','map-path').attr('d',path).attr('fill',f=>{const b=S.barrios[keyFor(f.properties?.nombre??f.properties?.BARRIO??'')];return b?color(valueFor(b)):getComputedStyle(document.documentElement).getPropertyValue('--grid')}).attr('stroke-width',f=>norm(f.properties?.nombre??f.properties?.BARRIO??'')===norm(highlight)?3:1.2).attr('tabindex',0)
      .on('mouseenter focus',function(ev,f){const name=f.properties?.nombre??f.properties?.BARRIO??'',b=S.barrios[keyFor(name)],v=b?valueFor(b):null;tip.style.display='block';tip.innerHTML=`<b>${name}</b><br>${meta.label}: ${labelFor(v)}<br><span>${b?C.n.format(b.poblacion)+' habitantes':'sin población asociada'}</span>`})
      .on('mousemove',ev=>{if(Number.isFinite(ev.offsetX)){tip.style.left=(ev.offsetX+12)+'px';tip.style.top=(ev.offsetY+12)+'px'}}).on('mouseleave blur',()=>tip.style.display='none')
      .on('click',(ev,f)=>{const name=f.properties?.nombre??f.properties?.BARRIO??'',k=keyFor(name);if(S.barrios[k])location.href='/territorio/barrios/'+k+'/'});
    status.textContent='48 barrios oficiales · fuente cartográfica: BA Data (GCBA)';
    const sorted=[...rows].sort((a,b)=>b.value-a.value),hi=sorted[0],lo=sorted[sorted.length-1],sum=rows.reduce((a,x)=>a+x.value,0),avg=rows.length?sum/rows.length:0;
    $('#thematic-summary').innerHTML=`<div class="thematic-stat"><span>Indicador</span><strong>${meta.label}</strong><small>${measure.value==='rate'?'Comparación relativa':'Cantidad de registros'}</small></div><div class="thematic-stat"><span>Mayor valor</span><strong>${hi?labelFor(hi.value):'—'}</strong><small>${hi?hi.b.nombre:'—'}</small></div><div class="thematic-stat"><span>Menor valor</span><strong>${lo?labelFor(lo.value):'—'}</strong><small>${lo?lo.b.nombre:'—'} · promedio barrial ${labelFor(avg)}</small></div>`;
    $('#thematic-title').textContent=meta.label;$('#thematic-desc').textContent=meta.description;
    const source=[];if(meta.historico)source.push('<span class="thematic-history">Fuente histórica / relevamiento específico</span>');if(meta.last)source.push(`<span>Fecha oficial de la fuente: <strong>${C.dateLabel(String(meta.last).slice(0,10))}</strong></span>`);if(meta.source)source.push(`<a class="more" href="${meta.source}" target="_blank" rel="noopener">Abrir fuente oficial ↗</a>`);if(mode.value==='featured')source.push('<span>La dimensión combina una selección de capas y usa población del Censo 2022 para las tasas.</span>');$('#thematic-source').innerHTML=source.join('');
    $('#thematic-ranking').innerHTML=sorted.slice(0,8).map((x,i)=>`<li><b>${i+1}</b><a href="/territorio/barrios/${x.key}/">${x.b.nombre}</a><strong>${labelFor(x.value)}</strong></li>`).join('');
    const gapLink=$('#thematic-gap-link');if(gapLink&&mode.value==='featured')gapLink.href=`/territorio/brechas/?dimension=${encodeURIComponent(indicator.value)}&medida=${encodeURIComponent(measure.value)}`;else if(gapLink)gapLink.href='/territorio/brechas/';
    syncUrl();
  }
  geo=await loadGeo();
  const requestedMeasure=params.get('medida');if(requestedMeasure==='count'||requestedMeasure==='rate')measure.value=requestedMeasure;
  if(params.get('capa'))mode.value='layer';
  populate();mode.addEventListener('change',populate);indicator.addEventListener('change',render);measure.addEventListener('change',render);
}catch(e){console.warn('Mapa temático:',e);const st=document.getElementById('thematic-map-status'),dt=document.getElementById('data-date');if(st)st.textContent='No se pudo cargar el mapa temático. Probá nuevamente más tarde.';if(dt)dt.textContent='Fecha no informada'}});
