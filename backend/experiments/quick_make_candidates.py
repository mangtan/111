from __future__ import annotations

"""
Generate an expanded set of candidate plans for quick experiments.
It reuses the built-in candidate generator and creates perturbed variants
to reach ~100 candidates without changing backend logic.

Usage (from backend/):
  python -m experiments.quick_make_candidates --out experiments/results/candidates.json --target 100 --seed 42
"""

import json
import os
import random
import argparse
from typing import Any, Dict, List

from services.load_prediction import load_prediction
from services.gis_service import gis_service


def _perturb(val: float, lo: float, hi: float) -> float:
    r = random.uniform(lo, hi)
    return float(val) * r


def _nearby_substation_id(from_id: str, k: int = 3) -> str | None:
    data = gis_service.get_network_summary()
    subs = data.get('substations') or []
    sub_by_id = {s['id']: s for s in subs if s.get('location')}
    from_sub = sub_by_id.get(from_id)
    if not from_sub:
        return None
    fx, fy = float(from_sub['location']['lat']), float(from_sub['location']['lon'])
    dists = []
    for sid, s in sub_by_id.items():
        if sid == from_id:
            continue
        x, y = float(s['location']['lat']), float(s['location']['lon'])
        d = (x - fx) ** 2 + (y - fy) ** 2
        dists.append((d, sid))
    dists.sort(key=lambda x: x[0])
    return dists[random.randint(0, min(k - 1, len(dists) - 1))][1] if dists else None


def expand_candidates(base: List[Dict[str, Any]], target: int = 100) -> List[Dict[str, Any]]:
    rng = random.Random()
    out: List[Dict[str, Any]] = []
    out.extend(base)
    i = 0
    while len(out) < target and i < target * 10:
        i += 1
        src = random.choice(base)
        c = json.loads(json.dumps(src))  # deep copy
        t = c.get('type')
        if t == 'new_line':
            # perturb length and pick a nearby to-substation
            if c.get('length_km'):
                c['length_km'] = _perturb(float(c['length_km']), 0.9, 1.1)
            if c.get('capacity_mva'):
                c['capacity_mva'] = _perturb(float(c['capacity_mva']), 0.85, 1.15)
            to_alt = _nearby_substation_id(c.get('from_substation_id'))
            if to_alt:
                c['to_substation_id'] = to_alt
        elif t == 'new_substation':
            if c.get('capacity_mva'):
                c['capacity_mva'] = _perturb(float(c['capacity_mva']), 0.85, 1.2)
            if c.get('location'):
                # small jitter in location (visual only, backend maps to nearest bus)
                c['location']['lat'] = float(c['location']['lat']) + random.uniform(-0.01, 0.01)
                c['location']['lon'] = float(c['location']['lon']) + random.uniform(-0.01, 0.01)
        elif t == 'substation_expansion':
            if c.get('additional_capacity'):
                c['additional_capacity'] = _perturb(float(c['additional_capacity']), 0.85, 1.2)
        else:
            continue
        out.append(c)
    return out[:target]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='experiments/results/candidates.json')
    ap.add_argument('--target', type=int, default=100)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    # Make sure summary and base candidates are available
    summary = load_prediction.get_load_summary()
    base = gis_service.get_expansion_candidates(summary['overload_areas'])
    expanded = expand_candidates(base, target=args.target)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump({'seed': args.seed, 'count': len(expanded), 'candidates': expanded}, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(expanded)} candidates to {args.out}")


if __name__ == '__main__':
    main()

