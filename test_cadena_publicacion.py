#!/usr/bin/env python3
"""Contrato offline: identidad de eventos, rebase real, no-op y antirregresión."""
from __future__ import annotations

import copy
import ast
import json
import os
import shutil
import textwrap
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "deploy"))
import encadenar_publicacion as chain
import evidencia_publicacion as evidence
import registrar_actualizacion as producer
import detectar_cambio_panorama as panorama_change
import preparar_sitio_publico as public_site

REGISTRY = json.loads((ROOT / "deploy/producer-workflows.json").read_text())
PATTERNS = [item["path"] for item in json.loads((ROOT / "deploy/publication-inputs.json").read_text())["inputs"]]
REPOSITORY = REGISTRY["repository"]
REPOSITORY_ID = 12345
DEFINITION = next(item for item in REGISTRY["workflows"] if item["path"].endswith("actualizar.yml"))


NEW_PRODUCER_OUTPUTS = {
    "descentralizacion-comunas.yml": (
        ["deploy/site-overlay/assets/data/descentralizacion-comunas.json"], ["descentralizacion_comunas.json"]),
    "dinamica-productiva.yml": (
        ["deploy/site-overlay/assets/data/estructura-productiva/dinamica.json"], ["diagnostico_dinamica_productiva.txt"]),
    "migraciones.yml": (["deploy/site-overlay/assets/data/migraciones.json"], ["datos/migraciones/migraciones.json"]),
    "natalidad.yml": (["deploy/site-overlay/assets/data/natalidad.json"], ["natalidad.json"]),
    "personas-mayores.yml": (
        ["deploy/site-overlay/assets/data/personas-mayores.json", "deploy/site-overlay/observatorio/personas-mayores/index.html"], []),
    "salud-mental.yml": (["deploy/site-overlay/assets/data/salud-mental.json"], ["salud_mental.json"]),
    "salud-reproductiva.yml": (["deploy/site-overlay/assets/data/salud-reproductiva.json"], ["salud_reproductiva.json"]),
    "validar-legislatura.yml": (["legislatura_publica.json", "sesiones_publicas.json"],
                                ["estado_legislatura.json", "estructura_legislativa.json"]),
    "validar-presupuesto.yml": (["presupuesto.json", "diagnostico_presupuestario.json"],
        ["estado_presupuesto.json", "presupuesto_analitico.json", "presupuesto_historico.json", "presupuesto_territorial.json"]),
    "endeudamiento-mensual.yml": (["datos/endeudamiento/manifest.json", "datos/endeudamiento/2026-10.json"], []),
}


def run(path: Path, *args: str, success: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=path, capture_output=True, text=True)
    if success and result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    if not success and not result.returncode:
        raise AssertionError("El comando debía rechazar el push concurrente")
    return result.stdout.strip()


class ChainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cepoes-chain-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        run(self.repo, "init", "-b", "main")
        run(self.repo, "config", "user.email", "actions@github.com")
        run(self.repo, "config", "user.name", "cepoes-bot")
        self.base = self.commit("datos.json", '{"valid":1}')
        self.git = chain.Git(self.repo)
        self.values = {"workflow": DEFINITION["path"], "run_id": "56789", "attempt": "2", "input_sha": self.base}
        self.event = {"action": "completed", "repository": {"full_name": REPOSITORY, "id": REPOSITORY_ID},
                      "workflow_run": {"id": 56789, "run_attempt": 2, "workflow_id": DEFINITION["id"],
                                       "name": DEFINITION["name"], "path": DEFINITION["path"],
                                       "status": "completed", "conclusion": "success", "head_branch": "main",
                                       "head_sha": self.base, "head_repository": {"full_name": REPOSITORY, "id": REPOSITORY_ID},
                                       "event": "schedule"}}

    def commit(self, path: str, contents: str, *, values=None, body=None) -> str:
        file = self.repo / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(contents)
        run(self.repo, "add", path)
        message = "fixture"
        if values is not None:
            message += "\n\n" + producer.trailers(values)
        if body is not None:
            message += "\n\n" + body
        run(self.repo, "commit", "-m", message)
        return run(self.repo, "rev-parse", "HEAD")

    def product(self) -> str:
        return self.commit("datos.json", '{"valid":2}', values=self.values)

    def select(self, event=None, sha=None, event_name="workflow_run", github_ref="refs/heads/main") -> dict:
        return chain.select_candidate(self.git, event_name, event or self.event, self.base,
                                      REPOSITORY, REPOSITORY_ID, REGISTRY, PATTERNS,
                                      sha or run(self.repo, "rev-parse", "HEAD"), github_ref)

    def event_for(self, definition, source_event=None):
        event = copy.deepcopy(self.event)
        event["workflow_run"].update(workflow_id=definition["id"], name=definition["name"],
                                     path=definition["path"], event=source_event or definition["events"][0])
        return event

    def test_all_registered_producers_and_each_allowed_event(self):
        for definition in REGISTRY["workflows"]:
            with self.subTest(workflow=definition["path"]):
                run(self.repo, "reset", "--hard", self.base)
                paths = NEW_PRODUCER_OUTPUTS.get(Path(definition["path"]).name, (["datos.json"], []))[0]
                produced = self.commit(paths[0], "agregado público", values={**self.values, "workflow": definition["path"]})
                for source_event in definition["events"]:
                    selected = self.select(self.event_for(definition, source_event))
                    self.assertEqual(selected["producer_sha"], produced)
                    self.assertEqual(selected["should_deploy"], "true")

    def test_each_producer_rejects_bad_origin_branch_event_identity_and_failure(self):
        for definition in REGISTRY["workflows"]:
            run(self.repo, "reset", "--hard", self.base)
            self.commit("datos.json", "producto", values={**self.values, "workflow": definition["path"]})
            changes = [("head_repository", {"full_name": "fork/CEPOES", "id": 10}),
                       ("head_repository", {"full_name": REPOSITORY, "id": 10}),
                       ("head_branch", "topic"), ("head_branch", None),
                       ("event", "pull_request"), ("event", "pull_request_target"),
                       ("event", "repository_dispatch"), ("event", "workflow_run"),
                       ("status", "in_progress"), ("name", "nombre copiado"),
                       ("path", ".github/workflows/otra.yml"), ("workflow_id", 1)]
            changes += [("event", source_event) for source_event in ("push", "schedule", "workflow_dispatch")
                        if source_event not in definition["events"]]
            changes += [("conclusion", result) for result in ("failure", "cancelled", "timed_out", "skipped", None)]
            for key, value in changes:
                with self.subTest(workflow=definition["path"], field=key, value=value):
                    event = self.event_for(definition)
                    event["workflow_run"][key] = value
                    with self.assertRaises(chain.Rejected):
                        self.select(event)
            event = self.event_for(definition)
            event["repository"]["id"] = 10
            with self.assertRaises(chain.Rejected):
                self.select(event)

    def test_each_producer_noop_diagnostic_old_attempt_and_already_published(self):
        for definition in REGISTRY["workflows"]:
            with self.subTest(workflow=definition["path"]):
                run(self.repo, "reset", "--hard", self.base)
                event = self.event_for(definition)
                values = {**self.values, "workflow": definition["path"]}
                self.assertEqual(self.select(event)["reason"], "sin-commit-producido")
                self.commit("estado_descargas.json", "diagnóstico", values=values)
                self.assertEqual(self.select(event)["reason"], "solo-diagnostico")
                run(self.repo, "reset", "--hard", self.base)
                self.commit("datos.json", "viejo", values={**values, "attempt": "1"})
                self.assertEqual(self.select(event)["should_deploy"], "false")
                run(self.repo, "reset", "--hard", self.base)
                produced = self.commit("datos.json", "validado", values=values)
                selected = chain.check_previous(self.git, self.select(event), {"commit_sha": produced}, PATTERNS)
                self.assertEqual(selected["should_deploy"], "false")

    def test_budget_diagnostic_alone_triggers_both_validated_budget_producers(self):
        for filename in ("presupuesto.yml", "validar-presupuesto.yml"):
            definition = next(item for item in REGISTRY["workflows"] if Path(item["path"]).name == filename)
            source = (ROOT / definition["path"]).read_text()
            self.assertIn("      - name: Verificar diagnóstico presupuestario\n        run: python verificar_diagnostico_presupuestario.py", source)
            self.assertLess(source.index("python verificar_diagnostico_presupuestario.py"), source.index("git commit"))
            for source_event in definition["events"]:
                with self.subTest(workflow=filename, event=source_event):
                    run(self.repo, "reset", "--hard", self.base)
                    produced = self.commit("diagnostico_presupuestario.json", '{"fixture":"agregado"}',
                                           values={**self.values, "workflow": definition["path"]})
                    selected = self.select(self.event_for(definition, source_event))
                    self.assertEqual(selected["should_deploy"], "true")
                    self.assertEqual(selected["producer_sha"], produced)

    def test_each_unlisted_secondary_output_is_explicit_noop(self):
        for filename, (_, omitted) in NEW_PRODUCER_OUTPUTS.items():
            definition = next(item for item in REGISTRY["workflows"] if Path(item["path"]).name == filename)
            for output in omitted:
                with self.subTest(workflow=filename, output=output):
                    run(self.repo, "reset", "--hard", self.base)
                    self.commit(output, "salida secundaria", values={**self.values, "workflow": definition["path"]})
                    self.assertEqual(self.select(self.event_for(definition))["reason"], "solo-diagnostico")

    def test_valid_product_uses_output_not_input(self):
        produced = self.product()
        selection = self.select()
        self.assertEqual(selection["producer_sha"], produced)
        self.assertEqual(selection["deploy_sha"], produced)
        self.assertNotEqual(selection["deploy_sha"], self.base)

    def test_real_rebase_concurrency_and_newer_main(self):
        bare = self.root / "remote.git"
        run(self.root, "init", "--bare", str(bare))
        run(self.repo, "remote", "add", "origin", str(bare))
        run(self.repo, "push", "-u", "origin", "main")
        first_product = self.product()
        # Otro commit llega a main mientras el actualizador genera su producto.
        run(self.repo, "checkout", "-b", "concurrent", self.base)
        self.commit("otro.json", "concurrente")
        run(self.repo, "push", "origin", "HEAD:main")
        run(self.repo, "checkout", "main")
        run(self.repo, "push", success=False)
        run(self.repo, "pull", "--rebase", "--autostash", "origin", "main")
        produced = run(self.repo, "rev-parse", "HEAD")
        self.assertNotEqual(first_product, produced)
        run(self.repo, "push")
        latest = self.commit("README.md", "otro cambio posterior")
        run(self.repo, "push")
        selection = self.select()
        self.assertEqual(selection["producer_sha"], produced)
        self.assertEqual(selection["deploy_sha"], latest)
        self.assertTrue(self.git.ancestor(produced, latest))
        self.assertFalse(self.git.ancestor(first_product, latest))

    def test_preflight_never_observes_uncommitted_production_under_upload(self):
        produced = self.product()
        run(self.repo, "update-ref", "refs/remotes/origin/main", produced)
        deploy = self.repo / "deploy"
        deploy.mkdir()
        (deploy / "producer-workflows.json").write_text(json.dumps(REGISTRY))
        (deploy / "publication-inputs.json").write_text(json.dumps({"inputs": [{"path": p} for p in PATTERNS]}))
        event_path = self.root / "event.json"
        event_path.write_text(json.dumps(self.event))
        output = self.root / "output"
        argv = ["chain", "--preflight-only", "--repository", REPOSITORY, "--repository-id", str(REPOSITORY_ID),
                "--event-file", str(event_path), "--event-name", "workflow_run", "--github-sha", self.base,
                "--output", str(output)]
        with patch.object(chain, "ROOT", self.repo), patch.object(sys, "argv", argv), \
                patch.object(chain, "fetch_marker", side_effect=AssertionError("No leer producción fuera del mutex")) as fetch:
            chain.main()
        fetch.assert_not_called()
        self.assertIn("should_deploy=true", output.read_text())

    def test_no_commit_is_noop(self):
        self.assertEqual(self.select()["reason"], "sin-commit-producido")
        self.assertEqual(self.select()["should_deploy"], "false")

    def test_diagnostic_only_is_noop(self):
        self.commit("estado_descargas.json", "diagnóstico", values=self.values)
        self.assertEqual(self.select()["reason"], "solo-diagnostico")
        self.assertEqual(self.select()["should_deploy"], "false")

    def test_old_attempt_does_not_count_as_product(self):
        self.commit("datos.json", "viejo", values={**self.values, "attempt": "1"})
        self.assertEqual(self.select()["should_deploy"], "false")

    def test_failed_cancelled_skipped_and_in_progress_rejected(self):
        self.product()
        for conclusion in ("failure", "cancelled", "timed_out", "skipped", None):
            with self.subTest(conclusion=conclusion):
                event = copy.deepcopy(self.event)
                event["workflow_run"]["conclusion"] = conclusion
                with self.assertRaises(chain.Rejected):
                    self.select(event)
        event = copy.deepcopy(self.event)
        event["workflow_run"]["status"] = "in_progress"
        with self.assertRaises(chain.Rejected):
            self.select(event)

    def test_pr_fork_foreign_branch_and_source_event_rejected(self):
        self.product()
        changes = [("event", "pull_request"), ("event", "pull_request_target"),
                   ("event", "repository_dispatch"), ("event", "workflow_run"),
                   ("head_branch", "topic"), ("head_repository", {"full_name": "fork/CEPOES", "id": 10}),
                   ("head_repository", {"full_name": REPOSITORY, "id": 10})]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                event = copy.deepcopy(self.event)
                event["workflow_run"][key] = value
                with self.assertRaises(chain.Rejected):
                    self.select(event)

    def test_repository_workflow_name_path_id_and_action_rejected(self):
        self.product()
        for key, value in (("workflow_id", 1), ("workflow_id", str(DEFINITION["id"])),
                           ("name", "nombre copiado"), ("path", ".github/workflows/evil.yml"),
                           ("run_attempt", 0), ("id", True)):
            with self.subTest(key=key):
                event = copy.deepcopy(self.event)
                event["workflow_run"][key] = value
                with self.assertRaises(chain.Rejected):
                    self.select(event)
        for key, value in (("action", "requested"), ("repository", {"full_name": "otro/CEPOES", "id": REPOSITORY_ID})):
            event = copy.deepcopy(self.event)
            event[key] = value
            with self.assertRaises(chain.Rejected):
                self.select(event)

    def test_unknown_or_nonancestral_input_rejected(self):
        self.product()
        event = copy.deepcopy(self.event)
        event["workflow_run"]["head_sha"] = "0" * 40
        with self.assertRaises(chain.Rejected):
            self.select(event)
        run(self.repo, "checkout", "-b", "other", self.base)
        foreign = self.commit("datos.json", "rama ajena")
        run(self.repo, "checkout", "main")
        event["workflow_run"]["head_sha"] = foreign
        with self.assertRaises(chain.Rejected):
            self.select(event)

    def test_ambiguous_product_rejected(self):
        self.product()
        self.commit("datos.json", "duplicado", values=self.values)
        with self.assertRaisesRegex(chain.Rejected, "Más de un"):
            self.select()

    def test_inconsistent_or_duplicate_trailers_rejected(self):
        self.commit("datos.json", "invalid", values={**self.values, "workflow": ".github/workflows/otra.yml"})
        with self.assertRaisesRegex(chain.Rejected, "Trailers"):
            self.select()
        run(self.repo, "reset", "--hard", self.base)
        self.commit("datos.json", "duplicado", body=producer.trailers(self.values) + "\nCEPOES-Producer-Run: 56789")
        with self.assertRaisesRegex(chain.Rejected, "Trailers"):
            self.select()

    def test_body_text_is_not_a_trailer(self):
        self.commit("datos.json", "body", body=producer.trailers(self.values) + "\n\ntexto posterior")
        self.assertEqual(self.select()["should_deploy"], "false")

    def test_direct_push_uses_current_main(self):
        produced = self.product()
        newest = self.commit("README.md", "latest")
        event = {"repository": self.event["repository"], "ref": "refs/heads/main", "after": produced}
        self.assertEqual(self.select(event, event_name="push")["deploy_sha"], newest)
        event["ref"] = "refs/heads/other"
        with self.assertRaises(chain.Rejected):
            self.select(event, event_name="push")

    def test_manual_only_main_and_unknown_event_rejected(self):
        self.product()
        event = {"repository": self.event["repository"], "ref": "main"}
        self.assertEqual(self.select(event, event_name="workflow_dispatch")["should_deploy"], "true")
        with self.assertRaises(chain.Rejected):
            self.select(event, event_name="workflow_dispatch", github_ref="refs/heads/other")
        with self.assertRaises(chain.Rejected):
            self.select(event, event_name="pull_request")

    def test_initial_marker_absence_allowed(self):
        self.product()
        checked = chain.check_previous(self.git, self.select(), None, PATTERNS)
        self.assertEqual(checked["should_deploy"], "true")
        self.assertEqual(checked["previous_sha"], "absent")

    def test_duplicate_sha_and_already_published_product_noop(self):
        produced = self.product()
        selection = self.select()
        result = chain.check_previous(self.git, selection, {"commit_sha": produced}, PATTERNS)
        self.assertEqual(result["reason"], "sha-ya-publicado")
        newest = self.commit("README.md", "latest")
        self.assertEqual(self.select()["deploy_sha"], newest)
        result = chain.check_previous(self.git, self.select(), {"commit_sha": produced}, PATTERNS)
        self.assertEqual(result["reason"], "evento-ya-publicado")
        self.assertEqual(result["should_deploy"], "false")

    def test_late_valid_event_recovers_newer_publication_from_replaced_queue(self):
        produced = self.product()
        first_selection = self.select()
        newest = self.commit("datos.json", "nuevo producto concurrente", values={**self.values, "run_id": "77777"})
        # El primer build termina mientras B esperaba. A llega tarde y reemplaza B:
        # bajo mutex se refija main y se conserva el delta publicable de B.
        result = chain.check_previous(self.git, self.select(), {"commit_sha": produced}, PATTERNS)
        self.assertEqual(result["deploy_sha"], newest)
        self.assertEqual(result["should_deploy"], "true")
        self.assertEqual(result["reason"], "main-con-entradas-publicables-nuevas")
        # Un evento sin producto ni siquiera entra en la cola de publicación.
        noop = copy.deepcopy(self.event)
        noop["workflow_run"]["id"] = 99999
        self.assertEqual(self.select(noop)["should_deploy"], "false")
        self.assertNotEqual(first_selection["deploy_sha"], result["deploy_sha"])

    def test_previous_ancestor_allowed_newer_or_divergent_rejected(self):
        produced = self.product()
        selection = self.select()
        self.assertEqual(chain.check_previous(self.git, selection, {"commit_sha": self.base}, PATTERNS)["should_deploy"], "true")
        future = self.commit("datos.json", "newer")
        with self.assertRaisesRegex(chain.Rejected, "regresión"):
            chain.check_previous(self.git, selection, {"commit_sha": future}, PATTERNS)
        run(self.repo, "checkout", "-b", "other", self.base)
        divergent = self.commit("datos.json", "divergent")
        with self.assertRaises(chain.Rejected):
            chain.check_previous(self.git, selection, {"commit_sha": divergent}, PATTERNS)

    def test_backup_guard_detects_race_and_duplicate(self):
        produced = self.product()
        site = self.root / "site"
        site.mkdir()
        for relative in evidence.PUBLIC_FILES:
            path = site / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("public")
        chain.guard_backup(self.git, site, REPOSITORY, produced, "absent")
        evidence.create_marker(site, REPOSITORY, self.base, "1", 1)
        chain.guard_backup(self.git, site, REPOSITORY, produced, self.base)
        with self.assertRaisesRegex(chain.Rejected, "cambió"):
            chain.guard_backup(self.git, site, REPOSITORY, produced, "absent")
        evidence.create_marker(site, REPOSITORY, produced, "2", 1)
        with self.assertRaisesRegex(chain.Rejected, "duplicada"):
            chain.guard_backup(self.git, site, REPOSITORY, produced, produced)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cepoes-marker-")
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name)
        self.contents = {relative: ("public " + relative).encode() for relative in evidence.PUBLIC_FILES}
        for relative, content in self.contents.items():
            path = self.site / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.marker = evidence.create_marker(self.site, REPOSITORY, "a" * 40, "123", 1)
        self.observatory = b"observatory current candidate"
        observatory = self.site / "observatorio/index.html"
        observatory.parent.mkdir()
        observatory.write_bytes(self.observatory)

    def read(self, path, nonce, **kwargs):
        if path == "/" + evidence.MARKER_PATH:
            return json.dumps(self.marker).encode()
        if path in ("/observatorio/", "/observatorio/index.html"):
            return self.observatory
        relative = next(key for key, value in evidence.PUBLIC_FILES.items() if value == path)
        return self.contents[relative]

    def test_exact_bytes_of_all_three_routes(self):
        with patch.object(evidence, "read_public", side_effect=self.read):
            evidence.verify_online(self.marker, "test")
        self.assertEqual(set(self.marker["files"]), set(evidence.PUBLIC_FILES))

    def test_canonical_checks_precede_all_cache_busting(self):
        with patch.object(evidence, "read_public", side_effect=self.read) as read:
            evidence.verify_online(self.marker, "test")
        calls = [(call.args[0], call.args[1]) for call in read.call_args_list]
        paths = ["/" + evidence.MARKER_PATH, *evidence.PUBLIC_FILES.values()]
        self.assertEqual(calls, [(path, None) for path in paths] + [(path, "test") for path in paths])
        workflow = (ROOT / ".github/workflows/desplegar-hostinger.yml").read_text()
        self.assertLess(workflow.index("run: python deploy/evidencia_publicacion.py smoke --site _site"),
                        workflow.index('SMOKE_Q="smoke='))

    def test_stale_canonical_fails_even_when_nonce_would_be_fresh(self):
        for stale_path in ["/" + evidence.MARKER_PATH, *evidence.PUBLIC_FILES.values()]:
            def response(path, nonce, **kwargs):
                if nonce is None and path == stale_path:
                    if path == "/" + evidence.MARKER_PATH:
                        return json.dumps({**self.marker, "commit_sha": "b" * 40}).encode()
                    return b"old canonical bytes"
                return self.read(path, nonce, **kwargs)
            with self.subTest(path=stale_path), patch.object(evidence, "read_public", side_effect=response) as read:
                with self.assertRaisesRegex(ValueError, "canónic"):
                    evidence.verify_online(self.marker, "test")
                self.assertTrue(all(call.args[1] is None for call in read.call_args_list))

    def test_candidate_observatory_checks_both_aliases_before_any_nonce(self):
        with patch.object(evidence, "read_public", side_effect=self.read) as read:
            evidence.verify_online(self.marker, "test", candidate_site=self.site)
        paths = ["/" + evidence.MARKER_PATH, *evidence.PUBLIC_FILES.values(),
                 "/observatorio/", "/observatorio/index.html"]
        self.assertEqual([(c.args[0], c.args[1]) for c in read.call_args_list],
                         [(p, None) for p in paths] + [(p, "test") for p in paths])
        # La verificación nueva no invalida los marcadores/restauraciones previos.
        self.assertEqual(self.marker["schema_version"], 1)
        self.assertEqual(set(self.marker["files"]), set(evidence.PUBLIC_FILES))
        self.assertNotIn("observatorio/index.html", self.marker["files"])
        self.assertEqual(evidence.validate_marker(self.marker, REPOSITORY), self.marker)

    def test_stale_observatory_alias_fails_even_when_nonce_is_current(self):
        for stale_path in ("/observatorio/", "/observatorio/index.html"):
            def response(path, nonce, **kwargs):
                if path == stale_path and nonce is None:
                    return b"stale six cards"
                return self.read(path, nonce, **kwargs)
            with self.subTest(path=stale_path), patch.object(evidence, "read_public", side_effect=response) as read:
                with self.assertRaisesRegex(ValueError, "bytes canónicos.*observatorio"):
                    evidence.verify_online(self.marker, "test", candidate_site=self.site)
                self.assertTrue(all(c.args[1] is None for c in read.call_args_list))

    def test_observatory_nonce_is_also_checked_against_candidate(self):
        for stale_path in ("/observatorio/", "/observatorio/index.html"):
            def response(path, nonce, **kwargs):
                if path == stale_path and nonce is not None:
                    return b"stale response with nonce"
                return self.read(path, nonce, **kwargs)
            with self.subTest(path=stale_path), patch.object(evidence, "read_public", side_effect=response):
                with self.assertRaisesRegex(ValueError, "bytes publicados.*observatorio"):
                    evidence.verify_online(self.marker, "test", candidate_site=self.site)

    def test_observatory_candidate_must_be_present_and_regular(self):
        path = self.site / "observatorio/index.html"
        path.unlink()
        with patch.object(evidence, "read_public") as read:
            with self.assertRaisesRegex(ValueError, "ruta pública regular.*observatorio"):
                evidence.verify_online(self.marker, "test", candidate_site=self.site)
            read.assert_not_called()
        path.symlink_to(self.site / "index.html")
        with patch.object(evidence, "read_public") as read:
            with self.assertRaisesRegex(ValueError, "ruta pública regular.*observatorio"):
                evidence.verify_online(self.marker, "test", candidate_site=self.site)
            read.assert_not_called()

    def test_smoke_cli_always_verifies_candidate_observatory(self):
        argv = ["evidencia_publicacion.py", "smoke", "--site", str(self.site),
                "--repository", REPOSITORY, "--run-id", "123"]
        with patch.object(sys, "argv", argv), patch.object(evidence, "verify_online") as verify:
            evidence.main()
        verify.assert_called_once()
        self.assertEqual(verify.call_args.kwargs, {"candidate_site": self.site})

    def test_ordinary_request_has_no_nonce_or_cache_request_headers(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"public"
        response.__enter__.return_value.headers = {"Cache-Control": "no-cache, max-age=0, must-revalidate"}
        opener = MagicMock()
        opener.open.return_value = response
        for path in ("/", "/observatorio/", "/observatorio/index.html"):
            with self.subTest(path=path), patch.object(evidence.urllib.request, "build_opener", return_value=opener):
                self.assertEqual(evidence.read_public(path, None), b"public")
            request = opener.open.call_args.args[0]
            self.assertEqual(request.full_url, "https://cepoes.org" + path)
            self.assertEqual(request.header_items(), [])

    def test_canonical_response_without_revalidation_headers_fails(self):
        from unittest.mock import MagicMock
        for value in ("", "public, max-age=3600", 'no-cache="Set-Cookie"', "max-age=0, must-revalidate"):
            response = MagicMock()
            response.__enter__.return_value.headers = {"Cache-Control": value}
            opener = MagicMock()
            opener.open.return_value = response
            for path in ("/", "/observatorio/", "/observatorio/index.html"):
                with self.subTest(value=value, path=path), patch.object(evidence.urllib.request, "build_opener", return_value=opener):
                    with self.assertRaisesRegex(ValueError, "política de revalidación"):
                        evidence.read_public(path, None)

    def test_revalidation_preserves_existing_htaccess_and_is_idempotent(self):
        existing = "# Existing production rules\nRedirect 301 /old/ /new/\n"
        result = public_site.prepare_public_revalidation(existing)
        self.assertTrue(result.startswith(existing))
        self.assertEqual(public_site.prepare_public_revalidation(result), result)
        self.assertEqual(result.count("# BEGIN CEPOES PUBLIC REVALIDATION"), 1)
        self.assertIn('Header onsuccess unset Cache-Control env=CEPOES_REVALIDATE', result)
        self.assertIn('Header always set Cache-Control "no-cache, max-age=0, must-revalidate" env=CEPOES_REVALIDATE', result)

    def test_revalidation_scopes_only_public_mutable_routes(self):
        def matches(path):
            return any(re.fullmatch(pattern, path) for pattern in public_site.PUBLIC_REVALIDATION_PATHS)
        for path in ("/", "/index.html", "/observatorio/", "/observatorio/index.html",
                     "/datos/estado/", "/datos/estado/index.html",
                     "/assets/data/estructura-productiva/actual.json", "/.well-known/cepoes-release.json"):
            with self.subTest(path=path):
                self.assertTrue(matches(path))
        for path in ("/privado/", "/privado/index.html", "/suscripcion/", "/publicaciones/index.html",
                     "/assets/mapa.js", "/assets/site.css", "/assets/data/otra.json", "/datos/estado/archivo.html",
                     "/observatorio/salud-mental/", "/observatorio/precios/ipc/", "/observatorio/otra.html"):
            with self.subTest(path=path):
                self.assertFalse(matches(path))

    def test_revalidation_rejects_partial_or_duplicate_managed_sections(self):
        begin = "# BEGIN CEPOES PUBLIC REVALIDATION\n"
        end = "# END CEPOES PUBLIC REVALIDATION\n"
        for broken in (begin, end, (begin + end) * 2):
            with self.subTest(broken=broken), self.assertRaisesRegex(ValueError, "incompleta o duplicada"):
                public_site.prepare_public_revalidation(broken)

    def test_http_200_old_html_or_data_fails(self):
        for relative in evidence.PUBLIC_FILES:
            with self.subTest(relative=relative):
                old = self.contents[relative]
                self.contents[relative] = b"stale content served with HTTP 200"
                with patch.object(evidence, "read_public", side_effect=self.read):
                    with self.assertRaisesRegex(ValueError, "bytes"):
                        evidence.verify_online(self.marker, "test")
                self.contents[relative] = old

    def test_different_marker_fails_even_if_public_bytes_match(self):
        changed = {**self.marker, "commit_sha": "b" * 40}
        with patch.object(evidence, "read_public", side_effect=self.read):
            with self.assertRaisesRegex(ValueError, "marcador"):
                evidence.verify_online(changed, "test")

    def test_marker_exposes_only_whitelist_and_valid_identity(self):
        changed = copy.deepcopy(self.marker)
        changed["files"]["private/secret.json"] = changed["files"]["index.html"]
        with self.assertRaises(ValueError):
            evidence.validate_marker(changed, REPOSITORY)
        with self.assertRaises(ValueError):
            evidence.validate_marker(self.marker, "other/repo")
        with self.assertRaises(ValueError):
            evidence.read_public("/private/secret.json", "test")

    def test_only_404_is_bootstrap_absence(self):
        for code in (404, 403, 500):
            error = urllib.error.HTTPError("https://cepoes.org/", code, "fixture", {}, None)
            with self.subTest(code=code), patch.object(evidence, "read_public", side_effect=error):
                if code == 404:
                    self.assertIsNone(evidence.fetch_marker(REPOSITORY, "test"))
                else:
                    with self.assertRaises(urllib.error.HTTPError):
                        evidence.fetch_marker(REPOSITORY, "test")
        with patch.object(evidence, "read_public", return_value=b"<html>fallback</html>"):
            with self.assertRaises(ValueError):
                evidence.fetch_marker(REPOSITORY, "test")

    def test_redirects_cannot_escape_https_origin_or_route(self):
        for target in ("http://outside.example/elsewhere", "https://outside.example/", "https://cepoes.org/other", "https://cepoes.org/"):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "redirección"):
                evidence.NoRedirect().redirect_request(None, None, 302, "Moved", {}, target)

    def test_missing_candidate_route_rejected(self):
        (self.site / "index.html").unlink()
        with self.assertRaisesRegex(ValueError, "Falta"):
            evidence.create_marker(self.site, REPOSITORY, "a" * 40, "123", 1)

    def test_producer_identity_rejects_invalid_metadata(self):
        env = {"GITHUB_REPOSITORY": REPOSITORY,
               "GITHUB_WORKFLOW_REF": REPOSITORY + "/" + DEFINITION["path"] + "@refs/heads/main",
               "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2", "GITHUB_SHA": "a" * 40}
        self.assertEqual(producer.identity(env)["workflow"], DEFINITION["path"])
        for key, value in (("GITHUB_RUN_ID", "123\nInjected: value"), ("GITHUB_SHA", "main"),
                           ("GITHUB_WORKFLOW_REF", "other/repo/.github/workflows/a.yml@refs/heads/main")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                producer.identity({**env, key: value})


class ObservatoryFallbackTests(unittest.TestCase):
    """El build siguiente parte del HTML publicado por el build anterior."""

    LEGACY = (
        '<html><head></head><body><nav class="subnav"><a>Agenda</a></nav>'
        '<main><header><span id="data-date">fecha anterior</span></header>'
        '<section class="section alt"><div>Panorama anterior</div></section>'
        '<section class="section alt" id="conservar">Otro contenido</section>'
        '</main></body></html>'
    )

    def setUp(self):
        self.data = json.loads((ROOT / "datos.json").read_text(encoding="utf-8"))
        self.other = {
            "presupuesto.json": {"periodo": "2026-T1", "total": {
                "ejecucion_pct": 25, "vigente": 100, "devengado": 25, "modificaciones": 0}},
            "diagnostico_presupuestario.json": {},
            "datos/endeudamiento/manifest.json": {"ultimo_periodo": "2026-01"},
            "datos/endeudamiento/2026-01.json": {"caba": {"total": {
                "deudores": 100, "personas_mora": 10, "deuda_total_pesos": 1000}}},
            "legislatura_publica.json": {"generado": "2026-01-01"},
        }

    def render(self, source):
        def load(name):
            return self.data if name == "datos.json" else self.other[name]
        with patch.object(public_site, "load_json", side_effect=load):
            return public_site.apply_fallbacks(source, "/observatorio/index.html")

    def cards(self, source):
        return re.findall(
            r'<a class="kpi kpi-link".*?<div class="label">(.*?)</div>'
            r'<div class="value">(.*?)</div><div class="small">(.*?)</div>.*?</a>',
            source, flags=re.S)

    def assert_current_cards(self, source):
        data = self.data
        number, period = public_site.fmt_number, public_site.fmt_period
        self.assertEqual(self.cards(source), [
            ("IPCBA · interanual", f'+{number(data["ipcba"]["var_ia"][-1])}%', period(data["ipcba"]["meses"][-1])),
            ("IPCBA · mensual", f'+{number(data["ipcba"]["var_m"][-1])}%', period(data["ipcba"]["meses"][-1])),
            ("Actividad · PGB", f'+{number(data["pgb"]["ultimo_var"])}%', period(data["pgb"]["ultimo_trim"])),
            ("Locales vacantes", f'{number(100 - data["comunas_locales"]["total"]["tasa_ocup"])}%', period(data["comunas_locales"]["periodo"])),
            ("Tasa de empleo", f'{number(data["empleo"]["empleo"][-1])}%', period(data["empleo"]["trimestres"][-1])),
            ("Pobreza", f'{number(data["pobreza"]["pob_per_pct"][-1])}%', period(data["pobreza"]["periodos"][-1])),
        ])
        self.assertIn(f'<span id="data-date">{public_site.fmt_date(data["generado"])}</span>', source)
        self.assertEqual(source.count('class="section alt observatory-overview"'), 1)
        self.assertEqual(source.count('id="obs-pulse"'), 1)
        self.assertIn('<section class="section alt" id="conservar">Otro contenido</section>', source)

    def advance_fixture(self):
        # Valores de prueba: simulan un nuevo corte, nunca se publican como datos.
        self.data = copy.deepcopy(self.data)
        self.data["generado"] = "2027-02-08"
        self.data["ipcba"].update(meses=["Ene-27"], var_ia=[24.6], var_m=[1.2])
        self.data["pgb"].update(ultimo_trim="2026-T4", ultimo_var=2.3)
        self.data["empleo"].update(trimestres=["2026-T4"], empleo=[54.6], desocupacion=[5.1])
        self.data["pobreza"].update(periodos=["2026-T4"], pob_per_pct=[19.2])
        self.data["comunas_locales"]["periodo"] = "2026-C3"
        self.data["comunas_locales"]["total"]["tasa_ocup"] = 92.4

    def test_legacy_and_repeated_build_use_current_data(self):
        result = self.render(self.LEGACY)
        self.assert_current_cards(result)
        self.assertEqual(self.render(result), result)

    def test_second_generation_refreshes_all_values_periods_and_date(self):
        first = self.render(self.LEGACY)
        self.advance_fixture()
        second = self.render(first)
        self.assert_current_cards(second)
        self.assertIn("3.er cuatrimestre 2026", second)
        self.assertNotIn("1.er relevamiento 2026", second)
        self.assertNotEqual(self.cards(first), self.cards(second))
        self.assertEqual(self.render(second), second)

    def test_existing_overview_wins_over_unrelated_legacy_section(self):
        source = self.LEGACY.replace(
            '<div>Panorama anterior</div>',
            '<section class="extra observatory-overview section alt">'
            '<section>Panorama obsoleto anidado</section></section>')
        result = self.render(source)
        self.assert_current_cards(result)
        self.assertNotIn("Panorama obsoleto", result)
        self.assertIn('<section class="section alt"><section class="section alt observatory-overview">', result)

    def test_missing_or_broken_overview_fails_explicitly(self):
        for source in ("<main></main>", '<section class="section alt observatory-overview">sin cierre'):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "panorama del Observatorio"):
                self.render(source)

    def test_health_patch_preserves_refreshed_overview_across_builds(self):
        from parche_observatorio_salud import patch as health_patch
        first = health_patch(self.render(self.LEGACY))
        self.advance_fixture()
        second = health_patch(self.render(first))
        self.assert_current_cards(second)
        self.assertEqual(second.count('id="observatorio-salud-cuidados"'), 1)
        self.assertEqual(health_patch(self.render(second)), second)

    def test_cuatrimestre_labels_follow_parser_period_contract(self):
        for raw, expected in (("2026-C1", "1.er cuatrimestre 2026"),
                              ("2026-C2", "2.º cuatrimestre 2026"),
                              ("2027-C3", "3.er cuatrimestre 2027"),
                              ("2026-T2", "2.º trimestre 2026"),
                              ("Ago-26", "Agosto 2026")):
            with self.subTest(raw=raw):
                self.assertEqual(public_site.fmt_period(raw), expected)


