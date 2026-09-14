"""Plot commanded (set) flow vs Keyence FD-X displayed flow.

Reads every CSV in raw_data/, skips copies and duplicate files, and writes
output_data/set_flow_vs_keyence.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"
OUTPUT_PNG = OUTPUT_DATA / "set_flow_vs_keyence.png"

LABELS = {
    "without_cathether.csv": "No catheter",
    "black_cathether.csv": "Black catheter",
    "SAGE prototype 2.csv": "SAGE test 1",
    "SAGE prototype 2_test2.csv": "SAGE test 2",
}

COLORS = {
    "No catheter": "tab:blue",
    "Black catheter": "0.25",
    "SAGE test 1": "tab:orange",
    "SAGE test 2": "tab:green",
}

LEFT_PANEL = ["No catheter", "Black catheter"]
RIGHT_PANEL = ["SAGE test 1", "SAGE test 2"]


def _skip_file(path: Path) -> bool:
    name = path.name.lower()
    if path.suffix.lower() != ".csv":
        return True
    if "copy" in name:
        return True
    return False


def load_run(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    set_col = next(
        (c for c in df.columns if c.lower().replace(" ", "") in {"setflowrate", "setflow"}),
        None,
    )
    keyence_col = next((c for c in df.columns if "keyence" in c.lower()), None)
    if set_col is None or keyence_col is None:
        raise KeyError(f"Need set-flow and Keyence columns in {path.name}: {list(df.columns)}")

    notes_col = next(
        (c for c in df.columns if c.lower() not in {set_col.lower(), "set rmp", "set rpm"}
         and "keyence" not in c.lower()),
        None,
    )

    notes = (
        df[notes_col].fillna("").astype(str).str.strip()
        if notes_col
        else ""
    )
    out = pd.DataFrame(
        {
            "set_ml_per_min": pd.to_numeric(df[set_col], errors="coerce"),
            "keyence_ml_per_min": pd.to_numeric(df[keyence_col], errors="coerce"),
            "notes": notes,
        }
    )
    out["notes"] = out["notes"].replace({"nan": "", "None": ""})
    out = out.dropna(subset=["set_ml_per_min", "keyence_ml_per_min"]).copy()
    out["source"] = path.name
    return out.reset_index(drop=True)


def fingerprint(df: pd.DataFrame) -> tuple:
    return tuple(
        zip(
            df["set_ml_per_min"].round(3).tolist(),
            df["keyence_ml_per_min"].round(3).tolist(),
        )
    )


def load_all() -> dict[str, pd.DataFrame]:
    csvs = sorted(p for p in RAW_DATA.iterdir() if not _skip_file(p))
    if not csvs:
        return {}

    loaded: dict[str, pd.DataFrame] = {}
    seen: dict[tuple, str] = {}
    for path in csvs:
        df = load_run(path)
        if df.empty:
            continue
        key = fingerprint(df)
        if key in seen:
            print(f"Skipping {path.name} (duplicate of {seen[key]})")
            continue
        seen[key] = path.name
        label = LABELS.get(path.name, path.stem)
        loaded[label] = df
    order = ["No catheter", "Black catheter", "SAGE test 1", "SAGE test 2"]
    return {k: loaded[k] for k in order if k in loaded} | {
        k: v for k, v in loaded.items() if k not in order
    }


def stats_row(label: str, df: pd.DataFrame) -> dict:
    err = df["keyence_ml_per_min"] - df["set_ml_per_min"]
    band = df[(df["set_ml_per_min"] >= 30) & (df["set_ml_per_min"] <= 100)]
    band_err = band["keyence_ml_per_min"] - band["set_ml_per_min"]
    return {
        "config": label,
        "n": int(len(df)),
        "mae_ml_min": float(err.abs().mean()),
        "mae_30_100_ml_min": float(band_err.abs().mean()) if not band.empty else float("nan"),
        "rmse_ml_min": float(np.sqrt((err**2).mean())),
        "max_abs_err_ml_min": float(err.abs().max()),
        "max_keyence_ml_min": float(df["keyence_ml_per_min"].max()),
        "max_set_ml_min": float(df["set_ml_per_min"].max()),
    }


def _connect_steps(ax, x: np.ndarray, y: np.ndarray, color, *, max_step: float = 20.0) -> None:
    """Draw lines only between neighbouring holds (skip large extra-check jumps)."""
    for i in range(len(x) - 1):
        if abs(x[i + 1] - x[i]) <= max_step:
            ax.plot(x[i : i + 2], y[i : i + 2], color=color, alpha=0.35, linewidth=1.2, zorder=2)


def _draw_runs(ax, runs: dict[str, pd.DataFrame]) -> None:
    for label, df in runs.items():
        color = COLORS.get(label)
        x = df["set_ml_per_min"].to_numpy()
        y = df["keyence_ml_per_min"].to_numpy()
        _connect_steps(ax, x, y, color)
        ax.scatter(x, y, color=color, s=36, zorder=3, label=label)


def _panel_limit(runs: dict[str, pd.DataFrame]) -> float:
    hi = max(
        float(df[["set_ml_per_min", "keyence_ml_per_min"]].to_numpy().max())
        for df in runs.values()
    )
    return hi + max(hi * 0.05, 5.0)


def plot(runs: dict[str, pd.DataFrame]) -> Path:
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)

    left = {k: runs[k] for k in LEFT_PANEL if k in runs}
    right = {k: runs[k] for k in RIGHT_PANEL if k in runs}
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.6))

    panels = (
        (axes[0], left, "No catheter and black catheter"),
        (axes[1], right, "SAGE prototype 2, test 1 and 2"),
    )
    for ax, subset, title in panels:
        if not subset:
            continue
        _draw_runs(ax, subset)
        lim = _panel_limit(subset)
        ax.set_xlim(0, lim)
        ax.set_ylim(0, lim)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("Set flow rate (ml/min)")
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", fontsize=8)

    axes[0].set_ylabel("Keyence FD-X displayed flow (ml/min)")
    fig.suptitle("Set flow vs Keyence FD-X")
    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=150)
    plt.close(fig)
    return OUTPUT_PNG


def main() -> None:
    runs = load_all()
    if not runs:
        print("No input files yet in raw_data/")
        return

    out = plot(runs)
    rows = [stats_row(label, df) for label, df in runs.items()]
    summary = pd.DataFrame(rows)
    print(summary.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    print()
    for label, df in runs.items():
        print(f"=== {label} ({df['source'].iloc[0]}) ===")
        show = df[["set_ml_per_min", "keyence_ml_per_min", "notes"]].copy()
        show["error"] = show["keyence_ml_per_min"] - show["set_ml_per_min"]
        print(show.to_string(index=False))
        print()
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
