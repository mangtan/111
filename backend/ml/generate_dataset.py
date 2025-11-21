"""
Generate training samples (极速版):
- Base grid: IEEE 14-bus from pandapower
- Candidate type: new_line between same-voltage buses not directly connected
- For each candidate: clone net, inject line, run power flow, collect metrics, label

Output: CSV with features X and label y
"""
from __future__ import annotations

import argparse
import os
import random
import math
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.networks as pn

from config import Config  # reuse thresholds


# Label weights (heuristic). Tune as needed.
W_VIOLATION_REDUCTION = 1.0     # fewer violations is better
W_MAX_LOADING_IMPROVE = 0.5     # lower max line loading is better (in p.u. of 1.0 == 100%)
W_LOSSES_REDUCTION = 0.2        # lower total line losses (MW) is better
COST_PER_KM_MILLION = 0.8       # million CNY per km (heuristic)
W_COST = 0.02                   # cost penalty weight


@dataclass
class Candidate:
    from_bus: int
    to_bus: int
    vn_kv: float
    length_km: float
    max_i_ka: float


@dataclass
class ExpansionCandidate:
    hv_bus: int
    lv_bus: int
    vn_kv: float
    add_sn_mva: float


def build_base_net(name: str = 'case14', load_scale: float = 1.0) -> pp.pandapowerNet:
    """Load a pandapower test case by name and run baseline power flow; apply load scaling."""
    if not hasattr(pn, name):
        raise ValueError(f'Unknown network: {name}')
    net = getattr(pn, name)()
    # scale loads (simple scenario variation)
    if 'load' in net and len(net.load) > 0 and load_scale != 1.0:
        net.load['p_mw'] = net.load['p_mw'] * load_scale
        if 'q_mvar' in net.load:
            net.load['q_mvar'] = net.load['q_mvar'] * load_scale
    pp.runpp(net)
    return net


def baseline_metrics(net: pp.pandapowerNet) -> Dict[str, Any]:
    """Collect baseline metrics on the given net."""
    # Violations: voltage deviation and line loading over limits
    violations = 0
    for _, row in net.res_bus.iterrows():
        if abs(row.vm_pu - 1.0) > Config.MAX_VOLTAGE_DEVIATION:
            violations += 1
    for _, row in net.res_line.iterrows():
        if row.loading_percent / 100.0 > Config.MAX_LINE_LOADING:
            violations += 1

    max_loading = float(net.res_line.loading_percent.max()) if len(net.res_line) else 0.0
    total_losses = float(net.res_line.pl_mw.sum()) if 'pl_mw' in net.res_line else 0.0

    return {
        'violations': violations,
        'max_loading_percent': max_loading,
        'total_losses_mw': total_losses,
    }


def already_connected_pairs(net: pp.pandapowerNet) -> set[Tuple[int, int]]:
    s = set()
    for _, line in net.line.iterrows():
        a = int(line.from_bus)
        b = int(line.to_bus)
        s.add(tuple(sorted((a, b))))
    return s


def candidate_pool_new_lines(net: pp.pandapowerNet, max_pairs: int = 10000, variants_per_pair: int = 1, allow_parallel: bool = True) -> List[Candidate]:
    """
    Make a pool of feasible new-line candidates: same-voltage bus pairs not directly connected.
    Length is sampled heuristically; current limit is a simple default value.
    """
    bus_kv = {int(i): float(v) for i, v in net.bus.vn_kv.items()}
    conn = already_connected_pairs(net)

    buses = list(bus_kv.keys())
    pool: List[Candidate] = []
    for i in range(len(buses)):
        for j in range(i + 1, len(buses)):
            a, b = buses[i], buses[j]
            if bus_kv[a] != bus_kv[b]:
                continue
            if not allow_parallel and (a, b) in conn:
                continue
            # Create multiple variants per bus pair
            for _ in range(max(1, variants_per_pair)):
                idx_gap = abs(i - j)
                base_len = 3.0 + idx_gap * 1.5  # km
                length_km = float(np.clip(np.random.normal(base_len, 1.5), 2.0, 50.0))
                vn = bus_kv[a]
                max_i_ka = (0.5 if vn >= 100 else 0.35) + np.random.uniform(-0.1, 0.1)
                pool.append(Candidate(from_bus=a, to_bus=b, vn_kv=vn, length_km=length_km, max_i_ka=max_i_ka))
                if len(pool) >= max_pairs:
                    return pool
    return pool


