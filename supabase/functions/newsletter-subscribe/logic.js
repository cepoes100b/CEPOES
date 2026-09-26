export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function normalizeEmail(value) {
  return String(value || "").trim().toLowerCase();
}

export function isValidEmail(email) {
  return email.length <= 254 && EMAIL_RE.test(email);
}

export function clientIpFromForwardedFor(value) {
  return String(value || "").split(",")[0].trim().slice(0, 80);
}

export function isAllowedTurnstileOutcome(outcome, allowedHostnames) {
  return outcome?.success === true &&
    outcome?.action === "newsletter_subscribe" &&
    allowedHostnames.has(String(outcome?.hostname || ""));
}

export function isValidConfirmationToken(token) {
  return /^[A-Za-z0-9_-]{40,60}$/.test(token);
}

export function isInsideResendCooldown(lastRequestedAt, now = Date.now()) {
  if (!lastRequestedAt) return false;
  const previous = Date.parse(lastRequestedAt);
  return Number.isFinite(previous) && now - previous < 15 * 60 * 1000;
}