class SubstantiveChangeTests(unittest.TestCase):
    def setUp(self):
        self.document = {"generado": "old", "fuentes": {"tabla": {"extraido": "old", "url": "https://example.test/source", "sha256": "a" * 64}},
                         "panorama": {"periodo": 2026, "valor": 100}, "fecha_corte": "2026-09-01"}

    def test_only_generation_and_source_extraction_dates_ignored(self):
        modified = copy.deepcopy(self.document)
        modified["generado"] = "new"
        modified["fuentes"]["tabla"]["extraido"] = "new"
        self.assertEqual(panorama_change.substantive(self.document), panorama_change.substantive(modified))
        self.assertEqual(self.document["fuentes"]["tabla"]["extraido"], "old")
        for key in ("sha256", "url"):
            changed = copy.deepcopy(modified)
            changed["fuentes"]["tabla"][key] = "different"
            self.assertNotEqual(panorama_change.substantive(self.document), panorama_change.substantive(changed))
        for key in ("fecha_corte", "panorama"):
            changed = copy.deepcopy(modified)
            changed[key] = "different"
            self.assertNotEqual(panorama_change.substantive(self.document), panorama_change.substantive(changed))

    def test_no_change_preserves_exact_previous_bytes_and_geo_change_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current, previous, current_geo, previous_geo = [root / name for name in ("current", "previous", "geo", "old_geo")]
            old_bytes = (json.dumps(self.document, indent=4) + "\n").encode()
            previous.write_bytes(old_bytes)
            modified = copy.deepcopy(self.document)
            modified["generado"] = "new"
            modified["fuentes"]["tabla"]["extraido"] = "new"
            current.write_text(json.dumps(modified))
            previous_geo.write_text('{"features": []}\n')
            current_geo.write_text('{ "features" : [] }')
            self.assertFalse(panorama_change.detect(current, previous, current_geo, previous_geo))
            self.assertEqual(current.read_bytes(), old_bytes)
            self.assertEqual(current_geo.read_bytes(), previous_geo.read_bytes())
            current_geo.write_text('{"features": [1]}')
            self.assertTrue(panorama_change.detect(current, previous, current_geo, previous_geo))


