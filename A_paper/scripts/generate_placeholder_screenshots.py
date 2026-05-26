from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "figures"
SIZE = (1600, 900)


def load_font(size: int, bold: bool = False):
    candidates = []
    if bold:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        ]
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_TITLE = load_font(38, bold=True)
FONT_SUBTITLE = load_font(24, bold=True)
FONT_BODY = load_font(22)
FONT_SMALL = load_font(18)


def rr(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def line(draw, xy, fill, width=1):
    draw.line(xy, fill=fill, width=width)


def text(draw, xy, s, font, fill, anchor=None):
    draw.text(xy, s, font=font, fill=fill, anchor=anchor)


def tag(draw, x, y, label, fill):
    bbox = draw.textbbox((0, 0), label, font=FONT_SMALL)
    w = bbox[2] - bbox[0] + 26
    h = bbox[3] - bbox[1] + 14
    rr(draw, (x, y, x + w, y + h), 12, fill)
    text(draw, (x + 13, y + 7), label, FONT_SMALL, "#f8fafc")
    return w


def base_canvas(title_cn: str, subtitle: str):
    img = Image.new("RGB", SIZE, "#eef2f7")
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, SIZE[0], SIZE[1]), fill="#edf2f7")
    draw.rectangle((0, 0, SIZE[0], 90), fill="#0f172a")
    draw.rectangle((0, 90, 260, SIZE[1]), fill="#182435")
    draw.rectangle((260, 90, SIZE[0], SIZE[1]), fill="#f8fafc")

    text(draw, (32, 28), "PLACEHOLDER SCREENSHOT", FONT_SUBTITLE, "#cbd5e1")
    text(draw, (310, 128), title_cn, FONT_TITLE, "#0f172a")
    text(draw, (310, 175), subtitle, FONT_BODY, "#475569")

    menu = [
        "Dashboard",
        "Datasets",
        "Prompt Tasks",
        "Model Runs",
        "Review Queue",
        "Risk Reports",
        "Audit Logs",
    ]
    y = 150
    for idx, item in enumerate(menu):
        fill = "#24364d" if idx == 0 else "#182435"
        rr(draw, (18, y - 10, 242, y + 32), 14, fill)
        text(draw, (36, y), item, FONT_BODY, "#e2e8f0")
        y += 62

    rr(draw, (1260, 22, 1560, 64), 18, "#1d4ed8")
    text(draw, (1410, 34), "Replace With Real Capture", FONT_SMALL, "#eff6ff", anchor="ma")
    return img, draw


def panel(draw, box, title_text):
    rr(draw, box, 18, "#ffffff", outline="#dbe3ee", width=2)
    draw.rectangle((box[0], box[1], box[2], box[1] + 48), fill="#f8fafc")
    line(draw, (box[0], box[1] + 48, box[2], box[1] + 48), "#dbe3ee", 2)
    text(draw, (box[0] + 20, box[1] + 14), title_text, FONT_SUBTITLE, "#1e293b")


def table_rows(draw, x1, y1, x2, rows, cols):
    row_h = 46
    col_w = (x2 - x1) // cols
    for r in range(rows):
        y = y1 + r * row_h
        fill = "#ffffff" if r % 2 == 0 else "#f8fafc"
        draw.rectangle((x1, y, x2, y + row_h), fill=fill)
        line(draw, (x1, y + row_h, x2, y + row_h), "#e2e8f0", 1)
    for c in range(cols + 1):
        x = x1 + c * col_w
        line(draw, (x, y1, x, y1 + rows * row_h), "#e2e8f0", 1)


def make_overview():
    img, draw = base_canvas("实验系统主界面占位图", "用于第三章框架实现展示，可替换为真实系统首页或控制台截图")
    panel(draw, (300, 220, 980, 520), "Experiment Summary")
    panel(draw, (1010, 220, 1540, 520), "Active Modules")
    panel(draw, (300, 550, 1540, 820), "Recent Jobs")

    cards = [
        ("Static Dataset", "6406 samples", "#0ea5e9"),
        ("Dynamic Redteam", "273 variants", "#10b981"),
        ("Multi-turn Runs", "180 sessions", "#f59e0b"),
        ("Defense Eval", "5 configs", "#ef4444"),
    ]
    x = 328
    for title_s, value_s, color in cards:
        rr(draw, (x, 280, x + 145, 430), 16, "#f8fafc", outline="#dbe3ee", width=2)
        rr(draw, (x + 18, 300, x + 56, 338), 12, color)
        text(draw, (x + 18, 356), title_s, FONT_SMALL, "#334155")
        text(draw, (x + 18, 390), value_s, FONT_SUBTITLE, "#0f172a")
        x += 165

    modules = [
        ("Static attack pipeline", "#22c55e"),
        ("Prompt variant generator", "#22c55e"),
        ("Online screening", "#f59e0b"),
        ("Offline adjudication", "#22c55e"),
        ("Defense middleware", "#22c55e"),
    ]
    y = 290
    for label, color in modules:
        rr(draw, (1040, y, 1508, y + 42), 12, "#f8fafc", outline="#dbe3ee", width=2)
        rr(draw, (1060, y + 10, 1082, y + 32), 8, color)
        text(draw, (1100, y + 10), label, FONT_BODY, "#1e293b")
        y += 54

    table_rows(draw, 325, 615, 1512, 4, 5)
    headers = ["Job ID", "Model", "Attack Group", "Status", "Updated"]
    xs = [345, 560, 760, 1085, 1295]
    for h, x in zip(headers, xs):
        text(draw, (x, 575), h, FONT_SMALL, "#64748b")
    rows = [
        ("run-0314", "deepseek-chat", "认知误导", "done", "09:44"),
        ("run-0315", "qwen2.5:1.5b", "指令重构", "running", "09:46"),
        ("run-0316", "qwen2.5:3b", "上下文操控", "queued", "09:47"),
        ("run-0317", "qwen2.5:3b", "防御全开", "done", "09:49"),
    ]
    y = 628
    for row in rows:
        for value, x in zip(row, xs):
            text(draw, (x, y), value, FONT_SMALL, "#0f172a")
        y += 46
    return img


