"""Publication-ready chart generation for jailbreak metrics."""

from __future__ import annotations

import base64
import math
import os
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings(
    "ignore",
    message=".*distutils Version classes are deprecated.*",
    category=DeprecationWarning,
    module=r"chineseize_matplotlib.*",
)


_ONE_BY_ONE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Ww4uS8AAAAASUVORK5CYII="
)


def _write_placeholder_png(path: Path) -> None:
    path.write_bytes(_ONE_BY_ONE_PNG)


def _pick_best_chinese_font(installed_fonts: set[str]) -> str | None:
    candidates = [
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "Source Han Sans SC",
        "Source Han Sans CN",
        "Microsoft YaHei",
        "WenQuanYi Zen Hei",
        "PingFang SC",
        "SimHei",
    ]
    for name in candidates:
        if name in installed_fonts:
            return name
    return None


def _configure_matplotlib() -> tuple[object, object, object | None]:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    try:
        import seaborn as sns  # type: ignore
    except Exception:
        sns = None

    cjk_font: str | None = None
    # Prefer bundled CJK font package when available.
    try:
        import chineseize_matplotlib  # type: ignore

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            warnings.filterwarnings("ignore", message=".*distutils Version classes are deprecated.*")
            chineseize_matplotlib.chineseize()
        installed = {f.name for f in font_manager.fontManager.ttflist}
        cjk_font = _pick_best_chinese_font(installed)
    except Exception:
        installed = {f.name for f in font_manager.fontManager.ttflist}
        cjk_font = _pick_best_chinese_font(installed)

    if cjk_font:
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = [cjk_font, "Noto Sans CJK SC", "DejaVu Sans", "Arial"]

    matplotlib.rcParams["axes.unicode_minus"] = False
    if sns is not None:
        sns.set_theme(style="whitegrid", context="paper")
    matplotlib.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.6,
        }
    )
    if not cjk_font:
        matplotlib.rcParams["font.family"] = "serif"
        matplotlib.rcParams["font.serif"] = ["Times New Roman", "DejaVu Serif", "Liberation Serif"]

    return matplotlib, plt, sns


def _group_label_df(group_df: pd.DataFrame) -> pd.DataFrame:
    work = group_df.copy()
    if "total" in work.columns:
        safe_total = pd.to_numeric(work["total"], errors="coerce").fillna(0)
    else:
        safe_total = pd.Series([0] * len(work), index=work.index)
    if "uncertain_count" in work.columns:
        uncertain_count = pd.to_numeric(work["uncertain_count"], errors="coerce").fillna(0)
    else:
        uncertain_count = pd.Series([0] * len(work), index=work.index)
    denom = safe_total.replace(0, pd.NA)
    work["uncertain_rate"] = (uncertain_count / denom).fillna(0.0)
    if "source_file" in work.columns:
        base_labels = [str(x) for x in work.get("source_file", [])]
    else:
        base_labels = [str(model) for model in work.get("model_name", [])]
    counts: dict[str, int] = {}
    unique_labels: list[str] = []
    for label in base_labels:
        counts[label] = counts.get(label, 0) + 1
        idx = counts[label]
        unique_labels.append(label if idx == 1 else f"{label} ({idx})")
    work["group_label"] = unique_labels
    return work


def _build_plot_label_df(group_df: pd.DataFrame) -> pd.DataFrame:
    work = _group_label_df(group_df)
    full_labels = work["group_label"].astype(str).tolist()
    short_labels = [f"D{i + 1}" for i in range(len(full_labels))]
    work["full_label"] = full_labels
    work["group_label"] = short_labels
    work["label_legend"] = [f"{short} | {full}" for short, full in zip(short_labels, full_labels)]
    return work


def _mapping_table_height(num_rows: int) -> float:
    if num_rows <= 0:
        return 0.0
    num_cols = max(1, math.ceil(num_rows / 8))
    rows_per_col = math.ceil(num_rows / num_cols)
    return max(1.2, 0.32 * (rows_per_col + 1))


