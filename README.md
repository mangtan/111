# 智能电网规划系统

基于LLM的GIS + 负载预测融合电网规划系统

## 系统特性

### 核心功能
1. **LLM集成** - 使用阿里通义千问(Qwen)大模型
   - 文档检索和约束解析
   - 标准、手册和政策解析为结构化约束
   - 智能规划建议生成

2. **负载预测** - 基于时间序列分析
   - 历史负载数据分析
   - 未来负载预测
   - 过载区域识别

3. **GIS数据处理** - 电网拓扑分析
   - 变电站和线路管理
   - 拓扑结构分析
   - 空间距离计算

4. **轻量级评分器** - 多特征融合
   - 负载增长特征
   - GIS距离特征
   - 拓扑结构特征
   - 约束满足评分

5. **潮流计算** - 使用pandapower
   - 基础潮流计算
   - N-1安全校验
   - 约束违规检查

6. **可视化界面** - Web操作界面
   - 交互式地图(Leaflet)
   - 负载预测图表(Chart.js)
   - 候选方案排名
   - LLM聊天交互

## 系统架构

```
mvp/
├── backend/                # 后端服务
│   ├── app.py             # Flask主应用
│   ├── config.py          # 配置文件
│   ├── services/          # 业务逻辑
│   │   ├── llm_service.py        # LLM服务
│   │   ├── retrieval_service.py  # 文档检索
│   │   ├── load_prediction.py    # 负载预测
│   │   ├── gis_service.py        # GIS处理
│   │   ├── scorer.py             # 评分器
│   │   └── power_flow.py         # 潮流计算
│   ├── data/              # 数据存储
│   └── requirements.txt   # Python依赖
│
└── frontend/              # 前端界面
    ├── index.html         # 主页面
    ├── css/               # 样式
    └── js/                # JavaScript
```

## 快速开始

### 环境要求
- Python 3.8+
- 现代浏览器(Chrome, Firefox, Safari)

### 安装步骤

1. **克隆项目**
```bash
cd /Users/maotao/Documents/接单/mvp
```

2. **安装后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

3. **配置API密钥**
- 将 Qwen API Key 写入环境变量或 `.env`（推荐仅本地保存，不要提交到仓库）
  - 在 `backend/.env`（已 gitignore）中添加：`QWEN_API_KEY=你的密钥`
  - 或在 shell 中导出：`export QWEN_API_KEY=你的密钥`
  - 代码会通过 `os.getenv('QWEN_API_KEY')` 自动读取。

4. **启动后端服务**
```bash
cd backend
python app.py
```
服务将在 http://localhost:5001 启动

5. **打开前端界面**
```bash
# 在浏览器中打开
open frontend/index.html

# 或使用简单的HTTP服务器
cd frontend
python -m http.server 8080
# 然后访问 http://localhost:8080
```

## 使用指南

### 主要操作

1. **加载数据**
   - 点击"加载数据"按钮
   - 系统将加载负载数据、网络拓扑和预测结果

2. **运行完整分析**
   - 点击"运行完整分析"按钮
   - 系统将执行:
     * 负载预测和过载识别
     * 生成候选扩展方案
     * 多特征评分和排名
     * 对Top-K方案进行潮流验证
     * LLM生成规划建议

3. **潮流计算**
   - 点击"潮流计算"查看当前网络状态
   - 显示母线电压、线路负载等信息

4. **N-1校验**
   - 点击"N-1校验"进行安全性分析
   - 识别关键故障场景

5. **LLM交互**
   - 在右侧聊天框输入问题
   - 与LLM进行电网规划咨询

### 可视化界面说明

- **左侧面板**: 系统控制、负载摘要、候选方案排名、LLM建议
- **中间区域**: 电网拓扑地图、负载预测曲线
- **右侧面板**: 潮流计算结果、约束检查、拓扑分析、LLM聊天

## API接口

### 主要端点

```
GET  /                           # 系统信息
GET  /api/documents              # 获取所有文档
POST /api/documents/search       # 搜索文档
POST /api/constraints/parse      # 解析约束
GET  /api/load/summary           # 负载摘要
POST /api/load/predict           # 负载预测
GET  /api/gis/network            # 网络拓扑
POST /api/planning/analyze       # 完整分析
POST /api/powerflow/run          # 潮流计算
POST /api/powerflow/n-minus-1    # N-1校验
POST /api/llm/chat               # LLM聊天
```

## 配置说明

### 主要配置项 (config.py)

```python
# LLM配置
QWEN_API_KEY = "sk-c3330572cec94e73be5ffcbe8af82612"
QWEN_MODEL = "qwen-plus"

# 评分器权重
SCORER_WEIGHTS = {
    'load_growth': 0.3,
    'distance': 0.2,
    'topology': 0.2,
    'constraint': 0.3
}

# 潮流计算配置
MAX_VOLTAGE_DEVIATION = 0.07  # 7%
MAX_LINE_LOADING = 0.9        # 90%
TOP_K_CANDIDATES = 5          # 前5名候选方案
```

## 技术栈

### 后端
- **Flask**: Web框架
- **pandas/numpy**: 数据处理
- **scikit-learn**: 机器学习
- **pandapower**: 电力系统分析
- **requests**: HTTP客户端
- **Qwen API**: 大语言模型

### 前端
- **Leaflet**: 地图可视化
- **Chart.js**: 图表展示
- **原生JavaScript**: 交互逻辑

## 系统流程

1. **数据收集**: 加载历史负载数据、GIS数据、标准文档
2. **负载预测**: 时间序列分析预测未来负载
3. **过载识别**: 识别可能过载的区域
4. **方案生成**: 生成扩展/加固候选方案
5. **约束解析**: LLM解析标准文档为结构化约束
6. **轻量评分**: 多特征融合对候选方案评分排名
7. **潮流验证**: 对Top-K方案进行详细潮流和N-1验证
8. **结果展示**: 可视化展示分析结果和规划建议

## 示例数据

系统包含示例数据:
- 2年历史负载数据
- 5个变电站、5条线路的网络拓扑
- 3个标准文档(技术标准、规划手册、地方政策)

## 注意事项

1. **API密钥**: 确保Qwen API密钥有效且有足够配额
2. **依赖安装**: 某些依赖(如pandapower)可能需要额外的系统库
3. **数据路径**: 所有数据保存在 `backend/data/` 目录
4. **跨域问题**: 前端需要后端CORS支持(已配置)

## 故障排除

### 后端无法启动
```bash
# 检查依赖
pip install -r requirements.txt

# 检查端口占用
lsof -i :5000
```

### API连接失败
- 确保后端服务已启动
- 检查API地址配置(默认: http://localhost:5000)
- 查看浏览器控制台错误信息

### LLM调用失败
- 检查API密钥是否正确
- 确认网络连接正常
- 查看后端日志错误信息

## 未来扩展

- [ ] 更复杂的负载预测模型(LSTM/Transformer)
- [ ] 更精确的GIS数据和地理计算
- [ ] 更多电网设备类型支持
- [ ] 优化算法(遗传算法、粒子群等)
- [ ] 数据库集成
- [ ] 用户认证和权限管理
- [ ] 历史方案管理
- [ ] 导出报告功能

## 许可证

本项目为演示系统，仅供学习和研究使用。

## 联系方式

如有问题，请联系开发团队。
