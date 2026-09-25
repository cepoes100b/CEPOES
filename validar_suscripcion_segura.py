#!/usr/bin/env python3
"""Contrato estático del backend protegido de suscripción."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIGRATION = ROOT / "supabase/migrations/20260925143000_harden_newsletter_double_opt_in.sql"
FUNCTION = ROOT / "supabase/functions/newsletter-subscribe/index.ts"


def require(source: str, tokens: list[str], label: str) -> None:
    missing = [token for token in tokens if token not in source]
    assert not missing, f"{label}: faltan {missing}"


def main() -> None:
    migration = MIGRATION.read_text(encoding="utf-8")
    function = FUNCTION.read_text(encoding="utf-8")

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
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            'outcome?.action === "newsletter_subscribe"',
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
    assert "sb_secret_" not in function and "service_role" not in function.lower().replace(
        "supabase_service_role_key", ""
    ), "No incluir credenciales de servicio"

    print("Suscripción segura: contrato backend preparado")


if __name__ == "__main__":
    main()
