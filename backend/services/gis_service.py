"""
GIS数据处理和拓扑分析服务
"""
import json
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import os
from config import Config


class GISService:
    """GIS数据处理服务"""

    def __init__(self):
        self.gis_dir = Config.GIS_DIR
        os.makedirs(self.gis_dir, exist_ok=True)
        self.network_data = None
        self.load_network_data()

    def load_network_data(self):
        """加载电网拓扑数据"""
        # ============================================
        # 切换到真实数据：IEEE 14-bus标准测试系统
        # ============================================
        ieee_data_file = os.path.join(self.gis_dir, 'ieee14_network.json')

        if os.path.exists(ieee_data_file):
            print(f"✓ 加载真实拓扑: IEEE 14-bus标准测试系统")
            with open(ieee_data_file, 'r', encoding='utf-8') as f:
                self.network_data = json.load(f)
            print(f"✓ 母线数: {len(self.network_data['buses'])}, 线路数: {len(self.network_data['lines'])}")
        else:
            # 如果IEEE数据不存在，回退到原始数据
            print("⚠ 未找到IEEE数据，使用模拟拓扑")
            data_file = os.path.join(self.gis_dir, 'network_topology.json')

            if os.path.exists(data_file):
                with open(data_file, 'r', encoding='utf-8') as f:
                    self.network_data = json.load(f)
            else:
                # 创建示例数据
                self.network_data = self._generate_sample_network()
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(self.network_data, f, ensure_ascii=False, indent=2)

    def _generate_sample_network(self) -> Dict[str, Any]:
        """生成示例电网拓扑数据"""
        # 变电站
        substations = [
            {
                'id': 'sub_1',
                'name': '220kV东城变',
                'voltage_level': 220,
                'capacity_mva': 360,
                'location': {'lat': 31.23, 'lon': 121.48},
                'type': 'transmission',
                'status': 'operating'
            },
            {
                'id': 'sub_2',
                'name': '220kV西城变',
                'voltage_level': 220,
                'capacity_mva': 360,
                'location': {'lat': 31.22, 'lon': 121.45},
                'type': 'transmission',
                'status': 'operating'
            },
            {
                'id': 'sub_3',
                'name': '110kV南区变',
                'voltage_level': 110,
                'capacity_mva': 100,
                'location': {'lat': 31.20, 'lon': 121.47},
                'type': 'distribution',
                'status': 'operating'
            },
            {
                'id': 'sub_4',
                'name': '110kV北区变',
                'voltage_level': 110,
                'capacity_mva': 126,
                'location': {'lat': 31.25, 'lon': 121.46},
                'type': 'distribution',
                'status': 'operating'
            },
            {
                'id': 'sub_5',
                'name': '110kV开发区变',
                'voltage_level': 110,
                'capacity_mva': 63,
                'location': {'lat': 31.21, 'lon': 121.50},
                'type': 'distribution',
                'status': 'operating'
            },
        ]

        # 线路
        lines = [
            {
                'id': 'line_1',
                'name': '东西220kV线路',
                'from_bus': 'sub_1',
                'to_bus': 'sub_2',
                'voltage_level': 220,
                'capacity_mva': 300,
                'length_km': 15.5,
                'status': 'operating'
            },
            {
                'id': 'line_2',
                'name': '东-南110kV线路',
                'from_bus': 'sub_1',
                'to_bus': 'sub_3',
                'voltage_level': 110,
                'capacity_mva': 100,
                'length_km': 8.2,
                'status': 'operating'
            },
            {
                'id': 'line_3',
                'name': '西-北110kV线路',
                'from_bus': 'sub_2',
                'to_bus': 'sub_4',
                'voltage_level': 110,
                'capacity_mva': 100,
                'length_km': 7.8,
                'status': 'operating'
            },
            {
                'id': 'line_4',
                'name': '东-开发区110kV线路',
                'from_bus': 'sub_1',
                'to_bus': 'sub_5',
                'voltage_level': 110,
                'capacity_mva': 63,
                'length_km': 12.3,
                'status': 'operating'
            },
            {
                'id': 'line_5',
                'name': '南-开发区110kV线路',
                'from_bus': 'sub_3',
                'to_bus': 'sub_5',
                'voltage_level': 110,
                'capacity_mva': 63,
                'length_km': 6.5,
                'status': 'operating'
            },
        ]

        # 负载点
        loads = [
            {'id': 'load_1', 'bus': 'sub_3', 'load_mw': 45, 'type': 'industrial'},
            {'id': 'load_2', 'bus': 'sub_3', 'load_mw': 25, 'type': 'residential'},
            {'id': 'load_3', 'bus': 'sub_4', 'load_mw': 60, 'type': 'commercial'},
            {'id': 'load_4', 'bus': 'sub_4', 'load_mw': 35, 'type': 'residential'},
            {'id': 'load_5', 'bus': 'sub_5', 'load_mw': 38, 'type': 'industrial'},
        ]

        return {
            'substations': substations,
            'lines': lines,
            'loads': loads
        }

    def calculate_distance(
        self,
        point1: Dict[str, float],
        point2: Dict[str, float]
    ) -> float:
        """
        计算两点之间的距离（简化的球面距离）

        Args:
            point1: {'lat': x, 'lon': y}
            point2: {'lat': x, 'lon': y}

        Returns:
            距离（km）
        """
        lat1, lon1 = point1['lat'], point1['lon']
        lat2, lon2 = point2['lat'], point2['lon']

        # 简化计算（实际应使用Haversine公式）
        R = 6371  # 地球半径（km）
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)

        a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * \
            np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

        distance = R * c
        return distance

    def find_nearest_substation(
        self,
        location: Dict[str, float],
        voltage_level: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        查找最近的变电站

        Args:
            location: 位置
            voltage_level: 电压等级筛选

        Returns:
            最近的变电站信息
        """
        # 兼容IEEE数据和原始数据
        substations = self.network_data.get('buses') or self.network_data.get('substations', [])

        if voltage_level:
            substations = [s for s in substations if s.get('voltage_level') == voltage_level or s.get('voltage_kv') == voltage_level]

        min_distance = float('inf')
        nearest = None

        for sub in substations:
            if 'location' not in sub:
                continue
            dist = self.calculate_distance(location, sub['location'])
            if dist < min_distance:
                min_distance = dist
                nearest = sub.copy()
                nearest['distance_km'] = dist

        return nearest

    def analyze_topology(self) -> Dict[str, Any]:
        """
        分析网络拓扑

        Returns:
            拓扑分析结果
        """
        # 兼容IEEE数据（使用buses）和原始数据（使用substations）
        substations = self.network_data.get('buses') or self.network_data.get('substations', [])
        lines = self.network_data['lines']

        # 构建邻接表
        adjacency = {sub['id']: [] for sub in substations}
        for line in lines:
            # IEEE数据使用数字索引，需要转换为bus_id
            from_bus_id = f"bus_{line['from_bus']}" if isinstance(line['from_bus'], int) else line['from_bus']
            to_bus_id = f"bus_{line['to_bus']}" if isinstance(line['to_bus'], int) else line['to_bus']

            if from_bus_id in adjacency:
                adjacency[from_bus_id].append(to_bus_id)
            if to_bus_id in adjacency:
                adjacency[to_bus_id].append(from_bus_id)

        # 计算节点度数
        node_degrees = {node: len(neighbors) for node, neighbors in adjacency.items()}

        # 识别关键节点（度数高的节点）
        critical_nodes = sorted(
            node_degrees.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # 识别薄弱环节（单连接节点）
        weak_nodes = [node for node, degree in node_degrees.items() if degree <= 1]

        return {
            'total_substations': len(substations),
            'total_lines': len(lines),
            'adjacency': adjacency,
            'node_degrees': node_degrees,
            'critical_nodes': [
                {'id': node, 'degree': degree}
                for node, degree in critical_nodes
            ],
            'weak_nodes': weak_nodes,
            'avg_degree': sum(node_degrees.values()) / len(node_degrees) if node_degrees else 0
        }

    def get_expansion_candidates(
        self,
        overload_areas: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成扩展候选方案

        Args:
            overload_areas: 过载区域列表

        Returns:
            候选方案列表
        """
        candidates = []

        # 构建邻接：便于识别已直连与未直连
        subs_all = self.network_data.get('buses') or self.network_data.get('substations', [])
        id_set = set(s['id'] for s in subs_all)
        adjacency = {sid: set() for sid in id_set}
        for ln in self.network_data.get('lines', []):
            fb = f"bus_{ln['from_bus']}" if isinstance(ln['from_bus'], int) else ln['from_bus']
            tb = f"bus_{ln['to_bus']}" if isinstance(ln['to_bus'], int) else ln['to_bus']
            if fb in adjacency and tb in adjacency:
                adjacency[fb].add(tb)
                adjacency[tb].add(fb)

        # 便捷索引
        sub_by_id = {s['id']: s for s in subs_all}

        for area in overload_areas:
            # 新建变电站候选（保留）
            nearest_sub = self.find_nearest_substation({'lat': area['lat'], 'lon': area['lon']})

            candidates.append({
                'type': 'new_substation',
                'area_id': area['id'],
                'area_name': area['name'],
                'location': {'lat': area['lat'], 'lon': area['lon']},
                'voltage_level': 110,
                'capacity_mva': max(100, area['overload_amount'] * 1.3),
                'nearest_existing': nearest_sub['id'],
                'distance_to_existing': nearest_sub['distance_km'],
                'estimated_cost_m': nearest_sub['distance_km'] * 0.8 + 50
            })

            # 变电站扩容候选（保留）
            if nearest_sub['distance_km'] < 5:
                candidates.append({
                    'type': 'substation_expansion',
                    'area_id': area['id'],
                    'area_name': area['name'],
                    'substation_id': nearest_sub['id'],
                    'substation_name': nearest_sub.get('name') or nearest_sub.get('name_zh') or nearest_sub['id'],
                    'current_capacity': nearest_sub.get('capacity_mva'),
                    'additional_capacity': area['overload_amount'] * 1.3,
                    'estimated_cost_m': 30
                })

            # 新建线路候选：两类——reinforcement(并联加固) 与 interconnection(新建联络)
            from_id = nearest_sub['id']
            from_loc = nearest_sub['location']
            # reinforcement：在已有直连对端中选一个（取最近的一个已有直连）
            try:
                neighbors = list(adjacency.get(from_id, []))
                if neighbors:
                    # 选与 from 最近的一个已直连站作为加固对象
                    best_nb = None; best_d = 1e18
                    for nb in neighbors:
                        sub_nb = sub_by_id.get(nb)
                        if not sub_nb or not sub_nb.get('location'): continue
                        d = self.calculate_distance(from_loc, sub_nb['location'])
                        if d < best_d:
                            best_d = d; best_nb = sub_nb
                    if best_nb is not None:
                        candidates.append({
                            'type': 'new_line',
                            'subtype': 'reinforcement',
                            'area_id': area['id'],
                            'area_name': area['name'],
                            'from_substation_id': from_id,
                            'to_substation_id': best_nb['id'],
                            'from_location': from_loc,
                            'to_location': best_nb['location'],
                            'length_km': best_d,
                            'voltage_level': 110,
                            'capacity_mva': area['overload_amount'] * 1.0,
                            'estimated_cost_m': best_d * 0.8
                        })
            except Exception:
                pass

            # interconnection：选择最近的“尚未直连”的其它站
            try:
                best_other = None; best_d2 = 1e18
                for sid, sub in sub_by_id.items():
                    if sid == from_id: continue
                    if sid in adjacency.get(from_id, set()):
                        continue  # 已直连，跳过
                    loc2 = sub.get('location');
                    if not loc2: continue
                    d = self.calculate_distance(from_loc, loc2)
                    if d < best_d2:
                        best_d2 = d; best_other = sub
                if best_other is not None:
                    candidates.append({
                        'type': 'new_line',
                        'subtype': 'interconnection',
                        'area_id': area['id'],
                        'area_name': area['name'],
                        'from_substation_id': from_id,
                        'to_substation_id': best_other['id'],
                        'from_location': from_loc,
                        'to_location': best_other['location'],
                        'length_km': best_d2,
                        'voltage_level': 110,
                        'capacity_mva': area['overload_amount'] * 1.2,
                        'estimated_cost_m': best_d2 * 0.8
                    })
            except Exception:
                pass

        return candidates

    def get_network_summary(self) -> Dict[str, Any]:
        """获取网络摘要"""
        topology = self.analyze_topology()

        # 兼容IEEE数据和原始数据结构
        buses_or_substations = self.network_data.get('buses') or self.network_data.get('substations', [])

        return {
            'buses': buses_or_substations,  # 统一使用buses字段
            'substations': buses_or_substations,  # 保持向后兼容
            'lines': self.network_data['lines'],
            'loads': self.network_data.get('loads', []),
            'generators': self.network_data.get('generators', []),  # IEEE数据包含generators
            'topology': topology
        }

    # ---------------- 区域/网格（GeoJSON） ----------------
    def get_zones_geojson(self) -> Dict[str, Any]:
        """返回现有区域划分（GeoJSON）。如果不存在则生成默认网格并保存。"""
        import json as _json
        zones_path = os.path.join(self.gis_dir, 'zones.geojson')

        # 如有缓存，直接读取
        if os.path.exists(zones_path):
            try:
                with open(zones_path, 'r', encoding='utf-8') as f:
                    return _json.load(f)
            except Exception:
                pass

        # 动态生成规则网格（6x10）并保存
        subs = self.network_data.get('buses') or self.network_data.get('substations', [])
        pts = [s.get('location') for s in subs if s.get('location')]
        if not pts:
            # 兜底：广州附近
            pts = [{'lat': 23.10, 'lon': 113.23}, {'lat': 23.17, 'lon': 113.31}]

        min_lat = min(p['lat'] for p in pts)
        max_lat = max(p['lat'] for p in pts)
        min_lon = min(p['lon'] for p in pts)
        max_lon = max(p['lon'] for p in pts)
        # 加边距
        dlat = (max_lat - min_lat) * 0.15 or 0.02
        dlon = (max_lon - min_lon) * 0.15 or 0.02
        min_lat -= dlat; max_lat += dlat; min_lon -= dlon; max_lon += dlon

        rows, cols = 6, 10
        feats = []
        id_counter = 1
        for i in range(rows):
            for j in range(cols):
                lat0 = min_lat + (max_lat - min_lat) * (i    ) / rows
                lat1 = min_lat + (max_lat - min_lat) * (i + 1) / rows
                lon0 = min_lon + (max_lon - min_lon) * (j    ) / cols
                lon1 = min_lon + (max_lon - min_lon) * (j + 1) / cols
                poly = [
                    [lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]
                ]
                feats.append({
                    'type': 'Feature',
                    'properties': {
                        'zone_id': f'zone_{id_counter}',
                        'name': f'区域 {i+1}-{j+1}',
                        'row': i+1,
                        'col': j+1,
                        'baseline_load_mw': None,
                        'status': '未设置'
                    },
                    'geometry': {'type': 'Polygon', 'coordinates': [poly]}
                })
                id_counter += 1

        geojson = {'type': 'FeatureCollection', 'features': feats}
        try:
            with open(zones_path, 'w', encoding='utf-8') as f:
                _json.dump(geojson, f, ensure_ascii=False)
        except Exception:
            pass
        return geojson

    def generate_zones_grid(self, rows: int = 6, cols: int = 10) -> Dict[str, Any]:
        """按当前网络包围盒生成规则网格，保存并返回GeoJSON。"""
        import json as _json
        zones_path = os.path.join(self.gis_dir, 'zones.geojson')

        subs = self.network_data.get('buses') or self.network_data.get('substations', [])
        pts = [s.get('location') for s in subs if s.get('location')]
        if not pts:
            pts = [{'lat': 23.10, 'lon': 113.23}, {'lat': 23.17, 'lon': 113.31}]

        min_lat = min(p['lat'] for p in pts); max_lat = max(p['lat'] for p in pts)
        min_lon = min(p['lon'] for p in pts); max_lon = max(p['lon'] for p in pts)
        dlat = (max_lat - min_lat) * 0.15 or 0.02
        dlon = (max_lon - min_lon) * 0.15 or 0.02
        min_lat -= dlat; max_lat += dlat; min_lon -= dlon; max_lon += dlon

        rows = max(1, int(rows)); cols = max(1, int(cols))
        feats = []
        id_counter = 1
        for i in range(rows):
            for j in range(cols):
                lat0 = min_lat + (max_lat - min_lat) * i / rows
                lat1 = min_lat + (max_lat - min_lat) * (i + 1) / rows
                lon0 = min_lon + (max_lon - min_lon) * j / cols
                lon1 = min_lon + (max_lon - min_lon) * (j + 1) / cols
                poly = [[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]
                feats.append({
                    'type': 'Feature',
                    'properties': {
                        'zone_id': f'zone_{id_counter}',
                        'name': f'区域 {i+1}-{j+1}',
                        'row': i+1,
                        'col': j+1,
                        'baseline_load_mw': None,
                        'status': '未设置'
                    },
                    'geometry': {'type': 'Polygon', 'coordinates': [poly]}
                })
                id_counter += 1

        geojson = {'type': 'FeatureCollection', 'features': feats}
        os.makedirs(self.gis_dir, exist_ok=True)
        with open(zones_path, 'w', encoding='utf-8') as f:
            _json.dump(geojson, f, ensure_ascii=False)
        return geojson

    def clear_zones(self) -> bool:
        """删除已保存的zones.geojson"""
        zones_path = os.path.join(self.gis_dir, 'zones.geojson')
        if os.path.exists(zones_path):
            os.remove(zones_path)
            return True
        return False


# 全局实例
gis_service = GISService()
