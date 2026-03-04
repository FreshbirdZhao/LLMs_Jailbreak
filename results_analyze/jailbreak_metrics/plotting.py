"""Matplotlib chart generation for jailbreak metrics."""

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


def _configure_matplotlib() -> tuple[object, object]:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    # Prefer bundled CJK font package when available.
    try:
        import chineseize_matplotlib  # type: ignore

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            warnings.filterwarnings("ignore", message=".*distutils Version classes are deprecated.*")
            chineseize_matplotlib.chineseize()
    except Exception:
        installed = {f.name for f in font_manager.fontManager.ttflist}
        chosen = _pick_best_chinese_font(installed)
        if chosen:
            matplotlib.rcParams["font.sans-serif"] = [chosen, "DejaVu Sans", "Arial"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    return matplotlib, plt


def plot_success_rate(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "success_rate.png"
    try:
        _, plt = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    if group_df.empty:
        plt.figure(figsize=(6, 4))
        plt.title("Success Rate by Model and Attack Type")
        plt.savefig(fig_path, dpi=150, bbox_inches="tight")
        plt.close()
        return fig_path

    x_labels = [f"{m}\n{a}" for m, a in zip(group_df["model_name"], group_df["attack_type"])]
    values = group_df["success_rate"].tolist()
    lows = (group_df["success_rate"] - group_df["ci95_low"]).clip(lower=0).tolist()
    highs = (group_df["ci95_high"] - group_df["success_rate"]).clip(lower=0).tolist()

    plt.figure(figsize=(max(8, len(x_labels) * 0.8), 4.8))
    plt.bar(x_labels, values, color="#2E6F95")
    plt.errorbar(x_labels, values, yerr=[lows, highs], fmt="none", ecolor="black", capsize=3)
    plt.ylim(0, 1)
    plt.ylabel("Jailbreak Success Rate")
    plt.title("Success Rate with 95% CI")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150)
    plt.close()
    return fig_path


def plot_risk_distribution(group_df: pd.DataFrame, output_dir: str | Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_path = out / "risk_distribution.png"
    try:
        _, plt = _configure_matplotlib()
    except Exception:
        _write_placeholder_png(fig_path)
        return fig_path

    plt.figure(figsize=(max(8, len(group_df) * 0.8), 5))
    if group_df.empty:
        plt.title("Risk Level Distribution")
        plt.savefig(fig_path, dpi=150, bbox_inches="tight")
        plt.close()
        return fig_path

    x_labels = [f"{m}\n{a}" for m, a in zip(group_df["model_name"], group_df["attack_type"])]
    bottom = [0.0] * len(group_df)
    colors = ["#D9D9D9", "#A6CEE3", "#1F78B4", "#FB9A99", "#E31A1C"]

    for i in range(5):
        values = group_df[f"risk_{i}_ratio"].tolist()
        plt.bar(x_labels, values, bottom=bottom, label=f"risk {i}", color=colors[i])
        bottom = [b + v for b, v in zip(bottom, values)]

    plt.ylim(0, 1)
    plt.ylabel("Ratio")
    plt.title("Risk Level Distribution by Model and Attack Type")
    plt.xticks(rotation=30, ha="right")
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150)
    plt.close()
    return fig_path
