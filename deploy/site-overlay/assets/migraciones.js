const MIG_GEO=[
  'https://cdn.buenosaires.gob.ar/datosabiertos/datasets/innovacion-transformacion-digital/comunas/comunas.geojson',
  'https://raw.githubusercontent.com/OpenDataCordoba/barrios/refs/heads/main/caba_comunas.geojson'
];

document.addEventListener('DOMContentLoaded', async()=>{
  const nf=new Intl.NumberFormat('es-AR'), n1=new Intl.NumberFormat('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1});
  const pct=v=>n1.format(v)+'%';
  const D=await fetch('/assets/data/migraciones.json?v=235').then(r=>{if(!r.ok)throw new Error('datos');return r.json()});
  const h=D.headline, eah=h.eah, latest=D.latest||{};
  const set=(id,t)=>{const e=document.getElementById(id);if(e)e.textContent=t};
  set('mig-kpi-eah-intl',pct(eah.migracion_internacional_pct)); set('mig-kpi-eah-internal',pct(eah.migracion_interna_pct));
  set('mig-meta-eah','EAH '+eah.year); set('mig-kpi-eah-intl-year','EAH '+eah.year); set('mig-kpi-eah-internal-year','EAH '+eah.year);
  set('mig-internal-pba',pct(eah.prov_ba_pct));set('mig-internal-other',pct(eah.otra_provincia_pct));set('mig-internal-total',pct(eah.migracion_interna_pct));
  ['mig-internal-pba-year','mig-internal-other-year','mig-internal-total-year'].forEach(id=>set(id,'EAH '+eah.year));
  set('mig-kpi-censo-intl',nf.format(h.censo2022.otro_pais)); set('mig-kpi-censo-intl-pct',pct(h.censo2022.otro_pais_pct)+' de la población censada');
  set('mig-kpi-censo-internal',nf.format(h.censo2022.otra_provincia)); set('mig-kpi-censo-internal-pct',pct(h.censo2022.otra_provincia_pct)+' de la población censada');

  set('mig-country-year','EAH '+D.countries.year); set('mig-country-period',`${D.countries.base_year||2015}–${D.countries.year}`); set('mig-community-year','EAH '+D.countries.year);
  const countryBox=document.getElementById('mig-country-bars');
  const crows=D.countries.rows.filter(x=>x.pais!=='Otros países'); const maxC=Math.max(...crows.map(x=>x.pct_2024));
  countryBox.innerHTML=crows.slice(0,10).map(x=>`<div class="migration-bar-row"><div><b>${x.pais}</b><span>${pct(x.pct_2024)}</span></div><div class="migration-bar-track"><i style="width:${x.pct_2024/maxC*100}%"></i></div></div>`).join('');
  const changes=[...crows].sort((a,b)=>Math.abs(b.cambio_pp)-Math.abs(a.cambio_pp)).slice(0,7);
  document.getElementById('mig-country-change').innerHTML=changes.map(x=>`<div class="migration-change ${x.cambio_pp>=0?'up':'down'}"><span>${x.pais}</span><strong>${x.cambio_pp>=0?'+':''}${n1.format(x.cambio_pp)} pp</strong><small>${n1.format(x.pct_2015)}% → ${n1.format(x.pct_2024)}%</small></div>`).join('');
  const topCommunities=[...crows].sort((a,b)=>b.pct_2024-a.pct_2024).slice(0,4);
  const cg=document.getElementById('mig-community-grid'); if(cg)cg.innerHTML=topCommunities.map((x,i)=>`<article class="migration-community-card"><span class="eyebrow">${String(i+1).padStart(2,'0')} · ${D.countries.year}</span><h3>${x.pais}</h3><strong>${pct(x.pct_2024)}</strong><p>de la población extranjera relevada por la EAH.</p><small>${D.countries.base_year||2015}: ${n1.format(x.pct_2015)}% · cambio: ${x.cambio_pp>=0?'+':''}${n1.format(x.cambio_pp)} pp</small></article>`).join('');

  const displayDesc=i=>({
    '1':'Retiro · San Nicolás · Puerto Madero · San Telmo · Monserrat · Constitución','2':'Recoleta','3':'Balvanera · San Cristóbal','4':'La Boca · Barracas · Parque Patricios · Nueva Pompeya','5':'Almagro · Boedo','6':'Caballito','7':'Flores · Parque Chacabuco','8':'Villa Soldati · Villa Riachuelo · Villa Lugano','9':'Liniers · Mataderos · Parque Avellaneda','10':'Villa Real · Monte Castro · Versalles · Floresta · Vélez Sarsfield · Villa Luro','11':'Villa General Mitre · Villa Devoto · Villa del Parque · Villa Santa Rita','12':'Coghlan · Saavedra · Villa Urquiza · Villa Pueyrredón','13':'Núñez · Belgrano · Colegiales','14':'Palermo','15':'Chacarita · Villa Crespo · La Paternal · Villa Ortúzar · Agronomía · Parque Chas'}[i]||'');
  const metrics=[
   {k:'censo_intl',label:'Migración internacional · Censo 2022',short:'Internacional · Censo 2022',source:'Censo 2022',desc:'Población nacida en otro país sobre la población en viviendas particulares.',get:i=>D.communes[i].censo2022.otro_pais_pct,fmt:pct,detail:i=>`${nf.format(D.communes[i].censo2022.otro_pais)} personas nacidas en otro país.`},
   {k:'eah_intl',label:`Migración internacional · EAH ${eah.year}`,short:`Internacional · EAH ${eah.year}`,source:`EAH ${eah.year}`,desc:'Estimación anual: país limítrofe + país no limítrofe. Los valores comunales tienen error muestral.',get:i=>D.communes[i].eah.migracion_internacional_pct,fmt:pct,detail:i=>`Limítrofes: ${pct(D.communes[i].eah.pais_limitrofe_pct)} · No limítrofes: ${pct(D.communes[i].eah.pais_no_limitrofe_pct)}.`},
   {k:'censo_internal',label:'Migración interna · Censo 2022',short:'Interna · Censo 2022',source:'Censo 2022',desc:'Población nacida en otra provincia argentina sobre la población en viviendas particulares.',get:i=>D.communes[i].censo2022.otra_provincia_pct,fmt:pct,detail:i=>`${nf.format(D.communes[i].censo2022.otra_provincia)} personas nacidas en otra provincia.`},
   {k:'eah_internal',label:`Migración interna · EAH ${eah.year}`,short:`Interna · EAH ${eah.year}`,source:`EAH ${eah.year}`,desc:'Estimación anual: Provincia de Buenos Aires + otras provincias.',get:i=>D.communes[i].eah.migracion_interna_pct,fmt:pct,detail:i=>`PBA: ${pct(D.communes[i].eah.prov_ba_pct)} · Otras provincias: ${pct(D.communes[i].eah.otra_provincia_pct)}.`}
  ];
  let current=metrics[0], geo=null;
  const controls=document.getElementById('mig-map-controls'); controls.innerHTML=metrics.map((x,i)=>`<button class="chip ${i===0?'active':''}" data-migmetric="${x.k}">${x.short}</button>`).join('');
  controls.addEventListener('click',e=>{const b=e.target.closest('[data-migmetric]');if(!b)return;current=metrics.find(x=>x.k===b.dataset.migmetric);controls.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===b));drawMap();});
  const communeId=f=>String(f?.properties?.comuna ?? f?.properties?.COMUNAS ?? f?.properties?.COMUNA ?? '');
  async function loadGeo(){for(const u of MIG_GEO){try{const g=await d3.json(u);if(g?.features?.length>=15)return g}catch(e){}}throw new Error('geo')}
  try{geo=await loadGeo();set('migration-map-status','Cartografía de comunas · BA Data (GCBA)');drawMap()}catch(e){set('migration-map-status','No se pudo cargar la cartografía. El ranking sigue disponible.');renderRanking()}
  function drawMap(){
    set('mig-map-title',current.label); set('mig-map-desc',current.desc); set('mig-map-source-label',current.source);
    if(!geo){renderRanking();return}
    const fs=geo.features.filter(f=>D.communes[communeId(f)]), vals=fs.map(f=>current.get(communeId(f))), ext=d3.extent(vals), mid=(ext[0]+ext[1])/2;
    const scale=d3.scaleLinear().domain([ext[0],mid,ext[1]]).range(['#E8F6FD','#55BDE5','#0079A8']);
    const svg=d3.select('#migration-map svg'); svg.selectAll('*').remove();
    const fc={type:'FeatureCollection',features:fs}, proj=d3.geoMercator().fitExtent([[22,18],[738,626]],fc), path=d3.geoPath(proj), tip=document.getElementById('migration-tooltip');
    svg.selectAll('path').data(fs).join('path').attr('class','map-path').attr('d',path).attr('fill',f=>scale(current.get(communeId(f)))).attr('tabindex',0)
      .attr('aria-label',f=>`Comuna ${communeId(f)} ${current.label}: ${current.fmt(current.get(communeId(f)))}`)
      .on('mouseenter focus',(ev,f)=>show(ev,f)).on('mousemove',ev=>position(ev,tip)).on('mouseleave blur',()=>tip.style.display='none').on('click',(ev,f)=>select(f));
    svg.selectAll('text').data(fs).join('text').attr('class','map-label').attr('transform',f=>`translate(${path.centroid(f)})`).attr('text-anchor','middle').attr('dy','.35em').text(f=>'C'+communeId(f)); renderRanking();
  }
  function show(ev,f){const i=communeId(f),tip=document.getElementById('migration-tooltip');tip.innerHTML=`<b>Comuna ${i}</b><br>${displayDesc(i)}<br><strong>${current.fmt(current.get(i))}</strong>`;tip.style.display='block';position(ev,tip);select(f)}
  function position(ev,tip){if(Number.isFinite(ev?.offsetX)){tip.style.left=(ev.offsetX+15)+'px';tip.style.top=(ev.offsetY+15)+'px'}}
  function select(f){const i=communeId(f);set('mig-selected-title','Comuna '+i);document.getElementById('mig-selected-desc').innerHTML=`${displayDesc(i)}<br><b>${current.label}:</b> ${current.fmt(current.get(i))}<br>${current.detail(i)}`}
  function renderRanking(){const rows=Object.keys(D.communes).map(i=>({i,v:current.get(i)})).sort((a,b)=>b.v-a.v);set('mig-rank-note',current.label);document.querySelector('#mig-ranking tbody').innerHTML=rows.map((x,j)=>`<tr><td>${j+1}</td><td><b>Comuna ${x.i}</b><br><small>${displayDesc(x.i)}</small></td><td class="num"><b>${current.fmt(x.v)}</b></td><td>${current.detail(x.i)}</td></tr>`).join('')}

  const H=D.recent_migration, svg=d3.select('#mig-history-chart'), W=920,Ht=360,m={l:58,r:28,t:24,b:48}, iw=W-m.l-m.r, ih=Ht-m.t-m.b;
  const x=d3.scalePoint().domain(H.years).range([m.l,m.l+iw]).padding(.2), y=d3.scaleLinear().domain([0,65]).range([m.t+ih,m.t]);
  svg.selectAll('*').remove(); svg.append('g').attr('transform',`translate(0,${m.t+ih})`).call(d3.axisBottom(x).tickFormat(d3.format('d'))).attr('class','migration-axis'); svg.append('g').attr('transform',`translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d=>d+'%')).attr('class','migration-axis');
  const series=[['Provincia de Buenos Aires',H.prov_ba,'#00A7E1'],['Otra provincia',H.otra_provincia,'#1B8F5F'],['Exterior',H.exterior,'#7048C4']]; const line=d3.line().x((d,i)=>x(H.years[i])).y(d=>y(d));
  series.forEach(([name,vals,color])=>{svg.append('path').datum(vals).attr('fill','none').attr('stroke',color).attr('stroke-width',4).attr('d',line);svg.selectAll('.p-'+name.replace(/\W/g,'')).data(vals).enter().append('circle').attr('cx',(d,i)=>x(H.years[i])).attr('cy',d=>y(d)).attr('r',4.5).attr('fill',color);});
  document.getElementById('mig-history-legend').innerHTML=series.map(([n,v,c])=>`<span><i style="background:${c}"></i><b>${n}</b><small>${pct(v[v.length-1])} en 2022</small></span>`).join('');

  function compareBars(id,obj,labels){const el=document.getElementById(id), mx=Math.max(...Object.values(obj));el.innerHTML=Object.entries(obj).map(([k,v])=>`<div class="migration-compare-row"><div><span>${labels[k]||k}</span><strong>${pct(v)}</strong></div><div class="migration-compare-track"><i style="width:${v/mx*100}%"></i></div></div>`).join('')}
  const act=D.socioeconomic.activity, sch=D.socioeconomic.schooling, pov=D.socioeconomic.poverty_multidimensional;
  set('mig-activity-year',`Actividad · ${act.year}`);set('mig-schooling-year',`Educación · ${sch.year}`);set('mig-poverty-year',`Pobreza multidimensional · ${pov.year}`);
  compareBars('mig-activity-bars',act.values,{total:'Total CABA',caba:'Nacidos en CABA',resto_pais:'Resto del país',exterior:'Nacidos en el exterior'});
  compareBars('mig-schooling-bars',sch.values,{total:'Total CABA',caba:'Nacidos en CABA',resto_pais:'Resto del país',exterior:'Nacidos en el exterior'});
  compareBars('mig-poverty-bars',pov.values,{total:'Total CABA',caba:'Nacidos en CABA',prov_ba:'Provincia de Buenos Aires',otra_provincia:'Otra provincia',pais_limitrofe:'País limítrofe',otro_pais:'Otro país'});
  const updated=D.updated_at?new Date(D.updated_at):null; set('mig-refresh-status',`Actualización automática activa · último conjunto validado: ${updated&&!Number.isNaN(updated)?updated.toLocaleString('es-AR',{dateStyle:'medium',timeStyle:'short'}):D.generated||'s/d'}.`);
}).catch(e=>{console.warn('Migraciones:',e);const s=document.getElementById('migration-map-status');if(s)s.textContent='No se pudieron cargar los datos de migraciones.'});
