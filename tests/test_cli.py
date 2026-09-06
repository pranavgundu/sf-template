import contextlib
import csv
import hashlib
import io
import json
import subprocess
import sys
import tomllib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from sf_template.cli import ROOT, TRACKS, analyze, check_project, init_project, main, read_measurements
from sf_template.presets import dependencies


class ProjectTests(unittest.TestCase):
    def test_no_arguments_opens_setup_and_selects_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "ml"
            answers = ["My ML project", str(destination), "ml", "torch", "1,2"]
            with patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main([]), 0)
            metadata = json.loads((destination / "project.json").read_text())
            self.assertEqual(metadata["framework"], "torch")
            self.assertEqual(metadata["addons"], ["notebooks", "tracking"])
            self.assertIn("Selected packages:", output.getvalue())

    def test_enter_accepts_defaults_and_invalid_choices_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "science"
            with patch("builtins.input", side_effect=["", "unknown", "", "99", ""]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["init", str(destination)]), 0)
            metadata = json.loads((destination / "project.json").read_text())
            self.assertEqual(metadata["title"], "My research")
            self.assertEqual(metadata["track"], "science")
            self.assertEqual(metadata["addons"], [])

    def test_setup_can_cancel_without_creating_files(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "cancelled"
            for interruption in (EOFError, KeyboardInterrupt):
                with patch("builtins.input", side_effect=interruption), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["init", str(destination)]), 130)
                self.assertFalse(destination.exists())

    def test_noninteractive_defaults_never_prompt(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "defaults"
            with patch("builtins.input", side_effect=AssertionError("Unexpected prompt")), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["init", str(destination), "--no-input"]), 0)
            self.assertEqual(json.loads((destination / "project.json").read_text())["track"], "science")

    def test_research_choice_changes_written_dependencies(self):
        expected = {
            "science": {"numpy", "scipy", "matplotlib"},
            "data-analytics": {"numpy", "scipy", "matplotlib", "pandas", "seaborn", "statsmodels", "openpyxl"},
            "literature-review": {"pandas", "bibtexparser"},
            "computational": {"numpy", "scipy", "matplotlib", "sympy", "networkx"},
        }
        with tempfile.TemporaryDirectory() as folder:
            for starter, names in expected.items():
                destination = Path(folder) / starter
                with patch("builtins.input", side_effect=[starter, ""]), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["init", str(destination), "--title", "Test"]), 0)
                project = tomllib.loads((destination / "pyproject.toml").read_text())
                actual = {package.split(">=")[0] for package in project["project"]["dependencies"]}
                self.assertEqual(actual, names)

    def test_each_starter_is_runnable_without_worksheets(self):
        with tempfile.TemporaryDirectory() as folder:
            for track in TRACKS:
                with self.subTest(track=track):
                    destination = Path(folder) / track
                    init_project(destination, "Bridge study", track)
                    self.assertFalse(list(destination.rglob("*.md")))
                    self.assertFalse((destination / "communication").exists())
                    for name in ("papers", "notes", "general", "notebooks"):
                        self.assertTrue((destination / name).is_dir())
                    self.assertEqual(check_project(destination), [])
                    self.assertEqual(json.loads((destination / "project.json").read_text())["track"], track)
                    metadata = tomllib.loads((destination / "pyproject.toml").read_text())
                    self.assertEqual(metadata["project"]["name"], "bridge-study")
                    expected, _ = dependencies(track)
                    self.assertEqual(metadata["project"]["dependencies"], expected)
                    result = subprocess.run(
                        [sys.executable, "-m", "project.main", "--output", "results/test"],
                        cwd=destination, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue((destination / "results/test/run.json").is_file())
                    tests = subprocess.run(
                        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                        cwd=destination, capture_output=True, text=True,
                    )
                    self.assertEqual(tests.returncode, 0, tests.stderr)
                    with self.assertRaises(ValueError):
                        init_project(destination, "Replacement", track)
                    self.assertEqual(json.loads((destination / "project.json").read_text())["title"], "Bridge study")

    def test_frameworks_and_addons_are_selective(self):
        with tempfile.TemporaryDirectory() as folder:
            for framework in ("sklearn", "torch", "jax"):
                destination = Path(folder) / framework
                init_project(destination, "ML", "ml", framework, ["notebooks", "tracking"])
                metadata = tomllib.loads((destination / "pyproject.toml").read_text())
                packages = metadata["project"]["dependencies"]
                self.assertTrue(any(p.startswith("jupyterlab") for p in packages))
                self.assertTrue(any(p.startswith("wandb") for p in packages))
                self.assertEqual(any(p.startswith("torch>") for p in packages), framework == "torch")
                self.assertEqual(any(p.startswith("jax>") for p in packages), framework == "jax")
                self.assertEqual(any(p.startswith("scikit-learn>") for p in packages), framework == "sklearn")
                self.assertEqual(len(packages), len(set(packages)))

    def test_bad_framework_does_not_create_project(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "bad"
            with self.assertRaises(ValueError):
                init_project(destination, "Bad", "science", "torch")
            self.assertFalse(destination.exists())

    def test_check_reports_missing_files_and_bad_config(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIn("Missing: pyproject.toml", check_project(folder))
            destination = Path(folder) / "project"
            init_project(destination, "Test", "general")
            (destination / "configs/experiment.toml").write_text("invalid = [")
            self.assertTrue(any("Invalid TOML" in item for item in check_project(destination)))

    def test_starter_discovery_and_alias(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["starters"]), 0)
        for track in TRACKS:
            self.assertIn(track, output.getvalue())
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            destination = Path(folder) / "ml"
            self.assertEqual(main(["init", str(destination), "--title", "ML", "--starter", "ml", "--framework", "torch", "--add", "config"]), 0)
            self.assertEqual(json.loads((destination / "project.json").read_text())["framework"], "torch")

    def test_cli_reports_missing_input_without_traceback(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(io.StringIO()) as err:
            result = main(["analyze", str(Path(folder) / "absent.csv"), "--output", str(Path(folder) / "out")])
            self.assertEqual(result, 2)
            self.assertIn("Error:", err.getvalue())

class MeasurementTests(unittest.TestCase):
    def parse(self, text, replicates="error"):
        return read_measurements(text.encode("utf-8"), replicates)

    def test_independent_summaries(self):
        summary, unit, rows, count = self.parse("unit_id,group,value,unit\na,A,1,cm\nb,A,3,cm\nc,B,5,cm\n")
        self.assertEqual((unit, rows, count), ("cm", 3, 3))
        self.assertEqual(summary[0]["mean"], 2)
        self.assertAlmostEqual(summary[0]["sd"], 2 ** 0.5)
        self.assertIsNone(summary[1]["sd"])

    def test_repeated_readings_are_averaged_per_unit_not_pooled(self):
        data = "unit_id,group,value\na,A,0\na,A,2\na,A,4\nb,A,10\n"
        with self.assertRaisesRegex(ValueError, "repeated unit"):
            self.parse(data)
        summary, _, rows, units = self.parse(data, "mean")
        self.assertEqual((rows, units), (4, 2))
        self.assertEqual(summary[0]["n"], 2)
        self.assertEqual(summary[0]["mean"], 6)

    def test_invalid_data_rejected(self):
        cases = [
            "group,value\nA,1\n",
            "unit_id,group,value,value\na,A,1,2\n",
            "unit_id,group,value\n",
            "unit_id,group,value\n,A,1\n",
            "unit_id,group,value\na,,1\n",
            "unit_id,group,value\na,A,\n",
            "unit_id,group,value\na,A,NaN\n",
            "unit_id,group,value\na,A,inf\n",
            "unit_id,group,value\na,A,1,extra\n",
            "unit_id,group,value\na,A\n",
            "unit_id,group,value,unit\na,A,1,g\nb,A,2,kg\n",
            "unit_id,group,value,unit\na,A,1,g\nb,A,2,\n",
            "unit_id,group,value\na,A,1\na,B,2\n",
        ]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.parse(data, "mean")

    def test_bom_and_quoted_group(self):
        summary, _, _, _ = self.parse('\ufeffunit_id,group,value\na,"A, B",-3\n')
        self.assertEqual(summary[0]["group"], "A, B")

    def test_end_to_end_output_provenance_and_no_overwrite(self):
        source = ROOT / "examples/paper-bridges/measurements.csv"
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "run"
            summary = analyze(source, out)
            self.assertEqual([row["mean"] for row in summary], [330, 110])
            self.assertAlmostEqual(summary[0]["sd"], 15.811388300841896)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["input_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(manifest["independent_units"], 10)
            ET.parse(out / "chart.svg")
            with (out / "summary.csv").open(newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 2)
            with self.assertRaises(ValueError):
                analyze(source, out)
            second = Path(folder) / "run-2"
            analyze(source, second)
            self.assertEqual((out / "summary.csv").read_bytes(), (second / "summary.csv").read_bytes())
            self.assertEqual((out / "chart.svg").read_bytes(), (second / "chart.svg").read_bytes())

    def test_chart_handles_equal_negative_values_and_escapes_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.csv"
            source.write_text('unit_id,group,value,unit\na,<script>&,-2,m\nb,<script>&,-2,m\n')
            out = Path(folder) / "out"
            analyze(source, out)
            chart = (out / "chart.svg").read_text()
            ET.fromstring(chart)
            self.assertNotIn("<script>", chart)
            self.assertIn("&lt;script&gt;&amp;", chart)

    def test_bad_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.csv"
            source.write_text("unit_id,group,value\na,A,nan\n")
            output = Path(folder) / "out"
            with self.assertRaises(ValueError):
                analyze(source, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
