/* Candidate GA4 adapter. Not injected into pages until activation is reviewed. */
(function () {
  'use strict';
  if (window.CEPOES_ANALYTICS) return;
  const allowed = new Set(['https://cepoes.org', 'https://www.cepoes.org']);
  const events = new Set(['report_download', 'map_interaction', 'neighborhood_view',
    'newsletter_confirmed', 'reading_progress']);
  const blocked = /^\/(?:privado|admin|newsletter)(?:\/|$)/;
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
    window.gtag('config', measurementId, {send_page_view: false,
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
    });
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
