"""Synthetic-only contract tests. No model, credentials, network or ingest."""
import contextlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from qa import probar_copilot_cli_release as release


def forbidden(*args, **kwargs):
    raise AssertionError("External operation in offline QA")


with patch.dict(sys.modules, {
    "requests": types.SimpleNamespace(Session=lambda: types.SimpleNamespace(headers={}, get=forbidden)),
    "bs4": types.SimpleNamespace(BeautifulSoup=forbidden),
    "docx": types.SimpleNamespace(Document=forbidden),
    "pypdf": types.SimpleNamespace(PdfReader=forbidden),
}):
    import automatizar_analisis_legislativo as pipeline
    import automatizar_analisis_legislativo_copilot as copilot
    import automatizar_analisis_legislativo_hardened as hardened
    import automatizar_analisis_legislativo_v3_3 as v33


class CopilotContractTests(unittest.TestCase):
    def test_cli_remains_noninteractive_without_remote_or_export(self):
        fixture = dict.fromkeys(pipeline.SCHEMA["schema"]["required"], "")
        fixture.update(internal_priority="baja", recommendation="sin_definir", confidence=0)
        result = subprocess.CompletedProcess([], 0, json.dumps(fixture), "")
        with patch.object(copilot.subprocess, "run", return_value=result) as run:
            self.assertEqual(copilot.run_programmatic_copilot("fixture sintético", "model-fixture"), fixture)
            argv = run.call_args.args[0]
            self.assertEqual(argv[:3], ["copilot", "-p", "fixture sintético"])
            self.assertIn("--sync-session=off", argv)
            for option in ("--no-ask-user", "--no-custom-instructions", "--no-auto-update",
                           "--deny-tool=shell,write,read,url,memory"):
                self.assertIn(option, argv)
            for option in ("--no-remote", "--no-remote-export", "--remote", "--connect", "--allow-all"):
                self.assertNotIn(option, argv)
            self.assertEqual(argv[-2:], ["--model", "model-fixture"])

    def test_active_hardened_path_reuses_same_arg_builder(self):
        with patch.dict(hardened.os.environ, {"COPILOT_GITHUB_TOKEN": "fixture-not-a-credential"},
                        clear=True), patch.object(copilot, "run_programmatic_copilot",
                                                 return_value={"fixture": True}) as run:
            self.assertEqual(hardened.run_copilot("fixture"), {"fixture": True})
            run.assert_called_once_with("fixture", "")

    def test_help_preflight_has_no_prompt_or_inherited_auth(self):
        help_flags = " ".join(f.split("=", 1)[0] for f in copilot.PROMPT_OPTIONS) + " --prompt"
        result = subprocess.CompletedProcess([], 0, help_flags, "")
        with patch.object(copilot.subprocess, "run", return_value=result) as run:
            copilot.check_copilot_cli()
            self.assertEqual(run.call_args.args[0], ["copilot", "--help"])
            self.assertEqual(set(run.call_args.kwargs["env"]), {"PATH", "TERM", "COPILOT_AUTO_UPDATE"})
            self.assertEqual(run.call_args.kwargs["env"]["COPILOT_AUTO_UPDATE"], "false")
            run.return_value = subprocess.CompletedProcess([], 0, help_flags.replace("--sync-session", "--no-remote-export"), "")
            with self.assertRaisesRegex(pipeline.ModelExecutionError, "incompatible"):
                copilot.check_copilot_cli()

    def test_cli_failures_are_typed_and_no_output_is_exposed(self):
        for result in [subprocess.CompletedProcess([], 1, "", "contenido interno ficticio"),
                       subprocess.CompletedProcess([], 0, "contenido interno ficticio", "")]:
            with self.subTest(code=result.returncode), patch.object(copilot.subprocess, "run", return_value=result):
                with self.assertRaises(pipeline.ModelExecutionError) as exc:
                    copilot.run_programmatic_copilot("fixture")
                self.assertNotIn("contenido interno ficticio", str(exc.exception))

    def test_active_v33_surfaces_cli_failure_and_synthetic_selftest_is_pure(self):
        with patch.object(copilot.subprocess, "run", side_effect=forbidden), contextlib.redirect_stdout(io.StringIO()):
            v33.self_test()
        failure = subprocess.CompletedProcess([], 1, "", "error sintético de opciones")
        with patch.dict(hardened.os.environ, {"COPILOT_GITHUB_TOKEN": "fixture-not-a-credential"},
                        clear=True), patch.object(copilot.subprocess, "run", return_value=failure) as run:
            with self.assertRaises(pipeline.ModelExecutionError):
                v33.call_copilot_v33("fixture sin documentos reales")
            self.assertEqual(run.call_count, 1)
            self.assertIn("--sync-session=off", run.call_args.args[0])


