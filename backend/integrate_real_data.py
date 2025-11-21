"""
数据集成脚本 - 将真实数据集成到系统中
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.real_data_loader import RealDataLoader
from services.gis_service import gis_service
from services.load_prediction import load_prediction
import json


def integrate_ieee_network():
    """集成IEEE标准测试系统"""
    print("\n" + "="*60)
    print("集成IEEE 14-bus标准测试系统")
    print("="*60)

    loader = RealDataLoader()

    # 加载IEEE 14-bus系统
    network_info = loader.get_ieee_network_info('case14')

    print(f"\n✓ 加载成功!")
    print(f"  - 母线数: {len(network_info['buses'])}")
    print(f"  - 线路数: {len(network_info['lines'])}")
    print(f"  - 负载数: {len(network_info['loads'])}")
    print(f"  - 发电机数: {len(network_info['generators'])}")

    total_load = sum([load['p_mw'] for load in network_info['loads']])
    print(f"  - 总负载: {total_load:.2f} MW")

    # 保存到GIS数据目录
    output_file = os.path.join('data/gis', 'ieee14_network.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(network_info, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 已保存到: {output_file}")

    return network_info


def integrate_realistic_china_data():
    """集成中国真实特征数据"""
    print("\n" + "="*60)
    print("集成中国真实特征负载数据")
    print("="*60)

    loader = RealDataLoader()

    # 生成广东、北京、上海数据
    provinces = ['guangdong', 'beijing', 'shanghai']

    for province in provinces:
        print(f"\n生成{province}省数据...")
        df = loader.generate_realistic_china_load(province)
        print(f"✓ {province}: {len(df)}条记录, 平均负载: {df['load_mw'].mean():.2f} MW")

    print("\n✓ 所有数据已生成!")


def switch_to_real_data():
    """切换系统使用真实数据"""
    print("\n" + "="*60)
    print("切换到真实数据模式")
    print("="*60)

    # 1. 更新GIS服务使用IEEE数据
    ieee_file = 'data/gis/ieee14_network.json'
    if os.path.exists(ieee_file):
        print(f"\n✓ IEEE网络数据已就绪: {ieee_file}")
        print("  可以在 gis_service.py 中切换使用此数据")
    else:
        print(f"\n✗ IEEE数据未找到，请先运行 integrate_ieee_network()")

    # 2. 更新负载预测使用真实数据
    real_load_files = [
        'data/load_data/realistic_guangdong_load.csv',
        'data/load_data/realistic_beijing_load.csv',
        'data/load_data/realistic_shanghai_load.csv'
    ]

    available_files = [f for f in real_load_files if os.path.exists(f)]

    if available_files:
        print(f"\n✓ 真实负载数据已就绪:")
        for f in available_files:
            print(f"  - {f}")
        print("  可以在 load_prediction.py 中切换使用这些数据")
    else:
        print(f"\n✗ 真实负载数据未找到，请先运行 integrate_realistic_china_data()")


def main():
    """主函数"""
    print("\n" + "="*70)
    print(" "*15 + "真实数据集成工具")
    print("="*70)

    print("\n请选择操作:")
    print("1. 集成IEEE 14-bus标准测试系统（电网拓扑）")
    print("2. 生成中国真实特征负载数据（广东/北京/上海）")
    print("3. 下载OPSD欧洲真实数据（需要网络，约200MB）")
    print("4. 一键集成所有真实数据")
    print("5. 查看当前数据状态")

    choice = input("\n请输入选项 (1-5): ").strip()

    if choice == '1':
        integrate_ieee_network()
    elif choice == '2':
        integrate_realistic_china_data()
    elif choice == '3':
        print("\n下载OPSD数据（欧洲真实负载数据）...")
        loader = RealDataLoader()
        # 下载德国数据作为示例
        df = loader.download_opsd_load_data('DE', years=2)
        if df is not None:
            print(f"\n✓ 下载成功! {len(df)}条记录")
            print(f"  时间范围: {df['timestamp'].min()} 到 {df['timestamp'].max()}")
            print(f"  平均负载: {df['load_mw'].mean():.2f} MW")
    elif choice == '4':
        print("\n一键集成所有数据...")
        integrate_ieee_network()
        integrate_realistic_china_data()
        switch_to_real_data()
        print("\n" + "="*60)
        print("✓ 所有真实数据已集成!")
        print("="*60)
    elif choice == '5':
        switch_to_real_data()
    else:
        print("\n✗ 无效选项")

    print("\n" + "="*70)


if __name__ == '__main__':
    main()
