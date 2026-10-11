/* Sharing is initiated by the reader. No posting credentials or third-party SDK. */
(function () {
  'use strict';
  document.querySelectorAll('.cepoes-share').forEach(function (root) {
    const dialog = root.querySelector('dialog');
    const title = root.dataset.shareTitle;
    const original = new URL(root.dataset.shareUrl);
    function url(platform) {
      const result = new URL(original);
      // Only documented territorial state; never forward arbitrary query strings.
      const current = new URL(location.href);
      ['comuna', 'barrio', 'tema', 'indicador', 'capa', 'dimension', 'medida', 'tipo', 'categoria', 'nivel', 'sector'].forEach(function (key) {
        const value = current.searchParams.get(key);
        if (value && /^[a-z0-9áéíóúñ_. -]{1,80}$/i.test(value)) result.searchParams.set(key, value);
      });
      if (/^#[a-z0-9_-]{1,80}$/i.test(current.hash) && document.getElementById(current.hash.slice(1))) result.hash = current.hash;
      result.searchParams.set('utm_source', platform);
      result.searchParams.set('utm_medium', 'social');
      result.searchParams.set('utm_campaign', 'compartir');
      return result.href;
    }
    function status(message) {
      const host = dialog.open ? dialog : root;
      host.querySelector('.share-status').textContent = message;
    }
    function track(platform, method) {
      if (window.CEPOES_ANALYTICS) window.CEPOES_ANALYTICS.event('share', {platform: platform, method: method});
    }
    async function copy(text) {
      try {
        await navigator.clipboard.writeText(text);
        status('Copiado. Ya podés pegarlo donde quieras.'); return true;
      } catch (_) {
        status('No se pudo copiar automáticamente. Copiá el texto del campo.');
        let field = root.querySelector('.share-manual');
        if (!field) {
          field = document.createElement('textarea'); field.className = 'share-manual';
          field.setAttribute('aria-label', 'Texto para copiar');
        }
        (dialog.open ? dialog : root).appendChild(field);
        field.value = text; field.focus({preventScroll: true}); field.select(); return false;
      }
    }
    root.querySelector('[data-share-copy]').addEventListener('click', async function () {
      if (await copy(url('copy'))) track('copy', 'copy_link');
    });
    root.querySelectorAll('a[data-share-platform]').forEach(function (link) {
      link.addEventListener('click', function () {
        const platform = link.dataset.sharePlatform;
        if (platform === 'whatsapp') link.href = 'https://wa.me/?text=' + encodeURIComponent(title + '\n' + url(platform));
        if (platform === 'x') link.href = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url(platform));
        if (platform === 'facebook') link.href = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url(platform));
        track(platform, platform === 'instagram_download' ? 'download_image' : 'open_composer');
      });
    });
    const native = root.querySelector('[data-share-native]');
    if (navigator.share) {
      native.hidden = false;
      native.addEventListener('click', async function () {
        try {
          await navigator.share({title: title, text: title, url: url('native')});
          track('native', 'native_share');
        } catch (error) { if (error.name !== 'AbortError') status('Usá los botones de la red o copiá el enlace.'); }
      });
    }
    root.querySelector('[data-share-instagram]').addEventListener('click', function () { dialog.showModal(); });
    root.querySelector('[data-share-close]').addEventListener('click', function () { dialog.close(); });
    dialog.addEventListener('click', function (event) { if (event.target === dialog) {
      const box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
    }});
    root.querySelector('[data-share-caption]').addEventListener('click', async function () {
      if (await copy(title + '\n\nLeé el contenido completo:\n' + url('instagram'))) track('instagram', 'copy_caption');
    });
    // Preload only when opening the dialog, so the eventual share retains user activation.
    const fileButton = root.querySelector('[data-share-file]');
    let file = null;
    root.querySelector('[data-share-instagram]').addEventListener('click', async function () {
      if (!navigator.share || !navigator.canShare || file) return;
      try {
        const response = await fetch(root.dataset.shareImage + '-historia.png');
        if (!response.ok) return;
        file = new File([await response.blob()], 'cepoes-historia.png', {type: 'image/png'});
        fileButton.hidden = !navigator.canShare({files: [file]});
      } catch (_) { /* Download remains available. */ }
    });
    fileButton.addEventListener('click', async function () {
      if (!file) return;
      try { await navigator.share({files: [file]}); track('instagram', 'native_image'); }
      catch (error) { if (error.name !== 'AbortError') status('Guardá la placa y subila desde Instagram.'); }
    });
  });
}());
