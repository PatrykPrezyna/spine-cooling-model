"""Plot SAGE prototype 2 flow vs pressure characterisation curves.

Pressure on X, Keyence-measured flow on Y. Same colours as
Experiments/20260805_Flow_Pressure_characterisiation_with_SAGE:
catheter input = tab:blue, catheter output = tab:orange.

Each contiguous RPM hold in pressure_log_*.csv is paired with the matching
row in the Keyence hand log (external_flow_log_*.csv). Pressures are the
mean and max of the last fraction of the hold. Holds with no Keyence
reading are skipped.
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

CATHETER_IN_COL = "catheter_in_bar"
CATHETER_OUT_COL = "catheter_out_bar"
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

# Match 20260805_Flow_Pressure_characterisiation_with_SAGE colours.
SERIES_STYLES = {
    "cath_in_bar": ("Catheter input", "tab:blue", "o"),
    "cath_out_bar": ("Catheter output", "tab:orange", "s"),
}
FLOW_PRESSURE_SERIES = (
    ("cath_in_mean", "Catheter input mean", "tab:blue", "o", "-"),
    ("cath_in_max", "Catheter input max", "tab:blue", "^", "--"),
    ("cath_out_mean", "Catheter output mean", "tab:orange", "s", "-"),
    ("cath_out_max", "Catheter output max", "tab:orange", "D", "--"),
)
FLOW_PRESSURE_MEAN_SERIES = (
    ("cath_in_mean", "Catheter input", "tab:blue", "o", "-"),
    ("cath_out_mean", "Catheter output", "tab:orange", "s", "-"),
)
FLOW_PRESSURE_MAX_SERIES = (
    ("cath_in_max", "Catheter input", "tab:blue", "^", "-"),
    ("cath_out_max", "Catheter output", "tab:orange", "D", "-"),
)


def catheter_channels_were_swapped(df: pd.DataFrame) -> bool:
    """True when mean logged output pressure exceeds mean logged input."""
    return float(df[CATHETER_OUT_COL].mean()) > float(df[CATHETER_IN_COL].mean())


def correct_swapped_catheter_pressures(
    df: pd.DataFrame, csv_path: Path | None = None
) -> tuple[pd.DataFrame, bool]:
    """Swap in/out columns when the log has output > input (connection mistake)."""
    if not catheter_channels_were_swapped(df):
        return df, False
    out = df.copy()
    out[CATHETER_IN_COL] = df[CATHETER_OUT_COL].to_numpy()
    out[CATHETER_OUT_COL] = df[CATHETER_IN_COL].to_numpy()
    name = csv_path.name if csv_path is not None else "(dataframe)"
    print(f"WARNING: {name}: {CONNECTION_MISTAKE_NOTE}")
    return out, True


def _load(csv_path: Path) -> tuple[pd.DataFrame, bool]:
    return correct_swapped_catheter_pressures(
        load_sensor_csv(csv_path), csv_path
    )


def keyence_path_for(pressure_csv: Path) -> Path | None:
    """external_flow_log matching a pressure_log timestamp / condition."""
    stem = pressure_csv.stem.removeprefix("pressure_log_").replace("_100Hz", "")
    for name in (f"external_flow_log_{stem}.csv", f"external_flow_{stem}.csv"):
        path = RAW_DATA / name
        if path.exists():
            return path
    return None


def load_keyence_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    set_col = next(
        (c for c in df.columns if c.lower().replace(" ", "") in {"setflowrate", "setflow"}),
        None,
    )
    rpm_col = next(
        (c for c in df.columns if "rpm" in c.lower() or c.lower() == "set rmp"),
        None,
    )
    keyence_col = next((c for c in df.columns if "keyence" in c.lower()), None)
    if set_col is None or rpm_col is None or keyence_col is None:
        raise KeyError(f"Need set flow, RPM, and Keyence columns in {path.name}: {list(df.columns)}")
    notes_col = next(
        (
            c
            for c in df.columns
            if c not in {set_col, rpm_col, keyence_col} and str(c).strip() != ""
        ),
        None,
    )
    notes = (
        df[notes_col].fillna("").astype(str).str.strip()
        if notes_col is not None
        else ""
    )
    out = pd.DataFrame(
        {
            "set_ml_per_min": pd.to_numeric(df[set_col], errors="coerce"),
            "rpm": pd.to_numeric(df[rpm_col], errors="coerce"),
            "keyence_ml_per_min": pd.to_numeric(df[keyence_col], errors="coerce"),
            "notes": notes,
        }
    )
    out["notes"] = out["notes"].replace({"nan": "", "None": ""})
    return out.reset_index(drop=True)


def _output_path(csv_path: Path, suffix: str = "") -> Path:
    stem = csv_path.stem.removeprefix("pressure_log_")
    return OUTPUT_DATA / f"flow_pressure_{stem}{suffix}.png"


def filter_outbound_set_flow(
    pts: pd.DataFrame, set_min: float = 10.0, set_max: float = 70.0
) -> pd.DataFrame:
    """Keep the rising sweep only, from ``set_min`` to ``set_max`` ml/min.

    Drops the return path (90 → 10) and any outbound holds above ``set_max``.
    """
    if pts.empty:
        return pts
    set_flow = pts["set_ml_per_min"].to_numpy()
    peak_i = 0
    for i in range(1, len(pts)):
        if set_flow[i] >= set_flow[i - 1]:
            peak_i = i
        else:
            break
    outbound = pts.iloc[: peak_i + 1]
    keep = (outbound["set_ml_per_min"] >= set_min) & (
        outbound["set_ml_per_min"] <= set_max
    )
    return outbound.loc[keep].reset_index(drop=True)


def contiguous_holds(df: pd.DataFrame) -> list[pd.DataFrame]:
    """Split a log into contiguous constant-RPM segments (time order)."""
    rpm = df["peristaltic_pump_set_speed_rpm"]
    run_id = rpm.ne(rpm.shift()).cumsum()
    return [g for _, g in df.groupby(run_id, sort=False)]


def pick_hold(df: pd.DataFrame, rpm: float) -> pd.DataFrame:
    """Longest contiguous hold at ``rpm`` (skip idle)."""
    matches = [
        g
        for g in contiguous_holds(df)
        if abs(float(g["peristaltic_pump_set_speed_rpm"].iloc[0]) - rpm) < 0.5
    ]
    if not matches:
        raise KeyError(f"No hold near {rpm} rpm")
    return max(matches, key=len)


def steady_slice(hold: pd.DataFrame) -> pd.DataFrame:
    """Last fraction of a hold — the window whose mean is plotted."""
    n = len(hold)
    start = max(0, int(n * (1.0 - STEADY_TAIL_FRACTION)))
    if n - start < MIN_STEADY_SAMPLES:
        start = max(0, n - MIN_STEADY_SAMPLES)
    return hold.iloc[start:]


def steady_points(df: pd.DataFrame, keyence: pd.DataFrame | None = None) -> pd.DataFrame:
    """Mean and max pressures per hold, with Keyence flow on Y when available."""
    holds = [
        g
        for g in contiguous_holds(df)
        if float(g["peristaltic_pump_set_speed_rpm"].iloc[0]) > 0
    ]
    rows = []
    ke_i = 0
    for hold in holds:
        rpm = float(hold["peristaltic_pump_set_speed_rpm"].iloc[0])
        set_flow = rpm_to_flow_ml_min(rpm, ML_PER_MIN_PER_RPM)
        keyence_flow = float("nan")
        notes = ""
        if keyence is not None and ke_i < len(keyence):
            while ke_i < len(keyence) and abs(float(keyence.iloc[ke_i]["rpm"]) - rpm) > 0.5:
                ke_i += 1
            if ke_i < len(keyence):
                krow = keyence.iloc[ke_i]
                keyence_flow = float(krow["keyence_ml_per_min"])
                set_flow = float(krow["set_ml_per_min"])
                notes = str(krow["notes"])
                ke_i += 1
        if keyence is not None and pd.isna(keyence_flow):
            print(f"skip {rpm:.0f} rpm: no Keyence reading")
            continue
        flow = keyence_flow if not pd.isna(keyence_flow) else set_flow
        steady = steady_slice(hold)
        rows.append(
            {
                "rpm": rpm,
                "set_ml_per_min": set_flow,
                "flow_ml_per_min": flow,
                "cath_in_mean": steady[CATHETER_IN_COL].mean(),
                "cath_in_max": steady[CATHETER_IN_COL].max(),
                "cath_out_mean": steady[CATHETER_OUT_COL].mean(),
                "cath_out_max": steady[CATHETER_OUT_COL].max(),
                "n_steady": len(steady),
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def plot_file(
    csv_path: Path,
    *,
    set_min: float | None = None,
    set_max: float | None = None,
    outbound_only: bool = False,
    mean_only: bool = False,
    max_only: bool = False,
    swap_axes: bool = False,
    suffix: str = "",
) -> Path:
    df, swapped = _load(csv_path)
    ke_path = keyence_path_for(csv_path)
    keyence = load_keyence_csv(ke_path) if ke_path is not None else None
    if ke_path is None:
        print(f"WARNING: no Keyence log for {csv_path.name}; Y uses pump-set flow")
    else:
        print(f"Keyence log: {ke_path.name}")
    pts = steady_points(df, keyence)
    if outbound_only or set_min is not None or set_max is not None:
        pts = filter_outbound_set_flow(
            pts,
            set_min=10.0 if set_min is None else set_min,
            set_max=70.0 if set_max is None else set_max,
        )
    label = csv_path.stem.removeprefix("pressure_log_")
    print(f"\n{csv_path.name} ({label})")
    print(pts.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))

    if max_only:
        series = FLOW_PRESSURE_MAX_SERIES
    elif mean_only:
        series = FLOW_PRESSURE_MEAN_SERIES
    else:
        series = FLOW_PRESSURE_SERIES
    fig, ax = plt.subplots(figsize=(8, 6))
    for col, series_name, color, marker, linestyle in series:
        x = pts["flow_ml_per_min"] if swap_axes else pts[col]
        y = pts[col] if swap_axes else pts["flow_ml_per_min"]
        ax.plot(
            x,
            y,
            color=color,
            marker=marker,
            linestyle=linestyle,
            linewidth=1.5,
            markersize=7,
            label=series_name,
        )

    pressure_label = f"Pressure [bar]"
    flow_label = "Flow rate [ml/min]" if swap_axes else "Keyence flow rate (ml/min)"
    label_size = 16 if swap_axes else 12
    tick_size = 13 if swap_axes else 10
    ax.set_xlabel(flow_label if swap_axes else pressure_label, fontsize=label_size)
    ax.set_ylabel(pressure_label if swap_axes else flow_label, fontsize=label_size)
    ax.tick_params(axis="both", labelsize=tick_size)
    y_note = "Keyence hand reading" if keyence is not None else "pump-set flow"
    if max_only:
        stat_note = "max"
    elif mean_only:
        stat_note = "mean"
    else:
        stat_note = "mean and max"
    range_note = ""
    if outbound_only or set_min is not None or set_max is not None:
        lo = 10.0 if set_min is None else set_min
        hi = 70.0 if set_max is None else set_max
        range_note = f"; outbound {lo:.0f}–{hi:.0f} ml/min (set), no return"
    title = (
        f"SAGE prototype 2 flow–pressure\n{csv_path.name}\n"
        f"{y_note}; {stat_note} of last {STEADY_TAIL_FRACTION:.0%} of each hold"
        f"{range_note}"
    )
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
    ax.legend(loc="best", fontsize=12 if swap_axes else None)
    if swap_axes:
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
    else:
        ax.set_ylim(bottom=0)

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = _output_path(csv_path, suffix=suffix)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_logs(csv_paths: list[Path] | None = None) -> list[Path]:
    if csv_paths is None:
        csv_paths = sorted(RAW_DATA.glob("pressure_log_*.csv"))
    if not csv_paths:
        print("No input files yet in raw_data/")
        return []

    written: list[Path] = []
    for csv_path in csv_paths:
        written.append(plot_file(csv_path))
        print(f"-> {written[-1]}")
    return written


if __name__ == "__main__":
    logs = sorted(RAW_DATA.glob("pressure_log_*.csv"))
    plot_logs(logs)
