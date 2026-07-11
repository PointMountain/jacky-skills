from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
AUDIT_STAGED = SKILL_ROOT / "scripts" / "audit_staged.py"


class AuditSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "security-tests@example.test")
        self.git("config", "user.name", "Security Tests")
        (self.repo / "baseline.txt").write_text("baseline\n", encoding="utf-8")
        self.git("add", "baseline.txt")
        self.git("commit", "-qm", "baseline")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def audit(self, *paths: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT_STAGED),
                "--repo",
                str(self.repo),
                "--paths",
                *paths,
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {}
        return result, payload

    @staticmethod
    def rules(payload: dict) -> set[str]:
        return {finding["rule"] for finding in payload.get("findings", [])}

    def test_reads_staged_blob_instead_of_worktree_file(self) -> None:
        path = self.repo / "target.txt"
        staged_secret = "Authori" + "zation: Bearer " + "s" * 32
        path.write_text(staged_secret + "\n", encoding="utf-8")
        self.git("add", "target.txt")
        path.write_text("工作区已经改回安全内容\n", encoding="utf-8")

        result, payload = self.audit("target.txt")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("authorization", self.rules(payload))

    def test_does_not_scan_unstaged_worktree_replacement(self) -> None:
        path = self.repo / "target.txt"
        path.write_text("公开说明\n", encoding="utf-8")
        self.git("add", "target.txt")
        worktree_only_secret = "Cook" + "ie: session=" + "w" * 32
        path.write_text(worktree_only_secret + "\n", encoding="utf-8")

        result, payload = self.audit("target.txt")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["ok"])

    def test_scans_entire_index_blob_not_only_added_lines(self) -> None:
        path = self.repo / "existing.txt"
        old_secret = "SERVICE" + "_TOKEN=" + "t" * 32
        path.write_text(old_secret + "\nold line\n", encoding="utf-8")
        self.git("add", "existing.txt")
        self.git("commit", "-qm", "seed fake credential")
        path.write_text(old_secret + "\nchanged safe line\n", encoding="utf-8")
        self.git("add", "existing.txt")

        result, payload = self.audit("existing.txt")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("credential_assignment", self.rules(payload))

    def test_rejects_media_extension_even_when_payload_looks_textual(self) -> None:
        path = self.repo / "assets" / "clip.mp4"
        path.parent.mkdir()
        path.write_bytes(b"not-a-real-video-but-still-not-source")
        self.git("add", "assets/clip.mp4")

        result, payload = self.audit("assets/clip.mp4")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("media_asset", self.rules(payload))

    def test_rejects_private_image_binary_by_default(self) -> None:
        path = self.repo / "assets" / "private" / "portrait.jpg"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"\xff\xd8\xff\xe0\x00\x10PRIVATE\x00PHOTO")
        self.git("add", "assets/private/portrait.jpg")

        result, payload = self.audit("assets/private/portrait.jpg")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("media_asset", self.rules(payload))

    def test_allows_small_font_only_in_exact_public_font_path(self) -> None:
        path = self.repo / "demo" / "assets" / "public" / "fonts" / "fixture.woff2"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"wOF2" + b"\x00" * 64)
        self.git("add", "demo/assets/public/fonts/fixture.woff2")

        result, payload = self.audit("demo/assets/public/fonts/fixture.woff2")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["ok"])

    def test_allows_small_font_in_demo_assets_fonts_path(self) -> None:
        path = self.repo / "demo" / "assets" / "fonts" / "fixture.woff2"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"wOF2" + b"\x00" * 64)
        self.git("add", "demo/assets/fonts/fixture.woff2")

        result, payload = self.audit("demo/assets/fonts/fixture.woff2")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["ok"])

    def test_rejects_font_binary_outside_exact_assets_font_paths(self) -> None:
        path = self.repo / "demo" / "fonts" / "private.woff2"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"wOF2" + b"\x00" * 64)
        self.git("add", "demo/fonts/private.woff2")

        result, payload = self.audit("demo/fonts/private.woff2")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("binary_asset", self.rules(payload))

    def test_detects_cookie_assignment_private_key_and_provider_tokens(self) -> None:
        cases = {
            "cookie_header": "Cook" + "ie: session=" + "c" * 32,
            "set_cookie_header": "Set-" + "Cook" + "ie: sid=" + "d" * 32 + "; HttpOnly",
            "credential_assignment": "OPENAI" + "_API_KEY='sk-" + "a" * 32 + "'",
            "private" + "_key": "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
            "github" + "_token": "g" + "hp_" + "g" * 40,
            "github_token_fine_grained": "github" + "_pat_" + "h" * 60,
            "npm" + "_token": "n" + "pm_" + "n" * 36,
        }

        for expected_rule, unsafe in cases.items():
            with self.subTest(rule=expected_rule):
                path = self.repo / f"{expected_rule}.txt"
                path.write_text(unsafe + "\n", encoding="utf-8")
                self.git("add", path.name)
                result, payload = self.audit(path.name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_rule, self.rules(payload))
                self.git("reset", "-q", "--", path.name)
                path.unlink()

    def test_detects_prefixed_password_and_secret_environment_variables(self) -> None:
        cases = {
            "DATABASE" + "_PASSWORD": "database-" + "password-" + "d" * 24,
            "AWS" + "_SECRET_ACCESS_KEY": "aws-secret-" + "access-" + "a" * 24,
            "OAUTH" + "_CLIENT_SECRET": "oauth-client-" + "secret-" + "o" * 24,
            "STRIPE" + "_SECRET_KEY": "stripe-secret-" + "key-" + "s" * 24,
        }

        for variable, unsafe_value in cases.items():
            with self.subTest(variable=variable):
                path = self.repo / f"{variable.lower()}.env"
                path.write_text(f'{variable}="{unsafe_value}"\n', encoding="utf-8")
                self.git("add", path.name)

                result, payload = self.audit(path.name)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("credential_assignment", self.rules(payload))
                self.git("reset", "-q", "--", path.name)
                path.unlink()

    def test_detects_punctuated_literal_and_quoted_sensitive_key(self) -> None:
        password_name = "DATABASE" + "_PASSWORD"
        client_secret_name = "OAUTH" + "_CLIENT_SECRET"
        punctuated_value = "C0rrect" + "!Horse?Battery#Staple"
        client_value = "oauth-client-" + "secret-value-2026"
        env_path = self.repo / "punctuated.env"
        json_path = self.repo / "quoted.json"
        env_path.write_text(
            f'{password_name}="{punctuated_value}"\n', encoding="utf-8"
        )
        json_path.write_text(
            json.dumps({client_secret_name: client_value}) + "\n", encoding="utf-8"
        )
        self.git("add", env_path.name, json_path.name)

        result, payload = self.audit(env_path.name, json_path.name)

        self.assertNotEqual(result.returncode, 0)
        findings = [
            finding
            for finding in payload["findings"]
            if finding["rule"] == "credential_assignment"
        ]
        self.assertEqual(
            {finding["path"] for finding in findings},
            {env_path.name, json_path.name},
        )

    def test_detects_unicode_posix_and_windows_home_paths(self) -> None:
        cases = {
            "unicode-macos.txt": "/" + "Users/alice/" + "照片/private.jpg",
            "unicode-linux.txt": "/" + "home/用户/" + "视频/private.mp4",
            "windows.txt": "C:" + "\\Users\\Alice\\Photos\\private.jpg",
        }
        for name, private_path in cases.items():
            (self.repo / name).write_text(private_path + "\n", encoding="utf-8")
        self.git("add", *cases)

        result, payload = self.audit(*cases)

        self.assertNotEqual(result.returncode, 0)
        home_findings = [
            finding for finding in payload["findings"] if finding["rule"] == "home_path"
        ]
        self.assertEqual(
            {finding["path"] for finding in home_findings}, set(cases)
        )

    def test_rejects_embedded_media_data_blob_and_large_base64(self) -> None:
        encoded = "QUJD" * 80
        data_prefix = "da" + "ta:image/jpeg;base64,"
        blob_prefix = "bl" + "ob:https://private.example/"
        fixtures = {
            "fixture.svg": f'<svg><image href="{data_prefix}{encoded}"/></svg>\n',
            "fixture.html": f'<video src="{blob_prefix}private-video"></video>\n',
            "fixture.css": f'.hero{{background:url("{data_prefix}{encoded}")}}\n',
            "encoded.txt": encoded + "\n",
        }
        for name, content in fixtures.items():
            (self.repo / name).write_text(content, encoding="utf-8")
        self.git("add", *fixtures)

        result, payload = self.audit(*fixtures)

        self.assertNotEqual(result.returncode, 0)
        findings_by_rule = {
            rule: {
                finding["path"]
                for finding in payload["findings"]
                if finding["rule"] == rule
            }
            for rule in ("embedded_data_uri", "blob_uri", "large_base64")
        }
        self.assertEqual(
            findings_by_rule["embedded_data_uri"], {"fixture.svg", "fixture.css"}
        )
        self.assertEqual(findings_by_rule["blob_uri"], {"fixture.html"})
        self.assertEqual(
            findings_by_rule["large_base64"],
            {"fixture.svg", "fixture.css", "encoded.txt"},
        )

    def test_allows_documentation_placeholders_and_environment_references(self) -> None:
        path = self.repo / "credential-policy.md"
        safe_examples = [
            'DATABASE_PASSWORD="<redacted>"',
            'AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}"',
            'OAUTH_CLIENT_SECRET="$OAUTH_CLIENT_SECRET"',
            'STRIPE_SECRET_KEY="<YOUR_STRIPE_SECRET_KEY>"',
            json.dumps({"DATABASE_PASSWORD": "${DATABASE_PASSWORD}"}),
            json.dumps({"OAUTH_CLIENT_SECRET": "<YOUR_OAUTH_CLIENT_SECRET>"}),
        ]
        path.write_text("\n".join(safe_examples) + "\n", encoding="utf-8")
        self.git("add", path.name)

        result, payload = self.audit(path.name)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["ok"])

    def test_type_change_from_symlink_to_binary_is_audited_with_safe_peer(self) -> None:
        target = self.repo / "safe-target.txt"
        target.write_text("safe target\n", encoding="utf-8")
        payload_path = self.repo / "payload.dat"
        payload_path.symlink_to(target.name)
        self.git("add", "safe-target.txt", "payload.dat")
        self.git("commit", "-qm", "seed symlink")

        payload_path.unlink()
        payload_path.write_bytes(b"\x00\xffPRIVATE-BINARY")
        peer = self.repo / "safe.txt"
        peer.write_text("公开说明\n", encoding="utf-8")
        self.git("add", "payload.dat", "safe.txt")
        self.assertIn("T\tpayload.dat", self.git("diff", "--cached", "--name-status").stdout)

        result, payload = self.audit(".")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(payload["staged_files"], ["payload.dat", "safe.txt"])
        self.assertIn("binary_asset", self.rules(payload))

    def test_rejects_non_regular_symlink_in_index(self) -> None:
        target = self.repo / "safe-target.txt"
        target.write_text("safe target\n", encoding="utf-8")
        link = self.repo / "public-link.txt"
        link.symlink_to(target.name)
        self.git("add", "public-link.txt")

        result, payload = self.audit("public-link.txt")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non_regular_index_entry", self.rules(payload))

    def test_redacted_policy_examples_remain_safe(self) -> None:
        path = self.repo / "policy.md"
        path.write_text(
            "\n".join(
                [
                    "Cook" + "ie: <redacted>",
                    "Set-" + "Cook" + "ie: <redacted>",
                    'OPENAI_API_KEY="<redacted>"',
                    'SERVICE_TOKEN="${SERVICE_TOKEN}"',
                    "私钥头部必须替换为占位符后才能提交。",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.git("add", "policy.md")

        result, payload = self.audit("policy.md")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
