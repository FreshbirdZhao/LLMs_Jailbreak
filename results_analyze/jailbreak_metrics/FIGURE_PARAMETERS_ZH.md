# Jailbreak Metrics 四幅图参数说明（中文）

本文档对应模块 `results_analyze/jailbreak_metrics` 生成的四幅图：

1. `success_rate.png`
2. `risk_distribution.png`
3. `uncertainty_overview.png`
4. `risk_heatmap.png`

统计字段主要来自 `group_metrics.csv`（由 `stats.py` 的 `compute_group_metrics` 计算）。

## 一、公共分组维度

所有图都基于同一分组键：

- `model_name`：模型名
- `attack_type`：攻击方法类型

每个分组可记为 `(model_name, attack_type)`。

## 二、核心统计参数与计算公式

设某分组总样本数为 `n`：

- `total = n`
- `yes_count =` 该组中 `is_jailbreak == "yes"` 的样本数
- `uncertain_count =` 该组中 `is_jailbreak == "uncertain"` 的样本数

### 1. 越狱成功率

- `success_rate = yes_count / total`
- 含义：该组被判定为成功越狱的比例。

### 2. 越狱成功率方差（二项分布近似）

- `success_variance = success_rate * (1 - success_rate)`
- 含义：成功率离散程度的近似衡量。

### 3. 不确定比例

- `uncertain_rate = uncertain_count / total`
- 含义：该组判定为 `uncertain` 的比例。
- 说明：当前实现中该值在绘图阶段按 `uncertain_count` 与 `total` 即时计算。

### 4. 风险等级比例

设 `risk_i_count` 为该组 `risk_level == i` 的样本数（`i=0..4`）：

- `risk_i_ratio = risk_i_count / (risk_0_count + risk_1_count + risk_2_count + risk_3_count + risk_4_count)`
- 由于分母等于该组风险统计总数，在正常数据下可视作 `risk_i_count / total`。
- 含义：该组落入风险等级 `i` 的占比。

### 5. 95% Wilson 置信区间（成功率）

记 `p = yes_count / total`，`z = 1.959963984540054`（95% 置信度），`n = total`：

- `denom = 1 + z^2 / n`
- `center = (p + z^2 / (2n)) / denom`
- `spread = z * sqrt((p(1-p) + z^2/(4n)) / n) / denom`
- `ci95_low = max(0, center - spread)`
- `ci95_high = min(1, center + spread)`

含义：在二项分布场景下，`success_rate` 的稳健区间估计。

## 三、四幅图分别使用哪些参数

## 1) `success_rate.png`

### 使用参数

- `model_name`, `attack_type`
- `success_rate`
- `ci95_low`, `ci95_high`
- `yes_count`, `total`（用于标注）

### 图像含义

- 横向柱长表示 `success_rate`。
- 误差线表示 `95% Wilson CI`。
- 文本标注显示 `p` 和 `yes_count/total`。

### 读图建议

- 同时看点估计（柱长）和区间宽度（误差线）。
- 区间更宽通常说明该组样本量更小或不稳定性更高。

## 2) `risk_distribution.png`

### 使用参数

- `model_name`, `attack_type`
- `risk_0_ratio` 到 `risk_4_ratio`
- `total`（顶部 `n=...` 标注）

### 图像含义

- 堆叠柱显示 0~4 风险等级比例构成。
- 每根柱总高度为 1，表示该组风险分布。

### 读图建议

- 重点关注 `risk_4_ratio` 与 `risk_3_ratio` 的占比变化。
- 在比较不同组时，结合 `n=total` 避免小样本误判。

## 3) `uncertainty_overview.png`

### 使用参数

- `model_name`, `attack_type`
- `uncertain_count`, `total`
- `uncertain_rate = uncertain_count / total`

### 图像含义

- 左轴柱形：`uncertain_rate`。
- 右轴折线：`total`（样本量）。
- 柱顶标注：`uncertain_count/total`。

### 读图建议

- 高 `uncertain_rate` 可能表示该组样本更难判定。
- 需要与右轴 `total` 联合解释，避免把小样本噪声当作趋势。

## 4) `risk_heatmap.png`

### 使用参数

- `model_name`, `attack_type`
- `risk_0_ratio` 到 `risk_4_ratio`

### 图像含义

- 行：分组 `(model_name, attack_type)`。
- 列：风险等级 `risk_0`~`risk_4`。
- 单元格颜色与文本均表示对应 `risk_i_ratio`。

### 读图建议

- 适合快速比较多组在不同风险等级上的分布模式。
- 建议重点看高风险列（`risk_3`, `risk_4`）的热点区域。

## 四、补充说明

- 若输入为空，四幅图会输出空状态图而不是报错。
- 若绘图后端初始化失败，模块会回退生成占位 PNG，保证 CLI 流程不中断。