def make_run_panel():
    img, draw = base_canvas("单次实验运行截图占位图", "用于第四章实验流程说明，可替换为真实批量执行、进度条与结果汇总页面")
    panel(draw, (300, 220, 1220, 820), "Pipeline Execution")
    panel(draw, (1240, 220, 1540, 500), "Run Meta")
    panel(draw, (1240, 525, 1540, 820), "Result Snapshot")

    stages = [
        ("1. Load dataset", 1.00, "#16a34a"),
        ("2. Normalize records", 1.00, "#16a34a"),
        ("3. Invoke target model", 0.72, "#2563eb"),
        ("4. Online screening", 0.69, "#2563eb"),
        ("5. Offline review queue", 0.34, "#f59e0b"),
    ]
    y = 278
    for name, progress, color in stages:
        text(draw, (330, y), name, FONT_BODY, "#1e293b")
        rr(draw, (620, y - 4, 1170, y + 28), 12, "#e2e8f0")
        rr(draw, (620, y - 4, int(620 + 550 * progress), y + 28), 12, color)
        pct = f"{int(progress * 100)}%"
        text(draw, (1184, y), pct, FONT_SMALL, "#475569", anchor="ra")
        y += 95

    panel(draw, (325, 590, 1195, 790), "Execution Log")
    logs = [
        "[09:42:11] dataset loaded: static_attack_set.jsonl",
        "[09:42:19] model target: qwen2.5:3b",
        "[09:43:06] sample 1452 flagged as uncertain",
        "[09:43:13] sample 1453 refused with policy marker",
        "[09:43:27] sample 1454 escalated to offline adjudication",
    ]
    y = 646
    for i, entry in enumerate(logs):
        fill = "#e0f2fe" if i == 2 else "#f8fafc"
        rr(draw, (346, y - 8, 1172, y + 28), 10, fill)
        text(draw, (362, y), entry, FONT_SMALL, "#0f172a")
        y += 38

    meta = [
        ("Dataset", "6406 records"),
        ("Model", "qwen2.5:3b"),
        ("Attack", "cognitive misleading"),
        ("Seed", "2026-05-25-04"),
        ("Mode", "single-turn static"),
    ]
    y = 285
    for k, v in meta:
        text(draw, (1264, y), k, FONT_SMALL, "#64748b")
        text(draw, (1264, y + 24), v, FONT_BODY, "#0f172a")
        y += 55

    stats = [("ASR", "2.23%"), ("UR", "78.55%"), ("High risk", "2.23%")]
    y = 590
    for k, v in stats:
        rr(draw, (1260, y, 1518, y + 62), 14, "#f8fafc", outline="#dbe3ee", width=2)
        text(draw, (1280, y + 12), k, FONT_SMALL, "#64748b")
        text(draw, (1280, y + 34), v, FONT_SUBTITLE, "#0f172a")
        y += 78
    return img