class ProcessSmokeTests(unittest.TestCase):
    def test_zero_new_drafts_can_be_healthy(self):
        model, call, out, err, result = self.exercise(True, [])
        self.assertEqual(result, 0)
        model.assert_not_called()
        self.assertEqual([c.args[0]["action"] for c in call.call_args_list], ["check", "check"])
        self.assertIn("0 completadas · 0 fallidas", out)
        self.assertNotIn("warning", err)

    def test_all_model_failures_raise_and_never_ingest(self):
        exc = pipeline.ModelExecutionError("CLI incompatible sintético")
        model, call, out, err, result = self.exercise(False, [exc, exc], expect_error=True)
        self.assertEqual(model.call_count, 2)
        self.assertEqual([c.args[0]["action"] for c in call.call_args_list], ["check", "check"])
        self.assertIn("0 completadas · 2 fallidas", out)

    def test_mixed_run_keeps_valid_ingest_and_marks_partial(self):
        _, call, out, err, result = self.exercise(False, [pipeline.ModelExecutionError("fixture"), {"fixture": True}])
        self.assertEqual(result, 1)
        self.assertEqual([c.args[0]["action"] for c in call.call_args_list], ["check", "check", "ingest"])
        self.assertIn("1 completadas · 1 fallidas", out)
        self.assertIn("::warning::", err)

    def exercise(self, exists, model_outputs, expect_error=False):
        projects = [{"numero": "TEST-1"}, {"numero": "TEST-2"}]
        call = Mock(side_effect=lambda payload: {"exists": exists} if payload["action"] == "check"
                    else {"inserted": True, "version": 1})
        model = Mock(side_effect=model_outputs)
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "legislatura.json"
            source.write_text(json.dumps({"expedientes": projects}), encoding="utf-8")
            with patch.multiple(pipeline, LEG_PATH=source,
                                get_focus_commissions=lambda: ["fixture"],
                                dedupe_candidates=lambda data, focus: data,
                                collect_source=lambda project: ("fixture", "hash", {}),
                                private_call=call, call_model=model), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                if expect_error:
                    with self.assertRaisesRegex(pipeline.ModelExecutionError, "Ninguna inferencia"):
                        pipeline.process(3)
                    result = None
                else:
                    result = pipeline.process(3)
        return model, call, out.getvalue(), err.getvalue(), result


