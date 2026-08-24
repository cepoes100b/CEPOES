import { createClient } from "npm:@supabase/supabase-js@2";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@6";

const ISSUER = "https://token.actions.githubusercontent.com";
const AUDIENCE = "cepoes-supabase-legislative-analysis";
const REPOSITORY = "cepoes100b/CEPOES";
const REF = "refs/heads/main";
const WORKFLOW_REF = `${REPOSITORY}/.github/workflows/analizar-legislatura.yml@refs/heads/main`;
const EVENTS = new Set(["schedule", "workflow_dispatch", "push"]);
const JWKS = createRemoteJWKSet(new URL(`${ISSUER}/.well-known/jwks`));
const KINDS = new Set(["proyecto", "dictamen", "despacho", "sesion", "otro"]);
const PRIORITIES = new Set(["critica", "alta", "media", "baja"]);
const RECOMMENDATIONS = new Set(["acompanar", "acompanar_con_modificaciones", "abstenerse", "rechazar", "sin_definir"]);
const MODES = new Set(["full", "preliminary_insufficient_evidence"]);

const respond = (status:number, body:unknown) => new Response(JSON.stringify(body), {
  status, headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}
});
const text = (v:unknown, max=30000) => String(v ?? "").replace(/\u0000/g, "").trim().slice(0,max);
const list = (v:unknown, n=30, max=1200) => Array.isArray(v) ? v.map(x=>text(x,max)).filter(Boolean).slice(0,n) : [];

async function claims(req:Request) {
  const auth = req.headers.get("authorization") || "";
  const match = auth.match(/^Bearer\s+(.+)$/i);
  if (!match) throw new Error("missing_bearer");
  const {payload} = await jwtVerify(match[1], JWKS, {issuer:ISSUER,audience:AUDIENCE});
  if (payload.repository !== REPOSITORY) throw new Error("repository");
  if (payload.ref !== REF) throw new Error("ref");
  if (payload.workflow_ref !== WORKFLOW_REF) throw new Error("workflow");
  if (!EVENTS.has(String(payload.event_name || ""))) throw new Error("event");
  return payload;
}

function admin() {
  const url = Deno.env.get("SUPABASE_URL") || "";
  let key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!key) {
    try {
      const keys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}");
      key = keys.default || Object.values(keys)[0] || "";
    } catch (_) { key = ""; }
  }
  if (!url || !key) throw new Error("admin_credentials");
  return createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
}

