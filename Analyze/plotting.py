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
    if "model_name" in work.columns:
        base_labels = [str(x) for x in work.get("model_name", [])]
    elif "analysis_group" in work.columns:
        base_labels = [str(x) for x in work.get("analysis_group", [])]
    elif "source_file" in work.columns:
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


def _build_dimension_plot_df(group_df: pd.DataFrame) -> pd.DataFrame:
    work = _group_label_df(group_df).copy()
    work["full_label"] = work["analysis_group"].astype(str)
    work["group_label"] = work["analysis_group"].astype(str)
    return work.sort_values(by=["success_rate", "high_risk_ratio", "total"], ascending=[False, False, False]).reset_index(drop=True)


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


def _mapping_table_axes_rect(main_height: float, table_height: float) -> tuple[float, float, float, float]:
    total_height = max(0.1, main_height + table_height)
    bottom = 0.02
    height = min(0.30, max(0.12, table_height / total_height))
    return (0.08, bottom, 0.84, height)


def _save_figure(fig: object, fig_path: Path) -> None:
    fig.savefig(fig_path, bbox_inches="tight", pad_inches=0.28)


def _attach_mapping_table(fig: object, legend_rows: list[tuple[str, str]]) -> None:
    if not legend_rows:
        return

    num_cols = max(1, math.ceil(len(legend_rows) / 8))
    rows_per_col = math.ceil(len(legend_rows) / num_cols)
    table_height = _mapping_table_height(len(legend_rows))
    main_height = max(4.5, 0.42 * rows_per_col + 2.5)
    ax = fig.add_axes(_mapping_table_axes_rect(main_height, table_height))
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
        _save_figure(fig, fig_path)
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
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_dangerous_success_rate(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    return plot_success_rate(group_df, output_dir)


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
        _save_figure(fig, fig_path)
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
    _save_figure(fig, fig_path)
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
        _save_figure(fig, fig_path)
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
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_high_risk_ratio(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "high_risk_ratio.png"
    try:
        _, plt, sns = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("High-risk Ratio")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        _save_figure(fig, fig_path)
        plt.close()
        return fig_path

    work = _build_plot_label_df(group_df).sort_values(by=["high_risk_ratio", "total"], ascending=[False, False]).reset_index(drop=True)
    fig, ax = _figure_with_table(plt, 10, max(4.5, 0.55 * len(work) + 1.5), len(work))
    values = pd.to_numeric(work["high_risk_ratio"], errors="coerce").fillna(0.0)
    color = "#AA4A44"
    if sns is not None:
        sns.barplot(data=work, x="high_risk_ratio", y="group_label", ax=ax, color=color, orient="h")
    else:
        ax.barh(work["group_label"], values, color=color)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("High-risk Ratio")
    ax.set_ylabel("Group")
    ax.set_title("High-risk Output Ratio by Group")
    _attach_mapping_table(fig, list(zip(work["group_label"].tolist(), work["full_label"].tolist())))
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_high_risk_vs_success(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "high_risk_vs_success.png"
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("High-risk vs Dangerous Success")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        _save_figure(fig, fig_path)
        plt.close()
        return fig_path

    work = _group_label_df(group_df)
    fig, ax = plt.subplots(figsize=(8.5, max(4.5, 3.8 + 0.12 * len(work))))
    x = pd.to_numeric(work["success_rate"], errors="coerce").fillna(0.0)
    y = pd.to_numeric(work["high_risk_ratio"], errors="coerce").fillna(0.0)
    sizes = 50 + 12 * pd.to_numeric(work["total"], errors="coerce").fillna(0.0)
    ax.scatter(x, y, s=sizes, color="#9C3D54", alpha=0.8, edgecolor="white", linewidth=0.8)
    for _, row in work.iterrows():
        ax.text(
            float(row["success_rate"]) + 0.01,
            float(row["high_risk_ratio"]) + 0.01,
            str(row["group_label"]),
            fontsize=8,
            clip_on=False,
        )
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("Dangerous Jailbreak Rate")
    ax.set_ylabel("High-risk Ratio")
    ax.set_title("High-risk vs Dangerous Success by Group")
    fig.tight_layout(pad=1.4)
    _save_figure(fig, fig_path)
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
        _save_figure(fig, fig_path)
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
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_dimension_success_ranking(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "dimension_success_ranking.png"
    try:
        _, plt, sns = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("Attack Dimension Success Ranking")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        _save_figure(fig, fig_path)
        plt.close()
        return fig_path

    work = _build_dimension_plot_df(group_df)
    y = pd.to_numeric(work["success_rate"], errors="coerce").fillna(0.0)
    lows = (y - pd.to_numeric(work["ci95_low"], errors="coerce").fillna(0.0)).clip(lower=0.0)
    highs = (pd.to_numeric(work["ci95_high"], errors="coerce").fillna(0.0) - y).clip(lower=0.0)
    fig, ax = plt.subplots(figsize=(10.5, max(5.0, 0.55 * len(work) + 1.8)))
    color = "#255F85"
    if sns is not None:
        sns.barplot(data=work, x="success_rate", y="group_label", ax=ax, color=color, orient="h")
    else:
        ax.barh(work["group_label"], y, color=color)
    ax.errorbar(y, work["group_label"], xerr=[lows, highs], fmt="none", ecolor="#1A1A1A", capsize=3, linewidth=1.1)
    ax.set_xlim(0, min(1.0, float(y.max()) * 1.35 + 0.02) if len(work) else 1.0)
    ax.set_xlabel("Dangerous Jailbreak Rate")
    ax.set_ylabel("Attack Dimension")
    ax.set_title("Attack Dimension Ranking by Dangerous Jailbreak Rate")
    for idx, row in work.iterrows():
        label_x = min(ax.get_xlim()[1] * 0.985, float(row["success_rate"]) + max(0.01, ax.get_xlim()[1] * 0.015))
        ax.text(label_x, idx, f"{int(row.get('yes_count', 0))}/{int(row.get('total', 0))}", va="center", fontsize=8, ha="left")
    fig.tight_layout()
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_dimension_risk_heatmap(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "dimension_risk_heatmap.png"
    try:
        _, plt, sns = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("Attack Dimension Risk Heatmap")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        _save_figure(fig, fig_path)
        plt.close()
        return fig_path

    work = _build_dimension_plot_df(group_df)
    heat = work[[f"risk_{i}_ratio" for i in range(5)]].copy()
    heat.index = work["group_label"]
    fig, ax = plt.subplots(figsize=(9.5, max(4.8, 0.55 * len(heat) + 1.6)))
    if sns is not None:
        sns.heatmap(
            heat,
            ax=ax,
            cmap="YlOrRd",
            vmin=0.0,
            vmax=1.0,
            annot=True,
            fmt=".2f",
            cbar_kws={"label": "Ratio"},
            linewidths=0.4,
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
                ax.text(c, r, f"{heat.iloc[r, c]:.2f}", ha="center", va="center", fontsize=8)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Ratio")
    ax.set_title("Risk Distribution Heatmap Across Attack Dimensions")
    ax.set_xlabel("Risk Level")
    ax.set_ylabel("Attack Dimension")
    ax.set_xticklabels([f"risk_{i}" for i in range(5)], rotation=0)
    fig.tight_layout()
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_dimension_profile_panel(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "dimension_profile_panel.png"
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("Attack Dimension Profile Panel")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        _save_figure(fig, fig_path)
        plt.close()
        return fig_path

    work = _build_dimension_plot_df(group_df)
    x = list(range(len(work)))
    width = 0.24
    fig, ax = plt.subplots(figsize=(12, max(5.2, 4.2 + 0.1 * len(work))))
    success = pd.to_numeric(work["success_rate"], errors="coerce").fillna(0.0)
    high_risk = pd.to_numeric(work["high_risk_ratio"], errors="coerce").fillna(0.0)
    uncertain = pd.to_numeric(work["uncertain_rate"], errors="coerce").fillna(0.0)
    ax.bar([v - width for v in x], success, width=width, label="Success Rate", color="#2C699A")
    ax.bar(x, high_risk, width=width, label="High-risk Ratio", color="#B23A48")
    ax.bar([v + width for v in x], uncertain, width=width, label="Uncertain Rate", color="#8C6BB1")
    ax.set_ylim(0, 1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(work["group_label"].tolist(), rotation=28, ha="right")
    ax.set_ylabel("Ratio")
    ax.set_xlabel("Attack Dimension")
    ax.set_title("Attack Dimension Profile: Success, High-risk, and Uncertainty")
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_dimension_priority_quadrants(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "dimension_priority_quadrants.png"
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.set_title("Attack Dimension Priority Quadrants")
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        _save_figure(fig, fig_path)
        plt.close()
        return fig_path

    work = _build_dimension_plot_df(group_df)
    x = pd.to_numeric(work["success_rate"], errors="coerce").fillna(0.0)
    y = pd.to_numeric(work["high_risk_ratio"], errors="coerce").fillna(0.0)
    sizes = 120 + 10 * pd.to_numeric(work["total"], errors="coerce").fillna(0.0)
    x_mid = float(x.mean()) if len(x) else 0.0
    y_mid = float(y.mean()) if len(y) else 0.0
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.scatter(x, y, s=sizes, color="#A23E48", alpha=0.78, edgecolor="white", linewidth=1.0)
    ax.axvline(x_mid, color="#7A7A7A", linestyle="--", linewidth=1.0)
    ax.axhline(y_mid, color="#7A7A7A", linestyle="--", linewidth=1.0)
    for _, row in work.iterrows():
        ax.text(
            float(row["success_rate"]) + 0.002,
            float(row["high_risk_ratio"]) + 0.0005,
            str(row["group_label"]),
            fontsize=8,
            clip_on=False,
        )
    ax.set_xlim(0, min(1.0, float(x.max()) * 1.25 + 0.01) if len(x) else 1.0)
    ax.set_ylim(0, min(1.0, float(y.max()) * 1.25 + 0.01) if len(y) else 1.0)
    ax.set_xlabel("Dangerous Jailbreak Rate")
    ax.set_ylabel("High-risk Ratio")
    ax.set_title("Attack Dimension Priority Quadrants")
    fig.tight_layout(pad=1.4)
    _save_figure(fig, fig_path)
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
        _save_figure(fig, fig_path)
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
    _save_figure(fig, fig_path)
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
        _save_figure(fig, fig_path)
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
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def _group_metric_rows(group_df: pd.DataFrame) -> list[dict]:
    return _records_from_dataframe(group_df)


def _build_label_distribution_rows(group_df: pd.DataFrame) -> list[dict]:
    rows = _group_metric_rows(group_df)
    built: list[dict] = []
    for row in rows:
        built.append(
            {
                "group_label": str(row.get("analysis_group", "unknown") or "unknown"),
                "blocked": float(row.get("blocked_count", 0) or 0),
                "benign": float(row.get("benign_count", 0) or 0),
                "ambiguous": float(row.get("ambiguous_count", 0) or 0),
                "harmful_informational": float(row.get("harmful_informational_count", 0) or 0),
                "harmful_actionable": float(row.get("harmful_actionable_count", 0) or 0),
            }
        )
    return built


def _build_ambiguity_breakdown_rows(group_df: pd.DataFrame) -> list[dict]:
    rows = _group_metric_rows(group_df)
    built: list[dict] = []
    for row in rows:
        built.append(
            {
                "group_label": str(row.get("analysis_group", "unknown") or "unknown"),
                "boundary_mixed": float(row.get("reason_boundary_mixed_count", 0) or 0),
                "target_unclear": float(row.get("reason_target_unclear_count", 0) or 0),
                "insufficient_evidence": float(row.get("reason_insufficient_evidence_count", 0) or 0),
                "context_conflict": float(row.get("reason_context_conflict_count", 0) or 0),
            }
        )
    return built


def _build_assistance_harm_matrix_rows(group_df: pd.DataFrame) -> list[dict]:
    rows = _group_metric_rows(group_df)
    built: list[dict] = []
    for row in rows:
        descriptive_ratio = float(row.get("assistance_descriptive_ratio", 0.0) or 0.0)
        procedural_ratio = float(row.get("assistance_procedural_ratio", 0.0) or 0.0)
        operational_ratio = float(row.get("assistance_operational_ratio", 0.0) or 0.0)
        ambiguous_total = float(row.get("ambiguous_count", 0) or 0)
        harmful_total = float((row.get("harmful_informational_count", 0) or 0) + (row.get("harmful_actionable_count", 0) or 0))
        harmful_total = 1.0 if harmful_total > 0 else 0.0
        ambiguous_total = 1.0 if ambiguous_total > 0 else 0.0
        built.append(
            {
                "group_label": str(row.get("analysis_group", "unknown") or "unknown"),
                "descriptive_ambiguous": descriptive_ratio * ambiguous_total,
                "descriptive_harmful": descriptive_ratio * harmful_total,
                "procedural_ambiguous": procedural_ratio * ambiguous_total,
                "procedural_harmful": 0.0,
                "operational_ambiguous": 0.0,
                "operational_harmful": operational_ratio * harmful_total,
            }
        )
    return built


def _build_risk_profile_rows(group_df: pd.DataFrame) -> list[dict]:
    rows = _group_metric_rows(group_df)
    built: list[dict] = []
    for row in rows:
        built.append(
            {
                "group_label": str(row.get("analysis_group", "unknown") or "unknown"),
                "harm_intent": float(row.get("harm_intent_mean", 0.0) or 0.0),
                "actionability": float(row.get("actionability_mean", 0.0) or 0.0),
                "specificity": float(row.get("specificity_mean", 0.0) or 0.0),
                "evasion": float(row.get("evasion_mean", 0.0) or 0.0),
                "impact": float(row.get("impact_mean", 0.0) or 0.0),
            }
        )
    return built


def _placeholder_first(group_df: pd.DataFrame, output_dir: str | Path, filename: str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / filename
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if getattr(group_df, "empty", True):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", transform=ax.transAxes)
        fig.tight_layout()
        _save_figure(fig, fig_path)
        plt.close()
        return fig_path

    # The richer figures can use a compact placeholder chart until full rendering is implemented.
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.text(0.5, 0.5, filename.replace(".png", "").replace("_", "\n"), ha="center", va="center", transform=ax.transAxes)
    ax.set_axis_off()
    fig.tight_layout()
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_label_distribution(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "label_distribution.png"
    rows = _build_label_distribution_rows(group_df)
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if not rows:
        return _placeholder_first(group_df, output_dir, "label_distribution.png")

    fig, ax = plt.subplots(figsize=(11, max(4.8, 0.6 * len(rows) + 1.6)))
    x_labels = [row["group_label"] for row in rows]
    bottom = [0.0] * len(rows)
    series = [
        ("blocked", "#7A8C99"),
        ("benign", "#7FB069"),
        ("ambiguous", "#D6A85F"),
        ("harmful_informational", "#D36E70"),
        ("harmful_actionable", "#8C2F39"),
    ]
    for key, color in series:
        values = [row[key] for row in rows]
        ax.bar(x_labels, values, bottom=bottom, label=key, color=color, width=0.72)
        bottom = [base + value for base, value in zip(bottom, values)]
    ax.set_ylabel("Count")
    ax.set_xlabel("Analysis Group")
    ax.set_title("Final Label Distribution by Group")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=28, ha="right")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.02), frameon=False)
    fig.tight_layout()
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_ambiguity_breakdown(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "ambiguity_breakdown.png"
    rows = _build_ambiguity_breakdown_rows(group_df)
    try:
        _, plt, _ = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if not rows:
        return _placeholder_first(group_df, output_dir, "ambiguity_breakdown.png")

    fig, ax = plt.subplots(figsize=(10.5, max(4.8, 0.6 * len(rows) + 1.6)))
    x_labels = [row["group_label"] for row in rows]
    bottom = [0.0] * len(rows)
    series = [
        ("boundary_mixed", "#C97C5D"),
        ("target_unclear", "#D9B44A"),
        ("insufficient_evidence", "#7D8CA3"),
        ("context_conflict", "#8D6A9F"),
    ]
    for key, color in series:
        values = [row[key] for row in rows]
        ax.bar(x_labels, values, bottom=bottom, label=key, color=color, width=0.72)
        bottom = [base + value for base, value in zip(bottom, values)]
    ax.set_ylabel("Count")
    ax.set_xlabel("Analysis Group")
    ax.set_title("Ambiguity Reason Breakdown")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=28, ha="right")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.02), frameon=False)
    fig.tight_layout()
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_assistance_vs_harm_matrix(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "assistance_vs_harm_matrix.png"
    rows = _build_assistance_harm_matrix_rows(group_df)
    try:
        _, plt, sns = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if not rows:
        return _placeholder_first(group_df, output_dir, "assistance_vs_harm_matrix.png")

    heat_rows = []
    y_labels = []
    for row in rows:
        heat_rows.append(
            [
                row["descriptive_ambiguous"],
                row["descriptive_harmful"],
                row["procedural_ambiguous"],
                row["procedural_harmful"],
                row["operational_ambiguous"],
                row["operational_harmful"],
            ]
        )
        y_labels.append(row["group_label"])

    fig, ax = plt.subplots(figsize=(11, max(4.8, 0.6 * len(rows) + 1.6)))
    x_labels = [
        "descriptive\nambiguous",
        "descriptive\nharmful",
        "procedural\nambiguous",
        "procedural\nharmful",
        "operational\nambiguous",
        "operational\nharmful",
    ]
    if sns is not None:
        sns.heatmap(heat_rows, ax=ax, cmap="YlOrBr", annot=True, fmt=".2f", cbar_kws={"label": "Weighted Ratio"})
    else:
        im = ax.imshow(heat_rows, cmap="YlOrBr", aspect="auto")
        for r, values in enumerate(heat_rows):
            for c, value in enumerate(values):
                ax.text(c, r, f"{value:.2f}", ha="center", va="center", fontsize=8)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Weighted Ratio")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=0)
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Assistance vs Harm Slice")
    ax.set_ylabel("Analysis Group")
    ax.set_title("Assistance vs Harm Matrix")
    fig.tight_layout()
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_risk_profile_heatmap(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "risk_profile_heatmap.png"
    rows = _build_risk_profile_rows(group_df)
    try:
        _, plt, sns = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if not rows:
        return _placeholder_first(group_df, output_dir, "risk_profile_heatmap.png")

    heat_rows = []
    y_labels = []
    for row in rows:
        heat_rows.append([row["harm_intent"], row["actionability"], row["specificity"], row["evasion"], row["impact"]])
        y_labels.append(row["group_label"])

    fig, ax = plt.subplots(figsize=(10.5, max(4.8, 0.6 * len(rows) + 1.6)))
    x_labels = ["harm_intent", "actionability", "specificity", "evasion", "impact"]
    if sns is not None:
        sns.heatmap(heat_rows, ax=ax, cmap="Reds", annot=True, fmt=".2f", cbar_kws={"label": "Mean Score"})
    else:
        im = ax.imshow(heat_rows, cmap="Reds", aspect="auto")
        for r, values in enumerate(heat_rows):
            for c, value in enumerate(values):
                ax.text(c, r, f"{value:.2f}", ha="center", va="center", fontsize=8)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Mean Score")
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels(x_labels, rotation=0)
    ax.set_yticks(range(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_xlabel("Risk Dimension")
    ax.set_ylabel("Analysis Group")
    ax.set_title("Risk Profile Heatmap")
    fig.tight_layout()
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path


def plot_refusal_leakage(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "refusal_leakage.png"
    rows = _group_metric_rows(group_df)
    try:
        _, plt, sns = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if not rows:
        return _placeholder_first(group_df, output_dir, "refusal_leakage.png")

    rows = sorted(rows, key=lambda row: float(row.get("refusal_leakage_rate", 0.0) or 0.0), reverse=True)
    fig, ax = plt.subplots(figsize=(10, max(4.8, 0.55 * len(rows) + 1.6)))
    x = [float(row.get("refusal_leakage_rate", 0.0) or 0.0) for row in rows]
    y = [str(row.get("analysis_group", "unknown") or "unknown") for row in rows]
    if sns is not None:
        # seaborn fallback to matplotlib if list-input barplot is unavailable in local version
        try:
            sns.barplot(x=x, y=y, ax=ax, color="#A23E48", orient="h")
        except Exception:
            ax.barh(y, x, color="#A23E48")
    else:
        ax.barh(y, x, color="#A23E48")
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Refusal Leakage Rate")
    ax.set_ylabel("Analysis Group")
    ax.set_title("Refusal Leakage by Group")
    fig.tight_layout()
    _save_figure(fig, fig_path)
    plt.close()
    return fig_path
