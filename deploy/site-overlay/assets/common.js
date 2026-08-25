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
      if(location.pathname==='/territorio/' && !document.querySelector('[data-cepoes-deporte-salud-access]')){
        const anchors=Array.from(document.querySelectorAll('a[href="/territorio/endeudamiento/"]')).filter(x=>!x.closest('.subnav'));
        const source=anchors.at(-1);
        if(source&&source.parentNode){
          const a=source.cloneNode(true);a.href='/territorio/deporte-salud/';a.dataset.cepoesDeporteSaludAccess='1';a.textContent='Deporte y vida saludable →';source.parentNode.insertBefore(a,source);
        }
      }
    }
    initSearch();
  });
  function initSearch(){
    const dialog=document.getElementById('site-search'),open=document.querySelector('[data-search-open]'),close=document.querySelector('[data-search-close]'),input=document.getElementById('site-search-input'),results=document.getElementById('site-search-results'),filters=document.getElementById('site-search-filters');
    if(!dialog||!open||!input||!results)return;let index=null,active='Todo';
    const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    const ensure=async()=>{if(index)return index;try{const r=await fetch('/assets/data/search-index.json?v=227');index=await r.json();if(!index.some(x=>x.url==='/territorio/deporte-salud/'))index.push({title:'Deporte y vida saludable en CABA',url:'/territorio/deporte-salud/',group:'Territorio',type:'Datos',summary:'Clubes, polideportivos, Estaciones Saludables y CeSAC: mapa, actividades y brechas por comuna.',tags:['deporte','salud','clubes','polideportivos','actividad fisica','estaciones saludables','cesac','barrios']});if(!index.some(x=>x.url==='/territorio/estructura-productiva/'))index.push({title:'Estructura productiva de CABA',url:'/territorio/estructura-productiva/',group:'Territorio',type:'Datos',summary:'Empresas privadas registradas, actividad comercial 2026 por comuna, habilitaciones recientes y mapa histórico por manzana.',tags:['estructura productiva','empresas','comercio','locales','habilitaciones','OEDE','SIPA','IDECBA','RUS']});if(!index.some(x=>x.url==='/territorio/migraciones/'))index.push({title:'Migraciones en CABA',url:'/territorio/migraciones/',group:'Territorio',type:'Datos',summary:'Migración internacional e interna: comunidades de origen, mapa por comuna, dinámica reciente, trabajo, educación y pobreza.',tags:['migraciones','migracion internacional','migracion interna','EAH','INDEC','IDECBA']})}catch(e){index=[]}return index};
    const render=async()=>{const q=norm(input.value.trim()),items=await ensure();if(q.length<2){results.innerHTML='<p class="search-empty">Escribí al menos dos caracteres para buscar.</p>';return}const words=q.split(/\s+/).filter(Boolean);const found=items.map(x=>{const hay=norm([x.title,x.summary,(x.tags||[]).join(' ')].join(' '));const score=words.reduce((a,w)=>a+(hay.includes(w)?1:0),0)+(norm(x.title).includes(q)?2:0);return {x,score}}).filter(o=>o.score>0&&(active==='Todo'||o.x.group===active)).sort((a,b)=>b.score-a.score||a.x.title.localeCompare(b.x.title)).slice(0,14).map(o=>o.x);results.innerHTML=found.length?found.map(x=>`<a class="search-result" href="${x.url}"><span class="search-result-type">${x.type||x.group||''}</span><strong>${x.title}</strong><p>${x.summary||''}</p></a>`).join(''):'<p class="search-empty">No encontramos resultados con esos términos.</p>'};
    open.addEventListener('click',async()=>{dialog.showModal();document.body.classList.add('search-open');await ensure();setTimeout(()=>input.focus(),30)});if(close)close.addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>document.body.classList.remove('search-open'));dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});input.addEventListener('input',render);if(filters)filters.addEventListener('click',e=>{const b=e.target.closest('[data-search-filter]');if(!b)return;active=b.dataset.searchFilter;filters.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x===b));render()});
  }
})();