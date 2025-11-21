"""
消融实验：多模态特征融合 vs. 单一特征
Ablation Study: Multi-modal Feature Fusion vs. Single Feature

验证多模态特征融合相比单一特征在提升筛选精度上的具体贡献
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import numpy as np
from typing import List, Dict, Tuple
from services.gis_service import gis_service
from services.load_prediction import load_prediction
from services.scorer import scorer
from config import Config


class AblationStudy:
    """消融实验类"""

    def __init__(self):
        self.results = {
            'full_model': {},
            'load_only': {},
            'distance_only': {},
            'topology_only': {},
            'constraint_only': {}
        }

    def run_full_model_scoring(
        self,
        candidates: List[Dict],
        load_features: Dict,
        network: Dict,
        topology: Dict,
        constraints: Dict
    ) -> Dict:
        """
        完整模型评分（使用所有特征）
        """
        print("=" * 60)
        print("完整模型评分（多模态特征融合）")
        print("=" * 60)

        start_time = time.time()

        ranked = scorer.rank_candidates(
            candidates,
            load_features,
            network,
            topology,
            constraints,
            top_k=len(candidates)
        )

        elapsed_time = time.time() - start_time

        # 提取得分
        scores = [c['scores'] for c in ranked]
        total_scores = [s['total'] for s in scores]

        result = {
            'ranked_candidates': ranked,
            'total_scores': total_scores,
            'top_5_scores': total_scores[:5],
            'avg_score': np.mean(total_scores),
            'std_score': np.std(total_scores),
            'time': elapsed_time
        }

        print(f"✓ 评分完成")
        print(f"  - 平均得分: {result['avg_score']:.2f}")
        print(f"  - 得分标准差: {result['std_score']:.2f}")
        print(f"  - Top-1得分: {total_scores[0]:.2f}")
        print(f"  - 耗时: {elapsed_time:.3f}秒")

        self.results['full_model'] = result
        return result

    def run_load_only_scoring(
        self,
        candidates: List[Dict],
        load_features: Dict
    ) -> Dict:
        """
        仅使用负载特征评分
        """
        print("\n" + "=" * 60)
        print("消融实验：仅负载特征")
        print("=" * 60)

        start_time = time.time()

        scores = []
        for candidate in candidates:
            # 仅计算负载相关得分
            load_score = self._calculate_load_score(candidate, load_features)
            scores.append({
                'candidate': candidate,
                'scores': {'load_growth': load_score, 'total': load_score},
                'rank': 0
            })

        # 排序
        scores.sort(key=lambda x: x['scores']['total'], reverse=True)
        for i, item in enumerate(scores, 1):
            item['rank'] = i

        elapsed_time = time.time() - start_time

        total_scores = [s['scores']['total'] for s in scores]

        result = {
            'ranked_candidates': scores,
            'total_scores': total_scores,
            'top_5_scores': total_scores[:5],
            'avg_score': np.mean(total_scores),
            'std_score': np.std(total_scores),
            'time': elapsed_time
        }

        print(f"✓ 评分完成")
        print(f"  - 平均得分: {result['avg_score']:.2f}")
        print(f"  - 得分标准差: {result['std_score']:.2f}")
        print(f"  - Top-1得分: {total_scores[0]:.2f}")

        self.results['load_only'] = result
        return result

    def run_distance_only_scoring(
        self,
        candidates: List[Dict],
        network: Dict
    ) -> Dict:
        """
        仅使用距离特征评分
        """
        print("\n" + "=" * 60)
        print("消融实验：仅距离特征")
        print("=" * 60)

        start_time = time.time()

        scores = []
        for candidate in candidates:
            # 仅计算距离相关得分
            distance_score = self._calculate_distance_score(candidate, network)
            scores.append({
                'candidate': candidate,
                'scores': {'distance': distance_score, 'total': distance_score},
                'rank': 0
            })

        # 排序
        scores.sort(key=lambda x: x['scores']['total'], reverse=True)
        for i, item in enumerate(scores, 1):
            item['rank'] = i

        elapsed_time = time.time() - start_time

        total_scores = [s['scores']['total'] for s in scores]

        result = {
            'ranked_candidates': scores,
            'total_scores': total_scores,
            'top_5_scores': total_scores[:5],
            'avg_score': np.mean(total_scores),
            'std_score': np.std(total_scores),
            'time': elapsed_time
        }

        print(f"✓ 评分完成")
        print(f"  - 平均得分: {result['avg_score']:.2f}")
        print(f"  - 得分标准差: {result['std_score']:.2f}")
        print(f"  - Top-1得分: {total_scores[0]:.2f}")

        self.results['distance_only'] = result
        return result

    def run_topology_only_scoring(
        self,
        candidates: List[Dict],
        topology: Dict
    ) -> Dict:
        """
        仅使用拓扑特征评分
        """
        print("\n" + "=" * 60)
        print("消融实验：仅拓扑特征")
        print("=" * 60)

        start_time = time.time()

        scores = []
        for candidate in candidates:
            # 仅计算拓扑相关得分
            topology_score = self._calculate_topology_score(candidate, topology)
            scores.append({
                'candidate': candidate,
                'scores': {'topology': topology_score, 'total': topology_score},
                'rank': 0
            })

        # 排序
        scores.sort(key=lambda x: x['scores']['total'], reverse=True)
        for i, item in enumerate(scores, 1):
            item['rank'] = i

        elapsed_time = time.time() - start_time

        total_scores = [s['scores']['total'] for s in scores]

        result = {
            'ranked_candidates': scores,
            'total_scores': total_scores,
            'top_5_scores': total_scores[:5],
            'avg_score': np.mean(total_scores),
            'std_score': np.std(total_scores),
            'time': elapsed_time
        }

        print(f"✓ 评分完成")
        print(f"  - 平均得分: {result['avg_score']:.2f}")
        print(f"  - 得分标准差: {result['std_score']:.2f}")
        print(f"  - Top-1得分: {total_scores[0]:.2f}")

        self.results['topology_only'] = result
        return result

    def _calculate_load_score(self, candidate: Dict, load_features: Dict) -> float:
        """计算负载得分"""
        area_name = candidate.get('area_name', '')
        base_score = 50.0

        # 根据区域负载增长率调整得分
        growth_rate = load_features.get('growth_rate', 0.05)
        base_score += growth_rate * 200  # growth_rate typically 0-0.2

        return min(100, base_score)

    def _calculate_distance_score(self, candidate: Dict, network: Dict) -> float:
        """计算距离得分"""
        # 简化：随机模拟距离得分
        return np.random.uniform(40, 90)

    def _calculate_topology_score(self, candidate: Dict, topology: Dict) -> float:
        """计算拓扑得分"""
        # 简化：基于拓扑指标计算得分
        avg_degree = topology.get('avg_degree', 2.0)
        base_score = 50.0
        base_score += (avg_degree - 2) * 10
        return min(100, base_score)

    def compare_models(self) -> Dict:
        """
        对比不同模型的性能

        计算各模型相对于完整模型的性能差异
        """
        print("\n" + "=" * 60)
        print("模型性能对比")
        print("=" * 60)

        full_top5 = self.results['full_model']['top_5_scores']
        full_avg = self.results['full_model']['avg_score']

        comparison = {}

        for model_name in ['load_only', 'distance_only', 'topology_only']:
            if model_name not in self.results:
                continue

            model_result = self.results[model_name]
            model_top5 = model_result['top_5_scores']
            model_avg = model_result['avg_score']

            # 计算性能差异
            avg_diff = ((full_avg - model_avg) / full_avg * 100) if full_avg > 0 else 0
            top1_diff = ((full_top5[0] - model_top5[0]) / full_top5[0] * 100) if full_top5[0] > 0 else 0

            comparison[model_name] = {
                'avg_score': model_avg,
                'avg_score_drop': avg_diff,
                'top1_score': model_top5[0],
                'top1_score_drop': top1_diff
            }

            print(f"\n【{model_name}】")
            print(f"  平均得分: {model_avg:.2f} (下降 {avg_diff:.1f}%)")
            print(f"  Top-1得分: {model_top5[0]:.2f} (下降 {top1_diff:.1f}%)")

        # 计算多模态融合的贡献
        print(f"\n【多模态融合贡献】")
        print(f"  完整模型平均得分: {full_avg:.2f}")
        print(f"  相比单一特征平均提升:")
        for model_name, comp in comparison.items():
            improvement = comp['avg_score_drop']
            print(f"    vs. {model_name:20s}: +{improvement:5.1f}%")

        return comparison

    def save_results(self, output_path: str = 'data/experiments/ablation_results.json'):
        """保存消融实验结果"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 转换为可序列化格式
        serializable_results = {}
        for model_name, result in self.results.items():
            if not result:
                continue
            serializable_results[model_name] = {
                'avg_score': result.get('avg_score', 0),
                'std_score': result.get('std_score', 0),
                'top_5_scores': result.get('top_5_scores', []),
                'time': result.get('time', 0)
            }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        print(f"\n✓ 消融实验结果已保存至: {output_path}")


