"""
快速测试脚本
Quick Test Script

用于验证实验框架是否正常工作
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from evaluation_metrics import EvaluationMetrics
from visualization import ExperimentVisualizer


def test_metrics():
    """测试评估指标计算"""
    print("=" * 60)
    print("测试评估指标计算模块")
    print("=" * 60)

    evaluator = EvaluationMetrics()

    # 测试召回率vs压缩率
    baseline_results = {
        'total_candidates': 100,
        'top_10_scores': [95, 93, 91, 89, 87, 85, 83, 81, 79, 77]
    }
    filtered_results = {
        'top_k_scores': [95, 93, 91, 89, 87]
    }
    evaluator.calculate_recall_vs_compression(baseline_results, filtered_results, k_values=[5, 10, 20])

    # 测试时间对比
    evaluator.calculate_time_comparison(
        baseline_time=1200.5,
        filtered_time=45.3,
        baseline_candidates=100,
        filtered_candidates=10
    )

    # 测试负荷预测误差
    y_true = np.array([100, 110, 105, 115, 120, 125, 130, 135])
    y_pred = np.array([98, 112, 103, 117, 118, 127, 128, 137])
    evaluator.calculate_load_prediction_errors(y_true, y_pred)

    # 测试LLM解析准确率
    ground_truth = [{
        'voltage_constraints': {'max_deviation': 0.05},
        'line_loading': {'max_loading': 0.9},
        'trafo_loading': {'max_loading': 0.85}
    }]
    llm_parsed = [{
        'voltage_constraints': {'max_deviation': 0.05},
        'line_loading': {'max_loading': 0.9},
        'trafo_loading': {'max_loading': 0.8}
    }]
    evaluator.calculate_llm_parsing_accuracy(ground_truth, llm_parsed)

    # 保存结果
    evaluator.save_all_metrics('data/experiments/test_metrics.json')
    evaluator.print_summary()

    print("\n✓ 评估指标测试通过")
    return evaluator


def test_visualization():
    """测试可视化模块"""
    print("\n" + "=" * 60)
    print("测试可视化模块")
    print("=" * 60)

    visualizer = ExperimentVisualizer(output_dir='data/experiments/test_figures')

    # 测试数据
    metrics = {
        'recall_compression': {
            'k_values': [5, 10, 20, 50],
            'compression_rates': [95, 90, 80, 50],
            'recall_rates': [1.0, 1.0, 1.0, 1.0],
            'precision_at_k': [0.8, 0.7, 0.6, 0.4]
        },
        'time_comparison': {
            'baseline_time': 1200.5,
            'filtered_time': 45.3,
            'speedup': 26.5,
            'baseline_candidates': 100,
            'filtered_candidates': 10
        },
        'llm_parsing': {
            'overall_accuracy': 0.85,
            'correct_fields': 4,
            'total_fields': 5,
            'field_accuracy': {
                'voltage_constraints': 0.9,
                'line_loading': 0.85,
                'trafo_loading': 0.8,
                'n_minus_1': 0.9,
                'distance_constraints': 0.75
            }
        }
    }

    ablation = {
        'full_model': {'avg_score': 85.5, 'std_score': 5.2},
        'load_only': {'avg_score': 72.3, 'std_score': 6.1},
        'distance_only': {'avg_score': 68.7, 'std_score': 7.3},
        'topology_only': {'avg_score': 70.1, 'std_score': 6.8}
    }

    # 生成所有图表
    visualizer.plot_recall_vs_compression(metrics)
    visualizer.plot_time_comparison(metrics)
    visualizer.plot_llm_parsing_accuracy(metrics)
    visualizer.plot_ablation_comparison(ablation)

    # 负荷预测误差
    y_true = np.random.normal(100, 20, 50)
    y_pred = y_true + np.random.normal(0, 5, 50)
    visualizer.plot_load_prediction_errors(y_true, y_pred)

    print("\n✓ 可视化测试通过")
    print(f"✓ 图表已保存至: {visualizer.output_dir}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("实验框架快速测试")
    print("Quick Test of Experimental Framework")
    print("=" * 60)

    try:
        # 测试评估指标
        evaluator = test_metrics()

        # 测试可视化
        test_visualization()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("✓ All tests passed!")
        print("=" * 60)
        print("\n下一步：")
        print("1. 运行 python experiments/baseline_brute_force.py")
        print("2. 运行 python experiments/ablation_study.py")
        print("3. 运行 python experiments/run_all_experiments.py")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
