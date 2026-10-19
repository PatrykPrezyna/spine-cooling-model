"""Plot the 2026-10-13 cool-plate log, with and without cartridge flow.

Reads raw_data/20261013_140723_sensors.csv and writes one PNG and one
interactive HTML for the full run and for each phase to output_data/.
Open an HTML file in a browser to zoom and hover for the clock time.

Grey bands are compressor-on time (60 s lockout after each real off;
command pulses shorter than 2 s are ignored). Single-sample grounding
spikes are removed in the plot only. Plate 2 also has a few impossible
readings (about −388 °C); those samples are interpolated and the raw log
is not rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from plot_coolplate_temperatures import compressor_really_on, despike

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "raw_data" / "20261013_140723_sensors.csv"
OUTPUT_DATA = HERE / "output_data"

MAX_POINTS = 4000
FAULT_BELOW_C = -20.0

TEMP_SERIES = (
    ("plate_1_c", "Cool plate 1", "#08519c", "solid"),
    ("plate_1b_c", "Cool plate 1 backup", "#6baed6", "dash"),
    ("plate_2_c", "Cool plate 2", "#d94801", "solid"),
    ("plate_2b_c", "Cool plate 2 backup", "#fdae6b", "dash"),
    ("cartrige_in_c", "Cartridge in", "#006d2c", "solid"),
    ("cartrige_out_c", "Cartridge out", "#74c476", "solid"),
    ("catheter_in_c", "Catheter in", "#6a51a3", "solid"),
    ("catheter_out_c", "Catheter out", "#9e9ac8", "solid"),
)


@dataclass(frozen=True)
class Phase:
    slug: str
    title: str
    start: str
    end: str


PHASES = (
    Phase(
        "00_full_run",
        "13 Oct 14:07–16:50 · no flow until 15:25, then 57 rpm",
        "2026-10-13 14:07:24",
        "2026-10-13 16:50:42",
    ),
    Phase(
        "01_no_flow",
        "No flow · 13 Oct 14:07–15:25 · plate 1 cuts out near −1 °C",
        "2026-10-13 14:07:24",
        "2026-10-13 15:25:05",
    ),
    Phase(
        "02_flow_57rpm",
        "57 rpm · 13 Oct 15:25–16:50 · flow about 42 ml/min through the cartridge",
        "2026-10-13 15:25:05",
        "2026-10-13 16:50:42",
    ),
)


def _repair_faults(series: pd.Series) -> tuple[pd.Series, int]:
    """Replace impossible readings, then single-sample grounding spikes."""

    n_faults = int((series < FAULT_BELOW_C).sum())
    cleaned = series.mask(series < FAULT_BELOW_C)
    cleaned = cleaned.interpolate(limit_direction="both")
    cleaned = despike(cleaned)
    return cleaned, n_faults


def _load() -> pd.DataFrame:
    columns = [
        "timestamp",
        "flow_sensor_ml_per_min",
        "compressor_cooling",
        *[column for column, *_ in TEMP_SERIES],
    ]
    df = pd.read_csv(CSV_PATH, usecols=columns, parse_dates=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    for column, label, *_ in TEMP_SERIES:
        cleaned, n_faults = _repair_faults(df[column])
        if n_faults:
            print(f"  {label}: interpolated {n_faults} impossible samples")
        df[column] = cleaned
    t_s = (df.index - df.index[0]).total_seconds().to_numpy()
    command = df["compressor_cooling"].astype(int).to_numpy() == 1
    really_on, debounced = compressor_really_on(t_s, command)
    df["cooling_command"] = debounced.astype(float)
    df["compressor_on"] = really_on.astype(float)
    df["flow_ml_per_min"] = df["flow_sensor_ml_per_min"].clip(lower=0)
    return df


def _rule_for(index: pd.DatetimeIndex) -> str:
    duration_s = (index[-1] - index[0]).total_seconds()
    step_s = max(1.0, duration_s / MAX_POINTS)
    return f"{int(round(step_s))}s"


def _resample(df: pd.DataFrame) -> pd.DataFrame:
    rule = _rule_for(df.index)
    temp_cols = [column for column, *_ in TEMP_SERIES]
    out = df[temp_cols].resample(rule).median()
    out["flow_ml_per_min"] = df["flow_ml_per_min"].resample(rule).median()
    out["cooling_command"] = df["cooling_command"].resample(rule).max()
    out["compressor_on"] = df["compressor_on"].resample(rule).max()
    return out.dropna(subset=["plate_1_c"])


def _on_spans(times: pd.DatetimeIndex, on: np.ndarray) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    spans: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    start = None
    for i, is_on in enumerate(on):
        if is_on and start is None:
            start = times[i]
        elif not is_on and start is not None:
            spans.append((start, times[i]))
            start = None
    if start is not None:
        spans.append((start, times[-1]))
    return spans


def _plot_png(phase: Phase, sampled: pd.DataFrame, out: Path) -> None:
    times = sampled.index
    on = sampled["compressor_on"].to_numpy() == 1
    fig, (ax_temp, ax_comp, ax_flow) = plt.subplots(
        3,
        1,
        sharex=True,
        figsize=(11, 8.5),
        gridspec_kw={"height_ratios": [3.2, 0.7, 0.9]},
    )

    for ax in (ax_temp, ax_flow):
        ax.fill_between(
            times,
            0,
            1,
            where=on,
            transform=ax.get_xaxis_transform(),
            step="post",
            color="0.75",
            alpha=0.45,
            linewidth=0,
        )

    for column, label, color, dash in TEMP_SERIES:
        ax_temp.plot(
            times,
            sampled[column],
            color=color,
            linestyle="--" if dash == "dash" else "-",
            linewidth=1.4,
            label=label,
        )

    ax_temp.set_ylabel("Temperature (°C)")
    ax_temp.grid(True, alpha=0.3)
    ax_temp.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=4,
        fontsize=8,
        frameon=False,
    )

    ax_comp.step(
        times,
        sampled["cooling_command"],
        where="post",
        color="0.55",
        linewidth=1.3,
        label="Cooling command",
    )
    ax_comp.fill_between(
        times,
        0,
        1,
        where=on,
        step="post",
        color="0.45",
        alpha=0.35,
        linewidth=0,
        label="Compressor on",
    )
    ax_comp.set_ylim(-0.05, 1.25)
    ax_comp.set_yticks([0, 1])
    ax_comp.set_yticklabels(["off", "on"])
    ax_comp.set_ylabel("Compressor")
    ax_comp.grid(True, alpha=0.3)
    ax_comp.legend(loc="upper right", fontsize=8)

    ax_flow.plot(times, sampled["flow_ml_per_min"], color="#54278f", linewidth=1.4)
    ax_flow.set_ylabel("Flow (ml/min)")
    ax_flow.set_xlabel("Time")
    flow_max = float(sampled["flow_ml_per_min"].max())
    if flow_max < 1:
        ax_flow.set_ylim(0, 5)
    else:
        ax_flow.set_ylim(0, flow_max * 1.15)
    ax_flow.grid(True, alpha=0.3)

    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax_flow.xaxis.set_major_locator(locator)
    ax_flow.xaxis.set_major_formatter(formatter)
    fig.suptitle(phase.title, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _plot_html(phase: Phase, sampled: pd.DataFrame, out: Path) -> None:
    times = sampled.index
    on = sampled["compressor_on"].to_numpy() == 1
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.62, 0.16, 0.22],
        vertical_spacing=0.05,
    )
    for start, end in _on_spans(times, on):
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor="rgba(160,160,160,0.35)",
            line_width=0,
            row="all",
            col=1,
        )
    for column, label, color, dash in TEMP_SERIES:
        fig.add_trace(
            go.Scatter(
                x=times,
                y=sampled[column],
                mode="lines",
                name=label,
                line=dict(color=color, dash=dash, width=1.5),
                hovertemplate="%{y:.2f} °C<extra></extra>",
            ),
            row=1,
            col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=sampled["cooling_command"],
            mode="lines",
            name="Cooling command",
            line=dict(color="rgb(140,140,140)", shape="hv", width=1.4),
            hovertemplate="%{y:.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=sampled["compressor_on"],
            mode="lines",
            name="Compressor on",
            line=dict(color="rgb(70,70,70)", shape="hv", width=1.4),
            fill="tozeroy",
            fillcolor="rgba(70,70,70,0.25)",
            hovertemplate="%{y:.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=sampled["flow_ml_per_min"],
            mode="lines",
            name="Flow",
            line=dict(color="#54278f", width=1.5),
            hovertemplate="%{y:.1f} ml/min<extra></extra>",
        ),
        row=3,
        col=1,
    )
    fig.update_layout(
        title=phase.title,
        hovermode="x unified",
        template="plotly_white",
        height=860,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(t=100),
    )
    fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
    fig.update_yaxes(
        title_text="Compressor",
        range=[-0.05, 1.25],
        tickvals=[0, 1],
        ticktext=["off", "on"],
        row=2,
        col=1,
    )
    fig.update_yaxes(title_text="Flow (ml/min)", rangemode="tozero", row=3, col=1)
    fig.update_xaxes(title_text="Time", row=3, col=1)
    fig.write_html(out, include_plotlyjs=True, config={"scrollZoom": True, "displaylogo": False})


def main() -> None:
    print(CSV_PATH.name)
    df = _load()
    OUTPUT_DATA.mkdir(exist_ok=True)
    for phase in PHASES:
        window = df.loc[phase.start:phase.end]
        sampled = _resample(window)
        png = OUTPUT_DATA / f"phase_{phase.slug}_20261013_140723.png"
        html = OUTPUT_DATA / f"phase_{phase.slug}_20261013_140723.html"
        _plot_png(phase, sampled, png)
        _plot_html(phase, sampled, html)
        print(f"{phase.slug}: {len(window)} samples -> {len(sampled)} plotted")
        print(f"  {png.name}")
        print(f"  {html.name}")


if __name__ == "__main__":
    main()