def make_multiturn():
    img, draw = base_canvas("多轮越狱对话日志占位图", "用于第三或第四章动态实验说明，可替换为真实对话过程与重规划日志截图")
    panel(draw, (300, 220, 930, 820), "Conversation Trace")
    panel(draw, (955, 220, 1540, 560), "Planner / Judge")
    panel(draw, (955, 585, 1540, 820), "Round Summary")

    bubbles = [
        ("Round 1 attacker prompt", "#dbeafe", "#1d4ed8"),
        ("Model reply: partial refusal with explanation", "#f1f5f9", "#334155"),
        ("Round 2 follow-up with reframing", "#dbeafe", "#1d4ed8"),
        ("Judge feedback: uncertain, suggest role shift", "#fef3c7", "#92400e"),
        ("Round 3 attacker prompt after replanning", "#dbeafe", "#1d4ed8"),
        ("Model reply: policy weakened, risky detail leaked", "#fee2e2", "#b91c1c"),
    ]
    y = 260
    for label, fill, accent in bubbles:
        rr(draw, (330, y, 900, y + 68), 18, fill, outline="#dbe3ee", width=2)
        rr(draw, (346, y + 18, 356, y + 50), 5, accent)
        text(draw, (374, y + 20), label, FONT_BODY, "#0f172a")
        y += 86

    text(draw, (985, 280), "Attack Plan", FONT_SUBTITLE, "#0f172a")
    plan_lines = [
        "Goal: preserve harmful intent",
        "Strategy A: role-play framing",
        "Strategy B: mechanism analysis",
        "Replan after 2 refusals",
    ]
    y = 324
    for item in plan_lines:
        text(draw, (985, y), item, FONT_SMALL, "#334155")
        y += 34

    text(draw, (985, 432), "Judge Output", FONT_SUBTITLE, "#0f172a")
    rr(draw, (985, 470, 1510, 528), 12, "#fffbeb", outline="#fcd34d", width=2)
    text(draw, (1006, 490), "status = uncertain; advice = increase context pressure", FONT_SMALL, "#78350f")

    summary = [
        ("Max rounds", "6"),
        ("Current round", "3"),
        ("Trigger replan", "yes"),
        ("Final label", "success"),
    ]
    y = 630
    for k, v in summary:
        text(draw, (985, y), k, FONT_SMALL, "#64748b")
        text(draw, (1320, y), v, FONT_BODY, "#0f172a")
        y += 42
    return img


def make_defense():
    img, draw = base_canvas("防御拦截与审计页面占位图", "用于第五章分层防御展示，可替换为真实审计日志、风险评分与输出拦截截图")
    panel(draw, (300, 220, 860, 820), "Risk Signals")
    panel(draw, (885, 220, 1540, 500), "Intervention Decision")
    panel(draw, (885, 525, 1540, 820), "Audit Trail")

    signals = [
        ("Input layer", 67, "#ef4444"),
        ("Interaction layer", 43, "#f59e0b"),
        ("Output layer", 81, "#dc2626"),
    ]
    y = 290
    for name, score, color in signals:
        text(draw, (330, y), name, FONT_BODY, "#1e293b")
        rr(draw, (330, y + 34, 820, y + 62), 12, "#e2e8f0")
        rr(draw, (330, y + 34, 330 + int(4.9 * score), y + 62), 12, color)
        text(draw, (830, y + 34), f"{score}/100", FONT_SMALL, "#475569", anchor="ra")
        y += 122

    rr(draw, (330, 650, 820, 790), 18, "#fff7ed", outline="#fdba74", width=2)
    text(draw, (356, 674), "Detected patterns", FONT_SUBTITLE, "#9a3412")
    badges = [
        ("role manipulation", "#b45309"),
        ("policy bypass", "#b91c1c"),
        ("harmful procedural detail", "#b91c1c"),
    ]
    x, y = 356, 720
    for label, color in badges:
        w = tag(draw, x, y, label, color)
        x += w + 14

    rr(draw, (920, 275, 1505, 445), 18, "#fef2f2", outline="#fecaca", width=2)
    text(draw, (950, 305), "Final action", FONT_SUBTITLE, "#991b1b")
    text(draw, (950, 350), "Full replacement", FONT_TITLE, "#7f1d1d")
    text(draw, (950, 397), "Reason: output-layer high risk with prior session warning", FONT_SMALL, "#7f1d1d")

    logs = [
        ("09:51:14", "input", "role manipulation matched"),
        ("09:51:17", "interaction", "risk accumulated after round 2"),
        ("09:51:23", "output", "dangerous procedural detail detected"),
        ("09:51:24", "system", "reply replaced with safe completion"),
    ]
    table_rows(draw, 915, 610, 1510, 4, 3)
    xs = [936, 1100, 1238]
    for h, x in zip(["Time", "Layer", "Message"], xs):
        text(draw, (x, 572), h, FONT_SMALL, "#64748b")
    y = 624
    for t, layer, msg in logs:
        text(draw, (936, y), t, FONT_SMALL, "#0f172a")
        text(draw, (1100, y), layer, FONT_SMALL, "#0f172a")
        text(draw, (1238, y), msg, FONT_SMALL, "#0f172a")
        y += 46
    return img


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "fig3-2-system-overview-placeholder.png": make_overview(),
        "fig4-3-experiment-run-placeholder.png": make_run_panel(),
        "fig4-4-multiturn-log-placeholder.png": make_multiturn(),
        "fig5-2-defense-audit-placeholder.png": make_defense(),
    }
    for name, image in outputs.items():
        image.save(OUT_DIR / name, format="PNG")
        print(OUT_DIR / name)


if __name__ == "__main__":
    main()
