# 真实数据集成指南

## 📊 已集成的开源数据

### ✅ 1. IEEE标准测试系统（已内置）
**来源**: IEEE Power Systems Test Case Archive
**通过**: pandapower库内置

**包含系统**:
- ✅ IEEE 14-bus (14节点系统)
- ✅ IEEE 30-bus (30节点系统)
- ✅ IEEE 118-bus (118节点系统)

**特点**:
- 最权威的电力系统测试数据
- 全球学术界和工业界标准
- 包含完整的母线、线路、负载、发电机数据

### ✅ 2. 中国真实特征负载数据（已生成）
**来源**: 基于中国电网公开统计数据建模
**位置**: `backend/data/load_data/realistic_*.csv`

**已生成数据**:
- ✅ 广东省 (基础负载6000MW, 年增6%)
- ✅ 北京市 (基础负载2000MW, 年增4%)
- ✅ 上海市 (基础负载3000MW, 年增5%)

**特点**:
- 考虑中国气候特征（夏季/冬季双峰）
- 工作日/节假日负载差异
- 午间小高峰 + 晚间大高峰
- 2年历史数据，17,520条小时级记录

### 🌐 3. Open Power System Data（可下载）
**来源**: https://open-power-system-data.org/
**类型**: 欧洲真实电力数据

**包含**:
- 真实负载数据（德国、法国、英国等）
- 可再生能源发电数据
- 电价数据
- 天气数据

**大小**: 约200MB
**格式**: CSV，小时级数据

---

## 🚀 快速开始

### 方法一：使用交互式脚本（推荐）

```bash
cd backend
source venv/bin/activate
python integrate_real_data.py
```

**选项**:
1. 集成IEEE 14-bus系统（电网拓扑）
2. 生成中国真实特征数据（广东/北京/上海）
3. 下载OPSD欧洲数据（需要网络）
4. **一键集成所有数据**
5. 查看当前数据状态

### 方法二：Python代码直接调用

```python
from services.real_data_loader import RealDataLoader

loader = RealDataLoader()

# 1. 加载IEEE标准系统
ieee_network = loader.get_ieee_network_info('case14')
print(f"母线数: {len(ieee_network['buses'])}")
print(f"总负载: {sum([l['p_mw'] for l in ieee_network['loads']])} MW")

# 2. 生成中国真实数据
df_gd = loader.generate_realistic_china_load('guangdong')
print(f"广东负载数据: {len(df_gd)}条记录")

# 3. 下载欧洲数据（可选）
df_eu = loader.download_opsd_load_data('DE', years=2)
```

---

## 📂 数据文件位置

生成的数据保存在：

```
backend/data/
├── load_data/
│   ├── realistic_guangdong_load.csv    ✅ 已生成
│   ├── realistic_beijing_load.csv
│   ├── realistic_shanghai_load.csv
│   └── opsd_DE_load.csv                (可下载)
│
└── gis/
    ├── network_topology.json            (原模拟数据)
    └── ieee14_network.json              (IEEE真实拓扑)
```

---

## 🔧 切换到真实数据

### 1. 切换负载数据

编辑 `backend/services/load_prediction.py`:

```python
def load_historical_data(self):
    # 原来的模拟数据
    # df = self.generate_sample_data()

    # 切换为真实数据
    data_file = os.path.join(self.data_dir, 'realistic_guangdong_load.csv')
    df = pd.read_csv(data_file, parse_dates=['timestamp'])

    self.historical_data = df
    return df
```

### 2. 切换电网拓扑

编辑 `backend/services/gis_service.py`:

```python
def load_network_data(self):
    # 使用IEEE标准系统
    data_file = os.path.join(self.gis_dir, 'ieee14_network.json')

    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            self.network_data = json.load(f)
```

---

## 📊 数据对比

| 数据源 | 拓扑 | 负载 | 真实性 | 规模 |
|--------|------|------|--------|------|
| **IEEE 14-bus** | ✅ 真实 | ✅ 标准 | ⭐⭐⭐⭐⭐ 学术标准 | 小型 |
| **中国特征数据** | ❌ | ✅ 真实特征 | ⭐⭐⭐⭐ 基于统计 | 省级 |
| **OPSD欧洲** | ❌ | ✅ 真实 | ⭐⭐⭐⭐⭐ 实测数据 | 国家级 |
| **原模拟数据** | ❌ | ❌ | ⭐⭐ 完全模拟 | 城市级 |

---

## 📈 数据统计

### 广东省真实特征数据（已生成）

```
✓ 文件: realistic_guangdong_load.csv
✓ 记录数: 17,520条（2年小时级）
✓ 平均负载: 6,000 MW
✓ 峰值负载: ~8,400 MW
✓ 谷值负载: ~4,500 MW
✓ 年增长率: 6%
✓ 特征: 夏季/冬季双峰，晚间大高峰
```

### IEEE 14-bus系统

```
✓ 母线数: 14
✓ 线路数: 20
✓ 负载数: 11
✓ 发电机数: 5
✓ 总负载: 259 MW
✓ 电压等级: 多级（含132kV, 33kV等）
```

---

## 🌍 更多开源数据源

### 1. **GridLAB-D**
- https://github.com/gridlab-d/gridlab-d
- 美国配电网模型

### 2. **PyPSA Networks**
- https://github.com/PyPSA/pypsa-eur
- 欧洲输电网模型

### 3. **PJM数据市场**
- https://dataminer2.pjm.com/
- 美国PJM电网实时数据

### 4. **ERCOT**
- http://www.ercot.com/gridinfo/load/
- 德州电网数据

### 5. **中国电力企业联合会**
- https://www.cec.org.cn/
- 统计年鉴（需手动下载）

---

## ⚠️ 注意事项

1. **OPSD数据下载较大**（约200MB），需要稳定网络
2. **IEEE系统是标准测试案例**，适合算法验证
3. **中国特征数据是基于统计建模**，非实测数据
4. **真实电网数据涉及安全**，生产环境需获得授权
5. **地理坐标可能需要调整**以适应中国地图

---

## 🎯 推荐使用方案

### 方案一：演示和开发（当前默认）
- 电网拓扑: 模拟数据（易于理解）
- 负载数据: 模拟数据（可控参数）
- 适用: MVP展示、功能开发

### 方案二：学术研究
- 电网拓扑: **IEEE 14/30/118-bus**
- 负载数据: **中国真实特征数据**
- 适用: 算法验证、论文实验

### 方案三：实际应用
- 电网拓扑: 从SCADA/EMS导入
- 负载数据: 从历史数据库导入
- 适用: 生产环境、实际规划

---

## 📞 获取帮助

需要帮助集成数据？运行：

```bash
cd backend
python integrate_real_data.py
```

选择选项5查看当前数据状态。
