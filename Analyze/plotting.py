"""Publication-ready chart generation for jailbreak metrics."""

from __future__ import annotations

import base64
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

    work = _group_label_df(group_df).sort_values(
        by=["success_rate", "total"], ascending=[False, False]
    ).reset_index(drop=True)
    y = pd.to_numeric(work["success_rate"], errors="coerce").fillna(0.0)
    lows = (y - pd.to_numeric(work["ci95_low"], errors="coerce").fillna(0.0)).clip(lower=0.0)
    highs = (pd.to_numeric(work["ci95_high"], errors="coerce").fillna(0.0) - y).clip(lower=0.0)
    fig, ax = plt.subplots(figsize=(10, max(4.5, 0.55 * len(work) + 1.5)))
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
    fig.tight_layout()
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

    work = _group_label_df(group_df).sort_values(by=["risk_4_ratio", "risk_3_ratio"], ascending=[False, False]).reset_index(
        drop=True
    )
    fig, ax = plt.subplots(figsize=(11, max(4.5, 0.65 * len(work) + 1.5)))
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
    fig.tight_layout()
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

    work = _group_label_df(group_df).sort_values(
        by=["uncertain_rate", "total"], ascending=[False, False]
    ).reset_index(drop=True)
    fig, ax1 = plt.subplots(figsize=(11, max(4.5, 0.6 * len(work) + 1.5)))
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
    fig.tight_layout()
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

    work = _group_label_df(group_df).sort_values(by=["risk_4_ratio", "risk_3_ratio"], ascending=[False, False]).reset_index(
        drop=True
    )
    heat = work[[f"risk_{i}_ratio" for i in range(5)]].copy()
    heat.index = work["group_label"]
    fig_h = max(4.5, len(heat) * 0.6 + 1.5)
    fig, ax = plt.subplots(figsize=(10, fig_h))
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
    fig.tight_layout()
    fig.savefig(fig_path, bbox_inches="tight")
    plt.close()
    return fig_path
