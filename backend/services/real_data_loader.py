"""
真实数据集成工具
用于下载和加载开源电力系统数据
"""
import pandas as pd
import pandapower as pp
import pandapower.networks as pn
import requests
from datetime import datetime, timedelta
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


class RealDataLoader:
    """真实数据加载器"""

    def __init__(self):
        self.data_dir = Config.DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

    # ========================================
    # 1. IEEE标准测试系统（来自pandapower）
    # ========================================

    def load_ieee_case14(self):
        """
        加载IEEE 14-bus标准测试系统
        这是最经典的电力系统测试案例
        """
        net = pn.case14()
        return net

    def load_ieee_case30(self):
        """加载IEEE 30-bus系统"""
        net = pn.case30()
        return net

    def load_ieee_case118(self):
        """加载IEEE 118-bus系统（更复杂）"""
        net = pn.case118()
        return net

    def get_ieee_network_info(self, case='case14'):
        """
        获取IEEE标准系统信息

        Args:
            case: 'case14', 'case30', 'case118'

        Returns:
            dict: 包含母线、线路、负载信息
        """
        if case == 'case14':
            net = pn.case14()
        elif case == 'case30':
            net = pn.case30()
        elif case == 'case118':
            net = pn.case118()
        else:
            raise ValueError(f"Unknown case: {case}")

        # 运行潮流
        pp.runpp(net)

        # 提取信息
        network_data = {
            'buses': [],
            'lines': [],
            'loads': [],
            'generators': []
        }

        # 母线信息
        for idx, bus in net.bus.iterrows():
            network_data['buses'].append({
                'id': f'bus_{idx}',
                'name': bus.get('name', f'Bus {idx}'),
                'voltage_kv': float(bus['vn_kv']),
                'type': bus.get('type', 'b'),
                'vm_pu': float(net.res_bus.at[idx, 'vm_pu']) if idx in net.res_bus.index else 1.0
            })

        # 线路信息
        for idx, line in net.line.iterrows():
            network_data['lines'].append({
                'id': f'line_{idx}',
                'name': line.get('name', f'Line {idx}'),
                'from_bus': int(line['from_bus']),
                'to_bus': int(line['to_bus']),
                'length_km': float(line['length_km']),
                'loading_percent': float(net.res_line.at[idx, 'loading_percent']) if idx in net.res_line.index else 0
            })

        # 负载信息
        for idx, load in net.load.iterrows():
            network_data['loads'].append({
                'id': f'load_{idx}',
                'bus': int(load['bus']),
                'p_mw': float(load['p_mw']),
                'q_mvar': float(load['q_mvar'])
            })

        # 发电机信息
        for idx, gen in net.gen.iterrows():
            network_data['generators'].append({
                'id': f'gen_{idx}',
                'bus': int(gen['bus']),
                'p_mw': float(gen['p_mw']),
                'vm_pu': float(gen['vm_pu'])
            })

        return network_data

    # ========================================
    # 2. Open Power System Data (欧洲真实数据)
    # ========================================

    def download_opsd_load_data(self, country='DE', years=2):
        """
        下载OPSD真实负载数据

        Args:
            country: 国家代码 (DE=德国, FR=法国, GB=英国等)
            years: 下载几年的数据

        Returns:
            DataFrame: 真实负载数据
        """
        print(f"下载{country}国家的负载数据...")

        # OPSD时间序列数据API
        url = f"https://data.open-power-system-data.org/time_series/2020-10-06/time_series_60min_singleindex.csv"

        try:
            # 下载数据
            print("正在下载数据（约200MB），请稍候...")
            df = pd.read_csv(url, parse_dates=['utc_timestamp'])

            # 筛选指定国家的负载数据
            load_column = f'{country}_load_actual_entsoe_transparency'

            if load_column in df.columns:
                load_data = df[['utc_timestamp', load_column]].copy()
                load_data.columns = ['timestamp', 'load_mw']
                load_data = load_data.dropna()

                # 只保留最近N年数据
                cutoff_date = datetime.now() - timedelta(days=365 * years)
                load_data = load_data[load_data['timestamp'] >= cutoff_date]

                # 保存到本地
                output_file = os.path.join(Config.LOAD_DATA_DIR, f'opsd_{country}_load.csv')
                load_data.to_csv(output_file, index=False)
                print(f"✓ 数据已保存到: {output_file}")
                print(f"✓ 共{len(load_data)}条记录")

                return load_data
            else:
                print(f"✗ 没有找到{country}的数据，可用列: {df.columns.tolist()[:10]}")
                return None

        except Exception as e:
            print(f"✗ 下载失败: {e}")
            print("提示: 可以手动从 https://data.open-power-system-data.org/ 下载数据")
            return None

    def load_opsd_sample_data(self):
        """
        加载OPSD示例数据（如果已下载）

        Returns:
            DataFrame: 负载数据
        """
        files = [
            'opsd_DE_load.csv',
            'opsd_FR_load.csv',
            'opsd_GB_load.csv'
        ]

        for file in files:
            filepath = os.path.join(Config.LOAD_DATA_DIR, file)
            if os.path.exists(filepath):
                print(f"✓ 找到数据文件: {file}")
                df = pd.read_csv(filepath, parse_dates=['timestamp'])
                return df

        print("✗ 未找到OPSD数据，请先运行 download_opsd_load_data()")
        return None

    # ========================================
    # 3. 中国电网模拟数据（基于真实参数）
    # ========================================

    def generate_realistic_china_load(self, province='guangdong'):
        """
        生成基于中国真实特征的负载数据

        Args:
            province: 省份 (guangdong, beijing, shanghai等)

        Returns:
            DataFrame: 模拟的真实负载数据
        """
        import numpy as np

        # 不同省份的真实负载特征（基于公开统计数据）
        province_params = {
            'guangdong': {
                'base_load': 6000,  # MW (广东电网约60GW)
                'growth_rate': 0.06,  # 6%年增长
                'summer_peak': 1.4,   # 夏季峰值倍数
                'winter_peak': 1.1    # 冬季峰值倍数
            },
            'beijing': {
                'base_load': 2000,
                'growth_rate': 0.04,
                'summer_peak': 1.3,
                'winter_peak': 1.5  # 北京冬季负载更高
            },
            'shanghai': {
                'base_load': 3000,
                'growth_rate': 0.05,
                'summer_peak': 1.4,
                'winter_peak': 1.2
            }
        }

        params = province_params.get(province, province_params['guangdong'])

        # 生成2年数据
        dates = pd.date_range(
            end=datetime.now(),
            periods=365 * 2 * 24,
            freq='h'
        )

        # 基础负载
        base = params['base_load']

        # 季节性（考虑中国夏季和冬季双峰）
        day_of_year = dates.dayofyear
        seasonal = np.where(
            (day_of_year >= 150) & (day_of_year <= 240),  # 夏季
            base * (params['summer_peak'] - 1) * np.sin((day_of_year - 150) * np.pi / 90),
            np.where(
                (day_of_year <= 60) | (day_of_year >= 330),  # 冬季
                base * (params['winter_peak'] - 1) * 0.5,
                0
            )
        )

        # 日周期（中国特色：午间小高峰 + 晚间大高峰）
        hour = dates.hour
        daily = base * 0.3 * (
            0.5 * np.sin((hour - 6) * np.pi / 12) +  # 白天波动
            0.8 * np.sin((hour - 12) * np.pi / 6)    # 晚间高峰
        )

        # 工作日vs周末
        weekly = base * 0.15 * (dates.weekday < 5).astype(float)

        # 增长趋势
        trend = base * params['growth_rate'] * np.arange(len(dates)) / (365 * 24)

        # 随机噪声
        noise = np.random.normal(0, base * 0.03, len(dates))

        # 总负载
        load = base + seasonal + daily + weekly + trend + noise
        load = np.maximum(load, base * 0.5)  # 最低负载限制

        df = pd.DataFrame({
            'timestamp': dates,
            'load_mw': load,
            'temperature': 20 + 15 * np.sin(2 * np.pi * dates.dayofyear / 365) + np.random.normal(0, 5, len(dates)),
            'is_holiday': np.random.choice([0, 1], len(dates), p=[0.96, 0.04])
        })

        # 保存
        output_file = os.path.join(Config.LOAD_DATA_DIR, f'realistic_{province}_load.csv')
        df.to_csv(output_file, index=False)
        print(f"✓ 生成{province}省真实特征负载数据: {output_file}")
        print(f"✓ 基础负载: {params['base_load']} MW, 增长率: {params['growth_rate']*100}%")

        return df

    # ========================================
    # 4. 数据统计和验证
    # ========================================

    def compare_datasets(self):
        """比较不同数据集的特征"""
        print("\n" + "="*60)
        print("可用数据集对比")
        print("="*60)

        datasets = {
            'IEEE 14-bus': 'IEEE标准测试系统 - 14节点',
            'IEEE 30-bus': 'IEEE标准测试系统 - 30节点',
            'IEEE 118-bus': 'IEEE标准测试系统 - 118节点',
            'OPSD': 'Open Power System Data - 欧洲真实数据',
            'Realistic China': '中国真实特征模拟数据'
        }

        for name, desc in datasets.items():
            print(f"\n{name}:")
            print(f"  描述: {desc}")

            if 'IEEE' in name:
                case = name.split()[1].lower()
                try:
                    net = getattr(pn, case)()
                    print(f"  ✓ 母线数: {len(net.bus)}")
                    print(f"  ✓ 线路数: {len(net.line)}")
                    print(f"  ✓ 负载数: {len(net.load)}")
                    print(f"  ✓ 总负载: {net.load['p_mw'].sum():.2f} MW")
                except Exception as e:
                    print(f"  ✗ 加载失败: {e}")

        print("\n" + "="*60)


# 使用示例
if __name__ == '__main__':
    loader = RealDataLoader()

    # 1. 加载IEEE标准系统
    print("\n1. 加载IEEE 14-bus系统...")
    net = loader.load_ieee_case14()
    info = loader.get_ieee_network_info('case14')
    print(f"✓ 成功加载，包含{len(info['buses'])}个母线")

    # 2. 生成中国真实特征数据
    print("\n2. 生成广东省真实特征负载数据...")
    df = loader.generate_realistic_china_load('guangdong')
    print(f"✓ 生成{len(df)}条数据")

    # 3. 对比所有数据集
    loader.compare_datasets()
