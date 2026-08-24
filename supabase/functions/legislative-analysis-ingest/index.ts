import { createClient } from "npm:@supabase/supabase-js@2";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@6";

const EXPECTED_ISSUER = "https://token.actions.githubusercontent.com";
const EXPECTED_AUDIENCE = "cepoes-supabase-legislative-analysis";
const EXPECTED_REPOSITORY = "cepoes100b/CEPOES";
const EXPECTED_REF = "refs/heads/main";
const EXPECTED_WORKFLOW_REF = `${EXPECTED_REPOSITORY}/.github/workflows/analizar-legislatura.yml@refs/heads/main`;
const ALLOWED_EVENTS = new Set(["schedule", "workflow_dispatch", "push"]);
const JWKS = createRemoteJWKSet(new URL(`${EXPECTED_ISSUER}/.well-known/jwks`));

const json = (status: number, body: unknown) => new Response(JSON.stringify(body), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});

function cleanString(value: unknown, max = 30000): string {
  return String(value ?? "").replace(/\u0000/g, "").trim().slice(0, max);
}
function stringArray(value: unknown, maxItems = 30, maxLen = 800): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((x) => cleanString(x, maxLen)).filter(Boolean).slice(0, maxItems);
}

async function verifyGithubOidc(req: Request) {
  const header = req.headers.get("authorization") || "";
  const match = header.match(/^Bearer\s+(.+)$/i);
  if (!match) throw new Error("missing_bearer");
  const { payload } = await jwtVerify(match[1], JWKS, { issuer: EXPECTED_ISSUER, audience: EXPECTED_AUDIENCE });
  if (payload.repository !== EXPECTED_REPOSITORY) throw new Error("repository_not_allowed");
  if (payload.ref !== EXPECTED_REF) throw new Error("ref_not_allowed");
  if (payload.workflow_ref !== EXPECTED_WORKFLOW_REF) throw new Error("workflow_not_allowed");
  if (!ALLOWED_EVENTS.has(String(payload.event_name || ""))) throw new Error("event_not_allowed");
  return payload;
}

function adminClient() {
  const url = Deno.env.get("SUPABASE_URL");
  const legacy = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  let key = legacy || "";
  if (!key) {
    try {
      const keys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}");
      key = keys.default || Object.values(keys)[0] || "";
    } catch (_) { key = ""; }
  }
  if (!url || !key) throw new Error("missing_supabase_admin_credentials");
  return createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
}

