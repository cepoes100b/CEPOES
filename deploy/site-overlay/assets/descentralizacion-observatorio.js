(() => {
  const GEO_COMUNAS = [
    '/assets/data/estructura-productiva/comunas.geojson',
    'https://cdn.buenosaires.gob.ar/datosabiertos/datasets/innovacion-transformacion-digital/comunas/comunas.geojson'
  ];
  const money = n => {
    if (!Number.isFinite(+n)) return '—';
    const v = +n;
    if (Math.abs(v) >= 1e12) return '$ ' + (v / 1e12).toLocaleString('es-AR', {maximumFractionDigits: 2}) + ' billones';
    if (Math.abs(v) >= 1e9) return '$ ' + (v / 1e9).toLocaleString('es-AR', {maximumFractionDigits: 1}) + ' mil M';
    return '$ ' + v.toLocaleString('es-AR', {maximumFractionDigits: 0});
  };
  const pct = n => Number.isFinite(+n) ? (+n).toLocaleString('es-AR', {minimumFractionDigits: 1, maximumFractionDigits: 2}) + '%' : '—';
  const number = n => Number.isFinite(+n) ? (+n).toLocaleString('es-AR', {maximumFractionDigits: 0}) : '—';
  const labels = {
    cumple_reportado: ['Cumple · autorreporte', 'ok'], cumple_funcional_reportado: ['Cumple funcional · autorreporte', 'ok'],
    parcial: ['Parcial', 'warn'], en_proceso: ['En proceso', 'warn'], no_acreditado: ['No acreditado', 'neutral'],
    no_informado: ['No informado', 'neutral'], incumple_explicito: ['Incumplimiento explícito', 'bad'],
    registrado_sin_contenido: ['Registrado sin contenido', 'warn'], no: ['Sin partida específica', 'neutral']
  };
  const pill = status => { const [label, cls] = labels[status] || [String(status || '—'), 'neutral']; return `<span class="pill ${cls}">${label}</span>`; };
  const $ = s => document.querySelector(s);
  const communeId = f => String(f?.properties?.comuna ?? f?.properties?.COMUNAS ?? f?.properties?.COMUNA ?? '');
  const modification = b => {
    const a = +b?.administrado?.sancionado, v = +b?.administrado?.vigente;
    return a ? (v / a - 1) * 100 : null;
  };

  $('#content-body').hidden = true;

  document.addEventListener('DOMContentLoaded', () => {
    const geoPromise = (async () => {
      if (!window.d3) throw new Error('biblioteca cartográfica no disponible');
      for (const url of GEO_COMUNAS) {
        try {
          const candidate = await d3.json(url);
          if (candidate?.features?.length >= 15) return candidate;
        } catch (_) {}
      }
      throw new Error('cartografía no disponible');
    })();

    return Promise.all([
    fetch('/assets/data/descentralizacion-comunas.json', {cache: 'no-store'}).then(r => { if (!r.ok) throw new Error('presupuesto comunal'); return r.json(); }),
    fetch('/assets/data/descentralizacion-transparencia-2024.json', {cache: 'no-store'}).then(r => r.json()),
    fetch('/assets/data/descentralizacion-competencias.json', {cache: 'no-store'}).then(r => r.json())
  ]).then(async ([budget, trans, comp]) => {
    const budgetBy = new Map((budget.comunas || []).map(x => [+x.comuna, x]));
    const transBy = new Map((trans.comunas || []).map(x => [+x.comuna, x]));
    const h = budget.headline || {};
    $('#periodo').textContent = `Presupuesto: ${budget.year || 2026}${budget.quarter ? ` · ${budget.quarter}.º trimestre` : ''} · Transparencia: línea de base 2024`;
    $('#m-vigente').textContent = money(h.presupuesto_administrado_comunas_vigente);
    $('#m-peso').textContent = pct(h.participacion_presupuesto_gcba_pct);
    $('#m-ejecucion').textContent = pct(h.ejecucion_comunas_pct);
    $('#m-web').textContent = `${trans.headline.web_admin_exclusiva_incumple_o_no_acredita}/15`;

    const metrics = {
      vigente: {label: 'Crédito vigente administrado', fmt: money, get: b => +b?.administrado?.vigente, colors: ['#d9f1fb', '#55bde5', '#0079a8']},
      ejecucion: {label: 'Ejecución acumulada', fmt: pct, get: b => +b?.administrado?.ejecucion_pct, colors: ['#e7f2f6', '#55bde5', '#006c92']},
      modificacion: {label: 'Modificación respecto del sancionado', fmt: pct, get: modification, diverging: true}
    };
    let current = metrics.vigente;
    let selected = 1;
    let geo = null;

    const renderDetail = cnum => {
      selected = +cnum;
      const b = budgetBy.get(selected), c = transBy.get(selected), admin = b?.administrado || {};
      $('#selected-title').textContent = `Comuna ${selected}`;
      $('#selected-main').textContent = money(admin.vigente);
      $('#selected-execution').textContent = pct(admin.ejecucion_pct);
      $('#selected-change').textContent = pct(modification(b));
      $('#selected-percapita').textContent = admin.vigente_por_habitante ? '$ ' + number(admin.vigente_por_habitante) : '—';
      $('#selected-localized').textContent = money(b?.gasto_localizado?.vigente);
      $('#selected-evidence').textContent = c?.evidencia || 'Sin evidencia descriptiva disponible.';
      $('#selected-status').innerHTML = c ? [c.art4_difusion, c.actas, c.dominio_art8, c.web_admin_exclusiva, c.contenidos_minimos, c.reclamos].map(pill).join(' ') : '';
      $('#selected-link').href = `/territorio/comuna-${selected}/`;
      document.querySelectorAll('[data-c]').forEach(x => x.classList.toggle('selected', +x.dataset.c === selected));
      drawMap();
    };

    const ranking = () => {
      const rows = [...budgetBy.entries()].map(([c, b]) => ({c, v: current.get(b)})).filter(x => Number.isFinite(x.v)).sort((a, b) => b.v - a.v);
      $('#ranking').innerHTML = rows.map((x, i) => `<button class="${x.c === selected ? 'selected' : ''}" data-c="${x.c}"><span>${i + 1}. Comuna ${x.c}</span><strong>${current.fmt(x.v)}</strong></button>`).join('');
    };
    const drawMap = () => {
      ranking();
      if (!geo || !window.d3) return;
      const valid = geo.features.filter(f => budgetBy.has(+communeId(f)));
      const vals = valid.map(f => current.get(budgetBy.get(+communeId(f)))).filter(Number.isFinite);
      const ext = d3.extent(vals);
      const scale = current.diverging
        ? d3.scaleLinear().domain([Math.min(ext[0], 0), 0, Math.max(ext[1], 0)]).range(['#b44a4a', '#edf1f4', '#0079a8'])
        : d3.scaleLinear().domain([ext[0], (ext[0] + ext[1]) / 2, ext[1]]).range(current.colors);
      const svg = d3.select('#commune-map'); svg.selectAll('*').remove();
      const fc = {type: 'FeatureCollection', features: valid};
      const projection = d3.geoMercator().fitExtent([[18, 18], [602, 502]], fc), path = d3.geoPath(projection);
      svg.selectAll('path').data(valid).join('path').attr('class', f => `commune-shape${+communeId(f) === selected ? ' selected' : ''}`)
        .attr('d', path).attr('fill', f => scale(current.get(budgetBy.get(+communeId(f)))))
        .attr('tabindex', 0).attr('aria-label', f => `Comuna ${communeId(f)}. ${current.label}: ${current.fmt(current.get(budgetBy.get(+communeId(f))))}`)
        .on('click keydown', (ev, f) => { if (ev.type === 'click' || ev.key === 'Enter' || ev.key === ' ') renderDetail(communeId(f)); });
      svg.selectAll('text').data(valid).join('text').attr('class', 'commune-label').attr('transform', f => `translate(${path.centroid(f)})`).attr('text-anchor', 'middle').attr('dy', '.35em').text(f => `C${communeId(f)}`);
      $('#map-legend').innerHTML = `<span>${current.fmt(ext[0])}</span><i></i><span>${current.fmt(ext[1])}</span>`;
    };
    $('#map-metrics').addEventListener('click', e => {
      const b = e.target.closest('[data-metric]'); if (!b) return;
      current = metrics[b.dataset.metric];
      document.querySelectorAll('[data-metric]').forEach(x => x.classList.toggle('active', x === b));
      $('#map-title').textContent = current.label;
      drawMap();
    });
    $('#ranking').addEventListener('click', e => { const b = e.target.closest('[data-c]'); if (b) renderDetail(b.dataset.c); });

    $('#matrix-body').innerHTML = (trans.comunas || []).map(c => {
      const b = budgetBy.get(+c.comuna), a = b?.administrado || {};
      return `<tr><th><button data-c="${c.comuna}">Comuna ${c.comuna}</button></th><td>${money(a.vigente)}</td><td>${pct(a.ejecucion_pct)}</td><td>${pill(c.art4_difusion)}</td><td>${pill(c.actas)}</td><td>${pill(c.dominio_art8)}</td><td>${pill(c.web_admin_exclusiva)}</td><td>${pill(c.contenidos_minimos)}</td><td>${pill(c.reclamos)}</td></tr>`;
    }).join('');
    $('#matrix-body').addEventListener('click', e => { const b = e.target.closest('[data-c]'); if (b) { renderDetail(b.dataset.c); $('#territorial').scrollIntoView({behavior: 'smooth'}); } });
    $('#competencias').innerHTML = (comp.competencias || []).map(x => `<article><div class="eyebrow">${x.tipo.replaceAll('_', ' ')}</div><h3>${x.nombre}</h3><p>${x.lectura}</p><small>${x.base}</small><span class="state ${x.estado_instrumental.includes('pendiente') ? 'warn' : 'ok'}">${x.estado_instrumental.replaceAll('_', ' ')}</span></article>`).join('');

    renderDetail(1);
    $('#loading').hidden = true;
    $('#content').hidden = false;
    $('#content-body').hidden = false;
    try {
      geo = await geoPromise;
      $('#map-status').textContent = 'Límites oficiales de Comunas · BA Data (GCBA)';
      drawMap();
    } catch (_) {
      $('#map-status').textContent = 'La cartografía no cargó. El selector y el ranking comunal siguen disponibles.';
    }
  }).catch(err => { $('#loading').innerHTML = `<strong>No se pudo cargar el observatorio.</strong><br>Falló la carga de ${err.message}.`; });
  });
})();
