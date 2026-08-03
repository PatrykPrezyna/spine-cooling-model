"""Plot catheter flow vs pressure characterisation curves.

Pressure on X, flow rate on Y. One marker series per quantity (cath in, cath out,
ΔP) for each pressure_log_*.csv in this folder. Uses the last fraction of each
RPM hold as the steady window.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
# Prior calibration: ~0.7823 ml/min per rpm (≈ 60 rpm → 47 ml/min)
ML_PER_MIN_PER_RPM = 0.7823
STEADY_TAIL_FRACTION = 0.3  # use last 30% of each RPM step
MIN_STEADY_SAMPLES = 50


def _load(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = [c.strip().replace("\\", "").lower() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def _run_label(csv_path: Path) -> str:
    name = csv_path.stem.lower()
    if "forward" in name:
        return "forward"
    if "reverse" in name:
        return "reverse"
    return csv_path.stem


def steady_points(df: pd.DataFrame) -> pd.DataFrame:
    """Mean pressures / flow per set RPM, from the end of each hold."""
    rows = []
    for rpm, g in df.groupby("peristaltic_pump_set_speed_rpm", sort=True):
        n = len(g)
        start = max(0, int(n * (1.0 - STEADY_TAIL_FRACTION)))
        if n - start < MIN_STEADY_SAMPLES:
            start = max(0, n - MIN_STEADY_SAMPLES)
        steady = g.iloc[start:]
        cath_in = steady["catheder_input_psi"].mean()
        cath_out = steady["catheder_output_psi"].mean()
        rows.append(
            {
                "rpm": float(rpm),
                "flow_ml_per_min": float(rpm) * ML_PER_MIN_PER_RPM,
                "cath_in_psi": cath_in,
                "cath_out_psi": cath_out,
                "delta_p_psi": cath_in - cath_out,
                "n_steady": len(steady),
            }
        )
    return pd.DataFrame(rows)


def plot_logs(csv_paths: list[Path] | None = None) -> Path:
    if csv_paths is None:
        csv_paths = sorted(HERE.glob("pressure_log_*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No pressure_log_*.csv in {HERE}")

    series_styles = {
        "cath_in_psi": ("Catheter input", "tab:blue", "o"),
        "cath_out_psi": ("Catheter output", "tab:orange", "s"),
        "delta_p_psi": ("ΔP (in − out)", "tab:green", "D"),
    }
    # Distinct linestyles when overlaying multiple runs
    run_linestyles = ["-", "--", "-.", ":"]

    fig, ax = plt.subplots(figsize=(8, 6))
    for i, csv_path in enumerate(csv_paths):
        df = _load(csv_path)
        pts = steady_points(df)
        label = _run_label(csv_path)
        ls = run_linestyles[i % len(run_linestyles)]
        print(f"\n{csv_path.name} ({label})")
        print(pts.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))

        for col, (series_name, color, marker) in series_styles.items():
            run_tag = f" [{label}]" if len(csv_paths) > 1 else ""
            ax.plot(
                pts[col],
                pts["flow_ml_per_min"],
                color=color,
                marker=marker,
                linestyle=ls,
                linewidth=1.5,
                markersize=7,
                label=f"{series_name}{run_tag}",
            )

    ax.set_xlabel("Pressure (psi)")
    ax.set_ylabel("Flow rate (ml/min)")
    ax.set_title("Catheter flow–pressure characterisation")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_ylim(bottom=0)

    stems = "_".join(p.stem.replace("pressure_log_", "") for p in csv_paths)
    out = HERE / f"flow_pressure_{stems}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    out = plot_logs()
    print(f"\n-> {out.name}")
