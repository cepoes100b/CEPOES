// CEPOES · Área Legislativa
// La clave publishable es pública por diseño. La seguridad reside en Auth + RLS.
// Nunca colocar aquí service_role ni otros secretos administrativos.
window.CEPOES_LEGISLATIVA = {
  supabaseUrl: 'https://nriexnijkjamrmfivfmd.supabase.co',
  supabaseAnonKey: 'sb_publishable_i2WWiop8sCom0yVZZ7xC8g_NGJCiddq',
  publicDataBase: 'https://raw.githubusercontent.com/cepoes100b/CEPOES/main/'
};

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
