"""Reusable helpers for experiment data analysis.

Keep experiment-specific file names, settings, reporting, and plots in each
experiment script. This module only contains common data preparation and
calculations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


WATER_SPECIFIC_HEAT_J_KG_K = 4186.0


@dataclass(frozen=True)
class CoolingWindow:
    """A time window in which temperature falls between two thresholds."""

    start: pd.Timestamp
    end: pd.Timestamp

    @property
    def duration_s(self) -> float:
        return (self.end - self.start).total_seconds()


@dataclass(frozen=True)
class CalorimetryResult:
    """Energy and average power calculated from a temperature drop."""

    start_temp_c: float
    end_temp_c: float
    duration_s: float
    energy_j: float
    average_power_w: float

    @property
    def delta_temp_c(self) -> float:
        return self.start_temp_c - self.end_temp_c


def load_sensor_csv(
    path: str | Path,
    *,
    timestamp_col: str = "timestamp",
    index_timestamp: bool = False,
) -> pd.DataFrame:
    """Load a sensor CSV with consistent columns and chronological timestamps."""

    df = pd.read_csv(path)
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df.columns = [column.strip().replace("\\", "").lower() for column in df.columns]

    if timestamp_col not in df.columns:
        raise KeyError(f"Missing timestamp column {timestamp_col!r} in {path}")

    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    df = df.sort_values(timestamp_col).reset_index(drop=True)
    if index_timestamp:
        df = df.set_index(timestamp_col)
    return df


def elapsed_time(
    timestamps: pd.Series | pd.DatetimeIndex,
    *,
    unit: str = "s",
) -> pd.Series | np.ndarray:
    """Return elapsed time from the first timestamp in seconds or minutes."""

    elapsed = timestamps - timestamps[0]
    elapsed_s = (
        elapsed.dt.total_seconds()
        if isinstance(elapsed, pd.Series)
        else elapsed.total_seconds()
    )
    if unit == "s":
        return elapsed_s
    if unit == "min":
        return elapsed_s / 60.0
    raise ValueError("unit must be 's' or 'min'")


def find_cooling_window(
    temperature: pd.Series,
    start_temp_c: float,
    end_temp_c: float,
    *,
    use_last_crossing: bool = True,
) -> CoolingWindow | None:
    """Find a downward threshold-to-threshold window after the temperature peak.

    The last crossings are useful for logs containing rewarming or repeated
    passes. Set ``use_last_crossing=False`` for the first complete pass.
    """

    temperature = temperature.dropna().sort_index()
    if temperature.empty:
        return None
    if start_temp_c <= end_temp_c:
        raise ValueError("start_temp_c must be greater than end_temp_c")

    after_peak = temperature.loc[temperature.idxmax() :]
    starts = after_peak[
        (after_peak.shift(1) > start_temp_c) & (after_peak <= start_temp_c)
    ]
    if starts.empty:
        return None
    start = starts.index[-1] if use_last_crossing else starts.index[0]

    after_start = temperature.loc[start:]
    ends = after_start[
        (after_start.shift(1) > end_temp_c) & (after_start <= end_temp_c)
    ]
    if ends.empty:
        return None
    end = ends.index[-1] if use_last_crossing else ends.index[0]

    window = CoolingWindow(pd.Timestamp(start), pd.Timestamp(end))
    return window if window.duration_s > 0 else None


def find_plateau_cooling_window(
    temperature: pd.Series,
    *,
    plateau_minutes: float = 5.0,
    cooling_fraction: float = 0.98,
) -> tuple[CoolingWindow, float] | None:
    """Find cooling from the peak to a fraction of the final plateau drop."""

    temperature = temperature.dropna().sort_index()
    if temperature.empty:
        return None
    if not 0 < cooling_fraction <= 1:
        raise ValueError("cooling_fraction must be between 0 and 1")

    plateau_start = temperature.index[-1] - pd.Timedelta(minutes=plateau_minutes)
    plateau_temp_c = float(temperature.loc[plateau_start:].mean())
    peak = pd.Timestamp(temperature.idxmax())
    peak_temp_c = float(temperature.loc[peak])
    threshold_c = peak_temp_c - cooling_fraction * (peak_temp_c - plateau_temp_c)

    after_peak = temperature.loc[peak:]
    reached = after_peak[after_peak <= threshold_c]
    end = pd.Timestamp(reached.index[0] if len(reached) else after_peak.index[-1])
    window = CoolingWindow(peak, end)
    if window.duration_s <= 0:
        return None
    return window, plateau_temp_c


def tank_calorimetry(
    temperature: pd.Series,
    window: CoolingWindow,
    *,
    mass_kg: float,
    specific_heat_j_kg_k: float = WATER_SPECIFIC_HEAT_J_KG_K,
) -> CalorimetryResult:
    """Calculate energy removed and average cooling power from a tank."""

    period = temperature.loc[window.start : window.end].dropna()
    if len(period) < 2:
        raise ValueError("Cooling window contains fewer than two temperatures")

    start_temp_c = float(period.iloc[0])
    end_temp_c = float(period.iloc[-1])
    energy_j = mass_kg * specific_heat_j_kg_k * (start_temp_c - end_temp_c)
    return CalorimetryResult(
        start_temp_c=start_temp_c,
        end_temp_c=end_temp_c,
        duration_s=window.duration_s,
        energy_j=energy_j,
        average_power_w=energy_j / window.duration_s,
    )


def flow_power(
    flow_ml_per_s: pd.Series,
    inlet_temp_c: pd.Series,
    outlet_temp_c: pd.Series,
    *,
    specific_heat_j_kg_k: float = WATER_SPECIFIC_HEAT_J_KG_K,
) -> pd.Series:
    """Calculate water-side cooling power, assuming 1 ml water is 0.001 kg."""

    mass_flow_kg_s = flow_ml_per_s / 1000.0
    return mass_flow_kg_s * specific_heat_j_kg_k * (inlet_temp_c - outlet_temp_c)


def time_weighted_mean(
    values: pd.Series,
    timestamps: pd.Series,
    *,
    duration_s: float | None = None,
) -> float:
    """Average irregularly sampled values by trapezoidal time integration.

    Pass ``duration_s`` when the intended analysis window is wider than the
    span of valid samples (for example, when endpoint sensor values are NaN).
    """

    valid = pd.DataFrame({"value": values, "timestamp": timestamps}).dropna()
    if len(valid) < 2:
        raise ValueError("Need at least two valid samples")

    valid = valid.sort_values("timestamp")
    seconds = (valid["timestamp"] - valid["timestamp"].iloc[0]).dt.total_seconds()
    sample_duration_s = float(seconds.iloc[-1])
    averaging_duration_s = sample_duration_s if duration_s is None else duration_s
    if averaging_duration_s <= 0:
        raise ValueError("Timestamps must span a positive duration")
    y = valid["value"].to_numpy()
    x = seconds.to_numpy()
    integral = np.trapezoid(y, x) if hasattr(np, "trapezoid") else np.trapz(y, x)
    return float(integral / averaging_duration_s)


def rpm_to_flow_ml_min(
    rpm: pd.Series | np.ndarray | float,
    ml_per_min_per_rpm: float,
):
    """Convert commanded pump speed to an estimated volumetric flow."""

    return rpm * ml_per_min_per_rpm


def add_rolling_means(
    df: pd.DataFrame,
    columns: Iterable[str],
    window: str,
    *,
    suffix: str = "_avg",
) -> pd.DataFrame:
    """Return a copy with centered time-based rolling means added."""

    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("DataFrame must have a DatetimeIndex")

    result = df.copy()
    for column in columns:
        result[f"{column}{suffix}"] = result[column].rolling(window, center=True).mean()
    return result


def longest_true_block_start(mask: pd.Series):
    """Return the index at the start of the longest contiguous true block."""

    mask = mask.fillna(False).astype(bool)
    if not mask.any():
        return None
    block_ids = mask.ne(mask.shift()).cumsum()
    true_blocks = block_ids[mask]
    longest = true_blocks.value_counts().idxmax()
    return true_blocks.index[true_blocks == longest][0]
