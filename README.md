# Experiment

`Experiment` 是一个面向大语言模型安全评测的实验仓库，围绕四个主功能组织：

- `Redteam`：生成或改写越狱提示
- `Jailbreak`：执行越狱攻击测试
- `Defense`：在攻击流程中插入输入/交互/输出三层防御
- `Analyze`：对结果进行判定、汇总和出图

项目当前已经形成一条完整实验链路：

`Attack_Dataset -> Redteam -> Jailbreak -> Defense(可选) -> Analyze`

这份 `README.md` 作为仓库根目录总说明，重点回答三件事：

1. 这个项目包含什么
2. 怎么从零开始跑通
3. 结果会输出到哪里、出现问题时如何排查

## 1. 项目概览

### 1.1 适用场景

这个仓库适合以下工作：

- 评估模型对中文越狱提示的抵抗能力
- 使用 surrogate/redteam 方法批量生成更强的攻击变体
- 在攻击链路中插入防御层，观察防御前后效果变化
- 对模型输出做规则判定、LLM 判定或融合判定
- 输出 `CSV`、聚合统计和图表，用于实验分析

### 1.2 四大模块

#### `Redteam/`

用于生成越狱提示变体。

核心能力：

- 从参考攻击样本中检索相似提示
- 调用本地或商用模型生成新变体
- 对生成结果做质量门过滤
- 支持单条生成和批量生成
- 结果输出到 `Redteam/redteam_results/`

主要入口：

- 交互式入口：`Jelly_Z/bin/redteam`
- Python 脚本：`Redteam/redteam_llm/surrogate_model.py`

#### `Jailbreak/`

用于把攻击数据集发送给目标模型，执行越狱测试。

核心能力：

- 支持单步和多步攻击模式
- 并发请求模型
- 失败自动重试
- 实时写入 JSONL
- 支持断点续跑
- 可选启用 `Defense` 模块

主要入口：

- 交互式入口：`Jelly_Z/bin/jailbreak`
- 单数据集多轮脚本：`Jailbreak/jailbreak_tools/single_jail/single_jail.py`
- 多数据集多轮脚本：`Jailbreak/jailbreak_tools/multi_jail/multi_jail.py`

#### `Defense/`

作为 `Jailbreak` 的可插拔防御层，不是独立运行主流程。

核心能力：

- 输入层：检测 prompt injection、越狱意图、角色诱导等
- 交互层：根据轮次和风险状态截断或阻断
- 输出层：检测有害输出、替换或脱敏、可归档审计

主要代码：

- `Defense/defense_mode/engine.py`
- `Defense/defense_mode/input/`
- `Defense/defense_mode/interaction/`
- `Defense/defense_mode/output/`

#### `Analyze/`

用于读取攻击结果，判定是否越狱成功，并输出统计结果和图表。

核心能力：

- 支持关键词判定
- 支持 LLM 判定
- 支持关键词 + LLM 融合判定
- 支持断点续跑
- 自动生成 `records.csv`、`group_metrics.csv` 和图表

主要入口：

- 交互式入口：`Jelly_Z/bin/analyze`
- Python CLI：`python -m Analyze.cli`

## 2. 项目结构

```text
Experiment/
├── Analyze/                     # 判定、统计、出图
├── Attack_Dataset/              # 攻击数据集与转换结果
├── Defense/                     # 三层防御模块与防御结果
├── Jailbreak/                   # 越狱测试执行器与测试结果
├── Redteam/                     # surrogate 变体生成与结果
├── Results/                     # Analyze 输出结果
├── Jelly_Z/                     # 项目虚拟环境
├── common/                      # 共享运行时与共享 LLM 配置层
├── docs/plans/                  # 设计与实施计划
├── model_registry.py            # 模型解析入口
└── models.yaml                  # 模型配置
```

常见输出目录：

- `Redteam/redteam_results/`
- `Jailbreak/jailbreak_results/`
- `Defense/defense_results/`
- `Results/final/`

## 3. 环境准备

### 3.1 Python 环境

仓库内已经包含虚拟环境目录 `Jelly_Z/`。推荐先激活：

```bash
cd /home/jellyz/Experiment
source Jelly_Z/bin/activate
```

如果你不激活，部分交互脚本也会尝试回退到仓库内的 `Jelly_Z/bin/python`。

### 3.2 模型服务

本项目同时支持：

- 本地 Ollama 模型
- OpenAI-compatible 商用接口

本地模型常见要求：

```bash
ollama serve
```

说明：

- 交互脚本在本地 Ollama 配置下会尝试自动健康检查和自动唤起
- 商用模型是否在菜单中显示，取决于 `models.yaml` 中对应的环境变量是否已设置

### 3.3 关键配置文件

