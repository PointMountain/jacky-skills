import os
import re
import subprocess
import unittest
from datetime import date
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_FLOW = REPO_ROOT / "labs" / "app-flow" / "app-flow"
HAPPY_EXPERIENCE = REPO_ROOT / "skills" / "happy-app-experience"


def load_skill(skill_root: Path) -> tuple[dict[str, object], str]:
    text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = text.split("---\n", 2)[1]
    metadata = yaml.safe_load(frontmatter)
    if not isinstance(metadata, dict):
        raise AssertionError(f"Invalid frontmatter in {skill_root / 'SKILL.md'}")
    return metadata, text


class AppFlowContractTests(unittest.TestCase):
    def assert_progressive_local_memory(self, skill_root: Path, body: str) -> None:
        ignore_lines = {
            line.strip()
            for line in (skill_root / ".gitignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertIn("local/", ignore_lines)
        self.assertIn("*.local.*", ignore_lines)

        ignored_path = skill_root / "local" / "memories" / "example.md"
        ignored = subprocess.run(
            [
                "git",
                "check-ignore",
                "-q",
                "--no-index",
                ignored_path.relative_to(REPO_ROOT).as_posix(),
            ],
            cwd=REPO_ROOT,
            check=False,
        )
        self.assertEqual(0, ignored.returncode)

        tracked = subprocess.run(
            ["git", "ls-files", (skill_root / "local").relative_to(REPO_ROOT).as_posix()],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual("", tracked.stdout.strip())

        protocol = REPO_ROOT / "docs" / "philosophy" / "references" / "local-memory.md"
        protocol_reference = Path(os.path.relpath(protocol, skill_root)).as_posix()
        self.assertIn(protocol_reference, body)
        self.assertTrue((skill_root / protocol_reference).resolve().is_file())

        self.assertIn("local/INDEX.md", body)
        self.assertRegex(
            body,
            r"1 个根入口[^\n]+1 个作用域 map[^\n]+3 条[^\n]+32 KiB",
        )
        self.assertRegex(
            body,
            r"定位优先级[^\n]*显式[^\n]*WorkTree[^\n]*分支[^\n]*Repo[^\n]*主题",
        )
        for invariant in ("repo-key", "不可变", "supersedes", "敏感", "损坏"):
            self.assertIn(invariant, body)

    def test_app_flow_is_thin_and_metadata_driven(self) -> None:
        metadata, body = load_skill(APP_FLOW)
        self.assertEqual("app-flow", metadata["name"])
        description = str(metadata["description"])
        for phrase in ("App", "截图", "长时间"):
            self.assertIn(phrase, description)

        for phrase in (
            "不固定技术栈",
            "不固定阶段",
            "不固定交付形式",
            "metadata",
            "最多 5 个",
            "最多 2 个",
            "没有匹配",
            "多个匹配",
            "不可读",
        ):
            self.assertIn(phrase, body)

        self.assertNotIn("happy-app-experience", body)
        self.assertFalse((APP_FLOW / "workflow.yaml").exists())

    def test_app_flow_has_bounded_durable_loop(self) -> None:
        _, body = load_skill(APP_FLOW)
        for phrase in (
            "唯一",
            "maps/resume/<repo-key>/<task-key>.md",
            "generation",
            "sequence",
            "fencing",
            "每 10 秒",
            "30 秒",
            "token",
            "非 owner",
            "checkpoint",
            "4 小时",
            "15 分钟",
            "失败签名",
            "新增证据",
            "阻塞",
            "用户授权",
        ):
            self.assertIn(phrase, body)

    def test_app_flow_local_memory_is_ignored_and_progressive(self) -> None:
        _, body = load_skill(APP_FLOW)
        self.assert_progressive_local_memory(APP_FLOW, body)

    def test_happy_experience_is_optional_and_evidence_backed(self) -> None:
        metadata, body = load_skill(HAPPY_EXPERIENCE)
        self.assertEqual("happy-app-experience", metadata["name"])
        description = str(metadata["description"])
        self.assertIn("参考 Happy/Paws 经验", description)
        self.assertIn("不是 App Workflow", body)
        self.assertIn("不强制", body)
        self.assertIn("历史经验", body)

        index = (HAPPY_EXPERIENCE / "references" / "INDEX.md").read_text(
            encoding="utf-8"
        )
        reference = (HAPPY_EXPERIENCE / "references" / "mobile-delivery.md").read_text(
            encoding="utf-8"
        )
        link = re.search(r"\[[^\]]+\]\(([^)]*mobile-delivery\.md)\)", index)
        self.assertIsNotNone(link)
        assert link is not None
        reference_path = HAPPY_EXPERIENCE / "references" / link.group(1)
        self.assertEqual(reference_path.resolve(), (HAPPY_EXPERIENCE / "references" / "mobile-delivery.md").resolve())
        self.assertTrue(reference_path.is_file())
        self.assertLessEqual(len(index.splitlines()), 80)

        index_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", index)
        reference_date = re.search(
            r"\*\*最近验证：\*\* (\d{4}-\d{2}-\d{2})", reference
        )
        self.assertTrue(index_dates)
        self.assertIsNotNone(reference_date)
        assert reference_date is not None
        self.assertEqual({index_dates[0]}, set(index_dates))
        self.assertEqual(index_dates[0], reference_date.group(1))
        date.fromisoformat(index_dates[0])

        repository = re.search(r"\*\*证据仓库：\*\* (https://github\.com/[^\s]+)", reference)
        revision = re.search(r"\*\*核验 revision：\*\* `([0-9a-f]{40})`", reference)
        self.assertIsNotNone(repository)
        self.assertIsNotNone(revision)
        assert repository is not None and revision is not None

        self.assertIn("## OTA 与重新构建是两条边界", reference)
        self.assertIn("## OTA 和真机是最终确认，不是基础 QA", reference)
        self.assertEqual(2, reference.count("**决策：**"))
        self.assertEqual(2, reference.count("**适用边界：**"))
        self.assertEqual(2, reference.count("**迁移到其他 App：**"))
        for invariant in ("JS 兼容", "原生依赖", "重新构建 App", "OTA 不替代"):
            self.assertIn(invariant, reference)

        evidence_paths = (
            "docs/getting-started.zh-CN.md",
            "packages/happy-app/app.config.js",
            "packages/happy-app/eas.json",
            "docs/research/2026-07-04-right-swipe-panel-retrospective.md",
        )
        for evidence_path in evidence_paths:
            self.assertIn(f"`{evidence_path}`", reference)
            stable_url = (
                f"{repository.group(1)}/blob/{revision.group(1)}/{evidence_path}"
            )
            self.assertIn(stable_url, reference)

        _, app_flow_body = load_skill(APP_FLOW)
        self.assertNotIn("happy-app-experience", app_flow_body)

    def test_happy_experience_local_memory_is_ignored_and_progressive(self) -> None:
        _, body = load_skill(HAPPY_EXPERIENCE)
        self.assert_progressive_local_memory(HAPPY_EXPERIENCE, body)

    def test_repository_docs_expose_both_skills(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        labs_readme = (REPO_ROOT / "labs" / "README.md").read_text(encoding="utf-8")
        self.assertIn("[happy-app-experience](./skills/happy-app-experience)", readme)
        self.assertIn("[app-flow](./labs/app-flow/app-flow)", readme)
        self.assertIn("j-skills link ./labs/app-flow/app-flow", labs_readme)
        self.assertIn(
            "j-skills install app-flow -g --env claude-code,codex", labs_readme
        )

    def test_memory_philosophy_uses_immutable_namespaced_records(self) -> None:
        local_memory = (
            REPO_ROOT / "docs" / "philosophy" / "references" / "local-memory.md"
        ).read_text(encoding="utf-8")
        memory_scoring = (
            REPO_ROOT / "docs" / "philosophy" / "references" / "memory-and-scoring.md"
        ).read_text(encoding="utf-8")
        combined = local_memory + "\n" + memory_scoring

        for phrase in (
            "maps/features/<repo-key>/<feature-key>.md",
            "32 KiB",
            "不可变",
            "supersedes",
            "superseded-by",
            "整个 `local/`",
            "只有 `app-flow`",
            "per-map lock",
            "每 10 秒",
            "30 秒",
            "fencing token",
            "持锁后重读",
            "最多 50 个",
            "pending-index",
            "scope",
            "status",
            "evidence",
            "created-at",
            "verified-at",
            "sensitivity",
        ):
            self.assertIn(phrase, combined)
        self.assertNotIn("更新原条目", combined)


if __name__ == "__main__":
    unittest.main()
