import tempfile
from pathlib import Path
import unittest

from project.analysis import read_measurements
from project.main import ROOT, load_config, run


class ResearchTests(unittest.TestCase):
    def test_independent_unit_mean(self):
        rows, _, _, count = read_measurements(b"unit_id,group,value\na,A,2\nb,A,4\n", "error")
        self.assertEqual(count, 2)
        self.assertEqual(rows[0]["mean"], 3)

    def test_repeated_readings_do_not_count_as_independent_units(self):
        data = b"unit_id,group,value\na,A,0\na,A,2\nb,A,9\n"
        with self.assertRaises(ValueError):
            read_measurements(data, "error")
        rows, _, _, count = read_measurements(data, "mean")
        self.assertEqual(count, 2)
        self.assertEqual(rows[0]["mean"], 5)

    def test_starter_config_is_valid(self):
        load_config(ROOT / "configs/experiment.toml")

    def test_run_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                run(ROOT / "configs/experiment.toml", Path(folder))


if __name__ == "__main__":
    unittest.main()