class PublishedLegislatureStateTests(unittest.TestCase):
    """Estado informa el mismo artefacto legislativo que se publica."""

    def generate_state(self, site):
        return subprocess.run(
            [sys.executable, str(ROOT / "generar_estado_datos.py"), str(site)],
            cwd=ROOT, capture_output=True, text=True,
        )

    def test_prepared_coverage_and_provenance_are_preserved(self):
        source_path = ROOT / "legislatura_publica.json"
        sessions_path = ROOT / "sesiones_publicas.json"
        originals = {path: path.read_bytes() for path in (source_path, sessions_path)}
        source = json.loads(originals[source_path])
        with tempfile.TemporaryDirectory(prefix="cepoes-state-") as directory:
            site = Path(directory)
            prepared = subprocess.run(
                [sys.executable, str(ROOT / "deploy/preparar_legislatura_publica.py"), str(site)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            public_path = site / "legislatura_publica.json"
            public = json.loads(public_path.read_text())
            self.assertEqual(len(public["expedientes"]), source["universo_consolidado"]["total"])
            self.assertNotEqual(len(public["expedientes"]), len(source["expedientes"]))
            self.assertEqual(public["expedientes_agenda"], source["expedientes"])
            for key in source.keys() - {"expedientes", "resumen"}:
                self.assertEqual(public[key], source[key], key)
            self.assertEqual(json.loads((site / "sesiones_publicas.json").read_text()),
                             json.loads(originals[sessions_path]))

            before = public_path.read_bytes()
            result = self.generate_state(site)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            page = (site / "datos/estado/index.html").read_text()
            import generar_estado_datos as state
            coverage = f'{len(public["expedientes"])} expedientes · {len(public["reuniones"])} reuniones'
            card = re.search(r'<article[^>]*>(?:(?!</article>).)*<h3><a href="/legislatura/">.*?</article>', page).group()
            self.assertIn(coverage, card)
            self.assertIn(state.date(public["generado"]), card)
            self.assertIn("Legislatura de la Ciudad de Buenos Aires", card)
            self.assertIn('/cepoes/metodologia/legislatura/', card)
            self.assertEqual(public_path.read_bytes(), before)

            # La fecha también debe proceder de la copia preparada, no del repo.
            public["generado"] = "2001-02-03T00:00:00+00:00"
            public_path.write_text(json.dumps(public))
            result = self.generate_state(site)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("3 de febrero de 2001", (site / "datos/estado/index.html").read_text())
        for path, original in originals.items():
            self.assertEqual(path.read_bytes(), original)

    def test_missing_or_invalid_prepared_json_cannot_fall_back_to_agenda(self):
        with tempfile.TemporaryDirectory(prefix="cepoes-state-") as directory:
            site = Path(directory)
            for contents in (None, "{invalid"):
                with self.subTest(contents=contents):
                    if contents is not None:
                        (site / "legislatura_publica.json").write_text(contents)
                    result = self.generate_state(site)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse((site / "datos/estado/index.html").exists())

    def test_deploy_prepares_legislature_before_state(self):
        workflow = (ROOT / ".github/workflows/desplegar-hostinger.yml").read_text()
        self.assertLess(workflow.index("python deploy/preparar_legislatura_publica.py _site"),
                        workflow.index("python generar_estado_datos.py _site"))


class WorkflowContractTests(unittest.TestCase):
    def test_fixed_registry_and_trigger_list(self):
        source = (ROOT / ".github/workflows/desplegar-hostinger.yml").read_text()
        block = source.split("  workflow_run:\n", 1)[1].split("\npermissions:", 1)[0]
        names = re.findall(r'^      - "([^"]+)"$', block, re.MULTILINE)
        self.assertEqual(names, [item["name"] for item in REGISTRY["workflows"]])
        self.assertEqual(len(set(item["id"] for item in REGISTRY["workflows"])), 16)
        self.assertIn("branches: [main]", block)
        self.assertIn("types: [completed]", block)
        for item in REGISTRY["workflows"]:
            text = (ROOT / item["path"]).read_text()
            self.assertTrue(text.startswith("name: " + item["name"] + "\n"))
            self.assertIn(' -m "$(python deploy/registrar_actualizacion.py trailers)"', text)
            self.assertIn("if git push; then\n              python deploy/registrar_actualizacion.py post-push", text)
            self.assertNotIn("actions: write", text)

    def test_new_producers_gate_commits_to_validated_main(self):
        for filename in NEW_PRODUCER_OUTPUTS:
            with self.subTest(workflow=filename):
                source = (ROOT / ".github/workflows" / filename).read_text()
                start = re.search(r"      - name: (?:Guardar|Commitear|Versionar)[^\n]*\n", source).start()
                block = source[start:].split("\n      - name:", 1)[0]
                event_condition = "== 'workflow_dispatch'" if filename.startswith("validar-") else "!= 'pull_request'"
                self.assertIn("if: github.ref == 'refs/heads/main' && github.event_name " + event_condition, block)
                self.assertIn("git diff --cached --quiet", block)
                self.assertLess(block.index("git diff --cached --quiet"), block.index("git commit"))
                self.assertIn('git pull --rebase --autostash origin "${GITHUB_REF_NAME}" || exit 1', block)
                self.assertIn('[ "$push_ok" -eq 1 ] || exit 1', block)
                self.assertNotIn("secrets.", source)
                import auditar_workflows_r2
                self.assertIn("git push", auditar_workflows_r2.inspect(ROOT / ".github/workflows" / filename)["evidence"])
        for filename in ("validar-legislatura.yml", "validar-presupuesto.yml"):
            definition = next(item for item in REGISTRY["workflows"] if Path(item["path"]).name == filename)
            self.assertEqual(definition["events"], ["workflow_dispatch"])
        dynamic = (ROOT / ".github/workflows/dinamica-productiva.yml").read_text()
        self.assertIn("if: always() && steps.generar.outputs.rc != '0'", dynamic)
        self.assertIn('[ "$fallo" -eq 0 ] && exit 0 || exit 1', dynamic)

    def test_new_commit_steps_execute_with_real_local_git_and_noop(self):
        # Sólo bare repositories temporales: no red, workflows, fuentes ni pushes externos.
        from test_endeudamiento_publico import manifest_fixture, period_fixture
        with tempfile.TemporaryDirectory(prefix="cepoes-producer-steps-") as directory:
            root = Path(directory)
            for index, (filename, (outputs, _)) in enumerate(NEW_PRODUCER_OUTPUTS.items()):
                with self.subTest(workflow=filename):
                    repo = root / str(index)
                    repo.mkdir()
                    run(repo, "init", "-b", "main")
                    run(repo, "config", "user.email", "actions@github.com")
                    run(repo, "config", "user.name", "cepoes-bot")
                    (repo / "README.md").write_text("fixture sin datos reales")
                    run(repo, "add", "README.md")
                    run(repo, "commit", "-m", "base")
                    base = run(repo, "rev-parse", "HEAD")
                    remote = root / f"remote-{index}.git"
                    run(root, "init", "--bare", str(remote))
                    run(repo, "remote", "add", "origin", str(remote))
                    run(repo, "push", "-u", "origin", "main")
                    deploy = repo / "deploy"
                    deploy.mkdir()
                    shutil.copy2(ROOT / "deploy/registrar_actualizacion.py", deploy)
                    source = (ROOT / ".github/workflows" / filename).read_text()
                    start = re.search(r"      - name: (?:Guardar|Commitear|Versionar)[^\n]*\n", source).start()
                    block = source[start:].split("\n      - name:", 1)[0]
                    script = textwrap.dedent(block.split("        run: |\n", 1)[1])
                    script = script.replace("${{ steps.generar.outputs.rc }}", "0")
                    script = script.replace("${{ needs.detectar.outputs.periodo }}", "2020-02")
                    if filename == "endeudamiento-mensual.yml":
                        shutil.copy2(ROOT / "deploy/validar_endeudamiento_publico.py", deploy)
                        public = repo / "datos/endeudamiento"
                        public.mkdir(parents=True)
                        (public / "manifest.json").write_text(json.dumps(manifest_fixture()))
                        for month in ("2020-01", "2020-02"):
                            (public / f"{month}.json").write_text(json.dumps(period_fixture(month)))
                        # Archivos ajenos presentes nunca entran en staging.
                        (public / "matriz_cp_barrio.json").write_text("fuera de alcance")
                        (public / "personas.json").write_text("sentinela sintética sin personas")
                    else:
                        paths = []
                        for line in re.findall(r"(?m)^\s+git add ([^\n]+)", source):
                            paths.extend(line.split())
                        for name in paths:
                            if name == "diagnostico_dinamica_productiva.txt":
                                continue
                            file = repo / name
                            file.parent.mkdir(parents=True, exist_ok=True)
                            file.write_text("agregado sintético validado por fixture")
                    env = {**os.environ, "GITHUB_REPOSITORY": REPOSITORY,
                           "GITHUB_WORKFLOW_REF": f"{REPOSITORY}/.github/workflows/{filename}@refs/heads/main",
                           "GITHUB_RUN_ID": str(50000 + index), "GITHUB_RUN_ATTEMPT": "1",
                           "GITHUB_SHA": base, "GITHUB_REF_NAME": "main"}
                    result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script],
                                            cwd=repo, env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    head = run(repo, "rev-parse", "HEAD")
                    self.assertNotEqual(head, base)
                    self.assertEqual(head, run(remote, "rev-parse", "main"))
                    self.assertIn('"commit_sha": "' + head + '"', result.stdout)
                    trailer = chain.Git(repo).trailers(head)
                    self.assertEqual(trailer[producer.KEYS["workflow"].lower()], [".github/workflows/" + filename])
                    changed = chain.Git(repo).changed(base, head)
                    self.assertTrue(chain.publication_changes(changed, PATTERNS))
                    if filename == "endeudamiento-mensual.yml":
                        self.assertEqual(set(changed), {"datos/endeudamiento/manifest.json", "datos/endeudamiento/2020-02.json"})
                    noop = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script],
                                          cwd=repo, env=env, text=True, capture_output=True)
                    self.assertEqual(noop.returncode, 0, noop.stdout + noop.stderr)
                    self.assertEqual(run(repo, "rev-parse", "HEAD"), head)
                    self.assertNotIn("CEPOES_POST_PUSH", noop.stdout)

                    if filename == "dinamica-productiva.yml":
                        (repo / "diagnostico_dinamica_productiva.txt").write_text("fallo sintético")
                        failed_script = textwrap.dedent(block.split("        run: |\n", 1)[1])
                        failed_script = failed_script.replace("${{ steps.generar.outputs.rc }}", "1")
                        failed = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", failed_script],
                                                cwd=repo, env=env, text=True, capture_output=True)
                        self.assertNotEqual(failed.returncode, 0)
                        diagnostic = run(repo, "rev-parse", "HEAD")
                        self.assertEqual(chain.Git(repo).changed(head, diagnostic), ["diagnostico_dinamica_productiva.txt"])
                        head = diagnostic

                    # Un rechazo del remoto local nunca se registra como push exitoso.
                    reject = remote / "hooks/pre-receive"
                    reject.write_text("#!/bin/sh\nexit 1\n")
                    reject.chmod(0o755)
                    if filename == "endeudamiento-mensual.yml":
                        for name, key in (("manifest.json", "actualizado_utc"), ("2020-02.json", "generado_utc")):
                            file = repo / "datos/endeudamiento" / name
                            document = json.loads(file.read_text())
                            document[key] = "2020-03-02T12:00:00+00:00"
                            file.write_text(json.dumps(document))
                    else:
                        file = repo / outputs[0]
                        file.write_text(file.read_text() + " cambio posterior")
                    failed = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script.replace("sleep 3", ":")],
                                            cwd=repo, env=env, text=True, capture_output=True)
                    self.assertNotEqual(failed.returncode, 0)
                    self.assertEqual(run(remote, "rev-parse", "main"), head)
                    self.assertNotIn("CEPOES_POST_PUSH", failed.stdout)

    def test_declared_outputs_match_workflow_staging_and_manifest(self):
        for filename, (public, secondary) in NEW_PRODUCER_OUTPUTS.items():
            with self.subTest(workflow=filename):
                source = (ROOT / ".github/workflows" / filename).read_text()
                for path in public:
                    self.assertTrue(chain.publication_changes([path], PATTERNS), path)
                for path in secondary:
                    self.assertFalse(chain.publication_changes([path], PATTERNS), path)
                if filename == "endeudamiento-mensual.yml":
                    self.assertNotIn("git add datos/endeudamiento/*.json", source)
                    self.assertIn('paths=$(python deploy/validar_endeudamiento_publico.py --root . --staging-paths)', source)
                    self.assertIn('git add -- "${public_paths[@]}"', source)
                else:
                    staged = []
                    for line in re.findall(r"(?m)^\s+git add ([^\n]+)", source):
                        staged.extend(line.split())
                    self.assertEqual(set(staged), set(public + secondary))

    def test_direct_json_reads_of_public_preparers_are_covered(self):
        direct = set()
        dynamic = []
        for filename, loader in (("deploy/preparar_sitio_publico.py", "load_json"),
                                 ("generar_estado_datos.py", "load")):
            tree = ast.parse((ROOT / filename).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == loader:
                    self.assertEqual(len(node.args), 1)
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        direct.add(arg.value)
                    else:
                        dynamic.append(ast.unparse(arg))
        # Única lectura variable: el período de Endeudamiento validado por su manifest.
        self.assertEqual(dynamic, ["f'datos/endeudamiento/{debt_file}'"])
        legislative = ast.parse((ROOT / "deploy/preparar_legislatura_publica.py").read_text())
        for node in ast.walk(legislative):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp)
                    and isinstance(node.value.left, ast.Name) and node.value.left.id == "ROOT"
                    and isinstance(node.value.right, ast.Constant)):
                direct.add(node.value.right.value)
        self.assertIn("diagnostico_presupuestario.json", direct)
        self.assertIn("sesiones_publicas.json", direct)
        missing = [path for path in sorted(direct) if not chain.publication_changes([path], PATTERNS)]
        self.assertEqual(missing, [], "Dependencias directas sin disparador: " + ", ".join(missing))
        self.assertIn("diagnostico_presupuestario.json", PATTERNS)
        self.assertNotIn("presupuesto*.json", PATTERNS)
        self.assertNotIn("*.json", PATTERNS)

    def test_endeudamiento_patterns_exclude_matrix_raw_personal_and_invalid_paths(self):
        for month in range(1, 13):
            self.assertTrue(chain.publication_changes([f"datos/endeudamiento/2026-{month:02}.json"], PATTERNS))
        for path in ("datos/endeudamiento/matriz_cp_barrio.json", "datos/endeudamiento/padron.json",
                     "datos/endeudamiento/cuit.json", "datos/endeudamiento/personas.json",
                     "datos/endeudamiento/raw/2026-08.json", "datos/endeudamiento/2026-00.json",
                     "datos/endeudamiento/2026-13.json", "bcra_deudores/202608DEUDORES.7Z",
                     "diagnostico_endeudamiento_productivo.json", "novedad_bcra.json"):
            self.assertFalse(chain.publication_changes([path], PATTERNS), path)
        publisher = (ROOT / ".github/workflows/desplegar-hostinger.yml").read_text()
        self.assertLess(publisher.index("python deploy/validar_endeudamiento_publico.py --root ."),
                        publisher.index("python deploy/preparar_sitio_publico.py"))
        self.assertNotIn("cp -a datos/endeudamiento", publisher)
        ci = (ROOT / ".github/workflows/validar-pr-r2.yml").read_text()
        self.assertIn("test_cadena_publicacion.py test_endeudamiento_publico.py", ci)

    def test_no_secret_preflight_or_permissions_expansion(self):
        source = (ROOT / ".github/workflows/desplegar-hostinger.yml").read_text()
        permissions = source.split("\npermissions:\n", 1)[1].split("\njobs:", 1)[0].strip()
        self.assertEqual(permissions, "contents: read\n  packages: write")
        preflight = source.split("jobs:\n  select:\n", 1)[1].split("\n  deploy:\n", 1)[0]
        for forbidden in ("secrets.", "environment: production", "packages: write", "actions: read", "workflow_run.head_sha"):
            self.assertNotIn(forbidden, preflight)
        self.assertIn("ref: main", preflight)
        self.assertIn("run: python deploy/encadenar_publicacion.py --preflight-only", preflight)
        self.assertIn("persist-credentials: false", preflight)
        self.assertIn("contents: read", preflight)
        self.assertIn("needs: select", source)
        self.assertIn("if: needs.select.outputs.should_deploy == 'true'", source)
        self.assertNotIn("gh run download", source)
        self.assertNotIn("actions: read", source)

    def test_exact_checkout_manifest_oci_marker_and_smoke(self):
        source = (ROOT / ".github/workflows/desplegar-hostinger.yml").read_text()
        self.assertIn("ref: ${{ steps.current.outputs.deploy_sha }}", source)
        self.assertIn('--commit "$DEPLOY_SHA"', source)
        self.assertIn('image.revision="${DEPLOY_SHA}"', source)
        self.assertNotIn('--commit "$GITHUB_SHA"', source)
        self.assertNotIn('image.revision="${GITHUB_SHA}"', source)
        self.assertIn("evidencia_publicacion.py create --site _site", source)
        self.assertIn("evidencia_publicacion.py smoke --site _site", source)
        self.assertLess(source.index("--guard-backup _rollback"), source.index("cp -a _rollback/. _site/"))
        self.assertLess(source.index("evidencia_publicacion.py create"), source.index("deploy/crear_release_durable.py \\"))
        self.assertLess(source.index("Conservar release durable en registro privado"), source.index("Publicar en Hostinger por SFTP"))
        for gate in ("validar_sitio_despliegue.py", "validar_contraste_visual.py", "validar_busqueda_global.py", "validar_r1_runtime.py"):
            self.assertIn("python " + gate, source)
        self.assertIn("package-anonymous-pull.log", source)
        self.assertIn("--retention-days 90", source)
        self.assertIn("steps.publish.outcome == 'failure'", source)
        self.assertIn("_rollback/.well-known/cepoes-release.json", source)
        self.assertIn('$marker_cleanup', source)
        self.assertIn("cancel-in-progress: false", source)

    def test_noop_cannot_replace_pending_publication_and_locked_reselection(self):
        source = (ROOT / ".github/workflows/desplegar-hostinger.yml").read_text()
        self.assertNotRegex(source, r"(?m)^concurrency:")
        preflight, deploy = source.split("  deploy:\n", 1)
        self.assertNotIn("group: cepoes-hostinger-production", preflight)
        self.assertIn("    concurrency:\n      group: cepoes-hostinger-production", deploy)
        self.assertLess(deploy.index("id: current"), deploy.index("ref: ${{ steps.current.outputs.deploy_sha }}"))
        self.assertLess(deploy.index("id: current"), deploy.index("Diagnosticar acceso SFTP"))
        for name in ("Instalar cliente SFTP", "Descargar producción como respaldo y base", "Publicar en Hostinger por SFTP"):
            self.assertIn("- name: " + name + "\n        if: steps.current.outputs.should_deploy == 'true'", deploy)

    def test_contract_is_in_ci_and_inputs_match(self):
        ci = (ROOT / ".github/workflows/validar-pr-r2.yml").read_text()
        self.assertIn("python -m unittest test_cadena_publicacion.py", ci)
        import validar_rutas_publicacion
        validar_rutas_publicacion.validate_input_manifest((ROOT / ".github/workflows/desplegar-hostinger.yml").read_text())


if __name__ == "__main__":
    unittest.main()