def _build_mapping_table_data(legend_rows: list[tuple[str, str]]) -> tuple[list[str], list[list[str]]]:
    if not legend_rows:
        return (["ID", "Full Name"], [])

    num_cols = max(1, math.ceil(len(legend_rows) / 8))
    rows_per_col = math.ceil(len(legend_rows) / num_cols)
    headers: list[str] = []
    for _ in range(num_cols):
        headers.extend(["ID", "Full Name"])

    cell_rows: list[list[str]] = []
    for row_idx in range(rows_per_col):
        row_cells: list[str] = []
        for col_idx in range(num_cols):
            item_idx = col_idx * rows_per_col + row_idx
            if item_idx < len(legend_rows):
                row_cells.extend(list(legend_rows[item_idx]))
            else:
                row_cells.extend(["", ""])
        cell_rows.append(row_cells)
    return headers, cell_rows


def _attach_mapping_table(fig: object, legend_rows: list[tuple[str, str]]) -> None:
    if not legend_rows:
        return

    num_cols = max(1, math.ceil(len(legend_rows) / 8))
    ax = fig.add_axes([0.08, 0.02, 0.84, 0.18])
    ax.axis("off")

    col_labels, cell_rows = _build_mapping_table_data(legend_rows)
    table = ax.table(cellText=cell_rows, colLabels=col_labels, loc="center", cellLoc="left", colLoc="left")
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)
    table.scale(1, 1.15)
    for (row, _col), cell in table.get_celld().items():
        cell.set_linewidth(0.0)
        cell.set_edgecolor("#FFFFFF")
        if row == 0:
            cell.set_text_props(weight="bold")
            cell.set_facecolor("#F2F4F7")
        else:
            cell.set_facecolor("#FFFFFF")


def _figure_with_table(plt: object, width: float, main_height: float, num_labels: int) -> tuple[object, object]:
    table_height = _mapping_table_height(num_labels)
    fig = plt.figure(figsize=(width, main_height + table_height))
    main_bottom = (table_height + 0.45) / (main_height + table_height)
    main_top = 1 - (0.35 / (main_height + table_height))
    ax = fig.add_axes([0.10, main_bottom, 0.78, max(0.35, main_top - main_bottom)])
    return fig, ax


def plot_success_rate(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "success_rate.png"
    try:
        _, plt, sns = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("Jailbreak Success Rate by Source File")
        ax.set_xlabel("Source File")
        ax.set_ylabel("Success Rate")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        fig.savefig(fig_path, bbox_inches="tight")
        plt.close()
        return fig_path

    work = _build_plot_label_df(group_df).sort_values(
        by=["success_rate", "total"], ascending=[False, False]
    ).reset_index(drop=True)
    y = pd.to_numeric(work["success_rate"], errors="coerce").fillna(0.0)
    lows = (y - pd.to_numeric(work["ci95_low"], errors="coerce").fillna(0.0)).clip(lower=0.0)
    highs = (pd.to_numeric(work["ci95_high"], errors="coerce").fillna(0.0) - y).clip(lower=0.0)
    fig, ax = _figure_with_table(plt, 10, max(4.5, 0.55 * len(work) + 1.5), len(work))
    color = "#336699"
    if sns is not None:
        sns.barplot(data=work, x="success_rate", y="group_label", ax=ax, color=color, orient="h")
    else:
        ax.barh(work["group_label"], y, color=color)
    ax.errorbar(y, work["group_label"], xerr=[lows, highs], fmt="none", ecolor="#1A1A1A", capsize=3, linewidth=1.1)
    ax.set_xlim(0, 1.08)
    ax.set_xlabel("Success Rate")
    ax.set_ylabel("Source File")
    ax.set_title("Jailbreak Success Rate with 95% Wilson CI")
    for idx, row in work.iterrows():
        yes_count = int(row.get("yes_count", 0) or 0)
        total = int(row.get("total", 0) or 0)
        text = f"p={row['success_rate']:.2f}, {yes_count}/{total}"
        x = min(1.04, float(row["success_rate"]) + 0.02)
        ax.text(x, idx, text, va="center", fontsize=8, ha="left", clip_on=False)
    _attach_mapping_table(fig, list(zip(work["group_label"].tolist(), work["full_label"].tolist())))
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close()
    return fig_path


def plot_risk_distribution(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "risk_distribution.png"
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("Risk Level Ratio Distribution")
        ax.set_xlabel("Source File")
        ax.set_ylabel("Ratio")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        fig.savefig(fig_path, bbox_inches="tight")
        plt.close()
        return fig_path

    work = _build_plot_label_df(group_df).sort_values(by=["risk_4_ratio", "risk_3_ratio"], ascending=[False, False]).reset_index(
        drop=True
    )
    fig, ax = _figure_with_table(plt, 11, max(4.5, 0.65 * len(work) + 1.5), len(work))
    x_labels = work["group_label"].tolist()
    bottom = [0.0] * len(work)
    colors = ["#C9D6DF", "#8DB3C7", "#5D89A8", "#D98989", "#B14848"]
    labels = [f"risk_{i}" for i in range(5)]
    for i in range(5):
        values = pd.to_numeric(work[f"risk_{i}_ratio"], errors="coerce").fillna(0.0).tolist()
        ax.bar(x_labels, values, bottom=bottom, label=labels[i], color=colors[i], width=0.72)
        bottom = [b + v for b, v in zip(bottom, values)]
    ax.set_ylim(0, 1.10)
    ax.set_ylabel("Ratio")
    ax.set_xlabel("Source File")
    ax.set_title("Risk Level Ratio Distribution by Group")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=28, ha="right")
    for idx, total in enumerate(pd.to_numeric(work["total"], errors="coerce").fillna(0).astype(int).tolist()):
        ax.text(idx, 1.03, f"n={total}", ha="center", va="bottom", fontsize=8)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.02), frameon=False, title="Risk Level")
    _attach_mapping_table(fig, list(zip(work["group_label"].tolist(), work["full_label"].tolist())))
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close()
    return fig_path


