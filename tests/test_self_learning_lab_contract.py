import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = REPO_ROOT / "labs" / "self-learning"
OLD_NAME = "tutorial-to-hyperframes-demo"


def skill_name(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    frontmatter = text.split("---\n", 2)[1]
    return str(yaml.safe_load(frontmatter)["name"])


class SelfLearningLabContractTests(unittest.TestCase):
    def test_main_and_hyperframes_skill_names_match_directories(self) -> None:
        main = LAB_ROOT / "self-learning" / "SKILL.md"
        hyperframes = LAB_ROOT / "self-learning-hyperframes" / "SKILL.md"
        self.assertEqual(skill_name(main), "self-learning")
        self.assertEqual(skill_name(hyperframes), "self-learning-hyperframes")
        self.assertFalse((REPO_ROOT / "skills" / OLD_NAME).exists())

    def test_main_skill_keeps_workflow_dynamic(self) -> None:
        main_root = LAB_ROOT / "self-learning"
        text = (main_root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("固定意图，动态路径", text)
        self.assertIn("简单任务", text)
        self.assertIn("人工检查门", text)
        self.assertFalse((main_root / "workflow.yaml").exists())

    def test_public_surfaces_use_only_new_names(self) -> None:
        public_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "labs" / "README.md",
            LAB_ROOT / "README.md",
            LAB_ROOT / "self-learning" / "SKILL.md",
            LAB_ROOT / "self-learning-hyperframes" / "SKILL.md",
            LAB_ROOT / "self-learning-hyperframes" / "agents" / "openai.yaml",
        ]
        for path in public_files:
            with self.subTest(path=path):
                self.assertNotIn(OLD_NAME, path.read_text(encoding="utf-8"))

    def test_readmes_classify_self_learning_as_lab(self) -> None:
        root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        labs_readme = (REPO_ROOT / "labs" / "README.md").read_text(encoding="utf-8")
        labs_section = root_readme.split("## Skill Labs（预览版）", 1)[1].split(
            "\n## ", 1
        )[0]
        self.assertIn("[self-learning](./labs/self-learning)", labs_section)
        self.assertIn("[`self-learning`](./self-learning/)", labs_readme)
        independent_section = root_readme.split("## 独立 Skills", 1)[1].split(
            "## Harness Ops Skills", 1
        )[0]
        self.assertNotIn(OLD_NAME, independent_section)

    def test_labs_remain_outside_batch_install(self) -> None:
        install_script = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertNotIn('"$REPO_DIR/labs"', install_script)

    def test_philosophy_links_runtime_workflows(self) -> None:
        philosophy = (REPO_ROOT / "docs" / "philosophy" / "README.md").read_text(
            encoding="utf-8"
        )
        runtime_workflows = (
            REPO_ROOT / "docs" / "philosophy" / "references" / "runtime-workflows.md"
        ).read_text(encoding="utf-8")
        yaml_contracts = (
            REPO_ROOT / "docs" / "philosophy" / "references" / "yaml-contracts.md"
        ).read_text(encoding="utf-8")
        self.assertIn("固定意图，动态路径", philosophy)
        self.assertIn("references/runtime-workflows.md", philosophy)
        self.assertIn("用户指定的顺序", runtime_workflows)
        self.assertIn("未受硬约束的执行顺序", runtime_workflows)
        self.assertIn("开放任务", yaml_contracts)
        self.assertIn("Markdown", yaml_contracts)


if __name__ == "__main__":
    unittest.main()
