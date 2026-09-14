"""Plot catheter flow vs pressure characterisation curves.

Pressure on X, flow rate on Y. One marker series per quantity (cath in, cath out)
for each pressure_log_*.csv in raw_data/. Uses the last fraction of each
RPM hold as the steady window. Writes one plot per log to output_data/.

Skips a CSV when its corresponding output already exists; delete that PNG to
force a re-run.

CONNECTION MISTAKE (do not edit raw_data/):
If logged catheder_output_psi is higher than catheder_input_psi, the catheter
pressure fittings / channels were swapped on the bench. Physically the inlet
(upstream) must be the higher pressure. correct_swapped_catheter_pressures()
swaps the two columns for plotting only. Known case:
pressure_log_20260804_091152_black_cath_direction_pumpout_cath_out.csv
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import (
    ML_PER_MIN_PER_RPM,
    load_sensor_csv,
    rpm_to_flow_ml_min,
)

CATHETER_IN_COL = "catheder_input_psi"
CATHETER_OUT_COL = "catheder_output_psi"
CONNECTION_MISTAKE_NOTE = (
    "CONNECTION MISTAKE: logged catheter OUTPUT pressure > INPUT. "
    "Fittings/channels were swapped on the bench. raw_data/ is unchanged; "
    "columns are swapped here so plots show input = upstream (higher P) "
    "and output = downstream (lower P)."
)

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"
STEADY_TAIL_FRACTION = 0.3  # use last 30% of each RPM step
MIN_STEADY_SAMPLES = 50


def catheter_channels_were_swapped(df: pd.DataFrame) -> bool:
    """True when mean logged output pressure exceeds mean logged input."""
    return float(df[CATHETER_OUT_COL].mean()) > float(df[CATHETER_IN_COL].mean())


def correct_swapped_catheter_pressures(
    df: pd.DataFrame, csv_path: Path | None = None
) -> tuple[pd.DataFrame, bool]:
    """Swap in/out columns when the log has output > input (connection mistake).

    Never writes back to the CSV. Callers plot from the returned frame.
    """
    if not catheter_channels_were_swapped(df):
        return df, False
    out = df.copy()
    out[CATHETER_IN_COL] = df[CATHETER_OUT_COL].to_numpy()
    out[CATHETER_OUT_COL] = df[CATHETER_IN_COL].to_numpy()
    name = csv_path.name if csv_path is not None else "(dataframe)"
    print(f"WARNING: {name}: {CONNECTION_MISTAKE_NOTE}")
    return out, True


def _load(csv_path: Path) -> tuple[pd.DataFrame, bool]:
    df, swapped = correct_swapped_catheter_pressures(
        load_sensor_csv(csv_path), csv_path
    )
    return df, swapped


def _run_label(csv_path: Path) -> str:
    name = csv_path.stem.lower()
    if "forward" in name:
        return "forward"
    if "reverse" in name:
        return "reverse"
    return csv_path.stem


def _output_path(csv_path: Path) -> Path:
    stem = csv_path.stem.removeprefix("pressure_log_")
    return OUTPUT_DATA / f"flow_pressure_{stem}.png"


def steady_points(df: pd.DataFrame) -> pd.DataFrame:
    """Mean pressures / flow per set RPM, from the end of each hold."""
    rows = []
    for rpm, g in df.groupby("peristaltic_pump_set_speed_rpm", sort=True):
        n = len(g)
        start = max(0, int(n * (1.0 - STEADY_TAIL_FRACTION)))
        if n - start < MIN_STEADY_SAMPLES:
            start = max(0, n - MIN_STEADY_SAMPLES)
        steady = g.iloc[start:]
        cath_in = steady[CATHETER_IN_COL].mean()
        cath_out = steady[CATHETER_OUT_COL].mean()
        rows.append(
            {
                "rpm": float(rpm),
                "flow_ml_per_min": rpm_to_flow_ml_min(
                    float(rpm), ML_PER_MIN_PER_RPM
                ),
                "cath_in_psi": cath_in,
                "cath_out_psi": cath_out,
                "n_steady": len(steady),
            }
        )
    return pd.DataFrame(rows)


def plot_file(csv_path: Path) -> Path:
    series_styles = {
        "cath_in_psi": ("Catheter input", "tab:blue", "o"),
        "cath_out_psi": ("Catheter output", "tab:orange", "s"),
    }

    df, swapped = _load(csv_path)
    pts = steady_points(df)
    label = _run_label(csv_path)
    print(f"\n{csv_path.name} ({label})")
    print(pts.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))

    fig, ax = plt.subplots(figsize=(8, 6))
    for col, (series_name, color, marker) in series_styles.items():
        ax.plot(
            pts[col],
            pts["flow_ml_per_min"],
            color=color,
            marker=marker,
            linestyle="-",
            linewidth=1.5,
            markersize=7,
            label=series_name,
        )
        for x, y in zip(pts[col], pts["flow_ml_per_min"]):
            ax.annotate(
                f"{x:.2f}",
                (x, y),
                textcoords="offset points",
                xytext=(5, 3),
                fontsize=7,
                color=color,
                alpha=0.9,
            )

    ax.set_xlabel("Pressure (psi)")
    ax.set_ylabel("Flow rate (ml/min)")
    title = f"Catheter flow–pressure characterisation\n{csv_path.name}"
    if swapped:
        title += "\nplotted with in/out swapped (connection mistake in log)"
    ax.set_title(title)
    if swapped:
        ax.text(
            0.02,
            0.98,
            "CONNECTION MISTAKE in log: output > input.\n"
            "Plotted with channels swapped. raw_data/ not modified.",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=8,
            color="tab:red",
            bbox={"facecolor": "white", "edgecolor": "tab:red", "alpha": 0.9},
        )
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_ylim(bottom=0)

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = _output_path(csv_path)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_logs(csv_paths: list[Path] | None = None) -> list[Path]:
    if csv_paths is None:
        csv_paths = sorted(RAW_DATA.glob("pressure_log_*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No pressure_log_*.csv in {RAW_DATA}")

    written: list[Path] = []
    for csv_path in csv_paths:
        out = _output_path(csv_path)
        if out.exists():
            print(f"skip {csv_path.name} (exists: {out.name})")
            continue
        written.append(plot_file(csv_path))
        print(f"-> {out}")
    return written


if __name__ == "__main__":
    plot_logs()
