import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from materialize_yaml import materialize, strip_yaml_comment


class MaterializeYamlTests(unittest.TestCase):
    def test_materializes_repository_example(self):
        root = Path(__file__).resolve().parent.parent
        actual = materialize(root / "root.yaml", root, ())
        expected = (root / "materialized.yaml").read_text(encoding="utf-8")
        self.assertEqual(actual, expected)

    def test_resolves_include_relative_to_root_dir(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "root.yaml").write_text(
                "parent:\n  !include: shared.yaml\n",
                encoding="utf-8",
            )
            (tmp_path / "nested").mkdir()
            (tmp_path / "nested" / "child.yaml").write_text(
                "!include: ../root.yaml\n",
                encoding="utf-8",
            )
            (tmp_path / "shared.yaml").write_text("value: 1\n", encoding="utf-8")

            actual = materialize(tmp_path / "nested" / "child.yaml", tmp_path, ())

            self.assertEqual(actual, "parent:\n  value: 1\n")

    def test_preserves_indentation_for_nested_include(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "root.yaml").write_text(
                "top:\n  !include: child.yaml\n",
                encoding="utf-8",
            )
            (tmp_path / "child.yaml").write_text("a: 1\nb: 2\n", encoding="utf-8")

            actual = materialize(tmp_path / "root.yaml", tmp_path, ())

            self.assertEqual(actual, "top:\n  a: 1\n  b: 2\n")

    def test_preserves_blank_lines_inside_included_content(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "root.yaml").write_text(
                "top:\n  !include: child.yaml\n",
                encoding="utf-8",
            )
            (tmp_path / "child.yaml").write_text("a: 1\n\n# spacer comment\nb: 2\n", encoding="utf-8")

            actual = materialize(tmp_path / "root.yaml", tmp_path, ())

            self.assertEqual(actual, "top:\n  a: 1\n\n  b: 2\n")

    def test_does_not_expand_include_inside_block_scalar(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "root.yaml").write_text(
                "script: |\n  !include: child.yaml\noutside:\n  !include: child.yaml\n",
                encoding="utf-8",
            )
            (tmp_path / "child.yaml").write_text("expanded: true\n", encoding="utf-8")

            actual = materialize(tmp_path / "root.yaml", tmp_path, ())

            self.assertEqual(
                actual,
                "script: |\n  !include: child.yaml\noutside:\n  expanded: true\n",
            )

    def test_detects_include_cycle(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "a.yaml").write_text("!include: b.yaml\n", encoding="utf-8")
            (tmp_path / "b.yaml").write_text("!include: a.yaml\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "include cycle detected"):
                materialize(tmp_path / "a.yaml", tmp_path, ())

    def test_raises_for_missing_include(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "root.yaml").write_text("!include: missing.yaml\n", encoding="utf-8")

            with self.assertRaisesRegex(FileNotFoundError, "include target 'missing.yaml' not found"):
                materialize(tmp_path / "root.yaml", tmp_path, ())

    def test_glob_include_is_sorted(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "root.yaml").write_text("!include: parts/*.yaml\n", encoding="utf-8")
            (tmp_path / "parts").mkdir()
            (tmp_path / "parts" / "b.yaml").write_text("b: 2\n", encoding="utf-8")
            (tmp_path / "parts" / "a.yaml").write_text("a: 1\n", encoding="utf-8")

            actual = materialize(tmp_path / "root.yaml", tmp_path, ())

            self.assertEqual(actual, "a: 1\nb: 2\n")

    def test_strip_yaml_comment_keeps_hash_inside_quotes(self):
        self.assertEqual(strip_yaml_comment('key: "va#lue" # comment\n'), 'key: "va#lue"\n')
        self.assertEqual(strip_yaml_comment("key: 'va#lue' # comment\n"), "key: 'va#lue'\n")
        self.assertEqual(strip_yaml_comment("plain: value # comment\n"), "plain: value\n")

    def test_cli_writes_output_file(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_path = tmp_path / "root.yaml"
            output_path = tmp_path / "out.yaml"
            child_path = tmp_path / "child.yaml"
            input_path.write_text("!include: child.yaml\n", encoding="utf-8")
            child_path.write_text("answer: 42\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "materialize_yaml.py", str(input_path), "-o", str(output_path)],
                cwd=Path(__file__).resolve().parent.parent,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "answer: 42\n")
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
