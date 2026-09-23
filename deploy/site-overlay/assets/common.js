(function(){
  const root=document.documentElement;
  let theme='light';
  try{theme=localStorage.getItem('cepoes-theme')|| (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')}catch(e){}
  root.dataset.theme=theme;
  document.addEventListener('DOMContentLoaded',()=>{
    const b=document.querySelector('[data-theme-toggle]');
    if(b){b.textContent=theme==='dark'?'☀':'◐';b.addEventListener('click',()=>{theme=root.dataset.theme==='dark'?'light':'dark';root.dataset.theme=theme;try{localStorage.setItem('cepoes-theme',theme)}catch(e){};b.textContent=theme==='dark'?'☀':'◐';document.dispatchEvent(new CustomEvent('cepoes-theme'))})}
    const m=document.querySelector('[data-menu-toggle]'),nav=document.querySelector('.nav-links');
    if(m&&nav)m.addEventListener('click',()=>nav.classList.toggle('open'));
    if(nav&&!nav.querySelector('a[href="/prensa/"]')){
      const a=document.createElement('a');a.href='/prensa/';a.textContent='Prensa';
      const cepoes=nav.querySelector('a[href="/cepoes/"]');cepoes?nav.insertBefore(a,cepoes):nav.appendChild(a);
    }
    const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('on');io.unobserve(e.target)}}),{threshold:.07});
    document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
    const sub=document.querySelector('.subnav .subnav-in');
    if(sub && location.pathname.startsWith('/territorio/')){
      if(!sub.querySelector('a[href="/territorio/deporte-salud/"]')){
        const a=document.createElement('a');a.href='/territorio/deporte-salud/';a.textContent='Deporte y salud';
        const prod=sub.querySelector('a[href="/territorio/estructura-productiva/"]'),mig=sub.querySelector('a[href="/territorio/migraciones/"]');
        prod?sub.insertBefore(a,prod):mig?sub.insertBefore(a,mig):sub.appendChild(a);
      }
      if(!sub.querySelector('a[href="/territorio/estructura-productiva/"]')){
        const a=document.createElement('a');a.href='/territorio/estructura-productiva/';a.textContent='Estructura productiva';
        const mig=sub.querySelector('a[href="/territorio/migraciones/"]'); mig?sub.insertBefore(a,mig):sub.appendChild(a);
      }
      if(!sub.querySelector('a[href="/territorio/migraciones/"]')){
        const a=document.createElement('a');a.href='/territorio/migraciones/';a.textContent='Migraciones';
        const debt=sub.querySelector('a[href="/territorio/endeudamiento/"]'); debt?sub.insertBefore(a,debt):sub.appendChild(a);
      }
    }
    if(sub && (location.pathname==='/observatorio/'||location.pathname==='/observatorio/index.html')){
      const href='/observatorio/#observatorio-salud-cuidados';
      if(!sub.querySelector(`a[href="${href}"]`)){
        const a=document.createElement('a');a.href=href;a.textContent='Salud';
        const agenda=[...sub.querySelectorAll('a')].find(x=>x.textContent.trim()==='Agenda');
        agenda?sub.insertBefore(a,agenda):sub.appendChild(a);
      }
    }
    initObservatorioHealth();
    initSearch();
    initPress();
  });
  function initObservatorioHealth(){
    if(location.pathname!=='/observatorio/'&&location.pathname!=='/observatorio/index.html')return;
    if(document.getElementById('observatorio-salud-cuidados'))return;
    const main=document.querySelector('main');
    if(!main)return;
    const hero=main.querySelector(':scope > header')||main.querySelector('.page-hero');
    const section=document.createElement('section');
    section.id='observatorio-salud-cuidados';
    section.className='section alt';
    section.innerHTML=`<div class="wrap"><div class="section-head"><div><span class="eyebrow">Eje transversal</span><h2>Salud y cuidados</h2><p>Indicadores y análisis sobre acceso a la salud, salud mental, salud reproductiva, cambios demográficos y cuidados en la Ciudad.</p></div><a class="more" href="/temas/#salud-y-cuidados">Explorar el tema →</a></div><div class="obs-health-grid"><a class="obs-health-card" href="/observatorio/salud-mental/"><span>Salud mental</span><strong>Atención, demanda y red territorial</strong><p>Serie SNIC 2016–2025, comparación federal, advertencias de comparabilidad y red de atención en CABA.</p><em>Explorar →</em></a><a class="obs-health-card" href="/observatorio/natalidad/"><span>Natalidad y demografía</span><strong>La caída de nacimientos en perspectiva</strong><p>Nacimientos, fecundidad y reemplazo generacional en Argentina y CABA, con lectura temporal de la Ley 27.610.</p><em>Explorar →</em></a><a class="obs-health-card" href="/observatorio/salud-reproductiva/"><span>Salud reproductiva</span><strong>PAEV, IVE/ILE y transparencia</strong><p>Monitor de acceso y neutralidad del PAEV, fuentes oficiales y matriz de información pública disponible y faltante.</p><em>Explorar →</em></a><a class="obs-health-card" href="/observatorio/personas-mayores/"><span>Personas mayores</span><strong>Demografía, ingresos, vivienda y cuidados</strong><p>Indicadores públicos para analizar envejecimiento, condiciones de vida y necesidades de cuidado en la Ciudad.</p><em>Explorar →</em></a></div></div>`;
    const style=document.createElement('style');
    style.id='observatorio-salud-cuidados-style';
    style.textContent=`#observatorio-salud-cuidados .section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-bottom:22px}#observatorio-salud-cuidados .section-head p{max-width:760px;margin:.55rem 0 0;color:var(--muted,#5f696e)}.obs-health-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.obs-health-card{display:flex;flex-direction:column;min-height:215px;padding:22px;border:1px solid rgba(23,33,38,.13);border-radius:18px;background:var(--surface,#fff);text-decoration:none;color:inherit;transition:transform .18s ease,border-color .18s ease}.obs-health-card:hover{transform:translateY(-2px);border-color:rgba(23,33,38,.28)}.obs-health-card span{font-size:.78rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--muted,#5f696e)}.obs-health-card strong{font-size:1.25rem;line-height:1.18;margin:.55rem 0}.obs-health-card p{margin:0 0 18px;color:var(--muted,#5f696e);line-height:1.5}.obs-health-card em{margin-top:auto;font-style:normal;font-weight:700}.obs-health-legacy-hidden{display:none!important}@media(max-width:760px){#observatorio-salud-cuidados .section-head{align-items:flex-start;flex-direction:column}.obs-health-grid{grid-template-columns:1fr}}`;
    document.head.appendChild(style);
    const legacy=['/observatorio/personas-mayores/','/observatorio/salud-mental/'];
    legacy.forEach(href=>document.querySelectorAll(`a[href="${href}"]`).forEach(a=>{if(!a.closest('#observatorio-salud-cuidados')&&!a.closest('nav')&&!a.closest('footer'))a.classList.add('obs-health-legacy-hidden')}));
    if(hero)hero.after(section);else main.prepend(section);
  }
  function initPress(){
    if(location.pathname.startsWith('/prensa/'))return;
    const routes=['/territorio/deporte-salud/','/territorio/migraciones/','/territorio/estructura-productiva/','/territorio/endeudamiento/'];
    const route=routes.find(x=>location.pathname===x);if(!route)return;
    if(!document.querySelector('link[href^="/assets/prensa.css"]')&&!document.querySelector('link[href*="prensa.css"]')){const l=document.createElement('link');l.rel='stylesheet';l.href='/assets/prensa.css?v=1';document.head.appendChild(l)}
    const api=`https://nriexnijkjamrmfivfmd.supabase.co/rest/v1/press_notes?select=slug,topic,title,summary,published_at,source_section&status=eq.publicada&source_section=eq.${encodeURIComponent(route)}`;
    fetch(api,{headers:{apikey:'sb_publishable_i2WWiop8sCom0yVZZ7xC8g_NGJCiddq'}}).then(r=>r.json()).then(notes=>{if(!notes.length)return;const section=document.createElement('section');section.className='section alt press-inline';section.id='analisis-prensa';section.innerHTML=`<div class="wrap"><div class="press-inline-head"><div><span class="eyebrow">Datos para comunicar</span><h2>Análisis y prensa</h2><p>Hallazgos breves elaborados a partir de esta sección.</p></div><a class="more" href="/prensa/">Ver todas las notas →</a></div><div class="press-inline-grid">${notes.map(n=>`<a class="press-card" href="/prensa/nota/?slug=${encodeURIComponent(n.slug)}"><span class="press-tag">${n.topic}</span><h3>${n.title}</h3><p>${n.summary}</p><span class="press-meta">${new Date(n.published_at).toLocaleDateString('es-AR')}</span></a>`).join('')}</div></div>`;const footer=document.querySelector('footer');footer?footer.before(section):document.body.appendChild(section)}).catch(()=>{});
  }
  function initSearch(){
    const dialog=document.getElementById('site-search'),open=document.querySelector('[data-search-open]'),close=document.querySelector('[data-search-close]'),input=document.getElementById('site-search-input'),results=document.getElementById('site-search-results'),filters=document.getElementById('site-search-filters');
    if(!dialog||!open||!input||!results)return;let index=null,active='Todo';
    const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    const balanceEntries=[
      {title:'Balance de gestión 2007–2026',url:'/balance/',group:'Balance',type:'Balance de gestión',summary:'Dossiers que relacionan decisiones, recursos y resultados para reconstruir cómo llegó la Ciudad a su situación actual.',tags:['balance','gestion','diagnostico','resultados','PRO','2007 2026'],priority:6},
      {title:'Vivienda y alquiler: balance de gestión',url:'/balance/vivienda-y-alquiler/',group:'Balance',type:'Balance · Dossier',summary:'Inversión habitacional, alquileres, déficit y decisiones de gestión en CABA, con foco 2022–2026.',tags:['vivienda','alquiler','alquileres','habitat','inversion','déficit habitacional','mercado inmobiliario'],priority:10},
      {title:'Salud pública: balance de gestión',url:'/balance/salud-publica/',group:'Balance',type:'Balance · Dossier',summary:'Presupuesto, hospitales, CeSAC, personal y desigualdades territoriales de la salud pública porteña.',tags:['salud','salud publica','hospitales','cesac','personal de salud','presupuesto sanitario'],priority:10},
      {title:'Presupuesto y modelo de gestión: balance',url:'/balance/presupuesto-y-modelo-de-gestion/',group:'Balance',type:'Balance · Dossier',summary:'Ejecución real, prioridades, concesiones y capacidad estatal en el modelo de gestión de la Ciudad.',tags:['presupuesto','modelo de gestion','ejecucion','concesiones','capacidad estatal','gasto publico'],priority:10}
      ,{title:'Personas mayores en Buenos Aires',url:'/publicaciones/informes/personas-mayores-caba/',group:'Publicaciones',type:'Informe temático',summary:'Envejecimiento, desigualdad y políticas públicas: demografía, ingresos, vivienda, salud y cuidados.',tags:['personas mayores','adultos mayores','envejecimiento','cuidados','jubilaciones','salud','CABA'],priority:10}
      ,{title:'Más personas sin techo en Buenos Aires',url:'/publicaciones/informes/situacion-de-calle-caba/',group:'Publicaciones',type:'Informe temático',summary:'Crecimiento, territorio y respuesta estatal ante la emergencia habitacional.',tags:['situacion de calle','sin techo','vivienda','habitat','REPSIC','Censo Popular','CABA'],priority:10}
      ,{title:'Dos evaluaciones, dos respuestas opuestas',url:'/publicaciones/informes/educacion-pisa-fepba-2025/',group:'Publicaciones',type:'Informe temático',summary:'PISA, FEPBA y TESBA: resultados, límites de comparación y propuestas para abrir la información educativa.',tags:['educacion','PISA','FEPBA','TESBA','evaluacion','presupuesto educativo','CABA'],priority:10}
      ,{title:'Seis años de registro y ningún número',url:'/publicaciones/informes/plataformas-juventudes-caba/',group:'Publicaciones',type:'Informe temático',summary:'Trabajo de plataformas, RUTRAMUR y juventudes en la Ciudad de Buenos Aires.',tags:['trabajo','plataformas','repartidores','RUTRAMUR','juventudes','empleo','CABA'],priority:10}
      ,{title:'Lo nuevo en CEPOES',url:'/lo-nuevo/',group:'Publicaciones',type:'Actualidad',summary:'Últimas publicaciones, datos, herramientas y notas de prensa de CEPOES.',tags:['lo nuevo','novedades','ultimas publicaciones','actualidad','CEPOES'],priority:10}
      ,{title:'Endeudarse para llegar a fin de mes',url:'/publicaciones/informes/endeudarse-para-llegar-a-fin-de-mes/',group:'Publicaciones',type:'Informe especial',summary:'Deuda, mora y desigualdad territorial de los hogares de la Ciudad.',tags:['deuda','endeudamiento','mora','hogares','barrios','BCRA','CABA'],priority:10}
      ,{title:'Producción y empleo: una recuperación desigual',url:'/publicaciones/informe-coyuntura-01-junio-2026/',group:'Publicaciones',type:'Informe de coyuntura',summary:'Capacidad instalada, empleo, empresas y vacancia comercial en Argentina y CABA.',tags:['produccion','empleo','industria','empresas','comercio','capacidad instalada','CABA'],priority:10}
    ];
    const dedupe=items=>{const merged=new Map();items.forEach(x=>{if(!x?.url)return;const url=x.url.replace('/observatorio/presupuesto/','/presupuesto/ejecucion/').replace('/territorio/presupuesto/','/presupuesto/territorio/');const next={...x,url},current=merged.get(url);if(!current||(next.priority||0)>(current.priority||0))merged.set(url,{...current,...next})});return [...merged.values()]};
    const withBalance=items=>dedupe([...(items||[]),...balanceEntries]);
    const ensure=async()=>{if(index)return index;try{const r=await fetch('/assets/data/search-index.json?v=258');index=await r.json();try{const api='https://nriexnijkjamrmfivfmd.supabase.co/rest/v1/press_notes?select=slug,topic,title,summary,tags&status=eq.publicada&limit=500',pr=await fetch(api,{headers:{apikey:'sb_publishable_i2WWiop8sCom0yVZZ7xC8g_NGJCiddq'}});if(pr.ok)(await pr.json()).forEach(n=>index.push({title:n.title,url:'/prensa/nota/?slug='+encodeURIComponent(n.slug),group:'Publicaciones',type:'Nota de prensa',summary:n.summary,tags:[n.topic,...(n.tags||[])]}))}catch(e){}index=dedupe(index)}catch(e){index=[]}return index};
    const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
    const render=async()=>{const q=norm(input.value.trim()),items=withBalance(await ensure());if(q.length<2){results.innerHTML='<p class="search-empty">Escribí al menos dos caracteres para buscar.</p>';return}const words=q.split(/\s+/).filter(Boolean);const found=items.map(x=>{const title=norm(x.title),hay=norm([x.title,x.summary,(x.tags||[]).join(' ')].join(' ')),matches=words.reduce((a,w)=>a+(hay.includes(w)?1:0),0),score=(title===q?1000:title.includes(q)?200:0)+matches*10+(matches?(x.priority||0):0);return {x,score}}).filter(o=>o.score>0&&(active==='Todo'||o.x.group===active)).sort((a,b)=>b.score-a.score||a.x.title.localeCompare(b.x.title,'es')).slice(0,14).map(o=>o.x);results.innerHTML=found.length?found.map(x=>`<a class="search-result" href="${esc(x.url)}"><span class="search-result-type">${esc(x.type||x.group||'')}</span><strong>${esc(x.title)}</strong><p>${esc(x.summary||'')}</p></a>`).join(''):'<p class="search-empty">No encontramos resultados con esos términos.</p>'};
    open.addEventListener('click',async()=>{dialog.showModal();document.body.classList.add('search-open');await ensure();setTimeout(()=>input.focus(),30)});if(close)close.addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>document.body.classList.remove('search-open'));dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});input.addEventListener('input',render);if(filters)filters.addEventListener('click',e=>{const b=e.target.closest('[data-search-filter]');if(!b)return;active=b.dataset.searchFilter;filters.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===b));render()});
  }
})();
