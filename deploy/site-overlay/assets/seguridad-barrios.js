(async function () {
  'use strict';
  const status = document.getElementById('sb-status');
  const target = document.getElementById('sb-episodes');
  if (!status || !target) return;
  const text = (tag, value, className) => {
    const node = document.createElement(tag);
    node.textContent = value;
    if (className) node.className = className;
    return node;
  };
  const formatDate = value => new Date(value + 'T12:00:00Z').toLocaleDateString('es-AR', { day:'numeric', month:'long', year:'numeric', timeZone:'UTC' });
  const metric = (list, label, value) => {
    list.append(text('dt', label), text('dd', value === null ? 'Sin dato público verificado' : String(value), value === null ? 'sb-missing' : ''));
  };
  try {
    const response = await fetch('/assets/data/seguridad-barrios-operativos.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error('Datos no disponibles');
    const data = await response.json();
    if (data.schema !== 'cepoes-seguridad-barrios-v1' || !Array.isArray(data.operativos) || !data.operativos.length) throw new Error('Formato de datos inesperado');
    const unique = new Set();
    for (const op of data.operativos) {
      if (unique.has(op.id) || !/^\d{4}-\d{2}-\d{2}$/.test(op.fecha) || !Number.isInteger(op.detenciones_iniciales) || !Number.isInteger(op.barrios_reportados) || !op.fuente_oficial?.startsWith('https://')) throw new Error('Ficha incompleta');
      unique.add(op.id);
      const card = document.createElement('article'); card.className = 'sb-card';
      const time = text('time', formatDate(op.fecha));
      time.dateTime = op.fecha;
      card.append(time, text('h3', op.nombre));
      const dl = document.createElement('dl');
      metric(dl, 'Territorios anunciados', op.barrios_reportados);
      metric(dl, 'Efectivos y agentes anunciados', `${op.efectivos_y_agentes.calificador} ${op.efectivos_y_agentes.valor_minimo.toLocaleString('es-AR')}`);
      metric(dl, 'Detenciones iniciales', op.detenciones_iniciales);
      metric(dl, 'Situación procesal posterior', op.situacion_procesal_posterior);
      metric(dl, 'Vehículos secuestrados', op.vehiculos_secuestrados);
      if (Number.isInteger(op.locales_inspeccionados)) metric(dl, 'Locales inspeccionados', op.locales_inspeccionados);
      if (Number.isInteger(op.comercios_clausurados)) metric(dl, 'Locales clausurados', op.comercios_clausurados);
      metric(dl, 'Costo del despliegue', op.costo);
      card.append(dl, text('p', `Estado: ${op.estado}.`, 'sb-source'));
      if (op.registros_posteriores) {
        const follow = op.registros_posteriores;
        const section = document.createElement('section'); section.className = 'sb-followup';
        section.append(text('h4', 'Registros y cuestionamientos posteriores'));
        if (follow.cels) {
          section.append(text('p', `Detenciones: ${op.detenciones_iniciales} según el GCBA; ${follow.cels.detenciones_mpd_citadas} registradas por el Ministerio Público de la Defensa, según el CELS. Falta cotejar el registro original y los criterios y horarios de ambos recuentos.`));
          section.append(text('p', `${follow.cels.denuncias} Estas denuncias se atribuyen al CELS; CEPOES aún no las verificó de forma independiente ni dispone de una resolución judicial sobre ellas.`));
          const source = text('p', 'Fuente: ', 'sb-source');
          const link = text('a', 'publicación del CELS (25/9) ↗'); link.href = follow.cels.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
          source.append(link); section.append(source);
        }
        if (follow.reaccion_curas_villeros) {
          const reaction = text('p', `${follow.reaccion_curas_villeros.resumen} `);
          const link = text('a', 'Crónica del 26/9 ↗'); link.href = follow.reaccion_curas_villeros.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
          reaction.append(link); section.append(reaction);
        }
        card.append(section);
      }
      if (Array.isArray(op.control_legislativo) && op.control_legislativo.length) {
        const section = document.createElement('section'); section.className = 'sb-followup';
        section.append(text('h4', 'Control legislativo'));
        for (const control of op.control_legislativo) {
          const entry = document.createElement('div'); entry.className = 'sb-legislative-entry';
          entry.append(text('p', `${control.tipo} ${control.expediente} (presentado el ${formatDate(control.fecha_presentacion)}). ${control.objeto}`));
          entry.append(text('p', `Estado al ${formatDate(control.fecha_consulta)}: ${control.estado}. Último movimiento registrado: ${formatDate(control.ultimo_movimiento)}.`));
          if (control.nota) entry.append(text('p', control.nota));
          const source = text('p', 'Fuente: ', 'sb-source');
          const link = text('a', `expediente ${control.expediente} en la Legislatura ↗`); link.href = control.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
          source.append(link); entry.append(source);
          section.append(entry);
        }
        card.append(section);
      }
      const p = text('p', 'Fuente: ', 'sb-source'); const a = text('a', 'parte del Gobierno de la Ciudad ↗');
      a.href = op.fuente_oficial; a.target = '_blank'; a.rel = 'noopener noreferrer'; p.append(a); card.append(p);
      target.append(card);
    }
    const updated = document.getElementById('sb-updated');
    if (updated) updated.textContent = formatDate(data.fecha_revision);
    status.textContent = `${data.operativos.length} operativos registrados. Cifras iniciales del Gobierno de la Ciudad; las fuentes posteriores se identifican en cada ficha.`;
  } catch (error) {
    target.replaceChildren();
    status.textContent = 'Las fichas no están disponibles en este momento. Consultá los partes oficiales enlazados abajo o escribinos para solicitar los datos.';
    const links = [
      ['24 de septiembre de 2026', 'https://buenosaires.gob.ar/gcaba_historico/noticias/tormenta-negra-megaoperativo-simultaneo-en-las-villas-con-mas-de-1500'],
      ['14 de mayo de 2026', 'https://buenosaires.gob.ar/gcaba_historico/noticias/megaoperativo-en-las-villas-hubo-27-detenidos-con-secuestro-de-droga-y-5']
    ];
    for (const [label, url] of links) { const p = document.createElement('p'); const a = text('a', `Parte oficial: ${label}`); a.href = url; p.append(a); target.append(p); }
  }
})();
