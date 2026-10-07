import assert from "node:assert/strict";
import test from "node:test";

import {
  clientIpFromForwardedFor,
  isAllowedTurnstileOutcome,
  isInsideResendCooldown,
  isValidConfirmationToken,
  isValidEmail,
  normalizeEmail,
} from "../supabase/functions/newsletter-subscribe/logic.js";

test("normaliza y valida correos sin aceptar formatos obvios inválidos", () => {
  const email = normalizeEmail("  Persona@Example.ORG ");
  assert.equal(email, "persona@example.org");
  assert.equal(isValidEmail(email), true);
  assert.equal(isValidEmail("sin-arroba.example.org"), false);
  assert.equal(isValidEmail(`${"a".repeat(250)}@x.ar`), false);
});

test("toma únicamente la primera IP reenviada y acota su longitud", () => {
  assert.equal(clientIpFromForwardedFor("203.0.113.7, 10.0.0.1"), "203.0.113.7");
  assert.equal(clientIpFromForwardedFor("x".repeat(120)).length, 80);
});

test("Turnstile exige éxito, acción y hostname esperados", () => {
  const hosts = new Set(["cepoes.org", "www.cepoes.org"]);
  const valid = { success: true, action: "newsletter_subscribe", hostname: "cepoes.org" };
  assert.equal(isAllowedTurnstileOutcome(valid, hosts), true);
  assert.equal(isAllowedTurnstileOutcome({ ...valid, action: "login" }, hosts), false);
  assert.equal(isAllowedTurnstileOutcome({ ...valid, hostname: "evil.example" }, hosts), false);
  assert.equal(isAllowedTurnstileOutcome({ ...valid, success: false }, hosts), false);
});

test("acepta sólo tokens de confirmación base64url con longitud esperada", () => {
  assert.equal(isValidConfirmationToken("A".repeat(43)), true);
  assert.equal(isValidConfirmationToken("A".repeat(39)), false);
  assert.equal(isValidConfirmationToken(`${"A".repeat(42)}+`), false);
});

test("aplica quince minutos de espera sin bloquear fechas inválidas", () => {
  const now = Date.parse("2026-09-25T16:00:00Z");
  assert.equal(isInsideResendCooldown("2026-09-25T15:46:00Z", now), true);
  assert.equal(isInsideResendCooldown("2026-09-25T15:45:00Z", now), false);
  assert.equal(isInsideResendCooldown("fecha-inválida", now), false);
});