class PublicReleaseProbeTests(unittest.TestCase):
    def test_version_allows_official_punctuation_and_either_channel(self):
        v = release.VERSION
        for stdout, stderr, expected in (
            (f"GitHub Copilot CLI {v}.\n", "", "stdout"),
            ("", f"GitHub Copilot CLI {v}\n", "stderr"),
            (f"\x1b[1mGitHub Copilot CLI {v}\x1b[0m (build abc)\n", f"v{v}\n", "stdout/stderr"),
            (f"Version: {v}\n", "", "stdout"),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(release.verify_version(stdout, stderr), expected)

    def test_wrong_numeric_versions_and_nonstable_tails_fail_without_raw_output(self):
        v = release.VERSION
        for stdout, stderr in (
            ("GitHub Copilot CLI 1.0.113.\n", ""),
            ("", f"GitHub Copilot CLI {v}-preview.3\n"),
            (f"GitHub Copilot CLI {v}-2\n", ""),
            (f"GitHub Copilot CLI {v}+a1b2\n", ""),
            (f"GitHub Copilot CLI {v}.1\n", ""),
            (f"GitHub Copilot CLI {v}\n", "GitHub Copilot CLI 2.0.114\n"),
            ("no es una versión; texto privado sintético\n", ""),
        ):
            with self.subTest(stdout=stdout, stderr=stderr), self.assertRaises(RuntimeError) as exc:
                release.verify_version(stdout, stderr)
            self.assertNotIn("texto privado", str(exc.exception))
            self.assertNotIn("preview", str(exc.exception))
            self.assertNotIn("a1b2", str(exc.exception))
            self.assertIn("stdout=", str(exc.exception))
            self.assertIn("stderr=", str(exc.exception))

    def test_public_https_release_origins_only(self):
        release.require_release_url(release.URL)
        release.require_release_url("https://release-assets.githubusercontent.com/test.bin")
        for url in ("http://github.com/file", "https://user@github.com/file",
                    "https://github.com:444/file", "https://api.github.com/file",
                    "https://example.com/file"):
            with self.subTest(url=url), self.assertRaises(RuntimeError):
                release.require_release_url(url)

    def test_probe_uses_actual_options_with_no_prompt_auth_or_network(self):
        self.assertEqual(release.FLAGS, copilot.PROMPT_OPTIONS)
        binary, home = Path("/fixture/copilot"), Path("/fixture/home")
        reply = subprocess.CompletedProcess([], 0, "fixture output", "")
        with patch.object(release.subprocess, "run", return_value=reply) as run:
            release.run_probe(binary, home, "--help", *release.FLAGS)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[1:10], [
            "--kill-after=5s", "45s", "/usr/bin/sudo", "-n", "--",
            "/usr/bin/unshare", "--net", "--", "/usr/bin/setpriv",
        ])
        self.assertIn("--no-new-privs", cmd)
        self.assertIn("-i", cmd)
        self.assertNotIn("-p", cmd)
        self.assertIn("PATH=/fixture/home/empty-path", cmd)
        self.assertEqual(set(run.call_args.kwargs["env"]), {"PATH", "TERM"})
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_extractor_accepts_only_regular_binary_and_writes_fixed_path(self):
        with tempfile.TemporaryDirectory() as raw:
            work = Path(raw)
            archive, binary = work / "sample.tgz", work / "known-path"
            with tarfile.open(archive, "w:gz") as tar:
                synthetic = b"no vendored executable"
                member = tarfile.TarInfo("some/subdirectory/copilot")
                member.size = len(synthetic)
                tar.addfile(member, io.BytesIO(synthetic))
                link = tarfile.TarInfo("another/copilot")
                link.type = tarfile.SYMTYPE
                link.linkname = "/outside"
                tar.addfile(link)
            release.extract_cli(archive, binary)
            self.assertEqual(binary.read_bytes(), synthetic)
            self.assertEqual(binary.stat().st_mode & 0o777, 0o700)
            self.assertEqual(sorted(x.name for x in work.iterdir()), ["known-path", "sample.tgz"])

    def test_shared_installer_only_exposes_verified_binary_and_never_runs_it(self):
        fixture = b"fixture, not a binary"

        def fake_download(archive):
            with tarfile.open(archive, "w:gz") as tar:
                member = tarfile.TarInfo("copilot")
                member.size = len(fixture)
                tar.addfile(member, io.BytesIO(fixture))

        with tempfile.TemporaryDirectory() as raw, patch.object(release, "require_platform"), \
                patch.object(release.subprocess, "run", side_effect=forbidden), \
                patch.object(release, "download", side_effect=fake_download) as download:
            output = Path(raw) / "copilot"
            release.install_verified(output)
            self.assertEqual(output.read_bytes(), fixture)
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            self.assertEqual(list(Path(raw).iterdir()), [output])
            self.assertEqual(download.call_args.args[0].name, release.ASSET)
            with self.assertRaises(FileExistsError):
                release.install_verified(output)
            self.assertEqual(output.read_bytes(), fixture)
            download.side_effect = RuntimeError("hash incorrecto simulado")
            failure = Path(raw) / "fallo"
            with self.assertRaisesRegex(RuntimeError, "hash incorrecto"):
                release.install_verified(failure)
            self.assertFalse(failure.exists())


if __name__ == "__main__":
    unittest.main()
