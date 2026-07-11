import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
J_SKILLS_DOC = (
    ROOT / "plugins/skills-management/skills/j-skills/SKILL.md"
).read_text(encoding="utf-8")
LINK_ALL_DOC = (
    ROOT / "plugins/skills-management/skills/link-all-skills/SKILL.md"
).read_text(encoding="utf-8")
LEGACY_LINK_SCRIPT = (
    ROOT / "plugins/skills-management/skills/link-all-skills/link-all.sh"
)


class JSkillsDocumentationContractTests(unittest.TestCase):
    def test_documents_only_supported_options(self) -> None:
        combined = J_SKILLS_DOC + "\n" + LINK_ALL_DOC
        for unsupported in (
            "--all-env",
            "--doctor",
            "--force",
            "link <skill-dir> -y",
            "link /path/to/skills --all",
        ):
            with self.subTest(option=unsupported):
                self.assertNotIn(unsupported, combined)

    def test_uses_the_installed_package_name_and_real_bulk_entrypoint(self) -> None:
        self.assertIn("npm install -g @wangjs-jacky/j-skills", J_SKILLS_DOC)
        self.assertIn("./install.sh", LINK_ALL_DOC)
        self.assertNotIn("./link-all.sh", LINK_ALL_DOC)

    def test_bulk_workflow_excludes_archived_and_does_not_overwrite_conflicts(self) -> None:
        self.assertIn("archived/", LINK_ALL_DOC)
        self.assertIn("链接冲突", LINK_ALL_DOC)
        self.assertNotIn("会被覆盖指向当前项目", LINK_ALL_DOC)

    def test_removed_legacy_script_cannot_call_unsupported_options(self) -> None:
        self.assertFalse(LEGACY_LINK_SCRIPT.exists())


if __name__ == "__main__":
    unittest.main()
