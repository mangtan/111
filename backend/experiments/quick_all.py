from __future__ import annotations

"""
Run all quick experiments in sequence to produce 5 English figures:
  1) Compression vs Recall (fig1_compression_recall.png)
  2) Runtime comparison (fig2_runtime_comparison.png)
  3) Rule extraction accuracy (fig3_llm_parsing_accuracy.png)
  4) Forecast overlay & metrics (fig4_forecast_overlay.png)
  5) Scorer ablation (fig5_ablation.png)

Usage (from backend/):
  python -m experiments.quick_all
"""

import os
import subprocess
import sys


def run(cmd: list[str]) -> None:
    print('>>', ' '.join(cmd))
    subprocess.check_call(cmd)


def main():
    outdir = 'experiments/results'
    os.makedirs(outdir, exist_ok=True)

    # 0) Make candidates (~100)
    run([sys.executable, '-m', 'experiments.quick_make_candidates', '--out', f'{outdir}/candidates.json', '--target', '100'])

    # 1 & 2) Compression-Recall + Runtime
    run([sys.executable, '-m', 'experiments.quick_eval_bruteforce', '--candidates', f'{outdir}/candidates.json', '--outdir', outdir, '--topk', '5', '10', '20', '30', '--sample', '60'])

    # 3) Parsing accuracy
    run([sys.executable, '-m', 'experiments.quick_eval_parsing', '--outdir', outdir])

    # 4) Forecast overlay
    run([sys.executable, '-m', 'experiments.quick_eval_forecast', '--outdir', outdir, '--test_days', '30'])

    # 5) Ablation
    run([sys.executable, '-m', 'experiments.quick_eval_ablation', '--candidates', f'{outdir}/candidates.json', '--outdir', outdir, '--topk', '20'])

    print('\nAll figures generated in', outdir)


if __name__ == '__main__':
    main()

