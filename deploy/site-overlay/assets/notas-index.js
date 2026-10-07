(()=>{'use strict';
const API='https://nriexnijkjamrmfivfmd.supabase.co/rest/v1/press_notes',KEY='sb_publishable_i2WWiop8sCom0yVZZ7xC8g_NGJCiddq',$=id=>document.getElementById(id);let notes=[],type='',topic='';
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const norm=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const fmt=d=>new Date(d).toLocaleDateString('es-AR',{day:'numeric',month:'long',year:'numeric'});


const topicsMap={'Endeudamiento':'Deuda de los hogares','Salud y cuidados':'Salud','Deporte y salud':'Salud','Estructura productiva':'Producción y empresas','Producción y comercio':'Producción y empresas','Educación e infancias':'Educación','Vivienda y hábitat':'Vivienda y alquiler'};
const canonical=n=>({...n,topic:topicsMap[n.topic]||n.topic||'Otros temas'});
const safeHref=s=>typeof s==='string'&&s.startsWith('/')&&!s.startsWith('//')?s:'';
function href(n){return safeHref(n.url)||'/prensa/nota/?slug='+encodeURIComponent(n.slug)}
function card(n,featured=false){
 const label=n.type==='analisis'?'Análisis':'Nota de prensa';
 return '<article class="notes-card'+(featured?' notes-feature-card':'')+'"><div class="notes-art" aria-hidden="true"><span>'+esc(n.topic)+'</span><span class="notes-art-mark">CEPOES / LECTURAS</span></div><div class="notes-card-body"><div class="press-meta"><span class="notes-type">'+label+'</span><time datetime="'+esc(n.first_published_at||n.published_at)+'">'+fmt(n.first_published_at||n.published_at)+'</time></div><h3><a href="'+esc(href(n))+'">'+esc(n.title)+'</a></h3><p>'+esc(n.summary)+'</p><div class="notes-card-actions"><a href="'+esc(href(n))+'">Leer '+(n.type==='analisis'?'análisis':'nota')+' <span aria-hidden="true">→</span></a>'+(safeHref(n.source_section)&&n.source_section!==n.url?'<a class="notes-data-link" href="'+esc(n.source_section)+'">Explorar los datos <span aria-hidden="true">↗</span></a>':'')+'</div></div></article>';
}
function saveFilters(){
 const p=new URLSearchParams(location.search);
 for(const [key,val] of Object.entries({q:$('notes-search').value,tema:topic,tipo:type,orden:$('notes-sort').value==='oldest'?'oldest':''})) {if(val)p.set(key,val);else p.delete(key)}
 history.replaceState(null,'',location.pathname+(p.size?'?'+p:'')+location.hash);
}
function render(){
 const q=norm($('notes-search').value),filtering=!!(q||topic||type);
 let shown=notes.filter(n=>(!type||n.type===type)&&(!topic||n.topic===topic)&&(!q||norm([n.title,n.summary,n.topic].join(' ')).includes(q)));
 if($('notes-sort').value==='oldest')shown=[...shown].reverse();
 // Featured stories remain searchable; avoid repeating them in the default view.
 const featuredSlugs=new Set(notes.filter(n=>n.type==='analisis').slice(0,3).map(n=>n.slug));
 const archive=filtering||$('notes-sort').value==='oldest'?shown:shown.filter(n=>!featuredSlugs.has(n.slug));
 $('notes-list').innerHTML=archive.length?archive.map(n=>card(n)).join(''):'<div class="notes-empty"><h3>No encontramos notas con esos filtros</h3><p>Probá otro tema o limpiá los filtros para volver al archivo.</p></div>';
 $('notes-total').textContent=filtering?shown.length+' resultados':notes.length+' publicaciones · '+featuredSlugs.size+' en foco y '+archive.length+' en el archivo';
 $('notes-reset').disabled=!filtering&&$('notes-sort').value==='newest';
 document.querySelectorAll('[data-note-type]').forEach(b=>{const active=b.dataset.noteType===type;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))});
 document.querySelectorAll('[data-note-topic]').forEach(b=>{const active=b.dataset.noteTopic===topic;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))});
 saveFilters();
}
async function load(){
 const results=await Promise.allSettled([
 fetch(API+'?select=slug,topic,title,summary,published_at,first_published_at,source_section&status=eq.publicada&order=published_at.desc&limit=500',{headers:{apikey:KEY},signal:AbortSignal.timeout(10000)}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}),
 fetch('/assets/data/analisis.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}),
 fetch('/assets/data/prensa.json?v=2',{signal:AbortSignal.timeout(10000)}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()})
 ]);
 const analyses=results[1].status==='fulfilled'?results[1].value.analyses:[];
 const local=results[2].status==='fulfilled'?results[2].value.notas.filter(n=>n.estado==='aprobada').map(n=>({slug:n.slug,topic:n.tema,title:n.titulo,summary:n.bajada,published_at:n.fecha+'T12:00:00',source_section:n.seccion})):[];
 const remote=results[0].status==='fulfilled'&&Array.isArray(results[0].value)?results[0].value:[];
 const bySlug=new Map();for(const n of [...local,...remote]){if(n.slug&&n.title)bySlug.set(n.slug,canonical({...n,type:'prensa'}))}
 notes=[...analyses.map(canonical),...bySlug.values()].sort((a,b)=>new Date(b.first_published_at||b.published_at)-new Date(a.first_published_at||a.published_at));
 const counts=new Map();for(const n of notes)counts.set(n.topic,(counts.get(n.topic)||0)+1);
 $('notes-topics').innerHTML='<button type="button" data-note-topic="" aria-pressed="true">Todos los temas <span>'+notes.length+'</span></button>'+[...counts].sort((a,b)=>a[0].localeCompare(b[0],'es')).map(([t,c])=>'<button type="button" data-note-topic="'+esc(t)+'" aria-pressed="false">'+esc(t)+' <span>'+c+'</span></button>').join('');
 const p=new URLSearchParams(location.search);type=['analisis','prensa'].includes(p.get('tipo'))?p.get('tipo'):'';topic=counts.has(p.get('tema'))?p.get('tema'):'';$('notes-search').value=p.get('q')||'';$('notes-sort').value=p.get('orden')==='oldest'?'oldest':'newest';
 $('notes-featured').innerHTML=notes.filter(n=>n.type==='analisis').slice(0,3).map(n=>card(n,true)).join('');
 $('notes-status').textContent=results.some(r=>r.status==='rejected')?'Mostramos las publicaciones disponibles. Parte del catálogo no pudo actualizarse en este momento.':'';
 render();
}
document.querySelector('.notes-type-filter').onclick=e=>{const b=e.target.closest('[data-note-type]');if(b){type=b.dataset.noteType;render()}};
$('notes-topics').onclick=e=>{const b=e.target.closest('[data-note-topic]');if(b){topic=b.dataset.noteTopic;render()}};
$('notes-search').oninput=render;$('notes-sort').onchange=render;
$('notes-reset').onclick=()=>{type='';topic='';$('notes-search').value='';$('notes-sort').value='newest';render();$('notes-search').focus()};
load().catch(()=>{$('notes-list').innerHTML='<p>No pudimos cargar el archivo. Recargá la página para volver a intentarlo.</p>'});
})();
