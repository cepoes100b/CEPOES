// CEPOES · Área Legislativa
// La clave publishable es pública por diseño. La seguridad reside en Auth + RLS.
// Nunca colocar aquí service_role ni otros secretos administrativos.
window.CEPOES_LEGISLATIVA = {
  supabaseUrl: 'https://nriexnijkjamrmfivfmd.supabase.co',
  supabaseAnonKey: 'sb_publishable_i2WWiop8sCom0yVZZ7xC8g_NGJCiddq',
  publicDataBase: 'https://raw.githubusercontent.com/cepoes100b/CEPOES/main/'
};

// Puente retrocompatible hacia el universo consolidado.
// legislativa.js históricamente consume `legislatura_publica.json.expedientes`.
// Para no reescribir ese módulo grande, interceptamos sólo esa respuesta pública:
// - conservamos la capa de agenda en `expedientes_agenda`;
// - exponemos el universo consolidado como `expedientes` cuando está disponible;
// - si una corrida no lo generó, la UI sigue funcionando con el esquema anterior.
(() => {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await nativeFetch(...args);
    try {
      const input = args[0];
      const url = typeof input === 'string' ? input : (input?.url || '');
      if (!url.includes('legislatura_publica.json') || !response.ok) return response;

      const data = await response.clone().json();
      const consolidated = data?.universo_consolidado?.expedientes;
      if (!Array.isArray(consolidated) || !consolidated.length) return response;

      data.expedientes_agenda = Array.isArray(data.expedientes) ? data.expedientes : [];
      data.expedientes = consolidated;

      const headers = new Headers(response.headers);
      headers.set('content-type', 'application/json; charset=utf-8');
      return new Response(JSON.stringify(data), {
        status: response.status,
        statusText: response.statusText,
        headers
      });
    } catch (err) {
      console.warn('CEPOES: no se pudo activar universo consolidado; se usa capa de agenda.', err);
      return response;
    }
  };
})();

// Legislativa.js crea el cliente autenticado principal. Lo exponemos sólo dentro
// de esta página para que módulos privados complementarios reutilicen la misma sesión.
if (window.supabase?.createClient) {
  const originalCreateClient = window.supabase.createClient.bind(window.supabase);
  window.supabase.createClient = (...args) => {
    const client = originalCreateClient(...args);
    if (!window.CEPOES_LEGISLATIVA_CLIENT) window.CEPOES_LEGISLATIVA_CLIENT = client;
    return client;
  };
}

// La UI ampliada se carga después del módulo principal. No contiene secretos ni
// datos internos: consulta la misma API protegida por Auth + RLS.
window.addEventListener('load', () => {
  if (document.querySelector('script[data-legislativa-auto-ui]')) return;
  const script = document.createElement('script');
  script.src = '/assets/legislativa-auto-ui.js?v=2';
  script.defer = true;
  script.dataset.legislativaAutoUi = '1';
  document.head.appendChild(script);
}, { once:true });
