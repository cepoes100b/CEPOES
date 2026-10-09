import {escapeHTML as esc,number as fmt,featureID,safeSourceURL} from '../model.mjs';
import {validateAnalysis,scaleForIndicator,ranks,cityRate,colorFor,normalized,COLORS,MAX_HEIGHT} from './model.mjs';
import {AnalyticalLayer} from './layer.mjs';
const $=id=>document.getElementById(id);
const valueText=(ind,v)=>v===null||v===undefined?'Sin dato':`${fmt(v,ind.digits??1)} ${ind.unit_short||ind.unit}`;
export async function createAnalysis({json,onChange,onSelect,qa}){
  const data=validateAnalysis(await json('analysis/indicators.json'));
  const ui=new AnalysisController({data,onChange,onSelect,qa});ui.bind();return ui;
}
class AnalysisController {
  constructor({data,onChange,onSelect,qa}){Object.assign(this,{data,onChange,onSelect,qa});this.adapter=null;this.last='';this.modeActive=false;this.rows=[];this.renderToken=0;}
  bind(){
    $('mt-analysis-indicator').innerHTML=this.data.indicators.map(i=>`<option value="${esc(i.id)}">${esc(i.name)}</option>`).join('');
    $('mt-analysis-indicator').addEventListener('change',()=>this.onChange({indicator:$('mt-analysis-indicator').value}));
    $('mt-analysis-views').addEventListener('click',event=>{const button=event.target.closest('[data-view]');if(button)this.onChange({view:button.dataset.view});});
    $('mt-analysis-orbit').addEventListener('click',()=>this.adapter?.toggleOrbit());
    $('mt-analysis-rank').addEventListener('click',event=>{const button=event.target.closest('[data-territory]');if(button)this.onSelect(button.dataset.territory);});
    $('mt-analysis-table').addEventListener('click',event=>{const button=event.target.closest('[data-territory]');if(button)this.onSelect(button.dataset.territory);});
    $('mt-analysis-comunas').addEventListener('click',()=>this.onChange({level:'comuna',territory:''}));
  }
  onMapState(status){
    Object.assign(this.qa.analysis,status);
    const button=$('mt-analysis-orbit');button.setAttribute('aria-pressed',String(status.orbit));button.textContent=status.orbit?'Detener giro':'Iniciar giro';
    button.disabled=!this.adapter?.active||status.view!=='3d'||status.reducedMotion;
    $('mt-analysis-animation').textContent=status.animation==='running'?'Transición visual. Los valores de la tabla son los finales.':status.reducedMotion?'Movimiento reducido activado.':'';
  }
  render(state,engine,territories){
    this.modeActive=true;
    const ind=this.data.indicators.find(i=>i.id===state.indicator)||this.data.indicators[0];state.indicator=ind.id;
    const supported=state.level===ind.level,t=territories.find(t=>featureID(t)===state.territory);
    const scale=scaleForIndicator(ind),sorted=ranks(ind.rows,ind.digits??1),row=sorted.find(r=>r.id===state.territory),city=cityRate(ind);
    this.qa.analysis??={};Object.assign(this.qa.analysis,{status:'ready',indicator:ind.id,view:supported?state.view:'flat',supported,rendered:false});
    $('mt-analysis-indicator').value=ind.id;$('mt-analysis-period').textContent=`${ind.period} · ${ind.unit}`;
    $('mt-analysis-universe').textContent=ind.universe;$('mt-analysis-scope').textContent=ind.scope||ind.method;
    $('mt-analysis-comunas').hidden=supported;
    $('mt-analysis-coverage').textContent=supported?'15 comunas · misma escala para todos los territorios':'Sin datos para barrios en este indicador. La selección barrial se conserva; no se le asigna el valor de su comuna.';
    document.querySelectorAll('[data-view]').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.view===(supported?state.view:'flat')));b.disabled=b.dataset.view==='3d'&&(!supported||!engine);});
    $('mt-analysis-availability').textContent=!engine?'El mapa no está disponible. La tabla y el ranking conservan la comparación completa.':supported?'La vista plana facilita comparar superficies sin oclusiones.':'';
    $('mt-place-kind').textContent='Análisis territorial';$('mt-place-name').textContent=t?.properties.name||'Toda la Ciudad';
    $('mt-place-description').textContent=ind.name;$('mt-map-title').textContent=`${ind.name} · ${ind.period}`;
    const current=supported?(state.territory?row?.value:city):null;
    const rank=row?.rank?`${row.rank}º de ${sorted.filter(r=>r.rank!==null).length}${row.tied?' · posición compartida':''}`:'';
    const comparison=current!==null&&current!==undefined&&city!==null&&state.territory?`Diferencia con Ciudad: ${current-city>=0?'+':''}${fmt(current-city,ind.digits??1)} ${ind.multiplier===100?'puntos porcentuales':ind.unit_short||ind.unit}.`:'';
    $('mt-metrics').innerHTML=`<div class="mt-metric-main"><strong>${current==null?'s/d':esc(fmt(current,ind.digits??1))}</strong><span>${esc(ind.unit)}</span></div><p class="mt-analysis-position">${esc(supported?rank:'Sin dato barrial')}</p><p class="mt-small">${esc(comparison)}</p><div class="mt-comparison"><div class="mt-comparison-head"><span>Ciudad · cociente de sumas</span><strong>${esc(valueText(ind,city))}</strong></div></div>`;
    $('mt-comparison-note').textContent=supported?(row?.missing_reason||ind.interpretation||ind.method):'Este indicador tiene cobertura comunal. Cambiá a comunas para comparar sus valores.';
    $('mt-service-card').hidden=true;
    $('mt-analysis-rank-title').textContent=`De mayor a menor · ${ind.unit}`;
    const renderKey=`${ind.id}:${ind.period}`;
    if(this.last!==renderKey){
      this.last=renderKey;
      $('mt-analysis-rank').innerHTML=sorted.map(r=>`<li><button type="button" data-territory="${r.id}" aria-pressed="${r.id===state.territory}" aria-label="Comuna ${r.id.split(':')[1]}, ${esc(valueText(ind,r.value))}${r.rank?`, posición ${r.rank}${r.tied?', compartida':''}`:''}"><span class="mt-rank-position">${r.rank===null?'s/d':`${r.rank}º`}</span><span class="mt-rank-label">Comuna ${r.id.split(':')[1]}<span class="mt-rank-track" aria-hidden="true"><i style="width:${(normalized(r.value,scale)??0)*100}%;background:${colorFor(r.value,scale)}"></i></span></span><strong>${r.value===null?'s/d':esc(fmt(r.value,ind.digits??1))}</strong></button></li>`).join('');
      $('mt-analysis-table').innerHTML=ind.rows.map(r=>{const rank=sorted.find(s=>s.id===r.id);return `<tr><th scope="row"><button type="button" data-territory="${r.id}" aria-pressed="${r.id===state.territory}">Comuna ${r.id.split(':')[1]}</button></th><td>${esc(valueText(ind,r.value))}</td><td>${fmt(r.numerator,ind.numerator_digits??0)}</td><td>${fmt(r.denominator,ind.denominator_digits??0)}</td><td>${rank.rank===null?'s/d':`${rank.rank}º${rank.tied?' (compartida)':''}`}</td><td>${esc(r.missing_reason||'Verificado')}</td></tr>`;}).join('');
    }
    for(const button of document.querySelectorAll('#mt-analysis-rank [data-territory],#mt-analysis-table [data-territory]'))button.setAttribute('aria-pressed',String(button.dataset.territory===state.territory));
    $('mt-analysis-table-caption').textContent=`${ind.name} · ${ind.period} · 15 comunas`;$('mt-analysis-num-title').textContent=ind.numerator_label;$('mt-analysis-den-title').textContent=ind.denominator_label;
    $('mt-legend').innerHTML=`<strong>${esc(ind.unit)} · escala lineal desde cero</strong><div class="mt-analysis-gradient" style="background:linear-gradient(to right,${COLORS.join(',')})" aria-hidden="true"></div><div class="mt-analysis-ticks">${scale.ticks.map(v=>`<span>${fmt(v,ind.digits??1)}</span>`).join('')}</div><p class="mt-small">Altura y color usan el mismo cociente: valor / ${fmt(scale.max,ind.digits??1)}. Gris: sin dato; cero: altura cero. Naranja: contorno de selección.</p><p class="mt-small">${state.view==='3d'&&supported?`Máximo de la escala = ${fmt(MAX_HEIGHT)} m gráficos. La altura es simbólica; el volumen depende del área de la comuna. Compará tasas con el ranking o la vista plana.`:'Vista plana con exactamente los mismos valores y colores.'}</p>`;
    const sources=ind.source_ids.map(id=>this.data.sources.find(s=>s.id===id));
    if(this.methodKey!==renderKey){this.methodKey=renderKey;$('mt-analysis-method').innerHTML=`<h3>${esc(ind.name)}</h3><p>${esc(ind.method)}</p><dl><dt>Período</dt><dd>${esc(ind.period)}</dd><dt>Universo</dt><dd>${esc(ind.universe)}</dd><dt>Cálculo</dt><dd>${esc(ind.numerator_label)} / ${esc(ind.denominator_label)}${ind.multiplier!==1?` × ${ind.multiplier}`:''}</dd><dt>Actualización</dt><dd>${esc(this.data.update_policy||'Insumos versionados; se valida la cobertura y el cálculo antes de reemplazar la última salida válida.')}</dd></dl><p>La escala parte de cero. Los porcentajes usan siempre 0–100%; las otras tasas redondean hacia arriba el máximo del conjunto completo. Es propia de cada indicador: las alturas de indicadores distintos no se comparan entre sí. La base de cada prisma es la superficie administrativa; su volumen no codifica un total. Las posiciones empatadas se comparten a la precisión visible.</p>${sources.map(s=>`<details><summary>${esc(s.name)}</summary><p>${esc(s.publisher)} · ${esc(s.license)} · verificado ${esc(s.checked_at)}</p><p>${esc(s.scope||'')}</p><p>${esc(s.attribution||'')}</p>${safeSourceURL(s.license_url)?`<p><a href="${esc(safeSourceURL(s.license_url))}" target="_blank" rel="noopener noreferrer">Licencia ${esc(s.license)} ↗</a></p>`:''}<a href="${esc(safeSourceURL(s.url))}" target="_blank" rel="noopener noreferrer">Abrir fuente oficial ↗</a></details>`).join('')}`;
    }
    $('mt-status').textContent=`${ind.name}. ${ind.period}. ${supported?`${state.territory?t?.properties.name:'Ciudad'}: ${valueText(ind,current??null)}.`:'Sin dato barrial.'} Ranking y tabla disponibles sin usar el mapa.`;
    if(engine){
      if(!this.adapter||this.adapter.engine!==engine)this.adapter=new AnalyticalLayer(engine,{onState:s=>this.onMapState(s)});
      this.adapter.set(ind,{view:state.view,level:state.level,selected:state.territory});
      engine.level=state.level;engine.selected=state.territory;
      const token=++this.renderToken;
      engine.map.once('idle',()=>{if(this.modeActive&&token===this.renderToken){const layer=engine.map.getLayer('analysis-volume');this.qa.analysis.rendered=true;this.qa.analysis.renderProof={pitch:engine.map.getPitch(),layerType:layer?.type,visible:engine.map.getLayoutProperty('analysis-volume','visibility'),renderedIds:[...new Set(engine.map.queryRenderedFeatures({layers:this.adapter.hitLayers()}).map(f=>String(f.properties.id)))],heights:ind.rows.map(r=>({id:r.id,ratio:engine.map.getFeatureState({source:'comuna',id:r.id}).ratio??null}))};}});
    }else this.onMapState({view:'flat',animation:'idle',orbit:false,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches});
  }
  deactivate(){this.modeActive=false;this.adapter?.deactivate();if(this.qa.analysis)this.qa.analysis.status='inactive';}
}
