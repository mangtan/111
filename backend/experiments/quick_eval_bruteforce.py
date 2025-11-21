from __future__ import annotations

"""
Quickly evaluate compression-recall curve and runtime bars.
It uses:
  - objective based on power flow results (violations, max loading, losses)
  - scorer ranking to select Top-K
Outputs:
  - fig1_compression_recall.png
  - fig2_runtime_comparison.png

Usage (from backend/):
  python -m experiments.quick_eval_bruteforce --candidates experiments/results/candidates.json \
      --outdir experiments/results --topk 5 10 20 30 --sample 60 --seed 42
"""

import argparse
import json
import os
import time
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt

from services.power_flow import power_flow
from services.scorer import scorer
from services.load_prediction import load_prediction
from services.gis_service import gis_service
try:
    from services.settings_service import settings
except Exception:
    settings = None  # type: ignore


def objective_from_pf(pf: Dict[str, Any]) -> float:
    res = pf.get('power_flow') or {}
    viol = len(res.get('violations') or [])
    max_line = 0.0
    for l in (res.get('lines') or []):
        max_line = max(max_line, float(l.get('loading_percent', 0.0)))
    max_trafo = 0.0
    for t in (res.get('transformers') or []):
        max_trafo = max(max_trafo, float(t.get('loading_percent', 0.0)))
    losses = 0.0
    for l in (res.get('lines') or []):
        losses += float(l.get('pl_mw', 0.0))
    return 1000.0*viol + 100.0*max_line + 50.0*max_trafo + losses


def run_pf(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return power_flow.evaluate_candidate_with_power_flow(candidate)


def rank_candidates(cands: List[Dict[str, Any]], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
    summary = load_prediction.get_load_summary()
    network = gis_service.get_network_summary()
    ranked = scorer.rank_candidates(
        cands, summary['current_features'], network, network['topology'], constraints, top_k=len(cands)
    )
    return ranked


def compute_ground_truth(cands: List[Dict[str, Any]], sample: int | None = None) -> List[Tuple[int, float]]:
    # Disable N-1 for speed (ground truth baseline)
    if settings is not None:
        try:
            settings.overrides['N_MINUS_1_CHECK'] = False
        except Exception:
            pass
    idxs = list(range(len(cands)))
    if sample is not None and sample < len(cands):
        idxs = idxs[:sample]
    scored: List[Tuple[int, float]] = []
    for i in idxs:
        pf = run_pf(cands[i])
        obj = objective_from_pf({'power_flow': pf.get('power_flow')})
        scored.append((i, obj))
    scored.sort(key=lambda x: x[1])  # lower is better
    return scored


def hit_at_k(gt_sorted: List[Tuple[int, float]], selected_indices: List[int], k: int) -> float:
    if not gt_sorted:
        return 0.0
    best_idx = gt_sorted[0][0]
    return 1.0 if best_idx in selected_indices[:k] else 0.0


def ndcg_at_k(gt_sorted: List[Tuple[int, float]], sel_order: List[int], k: int) -> float:
    # Relevance: inverse of obj (normalize)
    if not gt_sorted:
        return 0.0
    # Build rel dict
    objs = [o for _, o in gt_sorted]
    max_o = max(objs) or 1.0
    rel = {i: 1.0 - (o / max_o) for i, o in gt_sorted}  # 0..1
    import math
    def dcg(order):
        s = 0.0
        for rank, idx in enumerate(order[:k], 1):
            s += (2**rel.get(idx, 0.0) - 1.0) / math.log2(rank + 1.0)
        return s
    ideal = dcg([i for i, _ in gt_sorted])
    actual = dcg(sel_order)
    return float(actual / ideal) if ideal > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidates', default='experiments/results/candidates.json')
    ap.add_argument('--outdir', default='experiments/results')
    ap.add_argument('--topk', type=int, nargs='+', default=[5, 10, 20, 30])
    ap.add_argument('--sample', type=int, default=60, help='sample size for ground truth PF (None uses all)')
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    with open(args.candidates, 'r', encoding='utf-8') as f:
        data = json.load(f)
    cands = data['candidates']

    # Rank by our scorer (fast)
    t0 = time.perf_counter()
    ranked = rank_candidates(cands, constraints={})
    t_rank = time.perf_counter() - t0
    sel_order = [c['candidate'] for c in ranked]
    sel_indices = [cands.index(c) for c in sel_order]

    # Ground truth baseline by PF (sampled)
    t0 = time.perf_counter()
    gt_sorted = compute_ground_truth(cands, sample=args.sample)
    t_gt = time.perf_counter() - t0

    # Build curves
    xs = []
    hit = []
    ndcg = []
    n = len(cands)
    for K in args.topk:
        xs.append(100.0 * K / n)
        hit.append(hit_at_k(gt_sorted, sel_indices, K))
        ndcg.append(ndcg_at_k(gt_sorted, sel_indices, K))

    # FIG1: Compression-Recall
    plt.figure(figsize=(6,4))
    plt.plot(xs, hit, marker='o', label='Hit@K (Recall of best)')
    plt.plot(xs, ndcg, marker='s', label='NDCG@K', alpha=0.8)
    plt.xlabel('Compression (Top-K / Total) %')
    plt.ylabel('Score')
    plt.title('Compression vs. Recall Curve (IEEE-14, PF baseline)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    fig1 = os.path.join(args.outdir, 'fig1_compression_recall.png')
    plt.tight_layout(); plt.savefig(fig1, dpi=150)
    print('Saved', fig1)

    # FIG2: Runtime comparison (rough)
    # Full PF (estimate): evaluate all candidates or scale from sample
    full_pf_time = t_gt * (len(cands) / max(1, args.sample)) if args.sample and args.sample < len(cands) else t_gt
    # Filter Top-K
    runtimes = [full_pf_time]
    labels = ['Full brute-force']
    for K in [min(10, n), min(20, n)]:
        t0 = time.perf_counter()
        for idx in sel_indices[:K]:
            _ = run_pf(cands[idx])
        tK = time.perf_counter() - t0
        runtimes.append(t_rank + tK)
        labels.append(f'Filter@{K}')

    plt.figure(figsize=(6,4))
    plt.bar(labels, runtimes, color=['#6b7280', '#2563eb', '#10b981'])
    plt.ylabel('Total runtime (s)')
    plt.title('End-to-End Runtime Comparison')
    for i, v in enumerate(runtimes):
        plt.text(i, v, f'{v:.1f}s', ha='center', va='bottom')
    plt.tight_layout();
    fig2 = os.path.join(args.outdir, 'fig2_runtime_comparison.png')
    plt.savefig(fig2, dpi=150)
    print('Saved', fig2)


if __name__ == '__main__':
    main()

