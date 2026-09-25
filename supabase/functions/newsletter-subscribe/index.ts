import { createClient } from "npm:@supabase/supabase-js@2.95.0";

const PUBLIC_SITE = "https://cepoes.org/";
const FUNCTION_PATH = "/functions/v1/newsletter-subscribe";
const ALLOWED_ORIGINS = new Set([
  "https://cepoes.org",
  "https://www.cepoes.org",
]);
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const encoder = new TextEncoder();

function json(status: number, body: unknown, origin?: string) {
  const headers: Record<string, string> = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
  };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    headers["access-control-allow-origin"] = origin;
    headers["access-control-allow-methods"] = "POST, OPTIONS";
    headers["access-control-allow-headers"] = "content-type, apikey";
    headers["vary"] = "Origin";
  }
  return new Response(JSON.stringify(body), { status, headers });
}

function redirect(kind: "confirmed" | "invalid") {
  const url = new URL(PUBLIC_SITE);
  url.searchParams.set("suscripcion", kind);
  url.hash = "novedades";
  return Response.redirect(url, 303);
}

function env(name: string) {
  const value = (Deno.env.get(name) || "").trim();
  if (!value) throw new Error(`missing_${name}`);
  return value;
}

function admin() {
  return createClient(
    env("SUPABASE_URL"),
    env("SUPABASE_SERVICE_ROLE_KEY"),
    { auth: { persistSession: false, autoRefreshToken: false } },
  );
}

function bytesToHex(bytes: Uint8Array) {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function randomToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  const base64 = btoa(String.fromCharCode(...bytes));
  return base64.replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}

async function sha256(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return bytesToHex(new Uint8Array(digest));
}

async function hmacSha256(value: string, secret: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(value));
  return bytesToHex(new Uint8Array(signature));
}

function clientIp(req: Request) {
  return (req.headers.get("x-forwarded-for") || "")
    .split(",")[0]
    .trim()
    .slice(0, 80);
}

async function verifyTurnstile(token: string, ip: string) {
  const response = await fetch(
    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        secret: env("TURNSTILE_SECRET_KEY"),
        response: token,
        remoteip: ip || undefined,
        idempotency_key: crypto.randomUUID(),
      }),
    },
  );
  if (!response.ok) return false;
  const outcome = await response.json();
  const allowedHostnames = new Set(
    (Deno.env.get("TURNSTILE_ALLOWED_HOSTNAMES") || "cepoes.org,www.cepoes.org")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  );
  return outcome?.success === true &&
    outcome?.action === "newsletter_subscribe" &&
    allowedHostnames.has(String(outcome?.hostname || ""));
}

async function sendConfirmation(email: string, rawToken: string) {
  const functionUrl = new URL(env("SUPABASE_URL") + FUNCTION_PATH);
  functionUrl.searchParams.set("token", rawToken);
  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "authorization": `Bearer ${env("RESEND_API_KEY")}`,
      "content-type": "application/json",
      "idempotency-key": await sha256("newsletter:" + email + ":" + rawToken),
    },
    body: JSON.stringify({
      from: env("NEWSLETTER_FROM"),
      to: [email],
      subject: "Confirmá tu suscripción a CEPOES",
      html:
        `<p>Recibimos una solicitud para sumar este correo a las novedades de CEPOES.</p>` +
        `<p><a href="${functionUrl.toString()}">Confirmar suscripción</a></p>` +
        `<p>El enlace vence en 24 horas. Si no hiciste la solicitud, podés ignorar este mensaje.</p>`,
    }),
  });
  if (!response.ok) {
    console.error("confirmation_email_failed", response.status);
    throw new Error("email_failed");
  }
}

