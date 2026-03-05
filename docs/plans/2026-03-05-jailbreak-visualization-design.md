# Jailbreak Visualization Enhancement Design (Research-Oriented)

## Goal

Improve `results_analyze/jailbreak_metrics` plotting quality so outputs are clearer, more informative, and better suited for quantitative analysis.

## Scope

1. Upgrade existing charts:
- `success_rate.png`
- `risk_distribution.png`

2. Add new charts:
- `uncertainty_overview.png`
- `risk_heatmap.png`

## Design Decisions

1. `success_rate.png`
- Sort groups by `success_rate` desc (then `total` desc).
- Show 95% Wilson CI as error bars.
- Annotate each bar with:
  - success rate
  - `yes_count/total`
  - `[ci95_low, ci95_high]`

2. `risk_distribution.png`
- Keep stacked ratio bars for `risk_0` to `risk_4`.
- Sort by high-risk concentration (`risk_4`, then `risk_3`).
- Annotate visible segment ratios and per-group `n=total`.

3. `uncertainty_overview.png`
- Left axis: `uncertain_rate` bar.
- Right axis: `total` line.
- Annotate each bar with `uncertain_count/total`.

4. `risk_heatmap.png`
- Heatmap of `risk_0_ratio...risk_4_ratio` per group.
- Cell annotations as percentages.
- Colorbar for ratio scale.

## Robustness

- Keep existing font fallback and placeholder PNG behavior when matplotlib setup fails.
- Handle empty input dataframe by producing empty-state images instead of crashing.

## Test Strategy

1. Extend CLI smoke tests to assert the two new output files exist.
2. Add plotting tests to verify:
- all four chart functions generate files for normal input
- all four chart functions generate files for empty input
- generated files are non-empty

## Acceptance Criteria

1. CLI run produces:
- `figures/success_rate.png`
- `figures/risk_distribution.png`
- `figures/uncertainty_overview.png`
- `figures/risk_heatmap.png`

2. Relevant test suite passes.