Deno.serve(async (req:Request) => {
  if (req.method !== "POST") return respond(405,{error:"method_not_allowed"});
  let jwt:Record<string,unknown>;
  try { jwt = await claims(req) as Record<string,unknown>; }
  catch (e) { console.error("OIDC rejected",e); return respond(401,{error:"unauthorized"}); }

  let body:any;
  try { body = await req.json(); } catch (_) { return respond(400,{error:"invalid_json"}); }
  const action = text(body?.action,30) || "ingest";
  const db = admin();

  if (action === "focus") {
    const {data,error} = await db.from("analysis_focus_commissions")
      .select("commission_name,priority").eq("enabled",true)
      .order("priority",{ascending:false}).order("commission_name",{ascending:true});
    if (error) { console.error(error); return respond(500,{error:"focus_lookup_failed"}); }
    return respond(200,{commissions:data || []});
  }

  const expediente = text(body?.expediente_numero,120);
  const kind = text(body?.document_kind || "proyecto",30);
  const sourceHash = text(body?.source_hash,64).toLowerCase();
  if (!expediente || !KINDS.has(kind) || !/^[a-f0-9]{64}$/.test(sourceHash)) return respond(400,{error:"invalid_identity"});

  if (action === "check") {
    const {data,error} = await db.from("expediente_analyses")
      .select("id,version,review_status,updated_at")
      .eq("expediente_numero",expediente).eq("document_kind",kind)
      .eq("analysis_origin","automatic").eq("automation_source_hash",sourceHash).maybeSingle();
    if (error) return respond(500,{error:"check_failed"});
    return respond(200,{exists:Boolean(data),analysis:data || null});
  }
  if (action !== "ingest") return respond(400,{error:"unknown_action"});

  const a = body?.analysis || {};
  const evidence = typeof body?.source_evidence === "object" && body.source_evidence ? body.source_evidence : {};
  const priority = text(a.internal_priority,20);
  let recommendation = text(a.recommendation,50);
  let mode = text(a.analysis_mode || evidence.analysis_mode || "full",60);
  if (!MODES.has(mode)) mode = "full";
  if (!PRIORITIES.has(priority) || !RECOMMENDATIONS.has(recommendation)) return respond(400,{error:"invalid_classification"});
  const rawConfidence = Number(a.confidence);
  let confidence = Number.isFinite(rawConfidence) ? Math.max(0,Math.min(1,rawConfidence)) : null;
  const qualityFlags = list(a.quality_flags,20,120);

  if (mode === "preliminary_insufficient_evidence") {
    recommendation = "sin_definir";
    confidence = Math.min(confidence ?? 0, 0.20);
    if (!qualityFlags.includes("no_primary_document")) qualityFlags.push("no_primary_document");
  } else if ((confidence ?? 0) < 0.75) {
    recommendation = "sin_definir";
  }

  const {data:duplicate,error:dupError} = await db.from("expediente_analyses")
    .select("id,version").eq("expediente_numero",expediente).eq("document_kind",kind)
    .eq("analysis_origin","automatic").eq("automation_source_hash",sourceHash).maybeSingle();
  if (dupError) return respond(500,{error:"duplicate_check_failed"});
  if (duplicate) return respond(200,{inserted:false,duplicate:true,id:duplicate.id,version:duplicate.version});

  const {data:latest,error:versionError} = await db.from("expediente_analyses")
    .select("version").eq("expediente_numero",expediente).eq("document_kind",kind)
    .order("version",{ascending:false}).limit(1);
  if (versionError) return respond(500,{error:"version_lookup_failed"});
  const version = Number(latest?.[0]?.version || 0) + 1;

  evidence.github = {
    run_id:jwt.run_id || null, run_number:jwt.run_number || null, run_attempt:jwt.run_attempt || null,
    workflow_sha:jwt.workflow_sha || null, repository:jwt.repository || null, ref:jwt.ref || null
  };

  const preliminary = mode === "preliminary_insufficient_evidence";
  const row = {
    expediente_numero:expediente, document_kind:kind,
    title:text(body?.title || a.title || `Análisis ${expediente}`,500), source_url:text(body?.source_url,2000) || null,
    executive_summary:text(a.executive_summary), legal_impact:text(a.legal_impact), fiscal_impact:text(a.fiscal_impact),
    territorial_impact:text(a.territorial_impact), affected_actors:text(a.affected_actors), risks:text(a.risks),
    arguments_for:preliminary ? "" : text(a.arguments_for), arguments_against:preliminary ? "" : text(a.arguments_against), internal_priority:priority,
    recommendation, rationale:text(a.rationale), proposed_amendments:preliminary ? "" : text(a.proposed_amendments),
    committee_questions:list(a.committee_questions,20), intervention_arguments:preliminary ? "" : text(a.intervention_arguments),
    evidence_gaps:list(a.evidence_gaps,20), tags:list(a.tags,20,120),
    analysis_mode:mode, quality_flags:qualityFlags,
    review_status:"borrador", review_required:true, analysis_origin:"automatic", is_current:true,
    automation_source_hash:sourceHash, automation_model:text(body?.model,200), automation_confidence:confidence,
    automation_generated_at:new Date().toISOString(), source_evidence:evidence, version,
    created_by:null, updated_by:null
  };

  const {data:inserted,error:insertError} = await db.from("expediente_analyses").insert(row).select("id,version").single();
  if (insertError) { console.error(insertError); return respond(500,{error:"insert_failed"}); }

  const {error:supersedeError} = await db.from("expediente_analyses").update({is_current:false})
    .eq("expediente_numero",expediente).eq("document_kind",kind).eq("analysis_origin","automatic")
    .eq("is_current",true).neq("id",inserted.id);
  if (supersedeError) console.error("supersede_failed",supersedeError);
  return respond(201,{inserted:true,id:inserted.id,version:inserted.version,analysis_mode:mode});
});
