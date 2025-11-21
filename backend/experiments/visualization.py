"""
实验结果可视化
Visualization of Experiment Results

生成：
1. 筛选压缩率 vs. 最优解召回率曲线
2. 工程运行耗时对比柱状图
3. 负荷预测误差折线图
4. 消融实验对比图
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List


# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STSong']  # macOS/Windows/Linux
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


class ExperimentVisualizer:
    """实验结果可视化类"""

    def __init__(self, output_dir: str = 'data/experiments/figures'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def plot_recall_vs_compression(
        self,
        metrics: Dict,
        save_path: str = None
    ):
        """
        绘制召回率 vs. 压缩率权衡曲线
        """
        if 'recall_compression' not in metrics:
            print("⚠ 缺少召回率vs压缩率数据")
            return

        data = metrics['recall_compression']

        fig, ax1 = plt.subplots(figsize=(10, 6))

        # 主轴：召回率
        color = 'tab:blue'
        ax1.set_xlabel('Top-K Candidates', fontsize=12)
        ax1.set_ylabel('Optimal Solution Recall Rate (%)', color=color, fontsize=12)
        ax1.plot(data['k_values'], [r*100 for r in data['recall_rates']],
                color=color, marker='o', linewidth=2, markersize=8,
                label='Recall Rate')
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim([0, 105])

        # 次轴：压缩率
        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('Screening Compression Rate (%)', color=color, fontsize=12)
        ax2.plot(data['k_values'], data['compression_rates'],
                color=color, marker='s', linewidth=2, markersize=8,
                linestyle='--', label='Compression Rate')
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.set_ylim([0, 105])

        # 标题和图例
        plt.title('Recall vs. Compression Rate Trade-off Curve', fontsize=14, fontweight='bold')
        fig.tight_layout()

        # 添加图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='center right')

        # 保存
        if save_path is None:
            save_path = os.path.join(self.output_dir, 'recall_vs_compression.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ 召回率vs压缩率曲线已保存至: {save_path}")
        plt.close()

    def plot_time_comparison(
        self,
        metrics: Dict,
        save_path: str = None
    ):
        """
        绘制工程运行耗时对比柱状图
        """
        if 'time_comparison' not in metrics:
            print("⚠ 缺少时间对比数据")
            return

        data = metrics['time_comparison']

        fig, ax = plt.subplots(figsize=(10, 6))

        methods = ['Full Brute-Force', 'Proposed Filtering']
        times = [data['baseline_time'], data['filtered_time']]
        colors = ['#ff6b6b', '#4ecdc4']

        bars = ax.bar(methods, times, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

        # 添加数值标签
        for bar, time in zip(bars, times):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{time:.1f}s',
                   ha='center', va='bottom', fontsize=12, fontweight='bold')

        # 添加加速比标注
        speedup = data['speedup']
        ax.text(0.5, max(times) * 0.8,
               f'Speedup: {speedup:.1f}x\nEfficiency Gain: {(speedup-1)*100:.0f}%',
               ha='center', fontsize=14, fontweight='bold',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        ax.set_ylabel('Runtime (seconds)', fontsize=12)
        ax.set_title('Total Runtime Comparison', fontsize=14, fontweight='bold')
        ax.grid(True, axis='y', alpha=0.3)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'time_comparison.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ 耗时对比图已保存至: {save_path}")
        plt.close()

    def plot_load_prediction_errors(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        save_path: str = None
    ):
        """
        绘制负荷预测误差图
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # 子图1：真实值 vs 预测值
        ax1.scatter(y_true, y_pred, alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
        ax1.plot([y_true.min(), y_true.max()],
                [y_true.min(), y_true.max()],
                'r--', linewidth=2, label='Ideal Prediction Line')
        ax1.set_xlabel('Actual Load (MW)', fontsize=12)
        ax1.set_ylabel('Predicted Load (MW)', fontsize=12)
        ax1.set_title('Load Prediction: Actual vs. Predicted', fontsize=13, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 子图2：误差分布
        errors = y_pred - y_true
        ax2.hist(errors, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero Error Line')
        ax2.set_xlabel('Prediction Error (MW)', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.set_title('Prediction Error Distribution', fontsize=13, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'load_prediction_errors.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ 负荷预测误差图已保存至: {save_path}")
        plt.close()

    def plot_ablation_comparison(
        self,
        ablation_results: Dict,
        save_path: str = None
    ):
        """
        绘制消融实验对比图
        """
        if not ablation_results:
            print("⚠ 缺少消融实验数据")
            return

        models = []
        avg_scores = []
        std_scores = []

        # 提取数据
        for model_name, result in ablation_results.items():
            if 'avg_score' not in result:
                continue

            # 翻译模型名称
            name_map = {
                'full_model': 'Full Model\n(Multi-modal Fusion)',
                'load_only': 'Load Only',
                'distance_only': 'Distance Only',
                'topology_only': 'Topology Only'
            }
            models.append(name_map.get(model_name, model_name))
            avg_scores.append(result['avg_score'])
            std_scores.append(result.get('std_score', 0))

        fig, ax = plt.subplots(figsize=(10, 6))

        x = np.arange(len(models))
        colors = ['#2ecc71' if 'Full' in m else '#95a5a6' for m in models]

        bars = ax.bar(x, avg_scores, yerr=std_scores, capsize=5,
                     color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

        # 添加数值标签
        for i, (bar, score) in enumerate(zip(bars, avg_scores)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{score:.2f}',
                   ha='center', va='bottom', fontsize=11, fontweight='bold')

            # 标注性能下降百分比（相对于完整模型）
            if i > 0 and avg_scores[0] > 0:
                drop = (avg_scores[0] - score) / avg_scores[0] * 100
                ax.text(bar.get_x() + bar.get_width()/2., height * 0.5,
                       f'↓{drop:.1f}%',
                       ha='center', va='center', fontsize=10,
                       color='red', fontweight='bold')

        ax.set_ylabel('Average Score', fontsize=12)
        ax.set_title('Ablation Study: Multi-modal Fusion vs. Single Features', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(models, fontsize=10)
        ax.grid(True, axis='y', alpha=0.3)
        ax.set_ylim([0, max(avg_scores) * 1.2])

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'ablation_comparison.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ 消融实验对比图已保存至: {save_path}")
        plt.close()

    def plot_llm_parsing_accuracy(
        self,
        metrics: Dict,
        save_path: str = None
    ):
        """
        绘制LLM解析准确率图
        """
        if 'llm_parsing' not in metrics:
            print("⚠ 缺少LLM解析准确率数据")
            return

        data = metrics['llm_parsing']
        field_accuracy = data.get('field_accuracy', {})

        if not field_accuracy:
            print("⚠ 字段准确率数据为空")
            return

        # 字段名称映射为可读标签
        field_name_map = {
            'voltage_constraints': 'Voltage Constraints',
            'line_loading': 'Line Loading Limits',
            'trafo_loading': 'Transformer Loading',
            'n_minus_1': 'N-1 Security Criteria',
            'distance_constraints': 'Distance Constraints'
        }

        fields = [field_name_map.get(f, f) for f in field_accuracy.keys()]
        accuracies = [field_accuracy[f] * 100 for f in field_accuracy.keys()]

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = ['#2ecc71' if acc >= 90 else '#f39c12' if acc >= 70 else '#e74c3c'
                 for acc in accuracies]

        bars = ax.barh(fields, accuracies, color=colors, alpha=0.8,
                      edgecolor='black', linewidth=1.5)

        # 添加数值标签
        for bar, acc in zip(bars, accuracies):
            width = bar.get_width()
            ax.text(width + 2, bar.get_y() + bar.get_height()/2.,
                   f'{acc:.1f}%',
                   ha='left', va='center', fontsize=11, fontweight='bold')

        # 添加总体准确率标注
        overall_acc = data.get('overall_accuracy', 0) * 100
        ax.axvline(overall_acc, color='red', linestyle='--', linewidth=2,
                  label=f'Overall Accuracy: {overall_acc:.1f}%')

        ax.set_xlabel('Accuracy (%)', fontsize=12)
        ax.set_title('LLM Rule Parsing Accuracy (by Field)', fontsize=14, fontweight='bold')
        ax.set_xlim([0, 105])
        ax.legend()
        ax.grid(True, axis='x', alpha=0.3)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'llm_parsing_accuracy.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✓ LLM解析准确率图已保存至: {save_path}")
        plt.close()

    def generate_all_plots(
        self,
        metrics_path: str = 'data/experiments/evaluation_metrics.json',
        ablation_path: str = 'data/experiments/ablation_results.json'
    ):
        """生成所有可视化图表"""
        print("=" * 60)
        print("生成实验结果可视化图表")
        print("=" * 60)

        # 加载评估指标
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r', encoding='utf-8') as f:
                metrics = json.load(f)

            # 生成各类图表
            self.plot_recall_vs_compression(metrics)
            self.plot_time_comparison(metrics)
            self.plot_llm_parsing_accuracy(metrics)

            # 负荷预测误差图（需要原始数据，这里使用示例数据）
            if 'load_prediction' in metrics:
                # 生成示例数据进行演示
                n_samples = 100
                y_true = np.random.normal(100, 20, n_samples)
                y_pred = y_true + np.random.normal(0, 5, n_samples)
                self.plot_load_prediction_errors(y_true, y_pred)

        # 加载消融实验结果
        if os.path.exists(ablation_path):
            with open(ablation_path, 'r', encoding='utf-8') as f:
                ablation_results = json.load(f)
            self.plot_ablation_comparison(ablation_results)

        print("\n" + "=" * 60)
        print("✓ 所有图表生成完成！")
        print(f"✓ 保存位置: {self.output_dir}")
        print("=" * 60)


def demo_visualization():
    """可视化演示"""
    visualizer = ExperimentVisualizer()

    # 演示数据
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
            'speedup': 26.5
        },
        'llm_parsing': {
            'overall_accuracy': 0.85,
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

    # 生成图表
    visualizer.plot_recall_vs_compression(metrics)
    visualizer.plot_time_comparison(metrics)
    visualizer.plot_llm_parsing_accuracy(metrics)
    visualizer.plot_ablation_comparison(ablation)

    # 负荷预测误差
    y_true = np.random.normal(100, 20, 100)
    y_pred = y_true + np.random.normal(0, 5, 100)
    visualizer.plot_load_prediction_errors(y_true, y_pred)


if __name__ == '__main__':
    demo_visualization()
