# Experiment

`Experiment` 是一个面向大语言模型安全评测的实验仓库，覆盖红队提示生成、越狱测试、防御插入和结果分析四个环节。

仓库主链路如下：

```text
Attack_Dataset -> Redteam -> Jailbreak -> Defense(可选) -> Analyze
```

这份文档按“查用法优先”的思路组织，重点回答下面几件事：

- 从哪里启动
- 每一步输入什么、输出到哪里
- 常用命令怎么写
- 出错时先查什么

## 1. 仓库定位

本仓库主要用于以下工作：

- 批量生成或改写越狱攻击提示
- 将攻击数据发送给目标模型执行越狱测试
- 在测试流程中插入输入层、交互层、输出层防御
- 对结果做越狱判定、统计汇总和图表分析

四个核心模块如下：

- `Redteam/`：生成或改写攻击提示
- `Jailbreak/`：执行单轮或多轮越狱测试
- `Defense/`：作为 `Jailbreak` 的可插拔防御层
- `Analyze/`：读取结果并输出统计表与图表

## 2. 常用入口速查

推荐先激活仓库内虚拟环境：

```bash
cd /home/jellyz/Experiment
source Jelly_Z/bin/activate
```

激活后常用命令如下：

| 命令 | 作用 | 典型输出 |
| --- | --- | --- |
| `redteam` | 交互式生成攻击提示变体 | `Redteam/redteam_results/` |
| `convert` | 将 redteam 结果转换为可供越狱测试使用的数据集 | `Attack_Dataset/` |
| `jailbreak` | 交互式执行越狱测试 | `Jailbreak/jailbreak_results/` |
| `analyze` | 交互式分析结果 | `Results/` |
| `python -m Analyze.cli ...` | 非交互式分析入口 | `Results/<mode>/...` |

如果不想激活环境，也可以显式使用：

```bash
Jelly_Z/bin/redteam
Jelly_Z/bin/convert
Jelly_Z/bin/jailbreak
Jelly_Z/bin/analyze
```

## 3. 环境准备

### 3.1 Python 环境

仓库内已经包含虚拟环境目录 `Jelly_Z/`，默认优先使用它。

推荐做法：

```bash
cd /home/jellyz/Experiment
source Jelly_Z/bin/activate
python --version
```

### 3.2 模型服务

当前项目支持两类模型来源：

- 本地 `Ollama` 模型
- OpenAI-compatible 商业接口

如果使用本地模型，通常需要先启动服务：

```bash
ollama serve
```

常见要求：

- 本地模型必须已拉取并能在 `ollama list` 中看到
- 商业模型所需 API Key 必须提前写入环境变量
- 模型是否会在菜单里显示，取决于 `models.yaml` 配置和环境变量状态

### 3.3 模型配置文件

主配置文件是 [models.yaml](/home/jellyz/Experiment/models.yaml)。

它维护以下信息：

- 模型显示名称
- 模型类型
- provider
- base URL
- 实际模型 ID
- 商业模型所需环境变量名

示例：

```yaml
local:
  - name: qwen2:latest
    type: ollama
    base_url: http://localhost:11434
    model: qwen2:latest

commercial:
  - name: deepseek-chat
    type: openai_compatible
    provider: external
    base_url: https://api.deepseek.com
    model: deepseek-chat
    api_key_env: DEEPSEEK_API_KEY
```

如果使用商业模型，需要先导出对应变量，例如：

```bash
export DEEPSEEK_API_KEY="your-key"
```

## 4. 标准使用流程

推荐按下面的顺序执行：

1. 准备攻击数据集，或先生成 redteam 变体
2. 运行越狱测试
3. 如需对比防御效果，开启防御再跑一次
4. 对结果进行分析和出图

### 4.1 路线 A：直接使用现成攻击数据集

适合已经有数据集、只想快速测试模型的场景。

建议顺序：

1. 在 `Attack_Dataset/` 中选择现成 CSV
2. 运行 `jailbreak`
3. 运行 `analyze`

常见数据集位置：

- `Attack_Dataset/jailbreaking_dataset_v1.csv`
- `Attack_Dataset/JailBench.csv`
- `Attack_Dataset/resource/`
- `Attack_Dataset/test/`

### 4.2 路线 B：先生成 redteam 变体再测试

适合需要构造新攻击样本的场景。

建议顺序：

1. 运行 `redteam`
2. 运行 `convert`
3. 运行 `jailbreak`
4. 运行 `analyze`

