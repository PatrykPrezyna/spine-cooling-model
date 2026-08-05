"""Catheter flow-pressure characterisation: forward vs reverse comparison.
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import rpm_to_flow_ml_min

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

RPM_COL = "peristaltic_pump_set_speed_rpm"


def _load(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = [c.strip().replace("\\", "").lower() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def raw_points(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Every (flow, pressure) sample for one pressure channel."""
    rpm = df[RPM_COL].astype(float)
    out = pd.DataFrame(
        {
            "rpm": rpm,
            "flow_ml_per_min": rpm_to_flow_ml_min(rpm),
            "pressure_psi": df[col],
        }
    )
    return out.dropna(subset=["pressure_psi"]).reset_index(drop=True)


def group_means(pts: pd.DataFrame) -> pd.DataFrame:
    """Mean pressure at each flow level."""
    return (
        pts.groupby("flow_ml_per_min", as_index=False)["pressure_psi"]
        .mean()
        .sort_values("flow_ml_per_min")
    )


def fit_pressure_on_flow(pts: pd.DataFrame) -> tuple[float, float, float]:
    """OLS pressure = m*flow + c. Returns (slope, intercept, r_squared).

    Flow is the controlled variable, so it is the regressor. Slope m carries
    units of psi per (ml/min) -- a hydraulic resistance for this channel.
    """
    q = pts["flow_ml_per_min"].to_numpy()
    p = pts["pressure_psi"].to_numpy()
    m, c = np.polyfit(q, p, 1)
    resid = p - (m * q + c)
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((p - p.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(m), float(c), r2


def _draw_pair(ax, series, title):
    """series: list of (label, pts, color, marker)."""
    for label, pts, color, marker in series:
        ax.scatter(
            pts["pressure_psi"],
            pts["flow_ml_per_min"],
            s=3,
            alpha=0.5,
            color=color,
            edgecolors="none",
            zorder=1,
        )
        gm = group_means(pts)
        ax.plot(
            gm["pressure_psi"],
            gm["flow_ml_per_min"],
            linestyle="none",
            marker=marker,
            markersize=8,
            color=color,
            markeredgecolor="black",
            markeredgewidth=0.6,
            label=f"{label} -- hold mean",
            zorder=5,
        )
        m, c, r2 = fit_pressure_on_flow(pts)
        q_line = np.linspace(
            pts["flow_ml_per_min"].min(), pts["flow_ml_per_min"].max(), 100
        )
        ax.plot(
            m * q_line + c,
            q_line,
            linestyle="--",
            linewidth=1.5,
            color=color,
            label=f"{label} fit: P = {m:.3g}*Q + {c:.3g}  (R2={r2:.3f})",
            zorder=3,
        )

    ax.set_xlabel("Pressure (psi)")
    ax.set_ylabel("Flow rate (ml/min)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    ax.set_ylim(bottom=0)
    ax.set_xlim(-5, 70)


def plot_reversal(
    forward_csv: Path, reverse_csv: Path, out: Path | None = None
) -> Path:
    fwd = _load(forward_csv)
    rev = _load(reverse_csv)

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    _draw_pair(
        ax_l,
        [
            ("Forward", raw_points(fwd, "catheder_input_psi"), "tab:blue", "o"),
            ("Reverse", raw_points(rev, "catheder_output_psi"), "tab:orange", "s"),
        ],
        title="Upstream",
    )
    _draw_pair(
        ax_r,
        [
            ("Forward", raw_points(fwd, "catheder_output_psi"), "tab:blue", "o"),
            ("Reverse", raw_points(rev, "catheder_input_psi"), "tab:orange", "s"),
        ],
        title="Downstream",
    )

    fig.suptitle("Catheter flow-pressure characterisation -- reversal comparison")

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    if out is None:
        out = OUTPUT_DATA / "flow_pressure_reversal.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def _find_runs() -> tuple[Path, Path]:
    csvs = sorted(RAW_DATA.glob("pressure_log_*.csv"))
    return csvs[0], csvs[1]


if __name__ == "__main__":
    forward_csv, reverse_csv = _find_runs()
    print(f"forward: {forward_csv.name}")
    print(f"reverse: {reverse_csv.name}")
    print(f"-> {plot_reversal(forward_csv, reverse_csv)}")