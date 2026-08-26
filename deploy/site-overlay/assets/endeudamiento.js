(()=>{
'use strict';

// Producción: cuando la rama v2.30 llegue a main, el sitio toma automáticamente
// el manifest más nuevo de GitHub. El ZIP incluye junio 2026 como fallback local.
const DATA_BASES=[
  {id:'github',url:'https://raw.githubusercontent.com/cepoes100b/CEPOES/main/datos/endeudamiento/'},
  {id:'local',url:'/assets/data/endeudamiento/'}
];
const GEO_URLS=[
  'https://cdn.buenosaires.gob.ar/datosabiertos/datasets/innovacion-transformacion-digital/barrios/barrios.geojson',
  'https://raw.githubusercontent.com/OpenDataCordoba/barrios/refs/heads/main/caba_barrios.geojson'
];
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const fmtInt=new Intl.NumberFormat('es-AR',{maximumFractionDigits:0});
const fmt1=new Intl.NumberFormat('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1});
const fmt2=new Intl.NumberFormat('es-AR',{minimumFractionDigits:2,maximumFractionDigits:2});
const state={manifest:null,data:null,dataBase:null,geo:null,period:null,selectedName:null,rows:[],periodCache:new Map()};

const metricMeta={
  tasa_mora_pct:{label:'Tasa de mora del monto',short:'Tasa de mora',desc:'Proporción del monto en mora sobre el monto total adeudado.',fmt:v=>fmt2.format(v)+'%'},
  incidencia_mora_pct:{label:'Personas deudoras en mora',short:'Deudores en mora',desc:'Porcentaje de personas deudoras con mora sobre el total de deudores.',fmt:v=>fmt2.format(v)+'%'},
  personas_mora:{label:'Personas en mora',short:'Personas en mora',desc:'Cantidad estimada de personas deudoras en situaciones 3, 4 o 5.',fmt:v=>fmtInt.format(Math.round(v))},
  deudores:{label:'Personas deudoras',short:'Deudores',desc:'Cantidad estimada de personas con deuda en cada barrio.',fmt:v=>fmtInt.format(Math.round(v))},
  deuda_total_pesos:{label:'Deuda total',short:'Deuda total',desc:'Monto total adeudado, expresado en pesos corrientes.',fmt:v=>money(v)},
  deuda_mora_pesos:{label:'Deuda en mora',short:'Deuda en mora',desc:'Monto adeudado en situaciones 3, 4 o 5, expresado en pesos corrientes.',fmt:v=>money(v)}
};
const ageLabels={le25:'Hasta 25 años','26_35':'26 a 35 años','36_45':'36 a 45 años','46_55':'46 a 55 años','56_65':'56 a 65 años','66_75':'66 a 75 años',gt75:'Más de 75 años',desconocida:'Edad no disponible'};
const sexLabels={F:'Mujeres',M:'Varones'};
const categoryLabels={entidad_financiera:'Entidades financieras',emisora_tarjeta:'Emisoras de tarjetas',otro_pnfc:'Otros proveedores no financieros'};
const aliases={
  'boca':'la-boca','la-boca':'la-boca','paternal':'la-paternal','la-paternal':'la-paternal',
  'villa-gral-mitre':'villa-general-mitre','villa-general-mitre':'villa-general-mitre',
  'nunez':'nunez','agronomia':'agronomia','constitucion':'constitucion','monserrat':'monserrat',
  'villa-ortuzar':'villa-ortuzar','villa-pueyrredon':'villa-pueyrredon','velez-sarsfield':'velez-sarsfield'
};

function norm(s){return String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(gral|general)\.?\b/g,'general').replace(/^la\s+/,'').replace(/[^a-z0-9]+/g,' ').trim()}
function slug(s){return norm(s).replace(/\s+/g,'-')}
function barrioSlug(name){const x=slug(name);return aliases[x]||x}
function barrioLabel(name){return name==='Boca'?'La Boca':name==='Nunez'?'Núñez':name}
function pct(num,den){return den?Number(num)/Number(den)*100:0}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function escAttr(s){return esc(s)}
function money(v){const n=Number(v||0);if(Math.abs(n)>=1e12)return '$'+fmt2.format(n/1e12)+' billones';if(Math.abs(n)>=1e9)return '$'+fmt2.format(n/1e9)+' mil M';if(Math.abs(n)>=1e6)return '$'+fmt1.format(n/1e6)+' M';return '$'+fmtInt.format(n)}
function periodLabel(id){if(!/^\d{4}-\d{2}$/.test(String(id||'')))return id||'—';const d=new Date(id+'-01T00:00:00Z');const s=new Intl.DateTimeFormat('es-AR',{month:'long',year:'numeric',timeZone:'UTC'}).format(d);return s.charAt(0).toUpperCase()+s.slice(1)}
function featureName(f){return f?.properties?.nombre??f?.properties?.BARRIO??f?.properties?.barrio??f?.properties?.NOMBRE??''}

async function fetchJSON(base,path){const r=await fetch(base+path.replace(/^\//,''),{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status+' '+path);return r.json()}
async function loadManifest(){
  const tries=await Promise.all(DATA_BASES.map(async b=>{try{return {base:b,manifest:await fetchJSON(b.url,'manifest.json')}}catch(e){return null}}));
  const valid=tries.filter(Boolean);
  if(!valid.length)throw new Error('No se encontró el manifest de Endeudamiento');
  valid.sort((a,b)=>String(b.manifest.ultimo_periodo||'').localeCompare(String(a.manifest.ultimo_periodo||'')));
  state.dataBase=valid[0].base;
  return valid[0].manifest;
}
async function getPeriod(period){
  if(state.periodCache.has(period))return state.periodCache.get(period);
  const file=state.manifest.archivos?.[period]||`${period}.json`;
  const order=[state.dataBase,...DATA_BASES.filter(b=>b.id!==state.dataBase?.id)].filter(Boolean);
  let lastError=null;
  for(const b of order){try{const x=await fetchJSON(b.url,file);state.periodCache.set(period,x);return x}catch(e){lastError=e}}
  throw lastError||new Error('No se pudo cargar '+file);
}
async function loadGeo(){for(const u of GEO_URLS){try{const g=await d3.json(u);if(g&&g.features?.length===48)return g}catch(e){}}throw new Error('No se pudo cargar la cartografía barrial')}

function selectedFilters(){return {
  sexo:$('#debt-sex').value==='__ALL__'?null:$('#debt-sex').value,
  edad:$('#debt-age').value==='__ALL__'?null:$('#debt-age').value,
  acreedor:$('#debt-category').value==='__ALL__'?null:$('#debt-category').value
}}
function hasFilters(f=selectedFilters()){return !!(f.sexo||f.edad||f.acreedor)}
function sameFilters(a,b){return ['sexo','edad','acreedor'].every(k=>(a?.[k]??null)===(b?.[k]??null))}
function findSegment(data,filters){return (data.segmentos||[]).find(s=>sameFilters(s.filtros||{},filters))||null}
function rowsFromSegment(data,segment){
  if(!segment)return [];
  const names=data.barrios||[],metrics=data.metricas_segmento||[];
  const idx=Object.fromEntries(metrics.map((m,i)=>[m,i]));
  return names.map((nombre,i)=>{
    const a=segment.datos?.[i]||[];
    const r={nombre,geo_id:nombre};
    for(const m of metrics)r[m]=Number(a[idx[m]]||0);
    r.incidencia_mora_pct=pct(r.personas_mora,r.deudores);
    r.tasa_mora_pct=pct(r.deuda_mora_pesos,r.deuda_total_pesos);
    return r;
  });
}
function sumRows(rows){
  const x={deudores:0,personas_mora:0,deuda_total_pesos:0,deuda_mora_pesos:0};
  for(const r of rows){for(const k of Object.keys(x))x[k]+=Number(r[k]||0)}
  x.incidencia_mora_pct=pct(x.personas_mora,x.deudores);
  x.tasa_mora_pct=pct(x.deuda_mora_pesos,x.deuda_total_pesos);
  return x;
}
function currentKpis(){return hasFilters()?sumRows(state.rows):(state.data?.caba?.total||sumRows(state.rows))}
function filtersLabel(){const parts=[];const cat=$('#debt-category'),sex=$('#debt-sex'),age=$('#debt-age');if(cat.value!=='__ALL__')parts.push(cat.options[cat.selectedIndex]?.text);if(sex.value!=='__ALL__')parts.push(sex.options[sex.selectedIndex]?.text);if(age.value!=='__ALL__')parts.push(age.options[age.selectedIndex]?.text);return parts.length?parts.join(' · '):'Todos los deudores'}
function updateKPIs(){
  const k=currentKpis();
  const vals=[fmtInt.format(Math.round(k.deudores||0)),fmtInt.format(Math.round(k.personas_mora||0)),fmt2.format(k.incidencia_mora_pct||0)+'%',fmt2.format(k.tasa_mora_pct||0)+'%',money(k.deuda_total_pesos||0),money(k.deuda_mora_pesos||0)];
  $$('#debt-kpis .value').forEach((el,i)=>el.textContent=vals[i]);
  $('#debt-filter-summary').textContent=filtersLabel();
  $('#debt-period-label').textContent=periodLabel(state.period);
}
function updateCoverage(){
  const c=state.data?.caba?.cobertura_mapa_sobre_caba||{};
  const el=$('#debt-coverage-label');
  if(el)el.textContent=`${fmt1.format(c.deudores_pct||0)}% de los deudores y ${fmt1.format(c.deuda_total_pct||0)}% de la deuda total`;
}
function metricValue(r){const m=$('#debt-metric').value;return Number(r?.[m]??NaN)}
function metricFmt(v){return metricMeta[$('#debt-metric').value].fmt(v)}
function rowMap(){return new Map(state.rows.map(r=>[norm(r.nombre),r]))}
function rowForFeature(f){const name=featureName(f);const rm=rowMap();return rm.get(norm(name))||state.rows.find(r=>slug(r.nombre)===slug(name))||null}
function colorScale(vals){const finite=vals.filter(Number.isFinite).sort(d3.ascending);let lo=d3.quantile(finite,.05)??d3.min(finite)??0,hi=d3.quantile(finite,.95)??d3.max(finite)??1;if(hi<=lo)hi=lo+1;return d3.scaleSequential().domain([lo,hi]).interpolator(t=>d3.interpolateRgbBasis(['#D8EFF5','#6FB7CC','#135E7B','#8B2B3B'])(Math.max(0,Math.min(1,t))))}

function renderMap(){
  if(!state.geo||!state.rows.length)return;
  const meta=metricMeta[$('#debt-metric').value],vals=state.rows.map(metricValue).filter(Number.isFinite),scale=colorScale(vals);
  const mobile=window.matchMedia('(max-width:480px)').matches,vw=mobile?620:760,vh=mobile?760:650;
  const svg=d3.select('#debt-map svg').attr('viewBox',`0 0 ${vw} ${vh}`),proj=d3.geoMercator().fitExtent([[22,20],[vw-22,vh-70]],state.geo),path=d3.geoPath(proj),tip=$('#debt-tooltip');
  svg.selectAll('*').remove();
  svg.selectAll('path').data(state.geo.features).join('path')
    .attr('class','map-path').attr('d',path)
    .attr('fill',f=>{const r=rowForFeature(f),v=metricValue(r);return Number.isFinite(v)?scale(v):'var(--grid)'})
    .attr('stroke-width',f=>{const r=rowForFeature(f);return r&&norm(r.nombre)===norm(state.selectedName)?3:1.2})
    .attr('tabindex',0)
    .on('mousemove mouseenter focus',function(ev,f){const r=rowForFeature(f);if(!r)return;tip.style.display='block';tip.innerHTML=`<b>${esc(barrioLabel(r.nombre))}</b><br>${esc(meta.short)}: ${esc(metricFmt(metricValue(r)))}<br><span>${fmtInt.format(Math.round(r.deudores))} deudores · ${fmtInt.format(Math.round(r.personas_mora))} en mora</span>`;if(ev?.offsetX!=null){tip.style.left=Math.min(ev.offsetX+16,520)+'px';tip.style.top=Math.max(8,ev.offsetY-18)+'px'}})
    .on('mouseleave blur',()=>tip.style.display='none')
    .on('click',(ev,f)=>{const r=rowForFeature(f);if(r){state.selectedName=r.nombre;renderAll()}});
  $('#debt-map-status').textContent=`48 barrios · ${periodLabel(state.period)} · ${filtersLabel()}`;
  $('#debt-metric-title').textContent=meta.label;
  $('#debt-metric-description').textContent=meta.desc;
  renderRanking();renderSelected();
}
function renderRanking(){
  const meta=metricMeta[$('#debt-metric').value],sorted=[...state.rows].filter(r=>Number.isFinite(metricValue(r))).sort((a,b)=>metricValue(b)-metricValue(a));
  function list(id,arr){$(id).innerHTML=arr.map((r,i)=>`<li><b>${i+1}</b><button type="button" data-debt-name="${escAttr(r.nombre)}" >${esc(barrioLabel(r.nombre))}</button><strong>${esc(metricFmt(metricValue(r)))}</strong></li>`).join('')}
  list('#debt-ranking-high',sorted.slice(0,7));list('#debt-ranking-low',sorted.slice(-7).reverse());
  $('#debt-high-label').textContent=meta.short;$('#debt-low-label').textContent=meta.short;
  $$('[data-debt-name]').forEach(b=>b.addEventListener('click',()=>{state.selectedName=b.dataset.debtName;renderAll();document.querySelector('#debt-map')?.scrollIntoView({behavior:'smooth',block:'center'})}));
}
function renderSelected(){
  const r=state.rows.find(x=>norm(x.nombre)===norm(state.selectedName));
  if(!r){$('#debt-selected-title').textContent='Elegí un barrio';$('#debt-selected-period').textContent='Tocá el mapa o un ranking.';$('#debt-selected-grid').innerHTML='';$('#debt-selected-link').style.display='none';return}
  $('#debt-selected-title').textContent=barrioLabel(r.nombre);$('#debt-selected-period').textContent=`${periodLabel(state.period)} · ${filtersLabel()}`;
  $('#debt-selected-grid').innerHTML=`<div><span>Deudores</span><b>${fmtInt.format(Math.round(r.deudores))}</b></div><div><span>En mora</span><b>${fmtInt.format(Math.round(r.personas_mora))}</b></div><div><span>Deudores en mora</span><b>${fmt2.format(r.incidencia_mora_pct)}%</b></div><div><span>Tasa de mora</span><b>${fmt2.format(r.tasa_mora_pct)}%</b></div><div><span>Deuda total</span><b>${money(r.deuda_total_pesos)}</b></div><div><span>Deuda en mora</span><b>${money(r.deuda_mora_pesos)}</b></div>`;
  const link=$('#debt-selected-link');link.href='/territorio/barrios/'+barrioSlug(r.nombre)+'/';link.style.display='inline-flex';
}
function renderAll(){updateKPIs();updateCoverage();renderMap();renderEvolution()}

async function loadPeriod(period){
  state.period=period;state.data=await getPeriod(period);
  const seg=findSegment(state.data,selectedFilters());
  if(!seg)throw new Error('La combinación de filtros no está disponible');
  state.rows=rowsFromSegment(state.data,seg);
  if(state.selectedName&&!state.rows.some(x=>norm(x.nombre)===norm(state.selectedName)))state.selectedName=null;
  renderAll();
}
async function reloadSlice(){try{const seg=findSegment(state.data,selectedFilters());if(!seg)throw new Error('No hay datos para esa combinación');state.rows=rowsFromSegment(state.data,seg);renderAll()}catch(e){showError(e)}}

function valueForMetric(x,metric){
  if(metric==='incidencia_mora_pct')return Number(x.incidencia_mora_pct??pct(x.personas_mora,x.deudores));
  if(metric==='tasa_mora_pct')return Number(x.tasa_mora_pct??pct(x.deuda_mora_pesos,x.deuda_total_pesos));
  return Number(x?.[metric]||0);
}
async function loadEvolutionPoints(){
  const filters=selectedFilters(),metric=$('#debt-metric').value,pts=[];
  for(const p of state.manifest.periodos||[]){
    const data=await getPeriod(p);let value;
    const seg=findSegment(data,filters);if(!seg)continue;
    const rows=rowsFromSegment(data,seg);
    if(state.selectedName){const r=rows.find(x=>norm(x.nombre)===norm(state.selectedName));if(!r)continue;value=valueForMetric(r,metric)}
    else if(!hasFilters(filters)){value=valueForMetric(data.caba?.total||sumRows(rows),metric)}
    else value=valueForMetric(sumRows(rows),metric);
    pts.push({period:p,label:periodLabel(p),value});
  }
  return pts;
}
async function renderEvolution(){
  try{
    const section=$('#debt-evolution-section'),periods=state.manifest?.periodos||[];
    if(periods.length<2){if(section)section.hidden=true;return}
    if(section)section.hidden=false;
    const pts=await loadEvolutionPoints(),metric=$('#debt-metric').value,meta=metricMeta[metric],svg=d3.select('#debt-evolution-chart');svg.selectAll('*').remove();if(pts.length<2){if(section)section.hidden=true;return}
    const w=900,h=310,m={l:82,r:25,t:28,b:55},x=d3.scalePoint().domain(pts.map(d=>d.label)).range([m.l,w-m.r]).padding(.45),ext=d3.extent(pts,d=>d.value),pad=(ext[1]-ext[0]||Math.max(1,Math.abs(ext[1])*.1))*.25,y=d3.scaleLinear().domain([Math.max(0,ext[0]-pad),ext[1]+pad]).nice().range([h-m.b,m.t]);
    svg.append('g').attr('transform',`translate(0,${h-m.b})`).call(d3.axisBottom(x)).call(g=>g.selectAll('text').attr('fill','currentColor').style('font-family','Inter')).call(g=>g.selectAll('path,line').attr('stroke','var(--grid)'));
    svg.append('g').attr('transform',`translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(v=>metric.includes('_pesos')?money(v):metric.includes('_pct')?fmt1.format(v)+'%':fmtInt.format(v))).call(g=>g.selectAll('text').attr('fill','currentColor').style('font-family','Inter')).call(g=>g.selectAll('path,line').attr('stroke','var(--grid)'));
    if(pts.length>1){const line=d3.line().x(d=>x(d.label)).y(d=>y(d.value));svg.append('path').datum(pts).attr('fill','none').attr('stroke','var(--marca)').attr('stroke-width',3).attr('d',line)}
    svg.selectAll('.debt-dot').data(pts).join('circle').attr('class','debt-dot').attr('cx',d=>x(d.label)).attr('cy',d=>y(d.value)).attr('r',5).attr('fill','var(--marca-osc)');
    svg.selectAll('.debt-dot-label').data(pts).join('text').attr('class','debt-dot-label').attr('x',d=>x(d.label)).attr('y',d=>y(d.value)-12).attr('text-anchor','middle').text(d=>meta.fmt(d.value));
    $('#debt-evolution-table').innerHTML=pts.map(d=>`<div><span>${esc(d.label)}</span><strong>${esc(meta.fmt(d.value))}</strong></div>`).join('');
    const r=state.rows.find(x=>norm(x.nombre)===norm(state.selectedName));$('#debt-evolution-scope').textContent=(r?barrioLabel(r.nombre):'CABA')+' · '+filtersLabel();
  }catch(e){console.error('evolution',e)}
}

function fillOptions(data){
  const period=$('#debt-period');period.innerHTML=(state.manifest.periodos||[]).map(p=>`<option value="${escAttr(p)}">${esc(periodLabel(p))}</option>`).join('');period.value=state.manifest.ultimo_periodo;
  $('#debt-category').innerHTML='<option value="__ALL__">Todos</option>'+(data.filtros?.acreedores||[]).map(v=>`<option value="${escAttr(v)}">${esc(categoryLabels[v]||v)}</option>`).join('');
  $('#debt-sex').innerHTML='<option value="__ALL__">Todos</option>'+(data.filtros?.sexos||[]).map(v=>`<option value="${escAttr(v)}">${esc(sexLabels[v]||v)}</option>`).join('');
  $('#debt-age').innerHTML='<option value="__ALL__">Todas</option>'+(data.filtros?.edades||[]).map(v=>`<option value="${escAttr(v)}">${esc(ageLabels[v]||v)}</option>`).join('');
}
function bind(){
  $('#debt-metric').addEventListener('change',()=>{renderMap();renderEvolution()});
  ['#debt-category','#debt-sex','#debt-age'].forEach(id=>$(id).addEventListener('change',reloadSlice));
  $('#debt-period').addEventListener('change',e=>loadPeriod(e.target.value));
  $('#debt-reset').addEventListener('click',()=>{$('#debt-category').value='__ALL__';$('#debt-sex').value='__ALL__';$('#debt-age').value='__ALL__';$('#debt-metric').value='tasa_mora_pct';loadPeriod(state.manifest.ultimo_periodo)});
}
function showError(e){console.error(e);$('#debt-error').hidden=false;$('#debt-map-status').textContent='No se pudo cargar la capa de datos CEPOES.'}
async function init(){
  try{
    state.manifest=await loadManifest();
    state.period=state.manifest.ultimo_periodo;
    const [data,geo]=await Promise.all([getPeriod(state.period),loadGeo()]);state.data=data;state.geo=geo;
    fillOptions(data);bind();
    const seg=findSegment(data,selectedFilters());if(!seg)throw new Error('Falta el segmento general');state.rows=rowsFromSegment(data,seg);renderAll();
  }catch(e){showError(e)}
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