def inject_line(net: pp.pandapowerNet, cand: Candidate) -> int:
    """
    Inject a new line using parameter-based creation to avoid std_type dependency.
    Returns the created line index.
    """
    # Very rough per-km parameters; keep stable for IEEE14 scale.
    if cand.vn_kv >= 100:
        r_ohm_per_km = 0.06
        x_ohm_per_km = 0.32
        c_nf_per_km = 10.0
        max_i_ka = cand.max_i_ka
    else:
        r_ohm_per_km = 0.15
        x_ohm_per_km = 0.35
        c_nf_per_km = 8.0
        max_i_ka = cand.max_i_ka

    return pp.create_line_from_parameters(
        net,
        from_bus=cand.from_bus,
        to_bus=cand.to_bus,
        length_km=cand.length_km,
        r_ohm_per_km=r_ohm_per_km,
        x_ohm_per_km=x_ohm_per_km,
        c_nf_per_km=c_nf_per_km,
        max_i_ka=max_i_ka,
        name=f"cand_{cand.from_bus}_{cand.to_bus}_{cand.length_km:.1f}km",
        df=1.0,
        type="ol",
        parallel=1,
    )


def candidate_pool_expansions(net: pp.pandapowerNet, max_items: int = 100) -> List[ExpansionCandidate]:
    pool: List[ExpansionCandidate] = []
    if 'trafo' not in net or len(net.trafo) == 0:
        return pool
    for _, t in net.trafo.iterrows():
        hv = int(t.hv_bus)
        lv = int(t.lv_bus)
        vn = float(net.bus.at[hv, 'vn_kv'])
        # propose a small parallel transformer capacity (heuristic)
        add_sn = max(5.0, float(t.sn_mva) * 0.05)
        pool.append(ExpansionCandidate(hv_bus=hv, lv_bus=lv, vn_kv=vn, add_sn_mva=add_sn))
        if len(pool) >= max_items:
            break
    return pool


def inject_expansion(net: pp.pandapowerNet, cand: ExpansionCandidate) -> int:
    """Add a parallel transformer using parameters cloned from the first trafo between buses."""
    # find an existing trafo between the same buses to copy parameters
    base_idx = None
    for idx, t in net.trafo.iterrows():
        if int(t.hv_bus) == cand.hv_bus and int(t.lv_bus) == cand.lv_bus:
            base_idx = idx
            break
    if base_idx is None:
        # fallback: take first trafo
        base_idx = net.trafo.index[0]
    t = net.trafo.loc[base_idx]
    return pp.create_transformer_from_parameters(
        net,
        hv_bus=cand.hv_bus,
        lv_bus=cand.lv_bus,
        sn_mva=cand.add_sn_mva,
        vn_hv_kv=float(net.bus.at[cand.hv_bus, 'vn_kv']),
        vn_lv_kv=float(net.bus.at[cand.lv_bus, 'vn_kv']),
        vk_percent=float(t.vk_percent if not math.isnan(t.vk_percent) else 10.0),
        vkr_percent=float(t.vkr_percent if not math.isnan(t.vkr_percent) else 0.5),
        pfe_kw=float(t.pfe_kw if not math.isnan(t.pfe_kw) else 0.0),
        i0_percent=float(t.i0_percent if not math.isnan(t.i0_percent) else 0.0),
        shift_degree=float(t.shift_degree if not math.isnan(t.shift_degree) else 0.0),
        tap_side=str(t.tap_side) if not (isinstance(t.tap_side, float) and math.isnan(t.tap_side)) else 'hv',
        tap_neutral=int(t.tap_neutral) if not (isinstance(t.tap_neutral, float) and math.isnan(t.tap_neutral)) else 0,
        tap_min=int(t.tap_min) if not (isinstance(t.tap_min, float) and math.isnan(t.tap_min)) else 0,
        tap_max=int(t.tap_max) if not (isinstance(t.tap_max, float) and math.isnan(t.tap_max)) else 0,
        tap_step_percent=float(t.tap_step_percent if not math.isnan(t.tap_step_percent) else 2.5),
        tap_step_degree=float(t.tap_step_degree if not math.isnan(t.tap_step_degree) else 0.0),
    )


