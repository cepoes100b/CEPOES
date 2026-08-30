(() => {
  const fmtMoney = n => {
    if (n == null || Number.isNaN(+n)) return '—';
    const v = +n;
    if (Math.abs(v) >= 1e12) return '$ ' + (v / 1e12).toLocaleString('es-AR', {maximumFractionDigits: 2}) + ' billones';
    if (Math.abs(v) >= 1e9) return '$ ' + (v / 1e9).toLocaleString('es-AR', {maximumFractionDigits: 1}) + ' mil M';
    return '$ ' + v.toLocaleString('es-AR', {maximumFractionDigits: 0});
  };
  const fmtPct = n => n == null ? '—' : (+n).toLocaleString('es-AR', {minimumFractionDigits: 1, maximumFractionDigits: 2}) + '%';
  const labels = {
    cumple_reportado: ['Cumple · autorreporte', 'ok'],
    cumple_funcional_reportado: ['Cumple funcional · autorreporte', 'ok'],
    parcial: ['Parcial', 'warn'],
    en_proceso: ['En proceso', 'warn'],
    no_acreditado: ['No acreditado', 'neutral'],
    no_informado: ['No informado', 'neutral'],
    incumple_explicito: ['Incumplimiento explícito', 'bad'],
    registrado_sin_contenido: ['Registrado sin contenido', 'warn'],
    no: ['Sin partida específica', 'neutral']
  };
  const pill = status => {
    const [label, cls] = labels[status] || [status, 'neutral'];
    return `<span class="pill ${cls}">${label}</span>`;
  };
  const $ = s => document.querySelector(s);

  Promise.all([
    fetch('/assets/data/descentralizacion-comunas.json', {cache: 'no-store'}).then(r => {
      if (!r.ok) throw new Error('No se pudo cargar presupuesto comunal');
      return r.json();
    }),
    fetch('/assets/data/descentralizacion-transparencia-2024.json', {cache: 'no-store'}).then(r => r.json()),
    fetch('/assets/data/descentralizacion-competencias.json', {cache: 'no-store'}).then(r => r.json())
  ]).then(([budget, trans, comp]) => {
    const h = budget.headline || {};
    $('#periodo').textContent = `Presupuesto: ${budget.year || 2026} · ${budget.quarter ? budget.quarter + '.º trimestre' : ''} · Transparencia: línea de base 2024`;
    $('#m-vigente').textContent = fmtMoney(h.presupuesto_administrado_comunas_vigente);
    $('#m-peso').textContent = fmtPct(h.participacion_presupuesto_gcba_pct);
    $('#m-ejecucion').textContent = fmtPct(h.ejecucion_comunas_pct);
    $('#m-modificacion').textContent = fmtPct(h.variacion_vigente_vs_sancionado_pct);
    $('#m-web').textContent = `${trans.headline.web_admin_exclusiva_incumple_o_no_acredita}/15`;
    $('#m-dominio').textContent = `${trans.headline.dominio_explicito_no_registrado} explícitos`;

    const budgetBy = new Map((budget.comunas || []).map(x => [x.comuna, x]));
    const tbody = $('#matrix-body');
    tbody.innerHTML = trans.comunas.map(c => {
      const b = budgetBy.get(c.comuna);
      const admin = b?.administrado || {};
      return `<tr>
        <th><button class="commune-btn" data-c="${c.comuna}">Comuna ${c.comuna}</button></th>
        <td>${fmtMoney(admin.vigente)}</td>
        <td>${fmtPct(admin.ejecucion_pct)}</td>
        <td>${pill(c.art4_difusion)}</td>
        <td>${pill(c.actas)}</td>
        <td>${pill(c.dominio_art8)}</td>
        <td>${pill(c.web_admin_exclusiva)}</td>
        <td>${pill(c.contenidos_minimos)}</td>
        <td>${pill(c.reclamos)}</td>
      </tr>`;
    }).join('');

    const compBox = $('#competencias');
    compBox.innerHTML = comp.competencias.map(x => `
      <article class="competence">
        <div class="eyebrow">${x.tipo.replaceAll('_',' ')}</div>
        <h3>${x.nombre}</h3>
        <p>${x.lectura}</p>
        <div class="legal">${x.base}</div>
        <span class="state ${x.estado_instrumental.includes('pendiente') ? 'warn' : 'ok'}">${x.estado_instrumental.replaceAll('_',' ')}</span>
      </article>
    `).join('');

    const details = $('#detail');
    const show = cnum => {
      const c = trans.comunas.find(x => x.comuna === +cnum);
      const b = budgetBy.get(+cnum);
      if (!c) return;
      details.hidden = false;
      details.innerHTML = `
        <div class="detail-head">
          <div><div class="eyebrow">Ficha comunal</div><h2>Comuna ${c.comuna}</h2></div>
          <button id="close-detail" class="close">Cerrar ×</button>
        </div>
        <div class="detail-grid">
          <div><span>Crédito vigente</span><strong>${fmtMoney(b?.administrado?.vigente)}</strong></div>
          <div><span>Ejecución</span><strong>${fmtPct(b?.administrado?.ejecucion_pct)}</strong></div>
          <div><span>Vigente por habitante</span><strong>${b?.administrado?.vigente_por_habitante ? '$ '+(+b.administrado.vigente_por_habitante).toLocaleString('es-AR',{maximumFractionDigits:0}) : '—'}</strong></div>
          <div><span>Gasto localizado</span><strong>${fmtMoney(b?.gasto_localizado?.vigente)}</strong></div>
        </div>
        <p class="evidence">${c.evidencia}</p>
        <div class="chips">
          ${pill(c.art4_difusion)} ${pill(c.actas)} ${pill(c.dominio_art8)}
          ${pill(c.web_admin_exclusiva)} ${pill(c.contenidos_minimos)} ${pill(c.reclamos)}
        </div>
      `;
      $('#close-detail').onclick = () => { details.hidden = true; };
      details.scrollIntoView({behavior:'smooth', block:'start'});
    };
    document.querySelectorAll('.commune-btn').forEach(btn => btn.onclick = () => show(btn.dataset.c));

    $('#loading').hidden = true;
    $('#content').hidden = false;
  }).catch(err => {
    $('#loading').innerHTML = `<strong>No se pudo cargar la matriz.</strong><br>${err.message}`;
  });
})();
