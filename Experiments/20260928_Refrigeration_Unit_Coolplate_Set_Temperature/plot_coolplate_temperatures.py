"""Plot cool-plate temperatures, set temperature, and real compressor-on time.

Reads every CSV in raw_data/ and writes one PNG per log to output_data/.

The logged compressor_cooling flag is the cooling command. After each real
off, the compressor stays off for 60 s even if the command returns. Command
pulses shorter than 2 s are ignored (a 0.4 s blip at the start of the first
log is not a compressor start).

Single-sample temperature spikes from poor grounding are replaced with a
short rolling median. Raw logs are not rewritten.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import elapsed_time, load_sensor_csv

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

COMPRESSOR_OFF_PAUSE_S = 60.0
MIN_COMMAND_PULSE_S = 2.0
SPIKE_WINDOW = 5
SPIKE_THRESHOLD_C = 0.5
# Refrigeration set / off temperature is not logged. It is taken from the
# filename, e.g. 20260928_104911_sensors_set_-1C.csv. set_temperature_c in
# the CSV is the controller setpoint (32 °C here), not this value.
SET_TEMPERATURE_RE = re.compile(r"set_(-?\d+(?:\.\d+)?)C", re.IGNORECASE)

# Same hue for a plate and its backup sensor. Darker = plate, lighter = backup.
TEMP_SERIES = (
    ("plate_1_c", "Cool plate 1", "#08519c", "-"),
    ("plate_1b_c", "Cool plate 1 backup", "#6baed6", "--"),
    ("plate_2_c", "Cool plate 2", "#d94801", "-"),
    ("plate_2b_c", "Cool plate 2 backup", "#fdae6b", "--"),
)
# Archived logs used the old backup headers.
COLUMN_ALIASES = {
    "ice_water_c": "plate_1b_c",
    "cool_plate_backup_sensor_1_c": "plate_1b_c",
    "hot_bath2_c": "plate_2b_c",
    "cool_plate_backup_sensor_2_c": "plate_2b_c",
}


def _output_path(csv_path: Path) -> Path:
    return OUTPUT_DATA / f"coolplate_temperatures_{csv_path.stem}.png"


def set_temperature_c_from_name(csv_path: Path) -> float | None:
    match = SET_TEMPERATURE_RE.search(csv_path.stem)
    if match is None:
        print(f"  no set temperature in {csv_path.name}; expected set_<value>C")
        return None
    return float(match.group(1))


def despike(series: pd.Series) -> pd.Series:
    """Replace single-sample grounding spikes; leave real ramps alone."""

    median = series.rolling(SPIKE_WINDOW, center=True, min_periods=1).median()
    cleaned = series.copy()
    spike = (series - median).abs() > SPIKE_THRESHOLD_C
    cleaned.loc[spike] = median.loc[spike]
    return cleaned


def _debounce_command(t_s: np.ndarray, command: np.ndarray) -> np.ndarray:
    """Drop command runs shorter than MIN_COMMAND_PULSE_S."""

    command = np.asarray(command, dtype=bool)
    if len(command) == 0:
        return command
    out = command.copy()
    start = 0
    for i in range(1, len(command) + 1):
        if i == len(command) or command[i] != command[start]:
            duration_s = float(t_s[i - 1] - t_s[start])
            if duration_s < MIN_COMMAND_PULSE_S and start > 0:
                out[start:i] = out[start - 1]
            start = i
    return out


def compressor_really_on(t_s: np.ndarray, command: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (really_on, debounced_command).

    really_on follows the cooling command, except the compressor cannot
    restart until COMPRESSOR_OFF_PAUSE_S after it turns off.
    """

    cmd = _debounce_command(t_s, command)
    really = np.zeros(len(cmd), dtype=bool)
    on = False
    lockout_until_s = -np.inf
    for i, (t, cooling) in enumerate(zip(t_s, cmd)):
        if on and not cooling:
            on = False
            lockout_until_s = float(t) + COMPRESSOR_OFF_PAUSE_S
        elif (not on) and cooling and float(t) >= lockout_until_s:
            on = True
        really[i] = on
    return really, cmd


def _on_intervals_min(t_min: np.ndarray, on: np.ndarray) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    start = None
    for i, is_on in enumerate(on):
        if is_on and start is None:
            start = float(t_min[i])
        elif not is_on and start is not None:
            intervals.append((start, float(t_min[i])))
            start = None
    if start is not None:
        intervals.append((start, float(t_min[-1])))
    return intervals


def plot_log(csv_path: Path) -> Path:
    df = load_sensor_csv(csv_path)
    df = df.rename(columns=COLUMN_ALIASES)
    t_s = np.asarray(elapsed_time(df["timestamp"], unit="s"), dtype=float)
    t_min = t_s / 60.0

    command = df["compressor_cooling"].astype(int).to_numpy() == 1
    really_on, debounced = compressor_really_on(t_s, command)

    fig, (ax_temp, ax_comp) = plt.subplots(
        2,
        1,
        sharex=True,
        figsize=(11, 7),
        gridspec_kw={"height_ratios": [3, 1]},
    )

    ax_temp.fill_between(
        t_min,
        0,
        1,
        where=really_on,
        transform=ax_temp.get_xaxis_transform(),
        step="post",
        color="0.75",
        alpha=0.55,
        label="Compressor on",
        linewidth=0,
    )

    for column, label, color, linestyle in TEMP_SERIES:
        if column not in df.columns:
            continue
        cleaned = despike(df[column])
        n_spikes = int(((df[column] - cleaned).abs() > 0).sum())
        print(f"  {label}: removed {n_spikes} spike samples")
        ax_temp.plot(
            t_min,
            cleaned,
            color=color,
            linestyle=linestyle,
            linewidth=1.6,
            label=label,
        )

    set_temperature_c = set_temperature_c_from_name(csv_path)
    if set_temperature_c is not None:
        ax_temp.axhline(
            set_temperature_c,
            color="black",
            linestyle="--",
            linewidth=1.2,
            label=f"Set temperature ({set_temperature_c:.0f} °C)",
        )

    ax_temp.set_ylabel("Temperature (°C)")
    ax_temp.set_title(csv_path.name)
    ax_temp.grid(True, alpha=0.3)
    ax_temp.legend(loc="best", fontsize=8)

    ax_comp.step(
        t_min,
        debounced.astype(float),
        where="post",
        color="0.55",
        linewidth=1.4,
        label="Cooling command",
    )
    ax_comp.fill_between(
        t_min,
        0,
        1,
        where=really_on,
        step="post",
        color="0.45",
        alpha=0.35,
        label="Compressor on",
        linewidth=0,
    )
    ax_comp.set_ylim(-0.05, 1.25)
    ax_comp.set_yticks([0, 1])
    ax_comp.set_yticklabels(["off", "on"])
    ax_comp.set_ylabel("Compressor")
    ax_comp.set_xlabel("Time from start (min)")
    ax_comp.grid(True, alpha=0.3)
    ax_comp.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    OUTPUT_DATA.mkdir(exist_ok=True)
    out = _output_path(csv_path)
    fig.savefig(out, dpi=150)
    plt.close(fig)

    print(f"Saved {out}")
    for start_min, end_min in _on_intervals_min(t_min, really_on):
        print(f"  compressor on {start_min:.2f}–{end_min:.2f} min")
    return out


def main() -> None:
    logs = sorted(RAW_DATA.glob("*.csv"))
    if not logs:
        print(f"No input files yet in {RAW_DATA}")
        return
    for csv_path in logs:
        print(csv_path.name)
        plot_log(csv_path)


if __name__ == "__main__":
    main()
