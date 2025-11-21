from __future__ import annotations

"""
Scorer ablation: zero-out specific features and compare NDCG/Hit.

Usage:
  python -m experiments.quick_eval_ablation --candidates experiments/results/candidates.json \
      --outdir experiments/results --topk 20
Outputs: fig5_ablation.png
"""

import argparse
import json
import os
from typing import Any, Dict, List, Tuple
import matplotlib.pyplot as plt

from services.scorer import scorer
from services.load_prediction import load_prediction
from services.gis_service import gis_service
from experiments.quick_eval_bruteforce import compute_ground_truth, ndcg_at_k


def rank_with_weights(cands: List[Dict[str, Any]], weights: Dict[str, float]) -> List[int]:
    summary = load_prediction.get_load_summary()
    network = gis_service.get_network_summary()
    # backup and set
    old = dict(scorer.weights)
    scorer.weights.update(weights)
    ranked = scorer.rank_candidates(cands, summary['current_features'], network, network['topology'], constraints={}, top_k=len(cands))
    scorer.weights = old
    indices = [cands.index(r['candidate']) for r in ranked]
    return indices


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidates', default='experiments/results/candidates.json')
    ap.add_argument('--outdir', default='experiments/results')
    ap.add_argument('--topk', type=int, default=20)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    with open(args.candidates, 'r', encoding='utf-8') as f:
        cands = json.load(f)['candidates']

    # Ground truth baseline (sampled PF from earlier function)
    gt_sorted = compute_ground_truth(cands, sample=min(60, len(cands)))

    # Baseline weights
    base_indices = rank_with_weights(cands, scorer.weights)
    base_ndcg = ndcg_at_k(gt_sorted, base_indices, args.topk)

    # Ablations: set a weight to zero (and renormalize inside function)
    variants = {
        'No LoadGrowth': {'load_growth': 0.0},
        'No Distance': {'distance': 0.0},
        'No Topology': {'topology': 0.0},
        'No Constraint': {'constraint': 0.0},
    }
    scores = []
    for name, patch in variants.items():
        w = dict(scorer.weights)
        w.update(patch)
        s = sum(w.values()) or 1.0
        w = {k: v/s for k, v in w.items()}
        idx = rank_with_weights(cands, w)
        nd = ndcg_at_k(gt_sorted, idx, args.topk)
        scores.append((name, nd))

    plt.figure(figsize=(6,4))
    names = [n for n,_ in scores]
    vals = [v for _,v in scores]
    plt.bar(['Baseline']+names, [base_ndcg]+vals, color=['#1f2937']+['#2563eb']*len(names))
    plt.ylabel('NDCG@K')
    plt.title('Feature Ablation on Ranking Quality')
    for i, v in enumerate([base_ndcg]+vals):
        plt.text(i, v, f'{v:.2f}', ha='center', va='bottom')
    plt.tight_layout()
    fig = os.path.join(args.outdir, 'fig5_ablation.png')
    plt.savefig(fig, dpi=150)
    print('Saved', fig)


if __name__ == '__main__':
    main()

