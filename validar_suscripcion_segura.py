#!/usr/bin/env python3
"""Contrato estático del backend protegido de suscripción."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIGRATION = ROOT / "supabase/migrations/20260925143000_harden_newsletter_double_opt_in.sql"
FUNCTION = ROOT / "supabase/functions/newsletter-subscribe/index.ts"
LOGIC = ROOT / "supabase/functions/newsletter-subscribe/logic.js"
TESTS = ROOT / "tests/newsletter_logic.test.mjs"


def require(source: str, tokens: list[str], label: str) -> None:
    missing = [token for token in tokens if token not in source]
    assert not missing, f"{label}: faltan {missing}"


def main() -> None:
    migration = MIGRATION.read_text(encoding="utf-8")
    function = FUNCTION.read_text(encoding="utf-8")
    logic = LOGIC.read_text(encoding="utf-8")
    tests = TESTS.read_text(encoding="utf-8")

    require(
        migration,
        [
            "drop policy if exists public_can_subscribe",
            "revoke insert on table public.newsletter_subscriptions from anon",
            "'pending'::text",
            "confirmation_token_hash",
            "confirmation_expires_at",
            "newsletter_subscription_rate_limits",
            "newsletter_check_rate_limit",
            "security invoker",
            "revoke all on function public.newsletter_check_rate_limit",
            "grant execute on function public.newsletter_check_rate_limit",
        ],
        "Migración",
    )
    assert "security definer" not in migration.lower(), "No usar SECURITY DEFINER"

    require(
        function,
        [
            'npm:@supabase/supabase-js@2.95.0',
            'from "./logic.js"',
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            "TURNSTILE_ALLOWED_HOSTNAMES",
            "RATE_LIMIT_SALT",
            "newsletter_check_rate_limit",
            "confirmation_token_hash",
            "confirmation_expires_at",
            "RESEND_API_KEY",
            "idempotency-key",
            'status: "pending"',
            'status: "active"',
            "cache-control",
            "ALLOWED_ORIGINS",
        ],
        "Edge Function",
    )
    assert "SUPABASE_SERVICE_ROLE_KEY" in function
    secret_key_prefix = "sb_" + "secret_"
    scrubbed = function.lower().replace("supabase_service_role_key", "")
    assert secret_key_prefix not in function and "service_role" not in scrubbed, (
        "No incluir credenciales de servicio"
    )

    require(
        logic,
        [
            "isAllowedTurnstileOutcome",
            'outcome?.action === "newsletter_subscribe"',
            "isValidConfirmationToken",
            "isInsideResendCooldown",
        ],
        "Lógica comprobable",
    )
    require(
        tests,
        [
            "Turnstile exige éxito, acción y hostname esperados",
            "aplica quince minutos de espera",
        ],
        "Pruebas unitarias",
    )

    print("Suscripción segura: contrato backend preparado")


if __name__ == "__main__":
    main()