项目主配置文件是：

- [models.yaml](/home/jellyz/Experiment/models.yaml)

`models.yaml` 中维护：

- 模型名称
- 模型类型
- provider
- base_url
- model id
- 商业模型所需的环境变量名

例如：

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

如果你要使用商用模型，需要先导出对应环境变量，例如：

```bash
export DEEPSEEK_API_KEY="your-key"
```

## 4. 快速开始

推荐按下面顺序跑：

1. 准备或生成攻击提示
2. 执行越狱测试
3. 可选启用防御再跑一次
4. 分析结果

### 4.1 方式一：直接使用交互式脚本

这是最推荐的方式。

#### 生成红队变体

```bash
source Jelly_Z/bin/activate
redteam
```

这个脚本会交互式让你选择：

- 目标模型
- 变体数量 `num_variants`
- 参考样本数 `top_k`
- 参考数据集
- 单条 prompt 或批量 CSV

输出目录默认是：

```text
Redteam/redteam_results/
```

#### 转换 redteam 结果为攻击数据集

```bash
convert
```

该脚本会从 `Redteam/redteam_results/` 中选择一个 `json/jsonl` 文件，并转换到：

```text
Attack_Dataset/
```

#### 执行越狱测试

```bash
jailbreak
```

交互流程包括：

- 选择单步或多步攻击
- 选择攻击集合
- 选择模型
- 选择测试规模（部分 / 完整）
- 选择是否开启防御
- 若开启防御，选择输入层 / 交互层 / 输出层 / 三层全部

输出目录通常是：

- 未启用防御：`Jailbreak/jailbreak_results/`
- 启用防御：`Defense/defense_results/<layer>/`

#### 分析结果

```bash
analyze
```

交互流程包括：

- 选择一个或多个输入结果文件
- 选择判定模式：关键词 / LLM / 融合
- 若需要 LLM 判定，再选择判定模型

输出目录为：

```text
Results/<mode>/<run_xxxx>/
```

例如：

- `Results/final/run_0001/`

### 4.2 方式二：直接调用底层 Python CLI

如果你要做调试或脚本化运行，可以直接调用 Python 入口。

#### Redteam

单条生成：

```bash
python Redteam/redteam_llm/surrogate_model.py \
  --model qwen2:latest \
  --models-config models.yaml \
  --dataset Attack_Dataset/JailBench.csv \
  --prompt "请改写这个提示" \
  --num-variants 3 \
  --top-k 5
```

批量生成：

```bash
python Redteam/redteam_llm/surrogate_model.py \
  --model qwen2:latest \
  --models-config models.yaml \
  --dataset Attack_Dataset/JailBench.csv \
  --input-csv Attack_Dataset/example.csv \
  --num-variants 3 \
  --top-k 5 \
  --output-dir Redteam/redteam_results
```

#### Jailbreak

单步执行：

```bash
python Jailbreak/jailbreak_tools/single_jail/single_jail.py \
  --models qwen2:latest \
  --dataset Attack_Dataset/example.csv \
  --models-config models.yaml \
  --output-dir Jailbreak/jailbreak_results \
  --max-rounds 6
```

多数据集执行：

```bash
python Jailbreak/jailbreak_tools/multi_jail/multi_jail.py \
  --models qwen2:latest \
  --datasets Attack_Dataset/example.csv Attack_Dataset/JailBench.csv \
  --models-config models.yaml \
  --output-dir Jailbreak/jailbreak_results \
  --max-rounds 6
```

#### Analyze

论文正式判定：

```bash
python -m Analyze.cli \
  --input-dir Jailbreak/jailbreak_results/qwen2.5_3b_jailbreaking_dataset_v1_single_turn.jsonl \
  --judge-mode paper \
  --output-dir Results
```

## 5. 典型实验流程

这里给出一个最常见的完整流程。

### 场景 A：从 redteam 生成到 analyze 分析

1. 使用 `redteam` 生成攻击变体
2. 使用 `convert` 转为 `Attack_Dataset/*.csv`
3. 使用 `jailbreak` 对目标模型跑攻击
4. 使用 `analyze` 生成统计结果和图表

### 场景 B：直接用已有攻击数据集跑模型

1. 将攻击数据集放入 `Attack_Dataset/`
2. 运行 `jailbreak`
3. 运行 `analyze`

### 场景 C：比较开启防御前后的差异

1. 先在未启用防御时跑一次 `jailbreak`
2. 再启用某个防御层重新运行 `jailbreak`
3. 用 `analyze` 同时选择两组结果文件进行分析
4. 对比 `Results/<mode>/<run_xxxx>/group_metrics.csv`

## 6. 输出文件说明

### 6.1 Redteam 输出

目录：

