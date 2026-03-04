# jailbreak_metrics

Jailbreak result analyzer with three judge styles:
- keyword judge
- LLM classifier-style judge
- structured policy judge

It supports grouped quantitative analysis by `attack_type x model_name`, including:
- jailbreak success rate
- stability (`success_variance` and Wilson 95% CI)
- risk-level distribution (`risk_0_ratio` ... `risk_4_ratio`)

## Input

Directory containing `.jsonl` files, each line as one record. Common fields:
- `model_name`
- `attack_type`
- `category`
- `prompt`
- `response`

## CLI

Run keyword-only mode (no LLM call):

```bash
python -m results_analyze.jailbreak_metrics.cli \
  --input-dir /home/jellyz/Experiment/jailbreak_results \
  --output-dir /home/jellyz/Experiment/results_analyze/jailbreak_metrics/output \
  --judge-mode keyword
```

Run hybrid mode with local Ollama:

```bash
python -m results_analyze.jailbreak_metrics.cli \
  --input-dir /home/jellyz/Experiment/jailbreak_results \
  --output-dir /home/jellyz/Experiment/results_analyze/jailbreak_metrics/output_hybrid \
  --judge-mode hybrid \
  --llm-provider ollama \
  --llm-model qwen2:latest \
  --llm-base-url http://127.0.0.1:11434
```

Run LLM-only mode with external API adapter:

```bash
python -m results_analyze.jailbreak_metrics.cli \
  --input-dir /home/jellyz/Experiment/jailbreak_results \
  --output-dir /home/jellyz/Experiment/results_analyze/jailbreak_metrics/output_external \
  --judge-mode llm \
  --llm-provider external \
  --llm-model gpt-4o-mini \
  --llm-base-url https://api.openai.com/v1 \
  --llm-api-key YOUR_API_KEY
```

Progress display is enabled by default during judging (stderr, e.g. `Judging records: 123/2048`).
Use `--no-show-progress` to disable it.

## Output artifacts

In `--output-dir`:
- `<judge_mode>/records.csv`: per-record decision results
- `<judge_mode>/group_metrics.csv`: grouped quantitative metrics
- `<judge_mode>/figures/success_rate.png`: success-rate chart with CI
- `<judge_mode>/figures/risk_distribution.png`: risk-level stacked distribution

## Notes

- Fixed decision schema uses:
  - `is_jailbreak`: `yes/no/uncertain`
  - `risk_level`: `0-4`
  - `evidence_spans`: evidence snippets from model output
- If matplotlib is unavailable, plotting falls back to placeholder PNG files to keep pipelines non-blocking.
