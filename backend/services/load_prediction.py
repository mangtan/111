"""
负载预测服务 - 基于时间序列分析
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os
from config import Config


class LoadPrediction:
    """负载预测系统"""

    def __init__(self):
        self.data_dir = Config.LOAD_DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        self.historical_data = None

    def generate_sample_data(self, days: int = 365) -> pd.DataFrame:
        """
        生成示例负载数据

        Args:
            days: 天数

        Returns:
            负载数据DataFrame
        """
        dates = pd.date_range(
            end=datetime.now(),
            periods=days * 24,
            freq='H'
        )

        # 基础负载（MW）
        base_load = 1000

        # 季节性变化
        seasonal = 200 * np.sin(2 * np.pi * np.arange(len(dates)) / (365 * 24))

        # 日周期变化
        daily = 150 * np.sin(2 * np.pi * (np.arange(len(dates)) % 24) / 24 - np.pi/2)

        # 周周期变化（工作日vs周末）
        weekly = 100 * (np.array([d.weekday() < 5 for d in dates]) - 0.5)

        # 趋势（年增长5%）
        trend = base_load * 0.05 * np.arange(len(dates)) / (365 * 24)

        # 随机噪声
        noise = np.random.normal(0, 30, len(dates))

        # 总负载
        load = base_load + seasonal + daily + weekly + trend + noise
        load = np.maximum(load, 0)  # 确保非负

        df = pd.DataFrame({
            'timestamp': dates,
            'load_mw': load,
            'temperature': 20 + 10 * np.sin(2 * np.pi * np.arange(len(dates)) / (365 * 24)) + np.random.normal(0, 3, len(dates)),
            'is_holiday': np.random.choice([0, 1], len(dates), p=[0.95, 0.05])
        })

        return df

    def load_historical_data(self) -> pd.DataFrame:
        """加载历史数据"""
        # ============================================
        # 切换到真实数据：广东省真实特征负载数据
        # ============================================
        real_data_file = os.path.join(self.data_dir, 'realistic_guangdong_load.csv')

        if os.path.exists(real_data_file):
            print(f"✓ 加载真实数据: {real_data_file}")
            df = pd.read_csv(real_data_file, parse_dates=['timestamp'])
            print(f"✓ 广东省负载数据: {len(df)}条记录, 平均负载 {df['load_mw'].mean():.2f} MW")
        else:
            # 如果真实数据不存在，回退到模拟数据
            print("⚠ 未找到真实数据，使用模拟数据")
            data_file = os.path.join(self.data_dir, 'historical_load.csv')

            if os.path.exists(data_file):
                df = pd.read_csv(data_file, parse_dates=['timestamp'])
            else:
                # 生成示例数据
                df = self.generate_sample_data(days=730)  # 2年数据
                df.to_csv(data_file, index=False)

        self.historical_data = df
        return df

    def extract_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        提取负载特征

        Args:
            df: 负载数据

        Returns:
            特征字典
        """
        features = {
            'avg_load': float(df['load_mw'].mean()),
            'max_load': float(df['load_mw'].max()),
            'min_load': float(df['load_mw'].min()),
            'std_load': float(df['load_mw'].std()),
            'peak_hour': int(df.groupby(df['timestamp'].dt.hour)['load_mw'].mean().idxmax()),
            'valley_hour': int(df.groupby(df['timestamp'].dt.hour)['load_mw'].mean().idxmin()),
            'weekday_avg': float(df[df['timestamp'].dt.weekday < 5]['load_mw'].mean()),
            'weekend_avg': float(df[df['timestamp'].dt.weekday >= 5]['load_mw'].mean()),
            'growth_rate': self._calculate_growth_rate(df),
            'volatility': float(df['load_mw'].pct_change().std()),
        }

        return features

    def _calculate_growth_rate(self, df: pd.DataFrame) -> float:
        """计算年增长率"""
        if len(df) < 365 * 24:
            return 0.05  # 默认5%

        # 比较最近30天和一年前的30天
        recent = df.tail(30 * 24)['load_mw'].mean()
        year_ago = df.iloc[-(365+30)*24:-(365)*24]['load_mw'].mean()

        growth_rate = (recent - year_ago) / year_ago
        return float(growth_rate)

    def predict_future_load(
        self,
        horizon_days: int = 365,
        method: str = 'simple'
    ) -> pd.DataFrame:
        """
        预测未来负载

        Args:
            horizon_days: 预测天数
            method: 预测方法

        Returns:
            预测结果DataFrame
        """
        if self.historical_data is None:
            self.load_historical_data()

        df = self.historical_data.copy()

        # 提取特征
        features = self.extract_features(df)

        # 简单预测：基于历史趋势
        last_date = df['timestamp'].max()
        future_dates = pd.date_range(
            start=last_date + timedelta(hours=1),
            periods=horizon_days * 24,
            freq='H'
        )

        # 基础负载（使用最近的平均值）
        base_load = df.tail(30 * 24)['load_mw'].mean()

        # 应用增长率
        growth_rate = features['growth_rate']
        hours = np.arange(len(future_dates))
        trend = base_load * growth_rate * hours / (365 * 24)

        # 季节性模式（年周期，振幅约为基础负载的8%）
        seasonal = base_load * 0.08 * np.sin(2 * np.pi * hours / (365 * 24))

        # 日周期（24小时周期，振幅约为基础负载的15%）
        # 使用-np.pi/2使得峰值出现在下午3点左右
        daily = base_load * 0.15 * np.sin(2 * np.pi * (hours % 24) / 24 - np.pi/2)

        # 周周期（工作日高于周末，振幅约5%）
        weekly = base_load * 0.05 * (np.array([d.weekday() < 5 for d in future_dates]).astype(float) - 0.5)

        # 预测负载
        predicted_load = base_load + trend + seasonal + daily + weekly

        prediction_df = pd.DataFrame({
            'timestamp': future_dates,
            'predicted_load_mw': predicted_load,
            'confidence_lower': predicted_load * 0.9,
            'confidence_upper': predicted_load * 1.1
        })

        return prediction_df

    def identify_overload_areas(
        self,
        prediction: pd.DataFrame,
        capacity_threshold: float = 0.9
    ) -> List[Dict[str, Any]]:
        """
        识别可能过载的区域

        Args:
            prediction: 预测数据
            capacity_threshold: 容量阈值

        Returns:
            过载区域列表
        """
        # 基于GIS网络位置动态生成过载区域，确保与网络在同一城市范围
        try:
            # 延迟导入避免循环依赖
            from services.gis_service import gis_service  # type: ignore
            network = gis_service.get_network_summary()
            substations = [s for s in (network.get('substations') or []) if s.get('location')]
        except Exception:
            substations = []

        areas = []
        if substations:
            # 取最多5个站点，在其附近少量扰动生成区域点
            import random
            for i, sub in enumerate(substations[:5]):
                loc = sub['location']
                lat = float(loc['lat']) + float(np.random.uniform(-0.02, 0.02))
                lon = float(loc['lon']) + float(np.random.uniform(-0.02, 0.02))
                # 粗略容量：按电压等级设上下限
                v = sub.get('voltage_kv') or sub.get('voltage_level') or 110
                if float(v) >= 220:
                    cap = float(np.random.uniform(1200, 1800))
                elif float(v) >= 110:
                    cap = float(np.random.uniform(800, 1500))
                else:
                    cap = float(np.random.uniform(600, 1000))
                areas.append({
                    'id': f'area_{i+1}',
                    'name': sub.get('name_zh') or sub.get('name') or f'区域{i+1}',
                    'capacity': cap,
                    'lat': lat,
                    'lon': lon
                })
        else:
            # 回退：使用广州附近坐标（与示例拓扑一致）
            areas = [
                {'id': 'area_1', 'name': '城东区', 'capacity': 1200, 'lat': 23.13, 'lon': 113.28},
                {'id': 'area_2', 'name': '城西区', 'capacity': 1000, 'lat': 23.12, 'lon': 113.24},
                {'id': 'area_3', 'name': '城南区', 'capacity': 1500, 'lat': 23.10, 'lon': 113.26},
                {'id': 'area_4', 'name': '城北区', 'capacity': 1100, 'lat': 23.16, 'lon': 113.27},
                {'id': 'area_5', 'name': '开发区', 'capacity': 800, 'lat': 23.14, 'lon': 113.30},
            ]

        max_predicted = prediction['predicted_load_mw'].max()

        overload_areas = []
        for area in areas:
            # 为每个区域分配负载（简化：按比例分配）
            area_load = max_predicted * np.random.uniform(0.15, 0.35)

            if area_load / area['capacity'] > capacity_threshold:
                overload_areas.append({
                    **area,
                    'predicted_load': float(area_load),
                    'loading_rate': float(area_load / area['capacity']),
                    'overload_amount': float(area_load - area['capacity'] * capacity_threshold),
                    'priority': 'high' if area_load / area['capacity'] > 1.0 else 'medium'
                })

        return sorted(overload_areas, key=lambda x: x['loading_rate'], reverse=True)

    def get_load_summary(self) -> Dict[str, Any]:
        """获取负载摘要"""
        if self.historical_data is None:
            self.load_historical_data()

        features = self.extract_features(self.historical_data)
        prediction = self.predict_future_load(horizon_days=365)
        overload_areas = self.identify_overload_areas(prediction)

        return {
            'current_features': features,
            'future_prediction': {
                'max_load': float(prediction['predicted_load_mw'].max()),
                'avg_load': float(prediction['predicted_load_mw'].mean()),
                'growth_rate': features['growth_rate']
            },
            'overload_areas': overload_areas,
            'prediction_horizon_days': 365
        }


# 全局实例
load_prediction = LoadPrediction()
