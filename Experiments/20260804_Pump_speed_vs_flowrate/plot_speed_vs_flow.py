"""Plot pump set speed (RPM) vs gravimetric flow rate (ml/min).

Reads raw_data/gravimetric_runs.csv (mass collected over a timed hold),
converts mass → flow assuming water density, fits a line through the origin
and free intercept, and writes output_data/pump_speed_vs_flowrate.png.
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import LEGACY_ML_PER_MIN_PER_RPM, ML_PER_MIN_PER_RPM

HERE = Path(__file__).resolve().parent
RAW_CSV = HERE / "raw_data" / "gravimetric_runs.csv"
OUTPUT_DATA = HERE / "output_data"
OUTPUT_PNG = OUTPUT_DATA / "pump_speed_vs_flowrate.png"

# Water density [g/ml] at ~20 °C; override if using a different fluid.
WATER_DENSITY_G_PER_ML = 1.0
# Prior (2026-06-22) calibration for overlay.
PRIOR_ML_PER_MIN_PER_RPM = LEGACY_ML_PER_MIN_PER_RPM
# Adopted repo constant (mean Q/RPM on 2 min holds ≤ 180 rpm).
ADOPTED_ML_PER_MIN_PER_RPM = ML_PER_MIN_PER_RPM


def load_runs(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"set_speed_rpm", "duration_min", "mass_g"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Missing columns in {path}: {sorted(missing)}")

    df = df.dropna(subset=["set_speed_rpm", "duration_min", "mass_g"]).copy()
    if df.empty:
        raise ValueError(
            f"No completed runs in {path}. Fill mass_g (and check duration_min) first."
        )

    df["set_speed_rpm"] = df["set_speed_rpm"].astype(float)
    df["duration_min"] = df["duration_min"].astype(float)
    df["mass_g"] = df["mass_g"].astype(float)
    if (df["duration_min"] <= 0).any():
        raise ValueError("duration_min must be > 0")

    df["flow_ml_per_min"] = df["mass_g"] / (
        WATER_DENSITY_G_PER_ML * df["duration_min"]
    )
    return df.sort_values("set_speed_rpm").reset_index(drop=True)


def fit_linear(rpm: np.ndarray, flow: np.ndarray) -> dict[str, float]:
    """Return slope/intercept fits (free and through-origin)."""
    slope_free, intercept = np.polyfit(rpm, flow, 1)
    # Through origin: Q = k * rpm
    slope_origin = float(np.dot(rpm, flow) / np.dot(rpm, rpm))
    return {
        "slope_free": float(slope_free),
        "intercept_ml_per_min": float(intercept),
        "slope_origin": slope_origin,
    }


def plot(df: pd.DataFrame, fit: dict[str, float]) -> Path:
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    rpm = df["set_speed_rpm"].to_numpy()
    flow = df["flow_ml_per_min"].to_numpy()
    x = np.linspace(0, max(rpm.max() * 1.05, 1.0), 200)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(rpm, flow, color="tab:blue", zorder=3, label="Measured (scale)")

    ax.plot(
        x,
        fit["slope_origin"] * x,
        color="tab:blue",
        linestyle="-",
        label=f"Fit through origin: {fit['slope_origin']:.4f} ml/min per rpm",
    )
    ax.plot(
        x,
        fit["slope_free"] * x + fit["intercept_ml_per_min"],
        color="tab:orange",
        linestyle="--",
        label=(
            f"Free fit: {fit['slope_free']:.4f}·rpm "
            f"+ {fit['intercept_ml_per_min']:.2f} ml/min"
        ),
    )
    ax.plot(
        x,
        ADOPTED_ML_PER_MIN_PER_RPM * x,
        color="tab:green",
        linestyle="-.",
        label=f"Adopted: {ADOPTED_ML_PER_MIN_PER_RPM:.4f} ml/min per rpm",
    )
    ax.plot(
        x,
        PRIOR_ML_PER_MIN_PER_RPM * x,
        color="0.5",
        linestyle=":",
        label=f"Prior estimate: {PRIOR_ML_PER_MIN_PER_RPM:.4f} ml/min per rpm",
    )

    ax.set_xlabel("Pump set speed (rpm)")
    ax.set_ylabel("Flow rate (ml/min)")
    ax.set_title("Pump speed vs gravimetric flow rate")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=150)
    plt.close(fig)
    return OUTPUT_PNG


def main() -> None:
    df = load_runs(RAW_CSV)
    fit = fit_linear(
        df["set_speed_rpm"].to_numpy(),
        df["flow_ml_per_min"].to_numpy(),
    )
    out = plot(df, fit)

    print(df[["run", "set_speed_rpm", "duration_min", "mass_g", "flow_ml_per_min"]].to_string(index=False))
    print()
    print(f"Through-origin slope: {fit['slope_origin']:.4f} ml/min per rpm")
    print(
        f"Free fit:             {fit['slope_free']:.4f} ml/min per rpm "
        f"(intercept {fit['intercept_ml_per_min']:.2f} ml/min)"
    )
    print(f"Adopted constant:     {ADOPTED_ML_PER_MIN_PER_RPM:.4f} ml/min per rpm")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