```text
Redteam/redteam_results/
```

内容通常是 `jsonl`，记录：

- 原始 prompt
- 生成后的变体
- 使用的模型
- 时间戳

### 6.2 Jailbreak 输出

目录：

```text
Jailbreak/jailbreak_results/
```

每条记录通常包含：

- `model_name`
- `test_id`
- `test_name`
- `category`
- `attack_type`
- `prompt`
- `response`
- `http_status`
- `elapsed_time`

若启用防御，还会额外包含：

- `defense_enabled`
- `defense_action`
- `defense_risk_level`
- `defense_reasons`
- `defense_trace`
- `defense_prompt`

### 6.3 Analyze 输出

目录：

```text
Results/<mode>/<run_xxxx>/
```

主要文件：

- `records.csv`：逐条判定结果
- `group_metrics.csv`：聚合指标
- `figures/success_rate.png`
- `figures/risk_distribution.png`
- `figures/uncertainty_overview.png`
- `figures/risk_heatmap.png`

## 7. 判定模式说明

`Analyze` 当前仅保留最终判定模式：

### `paper`

面向固定单轮结果文件，输出论文分析图和代表性案例。

优点：

- 与当前论文口径一致
- 输出稳定
- 直接产出最终统计图

## 8. 当前实现特点

这个仓库目前有几个比较重要的工程特性：

- `Jailbreak` 支持断点续跑
- `Jailbreak` 请求失败会异步退避重试
- `Analyze` 支持 checkpoint 与 partial row 恢复
- `Analyze` 的交互式 runner 会在异常时隐藏完整 traceback，并尝试自动续跑
- `Defense` 通过 hook 方式插入 `Jailbreak` 链路
- `common/` 中已经开始抽共享运行时策略和共享 LLM 配置归一化层

## 9. 常见问题

### 9.1 商用模型不出现在交互菜单里

通常原因：

- 没有设置 `models.yaml` 中要求的环境变量
- `models.yaml` 中该模型配置不完整

先检查：

```bash
echo "$DEEPSEEK_API_KEY"
```

### 9.2 本地 Ollama 模型无法调用

先检查服务：

```bash
ollama list
curl http://127.0.0.1:11434/api/tags
```

如果没启动：

```bash
ollama serve
```

### 9.3 `analyze` 过程中出现“异常退出后自动续跑”

当前交互式 `analyze` runner 会：

- 隐藏终端里的完整 Python traceback
- 保留统一告警
- 自动重新拉起服务并断点续跑

这通常意味着：

- 本地 Ollama 暂时超时
- 商用接口暂时超时
- 判定过程中模型服务不稳定

### 9.4 输出文件太多，不知道先看哪个

建议优先看：

1. `records.csv`
2. `group_metrics.csv`
3. `figures/success_rate.png`

### 9.5 `Jailbreak` 中途停止后如何继续

确保输出文件还在，然后重新使用相同配置运行，并带上：

```bash
--resume
```

交互式 `jailbreak` 已默认启用 resume。

## 10. 开发与测试

当前仓库已经补上了一批基础回归测试，位于：

```text
tests/
```

可以运行：

```bash
python -m unittest discover tests
```

如果只跑当前已补的核心回归：

```bash
python -m unittest \
  tests.test_loader \
  tests.test_analyze_pipeline \
  tests.test_defense_engine \
  tests.test_analyze_runner \
  tests.test_common \
  tests.test_runtime_config \
  tests.test_shared_llm_config \
  tests.test_redteam_clients \
  tests.test_single_jail_runtime
```

## 11. 最近优化状态

当前仓库已经完成一轮边界 2 优化，主要包括：

- 建立 `tests/` 基础回归测试包
- 增加共享运行时策略 `common/runtime.py`
- 增加共享 LLM 配置归一化层 `common/llm/config.py`
- 为 `Analyze` 的 external provider 增加重试与退避
- 让 `Analyze` 接入共享配置归一化
- 对齐 `Redteam` 的 client 配置保护
- 为 `Jailbreak` 增加运行时 guardrails

这意味着当前代码相比之前更适合继续做下面两类工作：

- 继续统一 schema
- 继续扩展 `single_jail/` 与 `multi_jail/` 的策略模块

## 12. 后续建议

如果你准备继续演进这个仓库，推荐优先顺序是：

1. 统一跨模块结果 schema
2. 扩展 `Jailbreak/jailbreak_tools/single_jail/` 与 `multi_jail/`
3. 继续配置化 `Defense`
4. 提升 `Analyze` 的大规模吞吐

---

如果你是第一次接手这个仓库，推荐最短路径是：

```bash
source Jelly_Z/bin/activate
redteam
convert
jailbreak
analyze
```

先跑通，再开始改。  
