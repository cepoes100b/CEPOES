import {LAYERS,normalize,escapeHTML as esc,number as fmt,featureID,collection,hasPoint,filterRecords,aggregate,scaleFor,levelTerritories,searchTerritories,readState,stateQuery,safeSourceURL,assertTerritories} from './model.mjs';
import {TerritorialMap,palette} from './engine.mjs';
const $=id=>document.getElementById(id);
const BASE=new URL('./data/',import.meta.url);
const state={layer:'salud',level:'barrio',territory:'',category:'',query:'',limit:20,mode:'explore',view:'flat',indicator:''};
let analysis=null,analysisLoad=null,analysisRequest=0;
const cache=new Map();let territories=[],manifest=null,loaded=null,loadedLayerId='',stats=null,engine=null,request=0,initializing=false,engineAttempted=false;
const qa={started:performance.now(),status:'loading',map:'pending',measures:[],loadedLayers:[]};
Object.defineProperty(window,'__CEPOES_MAP_QA',{value:qa,writable:false});
const measure=(name,start)=>{qa.measures.push({name,ms:Math.round((performance.now()-start)*100)/100});if(qa.measures.length>100)qa.measures.shift();};
const selected=()=>territories.find(f=>featureID(f)===state.territory);
const layerMeta=()=>manifest?.layers?.find(x=>x.id===state.layer);
const sourceById=id=>manifest?.sources.find(x=>x.id===id);
const comparable=()=>layerMeta()?.comparable!==false&&state.layer!=='verdes';
const sourceLink=(id,label='Fuente oficial ↗')=>{const source=sourceById(id),url=safeSourceURL(source?.url);return url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`:'';};
function status(text){$('mt-status').textContent=text;}
function showError(text){$('mt-error-text').textContent=text;$('mt-error').hidden=false;}
function clearError(){$('mt-error').hidden=true;}
function syncURL(push=false){const url=location.pathname+stateQuery(state);if(url!==location.pathname+location.search)history[push?'pushState':'replaceState'](null,'',url);$('mt-share-url').value=location.origin+url;}
async function json(relative){
  if(!/^[a-z0-9/_.-]+$/.test(relative)||relative.includes('..'))throw new Error('Ruta de datos no válida');
  const url=new URL(relative,BASE);
  const digest=manifest?.files?.find(x=>x.path===relative)?.sha256;
  if(digest)url.searchParams.set('v',digest.slice(0,16));
  const response=await fetch(url,{credentials:'omit',cache:relative==='manifest.json'?'no-cache':'default',signal:AbortSignal.timeout(12000)});
  if(!response.ok)throw new Error(`No se pudo leer ${relative} (HTTP ${response.status})`);
  return response.json();
}
function modeChrome(){
  const analytical=state.mode==='analyze';$('mt-explorer').dataset.mode=state.mode;
  // One information dock in Analyze, original columns preserved in Explore.
  const workspace=document.querySelector('.mt-workspace'),panel=$('mt-analysis-controls'),dossier=document.querySelector('.mt-dossier');
  if(analytical&&dossier.parentElement!==panel)panel.appendChild(dossier);
  if(!analytical&&dossier.parentElement!==workspace)workspace.appendChild(dossier);
  document.querySelector('.mt-advanced-controls').open=!analytical;
  $('mt-explorer').classList.remove('mt-sheet-expanded');
  $('mt-sheet-toggle').setAttribute('aria-expanded','false');
  document.querySelector('.mt-sheet-label').textContent='Ampliar panel';
  document.querySelectorAll('#mt-mode-controls [data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===state.mode)));
  for(const id of ['mt-analysis-controls','mt-analysis-ranking','mt-analysis-data'])$(id).hidden=!analytical;
  for(const id of ['mt-records','mt-accessible','mt-method'])$(id).hidden=analytical;
  document.querySelector('.mt-layers').hidden=analytical;
  $('mt-streets').parentElement.hidden=analytical;
  document.querySelectorAll('.mt-dossier-actions a').forEach(a=>a.hidden=analytical);
  $('mt-search-results').hidden=true;$('mt-service-card').hidden=true;
  engine?.map.resize();
}
async function setMode(mode,{push=true,fit=false}={}){
  const token=++analysisRequest,start=performance.now();state.mode=mode==='analyze'?'analyze':'explore';
  modeChrome();clearError();
  if(state.mode==='explore'){
    analysis?.deactivate();populateTerritories();syncURL(push);
    if(loaded&&loadedLayerId===state.layer)render();else if(manifest)await loadLayer(state.layer,{push:false});return;
  }
  populateTerritories();syncURL(push);
  if(!analysis){
    $('mt-metrics').innerHTML='<p class="mt-small">Cargando el indicador y sus fuentes verificadas…</p>';
    $('mt-legend').textContent='Esperando datos analíticos. No se muestran valores de otra capa.';
    $('mt-analysis-indicator').disabled=true;status('Cargando modo analítico…');
    qa.analysis={status:'loading',rendered:false};
    // Do not leave 2D inventory colors or records visible under a new analytical legend.
    engine?.update({level:state.level,territory:state.territory,records:[],stats:null});
    try{
      analysisLoad??=import('./analysis/controller.mjs').then(m=>m.createAnalysis({json,onChange:patch=>{Object.assign(state,patch);populateTerritories();render();syncURL(true);},onSelect:id=>selectTerritory(id),qa}));
      analysis=await analysisLoad;
    }catch(error){analysisLoad=null;if(token!==analysisRequest||state.mode!=='analyze')return;qa.analysis={status:'error',rendered:false};qa.status='analysis-error';showError(`No se pudo verificar el indicador: ${error.message}. Los datos anteriores no se usan como reemplazo.`);status('Indicador no disponible. Volvé a intentar.');return;}
  }
  if(token!==analysisRequest||state.mode!=='analyze')return;
  $('mt-analysis-indicator').disabled=false;render();qa.status='ready';measure('analysis-ready',start);syncURL(false);if(fit)engine?.fit(selected());
}
function populateTerritories(){
  $('mt-level').value=state.level;
  $('mt-territory').innerHTML='<option value="">Toda la Ciudad</option>'+levelTerritories(territories,state.level).map(f=>`<option value="${esc(featureID(f))}">${esc(f.properties.name)}</option>`).join('');
  $('mt-territory').value=state.territory;
}
function selectTerritory(id,{push=true,fit=true}={}){
  const territory=territories.find(f=>featureID(f)===id);state.territory=territory?id:'';if(territory)state.level=territory.properties.level;
  state.limit=20;state.query='';$('mt-record-search').value='';$('mt-service-card').hidden=true;
  populateTerritories();render();if(fit&&engine)engine.fit(territory);syncURL(push);
}
function renderSearch(){
  const results=searchTerritories(territories,$('mt-search').value).slice(0,10);const list=$('mt-search-results');
  list.hidden=!$('mt-search').value.trim();
  list.innerHTML=results.length?results.map(f=>`<li><button type="button" data-territory="${esc(featureID(f))}">${esc(f.properties.name)}<span>${f.properties.level==='barrio'?`Barrio · Comuna ${f.properties.comuna}`:'Comuna'}</span></button></li>`).join(''):'<li><p>No encontramos ese territorio. Probá con otro nombre.</p></li>';
}
function renderSources(){
  const date=v=>v?esc(String(v).slice(0,10)):'No informado por la fuente';
  $('mt-sources').innerHTML=manifest.sources.map(s=>`<details><summary>${esc(s.name)}</summary><dl><dt>Organismo</dt><dd>${esc(s.publisher||'GCBA / BA Data')}</dd><dt>Licencia</dt><dd><a href="${esc(safeSourceURL(s.license_url)||'https://data.buenosaires.gob.ar/')}" target="_blank" rel="noopener noreferrer">${esc(s.license)}</a></dd><dt>Catálogo actualizado</dt><dd>${date(s.catalog_updated_at)}</dd><dt>Modificación del recurso</dt><dd>${date(s.resource_last_modified_visible||s.resource_last_modified_recorded||s.geojson_resource_last_modified_visible)}</dd><dt>Corte de observación</dt><dd>${date(s.data_observed_at)}</dd><dt>Verificado por CEPOES</dt><dd>${date(s.checked_at||s.downloaded_at||manifest.checked_at)}</dd><dt>Fuente</dt><dd>${sourceLink(s.id,'Abrir catálogo oficial ↗')}</dd></dl></details>`).join('');
}
async function loadLayer(id,{force=false,push=true}={}){
  if(!Object.hasOwn(LAYERS,id))return;const token=++request,start=performance.now();
  state.layer=id;state.category='';state.limit=20;state.query='';$('mt-record-search').value='';loaded=null;loadedLayerId='';stats=null;
  $('mt-service-card').hidden=true;$('mt-service-card').innerHTML='';
  $('mt-territory-table').innerHTML='';$('mt-table-caption').textContent=`${LAYERS[id].name} · cargando fuente`;
  $('mt-record-count').textContent='Cargando…';$('mt-record-warning').textContent='';$('mt-more').hidden=true;
  $('mt-source-short').textContent='Cargando fuente y alcance de esta capa…';
  clearError();$('mt-category').disabled=true;$('mt-category').innerHTML='<option value="">Cargando tipos…</option>';
  document.querySelectorAll('[data-layer]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.layer===id)));
  status(`Cargando ${LAYERS[id].name.toLowerCase()}…`);$('mt-record-list').innerHTML='<p class="mt-empty">Cargando registros de esta capa…</p>';
  $('mt-metrics').innerHTML='<p class="mt-small">Esperando la fuente seleccionada…</p>';$('mt-legend').innerHTML='<strong>Esperando datos</strong><p>No se presentan valores de otra capa.</p>';
  engine?.update({level:state.level,territory:state.territory,records:[],stats:null});
  render();syncURL(push);
  try{
    if(force)cache.delete(id);
    if(!cache.has(id))cache.set(id,json(`layers/${id}.geojson`).then(data=>{
      if(data.type!=='FeatureCollection'||!Array.isArray(data.features)||data.features.length!==manifest.layers.find(l=>l.id===id).count)throw new Error('La cobertura recibida no coincide con el manifiesto verificado.');
      const ids=data.features.map(featureID);if(ids.some(x=>!x)||new Set(ids).size!==ids.length)throw new Error('Registros sin identificador o duplicados.');
      return data;
    }).catch(e=>{cache.delete(id);throw e;}));
    const data=await cache.get(id);if(token!==request||state.layer!==id)return;
    loaded=data;loadedLayerId=id;
    if(!qa.loadedLayers.includes(id))qa.loadedLayers.push(id);
    const categories=[...new Set(data.features.map(f=>f.properties.category).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'es'));
    $('mt-category').innerHTML='<option value="">Todos los tipos</option>'+categories.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');$('mt-category').disabled=false;
    render();measure(`load-layer:${id}`,start);qa.status='ready';
  }catch(error){if(token!==request||state.layer!==id||state.mode==='analyze')return;qa.status='layer-error';showError(`${LAYERS[id].name}: ${error.message}. Podés volver a intentar o elegir otra capa.`);status('Capa no disponible. No se sustituyen los datos faltantes por ceros.');$('mt-record-list').innerHTML='<p class="mt-empty">Sin datos disponibles para esta capa. Los registros anteriores se ocultaron para evitar confusiones.</p>';$('mt-territory-table').innerHTML='';$('mt-record-count').textContent='Sin dato';$('mt-more').hidden=true;}
}
function render(){
  if(state.mode==='analyze'){analysis?.render(state,engine,territories);return;}
  const t=selected(),p=t?.properties,name=p?.name||'Toda la Ciudad';
  $('mt-place-name').textContent=name;$('mt-map-title').textContent=p?.name||'Ciudad de Buenos Aires';
  $('mt-place-kind').textContent=p?(p.level==='barrio'?`Barrio · Comuna ${p.comuna}`:'Comuna'):'Ciudad de Buenos Aires';
  $('mt-place-description').textContent=p?`${fmt(p.area_km2,2)} km² de superficie administrativa · ${LAYERS[state.layer].name}`:'48 barrios y 15 comunas. Elegí un territorio para comparar su inventario.';
  $('mt-related').href=p?.level==='barrio'?`/territorio/barrios/${p.slug}/`:'/territorio/equipamientos/';
  $('mt-related').textContent=p?.level==='barrio'?`Leer la ficha de ${p.name} →`:'Explorar catálogo territorial →';
  if(!loaded||loadedLayerId!==state.layer)return;
  const start=performance.now(),records=filterRecords(loaded.features,{category:state.category});
  stats=aggregate(records,territories);
  const scope=filterRecords(records,{territory:state.territory});
  const current=state.territory?stats.rows.get(state.territory):stats.city;
  renderMetrics(current,t);renderLegend();renderTable();renderRecords();
  engine?.update({level:state.level,territory:state.territory,records:scope,stats:comparable()?stats:null});
  const mapped=scope.filter(hasPoint).length;
  status(`${fmt(scope.length)} registros en ${name} · ${fmt(mapped)} puntos verificados en el mapa${scope.length-mapped?` · ${fmt(scope.length-mapped)} sin punto verificable`:''}.`);
  const sourceIds=[...new Set(loaded.features.map(f=>f.properties.source_id))];
  const sources=sourceIds.map(sourceById).filter(Boolean);
  $('mt-source-short').textContent=`${fmt(loaded.features.length)} registros. ${sources.map(s=>`${s.name}: archivo ${String(s.resource_last_modified_visible||s.resource_last_modified_recorded||s.geojson_resource_last_modified_visible||'sin fecha').slice(0,10)}`).join('. ')}. Corte observado no informado.`;
  if(state.layer==='verdes')showError('Espacios verdes: 41 registros tienen diferencias entre el polígono y el barrio declarado. Esos puntos se omiten del mapa y se conservan identificados en el listado. La comparación de densidad está suspendida para esta capa. Los puntos restantes representan polígonos, no accesos; el inventario incluye canteros y jardines.');
  else clearError();
  measure('render-filter',start);
}
function renderMetrics(current,t){
  if(!current)return;
  let comparison='';
  if(comparable()){
    const rows=[{label:t?.properties.name||'Ciudad',row:current}];
    if(t?.properties.level==='barrio')rows.push({label:`Comuna ${t.properties.comuna}`,row:stats.rows.get(`comuna:${t.properties.comuna}`)});
    if(t)rows.push({label:'Ciudad',row:stats.city});
    const max=Math.max(1,...rows.map(r=>r.row?.rate??0));
    comparison='<p class="mt-small">Densidad de inventario · registros por km²</p>'+rows.map((r,i)=>`<div class="mt-comparison ${i?'secondary':''}"><div class="mt-comparison-head"><span>${esc(r.label)}</span><strong>${fmt(r.row?.rate,2)}</strong></div><div class="mt-comparison-track" aria-hidden="true"><span style="width:${Math.max(0,(r.row?.rate??0)/max*100)}%"></span></div></div>`).join('');
  }else comparison='<p class="mt-small">Comparación territorial en revisión: se detectaron discrepancias entre geometrías y atributos de la fuente. Se muestra el inventario según el barrio declarado, sin ranking ni tasa.</p>';
  $('mt-metrics').innerHTML=`<div class="mt-metric-main"><strong>${fmt(current.count)}</strong><span>${esc(LAYERS[state.layer].record)}${state.category?` · ${esc(state.category)}`:''}</span></div>${comparison}<p class="mt-small">${fmt(current.mapped)} con punto verificable · ${fmt(current.missing)} sin punto verificable.</p>`;
  $('mt-comparison-note').textContent=comparable()?'Cálculo CEPOES sobre registros de la fuente y superficie administrativa. Incluye registros sin coordenadas cuando tienen territorio declarado. No mide capacidad, calidad ni accesibilidad.':'Los atributos territoriales se conservan como fueron publicados. El detalle de cada discrepancia está disponible en los registros afectados.';
}
function renderLegend(){
  if(!comparable()){$('mt-legend').innerHTML='<strong>Espacios verdes · exploración del inventario</strong><p class="mt-small">Sin escala de densidad mientras se revisan las discrepancias territoriales.</p><p class="mt-point-legend">Punto interior del polígono, no acceso. Círculos mayores agrupan puntos: tocá para acercar.</p>';return;}
  const s=scaleFor(levelTerritories(territories,state.level).map(f=>stats.rows.get(featureID(f))?.rate));
  const colors=palette();
  $('mt-legend').innerHTML='<strong>Densidad de registros por km²</strong><div class="mt-scale">'+s.thresholds.map((v,i)=>`<div><i style="background:${colors[i]}" aria-hidden="true"></i><span>${fmt(v,2)}</span></div>`).join('')+'</div><p class="mt-small">Escala continua, de menor a mayor densidad. Gris: sin dato. Selección: contorno reforzado.</p><p class="mt-point-legend">Registro geolocalizado. Círculos mayores agrupan puntos: tocá para acercar.</p>';
}
function renderTable(){
  $('mt-table-caption').textContent=`${state.level==='barrio'?'48 barrios':'15 comunas'} · ${LAYERS[state.layer].name}${state.category?` · ${state.category}`:''}`;
  $('mt-territory-table').innerHTML=levelTerritories(territories,state.level).map(f=>{const r=stats.rows.get(featureID(f));return `<tr><th scope="row"><button type="button" data-territory="${esc(featureID(f))}">${esc(f.properties.name)}</button></th><td>${fmt(r.count)}</td><td>${comparable()?fmt(r.rate,2):'En revisión'}</td><td>${fmt(r.missing)}</td></tr>`;}).join('');
}
function positionDescription(f){
  const p=f.properties;
  if(p.position_territory_warning)return 'Ubicación en revisión: el punto no coincide con el barrio declarado por la fuente. No se muestra en el mapa.';
  if(!hasPoint(f)){const reasons={edificio_cui_discrepante:'El edificio no coincide entre archivos oficiales.',sin_cue_anexo_en_geometria:'No se encontró una geometría oficial enlazable.',atributo_territorial_discrepante:'El territorio no coincide entre archivos oficiales.'};return 'Sin punto verificable. '+(reasons[p.missing_reason]||reasons[p.position_missing_reason]||'La identidad o ubicación no se pudo confirmar.');}
  return manifest.position_methods[p.position_method]||'Punto procedente de fuente oficial.';
}
function renderRecords(){
  if(!loaded||loadedLayerId!==state.layer)return;
  const all=filterRecords(loaded.features,{territory:state.territory,category:state.category});
  const records=filterRecords(all,{query:state.query}).sort((a,b)=>a.properties.name.localeCompare(b.properties.name,'es'));
  $('mt-records-title').textContent=LAYERS[state.layer].name+(selected()?` en ${selected().properties.name}`:' en la Ciudad');
  $('mt-record-count').textContent=`${fmt(records.length)} registros${state.query?` de ${fmt(all.length)}`:''}`;
  $('mt-record-warning').textContent='La búsqueda de abajo filtra sólo el listado. Se conservan los registros sin ubicación verificable; sus atributos provienen de la fuente.';
  $('mt-record-list').innerHTML=records.slice(0,state.limit).map(f=>{const p=f.properties,b=territories.find(t=>featureID(t)===p.barrio_id)?.properties.name||'Barrio no informado';return `<article class="mt-record"><p class="mt-record-tag">${esc(p.category||LAYERS[state.layer].name)} · ${esc(b)}</p><h3>${esc(p.name)}</h3><p>${esc(p.address||'Dirección no informada')}</p><p>${esc(positionDescription(f))}</p>${hasPoint(f)?`<button type="button" data-record="${esc(featureID(f))}">Ver en el mapa</button>`:''}${sourceLink(p.source_id)}</article>`;}).join('')||'<p class="mt-empty">La fuente no registra resultados para esta selección. Probá otro filtro.</p>';
  $('mt-more').hidden=records.length<=state.limit;
}
function showRecord(f){
  const p=f.properties,card=$('mt-service-card');
  card.innerHTML=`<p class="mt-eyebrow">Registro seleccionado</p><h3>${esc(p.name)}</h3><p>${esc(p.address||'Dirección no informada')}</p><p>${esc(positionDescription(f))}</p>${sourceLink(p.source_id)}<br><button type="button" id="mt-close-record">Cerrar detalle del registro</button>`;card.hidden=false;
  $('mt-close-record').addEventListener('click',()=>{card.hidden=true;$('mt-territory').focus();});
  engine?.focusRecord(f);
  if(matchMedia('(max-width:760px)').matches)card.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'});
}
function mapFailed(error){
  if(engine){engine.destroy();engine=null;}
  qa.map='unavailable';$('mt-map').classList.add('mt-map-failed');
  $('mt-map').innerHTML='<div class="mt-map-loading" role="status"><p>El mapa interactivo no está disponible en este navegador. Podés explorar todos los barrios, comunas y registros con los selectores y la tabla de esta página.</p></div>';
  $('mt-streets').disabled=true;$('mt-fit').disabled=true;if(state.mode==='analyze')render();console.warn('CEPOES Mapa:',error?.message||'WebGL no disponible');
}
async function initEngine(){
  if(engineAttempted)return;engineAttempted=true;
  try{
    engine=await TerritorialMap.create({container:'mt-map',territories,onTerritory:id=>selectTerritory(id),onRecord:showRecord,onReady:()=>{$('mt-map-loading')?.remove();$('mt-streets').disabled=false;$('mt-fit').disabled=false;qa.map='ready';measure('map-ready',qa.started);render();if(selected()||state.mode==='analyze')engine?.fit(selected());},onFailure:mapFailed,onBaseStatus:(message,enabled)=>{$('mt-base-status').textContent=message;$('mt-streets').checked=enabled;}});
    render();
  }catch(e){mapFailed(e);}
}
async function initialize(){
  if(initializing)return;initializing=true;clearError();
  try{
    manifest=await json('manifest.json');
    ({features:territories}=assertTerritories(await json('territories.geojson')));
    if(!Array.isArray(manifest.sources)||!Array.isArray(manifest.layers)||['salud','educacion','verdes'].some(id=>!manifest.layers.some(l=>l.id===id)))throw new Error('Manifiesto de fuentes incompleto.');
    Object.assign(state,readState(location.search,territories));populateTerritories();renderSources();
    if(state.mode==='analyze')await setMode('analyze',{push:false});else await loadLayer(state.layer,{push:false});initEngine();
  }catch(error){qa.status='initial-error';showError(`No se pudo iniciar el explorador: ${error.message}. Volvé a intentar.`);$('mt-map-loading').textContent='Cartografía no disponible. No se muestran territorios parciales.';status('No se pudo comprobar la cobertura 48 barrios / 15 comunas.');}
  finally{initializing=false;}
}
$('mt-mode-controls').addEventListener('click',e=>{const button=e.target.closest('[data-mode]');if(!button||!manifest||button.dataset.mode===state.mode)return;if(button.dataset.mode==='analyze'){if(!state.territory)state.level='comuna';state.view='3d';}setMode(button.dataset.mode,{fit:button.dataset.mode==='analyze'});});
$('mt-sheet-toggle').addEventListener('click',()=>{
  const expanded=$('mt-explorer').classList.toggle('mt-sheet-expanded');
  $('mt-sheet-toggle').setAttribute('aria-expanded',String(expanded));
  document.querySelector('.mt-sheet-label').textContent=expanded?'Mostrar más mapa':'Ampliar panel';
  engine?.map.resize();
});
$('mt-search').addEventListener('input',renderSearch);
$('mt-search').addEventListener('keydown',e=>{if(e.key==='Escape'){$('mt-search-results').hidden=true;}if(e.key==='ArrowDown'){e.preventDefault();$('mt-search-results').querySelector('button')?.focus();}});
$('mt-search-form').addEventListener('submit',e=>{e.preventDefault();const matches=searchTerritories(territories,$('mt-search').value);if(matches.length===1){selectTerritory(featureID(matches[0]));$('mt-search-results').hidden=true;}else renderSearch();});
$('mt-search-results').addEventListener('click',e=>{const b=e.target.closest('[data-territory]');if(b){selectTerritory(b.dataset.territory);$('mt-search').value='';$('mt-search-results').hidden=true;$('mt-territory').focus();}});
document.addEventListener('click',e=>{if(!$('mt-search-form').contains(e.target))$('mt-search-results').hidden=true;});
$('mt-level').addEventListener('change',()=>{state.level=$('mt-level').value;state.territory='';populateTerritories();render();syncURL(true);});
$('mt-territory').addEventListener('change',()=>selectTerritory($('mt-territory').value));
$('mt-layer-controls').addEventListener('click',e=>{const b=e.target.closest('[data-layer]');if(b&&manifest&&b.dataset.layer!==state.layer)loadLayer(b.dataset.layer);});
$('mt-category').addEventListener('change',()=>{state.category=$('mt-category').value;state.limit=20;$('mt-service-card').hidden=true;render();});
$('mt-record-search').addEventListener('input',()=>{state.query=$('mt-record-search').value;state.limit=20;renderRecords();});
$('mt-record-list').addEventListener('click',e=>{const b=e.target.closest('[data-record]');if(b){const f=loaded.features.find(f=>featureID(f)===b.dataset.record);if(f)showRecord(f);}});
$('mt-more').addEventListener('click',()=>{state.limit+=20;renderRecords();});
$('mt-territory-table').addEventListener('click',e=>{const b=e.target.closest('[data-territory]');if(b){selectTerritory(b.dataset.territory);$('mt-place-name').scrollIntoView({block:'nearest'});}});
$('mt-reset').addEventListener('click',()=>{state.category='';$('mt-category').value='';$('mt-search').value='';$('mt-search-results').hidden=true;selectTerritory('');});
$('mt-fit').addEventListener('click',()=>engine?.fit(selected()));
$('mt-streets').addEventListener('change',()=>engine?.setStreets($('mt-streets').checked));
$('mt-share').addEventListener('click',()=>{syncURL();$('mt-share-url').hidden=false;$('mt-share-url').focus();$('mt-share-url').select();});
$('mt-retry').addEventListener('click',()=>state.mode==='analyze'&&manifest?setMode('analyze',{push:false}):manifest&&territories.length?loadLayer(state.layer,{force:true,push:false}):initialize());
window.addEventListener('popstate',()=>{if(!territories.length)return;const next={mode:'explore',view:'flat',indicator:'',...readState(location.search,territories)},changed=next.layer!==state.layer;if(changed){request++;loaded=null;loadedLayerId='';stats=null;}Object.assign(state,next);state.query='';state.limit=20;$('mt-record-search').value='';$('mt-category').value='';$('mt-service-card').hidden=true;populateTerritories();if(state.mode==='analyze')setMode('analyze',{push:false,fit:true});else{analysisRequest++;analysis?.deactivate();modeChrome();if(changed||!loaded)loadLayer(state.layer,{push:false});else{render();engine?.fit(selected());}}});
new MutationObserver(()=>{if(state.mode==='analyze')render();else if(stats)renderLegend();}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
initialize();
