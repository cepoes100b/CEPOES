// Copiar como /assets/legislativa-config.js únicamente al conectar el proyecto Supabase.
// La anon key de Supabase es una clave pública de cliente: la confidencialidad depende de RLS.
// NUNCA colocar aquí service_role, contraseñas, tokens administrativos ni secretos.
window.CEPOES_LEGISLATIVA = {
  supabaseUrl: 'https://TU-PROYECTO.supabase.co',
  supabaseAnonKey: 'TU_SUPABASE_ANON_KEY',
  publicDataBase: 'https://raw.githubusercontent.com/cepoes100b/CEPOES/main/'
};
