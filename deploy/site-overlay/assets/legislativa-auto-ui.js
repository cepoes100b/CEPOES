(() => {
  'use strict';

  const esc = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const arr = value => Array.isArray(value) ? value : [];
  const positionText = value => ({
    acompanar:'Acompañar',
    acompanar_con_modificaciones:'Acompañar con modificaciones',
    abstenerse:'Abstenerse',
    rechazar:'Rechazar',
    sin_definir:'Sin definir'
  })[value] || value || 'Sin definir';
  const displayDate = value => {
    if (!value) return '—';
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? esc(value) : new Intl.DateTimeFormat('es-AR',{day:'2-digit',month:'short',year:'numeric'}).format(d);
  };

  let client = null;
  let current = [];
  let currentById = new Map();

  function injectStyles(){
    if (document.getElementById('legislativa-auto-styles')) return;
    const style = document.createElement('style');
    style.id = 'legislativa-auto-styles';
    style.textContent = `
      .auto-meta{display:flex;gap:7px;flex-wrap:wrap;align-items:center;margin-top:9px}
      .auto-chip{display:inline-flex;align-items:center;border-radius:999px;padding:5px 8px;border:1px solid #c9d8d3;background:#f2f8f6;color:#225f53;font:700 .6rem Poppins,sans-serif}
      .auto-chip.review{border-color:#e0c6a5;background:#fff8ed;color:#8a5521}
      .auto-chip.valid{border-color:#b9d7ce;background:#edf8f4;color:#28775d}
      .auto-confidence{font-size:.64rem;color:var(--muted)}
      .analysis-auto-note{padding:10px 12px;border:1px solid #d7e4df;background:#f5faf8;border-radius:10px;color:#50635d;font-size:.7rem;line-height:1.45}
    `;
    document.head.appendChild(style);
  }

  function injectEditorFields(){
    const risks = document.getElementById('analysis-risks');
    if (!risks || document.getElementById('analysis-actors')) return;
    const anchor = risks.closest('label');
    if (!anchor) return;
    anchor.insertAdjacentHTML('afterend', `
      <label>Actores y sectores afectados<textarea id="analysis-actors" rows="3"></textarea></label>
      <div class="form-grid two">
        <label>Argumentos técnicos a favor<textarea id="analysis-for" rows="4"></textarea></label>
        <label>Argumentos técnicos en contra<textarea id="analysis-against" rows="4"></textarea></label>
      </div>
      <label>Brechas de evidencia<textarea id="analysis-gaps" rows="3" placeholder="Una brecha por línea"></textarea></label>
      <div id="analysis-auto-note" class="analysis-auto-note" hidden></div>
    `);
  }

  function setEditorExtras(){
    const id = document.getElementById('analysis-id')?.value || '';
    const a = currentById.get(id);
    const actors = document.getElementById('analysis-actors');
    const yes = document.getElementById('analysis-for');
    const no = document.getElementById('analysis-against');
    const gaps = document.getElementById('analysis-gaps');
    const note = document.getElementById('analysis-auto-note');
    if (!actors || !yes || !no || !gaps || !note) return;
    actors.value = a?.affected_actors || '';
    yes.value = a?.arguments_for || '';
    no.value = a?.arguments_against || '';
    gaps.value = arr(a?.evidence_gaps).join('\n');
    if (a?.analysis_origin === 'automatic') {
      const confidence = Number.isFinite(Number(a.automation_confidence)) ? `${Math.round(Number(a.automation_confidence)*100)}%` : 'sin estimar';
      note.hidden = false;
      note.innerHTML = `<strong>Origen automático.</strong> Este análisis fue generado como borrador técnico y requiere revisión humana. Confianza declarada: ${esc(confidence)}${a.automation_model ? ` · Modelo: ${esc(a.automation_model)}` : ''}.`;
    } else {
      note.hidden = true;
      note.textContent = '';
    }
  }

  function originLabel(a){
    if (a.analysis_origin !== 'automatic') return `${esc(a.document_kind || 'proyecto')} · ${esc(a.expediente_numero)}`;
    return `${a.review_required ? 'BORRADOR AUTOMÁTICO' : 'ORIGEN AUTOMÁTICO'} · ${esc(a.document_kind || 'proyecto')} · ${esc(a.expediente_numero)}`;
  }

  function reviewChip(a){
    if (a.review_status === 'validado') return '<span class="auto-chip valid">VALIDADO</span>';
    if (a.analysis_origin === 'automatic' && a.review_required) return '<span class="auto-chip review">REVISIÓN REQUERIDA</span>';
    return `<span class="auto-chip">${esc(String(a.review_status || 'borrador').toUpperCase())}</span>`;
  }

  function confidence(a){
    if (a.analysis_origin !== 'automatic' || a.automation_confidence === null || a.automation_confidence === undefined) return '';
    const n = Number(a.automation_confidence);
    return Number.isFinite(n) ? `<span class="auto-confidence">Confianza ${Math.round(n*100)}%</span>` : '';
  }

  function renderAnalyses(){
    const target = document.getElementById('analisis-list');
    if (!target) return;
    target.innerHTML = current.map(a => `
      <article class="analysis-card">
        <header>
          <div><span class="eyebrow">${originLabel(a)}</span><h3>${esc(a.title)}</h3></div>
          <span class="internal-priority ${esc(a.internal_priority)}">${esc(a.internal_priority)}</span>
        </header>
        <p>${esc(a.executive_summary || 'Sin resumen ejecutivo cargado.')}</p>
        <div class="position"><strong>${a.analysis_origin === 'automatic' && a.review_required ? 'Posición técnica preliminar:' : 'Posición sugerida:'}</strong> ${esc(positionText(a.recommendation))}</div>
        <div class="auto-meta">${reviewChip(a)}${confidence(a)}<span class="auto-confidence">Actualizado ${displayDate(a.updated_at)}</span></div>
        <div class="card-actions"><button data-open-analysis="${esc(a.id)}">Ver ficha</button><button data-edit-analysis="${esc(a.id)}">Editar / revisar</button></div>
      </article>`).join('') || '<div class="empty">Todavía no hay análisis internos.</div>';
  }

  function renderLatest(){
    const target = document.getElementById('latest-analysis-list');
    if (!target) return;
    target.innerHTML = current.slice(0,6).map(a => `
      <article class="list-item">
        <div class="list-item-head"><strong>${esc(a.expediente_numero)}</strong><span class="internal-priority ${esc(a.internal_priority)}">${esc(a.internal_priority)}</span></div>
        <p>${esc(a.title)}</p>
        <div class="auto-meta">${a.analysis_origin === 'automatic' ? reviewChip(a) : ''}<span class="auto-confidence">${esc(positionText(a.recommendation))}</span></div>
      </article>`).join('') || '<div class="empty">Todavía no hay análisis internos cargados.</div>';
  }

  function updateKpi(){
    const cards = document.querySelectorAll('#kpi-grid .kpi');
    if (cards.length >= 4) {
      const strong = cards[3].querySelector('strong');
      const small = cards[3].querySelector('small');
      if (strong) strong.textContent = String(current.length);
      if (small) small.textContent = 'análisis vigentes en la capa privada';
    }
  }

  async function refresh(){
    if (!client) return;
    const { data: sessionData } = await client.auth.getSession();
    if (!sessionData?.session?.user) return;
    const { data, error } = await client.from('expediente_analyses')
      .select('*')
      .eq('is_current', true)
      .order('updated_at',{ascending:false})
      .limit(250);
    if (error) {
      console.error('No se pudieron cargar los análisis vigentes', error);
      return;
    }
    current = data || [];
    currentById = new Map(current.map(a => [a.id,a]));
    renderAnalyses();
    renderLatest();
    updateKpi();
  }

  async function saveExtras(){
    const id = document.getElementById('analysis-id')?.value || '';
    if (!id || !currentById.has(id)) return;
    const a = currentById.get(id);
    const { data: userData } = await client.auth.getUser();
    const user = userData?.user;
    if (!user) return;
    const status = document.getElementById('analysis-status')?.value || 'borrador';
    const payload = {
      affected_actors: document.getElementById('analysis-actors')?.value.trim() || '',
      arguments_for: document.getElementById('analysis-for')?.value.trim() || '',
      arguments_against: document.getElementById('analysis-against')?.value.trim() || '',
      evidence_gaps: (document.getElementById('analysis-gaps')?.value || '').split('\n').map(x => x.trim()).filter(Boolean),
      updated_by: user.id,
      review_required: a.analysis_origin === 'automatic' ? status !== 'validado' : false
    };
    const { error } = await client.from('expediente_analyses').update(payload).eq('id',id);
    if (error) console.error('No se pudieron guardar los campos ampliados', error);
    setTimeout(refresh,350);
  }

  function bindDialog(){
    const dialog = document.getElementById('analysis-dialog');
    if (!dialog) return;
    const observer = new MutationObserver(() => {
      if (dialog.hasAttribute('open')) queueMicrotask(setEditorExtras);
    });
    observer.observe(dialog,{attributes:true,attributeFilter:['open']});
    document.getElementById('analysis-form')?.addEventListener('submit',() => { void saveExtras(); },true);
  }

  function bindViewRefresh(){
    document.body.addEventListener('click', ev => {
      if (ev.target.closest('[data-view="analisis"]')) setTimeout(refresh,50);
    });
  }

  async function init(){
    injectStyles();
    injectEditorFields();
    client = window.CEPOES_LEGISLATIVA_CLIENT || null;
    if (!client) {
      console.warn('Cliente CEPOES no disponible para la capa automática');
      return;
    }
    bindDialog();
    bindViewRefresh();
    client.auth.onAuthStateChange((_event,session) => { if (session?.user) setTimeout(refresh,100); });
    await refresh();
  }

  if (document.readyState === 'complete') init();
  else window.addEventListener('load',init,{once:true});
})();
