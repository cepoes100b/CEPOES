/*
 * CEPOES · puente de datos para /legislatura/
 *
 * La página pública histórica puede pedir legislatura_publica.json desde
 * distintas URLs. Antes de que su aplicación procese la respuesta, este
 * puente sustituye la colección legado `expedientes` por
 * `universo_consolidado.expedientes`.
 *
 * No modifica la fuente ni inventa estados. Sólo adapta el modelo consolidado
 * al contrato que ya entiende el frontend público.
 */
(() => {
  'use strict';

  if (window.__CEPOES_LEGISLATURA_PUBLIC_BRIDGE__) return;
  window.__CEPOES_LEGISLATURA_PUBLIC_BRIDGE__ = '2026-08-27-v1';

  const clean = value => String(value ?? '').trim();

  function authorsOf(row) {
    const direct = Array.isArray(row?.autores) ? row.autores : [];
    const official = Array.isArray(row?.ficha_oficial?.autores)
      ? row.ficha_oficial.autores
      : [];
    if (direct.length) return direct.filter(Boolean);
    if (official.length) return official.filter(Boolean);
    const fallback = row?.autor_reportado || row?.autor;
    return fallback ? [fallback] : [];
  }

  function adaptRow(input) {
    const row = {...input};
    const authors = authorsOf(row);

    row.autores = authors;

    // Compatibilidad con filtros históricos que buscan en `autor`.
    // Se conserva la lista completa para incluir coautorías.
    row.autor = authors.length
      ? authors.join(' · ')
      : clean(row.autor_reportado || row.autor);

    row.etapa =
      row.etapa_ciclo ||
      row.etapa ||
      row.estado_actual ||
      '';

    row.fecha_reunion =
      row.fecha_ultima_actividad ||
      row.fecha_reunion ||
      row.fecha_ingreso ||
      row.fecha_inicio ||
      '';

    if (!row.comision) {
      const commissions = Array.isArray(row.comisiones) && row.comisiones.length
        ? row.comisiones
        : (Array.isArray(row.giros) ? row.giros : []);
      row.comision = commissions.filter(Boolean).join(' · ');
    }

    return row;
  }

  function adaptLegislativeData(data) {
    if (!data || typeof data !== 'object') return data;

    const consolidated = data?.universo_consolidado?.expedientes;
    if (!Array.isArray(consolidated) || consolidated.length < 1000) {
      console.warn(
        'CEPOES Legislatura: universo consolidado ausente/incompleto; se conserva la respuesta original.'
      );
      return data;
    }

    const adapted = {
      ...data,
      expedientes_agenda: Array.isArray(data.expedientes)
        ? data.expedientes
        : [],
      expedientes: consolidated.map(adaptRow)
    };

    adapted.resumen = {
      ...(adapted.resumen || {}),
      expedientes_publicos_total: adapted.expedientes.length,
      fuente_expedientes_publicos: 'universo_consolidado'
    };

    const claudia = adapted.expedientes.filter(row => {
      const haystack = [
        row.autor,
        ...(Array.isArray(row.autores) ? row.autores : [])
      ].join(' ').toLocaleLowerCase('es');
      return haystack.includes('negri') && haystack.includes('claudia');
    });

    const target832 = adapted.expedientes.find(row => {
      const number = clean(row.numero).toUpperCase();
      return number.includes('832') && (number.includes('2026') || number.includes('26'));
    });

    console.info(
      `CEPOES Legislatura · puente activo · ${adapted.expedientes.length} expedientes · ` +
      `Claudia ${claudia.length} · 832 ${target832 ? 'presente' : 'ausente'}`
    );

    return adapted;
  }

  const nativeFetch = window.fetch.bind(window);

  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);

    try {
      const input = args[0];
      const url = typeof input === 'string'
        ? input
        : (input && input.url ? input.url : '');

      if (!String(url).includes('legislatura_publica.json') || !response.ok) {
        return response;
      }

      const data = await response.clone().json();
      const adapted = adaptLegislativeData(data);

      if (adapted === data) return response;

      const headers = new Headers(response.headers);
      headers.set('content-type', 'application/json; charset=utf-8');
      headers.set('x-cepoes-legislatura-bridge', '1');

      return new Response(JSON.stringify(adapted), {
        status: response.status,
        statusText: response.statusText,
        headers
      });
    } catch (error) {
      console.error('CEPOES Legislatura: error adaptando la respuesta pública.', error);
      return response;
    }
  };

  // Exportado sólo para validación/diagnóstico.
  window.__CEPOES_ADAPT_LEGISLATIVE_DATA__ = adaptLegislativeData;
})();
