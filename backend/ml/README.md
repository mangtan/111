快速生成训练数据与基线模型（极速版）

目的
- 生成“新建线路”候选在 IEEE 14-bus 基网上的仿真样本，并用潮流结果自动打标签，训练一个简单的 GBDT 基线评分器。

包含
- generate_dataset.py: 生成候选→注入→潮流→打标，导出 CSV
- train_baseline.py: 训练 GradientBoostingRegressor 并输出指标与模型

使用
1) 进入后端虚拟环境
   cd backend
   source venv/bin/activate

2) 生成 1000 个样本
   python -m ml.generate_dataset --samples 1000 --output data/ml/ieee14_newline_samples.csv

3) 训练基线模型并评估
   python -m ml.train_baseline --data data/ml/ieee14_newline_samples.csv --model data/ml/gbdt_ieee14.joblib

说明
- 仅使用 pandapower 内置 IEEE 14-bus，不依赖外部下载。
- 候选类型仅“新建线路”，要求两端母线电压等级一致且原网络未直接相连。
- 成本粗略：cost_m = length_km × 0.8（百万/公里）。
- 标签 y = 违规减少 + 装载率改善 + 网损减少 − 成本权重，具体见 generate_dataset.py 顶部常量。
- 这是最小可行实现，用于快速产出可训练数据，后续可按需要扩展 N-1、更多网络/特征/候选类型。

