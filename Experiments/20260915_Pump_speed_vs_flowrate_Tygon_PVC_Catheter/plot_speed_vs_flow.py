"""Plot pump set speed (RPM) vs gravimetric and Keyence flow rate.

Reads every CSV in raw_data/ (one file per run), converts mass → flow
assuming water density, fits a free linear model (slope + intercept),
and writes a PNG under output_data/.
"""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import ML_PER_MIN_PER_RPM

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

WATER_DENSITY_G_PER_ML = 1.0
DEFAULT_DURATION_MIN = 5.0

FILE_LABELS = {
    "catheter.csv": "Catheter (SAGE prototype 2)",
    "sage_prototype_2.csv": "SAGE prototype 2",
}


def _col(df: pd.DataFrame, *needles: str) -> str | None:
    for col in df.columns:
        compact = str(col).strip().lower().replace(" ", "").replace("_", "")
        for needle in needles:
            if compact == needle.replace(" ", "").replace("_", ""):
                return col
    return None


def config_label(path: Path) -> str:
    if path.name in FILE_LABELS:
        return FILE_LABELS[path.name]
    return path.stem.replace("_", " ")


def load_run(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c != ""]].copy()

    rpm_col = next(
        (c for c in df.columns if "rpm" in c.lower() or c.lower() == "set rmp"),
        None,
    )
    mass_col = _col(df, "massg", "mass")
    keyence_col = next((c for c in df.columns if "keyence" in c.lower()), None)
    duration_col = _col(df, "durationmin", "duration")
    if rpm_col is None or mass_col is None:
        raise KeyError(
            f"Need set RPM and mass columns in {path.name}: {list(df.columns)}"
        )

    df = df.dropna(subset=[rpm_col, mass_col]).copy()
    if df.empty:
        return pd.DataFrame()

    out = pd.DataFrame(
        {
            "set_speed_rpm": df[rpm_col].astype(float),
            "mass_g": df[mass_col].astype(float),
        }
    )
    if duration_col is not None:
        out["duration_min"] = pd.to_numeric(df[duration_col], errors="coerce")
        out["duration_min"] = out["duration_min"].fillna(DEFAULT_DURATION_MIN)
    else:
        out["duration_min"] = DEFAULT_DURATION_MIN
    if (out["duration_min"] <= 0).any():
        raise ValueError(f"duration must be > 0 in {path.name}")

    out["flow_ml_per_min"] = out["mass_g"] / (
        WATER_DENSITY_G_PER_ML * out["duration_min"]
    )
    if keyence_col is not None:
        out["keyence_ml_per_min"] = pd.to_numeric(df[keyence_col], errors="coerce")
    else:
        out["keyence_ml_per_min"] = np.nan

    out["configuration"] = config_label(path)
    out["source"] = path.name
    return out.sort_values("set_speed_rpm").reset_index(drop=True)


def load_runs() -> pd.DataFrame:
    preferred = ["sage_prototype_2.csv", "catheter.csv"]
    paths = [RAW_DATA / name for name in preferred if (RAW_DATA / name).is_file()]
    if not paths:
        paths = sorted(
            p
            for p in RAW_DATA.glob("*.csv")
            if p.is_file() and "copy" not in p.stem.lower()
        )
    frames = [load_run(p) for p in paths]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def r_squared(y: np.ndarray, yhat: np.ndarray) -> float:
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot == 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def rmse(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def fit_free_linear(rpm: np.ndarray, flow: np.ndarray) -> dict[str, float]:
    slope, intercept = (float(v) for v in np.polyfit(rpm, flow, 1))
    yhat = slope * rpm + intercept
    return {
        "slope": slope,
        "intercept": intercept,
        "r2": r_squared(flow, yhat),
        "rmse": rmse(flow, yhat),
    }


def plot_config(
    group: pd.DataFrame,
    config: str,
    fit: dict[str, float],
    rpm_max: float,
    flow_max: float,
) -> Path:
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    stem = config.lower().replace(" ", "_").replace("(", "").replace(")", "")
    out_path = OUTPUT_DATA / f"pump_speed_vs_flowrate_{stem}.png"
    x = np.linspace(0, max(rpm_max * 1.05, 1.0), 200)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(
        group["set_speed_rpm"],
        group["flow_ml_per_min"],
        color="tab:orange",
        zorder=3,
        label="Scale",
    )
    keyence = group.dropna(subset=["keyence_ml_per_min"])
    if not keyence.empty:
        ax.scatter(
            keyence["set_speed_rpm"],
            keyence["keyence_ml_per_min"],
            facecolors="none",
            edgecolors="tab:orange",
            marker="D",
            zorder=4,
            label="Keyence",
        )
    ax.plot(
        x,
        fit["slope"] * x + fit["intercept"],
        color="tab:orange",
        linestyle="-",
        label=(
            f"Fit: {fit['slope']:.4f}·rpm + {fit['intercept']:.2f} ml/min"
            f"  (R²={fit['r2']:.4f})"
        ),
    )
    ax.plot(
        x,
        ML_PER_MIN_PER_RPM * x,
        color="0.55",
        linestyle="-.",
        label=f"2026-09-14 (worn tubing): {ML_PER_MIN_PER_RPM:.4f}",
    )

    ax.set_xlim(0, max(rpm_max * 1.05, 1.0))
    ax.set_ylim(0, max(flow_max * 1.08, 1.0))
    ax.set_xlabel("Pump set speed (rpm)")
    ax.set_ylabel("Flow rate (ml/min)")
    ax.set_title(f"Pump speed vs flow — {config}")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def main() -> None:
    csvs = list(RAW_DATA.glob("*.csv"))
    if not csvs:
        print(f"No input files yet - add a CSV under {RAW_DATA.relative_to(HERE)}")
        return

    df = load_runs()
    if df.empty:
        print(
            "No completed runs yet - fill mass g in "
            f"{RAW_DATA.relative_to(HERE)}/*.csv"
        )
        return

    fits: dict[str, dict[str, float]] = {}
    for config, group in df.groupby("configuration", sort=False):
        fits[config] = fit_free_linear(
            group["set_speed_rpm"].to_numpy(),
            group["flow_ml_per_min"].to_numpy(),
        )

    rpm_max = float(df["set_speed_rpm"].max())
    pred_max = [fit["slope"] * rpm_max + fit["intercept"] for fit in fits.values()]
    flow_max = float(
        np.nanmax(
            np.concatenate(
                [
                    df["flow_ml_per_min"].to_numpy(),
                    df["keyence_ml_per_min"].to_numpy(),
                    np.array([ML_PER_MIN_PER_RPM * rpm_max]),
                    np.array(pred_max),
                ]
            )
        )
    )

    outs: list[Path] = []
    for config, group in df.groupby("configuration", sort=False):
        outs.append(plot_config(group, config, fits[config], rpm_max, flow_max))

    cols = [
        "configuration",
        "set_speed_rpm",
        "duration_min",
        "mass_g",
        "flow_ml_per_min",
        "keyence_ml_per_min",
    ]
    print(df[cols].to_string(index=False))
    print()
    for config, fit in fits.items():
        print(config)
        print(
            f"  Q = {fit['slope']:.4f}·rpm + {fit['intercept']:.2f} ml/min"
            f"   R²={fit['r2']:.4f}  RMSE={fit['rmse']:.2f}"
        )
    print(f"2026-09-14 worn tubing (provisional): {ML_PER_MIN_PER_RPM:.4f}")
    for out in outs:
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
