# 快速启动指南

## 1. 启动后端服务

### 方法一：使用启动脚本（推荐）

**Mac/Linux:**
```bash
cd /Users/maotao/Documents/接单/mvp
chmod +x start.sh
./start.sh
```

**Windows:**
```cmd
cd /Users/maotao/Documents/接单/mvp
start.bat
```

### 方法二：手动启动

```bash
cd /Users/maotao/Documents/接单/mvp/backend

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# 或
venv\Scripts\activate.bat  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

服务将在 **http://localhost:5001** 启动

## 2. 打开前端界面

### 方法一：直接在浏览器打开
```bash
open frontend/index.html  # Mac
# 或在浏览器中打开 frontend/index.html
```

### 方法二：使用HTTP服务器（推荐）
```bash
cd frontend
python3 -m http.server 8080
```
然后在浏览器访问: **http://localhost:8080**

## 3. 使用系统

### 首次使用
1. 点击"加载数据"按钮，系统会：
   - 自动生成示例电网拓扑数据
   - 生成2年历史负载数据
   - 创建标准文档库
   - 在地图上显示电网拓扑

2. 点击"运行完整分析"按钮，系统会：
   - 预测未来负载
   - 识别过载区域
   - 生成候选扩展方案
   - 使用LLM解析约束条件
   - 对候选方案评分排名
   - 对Top-5方案进行潮流验证
   - 生成规划建议

### 其他功能
- **潮流计算**: 查看当前网络的潮流分析结果
- **N-1校验**: 进行N-1安全性分析
- **LLM交互**: 在右侧聊天框与AI助手交流

## 4. 验证系统运行

### 测试API
```bash
# 测试根路径
curl http://localhost:5001/

# 测试获取网络拓扑
curl http://localhost:5001/api/gis/network

# 测试负载摘要
curl http://localhost:5001/api/load/summary
```

### 检查服务状态
```bash
# Mac/Linux
lsof -i :5001

# 查看Python进程
ps aux | grep python
```

## 5. 系统配置

### API配置
- Qwen API Key: 已配置在 `backend/config.py`
- API Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1
- 模型: qwen-plus

### 端口配置
- 后端端口: 5001 (在 `backend/config.py` 修改)
- 前端端口: 8080 (可自定义)

如果需要修改端口，需要同时修改:
1. `backend/config.py` 中的 `FLASK_PORT`
2. `frontend/js/app.js` 中的 `API_BASE_URL`

## 6. 常见问题

### 端口被占用
如果5001端口被占用，修改配置文件中的端口号。

### 依赖安装失败
确保使用Python 3.8+版本，并在虚拟环境中安装。

### API连接失败
1. 确认后端服务已启动
2. 检查浏览器控制台错误
3. 确认防火墙未阻止连接

### LLM调用失败
1. 检查API密钥是否正确
2. 确认网络连接正常
3. 查看后端终端输出的错误信息

## 7. 停止服务

### 停止后端
在终端中按 `Ctrl+C` 停止Flask服务

### 完全清理
```bash
# 找到并杀死所有相关进程
ps aux | grep "python app.py" | grep -v grep | awk '{print $2}' | xargs kill
```

## 8. 项目结构快速参考

```
mvp/
├── backend/
│   ├── app.py              # Flask主应用 ✓
│   ├── config.py           # 系统配置 ✓
│   ├── services/           # 业务逻辑模块 ✓
│   ├── data/               # 数据存储 (自动生成)
│   └── venv/               # Python虚拟环境
│
└── frontend/
    ├── index.html          # 主页面 ✓
    ├── css/style.css       # 样式 ✓
    └── js/app.js           # 交互逻辑 ✓
```

## 9. 下一步

系统已经完全可用！你可以：
- 导入真实的电网数据
- 调整评分权重和约束参数
- 扩展更多功能模块
- 集成更多数据源

祝使用愉快！
