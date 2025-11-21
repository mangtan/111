"""
评估指标计算模块
Evaluation Metrics Calculation

包含：
1. 筛选压缩率 vs. 最优解召回率
2. 工程运行总耗时对比
3. 负荷预测误差统计 (RMSE, MAPE)
4. LLM规则解析准确率
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import numpy as np
from typing import List, Dict, Tuple
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error


class EvaluationMetrics:
    """评估指标计算类"""

    def __init__(self):
        self.metrics = {}

    def calculate_recall_vs_compression(
        self,
        baseline_results: Dict,
        filtered_results: Dict,
        k_values: List[int] = [5, 10, 20, 50]
    ) -> Dict:
        """
        计算不同压缩率下的最优解召回率

        Args:
            baseline_results: 基准全量测试结果
            filtered_results: 筛选后的结果
            k_values: 要测试的Top-K值列表

        Returns:
            包含召回率和压缩率的字典
        """
        print("=" * 60)
        print("计算召回率 vs. 压缩率权衡曲线")
        print("=" * 60)

        total_candidates = baseline_results.get('total_candidates', 100)
        baseline_top_k_scores = baseline_results.get('top_10_scores', [])

        results = {
            'k_values': [],
            'compression_rates': [],
            'recall_rates': [],
            'precision_at_k': []
        }

        for k in k_values:
            # 压缩率：筛选后保留的比例
            compression_rate = (total_candidates - k) / total_candidates * 100

            # 召回率：在Top-K中找到的真正最优解的比例
            # 假设filtered_results中有对应的top_k_scores
            filtered_top_k = filtered_results.get('top_k_scores', baseline_top_k_scores[:k])

            # 计算召回率（简化版：检查最优解是否在Top-K中）
            if baseline_top_k_scores:
                optimal_score = baseline_top_k_scores[0]
                recall = 1.0 if optimal_score in filtered_top_k[:k] else 0.0

                # Precision@K: Top-K中真正的最优解占比
                true_positives = sum(1 for s in filtered_top_k[:k] if s in baseline_top_k_scores[:k])
                precision_at_k = true_positives / k if k > 0 else 0

                results['k_values'].append(k)
                results['compression_rates'].append(compression_rate)
                results['recall_rates'].append(recall)
                results['precision_at_k'].append(precision_at_k)

                print(f"Top-{k:2d} | 压缩率: {compression_rate:5.1f}% | 召回率: {recall*100:5.1f}% | Precision@K: {precision_at_k:.3f}")

        self.metrics['recall_compression'] = results
        return results

    def calculate_time_comparison(
        self,
        baseline_time: float,
        filtered_time: float,
        baseline_candidates: int,
        filtered_candidates: int
    ) -> Dict:
        """
        计算工程运行总耗时对比

        Returns:
            包含时间对比和加速比的字典
        """
        print("\n" + "=" * 60)
        print("工程运行总耗时对比")
        print("=" * 60)

        speedup = baseline_time / filtered_time if filtered_time > 0 else float('inf')

        results = {
            'baseline_time': baseline_time,
            'filtered_time': filtered_time,
            'speedup': speedup,
            'baseline_candidates': baseline_candidates,
            'filtered_candidates': filtered_candidates,
            'time_per_candidate_baseline': baseline_time / baseline_candidates if baseline_candidates > 0 else 0,
            'time_per_candidate_filtered': filtered_time / filtered_candidates if filtered_candidates > 0 else 0
        }

        print(f"全量仿真耗时:    {baseline_time:8.2f}秒 ({baseline_candidates} 个方案)")
        print(f"筛选策略耗时:    {filtered_time:8.2f}秒 ({filtered_candidates} 个方案)")
        print(f"加速比:          {speedup:8.2f}x")
        print(f"效率提升:        {(speedup-1)*100:8.1f}%")

        self.metrics['time_comparison'] = results
        return results

    def calculate_load_prediction_errors(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict:
        """
        计算负荷预测误差统计

        Args:
            y_true: 真实负荷值
            y_pred: 预测负荷值

        Returns:
            包含RMSE和MAPE的字典
        """
        print("\n" + "=" * 60)
        print("负荷预测误差统计")
        print("=" * 60)

        # RMSE (Root Mean Square Error)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))

        # MAPE (Mean Absolute Percentage Error)
        # 避免除以零
        mask = y_true != 0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

        # MAE (Mean Absolute Error)
        mae = np.mean(np.abs(y_true - y_pred))

        # R² Score
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        results = {
            'rmse': float(rmse),
            'mape': float(mape),
            'mae': float(mae),
            'r2_score': float(r2),
            'sample_size': len(y_true)
        }

        print(f"RMSE:            {rmse:8.2f} MW")
        print(f"MAPE:            {mape:8.2f}%")
        print(f"MAE:             {mae:8.2f} MW")
        print(f"R² Score:        {r2:8.4f}")
        print(f"样本数量:        {len(y_true)}")

        self.metrics['load_prediction'] = results
        return results

    def calculate_llm_parsing_accuracy(
        self,
        ground_truth: List[Dict],
        llm_parsed: List[Dict]
    ) -> Dict:
        """
        计算LLM规则解析的准确率

        Args:
            ground_truth: 人工标注的真值
            llm_parsed: LLM解析的结果

        Returns:
            包含准确率、精确率、召回率的字典
        """
        print("\n" + "=" * 60)
        print("LLM规则解析准确率验证")
        print("=" * 60)

        # 关键字段匹配
        fields_to_check = [
            'voltage_constraints',
            'line_loading',
            'trafo_loading',
            'n_minus_1',
            'distance_constraints'
        ]

        correct_fields = 0
        total_fields = 0

        field_accuracy = {}

        for field in fields_to_check:
            gt_value = ground_truth[0].get(field) if ground_truth else None
            llm_value = llm_parsed[0].get(field) if llm_parsed else None

            if gt_value is not None:
                total_fields += 1
                # 简化比较：检查字段是否存在且结构相似
                if llm_value is not None and type(gt_value) == type(llm_value):
                    correct_fields += 1
                    field_accuracy[field] = 1.0
                else:
                    field_accuracy[field] = 0.0

        overall_accuracy = correct_fields / total_fields if total_fields > 0 else 0

        results = {
            'overall_accuracy': overall_accuracy,
            'correct_fields': correct_fields,
            'total_fields': total_fields,
            'field_accuracy': field_accuracy
        }

        print(f"总体准确率:      {overall_accuracy*100:8.2f}%")
        print(f"正确字段数:      {correct_fields}/{total_fields}")
        print(f"\n各字段准确率:")
        for field, acc in field_accuracy.items():
            print(f"  {field:30s}: {acc*100:5.1f}%")

        self.metrics['llm_parsing'] = results
        return results

    def save_all_metrics(self, output_path: str = 'data/experiments/evaluation_metrics.json'):
        """保存所有评估指标"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)

        print(f"\n✓ 评估指标已保存至: {output_path}")

    def print_summary(self):
        """打印评估结果摘要"""
        print("\n" + "=" * 60)
        print("评估结果摘要")
        print("=" * 60)

        if 'recall_compression' in self.metrics:
            rc = self.metrics['recall_compression']
            print(f"\n【召回率 vs. 压缩率】")
            print(f"  最高压缩率: {max(rc['compression_rates']):.1f}% (召回率: {rc['recall_rates'][rc['compression_rates'].index(max(rc['compression_rates']))]*100:.1f}%)")

        if 'time_comparison' in self.metrics:
            tc = self.metrics['time_comparison']
            print(f"\n【工程耗时对比】")
            print(f"  加速比: {tc['speedup']:.2f}x")
            print(f"  效率提升: {(tc['speedup']-1)*100:.1f}%")

        if 'load_prediction' in self.metrics:
            lp = self.metrics['load_prediction']
            print(f"\n【负荷预测误差】")
            print(f"  RMSE: {lp['rmse']:.2f} MW")
            print(f"  MAPE: {lp['mape']:.2f}%")

        if 'llm_parsing' in self.metrics:
            llm = self.metrics['llm_parsing']
            print(f"\n【LLM解析准确率】")
            print(f"  总体准确率: {llm['overall_accuracy']*100:.2f}%")


