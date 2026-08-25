import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "plugins" / "evaluators" / "skill-design-benchmark"
SKILL_FILE = SKILL_DIR / "SKILL.md"
RUBRIC_FILE = SKILL_DIR / "references" / "rubric.md"
SOURCES_FILE = SKILL_DIR / "references" / "source-basis.md"
FACTS_SCRIPT = SKILL_DIR / "scripts" / "collect_skill_facts.py"
PLUGIN_MANIFEST = ROOT / "plugins" / "evaluators" / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"


class SkillDesignBenchmarkContractTests(unittest.TestCase):
    def test_skill_is_lean_and_has_only_required_resources(self) -> None:
        self.assertTrue(SKILL_FILE.is_file(), "缺少 skill-design-benchmark/SKILL.md")
        self.assertTrue(RUBRIC_FILE.is_file(), "缺少 references/rubric.md")
        self.assertTrue(SOURCES_FILE.is_file(), "缺少 references/source-basis.md")
        self.assertTrue(FACTS_SCRIPT.is_file(), "缺少 scripts/collect_skill_facts.py")
        self.assertTrue((SKILL_DIR / "agents" / "openai.yaml").is_file())

        skill_lines = SKILL_FILE.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(skill_lines), 180, "SKILL.md 应保持为轻量入口地图")

        top_level_files = {
            path.relative_to(SKILL_DIR).as_posix()
            for path in SKILL_DIR.rglob("*")
            if path.is_file()
        }
        self.assertNotIn("README.md", top_level_files)
        self.assertNotIn("QUICK_REFERENCE.md", top_level_files)

    def test_rubric_has_eight_dimensions_and_weights_sum_to_100(self) -> None:
        self.assertTrue(RUBRIC_FILE.is_file(), "rubric 尚未实现")
        content = RUBRIC_FILE.read_text(encoding="utf-8")
        rows = re.findall(
            r"(?m)^\|\s*(D[1-8])\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|$",
            content,
        )

        self.assertEqual([row[0] for row in rows], [f"D{i}" for i in range(1, 9)])
        self.assertEqual(sum(int(row[2]) for row in rows), 100)
        self.assertEqual(sum(int(row[2]) for row in rows[:7]), 85)
        self.assertEqual(int(rows[7][2]), 15)
        for dimension in range(1, 9):
            self.assertIn(f"### D{dimension}", content)

    def test_every_dimension_has_traceable_source_ids(self) -> None:
        self.assertTrue(RUBRIC_FILE.is_file(), "rubric 尚未实现")
        self.assertTrue(SOURCES_FILE.is_file(), "source basis 尚未实现")
        rubric = RUBRIC_FILE.read_text(encoding="utf-8")
        sources = SOURCES_FILE.read_text(encoding="utf-8")

        rows = re.findall(
            r"(?m)^\|\s*(D[1-8])\s*\|\s*[^|]+\|\s*\d+\s*\|\s*([^|]+?)\s*\|$",
            rubric,
        )
        defined_ids = set(re.findall(r"(?m)^##\s+([GW]-[A-Z0-9-]+)\s*$", sources))

        self.assertGreaterEqual(len(defined_ids), 10)
        source_sections = {
            match.group(1): match.group(2)
            for match in re.finditer(
                r"(?ms)^##\s+([GW]-[A-Z0-9-]+)\s*$\n(.*?)(?=^##\s+|\Z)",
                sources,
            )
        }
        for source_id, section in source_sections.items():
            for field in ("**证据**", "**观察**", "**推导**", "**边界**"):
                self.assertIn(field, section, f"{source_id} 缺少来源字段 {field}")
        for dimension, raw_ids in rows:
            ids = {item.strip() for item in raw_ids.split(",") if item.strip()}
            self.assertTrue(ids, f"{dimension} 没有来源依据")
            self.assertTrue(ids <= defined_ids, f"{dimension} 引用了未定义来源：{ids - defined_ids}")

    def test_anti_inflation_and_proportionality_rules_are_explicit(self) -> None:
        self.assertTrue(SKILL_FILE.is_file(), "SKILL.md 尚未实现")
        content = SKILL_FILE.read_text(encoding="utf-8")
        required_contracts = (
            "资源数量本身不加分",
            "不适用的复杂机制不扣分",
            "简单 Skill 可以获得高分",
            "100 分不得四舍五入",
            "满分必须包含运行证据",
            "默认只读",
            "每个分数必须附证据",
        )
        for contract in required_contracts:
            self.assertIn(contract, content)

    def test_fact_collector_reports_resources_links_and_excludes_archived(self) -> None:
        self.assertTrue(FACTS_SCRIPT.is_file(), "facts collector 尚未实现")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = root / "skills" / "demo-skill"
            active.mkdir(parents=True)
            (active / "references").mkdir()
            (active / "scripts").mkdir()
            (active / "references" / "guide.md").write_text("# Guide\n", encoding="utf-8")
            (active / "references" / "with space.md").write_text(
                "# Spaced path\n", encoding="utf-8"
            )
            (active / "scripts" / "run.py").write_text("print('ok')\n", encoding="utf-8")
            (active / "SKILL.md").write_text(
                "---\n"
                "name: demo-skill\n"
                "description: Demo skill\n"
                "---\n\n"
                "# Demo\n\n"
                "[Guide](references/guide.md)\n"
                "[Spaced](<references/with space.md>)\n"
                "[Missing](references/missing.md)\n",
                encoding="utf-8",
            )
            archived = root / "archived" / "old-skill"
            archived.mkdir(parents=True)
            (archived / "SKILL.md").write_text("# ignored\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(FACTS_SCRIPT), str(root), "--format", "json"],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["skills"]), 1)
        facts = payload["skills"][0]
        self.assertEqual(facts["name"], "demo-skill")
        self.assertEqual(facts["non_empty_line_count"], 8)
        self.assertEqual(facts["resources"]["references"], 2)
        self.assertEqual(facts["resources"]["scripts"], 1)
        self.assertEqual(facts["local_links"], 3)
        self.assertEqual(facts["missing_local_links"], ["references/missing.md"])

    def test_evaluators_plugin_registers_the_new_benchmark(self) -> None:
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        marketplace_entry = next(
            item for item in marketplace["plugins"] if item["name"] == "evaluators"
        )

        self.assertEqual(manifest["version"], "1.1.0")
        self.assertIn("./skill-design-benchmark/", manifest["skills"])
        self.assertEqual(marketplace_entry["version"], manifest["version"])
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertRegex(
            readme,
            r"\| \[evaluators\].*\| 1\.1\.0 .*harness-benchmark, skill-design-benchmark \|",
        )


if __name__ == "__main__":
    unittest.main()
