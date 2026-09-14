"""One explanatory plot: how mean and max are taken from a hold.

This is not a per-run figure. It uses a single example hold (50 ml/min /
85 rpm from the water open-forward log) to show the last-30% window.
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from plot_flow_pressure import (
    CATHETER_IN_COL,
    CATHETER_OUT_COL,
    ML_PER_MIN_PER_RPM,
    OUTPUT_DATA,
    RAW_DATA,
    SERIES_STYLES,
    STEADY_TAIL_FRACTION,
    _load,
    keyence_path_for,
    load_keyence_csv,
    pick_hold,
    rpm_to_flow_ml_min,
    steady_slice,
)

EXAMPLE_RPM = 85.0
OUTPUT_PNG = OUTPUT_DATA / "hold_raw_explained.png"
EXAMPLE_GLOB = "pressure_log_*water_open_forward*.csv"


def example_pressure_log() -> Path:
    logs = sorted(RAW_DATA.glob(EXAMPLE_GLOB))
    if not logs:
        raise FileNotFoundError(f"No {EXAMPLE_GLOB} in {RAW_DATA}")
    return logs[0]


def plot_hold_explained(csv_path: Path | None = None, rpm: float = EXAMPLE_RPM) -> Path:
    if csv_path is None:
        csv_path = example_pressure_log()
    df, _ = _load(csv_path)
    hold = pick_hold(df, rpm).copy()
    hold["elapsed_s"] = (
        hold["timestamp"] - hold["timestamp"].iloc[0]
    ).dt.total_seconds()
    steady = steady_slice(hold)
    t0 = hold["elapsed_s"].iloc[0]
    t1 = hold["elapsed_s"].iloc[-1]
    t_steady = float(steady["elapsed_s"].iloc[0])
    flow = rpm_to_flow_ml_min(rpm, ML_PER_MIN_PER_RPM)
    ke_note = f"{flow:.0f} ml/min set"
    ke_path = keyence_path_for(csv_path)
    if ke_path is not None:
        ke = load_keyence_csv(ke_path)
        match = ke.loc[ke["rpm"].sub(rpm).abs() < 0.5, "keyence_ml_per_min"].dropna()
        if not match.empty:
            ke_note = f"Keyence {float(match.iloc[-1]):.0f} ml/min ({rpm:.0f} rpm hold)"

    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    ax.axvspan(
        t_steady,
        t1,
        color="0.88",
        zorder=0,
        label=f"Steady window (last {STEADY_TAIL_FRACTION:.0%} of hold)",
    )
    ax.axvline(t_steady, color="0.45", linestyle="-", linewidth=1.0, zorder=1)

    for _col, (series_name, color, _) in SERIES_STYLES.items():
        src = CATHETER_IN_COL if "input" in series_name.lower() else CATHETER_OUT_COL
        mean_p = float(steady[src].mean())
        max_idx = steady[src].idxmax()
        max_p = float(steady.loc[max_idx, src])
        t_max = float(steady.loc[max_idx, "elapsed_s"])

        ax.plot(
            hold["elapsed_s"],
            hold[src],
            color=color,
            linewidth=0.55,
            alpha=0.4,
            label=f"{series_name} raw (100 Hz)",
            zorder=2,
        )
        ax.hlines(
            mean_p,
            t_steady,
            t1,
            colors=color,
            linestyles="-",
            linewidth=2.2,
            zorder=4,
            label=f"{series_name} mean = {mean_p:.2f} bar",
        )
        ax.hlines(
            max_p,
            t_steady,
            t1,
            colors=color,
            linestyles="--",
            linewidth=1.6,
            zorder=4,
            label=f"{series_name} max = {max_p:.2f} bar",
        )
        ax.scatter(
            [t_max],
            [max_p],
            color=color,
            marker="^",
            s=45,
            zorder=5,
            edgecolors="black",
            linewidths=0.4,
        )
        print(
            f"{series_name}: n={len(steady)}  mean={mean_p:.3f} bar  "
            f"max={max_p:.3f} bar at t={t_max:.1f}s"
        )

    ax.set_xlim(t0, t1)
    ax.set_xlabel("Time in hold (s)")
    ax.set_ylabel("Pressure (bar)")
    ax.set_title(f"How mean and max are taken — {ke_note}")
    ax.text(
        t_steady + 0.02 * (t1 - t0),
        0.02,
        "Mean = average of samples in the grey window.\n"
        "Max = highest sample in the same window (triangle).",
        transform=ax.get_xaxis_transform(),
        va="bottom",
        ha="left",
        fontsize=8,
        color="0.15",
        bbox={"facecolor": "white", "edgecolor": "0.7", "alpha": 0.92, "pad": 4},
    )
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8)
    ax.set_ylim(bottom=min(-0.15, ax.get_ylim()[0]))

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return OUTPUT_PNG


if __name__ == "__main__":
    print(f"-> {plot_hold_explained()}")