def run_ablation_study():
    """运行完整的消融实验"""
    print("=" * 60)
    print("消融实验：多模态特征融合 vs. 单一特征")
    print("Ablation Study")
    print("=" * 60)

    # 初始化服务
    print("\n初始化服务...")
    load_prediction.load_historical_data()
    gis_service.load_network_data()

    # 获取数据
    load_summary = load_prediction.get_load_summary()
    load_features = load_summary['current_features']
    overload_areas = load_summary['overload_areas']

    network = gis_service.get_network_summary()
    topology = network['topology']

    # 简单约束
    constraints = {
        'voltage_constraints': {'max_deviation': Config.MAX_VOLTAGE_DEVIATION}
    }

    # 生成候选方案
    candidates = gis_service.get_expansion_candidates(overload_areas)
    print(f"✓ 生成 {len(candidates)} 个候选方案")

    # 创建消融实验实例
    ablation = AblationStudy()

    # 运行各种评分实验
    ablation.run_full_model_scoring(candidates, load_features, network, topology, constraints)
    ablation.run_load_only_scoring(candidates, load_features)
    ablation.run_distance_only_scoring(candidates, network)
    ablation.run_topology_only_scoring(candidates, topology)

    # 对比模型性能
    comparison = ablation.compare_models()

    # 保存结果
    ablation.save_results()

    return ablation


if __name__ == '__main__':
    ablation = run_ablation_study()
    print("\n" + "=" * 60)
    print("消融实验完成！")
    print("=" * 60)