## 5. 各步骤使用说明

### 5.1 生成攻击提示变体：`redteam`

启动方式：

```bash
source Jelly_Z/bin/activate
redteam
```

主要作用：

- 从参考攻击样本中检索相似提示
- 调用模型生成新的越狱提示变体
- 支持单条提示生成和批量生成
- 将结果保存为 `json` 或 `jsonl`

你通常会在交互流程中选择：

- 目标生成模型
- 每条原始提示生成的变体数量
- 检索参考样本数量
- 参考数据集
- 输入来源是单条提示还是批量文件

主要输出目录：

```text
Redteam/redteam_results/
```

典型输出文件示例：

- `redteam_results_231956.jsonl`
- `redteam_jailbreaking_dataset_v1.jsonl`

### 5.2 转换 redteam 结果为攻击数据集：`convert`

启动方式：

```bash
source Jelly_Z/bin/activate
convert
```

作用：

- 从 `Redteam/redteam_results/` 中选择一个 `json` 或 `jsonl`
- 提取生成后的提示
- 转换为 `Jailbreak` 可直接读取的 CSV

默认输出目录：

```text
Attack_Dataset/
```

如果你想直接走脚本，也可以使用：

```bash
python Redteam/redteam_convert/redteam_convert.py \
  --input Redteam/redteam_results/your_file.jsonl \
  --output-dir Attack_Dataset
```

### 5.3 执行越狱测试：`jailbreak`

启动方式：

```bash
source Jelly_Z/bin/activate
jailbreak
```

它负责：

- 读取攻击数据集
- 将提示发送到目标模型
- 支持单轮或多轮测试
- 并发请求模型
- 自动重试、实时写入、断点续跑
- 可选挂接 `Defense`

交互流程通常包括：

- 选择单轮或多轮测试
- 选择攻击数据集
- 选择目标模型
- 选择测试范围
- 选择是否启用防御
- 若启用防御，选择输入层、交互层、输出层或组合方案

主要输出目录：

```text
Jailbreak/jailbreak_results/
```

示例结果文件：

- `qwen2.5_3b_jailbreaking_dataset_v1_single_turn.jsonl`
- `deepseek-r1_8b_jailbreaking_dataset_v1_multi_turn.jsonl`

### 5.4 开启防御测试：`Defense`

`Defense` 不是独立主入口，而是挂在 `Jailbreak` 流程里的可选能力。

支持三层防御：

- 输入层：检测越狱意图、角色诱导、注入模式
- 交互层：在多轮过程中按风险动态拦截、截断或限制
- 输出层：对模型输出进行风险过滤、改写或审计归档

主要代码位置：

- [Defense/defense_mode/engine.py](/home/jellyz/Experiment/Defense/defense_mode/engine.py)
- [Defense/defense_mode/input/module.py](/home/jellyz/Experiment/Defense/defense_mode/input/module.py)
- [Defense/defense_mode/interaction/module.py](/home/jellyz/Experiment/Defense/defense_mode/interaction/module.py)
- [Defense/defense_mode/output/module.py](/home/jellyz/Experiment/Defense/defense_mode/output/module.py)

主要输出目录：

```text
Defense/defense_results/
```

常见子目录：

- `Defense/defense_results/input_layer/`
- `Defense/defense_results/interaction_layer/`
- `Defense/defense_results/output_layer/`
- `Defense/defense_results/all_layers/`

### 5.5 分析结果：`analyze`

推荐先使用交互式入口：

```bash
source Jelly_Z/bin/activate
analyze
```

如果你需要稳定复现、批处理或写脚本，建议直接使用 CLI：

```bash
python -m Analyze.cli \
  --input-dir Jailbreak/jailbreak_results/your_result.jsonl \
  --output-dir Results \
  --judge-mode paper
```

`Analyze` 负责：

- 读取 `jsonl` 结果
- 对每条结果执行越狱判定
- 输出记录表、聚合统计和图表
- 支持断点续跑

主要输出内容：

- `records.csv`
- `group_metrics.csv`
- `representative_cases.csv`
- `figures/`

默认结果根目录：

```text
Results/
```

如果使用当前 CLI，分析结果会按模式写入类似目录：

```text
Results/final/<run_id>/
Results/multi_turn/<judge_mode>/<run_id>/
```

仓库中已经存在一个结果说明文档，可配合查看：

