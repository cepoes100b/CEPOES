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
    initObservatorioHealth();
    initSearch();
    initPress();
  });
  function initObservatorioHealth(){
    if(location.pathname!=='/observatorio/'&&location.pathname!=='/observatorio/index.html')return;
    if(document.getElementById('observatorio-salud-cuidados'))return;
    const target=[...document.querySelectorAll('h2')].find(h=>h.textContent.trim()==='El Observatorio')?.closest('section');
    const main=document.querySelector('main');
    if(!main)return;
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
    if(target)target.before(section);else main.appendChild(section);
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
    const ensure=async()=>{if(index)return index;try{const r=await fetch('/assets/data/search-index.json?v=227');index=await r.json();index.forEach(x=>{if(x.url==='/observatorio/presupuesto/')x.url='/presupuesto/ejecucion/';if(x.url==='/territorio/presupuesto/')x.url='/presupuesto/territorio/'});if(!index.some(x=>x.url==='/territorio/deporte-salud/'))index.push({title:'Deporte y vida saludable en CABA',url:'/territorio/deporte-salud/',group:'Territorio',type:'Datos',summary:'Clubes, polideportivos, Estaciones Saludables y CeSAC: mapa, actividades y brechas por comuna.',tags:['deporte','salud','clubes','polideportivos','actividad fisica','estaciones saludables','cesac','barrios']});if(!index.some(x=>x.url==='/territorio/estructura-productiva/'))index.push({title:'Estructura productiva de CABA',url:'/territorio/estructura-productiva/',group:'Territorio',type:'Datos',summary:'Empresas privadas registradas, actividad comercial 2026 por comuna, habilitaciones recientes y mapa histórico por manzana.',tags:['estructura productiva','empresas','comercio','locales','habilitaciones','OEDE','SIPA','IDECBA','RUS']});if(!index.some(x=>x.url==='/territorio/migraciones/'))index.push({title:'Migraciones en CABA',url:'/territorio/migraciones/',group:'Territorio',type:'Datos',summary:'Migración internacional e interna: comunidades de origen, mapa por comuna, dinámica reciente, trabajo, educación y pobreza.',tags:['migraciones','migracion internacional','migracion interna','EAH','INDEC','IDECBA']});if(!index.some(x=>x.url==='/presupuesto/descentralizacion/'))index.push({title:'Descentralización y Comunas',url:'/presupuesto/descentralizacion/',group:'Datos',type:'Presupuesto y Estado',summary:'Presupuesto administrado por las 15 Comunas, competencias transferidas y matriz de transparencia institucional.',tags:['descentralizacion','comunas','presupuesto comunal','ley 1777','ley 5629','transparencia','participacion']});if(!index.some(x=>x.url==='/observatorio/natalidad/'))index.push({title:'Natalidad y cambio demográfico',url:'/observatorio/natalidad/',group:'Datos',type:'Salud y cuidados',summary:'Nacimientos y fecundidad en Argentina y CABA: cronología, reemplazo generacional y contraste temporal con la Ley 27.610.',tags:['natalidad','fecundidad','demografia','nacimientos','IVE','ley 27610','reemplazo generacional','salud']});if(!index.some(x=>x.url==='/observatorio/salud-reproductiva/'))index.push({title:'Salud reproductiva y PAEV en CABA',url:'/observatorio/salud-reproductiva/',group:'Datos',type:'Salud y cuidados',summary:'Monitor de transparencia, acceso y neutralidad del PAEV, con base oficial IVE/ILE y matriz de información pública.',tags:['salud reproductiva','PAEV','IVE','ILE','embarazo vulnerable','CESAC','autonomia','CABA']});if(!index.some(x=>x.url==='/prensa/'))index.push({title:'Prensa — CEPOES',url:'/prensa/',group:'Publicaciones',type:'Notas de prensa',summary:'Hallazgos, datos citables y materiales para periodistas.',tags:['prensa','medios','datos','hallazgos']});if(!index.some(x=>x.url==='/temas/'))index.push({title:'Explorar por tema',url:'/temas/',group:'Publicaciones',type:'Índice temático',summary:'Datos, publicaciones, notas, propuestas y territorio conectados por ocho temas comunes.',tags:['vivienda','salud','educacion','trabajo','precios','produccion','presupuesto','ambiente','movilidad']});try{const api='https://nriexnijkjamrmfivfmd.supabase.co/rest/v1/press_notes?select=slug,topic,title,summary,tags&status=eq.publicada&limit=500',pr=await fetch(api,{headers:{apikey:'sb_publishable_i2WWiop8sCom0yVZZ7xC8g_NGJCiddq'}});if(pr.ok)(await pr.json()).forEach(n=>index.push({title:n.title,url:'/prensa/nota/?slug='+encodeURIComponent(n.slug),group:'Publicaciones',type:'Nota de prensa',summary:n.summary,tags:[n.topic,...(n.tags||[])]}))}catch(e){}}catch(e){index=[]}return index};
    const render=async()=>{const q=norm(input.value.trim()),items=await ensure();if(q.length<2){results.innerHTML='<p class="search-empty">Escribí al menos dos caracteres para buscar.</p>';return}const words=q.split(/\s+/).filter(Boolean);const found=items.map(x=>{const hay=norm([x.title,x.summary,(x.tags||[]).join(' ')].join(' '));const score=words.reduce((a,w)=>a+(hay.includes(w)?1:0),0)+(norm(x.title).includes(q)?2:0);return {x,score}}).filter(o=>o.score>0&&(active==='Todo'||o.x.group===active)).sort((a,b)=>b.score-a.score||a.x.title.localeCompare(b.x.title)).slice(0,14).map(o=>o.x);results.innerHTML=found.length?found.map(x=>`<a class="search-result" href="${x.url}"><span class="search-result-type">${x.type||x.group||''}</span><strong>${x.title}</strong><p>${x.summary||''}</p></a>`).join(''):'<p class="search-empty">No encontramos resultados con esos términos.</p>'};
    open.addEventListener('click',async()=>{dialog.showModal();document.body.classList.add('search-open');await ensure();setTimeout(()=>input.focus(),30)});if(close)close.addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>document.body.classList.remove('search-open'));dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});input.addEventListener('input',render);if(filters)filters.addEventListener('click',e=>{const b=e.target.closest('[data-search-filter]');if(!b)return;active=b.dataset.searchFilter;filters.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===b));render()});
  }
})();
