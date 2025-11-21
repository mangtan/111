"""
配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """系统配置"""

    # LLM配置 - 阿里Qwen（从环境变量读取，避免泄露）
    QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
    QWEN_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL = "qwen-plus"  # 可选: qwen-turbo, qwen-plus, qwen-max

    # 数据路径
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
    DOCUMENTS_DIR = os.path.join(DATA_DIR, 'documents')
    GIS_DIR = os.path.join(DATA_DIR, 'gis')
    LOAD_DATA_DIR = os.path.join(DATA_DIR, 'load_data')

    # 向量数据库配置
    VECTOR_DB_PATH = os.path.join(DATA_DIR, 'vector_db')
    EMBEDDING_MODEL = "text-embedding-v1"

    # 评分器配置
    SCORER_WEIGHTS = {
        'load_growth': 0.3,      # 负载增长权重
        'distance': 0.2,         # 距离权重
        'topology': 0.2,         # 拓扑权重
        'constraint': 0.3        # 约束满足权重
    }

    # 潮流计算配置
    VOLTAGE_LEVELS = [10, 35, 110, 220, 500]  # kV
    MAX_VOLTAGE_DEVIATION = 0.07  # 7%
    MAX_LINE_LOADING = 0.9  # 90%
    MAX_TRAFO_LOADING = 0.9  # 变压器允许负载率（p.u.）

    # N-1校验配置
    N_MINUS_1_CHECK = True

    # 候选方案配置
    TOP_K_CANDIDATES = 6  # 演示期扩大到前6名
    DEMO_DIVERSIFY_TOPK = True  # 演示开关：Top-K内进行类型多样化选择
    # 演示：新建变电站时将邻近母线部分负荷“迁移”到新母线，以放大方案效果
    DEMO_REASSIGN_LOAD_ALPHA = 0.3  # 迁移比例（0~1），仅用于候选注入评估

    # 机器学习评分配置
    ENABLE_ML_SCORING = True
    ML_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'ml', 'gbdt_ieee14.joblib')
    ML_SCORE_WEIGHT = 0.3  # ML分数在总分中的权重 (0~1)

    # Flask配置
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = 5001
    FLASK_DEBUG = True