def _n_minus_1_penalty(net: pp.pandapowerNet) -> float:
    """Compute a simple N-1 penalty: fraction of single-line outages that are critical."""
    base = baseline_metrics(net)
    critical = 0
    total = len(net.line)
    if total == 0:
        return 0.0
    original = net.line['in_service'].copy()
    try:
        for idx in net.line.index:
            net.line.at[idx, 'in_service'] = False
            try:
                pp.runpp(net)
                met = baseline_metrics(net)
                if not net.converged or met['violations'] > base['violations']:
                    critical += 1
            except Exception:
                critical += 1
            finally:
                net.line.at[idx, 'in_service'] = original.at[idx]
    finally:
        net.line['in_service'] = original
    return critical / float(total)


def evaluate_candidate(base_net: pp.pandapowerNet, cand: Candidate, base_metrics: Dict[str, Any], run_n1_if_y_gt: float | None = None, n1_weight: float = 0.5) -> Dict[str, Any]:
    """Clone net, inject line, run pp, compute metrics & label."""
    net = base_net.deepcopy()
    try:
        inject_line(net, cand)
        pp.runpp(net)
        ok = True
    except Exception:
        ok = False

    if not ok or not net.converged:
        return {
            'ok': False,
            'y': -1.0,  # penalize failed
        }

    met = baseline_metrics(net)

    # Improvements (positive is good)
    d_viol = base_metrics['violations'] - met['violations']
    d_max_loading = (base_metrics['max_loading_percent'] - met['max_loading_percent']) / 100.0
    d_losses = base_metrics['total_losses_mw'] - met['total_losses_mw']

    # Cost penalty (million CNY)
    cost_m = cand.length_km * COST_PER_KM_MILLION

    y = (
        W_VIOLATION_REDUCTION * d_viol +
        W_MAX_LOADING_IMPROVE * d_max_loading +
        W_LOSSES_REDUCTION * d_losses -
        W_COST * cost_m
    )

    # Optional N-1 penalty for promising samples
    if run_n1_if_y_gt is not None and y > run_n1_if_y_gt:
        try:
            penalty_frac = _n_minus_1_penalty(net)
            y -= n1_weight * penalty_frac
        except Exception:
            pass

    # Simple local features (can be extended)
    # Node degrees before injection
    deg = {int(b): 0 for b in base_net.bus.index}
    for _, line in base_net.line.iterrows():
        deg[int(line.from_bus)] += 1
        deg[int(line.to_bus)] += 1

    features = {
        'from_bus': cand.from_bus,
        'to_bus': cand.to_bus,
        'vn_kv': cand.vn_kv,
        'length_km': cand.length_km,
        'max_i_ka': cand.max_i_ka,
        'deg_from': deg.get(cand.from_bus, 0),
        'deg_to': deg.get(cand.to_bus, 0),
        'base_violations': base_metrics['violations'],
        'base_max_loading_percent': base_metrics['max_loading_percent'],
        'base_total_losses_mw': base_metrics['total_losses_mw'],
    }

    return {
        'ok': True,
        'y': float(y),
        **features
    }


