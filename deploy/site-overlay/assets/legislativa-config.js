// CEPOES · Área Legislativa
// La clave publishable es pública por diseño. La seguridad reside en Auth + RLS.
// Nunca colocar aquí service_role ni otros secretos administrativos.
window.CEPOES_LEGISLATIVA = {
  supabaseUrl: 'https://nriexnijkjamrmfivfmd.supabase.co',
  supabaseAnonKey: 'sb_publishable_i2WWiop8sCom0yVZZ7xC8g_NGJCiddq',
  publicDataBase: 'https://raw.githubusercontent.com/cepoes100b/CEPOES/main/'
};

// Bootstrap sin contraseña: permite solicitar un enlace de acceso por email.
// La autorización real se resuelve del lado servidor mediante profiles + RLS;
// un correo no incluido en la allowlist puede autenticarse, pero queda inactivo.
document.addEventListener('DOMContentLoaded', () => {
  const cfg = window.CEPOES_LEGISLATIVA || {};
  const form = document.getElementById('login-form');
  const emailInput = document.getElementById('login-email');
  const message = document.getElementById('login-message');
  if (!form || !emailInput || !message || !window.supabase?.createClient || !cfg.supabaseUrl || !cfg.supabaseAnonKey) return;

  const submit = form.querySelector('button[type="submit"]');
  if (!submit || document.getElementById('login-magic-link')) return;

  const magic = document.createElement('button');
  magic.id = 'login-magic-link';
  magic.type = 'button';
  magic.className = 'secondary-btn';
  magic.textContent = 'Recibir enlace de acceso';
  submit.insertAdjacentElement('afterend', magic);

  const client = window.supabase.createClient(cfg.supabaseUrl, cfg.supabaseAnonKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
      detectSessionInUrl: false,
      storageKey: 'cepoes-legislativa-bootstrap'
    }
  });

  magic.addEventListener('click', async () => {
    const email = emailInput.value.trim().toLowerCase();
    if (!email || !emailInput.checkValidity()) {
      emailInput.reportValidity();
      return;
    }

    magic.disabled = true;
    message.textContent = 'Enviando enlace seguro…';
    try {
      const redirectTo = new URL('/legislativa/', window.location.origin).href;
      const { error } = await client.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: redirectTo, shouldCreateUser: true }
      });
      if (error) throw error;
      message.textContent = 'Te enviamos un enlace de acceso. Abrilo desde este dispositivo para ingresar.';
    } catch (error) {
      console.error(error);
      message.textContent = 'No se pudo enviar el enlace de acceso. Reintentá o usá una contraseña si ya tenés una cuenta.';
    } finally {
      magic.disabled = false;
    }
  });
});
