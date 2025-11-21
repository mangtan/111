"""
为IEEE 14-bus系统添加地理坐标
"""
import json
import os

# 广州地区坐标 (23.1N, 113.2E)
# 为14个母线分配合理的地理位置
GUANGZHOU_COORDS = [
    {'lat': 23.13, 'lon': 113.26},  # Bus 0 - 天河区
    {'lat': 23.11, 'lon': 113.30},  # Bus 1 - 黄埔区
    {'lat': 23.12, 'lon': 113.24},  # Bus 2 - 越秀区
    {'lat': 23.09, 'lon': 113.28},  # Bus 3 - 海珠区
    {'lat': 23.15, 'lon': 113.22},  # Bus 4 - 白云区
    {'lat': 23.03, 'lon': 113.34},  # Bus 5 - 番禺区
    {'lat': 23.18, 'lon': 113.28},  # Bus 6 - 花都区
    {'lat': 23.08, 'lon': 113.32},  # Bus 7 - 增城区
    {'lat': 23.05, 'lon': 113.20},  # Bus 8 - 南沙区
    {'lat': 23.16, 'lon': 113.35},  # Bus 9 - 从化区
    {'lat': 23.12, 'lon': 113.29},  # Bus 10 - 萝岗区
    {'lat': 23.10, 'lon': 113.25},  # Bus 11 - 荔湾区
    {'lat': 23.14, 'lon': 113.31},  # Bus 12 - 增城新塘
    {'lat': 23.11, 'lon': 113.22},  # Bus 13 - 白云新城
]

# 读取IEEE数据
ieee_file = 'data/gis/ieee14_network.json'

with open(ieee_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 为每个母线添加地理坐标
for i, bus in enumerate(data['buses']):
    bus['location'] = GUANGZHOU_COORDS[i]

# 为母线添加中文名称
bus_names = [
    '220kV天河主变',
    '220kV黄埔主变',
    '220kV越秀主变',
    '110kV海珠变',
    '110kV白云变',
    '110kV番禺变',
    '110kV花都变',
    '110kV增城变',
    '110kV南沙变',
    '110kV从化变',
    '35kV萝岗变',
    '35kV荔湾变',
    '35kV新塘变',
    '35kV白云新城变'
]

for i, bus in enumerate(data['buses']):
    bus['name_zh'] = bus_names[i]
    # 根据电压等级设置容量
    if bus['voltage_kv'] > 200:
        bus['capacity_mva'] = 360
        bus['type_zh'] = '超高压变电站'
    elif bus['voltage_kv'] > 100:
        bus['capacity_mva'] = 126
        bus['type_zh'] = '高压变电站'
    else:
        bus['capacity_mva'] = 50
        bus['type_zh'] = '中压变电站'

# 保存更新后的数据
with open(ieee_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✓ 已为IEEE 14-bus系统添加地理坐标")
print(f"✓ 位置: 广州市区域")
print(f"✓ 母线数: {len(data['buses'])}")
print(f"✓ 线路数: {len(data['lines'])}")
print(f"✓ 负载数: {len(data['loads'])}")
print(f"\n已保存到: {ieee_file}")