async function confirm(req: Request) {
  const token = new URL(req.url).searchParams.get("token") || "";
  if (!/^[A-Za-z0-9_-]{40,60}$/.test(token)) return redirect("invalid");
  const tokenHash = await sha256(token);
  const db = admin();
  const { data, error } = await db
    .from("newsletter_subscriptions")
    .select("id")
    .eq("status", "pending")
    .eq("confirmation_token_hash", tokenHash)
    .gt("confirmation_expires_at", new Date().toISOString())
    .maybeSingle();
  if (error || !data) return redirect("invalid");
  const { error: updateError } = await db
    .from("newsletter_subscriptions")
    .update({
      status: "active",
      confirmed_at: new Date().toISOString(),
      confirmation_token_hash: null,
      confirmation_expires_at: null,
    })
    .eq("id", data.id)
    .eq("status", "pending");
  return redirect(updateError ? "invalid" : "confirmed");
}

async function subscribe(req: Request, origin: string) {
  if (!ALLOWED_ORIGINS.has(origin)) return json(403, { ok: false }, origin);
  const contentLength = Number(req.headers.get("content-length") || "0");
  if (contentLength > 4096) return json(413, { ok: false }, origin);

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json(400, { ok: false }, origin);
  }

  if (String(body.company || "").trim()) return json(202, { ok: true }, origin);
  const email = String(body.email || "").trim().toLowerCase();
  const consent = body.consent === true;
  const turnstileToken = String(body.turnstile_token || "");
  if (!consent || email.length > 254 || !EMAIL_RE.test(email)) {
    return json(400, { ok: false }, origin);
  }

  const ip = clientIp(req);
  const fingerprint = await hmacSha256(ip || "unknown", env("RATE_LIMIT_SALT"));
  const db = admin();
  const { data: allowed, error: limitError } = await db.rpc(
    "newsletter_check_rate_limit",
    {
      p_fingerprint_hash: fingerprint,
      p_window_start: new Date().toISOString(),
      p_limit: 5,
    },
  );
  if (limitError) throw limitError;
  if (!allowed) return json(429, { ok: false, retry_after: 3600 }, origin);
  if (!(await verifyTurnstile(turnstileToken, ip))) {
    return json(400, { ok: false }, origin);
  }

  const { data: existing, error: existingError } = await db
    .from("newsletter_subscriptions")
    .select("id,status,last_requested_at,request_count")
    .eq("email", email)
    .maybeSingle();
  if (existingError) throw existingError;
  if (existing?.status === "active") return json(202, { ok: true }, origin);

  if (existing?.last_requested_at) {
    const elapsed = Date.now() - Date.parse(existing.last_requested_at);
    if (elapsed < 15 * 60 * 1000) return json(202, { ok: true }, origin);
  }

  const rawToken = randomToken();
  const tokenHash = await sha256(rawToken);
  const now = new Date();
  const expires = new Date(now.getTime() + 24 * 60 * 60 * 1000);
  const record = {
    email,
    status: "pending",
    source: "home",
    privacy_version: "2026-09",
    consent_at: now.toISOString(),
    confirmation_token_hash: tokenHash,
    confirmation_expires_at: expires.toISOString(),
    confirmed_at: null,
    last_requested_at: now.toISOString(),
    request_count: Number(existing?.request_count || 0) + 1,
  };
  const query = existing
    ? db.from("newsletter_subscriptions").update(record).eq("id", existing.id)
    : db.from("newsletter_subscriptions").insert(record);
  const { error: writeError } = await query;
  if (writeError) throw writeError;

  await sendConfirmation(email, rawToken);
  return json(202, { ok: true }, origin);
}

Deno.serve(async (req: Request) => {
  try {
    if (req.method === "GET") return await confirm(req);
    const origin = req.headers.get("origin") || "";
    if (req.method === "OPTIONS") {
      if (!ALLOWED_ORIGINS.has(origin)) return json(403, { ok: false });
      return new Response(null, {
        status: 204,
        headers: {
          "access-control-allow-origin": origin,
          "access-control-allow-methods": "POST, OPTIONS",
          "access-control-allow-headers": "content-type, apikey",
          "access-control-max-age": "86400",
          "vary": "Origin",
        },
      });
    }
    if (req.method !== "POST") return json(405, { ok: false }, origin);
    return await subscribe(req, origin);
  } catch (error) {
    console.error("newsletter_subscribe_failed", error);
    return json(503, { ok: false });
  }
});
