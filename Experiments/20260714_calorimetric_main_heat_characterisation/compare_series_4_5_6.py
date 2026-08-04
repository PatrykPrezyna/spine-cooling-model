"""Combine and compare calorimetry runs from series 4, 5, and 6.

Series 4 — single / dual cartridge with catheter (RPM sweep)
Series 5 — cartridge open lines (no catheter)
Series 6 — ice bucket with catheter (no cartridge)

Produces:
  output_data/compare_series_4_5_6_cooldown.png  — tank cool-down overlays
  output_data/compare_series_4_5_6_power.png     — P_tank / P_flow bars
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import (
    find_cooling_window,
    flow_power,
    load_sensor_csv,
    tank_calorimetry,
    time_weighted_mean,
)

FOLDER = Path(__file__).resolve().parent
RAW_DATA = FOLDER / "raw_data"
OUTPUT_DATA = FOLDER / "output_data"

MASS_KG = 0.838
C = 4186.0
T_START_C = 37.0
T_END_C = 32.0
TEMP_FAULT_C = -20.0

SERIES_PREFIXES = ("4", "5", "6")

SERIES_TITLES = {
    "4": "4 — cartridge + catheter",
    "5": "5 — open lines (no catheter)",
    "6": "6 — ice bucket + catheter",
}

# Short legend labels keyed by stem (override auto parse when helpful)
LABEL_OVERRIDES = {
    "4_1_single_cartrige_60rmp": "1× cart + cath 60 rpm",
    "4_2_single_cartrige_120rmp": "1× cart + cath 120 rpm",
    "4_3_single_cartrige__240rmp": "1× cart + cath 240 rpm",
    "4_4_single_cartrige_360rmp": "1× cart + cath 360 rpm",
    "4_5_2x_cart_60rmp_v1": "2× cart + cath 60 rpm",
    "5_1_single_cart_60rmp_open_lines_without_catheder": "1× cart open 60 rpm",
    "5_2_2x_cart_60rmp_open_lines_without_catheder": "2× cart open 60 rpm",
    "5_2_2x_cart_60rmp_open_lines_without_catheder_v2": "2× cart open 60 rpm v2",
    "6_1_no_cart_ice_bucket_with_catheder_60rmp": "ice + cath 60 rpm",
    "6_1_no_cart_ice_bucket_with_catheder_120rmp": "ice + cath 120 rpm",
}


def blank_after_temp_fault(series: pd.Series, limit_c: float = TEMP_FAULT_C) -> pd.Series:
    out = series.astype(float).copy()
    bad = out <= limit_c
    if bad.any():
        out.iloc[bad.argmax() :] = np.nan
    return out


def resolve_flow_cols(df: pd.DataFrame) -> tuple[str, str]:
    if "cart_in_c" in df.columns and "cart_out_c" in df.columns:
        return "cart_in_c", "cart_out_c"
    if "cath_in_c" in df.columns and "cath_out_c" in df.columns:
        return "cath_in_c", "cath_out_c"
    raise KeyError(f"Need cart_* or cath_* columns in dataframe")


def series_id(stem: str) -> str:
    return stem.split("_", 1)[0][0]


def short_label(stem: str) -> str:
    if stem in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[stem]
    # Fallback: drop leading series index and compress common tokens
    rest = re.sub(r"^\d+_\d+_", "", stem)
    rest = rest.replace("cartrige", "cart").replace("catheder", "cath")
    rest = rest.replace("without_catheder", "open").replace("rmp", "rpm")
    return rest.replace("_", " ")


def rpm_from_stem(stem: str) -> int:
    for token in stem.split("_"):
        if token.endswith("rmp") or token.endswith("rpm"):
            digits = "".join(ch for ch in token if ch.isdigit())
            if digits:
                return int(digits)
    return 0


def sub_index(stem: str) -> int:
    """Parse the N in '{series}_{N}_...' (e.g. 4_3 → 3)."""
    parts = stem.split("_", 2)
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return 0


def discover_csvs() -> list[Path]:
    files = [
        path
        for path in RAW_DATA.glob("*.csv")
        if path.stem[:1] in SERIES_PREFIXES and path.stem[1:2] == "_"
    ]
    # series → run index → rpm (so 60 before 120 when the index is the same)
    return sorted(
        files,
        key=lambda p: (p.stem[0], sub_index(p.stem), rpm_from_stem(p.stem), p.stem),
    )


def analyze(csv_path: Path) -> dict | None:
    df = load_sensor_csv(csv_path)
    in_col, out_col = resolve_flow_cols(df)

    for col in ["tank_c", in_col, out_col]:
        df[col] = blank_after_temp_fault(df[col])

    temp = df.set_index("timestamp")["tank_c"].dropna()
    if temp.empty:
        print(f"SKIP (no tank data): {csv_path.name}")
        return None

    window = find_cooling_window(temp, T_START_C, T_END_C)
    if window is None:
        print(f"SKIP (no 37→32 window): {csv_path.name}")
        return None

    tank_result = tank_calorimetry(
        temp, window, mass_kg=MASS_KG, specific_heat_j_kg_k=C
    )

    active = (df["timestamp"] >= window.start) & (df["timestamp"] <= window.end)
    a = df.loc[active].copy()
    a["power_w"] = flow_power(
        a["pump_flow_ml_per_s"], a[in_col], a[out_col],
        specific_heat_j_kg_k=C,
    )
    a = a.dropna(subset=["power_w", "tank_c"])
    if len(a) < 2:
        print(f"SKIP (too few active samples): {csv_path.name}")
        return None

    p_flow_w = time_weighted_mean(
        a["power_w"], a["timestamp"], duration_s=window.duration_s
    )
    a["t_min_active"] = (a["timestamp"] - window.start).dt.total_seconds() / 60.0

    stem = csv_path.stem
    return {
        "file": csv_path.name,
        "stem": stem,
        "series": series_id(stem),
        "label": short_label(stem),
        "duration_s": window.duration_s,
        "flow_ml_min": float(a["pump_flow_ml_per_s"].mean() * 60.0),
        "P_tank_W": tank_result.average_power_w,
        "P_flow_W": float(p_flow_w),
        "df_active": a,
    }


def plot_cooldowns(rows: list[dict], out_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), sharey=True)
    for ax, series in zip(axes, SERIES_PREFIXES):
        series_rows = [r for r in rows if r["series"] == series]
        for r in series_rows:
            a = r["df_active"]
            ax.plot(
                a["t_min_active"],
                a["tank_c"],
                lw=1.8,
                label=f"{r['label']}  ({r['P_tank_W']:.1f} W)",
            )
        ax.axhline(T_START_C, color="k", ls=":", alpha=0.4)
        ax.axhline(T_END_C, color="k", ls=":", alpha=0.4)
        ax.set_xlabel("Time from 37 °C (min)")
        ax.set_title(SERIES_TITLES[series])
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="best")
    axes[0].set_ylabel("Tank temperature (°C)")
    fig.suptitle(
        f"Tank cool-down comparison — series 4 / 5 / 6  ({T_START_C:.0f}→{T_END_C:.0f} °C)",
        fontsize=12,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_power_bars(rows: list[dict], out_path: Path) -> None:
    labels = [r["label"] for r in rows]
    p_tank = [r["P_tank_W"] for r in rows]
    p_flow = [abs(r["P_flow_W"]) for r in rows]
    series_colors = {"4": "tab:blue", "5": "tab:orange", "6": "tab:green"}

    fig, ax = plt.subplots(figsize=(12, 5.5))
    x = np.arange(len(rows))
    w = 0.38

    bars1 = ax.bar(
        x - w / 2, p_tank, width=w, color="tab:purple",
        label=r"$P_{\mathrm{tank}}$ (calorimetry)",
    )
    bars2 = ax.bar(
        x + w / 2, p_flow, width=w, color="tab:cyan",
        label=r"$|P_{\mathrm{flow}}|$ ($\dot{m}\,c\,\Delta T$)",
    )

    # Series separators / ticks
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    for i, r in enumerate(rows):
        ax.get_xticklabels()[i].set_color(series_colors.get(r["series"], "black"))

    # Vertical dividers between series groups
    for i in range(1, len(rows)):
        if rows[i]["series"] != rows[i - 1]["series"]:
            ax.axvline(i - 0.5, color="gray", ls="--", alpha=0.5, lw=1)

    ax.set_ylabel("Average power (W)")
    ax.set_title(
        f"Cooling power comparison — series 4 / 5 / 6  ({T_START_C:.0f}→{T_END_C:.0f} °C)"
    )
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=9, loc="upper left")

    for bars in (bars1, bars2):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f"{h:.0f}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
            )

    # Series legend strip
    handles = [
        plt.Line2D([0], [0], color=series_colors[s], lw=4, label=SERIES_TITLES[s])
        for s in SERIES_PREFIXES
    ]
    ax2 = ax.twinx()
    ax2.set_yticks([])
    ax2.legend(handles=handles, loc="upper right", fontsize=8, title="series")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    csvs = discover_csvs()
    if not csvs:
        raise SystemExit(f"No series 4/5/6 CSVs found in {RAW_DATA}")

    rows: list[dict] = []
    for path in csvs:
        result = analyze(path)
        if result is not None:
            rows.append(result)

    if not rows:
        raise SystemExit("No runs produced a valid 37→32 °C window")

    # Keep discovery order (already sorted by filename → series then sub-index)
    print(f"{'file':<55} {'series':>6} {'dt_s':>7} {'flow':>8} {'P_tank':>8} {'P_flow':>8}")
    print("-" * 100)
    for r in rows:
        print(
            f"{r['file']:<55} {r['series']:>6} {r['duration_s']:7.0f} "
            f"{r['flow_ml_min']:7.1f}  {r['P_tank_W']:7.1f}  {r['P_flow_W']:7.1f}"
        )

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    cooldown_path = OUTPUT_DATA / "compare_series_4_5_6_cooldown.png"
    power_path = OUTPUT_DATA / "compare_series_4_5_6_power.png"
    plot_cooldowns(rows, cooldown_path)
    plot_power_bars(rows, power_path)
    print(f"\nWrote {cooldown_path}")
    print(f"Wrote {power_path}")


if __name__ == "__main__":
    main()
