/* CEPOES GA4: consent-gated, public paths and explicit event parameters only. */
(function () {
  'use strict';
  if (window.CEPOES_ANALYTICS) return;
  const allowed = new Set(['https://cepoes.org', 'https://www.cepoes.org']);
  const events = new Set(['report_download', 'map_interaction', 'neighborhood_view',
    'newsletter_confirmed', 'reading_progress', 'filter_change', 'outbound_click']);
  const blocked = /\/(?:privado|private|admin|login|auth|newsletter|suscripcion|subscribe|unsubscribe|confirmar|baja)(?:\/|$)/i;
  let started = false;
  let withdrawn = false;
  let measurementId = '';
  function publicPath(value) {
    try {
      const url = new URL(value, location.origin);
      if (!allowed.has(url.origin) || blocked.test(url.pathname) || /@|%40/i.test(url.pathname)) return null;
      return url.pathname;
    } catch (_) { return null; }
  }
  function emit(name, params) {
    if (!started || !events.has(name)) return false;
    const path = publicPath(location.href);
    if (!path) return false;
    // Explicit allowlist: discard form contents, emails, searches and arbitrary payloads.
    const safe = {send_to: measurementId, page_path: path,
      page_location: location.origin + path, page_title: path};
    if (params && Number.isInteger(params.percent) && [25, 50, 75, 100].includes(params.percent)) safe.percent = params.percent;
    if (params && params.target_path) {
      const target = publicPath(params.target_path);
      if (target) safe.target_path = target;
    }
    if (params && /^[a-z0-9.-]{1,100}$/i.test(params.target_domain || '')) safe.target_domain = params.target_domain;
    window.gtag('event', name, safe);
    return true;
  }
  function start(config) {
    if (started || withdrawn || !config || config.analyticsConsent !== true ||
        !/^G-[A-Z0-9]+$/.test(config.measurementId || '') ||
        !allowed.has(location.origin) || !publicPath(location.href)) return false;
    measurementId = config.measurementId;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    let referrer = '';
    try { referrer = document.referrer ? new URL(document.referrer).origin : ''; } catch (_) {}
    window.gtag('consent', 'default', {analytics_storage: 'granted', ad_storage: 'denied',
      ad_user_data: 'denied', ad_personalization: 'denied'});
    window.gtag('js', new Date());
    const path = publicPath(location.href);
    const campaign = {};
    const query = new URL(location.href).searchParams;
    for (const [key, parameter] of [['utm_source', 'campaign_source'], ['utm_medium', 'campaign_medium'], ['utm_campaign', 'campaign_name']]) {
      const value = query.get(key);
      if (value && /^[a-z0-9_-]{1,80}$/i.test(value)) campaign[parameter] = value;
    }
    window.gtag('config', measurementId, {send_page_view: false, ...campaign,
      allow_google_signals: false, allow_ad_personalization_signals: false,
      page_location: location.origin + path, page_title: path, page_referrer: referrer});
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
    document.head.appendChild(script);
    started = true;
    window.gtag('event', 'page_view', {send_to: measurementId,
      page_location: location.origin + path, page_title: path, page_referrer: referrer});
    document.addEventListener('click', function (event) {
      const link = event.target.closest && event.target.closest('a[href]');
      if (!link) return;
      const target = publicPath(link.href);
      if (target && /\.pdf$/i.test(target)) emit('report_download', {target_path: target});
      if (target && /^\/territorio\/barrios\/[^/]+\//.test(target)) emit('neighborhood_view', {target_path: target});
      try {
        const url = new URL(link.href);
        if (url.protocol === 'https:' && !allowed.has(url.origin)) emit('outbound_click', {target_domain: url.hostname});
      } catch (_) {}
    });
    document.addEventListener('change', function (event) {
      if (event.target.tagName === 'SELECT' && !event.target.closest('form[id*="subscription"],form[id*="subscribe"]')) emit('filter_change');
    });
    document.addEventListener('click', function (event) {
      if (event.target.closest && event.target.closest('.leaflet-control-zoom,.leaflet-control-layers')) emit('map_interaction');
    });
    const reached = new Set();
    window.addEventListener('scroll', function () {
      if (!started || document.visibilityState !== 'visible') return;
      const height = document.documentElement.scrollHeight - window.innerHeight;
      if (height <= 0) return;
      const percent = Math.min(100, Math.round(window.scrollY / height * 100));
      for (const milestone of [25, 50, 75, 100]) {
        if (percent >= milestone && !reached.has(milestone)) {
          reached.add(milestone); emit('reading_progress', {percent: milestone});
        }
      }
    }, {passive: true});
    return true;
  }
  function stop() {
    if (!started) return;
    window['ga-disable-' + measurementId] = true;
    window.gtag('consent', 'update', {analytics_storage: 'denied'});
    started = false;
    withdrawn = true;
    // Reload after withdrawal; a subsequent start in the same page is intentionally disabled.
  }
  window.CEPOES_ANALYTICS = Object.freeze({start, event: emit, stop});
})();

(function () {
  'use strict';
  if (!document.querySelector) return;
  function init() {
    if (!document.querySelector('meta[name="cepoes-analytics"]') || document.getElementById('cepoes-analytics-choice')) return;
    const key = 'cepoes-analytics-consent-v1';
    const id = 'G-Z6E4BNZXMG';
    let previous = null;
    try {
      const saved = JSON.parse(localStorage.getItem(key));
      if (saved && ['granted', 'denied'].includes(saved.choice) && saved.expires > Date.now()) previous = saved.choice;
    } catch (_) {}
    const panel = document.createElement('section');
    panel.id = 'cepoes-analytics-choice';
    panel.setAttribute('role', 'region');
    panel.setAttribute('aria-label', 'Preferencias de medición');
    panel.innerHTML = '<strong>Ayudanos a mejorar CEPOES</strong><p>Con tu permiso usamos Google Analytics para conocer qué páginas y herramientas se utilizan. Podés navegar sin aceptar.</p><details><summary>Qué medimos y cómo cambiar tu elección</summary><p>Medimos visitas, tiempo de interacción, desplazamientos, clics a informes y uso de filtros. Google recibe información técnica del navegador y usa cookies de analítica. No enviamos el correo de suscripción, búsquedas, coordenadas ni enlaces de confirmación. La medición está separada de la suscripción y no habilita publicidad personalizada.</p><p>Guardamos tu elección durante 180 días. Podés retirarla desde «Privacidad y medición» al pie de cada página. Para consultas: <a href="mailto:contacto@cepoes.org">contacto@cepoes.org</a>. <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">Privacidad de Google</a>.</p></details><div class="cepoes-analytics-actions"><button type="button" data-analytics-choice="denied">No aceptar</button><button type="button" data-analytics-choice="granted">Aceptar medición</button></div>';
    panel.hidden = previous !== null;
    document.body.appendChild(panel);
    const manage = document.createElement('button');
    manage.type = 'button'; manage.className = 'cepoes-analytics-manage';
    manage.textContent = 'Privacidad y medición';
    (document.querySelector('footer') || document.body).appendChild(manage);
    manage.addEventListener('click', function () {
      panel.hidden = false;
      panel.querySelector('button').focus();
    });
    function clearCookies() {
      for (const cookie of document.cookie.split(';')) {
        const name = cookie.split('=')[0].trim();
        if (!/^_ga(?:_|$)/.test(name)) continue;
        for (const domain of ['', '; domain=' + location.hostname, '; domain=cepoes.org', '; domain=.cepoes.org']) {
          document.cookie = name + '=; Max-Age=0; path=/' + domain + '; SameSite=Lax';
        }
      }
    }
    panel.addEventListener('click', function (event) {
      const button = event.target.closest('[data-analytics-choice]');
      if (!button) return;
      const choice = button.dataset.analyticsChoice;
      try { localStorage.setItem(key, JSON.stringify({choice, expires: Date.now() + 180 * 86400000})); } catch (_) {}
      panel.hidden = true;
      if (choice === 'granted') window.CEPOES_ANALYTICS.start({measurementId: id, analyticsConsent: true});
      else {
        window.CEPOES_ANALYTICS.stop(); clearCookies();
        if (previous === 'granted') location.reload();
      }
      previous = choice;
      manage.focus();
    });
    if (previous === 'granted') window.CEPOES_ANALYTICS.start({measurementId: id, analyticsConsent: true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