def main():
    parser = argparse.ArgumentParser(description='Generate training samples on IEEE14 (new line candidates).')
    parser.add_argument('--samples', type=int, default=1000, help='number of samples to generate')
    parser.add_argument('--variants-per-pair', type=int, default=10, help='how many variants to sample per bus pair')
    parser.add_argument('--output', type=str, default='data/ml/ieee14_newline_samples.csv', help='output CSV path (under backend)')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--networks', type=str, default='case14', help='comma separated pandapower networks, e.g., case14,case30')
    parser.add_argument('--scales', type=str, default='1.0', help='comma separated load scales, e.g., 0.9,1.0,1.1')
    parser.add_argument('--n1-threshold', type=float, default=0.2, help='run N-1 if preliminary y greater than this')
    parser.add_argument('--n1-weight', type=float, default=0.5, help='weight of N-1 penalty in label')
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)

    nets = [s.strip() for s in args.networks.split(',') if s.strip()]
    scales = [float(s.strip()) for s in args.scales.split(',') if s.strip()]

    rows = []
    per_scenario = max(1, args.samples // max(1, len(nets) * len(scales)))

    for net_name in nets:
        for sc in scales:
            base_net = build_base_net(net_name, sc)
            base_met = baseline_metrics(base_net)
            pool = candidate_pool_new_lines(base_net, max_pairs=per_scenario * 20, variants_per_pair=args.variants_per_pair, allow_parallel=True)
            used = 0
            for cand in pool:
                if used >= per_scenario:
                    break
                res = evaluate_candidate(base_net, cand, base_met, run_n1_if_y_gt=args.n1_threshold, n1_weight=args.n1_weight)
                if not res.get('ok'):
                    continue
                # Scenario metadata for analysis
                res['scenario_net'] = net_name
                res['scenario_scale'] = sc
                rows.append(res)
                used += 1

            # Also generate expansion candidates (lighter volume per scenario)
            exp_pool = candidate_pool_expansions(base_net, max_items=max(5, per_scenario // 10))
            for exp in exp_pool:
                net2 = base_net.deepcopy()
                try:
                    inject_expansion(net2, exp)
                    pp.runpp(net2)
                except Exception:
                    continue
                met = baseline_metrics(net2)
                d_viol = base_met['violations'] - met['violations']
                d_max_loading = (base_met['max_loading_percent'] - met['max_loading_percent']) / 100.0
                d_losses = base_met['total_losses_mw'] - met['total_losses_mw']
                cost_m = 0.0  # treat as local retrofit; cost omitted in minimal version
                y = W_VIOLATION_REDUCTION * d_viol + W_MAX_LOADING_IMPROVE * d_max_loading + W_LOSSES_REDUCTION * d_losses - W_COST * cost_m
                # optional N-1
                if y > args.n1_threshold:
                    try:
                        y -= args.n1_weight * _n_minus_1_penalty(net2)
                    except Exception:
                        pass

                # degrees
                deg = {int(b): 0 for b in base_net.bus.index}
                for _, line in base_net.line.iterrows():
                    deg[int(line.from_bus)] += 1
                    deg[int(line.to_bus)] += 1
                row = {
                    'ok': True,
                    'y': float(y),
                    'from_bus': int(exp.hv_bus),
                    'to_bus': int(exp.lv_bus),
                    'vn_kv': float(exp.vn_kv),
                    'length_km': 0.0,
                    'max_i_ka': 0.5 if float(exp.vn_kv) >= 100 else 0.35,
                    'deg_from': deg.get(int(exp.hv_bus), 0),
                    'deg_to': deg.get(int(exp.lv_bus), 0),
                    'base_violations': base_met['violations'],
                    'base_max_loading_percent': base_met['max_loading_percent'],
                    'base_total_losses_mw': base_met['total_losses_mw'],
                    'scenario_net': net_name,
                    'scenario_scale': sc,
                }
                rows.append(row)

    if not rows:
        raise RuntimeError('No successful samples generated')

    df = pd.DataFrame(rows)
    # Keep columns order: features then label
    cols = [c for c in df.columns if c not in ('ok', 'y')] + ['y']
    df = df[cols]
    df.to_csv(args.output, index=False)

    print(f"✓ Generated {len(df)} samples → {args.output}")


if __name__ == '__main__':
    main()
