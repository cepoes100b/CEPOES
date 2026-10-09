// Analytical scales operate on rates, never on polygon area or decorative pedestals.
export const MAX_HEIGHT=3200;
export const MISSING_COLOR='#929da5';
export const COLORS=['#e0f1ef','#99d1cb','#4ba9a6','#197e85','#0e526b'];
const finite=value=>typeof value==='number'&&Number.isFinite(value);
const text=value=>typeof value==='string'&&value.trim().length>0;
export function validateAnalysis(data){
  if(data?.schema!=='cepoes-territorial-analysis-v1'||!Array.isArray(data.indicators)||!data.indicators.length||!Array.isArray(data.sources))throw new Error('Contrato analítico incompleto');
  const sources=new Map(data.sources.map(s=>[s.id,s]));
  for(const s of data.sources){
    let url;try{url=new URL(s.url);}catch{throw new Error('Fuente sin URL');}
    if(url.protocol!=='https:'||!text(s.publisher)||!text(s.license)||!text(s.checked_at))throw new Error('Fuente sin trazabilidad');
  }
  const ids=new Set();
  for(const ind of data.indicators){
    if(!/^[a-z][a-z0-9-]+$/.test(ind.id)||ids.has(ind.id))throw new Error('Identificador analítico inválido');ids.add(ind.id);
    if(ind.digits!==undefined&&(!Number.isInteger(ind.digits)||ind.digits<0||ind.digits>4))throw new Error('Precisión inválida');
    for(const key of ['name','unit','period','universe','method','numerator_label','denominator_label'])if(!text(ind[key]))throw new Error(`Falta ${key}`);
    if(ind.status!=='verified'||ind.level!=='comuna'||!finite(ind.multiplier)||ind.multiplier<=0||!Array.isArray(ind.source_ids)||!ind.source_ids.length||ind.source_ids.some(id=>!sources.has(id)))throw new Error('Indicador sin validación y fuentes completas');
    if(!Array.isArray(ind.rows)||ind.rows.length!==15||new Set(ind.rows.map(r=>r.id)).size!==15)throw new Error('Se requieren las 15 comunas');
    for(let i=1;i<=15;i++)if(!ind.rows.some(r=>r.id===`comuna:${i}`))throw new Error('Cobertura comunal incompleta');
    for(const row of ind.rows){
      if(row.value===null){if(!text(row.missing_reason))throw new Error('Faltante sin justificación');continue;}
      if(!finite(row.numerator)||row.numerator<0||!finite(row.denominator)||row.denominator<=0||!finite(row.value)||row.value<0)throw new Error('Valor o denominador inválido');
      if(ind.multiplier===100&&row.numerator>row.denominator)throw new Error('Porcentaje fuera del universo');
      if(Math.abs(row.value-row.numerator/row.denominator*ind.multiplier)>1e-7)throw new Error('Valor distinto del cociente documentado');
    }
  }
  return data;
}
export function scaleForIndicator(ind){
  const max=Math.max(0,...ind.rows.filter(r=>finite(r.value)).map(r=>r.value));
  // Percentages always use 0–100. Other ratios use a rounded full-dataset ceiling.
  // Neither domain changes with selection. The same ratio drives height, color and bars.
  const power=max?10**Math.floor(Math.log10(max)):1;
  const ceiling=ind.multiplier===100?100:max?Math.ceil(max/power*2)/2*power:1;
  return {min:0,max:ceiling,height:MAX_HEIGHT,ticks:Array.from({length:5},(_,i)=>ceiling*i/4)};
}
export function normalized(value,scale){return finite(value)&&value>=0?Math.min(1,value/scale.max):null;}
export function heightFor(value,scale){const n=normalized(value,scale);return n===null?0:n*MAX_HEIGHT;}
export function ranks(rows,digits=1){
  // Precision shown to the reader defines ties; no invisible decimals break them.
  const formatter=new Intl.NumberFormat('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits,useGrouping:false});
  const key=v=>Number(formatter.format(v));
  const valid=rows.filter(r=>finite(r.value)).sort((a,b)=>key(b.value)-key(a.value)||a.id.localeCompare(b.id,'es',{numeric:true}));
  const counts=new Map();for(const r of valid)counts.set(key(r.value),(counts.get(key(r.value))||0)+1);
  let previous=null,rank=0;
  const ranked=valid.map((r,i)=>{const v=key(r.value);if(v!==previous)rank=i+1;previous=v;return {...r,rank,tied:counts.get(v)>1};});
  return [...ranked,...rows.filter(r=>!finite(r.value)).sort((a,b)=>a.id.localeCompare(b.id,'es',{numeric:true})).map(r=>({...r,rank:null,tied:false}))];
}
export function cityRate(ind){
  if(ind.rows.some(r=>!finite(r.value)))return null;
  const n=ind.rows.reduce((s,r)=>s+r.numerator,0),d=ind.rows.reduce((s,r)=>s+r.denominator,0);
  return d>0?n/d*ind.multiplier:null;
}
export function colorFor(value,scale){
  const v=normalized(value,scale);if(v===null)return MISSING_COLOR;
  const p=v*(COLORS.length-1),lo=Math.floor(p),hi=Math.min(lo+1,COLORS.length-1),t=p-lo;
  return '#'+[1,3,5].map(i=>Math.round(parseInt(COLORS[lo].slice(i,i+2),16)*(1-t)+parseInt(COLORS[hi].slice(i,i+2),16)*t).toString(16).padStart(2,'0')).join('');
}