- [Results/ANALYZE_RESULTS_GUIDE_ZH.md](/home/jellyz/Experiment/Results/ANALYZE_RESULTS_GUIDE_ZH.md)

## 6. 输入与输出对照

### 6.1 Redteam

- 输入：单条提示、参考数据集、批量 CSV
- 输出：`Redteam/redteam_results/*.json` 或 `*.jsonl`

### 6.2 Convert

- 输入：`Redteam/redteam_results/` 下的 redteam 结果文件
- 输出：`Attack_Dataset/*.csv`

### 6.3 Jailbreak

- 输入：`Attack_Dataset/*.csv`
- 输出：`Jailbreak/jailbreak_results/*.jsonl`

### 6.4 Defense

- 输入：`Jailbreak` 运行过程中的请求和响应
- 输出：`Defense/defense_results/` 下的审计记录和防御后结果

### 6.5 Analyze

- 输入：`Jailbreak/jailbreak_results/*.jsonl` 或防御后的结果文件
- 输出：`Results/` 下的 `csv` 与图表

## 7. 常见目录说明

```text
Experiment/
├── Analyze/               # 判定、统计、绘图
├── Attack_Dataset/        # 攻击数据集与转换结果
├── Defense/               # 三层防御模块与防御结果
├── Jailbreak/             # 越狱测试执行器与测试结果
├── Redteam/               # 攻击提示生成与转换
├── Results/               # 最终分析结果
├── Jelly_Z/               # 仓库内虚拟环境
├── common/                # 共享运行时与 LLM 配置逻辑
├── docs/plans/            # 设计和实施记录
├── model_registry.py      # 模型解析入口
└── models.yaml            # 模型配置文件
```

## 8. 常用操作示例

### 8.1 从现成数据集直接跑一轮

```bash
cd /home/jellyz/Experiment
source Jelly_Z/bin/activate
jailbreak
analyze
```

### 8.2 先生成变体再测试

```bash
cd /home/jellyz/Experiment
source Jelly_Z/bin/activate
redteam
convert
jailbreak
analyze
```

### 8.3 命令行方式分析某个结果文件

```bash
cd /home/jellyz/Experiment
source Jelly_Z/bin/activate
python -m Analyze.cli \
  --input-dir Jailbreak/jailbreak_results/deepseek-chat_jailbreaking_dataset_v1_single_turn.jsonl \
  --output-dir Results \
  --judge-mode paper
```

## 9. 常见问题与排障

### 9.1 命令找不到

现象：

- `redteam: command not found`
- `jailbreak: command not found`

优先检查：

```bash
source Jelly_Z/bin/activate
which redteam
which jailbreak
```

如果仍然不方便使用 shell 命令名，可直接执行：

```bash
Jelly_Z/bin/redteam
Jelly_Z/bin/jailbreak
Jelly_Z/bin/analyze
Jelly_Z/bin/convert
```

### 9.2 模型在菜单里不显示

优先检查：

- `models.yaml` 中是否已配置该模型
- 商业模型依赖的环境变量是否已经导出
- 本地 `Ollama` 服务是否已经启动

建议排查顺序：

1. 打开 [models.yaml](/home/jellyz/Experiment/models.yaml)
2. 检查 `api_key_env` 对应变量是否存在
3. 若为本地模型，执行 `ollama serve`

### 9.3 本地模型请求失败

优先检查：

- `ollama serve` 是否运行
- 模型是否已经拉取
- `base_url` 是否与本地服务一致

### 9.4 分析阶段没有输出图表

优先检查：

- 输入文件是否为有效 `jsonl`
- `Analyze` 是否成功写出 `records.csv`
- 输出目录下是否已生成 `figures/`

建议先确认：

```text
Results/.../records.csv
Results/.../group_metrics.csv
Results/.../figures/
```

### 9.5 中断后如何续跑

当前仓库多处流程支持断点续跑或增量写入，尤其是：

- `Jailbreak`
- `Analyze`

如果要续跑，通常不要删除已有输出文件，优先复用原结果目录重新执行。

## 10. 推荐阅读顺序

如果你只是想快速上手，建议按下面顺序看：

1. 本文第 2 节“常用入口速查”
2. 本文第 4 节“标准使用流程”
3. 本文第 5 节“各步骤使用说明”
4. 本文第 9 节“常见问题与排障”

如果你已经知道要做什么，只需要记住下面四个命令：

```bash
redteam
convert
jailbreak
analyze
```
