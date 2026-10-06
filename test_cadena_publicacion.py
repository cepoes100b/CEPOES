#!/usr/bin/env python3
"""Contrato offline: identidad de eventos, rebase real, no-op y antirregresión."""
from __future__ import annotations

import copy
import json
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

REGISTRY = json.loads((ROOT / "deploy/producer-workflows.json").read_text())
PATTERNS = [item["path"] for item in json.loads((ROOT / "deploy/publication-inputs.json").read_text())["inputs"]]
REPOSITORY = REGISTRY["repository"]
REPOSITORY_ID = 12345
DEFINITION = next(item for item in REGISTRY["workflows"] if item["path"].endswith("actualizar.yml"))


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

    def read(self, path, nonce, **kwargs):
        if path == "/" + evidence.MARKER_PATH:
            return json.dumps(self.marker).encode()
        relative = next(key for key, value in evidence.PUBLIC_FILES.items() if value == path)
        return self.contents[relative]

    def test_exact_bytes_of_all_three_routes(self):
        with patch.object(evidence, "read_public", side_effect=self.read):
            evidence.verify_online(self.marker, "test")
        self.assertEqual(set(self.marker["files"]), set(evidence.PUBLIC_FILES))

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


class WorkflowContractTests(unittest.TestCase):
    def test_fixed_registry_and_trigger_list(self):
        source = (ROOT / ".github/workflows/desplegar-hostinger.yml").read_text()
        block = source.split("  workflow_run:\n", 1)[1].split("\npermissions:", 1)[0]
        names = re.findall(r'^      - "([^"]+)"$', block, re.MULTILINE)
        self.assertEqual(names, [item["name"] for item in REGISTRY["workflows"]])
        self.assertEqual(len(set(item["id"] for item in REGISTRY["workflows"])), 6)
        self.assertIn("branches: [main]", block)
        self.assertIn("types: [completed]", block)
        for item in REGISTRY["workflows"]:
            text = (ROOT / item["path"]).read_text()
            self.assertTrue(text.startswith("name: " + item["name"] + "\n"))
            self.assertIn(' -m "$(python deploy/registrar_actualizacion.py trailers)"', text)
            self.assertIn("if git push; then\n              python deploy/registrar_actualizacion.py post-push", text)
            self.assertNotIn("actions: write", text)

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