def plot_uncertainty_overview(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "uncertainty_overview.png"
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("Uncertainty Overview")
        ax.set_xlabel("Source File")
        ax.set_ylabel("Uncertain Rate")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        fig.savefig(fig_path, bbox_inches="tight")
        plt.close()
        return fig_path

    work = _build_plot_label_df(group_df).sort_values(
        by=["uncertain_rate", "total"], ascending=[False, False]
    ).reset_index(drop=True)
    fig, ax1 = _figure_with_table(plt, 11, max(4.5, 0.6 * len(work) + 1.5), len(work))
    x = list(range(len(work)))
    uncertain_rate = pd.to_numeric(work["uncertain_rate"], errors="coerce").fillna(0.0)
    totals = pd.to_numeric(work["total"], errors="coerce").fillna(0.0)
    bars = ax1.bar(x, uncertain_rate, color="#8C6BB1", alpha=0.9, width=0.72)
    ax1.set_ylim(0, 1)
    ax1.set_ylabel("Uncertain Rate")
    ax1.set_xlabel("Source File")
    ax1.set_title("Uncertainty Overview: Rate and Sample Size")
    ax1.set_xticks(x)
    ax1.set_xticklabels(work["group_label"].tolist(), rotation=28, ha="right")

    ax2 = ax1.twinx()
    ax2.plot(x, totals, color="#2F4F4F", marker="o", linewidth=1.5, label="Total Samples")
    ymax = max(1.0, float(totals.max()) * 1.2)
    ax2.set_ylim(0, ymax)
    ax2.set_ylabel("Total Samples")

    for idx, (bar, row) in enumerate(zip(bars, work.to_dict(orient="records"))):
        uncertain_count = int(row.get("uncertain_count", 0) or 0)
        total = int(row.get("total", 0) or 0)
        y = min(0.96, bar.get_height() + 0.02)
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            f"{uncertain_count}/{total}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    _attach_mapping_table(fig, list(zip(work["group_label"].tolist(), work["full_label"].tolist())))
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close()
    return fig_path


def plot_risk_heatmap(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "risk_heatmap.png"
    try:
        _, plt, sns = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("Risk Ratio Heatmap")
        ax.set_xlabel("Risk Level")
        ax.set_ylabel("Source File")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        fig.savefig(fig_path, bbox_inches="tight")
        plt.close()
        return fig_path

    work = _build_plot_label_df(group_df).sort_values(by=["risk_4_ratio", "risk_3_ratio"], ascending=[False, False]).reset_index(
        drop=True
    )
    heat = work[[f"risk_{i}_ratio" for i in range(5)]].copy()
    heat.index = work["group_label"]
    fig_h = max(4.5, len(heat) * 0.6 + 1.5)
    fig, ax = _figure_with_table(plt, 10, fig_h, len(work))
    if sns is not None:
        sns.heatmap(
            heat,
            ax=ax,
            cmap="YlOrRd",
            vmin=0.0,
            vmax=1.0,
            annot=True,
            fmt=".2%",
            cbar_kws={"label": "Ratio"},
            linewidths=0.3,
            linecolor="white",
        )
    else:
        im = ax.imshow(heat.values, cmap="YlOrRd", vmin=0.0, vmax=1.0, aspect="auto")
        ax.set_xticks(range(heat.shape[1]))
        ax.set_yticks(range(heat.shape[0]))
        ax.set_xticklabels(heat.columns.tolist())
        ax.set_yticklabels(heat.index.tolist())
        for r in range(heat.shape[0]):
            for c in range(heat.shape[1]):
                ax.text(c, r, f"{heat.iloc[r, c]:.2%}", ha="center", va="center", fontsize=8)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Ratio")
    ax.set_title("Risk Ratio Heatmap by Source File")
    ax.set_xlabel("Risk Level")
    ax.set_ylabel("Source File")
    _attach_mapping_table(fig, list(zip(work["group_label"].tolist(), work["full_label"].tolist())))
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close()
    return fig_path


def _records_from_dataframe(df: pd.DataFrame) -> list[dict]:
    to_dict = getattr(df, "to_dict", None)
    if callable(to_dict):
        try:
            return list(to_dict(orient="records"))
        except TypeError:
            pass
    rows = getattr(df, "_rows", None)
    if rows is not None:
        return list(rows)
    raise TypeError("Unsupported dataframe type for plotting")


def plot_multi_turn_cumulative_success(round_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "multi_turn_cumulative_success.png"
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    rows = _records_from_dataframe(round_df)
    if not rows:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("Multi-turn Cumulative Success Rate")
        ax.set_xlabel("Round")
        ax.set_ylabel("Cumulative Success Rate")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        fig.savefig(fig_path, bbox_inches="tight")
        plt.close()
        return fig_path

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("source_file", "unknown") or "unknown"), []).append(row)

    fig, ax = plt.subplots(figsize=(9, max(4.5, 3.8 + 0.2 * len(grouped))))
    palette = ["#2E5EAA", "#C85C41", "#4C956C", "#9B6EF3", "#A67C52", "#D45087"]
    for idx, (source_file, source_rows) in enumerate(sorted(grouped.items())):
        source_rows.sort(key=lambda row: int(row.get("round", 0) or 0))
        x = [int(row.get("round", 0) or 0) for row in source_rows]
        y = [float(row.get("cumulative_success_rate", 0.0) or 0.0) for row in source_rows]
        ax.plot(x, y, marker="o", linewidth=1.8, color=palette[idx % len(palette)], label=source_file)

    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Round")
    ax.set_ylabel("Cumulative Success Rate")
    ax.set_title("Multi-turn Cumulative Success Rate by Round")
    ax.legend(loc="best", frameon=False)
    fig.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close()
    return fig_path


def plot_multi_turn_first_success_distribution(round_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "multi_turn_first_success_distribution.png"
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    rows = _records_from_dataframe(round_df)
    if not rows:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("First Success Round Distribution")
        ax.set_xlabel("Round")
        ax.set_ylabel("First Success Count")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        fig.savefig(fig_path, bbox_inches="tight")
        plt.close()
        return fig_path

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("source_file", "unknown") or "unknown"), []).append(row)

    fig, ax = plt.subplots(figsize=(9, max(4.5, 3.8 + 0.2 * len(grouped))))
    width = 0.8 / max(1, len(grouped))
    palette = ["#355070", "#B56576", "#6D597A", "#43AA8B", "#BC6C25", "#577590"]
    for idx, (source_file, source_rows) in enumerate(sorted(grouped.items())):
        source_rows.sort(key=lambda row: int(row.get("round", 0) or 0))
        x = [int(row.get("round", 0) or 0) for row in source_rows]
        y = [int(row.get("first_success_count", 0) or 0) for row in source_rows]
        shifted_x = [value + (idx - (len(grouped) - 1) / 2) * width for value in x]
        ax.bar(shifted_x, y, width=width, color=palette[idx % len(palette)], label=source_file)

    all_rounds = sorted({int(row.get("round", 0) or 0) for row in rows})
    ax.set_xticks(all_rounds)
    ax.set_xlabel("Round")
    ax.set_ylabel("First Success Count")
    ax.set_title("First Successful Jailbreak Round Distribution")
    ax.legend(loc="best", frameon=False)
    fig.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close()
    return fig_path
