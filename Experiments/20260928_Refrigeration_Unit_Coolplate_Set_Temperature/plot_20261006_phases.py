"""Plot each phase of the 2026-10-06 to 2026-10-08 −4 °C cool-plate log.

Reads raw_data/20261006_153226_sensors.csv and writes one PNG and one
interactive HTML per phase to output_data/. Open an HTML file in a browser
to zoom and hover for the clock time.
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
CSV_PATH = HERE / "raw_data" / "20261006_153226_sensors.csv"
OUTPUT_DATA = HERE / "output_data"

SETPOINT_C = -4.0
MAX_POINTS = 4000

TEMP_SERIES = (
    ("plate_1_c", "Cool plate 1", "#08519c", "solid"),
    ("plate_1b_c", "Cool plate 1 backup", "#6baed6", "dash"),
    ("plate_2_c", "Cool plate 2", "#d94801", "solid"),
    ("plate_2b_c", "Cool plate 2 backup", "#fdae6b", "dash"),
    ("cartrige_in_c", "Cartridge in", "#006d2c", "solid"),
    ("cartrige_out_c", "Cartridge out", "#74c476", "solid"),
)


@dataclass(frozen=True)
class Phase:
    slug: str
    title: str
    start: str
    end: str
    show_setpoint: bool


PHASES = (
    Phase(
        "01_49ml_min",
        "Phase 1 · 6 Oct 15:32–17:00 · 49 ml/min through the cartridge",
        "2026-10-06 15:32:26",
        "2026-10-06 17:00:00",
        True,
    ),
    Phase(
        "02_idle_warmup",
        "Phase 2 · 6 Oct 17:00 – 7 Oct 09:07 · compressor off, plates warm to room",
        "2026-10-06 17:00:00",
        "2026-10-07 09:07:08",
        False,
    ),
    Phase(
        "03_setpoint_steps",
        "Phase 3 · 7 Oct 09:07–11:38 · shutoff steps from −1 °C to −3 °C",
        "2026-10-07 09:07:08",
        "2026-10-07 11:37:54",
        True,
    ),
    Phase(
        "04_hold_minus4",
        "Phase 4 · 7 Oct 11:38–12:40 · both plates reach −4 °C",
        "2026-10-07 11:37:54",
        "2026-10-07 12:40:26",
        True,
    ),
    Phase(
        "05_lost_setpoint",
        "Phase 5 · 7 Oct 12:40–14:49 · command stays on and plates warm to +1 °C",
        "2026-10-07 12:40:26",
        "2026-10-07 14:48:40",
        True,
    ),
    Phase(
        "06_recovered",
        "Phase 6 · 7 Oct 14:49–18:03 · cycles return to −4 °C",
        "2026-10-07 14:48:40",
        "2026-10-07 18:03:04",
        True,
    ),
    Phase(
        "07_stuck_plus1",
        "Phase 7 · 7 Oct 18:03 – 8 Oct 09:40 · command on, plates hold near +1.5 °C",
        "2026-10-07 18:03:04",
        "2026-10-08 09:40:23",
        True,
    ),
    Phase(
        "08_flow_28ml_min",
        "Phase 8 · 8 Oct 09:40–09:57 · 28 ml/min, plates rise to about +3.3 °C",
        "2026-10-08 09:40:23",
        "2026-10-08 09:57:00",
        True,
    ),
)


def _load() -> pd.DataFrame:
    columns = ["timestamp", "flow_sensor_ml_per_min", "compressor_cooling", *[c for c, *_ in TEMP_SERIES]]
    df = pd.read_csv(CSV_PATH, usecols=columns, parse_dates=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    for column, *_ in TEMP_SERIES:
        df[column] = despike(df[column])
    t_s = (df.index - df.index[0]).total_seconds().to_numpy()
    command = df["compressor_cooling"].astype(int).to_numpy() == 1
    really_on, debounced = compressor_really_on(t_s, command)
    df["cooling_command"] = debounced.astype(float)
    df["compressor_on"] = really_on.astype(float)
    df["flow_ml_per_min"] = df["flow_sensor_ml_per_min"].clip(lower=0)
    return df


def _rule_for(index: pd.DatetimeIndex) -> str:
    duration_s = (index[-1] - index[0]).total_seconds()
    step_s = max(2.0, duration_s / MAX_POINTS)
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
    if phase.show_setpoint:
        ax_temp.axhline(
            SETPOINT_C,
            color="black",
            linestyle="--",
            linewidth=1.1,
            label="Set temperature (−4 °C)",
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

    ax_comp.step(times, sampled["cooling_command"], where="post", color="0.55", linewidth=1.3, label="Cooling command")
    ax_comp.fill_between(times, 0, 1, where=on, step="post", color="0.45", alpha=0.35, linewidth=0, label="Compressor on")
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
    if phase.show_setpoint:
        fig.add_trace(
            go.Scatter(
                x=times,
                y=np.full(len(times), SETPOINT_C),
                mode="lines",
                name="Set temperature (−4 °C)",
                line=dict(color="black", dash="dash", width=1.1),
                hovertemplate="%{y:.1f} °C<extra></extra>",
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
    df = _load()
    OUTPUT_DATA.mkdir(exist_ok=True)
    for phase in PHASES:
        window = df.loc[phase.start:phase.end]
        sampled = _resample(window)
        png = OUTPUT_DATA / f"phase_{phase.slug}_20261006_153226.png"
        html = OUTPUT_DATA / f"phase_{phase.slug}_20261006_153226.html"
        _plot_png(phase, sampled, png)
        _plot_html(phase, sampled, html)
        print(f"{phase.slug}: {len(window)} samples -> {len(sampled)} plotted")
        print(f"  {png.name}")
        print(f"  {html.name}")


if __name__ == "__main__":
    main()
