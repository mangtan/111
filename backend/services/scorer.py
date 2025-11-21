"""
轻量级评分器 - 融合负载时间序列特征与GIS/拓扑特征
"""
import numpy as np
from typing import Dict, List, Any
from config import Config
try:
    from .settings_service import settings  # package import
except Exception:  # pragma: no cover
    from services.settings_service import settings  # module import
try:
    from ..ml.runtime import MLScorer  # when imported as package
except Exception:
    try:
        from ml.runtime import MLScorer  # direct run from backend cwd
    except Exception:
        MLScorer = None  # type: ignore


class CandidateScorer:
    """候选方案评分器"""

    def __init__(self):
        self.weights = Config.SCORER_WEIGHTS
        self.ml = None
        if Config.ENABLE_ML_SCORING and MLScorer is not None:
            try:
                self.ml = MLScorer()
            except Exception:
                self.ml = None

    def calculate_load_growth_score(
        self,
        candidate: Dict[str, Any],
        load_features: Dict[str, Any]
    ) -> float:
        """
        计算负载增长得分

        Args:
            candidate: 候选方案
            load_features: 负载特征

        Returns:
            得分 (0-100)
        """
        # 获取负载增长率
        growth_rate = load_features.get('growth_rate', 0.05)

        # 根据候选类型计算得分
        if candidate['type'] == 'new_substation':
            # 新建变电站能更好地应对负载增长
            capacity = candidate.get('capacity_mva', 100)
            score = min(100, (growth_rate * 1000 + capacity / 2))
        elif candidate['type'] == 'substation_expansion':
            # 扩容也能有效应对负载增长
            additional_capacity = candidate.get('additional_capacity', 50)
            score = min(100, (growth_rate * 800 + additional_capacity / 2))
        elif candidate['type'] == 'new_line':
            # 新建线路对负载增长的作用较小
            capacity = candidate.get('capacity_mva', 50)
            score = min(100, (growth_rate * 600 + capacity / 3))
        else:
            score = 50

        return score

    def calculate_distance_score(
        self,
        candidate: Dict[str, Any],
        gis_data: Dict[str, Any]
    ) -> float:
        """
        计算距离得分（距离越近得分越高）

        Args:
            candidate: 候选方案
            gis_data: GIS数据

        Returns:
            得分 (0-100)
        """
        # 获取距离
        if candidate['type'] == 'new_substation':
            distance = candidate.get('distance_to_existing', 10)
        elif candidate['type'] == 'new_line':
            distance = candidate.get('length_km', 10)
        elif candidate['type'] == 'substation_expansion':
            distance = 0  # 扩容不需要额外距离
        else:
            distance = 5

        # 距离越短得分越高，使用指数衰减
        # 假设理想距离为5km，最大距离为20km
        if distance == 0:
            score = 100
        else:
            score = 100 * np.exp(-distance / 10)

        return score

    def calculate_topology_score(
        self,
        candidate: Dict[str, Any],
        topology: Dict[str, Any]
    ) -> float:
        """
        计算拓扑得分

        Args:
            candidate: 候选方案
            topology: 拓扑信息

        Returns:
            得分 (0-100)
        """
        # 评估对网络可靠性的改善
        if candidate['type'] == 'new_substation':
            # 新变电站增加网络连接性
            score = 85
        elif candidate['type'] == 'new_line':
            # 新线路也能改善连接性
            score = 75
        elif candidate['type'] == 'substation_expansion':
            # 扩容对拓扑结构改善较小
            score = 60
        else:
            score = 50

        # 如果能改善薄弱环节，增加得分
        weak_nodes = topology.get('weak_nodes', [])
        if candidate.get('substation_id') in weak_nodes:
            score += 15

        return min(100, score)

    def calculate_constraint_score(
        self,
        candidate: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> float:
        """
        计算约束满足得分

        Args:
            candidate: 候选方案
            constraints: 约束条件

        Returns:
            得分 (0-100)
        """
        score = 100

        # 检查电压等级约束
        voltage_level = candidate.get('voltage_level', 110)
        valid_levels = settings.get('VOLTAGE_LEVELS', Config.VOLTAGE_LEVELS)
        if voltage_level not in valid_levels:
            score -= 30

        # 检查容量约束（按类型取有效容量）
        if candidate['type'] == 'new_substation':
            cap = float(candidate.get('capacity_mva', 0) or 0)
        elif candidate['type'] == 'substation_expansion':
            cap = float(candidate.get('additional_capacity', 0) or 0)
        else:
            cap = 0.0
        if candidate['type'] in ['new_substation', 'substation_expansion']:
            if cap < 50:
                score -= 20

        # 检查距离约束（如果有）
        if candidate['type'] == 'new_substation':
            distance = float(candidate.get('distance_to_existing', 0) or 0)
            min_d = float(settings.get('MIN_NEW_STATION_DISTANCE_KM', 1.0))
            max_d = float(settings.get('MAX_NEW_STATION_DISTANCE_KM', 25.0))
            if distance < min_d:
                score -= 5
            elif distance > max_d:
                score -= 15

        return max(0, score)

    def calculate_cost_efficiency(
        self,
        candidate: Dict[str, Any]
    ) -> float:
        """
        计算成本效益

        Args:
            candidate: 候选方案

        Returns:
            效益得分 (0-100)
        """
        cost = candidate.get('estimated_cost_m', 50)  # 百万元
        capacity = candidate.get('capacity_mva', 0)

        if candidate['type'] == 'substation_expansion':
            capacity = candidate.get('additional_capacity', 0)

        # 计算单位容量成本
        if capacity > 0:
            unit_cost = cost / capacity
            # 理想单位成本：0.3-0.5 百万/MVA
            if unit_cost < 0.3:
                score = 100
            elif unit_cost < 0.5:
                score = 90
            elif unit_cost < 0.8:
                score = 70
            else:
                score = 50
        else:
            score = 50

        return score

    def score_candidate(
        self,
        candidate: Dict[str, Any],
        load_features: Dict[str, Any],
        gis_data: Dict[str, Any],
        topology: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        对单个候选方案进行综合评分

        Args:
            candidate: 候选方案
            load_features: 负载特征
            gis_data: GIS数据
            topology: 拓扑信息
            constraints: 约束条件

        Returns:
            评分结果
        """
        # 计算各项得分
        load_score = self.calculate_load_growth_score(candidate, load_features)
        distance_score = self.calculate_distance_score(candidate, gis_data)
        topology_score = self.calculate_topology_score(candidate, topology)
        constraint_score = self.calculate_constraint_score(candidate, constraints)
        cost_efficiency = self.calculate_cost_efficiency(candidate)

        # 加权平均（规则分）
        rule_score = (
            load_score * self.weights['load_growth'] +
            distance_score * self.weights['distance'] +
            topology_score * self.weights['topology'] +
            constraint_score * self.weights['constraint']
        )

        # 应用成本效益调整
        total_score = rule_score * (0.5 + cost_efficiency / 200)

        # 机器学习分（可选融合）
        ml_score = None
        if self.ml is not None:
            try:
                ml_score = self.ml.score(candidate, gis_data, topology)
            except Exception:
                ml_score = None

        if ml_score is not None:
            w = float(getattr(Config, 'ML_SCORE_WEIGHT', 0.3))
            total_score = (1.0 - w) * total_score + w * ml_score

        return {
            'candidate': candidate,
            'scores': {
                'load_growth': round(load_score, 2),
                'distance': round(distance_score, 2),
                'topology': round(topology_score, 2),
                'constraint': round(constraint_score, 2),
                'cost_efficiency': round(cost_efficiency, 2),
                **({'ml': round(ml_score, 2)} if ml_score is not None else {}),
                'total': round(total_score, 2)
            }
        }

    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        load_features: Dict[str, Any],
        gis_data: Dict[str, Any],
        topology: Dict[str, Any],
        constraints: Dict[str, Any],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        对所有候选方案进行排名

        Args:
            candidates: 候选方案列表
            load_features: 负载特征
            gis_data: GIS数据
            topology: 拓扑信息
            constraints: 约束条件
            top_k: 返回前k个结果

        Returns:
            排序后的候选方案列表
        """
        if top_k is None:
            top_k = Config.TOP_K_CANDIDATES

        # 对每个候选方案评分
        scored_candidates = []
        for candidate in candidates:
            scored = self.score_candidate(
                candidate,
                load_features,
                gis_data,
                topology,
                constraints
            )
            scored_candidates.append(scored)

        # 按总分排序
        scored_candidates.sort(
            key=lambda x: x['scores']['total'],
            reverse=True
        )

        # 添加排名
        for i, candidate in enumerate(scored_candidates):
            candidate['rank'] = i + 1

        return scored_candidates[:top_k]


# 全局实例
scorer = CandidateScorer()
