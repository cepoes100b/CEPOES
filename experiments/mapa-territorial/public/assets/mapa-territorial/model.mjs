export const LAYERS = Object.freeze({
  salud: {name:'Salud', subtitle:'Hospitales y CeSAC', record:'registros de salud'},
  educacion: {name:'Educación', subtitle:'Establecimientos activos', record:'establecimientos educativos'},
  verdes: {name:'Espacios verdes', subtitle:'Inventario oficial', record:'registros de espacios verdes'}
});
export const normalize = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const number = (value, digits=0) => Number.isFinite(value) ? new Intl.NumberFormat('es-AR',{maximumFractionDigits:digits,minimumFractionDigits:digits}).format(value) : 'Sin dato';
export const featureID = feature => String(feature?.properties?.id ?? feature?.id ?? '');
export const collection = features => ({type:'FeatureCollection',features});
export function hasPoint(feature) {
  const c=feature?.geometry?.coordinates;
  return !feature?.properties?.position_territory_warning && feature?.geometry?.type==='Point' && Array.isArray(c) && c.length>=2 && c.slice(0,2).every(Number.isFinite) && c[0]>=-58.6 && c[0]<=-58.3 && c[1]>=-34.8 && c[1]<=-34.4;
}
export function filterRecords(features,{territory='',category='',query=''}={}) {
  const terms=normalize(query).split(/\s+/).filter(Boolean);
  return features.filter(f=>{
    const p=f.properties;
    if(category && p.category!==category)return false;
    if(territory && p.barrio_id!==territory && p.comuna_id!==territory)return false;
    const haystack=normalize([p.name,p.address,p.category,p.barrio,p.comuna].join(' '));
    return terms.every(t=>haystack.includes(t));
  });
}
export function aggregate(features,territories) {
  const rows = new Map(territories.map(f=>[featureID(f),{count:0,mapped:0,missing:0,area:f.properties.area_km2,rate:null}]));
  let mapped=0,unassigned=0;
  for(const f of features){
    const point=hasPoint(f); if(point)mapped++;
    let assigned=false;
    for(const id of new Set([f.properties.barrio_id,f.properties.comuna_id])){
      if(!rows.has(id))continue;
      assigned=true;
      const r=rows.get(id);r.count++;if(point)r.mapped++;else r.missing++;
    }
    if(!assigned)unassigned++;
  }
  for(const r of rows.values())r.rate=Number.isFinite(r.area)&&r.area>0?r.count/r.area:null;
  const areas=territories.filter(f=>f.properties.level==='barrio').map(f=>f.properties.area_km2);
  const area=areas.length===48&&areas.every(x=>Number.isFinite(x)&&x>0)?areas.reduce((a,b)=>a+b,0):null;
  const city={count:features.length,mapped,missing:features.length-mapped,unassigned,area,rate:area?features.length/area:null};
  return {rows,city};
}
export function scaleFor(values) {
  const finite=values.filter(x=>Number.isFinite(x)&&x>=0);
  const max=Math.max(0,...finite);
  const top=max===0?1:Math.ceil(max*10)/10;
  const thresholds=[0,top/4,top/2,top*3/4,top];
  return {max:top,thresholds};
}
export function levelTerritories(territories,level){
  return territories.filter(f=>f.properties.level===level).sort((a,b)=>a.properties.name.localeCompare(b.properties.name,'es',{numeric:true}));
}
export function searchTerritories(territories,query){
  const terms=normalize(query).split(/\s+/).filter(Boolean);if(!terms.length)return [];
  return territories.filter(f=>terms.every(t=>normalize(`${f.properties.name} ${f.properties.level==='comuna'?'comuna':''}`).includes(t))).sort((a,b)=>a.properties.name.localeCompare(b.properties.name,'es',{numeric:true}));
}
export function readState(search,territories){
  const p=new URLSearchParams(search);const ids=new Map(territories.map(f=>[featureID(f),f]));
  const raw=p.get('territorio')||'';const territory=ids.has(raw)?raw:'';
  return {layer:Object.hasOwn(LAYERS,p.get('capa'))?p.get('capa'):'salud',level:territory?ids.get(territory).properties.level:p.get('escala')==='comuna'?'comuna':'barrio',territory,category:''};
}
export function stateQuery(state){
  const p=new URLSearchParams({capa:Object.hasOwn(LAYERS,state.layer)?state.layer:'salud',escala:state.level==='comuna'?'comuna':'barrio'});
  if(/^barrio:[a-z0-9-]+$|^comuna:(?:[1-9]|1[0-5])$/.test(state.territory))p.set('territorio',state.territory);
  return `?${p}`;
}
export function boundsFor(feature){
  const coordinates=[]; const visit=x=>{if(Array.isArray(x)&&x.length>=2&&typeof x[0]==='number')coordinates.push(x);else if(Array.isArray(x))x.forEach(visit);};
  visit(feature.geometry.coordinates);if(!coordinates.length)throw new Error('Territory without coordinates');
  return [[Math.min(...coordinates.map(x=>x[0])),Math.min(...coordinates.map(x=>x[1]))],[Math.max(...coordinates.map(x=>x[0])),Math.max(...coordinates.map(x=>x[1]))]];
}
export function safeSourceURL(raw){try{const url=new URL(raw);return url.protocol==='https:'?url.href:null;}catch{return null;}}
export function assertTerritories(fc){
  if(fc?.type!=='FeatureCollection'||!Array.isArray(fc.features))throw new Error('Formato de cartografía inválido');
  const ids=fc.features.map(featureID);
  if(new Set(ids).size!==63||ids.length!==63)throw new Error('Se esperan 63 territorios únicos');
  if(fc.features.filter(x=>x.properties.level==='barrio').length!==48||fc.features.filter(x=>x.properties.level==='comuna').length!==15)throw new Error('Cobertura territorial incompleta');
  for(const f of fc.features){if(!['Polygon','MultiPolygon'].includes(f.geometry?.type)||!Number.isFinite(f.properties.area_km2)||f.properties.area_km2<=0)throw new Error('Geometría o superficie inválida');}
  return fc;
}