const allowedKinds = new Set(["proyecto", "dictamen", "despacho", "sesion", "otro"]);
const allowedPriorities = new Set(["critica", "alta", "media", "baja"]);
const allowedRecommendations = new Set(["acompanar", "acompanar_con_modificaciones", "abstenerse", "rechazar", "sin_definir"]);

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return json(405, { error: "method_not_allowed" });
  let claims: Record<string, unknown>;
  try { claims = await verifyGithubOidc(req) as Record<string, unknown>; }
  catch (error) { console.error("OIDC rejected", error); return json(401, { error: "unauthorized" }); }

  let body: any;
  try { body = await req.json(); }
  catch (_) { return json(400, { error: "invalid_json" }); }

  const action = cleanString(body?.action, 30) || "ingest";
  const db = adminClient();

  if (action === "focus") {
    const { data, error } = await db.schema("private").from("analysis_focus_commissions")
      .select("commission_name,priority").eq("enabled", true)
      .order("priority", { ascending: false }).order("commission_name", { ascending: true });
    if (error) { console.error(error); return json(500, { error: "focus_lookup_failed" }); }
    return json(200, { commissions: data || [] });
  }

  const expediente = cleanString(body?.expediente_numero, 120);
  const kind = cleanString(body?.document_kind || "proyecto", 30);
  const sourceHash = cleanString(body?.source_hash, 64).toLowerCase();
  if (!expediente || !allowedKinds.has(kind) || !/^[a-f0-9]{64}$/.test(sourceHash)) return json(400, { error: "invalid_identity" });

  if (action === "check") {
    const { data, error } = await db.from("expediente_analyses")
      .select("id,version,review_status,updated_at")
      .eq("expediente_numero", expediente).eq("document_kind", kind)
      .eq("analysis_origin", "automatic").eq("automation_source_hash", sourceHash).maybeSingle();
    if (error) return json(500, { error: "check_failed" });
    return json(200, { exists: Boolean(data), analysis: data || null });
  }
  if (action !== "ingest") return json(400, { error: "unknown_action" });

  const input = body?.analysis || {};
  const priority = cleanString(input.internal_priority, 20);
  const recommendation = cleanString(input.recommendation, 50);
  const confidenceRaw = Number(input.confidence);
  const confidence = Number.isFinite(confidenceRaw) ? Math.min(1, Math.max(0, confidenceRaw)) : null;
  if (!allowedPriorities.has(priority) || !allowedRecommendations.has(recommendation)) return json(400, { error: "invalid_classification" });

  const { data: duplicate, error: duplicateError } = await db.from("expediente_analyses")
    .select("id,version").eq("expediente_numero", expediente).eq("document_kind", kind)
    .eq("analysis_origin", "automatic").eq("automation_source_hash", sourceHash).maybeSingle();
  if (duplicateError) return json(500, { error: "duplicate_check_failed" });
  if (duplicate) return json(200, { inserted: false, duplicate: true, id: duplicate.id, version: duplicate.version });

  const { data: latest, error: latestError } = await db.from("expediente_analyses")
    .select("version").eq("expediente_numero", expediente).eq("document_kind", kind)
    .order("version", { ascending: false }).limit(1);
  if (latestError) return json(500, { error: "version_lookup_failed" });
  const nextVersion = Math.max(0, Number(latest?.[0]?.version || 0)) + 1;

  const sourceEvidence = typeof body?.source_evidence === "object" && body.source_evidence ? body.source_evidence : {};
  sourceEvidence.github = {
    run_id: claims.run_id || null, run_number: claims.run_number || null, run_attempt: claims.run_attempt || null,
    workflow_sha: claims.workflow_sha || null, repository: claims.repository || null, ref: claims.ref || null,
  };

  const row = {
    expediente_numero: expediente, document_kind: kind,
    title: cleanString(body?.title || input.title || `Análisis ${expediente}`, 500),
    source_url: cleanString(body?.source_url, 2000) || null,
    executive_summary: cleanString(input.executive_summary), fiscal_impact: cleanString(input.fiscal_impact),
    territorial_impact: cleanString(input.territorial_impact), legal_impact: cleanString(input.legal_impact),
    risks: cleanString(input.risks), internal_priority: priority, recommendation,
    rationale: cleanString(input.rationale), proposed_amendments: cleanString(input.proposed_amendments),
    committee_questions: stringArray(input.committee_questions, 20, 1200),
    intervention_arguments: cleanString(input.intervention_arguments), affected_actors: cleanString(input.affected_actors),
    arguments_for: cleanString(input.arguments_for), arguments_against: cleanString(input.arguments_against),
    evidence_gaps: stringArray(input.evidence_gaps, 20, 1200), tags: stringArray(input.tags, 20, 120),
    review_status: "borrador", review_required: true, analysis_origin: "automatic", is_current: true,
    automation_source_hash: sourceHash, automation_model: cleanString(body?.model, 200), automation_confidence: confidence,
    automation_generated_at: new Date().toISOString(), source_evidence: sourceEvidence, version: nextVersion,
    created_by: null, updated_by: null,
  };

  const { data: inserted, error: insertError } = await db.from("expediente_analyses").insert(row).select("id,version").single();
  if (insertError) { console.error(insertError); return json(500, { error: "insert_failed" }); }

  const { error: supersedeError } = await db.from("expediente_analyses").update({ is_current: false })
    .eq("expediente_numero", expediente).eq("document_kind", kind).eq("analysis_origin", "automatic")
    .eq("is_current", true).neq("id", inserted.id);
  if (supersedeError) console.error("Could not supersede previous automatic drafts", supersedeError);
  return json(201, { inserted: true, id: inserted.id, version: inserted.version });
});
