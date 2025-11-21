
# Experiments (Quick Figures)

This folder contains quick, publication‑ready experiments to produce five English figures without heavy engineering.

Run from `backend/`:

```
pip install -r requirements.txt
pip install numba llvmlite matplotlib  # optional but recommended for speed
python -m experiments.quick_all
```

Outputs will be written to `experiments/results/`:

- fig1_compression_recall.png — Compression (Top‑K/Total) vs Recall (Hit@K) + NDCG@K
- fig2_runtime_comparison.png — End‑to‑End runtime: Full brute‑force vs Filter@K
- fig3_llm_parsing_accuracy.png — Rule extraction accuracy (tolerance aware)
- fig4_forecast_overlay.png — Forecast vs actual (last 7 days overlay), with `forecast_metrics.json`
- fig5_ablation.png — Feature ablation on ranking quality (NDCG@K)

Notes
- Candidates are expanded from the built‑in generator to about ~100 by small perturbations.
- Ground‑truth objective uses a power‑flow baseline (N‑1 disabled for speed) combining: violations, max line/trafo loading, and total losses.
- If `QWEN_API_KEY` is not provided, parsing accuracy falls back to a regex parser (heuristic) to keep the pipeline runnable.
- Forecast evaluation uses the built‑in synthetic/statistical model on a rolling split (last 30 days as test).

Reproducibility
- Random seed is fixed by default. Figures include the IEEE‑14 base and may be re‑run to refresh numbers.
- For large cases or aggressive N‑1, please install `numba` to speed up `pandapower.runpp`.
