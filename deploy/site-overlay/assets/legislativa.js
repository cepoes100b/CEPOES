(() => {
  'use strict';

  const cfg = window.CEPOES_LEGISLATIVA || {};
  const el = id => document.getElementById(id);
  const PUBLIC_BASE = cfg.publicDataBase || 'https://raw.githubusercontent.com/cepoes100b/CEPOES/main/';
  const state = { client:null, profile:null, legislative:null, sessions:null, structure:null, analyses:[], briefs:[], projects:[], view:'inicio' };
  const titles = { inicio:'Inicio', expedientes:'Expedientes', analisis:'Análisis', sesiones:'Carpeta de sesión', proyectos:'Banco de proyectos' };
  const writerRoles = new Set(['admin','asesor','investigador']);

  function esc(value){return String(value ?? '').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
  function arr(v){return Array.isArray(v)?v:[];}
  function displayDate(v){if(!v)return '—'; const d=new Date(`${String(v).slice(0,10)}T12:00:00-03:00`); return Number.isNaN(d.getTime())?esc(v):new Intl.DateTimeFormat('es-AR',{day:'2-digit',month:'short',year:'numeric'}).format(d);}
  function todayBA(){return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Argentina/Buenos_Aires',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());}
  function textPosition(v){return ({acompanar:'Acompañar',acompanar_con_modificaciones:'Acompañar con modificaciones',abstenerse:'Abstenerse',rechazar:'Rechazar',sin_definir:'Sin definir'})[v]||v||'Sin definir';}
  function setStatus(text,kind=''){const x=el('data-status'); if(!x)return; x.textContent=text; x.className=`status-chip ${kind}`.trim();}
  function globalMessage(text){const x=el('global-message'); if(!text){x.hidden=true;return;} x.textContent=text;x.hidden=false;}

  function configured(){return Boolean(cfg.supabaseUrl && cfg.supabaseAnonKey && window.supabase?.createClient);}
  function failClosed(){
    const form=el('login-form');
    form.querySelectorAll('input,button').forEach(x=>x.disabled=true);
    el('login-message').textContent='El Área Legislativa todavía no tiene vinculada su capa de autenticación. El acceso permanece cerrado por seguridad.';
  }

  async function validateProfile(user){
    const {data,error}=await state.client.from('profiles').select('id,display_name,role,active,commission_filters').eq('id',user.id).maybeSingle();
    if(error || !data || !data.active){
      await state.client.auth.signOut();
      throw new Error('La cuenta existe pero no está habilitada para el Área Legislativa.');
    }
    state.profile=data;
    return data;
  }

  async function bootSession(session){
    if(!session?.user){showAuth();return;}
    try{
      await validateProfile(session.user);
      showApp();
      await loadAll();
    }catch(err){showAuth(err.message);}
  }

  function showAuth(message=''){
    el('auth-view').hidden=false; el('app-view').hidden=true;
    if(message)el('login-message').textContent=message;
  }
  function showApp(){
    el('auth-view').hidden=true; el('app-view').hidden=false;
    const p=state.profile||{};
    el('user-summary').innerHTML=`<strong>${esc(p.display_name||'Usuario CEPOES')}</strong><small>${esc(p.role||'')}</small>`;
    el('new-analysis-btn').hidden=!writerRoles.has(p.role);
  }

  function preparePasswordlessUi(){
    const password=el('login-password');
    if(password){
      password.required=false;
      password.disabled=true;
      const label=password.closest('label');
      if(label)label.hidden=true;
    }
    const submit=el('login-form')?.querySelector('button[type="submit"]');
    if(submit)submit.textContent='Recibir enlace de acceso';
  }

  async function login(ev){
    ev.preventDefault();
    const msg=el('login-message');
    const submit=el('login-form')?.querySelector('button[type="submit"]');
    const email=el('login-email').value.trim().toLowerCase();
    if(!email){msg.textContent='Ingresá tu correo electrónico.';return;}
    msg.textContent='Enviando enlace seguro…';
    if(submit)submit.disabled=true;
    const redirectTo=new URL('/legislativa/',window.location.origin).href;
    const {error}=await state.client.auth.signInWithOtp({
      email,
      options:{shouldCreateUser:true,emailRedirectTo:redirectTo}
    });
    if(submit)submit.disabled=false;
    if(error){
      console.error(error);
      msg.textContent='No se pudo enviar el enlace. Si tu correo está autorizado, revisaremos la configuración de acceso.';
      return;
    }
    msg.textContent='Te enviamos un enlace de acceso. Abrilo desde este dispositivo para ingresar.';
  }

  async function logout(){await state.client.auth.signOut(); state.profile=null; showAuth();}

  async function fetchJson(url){
    const r=await fetch(url,{cache:'no-store'});
    if(!r.ok)throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  async function loadPublic(){
    const [leg,ses,est]=await Promise.all([
      fetchJson(`${PUBLIC_BASE}legislatura_publica.json`),
      fetchJson(`${PUBLIC_BASE}sesiones_publicas.json`),
      fetchJson(`${PUBLIC_BASE}estructura_legislativa.json`)
    ]);
    state.legislative=leg; state.sessions=ses; state.structure=est;
  }

  async function loadPrivate(){
    const [a,b,p]=await Promise.all([
      state.client.from('expediente_analyses').select('*').order('updated_at',{ascending:false}).limit(250),
      state.client.from('session_briefs').select('*,session_brief_items(*)').order('session_date',{ascending:false}).limit(100),
      state.client.from('project_bank').select('*').order('updated_at',{ascending:false}).limit(200)
    ]);
    if(a.error)throw a.error; if(b.error)throw b.error; if(p.error)throw p.error;
    state.analyses=a.data||[]; state.briefs=b.data||[]; state.projects=p.data||[];
  }

  async function loadAll(){
    setStatus('Actualizando información…'); globalMessage('');
    try{
      await Promise.all([loadPublic(),loadPrivate()]);
      renderAll();
      const stamp=state.legislative?.generado || state.sessions?.actualizado_en;
      setStatus(stamp?`Actualizado ${displayDate(stamp)}`:'Información actualizada','ok');
    }catch(err){
      console.error(err); setStatus('Error de actualización','error');
      globalMessage('No fue posible cargar toda la información. El acceso privado sigue protegido; reintentá en unos minutos.');
    }
  }

  function meetingMatchesProfile(m){
    const filters=arr(state.profile?.commission_filters).map(x=>String(x).toLowerCase()).filter(Boolean);
    if(!filters.length)return true;
    const name=String(m.comision||'').toLowerCase();
    return filters.some(f=>name.includes(f));
  }

  function uniqueExpedientes(){
    const map=new Map();
    for(const p of arr(state.legislative?.expedientes)){
      const key=String(p.numero||'').trim(); if(!key)continue;
      const prev=map.get(key);
      if(!prev || String(p.fecha_reunion||'')>String(prev.fecha_reunion||'')) map.set(key,p);
    }
    return [...map.values()].sort((a,b)=>String(b.fecha_reunion||'').localeCompare(String(a.fecha_reunion||'')));
  }

  function renderAll(){renderHome();renderTopicOptions();renderExpedientes();renderAnalyses();renderBriefs();renderProjectBank();}

  function renderHome(){
    const today=todayBA();
    const meetings=arr(state.legislative?.reuniones).filter(m=>String(m.fecha||'')>=today && meetingMatchesProfile(m)).sort((a,b)=>`${a.fecha}${a.hora||''}`.localeCompare(`${b.fecha}${b.hora||''}`));
    const exp=uniqueExpedientes();
    const high=exp.filter(x=>x.prioridad_tecnica==='alta' && String(x.fecha_reunion||'')>=today);
    el('kpi-grid').innerHTML=[
      ['Próximas reuniones',meetings.length,'según agenda oficial'],
      ['Expedientes detectados',exp.length,'en el universo reciente'],
      ['Atención técnica alta',high.length,'clasificación pública'],
      ['Análisis internos',state.analyses.length,'capa privada CEPOES']
    ].map(x=>`<article class="kpi"><span>${esc(x[0])}</span><strong>${esc(x[1])}</strong><small>${esc(x[2])}</small></article>`).join('');

    el('agenda-list').innerHTML=meetings.slice(0,10).map(m=>`<article class="list-item"><div class="list-item-head"><strong>${esc(m.comision||'Reunión')}</strong><span class="badge">${displayDate(m.fecha)} · ${esc(m.hora||'s/h')}</span></div><p>${esc((m.tipo_reunion||'reunión').replaceAll('_',' '))}${m.expedientes_anunciados?` · ${esc(m.expedientes_anunciados)} expedientes anunciados`:''}</p><div class="meta"><span>Fuente oficial</span>${m.url?`<a class="exp-link" target="_blank" rel="noopener" href="${esc(m.url)}">Abrir agenda ↗</a>`:''}</div></article>`).join('') || '<div class="empty">No hay reuniones próximas detectadas para los filtros de este usuario.</div>';

    el('priority-list').innerHTML=high.slice(0,7).map(p=>`<article class="list-item"><div class="list-item-head"><strong>${esc(p.numero)}</strong><span class="internal-priority alta">ALTA</span></div><p>${esc(p.sumario)}</p><div class="meta"><span>${esc(p.comision||'')}</span><span>${displayDate(p.fecha_reunion)}</span></div></article>`).join('') || '<div class="empty">No hay expedientes próximos clasificados con prioridad técnica alta.</div>';

    el('latest-analysis-list').innerHTML=state.analyses.slice(0,6).map(a=>`<article class="list-item"><div class="list-item-head"><strong>${esc(a.expediente_numero)}</strong><span class="internal-priority ${esc(a.internal_priority)}">${esc(a.internal_priority)}</span></div><p>${esc(a.title)}</p><div class="meta"><span>${esc(textPosition(a.recommendation))}</span><span>${esc(a.review_status)}</span></div></article>`).join('') || '<div class="empty">Todavía no hay análisis internos cargados.</div>';
  }

  function renderTopicOptions(){
    const topics=arr(state.legislative?.taxonomia_tematica);
    el('exp-topic').innerHTML='<option value="">Todos los temas</option>'+topics.map(x=>`<option value="${esc(x)}">${esc(x.replaceAll('_',' '))}</option>`).join('');
  }

  function renderExpedientes(){
    const q=(el('exp-search')?.value||'').trim().toLowerCase(), topic=el('exp-topic')?.value||'', prio=el('exp-priority')?.value||'';
    let rows=uniqueExpedientes();
    rows=rows.filter(p=>{
      const hay=[p.numero,p.sumario,p.autor,p.comision,...arr(p.temas)].join(' ').toLowerCase();
      return (!q||hay.includes(q)) && (!topic||arr(p.temas).includes(topic)) && (!prio||p.prioridad_tecnica===prio);
    }).slice(0,300);
    el('expedientes-table').innerHTML=`<table><thead><tr><th>Expediente</th><th>Sumario</th><th>Comisión</th><th>Fecha</th><th>Prioridad técnica</th><th>Análisis</th></tr></thead><tbody>${rows.map(p=>{
      const has=state.analyses.find(a=>a.expediente_numero===p.numero);
      return `<tr><td>${p.url_expediente?`<a class="exp-link" target="_blank" rel="noopener" href="${esc(p.url_expediente)}">${esc(p.numero)} ↗</a>`:`<strong>${esc(p.numero)}</strong>`}<div class="meta"><span>${esc(p.autor||'')}</span></div></td><td class="summary-cell">${esc(p.sumario)}</td><td>${esc(p.comision||'—')}</td><td>${displayDate(p.fecha_reunion)}</td><td><strong class="priority-${esc(p.prioridad_tecnica)}">${esc(p.prioridad_tecnica||'—')}</strong></td><td>${has?`<button class="secondary-btn" data-open-analysis="${esc(has.id)}">Ver análisis</button>`:(writerRoles.has(state.profile?.role)?`<button class="secondary-btn" data-new-for-exp="${esc(p.numero)}">Analizar</button>`:'—')}</td></tr>`;
    }).join('')}</tbody></table>`;
    if(!rows.length)el('expedientes-table').innerHTML='<div class="empty">No hay expedientes que coincidan con los filtros.</div>';
  }

  function renderAnalyses(){
    el('analisis-list').innerHTML=state.analyses.map(a=>`<article class="analysis-card"><header><div><span class="eyebrow">${esc(a.document_kind||'proyecto')} · ${esc(a.expediente_numero)}</span><h3>${esc(a.title)}</h3></div><span class="internal-priority ${esc(a.internal_priority)}">${esc(a.internal_priority)}</span></header><p>${esc(a.executive_summary||'Sin resumen ejecutivo cargado.')}</p><div class="position"><strong>Posición sugerida:</strong> ${esc(textPosition(a.recommendation))}</div><div class="meta"><span>${esc(a.review_status)}</span><span>Actualizado ${displayDate(a.updated_at)}</span></div><div class="card-actions"><button data-open-analysis="${esc(a.id)}">Ver ficha</button>${writerRoles.has(state.profile?.role)?`<button data-edit-analysis="${esc(a.id)}">Editar</button>`:''}</div></article>`).join('') || '<div class="empty">Todavía no hay análisis internos. Los perfiles autorizados pueden crear el primero.</div>';
  }

  function renderBriefs(){
    el('briefs-list').innerHTML=state.briefs.map(b=>`<article class="analysis-card"><header><div><span class="eyebrow">SESIÓN · ${displayDate(b.session_date)}</span><h3>${esc(b.title)}</h3></div><span class="badge">${esc(b.status)}</span></header><p>${esc(b.executive_summary||'Sin resumen consolidado.')}</p><div class="meta"><span>${arr(b.session_brief_items).length} asuntos priorizados</span><span>Actualizado ${displayDate(b.updated_at)}</span></div>${arr(b.session_brief_items).length?`<div class="stack-list" style="margin-top:12px">${arr(b.session_brief_items).sort((a,c)=>(a.item_order||0)-(c.item_order||0)).slice(0,8).map(i=>`<div class="list-item"><div class="list-item-head"><strong>${esc(i.expediente_numero||i.title||'Asunto')}</strong><span class="internal-priority ${esc(i.internal_priority)}">${esc(i.internal_priority)}</span></div><p>${esc(i.key_argument||i.recommendation||'')}</p></div>`).join('')}</div>`:''}</article>`).join('') || '<div class="empty">Todavía no hay carpetas internas de sesión.</div>';
  }

  function renderProjectBank(){
    el('project-bank-list').innerHTML=state.projects.map(p=>`<article class="analysis-card"><header><div><span class="eyebrow">${esc(p.area||'Agenda propia')}</span><h3>${esc(p.title)}</h3></div><span class="badge">${esc(p.stage)}</span></header><p>${esc(p.problem_statement||'')}</p><div class="meta"><span>${esc(p.owner_name||'')}</span><span>Actualizado ${displayDate(p.updated_at)}</span></div></article>`).join('') || '<div class="empty">Todavía no hay iniciativas cargadas en el banco de proyectos.</div>';
  }

  function changeView(view){
    state.view=view; document.querySelectorAll('.view').forEach(x=>x.classList.toggle('active',x.id===`view-${view}`)); document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===view)); el('view-title').textContent=titles[view]||view; el('new-analysis-btn').hidden=!(writerRoles.has(state.profile?.role)&&view==='analisis');
  }

  function resetAnalysisForm(){el('analysis-form').reset();el('analysis-id').value='';el('analysis-priority').value='media';el('analysis-position').value='sin_definir';el('analysis-status').value='borrador';el('analysis-form-title').textContent='Nuevo análisis';el('analysis-form-message').textContent='';}
  function openNewAnalysis(expediente=''){resetAnalysisForm();el('analysis-expediente').value=expediente;el('analysis-dialog').showModal();}
  function fillAnalysis(a,editable=false){
    resetAnalysisForm(); const map={
      'analysis-id':a.id,'analysis-expediente':a.expediente_numero,'analysis-kind':a.document_kind,'analysis-title':a.title,'analysis-source':a.source_url,'analysis-summary':a.executive_summary,'analysis-priority':a.internal_priority,'analysis-position':a.recommendation,'analysis-fiscal':a.fiscal_impact,'analysis-territorial':a.territorial_impact,'analysis-legal':a.legal_impact,'analysis-risks':a.risks,'analysis-rationale':a.rationale,'analysis-amendments':a.proposed_amendments,'analysis-questions':arr(a.committee_questions).join('\n'),'analysis-arguments':a.intervention_arguments,'analysis-status':a.review_status,'analysis-tags':arr(a.tags).join(', ')
    }; Object.entries(map).forEach(([id,v])=>{if(el(id))el(id).value=v??'';}); el('analysis-form-title').textContent=editable?'Editar análisis':'Ficha de análisis';
    el('analysis-form').querySelectorAll('input,select,textarea').forEach(x=>x.disabled=!editable); el('analysis-form').querySelector('button[type="submit"]').hidden=!editable; el('analysis-dialog').showModal();
  }
  function restoreEditorState(){el('analysis-form').querySelectorAll('input,select,textarea').forEach(x=>x.disabled=false);el('analysis-form').querySelector('button[type="submit"]').hidden=false;}

  async function saveAnalysis(ev){
    ev.preventDefault(); const msg=el('analysis-form-message'); msg.textContent='Guardando…';
    const id=el('analysis-id').value||null;
    const payload={expediente_numero:el('analysis-expediente').value.trim(),document_kind:el('analysis-kind').value,title:el('analysis-title').value.trim(),source_url:el('analysis-source').value.trim()||null,executive_summary:el('analysis-summary').value.trim(),internal_priority:el('analysis-priority').value,recommendation:el('analysis-position').value,fiscal_impact:el('analysis-fiscal').value.trim(),territorial_impact:el('analysis-territorial').value.trim(),legal_impact:el('analysis-legal').value.trim(),risks:el('analysis-risks').value.trim(),rationale:el('analysis-rationale').value.trim(),proposed_amendments:el('analysis-amendments').value.trim(),committee_questions:el('analysis-questions').value.split('\n').map(x=>x.trim()).filter(Boolean),intervention_arguments:el('analysis-arguments').value.trim(),review_status:el('analysis-status').value,tags:el('analysis-tags').value.split(',').map(x=>x.trim()).filter(Boolean),updated_by:state.profile.id};
    let result;
    if(id) result=await state.client.from('expediente_analyses').update(payload).eq('id',id).select().single();
    else result=await state.client.from('expediente_analyses').insert({...payload,created_by:state.profile.id}).select().single();
    if(result.error){console.error(result.error);msg.textContent='No se pudo guardar el análisis.';return;}
    msg.textContent='Guardado.'; await loadPrivate(); renderAll(); setTimeout(()=>{el('analysis-dialog').close();restoreEditorState();},250);
  }

  function bind(){
    el('login-form').addEventListener('submit',login);el('logout-btn').addEventListener('click',logout);
    document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>changeView(b.dataset.view)));
    ['exp-search','exp-topic','exp-priority'].forEach(id=>el(id)?.addEventListener(id==='exp-search'?'input':'change',renderExpedientes));
    el('new-analysis-btn').addEventListener('click',()=>openNewAnalysis());el('analysis-form').addEventListener('submit',saveAnalysis);
    document.querySelectorAll('[data-close-dialog]').forEach(b=>b.addEventListener('click',()=>{el('analysis-dialog').close();restoreEditorState();}));
    document.body.addEventListener('click',ev=>{
      const view=ev.target.closest('[data-open-analysis]'), edit=ev.target.closest('[data-edit-analysis]'), fresh=ev.target.closest('[data-new-for-exp]');
      if(view){const a=state.analyses.find(x=>x.id===view.dataset.openAnalysis);if(a)fillAnalysis(a,false);}
      if(edit){const a=state.analyses.find(x=>x.id===edit.dataset.editAnalysis);if(a)fillAnalysis(a,true);}
      if(fresh)openNewAnalysis(fresh.dataset.newForExp);
    });
  }

  async function init(){
    bind();
    preparePasswordlessUi();
    if(!configured()){failClosed();return;}
    state.client=window.supabase.createClient(cfg.supabaseUrl,cfg.supabaseAnonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
    const {data}=await state.client.auth.getSession(); await bootSession(data.session);
    state.client.auth.onAuthStateChange((_event,session)=>{if(!session)showAuth();});
  }

  document.addEventListener('DOMContentLoaded',init);
})();