"""
基准测试：全量候选方案暴力仿真
Baseline: Brute-force simulation of all candidate solutions

用于生成"筛选压缩率 vs. 最优解召回率"权衡曲线的基准数据
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from typing import List, Dict, Tuple
import numpy as np
from services.gis_service import gis_service
from services.load_prediction import load_prediction
from services.power_flow import power_flow
from services.scorer import scorer
from config import Config


class BaselineBruteForce:
    """全量基准测试类"""

    def __init__(self):
        self.results = {
            'all_candidates': [],
            'evaluated_candidates': [],
            'optimal_solution': None,
            'total_time': 0,
            'evaluation_times': []
        }

    def generate_all_candidates(self, overload_areas: List[Dict]) -> List[Dict]:
        """
        生成所有可能的候选方案（不做初步筛选）
        Returns: 完整的候选方案列表
        """
        print("=" * 60)
        print("生成全量候选方案...")
        print("=" * 60)

        candidates = gis_service.get_expansion_candidates(overload_areas)

        print(f"✓ 总候选方案数: {len(candidates)}")
        print(f"  - 新建变电站: {sum(1 for c in candidates if c['type'] == 'new_substation')}")
        print(f"  - 变电站扩容: {sum(1 for c in candidates if c['type'] == 'substation_expansion')}")
        print(f"  - 新建线路: {sum(1 for c in candidates if c['type'] == 'new_line')}")

        self.results['all_candidates'] = candidates
        return candidates

    def evaluate_all_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """
        对所有候选方案进行详细的潮流仿真评估
        Returns: 评估后的候选方案列表（按性能排序）
        """
        print("\n" + "=" * 60)
        print("全量潮流仿真评估...")
        print("=" * 60)

        start_time = time.time()
        evaluated = []

        for i, candidate in enumerate(candidates, 1):
            print(f"\r评估进度: {i}/{len(candidates)} ({i/len(candidates)*100:.1f}%)", end='', flush=True)

            eval_start = time.time()

            # 潮流计算评估
            pf_result = power_flow.evaluate_candidate_with_power_flow(candidate)

            eval_time = time.time() - eval_start
            self.results['evaluation_times'].append(eval_time)

            # 计算综合得分
            score = self._calculate_comprehensive_score(candidate, pf_result)

            evaluated.append({
                'candidate': candidate,
                'power_flow_result': pf_result,
                'comprehensive_score': score,
                'evaluation_time': eval_time
            })

        print()  # 换行

        # 按综合得分排序
        evaluated.sort(key=lambda x: x['comprehensive_score'], reverse=True)

        total_time = time.time() - start_time
        self.results['total_time'] = total_time
        self.results['evaluated_candidates'] = evaluated
        self.results['optimal_solution'] = evaluated[0] if evaluated else None

        print(f"\n✓ 全量评估完成")
        print(f"  - 总耗时: {total_time:.2f}秒")
        print(f"  - 平均每个方案: {total_time/len(candidates):.3f}秒")
        print(f"  - 最优方案得分: {evaluated[0]['comprehensive_score']:.2f}")

        return evaluated

    def _calculate_comprehensive_score(self, candidate: Dict, pf_result: Dict) -> float:
        """
        计算综合得分（考虑潮流结果、成本、可行性等）
        """
        score = 0.0

        # 潮流验证通过加分
        if pf_result.get('passed', False):
            score += 50

            # 根据潮流收敛质量加分
            pf_data = pf_result.get('power_flow', {})
            if pf_data.get('converged', False):
                score += 20

                # 无违规项加分
                violations = pf_data.get('violations', [])
                if not violations:
                    score += 20
                else:
                    # 违规项越少得分越高
                    score += max(0, 20 - len(violations) * 2)

        # 成本得分（成本越低得分越高）
        cost = candidate.get('estimated_cost_m', 100)
        cost_score = max(0, 20 - cost / 10)
        score += cost_score

        # N-1校验通过加分
        n1_result = pf_result.get('n_minus_1', {})
        if n1_result.get('n_minus_1_passed', False):
            score += 30

        return score

    def save_results(self, output_path: str = 'data/experiments/baseline_results.json'):
        """保存基准测试结果"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 转换为可序列化格式
        serializable_results = {
            'total_candidates': len(self.results['all_candidates']),
            'total_time': self.results['total_time'],
            'avg_time_per_candidate': np.mean(self.results['evaluation_times']) if self.results['evaluation_times'] else 0,
            'optimal_score': self.results['optimal_solution']['comprehensive_score'] if self.results['optimal_solution'] else 0,
            'optimal_candidate_type': self.results['optimal_solution']['candidate']['type'] if self.results['optimal_solution'] else None,
            'top_10_scores': [e['comprehensive_score'] for e in self.results['evaluated_candidates'][:10]],
            'evaluation_times': self.results['evaluation_times']
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        print(f"\n✓ 基准结果已保存至: {output_path}")

    def get_top_k_candidates(self, k: int = 10) -> List[Dict]:
        """获取Top-K候选方案"""
        return self.results['evaluated_candidates'][:k]


def run_baseline_test():
    """运行完整的基准测试"""
    print("=" * 60)
    print("基准测试：全量候选方案暴力仿真")
    print("Baseline: Brute-force Simulation")
    print("=" * 60)

    # 初始化服务
    print("\n初始化服务...")
    load_prediction.load_historical_data()
    gis_service.load_network_data()

    # 获取过载区域
    load_summary = load_prediction.get_load_summary()
    overload_areas = load_summary['overload_areas']
    print(f"✓ 检测到 {len(overload_areas)} 个过载区域")

    # 创建基准测试实例
    baseline = BaselineBruteForce()

    # 1. 生成所有候选方案
    candidates = baseline.generate_all_candidates(overload_areas)

    # 2. 全量评估
    evaluated = baseline.evaluate_all_candidates(candidates)

    # 3. 保存结果
    baseline.save_results()

    # 4. 输出Top-5结果
    print("\n" + "=" * 60)
    print("Top-5 最优方案:")
    print("=" * 60)
    top_5 = baseline.get_top_k_candidates(5)
    for i, item in enumerate(top_5, 1):
        c = item['candidate']
        score = item['comprehensive_score']
        print(f"{i}. [{c['type']}] 得分: {score:.2f} | 成本: {c.get('estimated_cost_m', 0):.1f}M")

    return baseline


if __name__ == '__main__':
    baseline = run_baseline_test()
    print("\n" + "=" * 60)
    print("基准测试完成！")
    print("=" * 60)
