import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from Experiments.experiment_tools import (
    add_rolling_means,
    find_cooling_window,
    find_plateau_cooling_window,
    flow_power,
    load_sensor_csv,
    longest_true_block_start,
    tank_calorimetry,
    time_weighted_mean,
)


class ExperimentToolsTests(unittest.TestCase):
    def test_load_sensor_csv_normalizes_and_sorts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "log.csv"
            pd.DataFrame(
                {
                    " Timestamp\\": ["2026-01-01 00:00:01", "2026-01-01 00:00:00"],
                    "Tank_C": [31.0, 32.0],
                }
            ).to_csv(path, index=False)

            result = load_sensor_csv(path)

        self.assertEqual(list(result.columns), ["timestamp", "tank_c"])
        self.assertEqual(result["tank_c"].tolist(), [32.0, 31.0])

    def test_find_window_and_tank_calorimetry(self):
        index = pd.date_range("2026-01-01", periods=7, freq="10s")
        temperature = pd.Series([36.0, 38.0, 37.5, 36.5, 34.0, 31.5, 30.0], index=index)

        window = find_cooling_window(temperature, 37.0, 32.0)

        self.assertIsNotNone(window)
        assert window is not None
        self.assertEqual(window.start, index[3])
        self.assertEqual(window.end, index[5])
        result = tank_calorimetry(
            temperature, window, mass_kg=1.0, specific_heat_j_kg_k=100.0
        )
        self.assertAlmostEqual(result.energy_j, 500.0)
        self.assertAlmostEqual(result.average_power_w, 25.0)

    def test_flow_power_and_time_weighted_mean(self):
        timestamps = pd.Series(pd.date_range("2026-01-01", periods=2, freq="2s"))
        power = flow_power(
            pd.Series([1.0, 1.0]),
            pd.Series([12.0, 14.0]),
            pd.Series([10.0, 10.0]),
            specific_heat_j_kg_k=1000.0,
        )

        np.testing.assert_allclose(power, [2.0, 4.0])
        self.assertAlmostEqual(time_weighted_mean(power, timestamps), 3.0)
        self.assertAlmostEqual(
            time_weighted_mean(power, timestamps, duration_s=4.0), 1.5
        )

    def test_find_plateau_cooling_window(self):
        index = pd.date_range("2026-01-01", periods=7, freq="1min")
        temperature = pd.Series([35.0, 40.0, 38.0, 35.0, 32.0, 30.0, 30.0], index=index)

        result = find_plateau_cooling_window(
            temperature, plateau_minutes=1, cooling_fraction=0.8
        )

        self.assertIsNotNone(result)
        assert result is not None
        window, plateau_temp = result
        self.assertEqual(window.start, index[1])
        self.assertEqual(window.end, index[4])
        self.assertEqual(plateau_temp, 30.0)

    def test_rolling_means_and_longest_block(self):
        index = pd.date_range("2026-01-01", periods=5, freq="1s")
        df = pd.DataFrame({"pressure": [1, 2, 3, 4, 5]}, index=index)

        result = add_rolling_means(df, ["pressure"], "3s")

        self.assertIn("pressure_avg", result)
        mask = pd.Series([False, True, False, True, True, True, False])
        self.assertEqual(longest_true_block_start(mask), 3)


if __name__ == "__main__":
    unittest.main()