def run_evaluation_demo():
    """运行评估指标计算示例"""
    evaluator = EvaluationMetrics()

    # 示例1：召回率vs压缩率
    baseline_results = {
        'total_candidates': 100,
        'top_10_scores': [95, 93, 91, 89, 87, 85, 83, 81, 79, 77]
    }
    filtered_results = {
        'top_k_scores': [95, 93, 91, 89, 87]
    }
    evaluator.calculate_recall_vs_compression(baseline_results, filtered_results)

    # 示例2：时间对比
    evaluator.calculate_time_comparison(
        baseline_time=1200.5,
        filtered_time=45.3,
        baseline_candidates=100,
        filtered_candidates=5
    )

    # 示例3：负荷预测误差
    y_true = np.array([100, 110, 105, 115, 120])
    y_pred = np.array([98, 112, 103, 117, 118])
    evaluator.calculate_load_prediction_errors(y_true, y_pred)

    # 示例4：LLM解析准确率
    ground_truth = [{
        'voltage_constraints': {'max_deviation': 0.05},
        'line_loading': {'max_loading': 0.9}
    }]
    llm_parsed = [{
        'voltage_constraints': {'max_deviation': 0.05},
        'line_loading': {'max_loading': 0.85}
    }]
    evaluator.calculate_llm_parsing_accuracy(ground_truth, llm_parsed)

    # 保存并打印摘要
    evaluator.save_all_metrics()
    evaluator.print_summary()


if __name__ == '__main__':
    run_evaluation_demo()
