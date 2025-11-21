"""
文档检索服务 - 使用向量数据库进行文档检索
"""
import os
import json
from typing import List, Dict, Any, Optional
import numpy as np
from pathlib import Path
import pickle


class DocumentRetrieval:
    """文档检索系统"""

    def __init__(self, documents_dir: str, vector_db_path: str):
        self.documents_dir = documents_dir
        self.vector_db_path = vector_db_path
        self.documents = []
        self.embeddings = []
        self.index = None

        # 创建目录
        os.makedirs(documents_dir, exist_ok=True)
        os.makedirs(os.path.dirname(vector_db_path), exist_ok=True)

        # 加载已有索引
        self.load_index()

    def load_documents(self):
        """加载文档"""
        self.documents = []

        # 扫描文档目录
        for file_path in Path(self.documents_dir).rglob('*.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.documents.append({
                    'path': str(file_path),
                    'filename': file_path.name,
                    'content': content,
                    'type': self._get_document_type(file_path.name)
                })

        # 添加示例文档（如果目录为空）
        if len(self.documents) == 0:
            self._create_sample_documents()

    def _get_document_type(self, filename: str) -> str:
        """根据文件名判断文档类型"""
        filename_lower = filename.lower()
        if '标准' in filename or 'standard' in filename_lower:
            return 'standard'
        elif '手册' in filename or 'manual' in filename_lower:
            return 'manual'
        elif '政策' in filename or 'policy' in filename_lower:
            return 'policy'
        else:
            return 'general'

    def _create_sample_documents(self):
        """创建示例文档"""
        sample_docs = [
            {
                'filename': '电网规划技术标准.txt',
                'content': """电网规划技术标准

第一章 电压等级和质量标准
1. 110kV电网电压偏差：±7%
2. 220kV电网电压偏差：±5%
3. 500kV电网电压偏差：±3%

第二章 线路负载率标准
1. 正常运行时线路负载率不超过90%
2. N-1故障时线路负载率不超过100%
3. 重载时段线路负载率不超过95%

第三章 变电站容量标准
1. 110kV变电站主变容量：2×50MVA或2×63MVA
2. 220kV变电站主变容量：2×180MVA或2×240MVA
3. 变电站备用容量不低于30%

第四章 供电可靠性要求
1. 重要用户供电可靠性不低于99.99%
2. 城市用户供电可靠性不低于99.95%
3. 农村用户供电可靠性不低于99.9%

第五章 安全距离要求
1. 110kV线路与建筑物最小水平距离：5米
2. 220kV线路与建筑物最小水平距离：6米
3. 500kV线路与建筑物最小水平距离：8.5米
""",
                'type': 'standard'
            },
            {
                'filename': '电网扩展规划手册.txt',
                'content': """电网扩展规划手册

第一章 规划原则
1. 以负载预测为基础
2. 满足N-1安全准则
3. 考虑经济性和可靠性平衡
4. 适应城市发展规划

第二章 变电站选址原则
1. 靠近负荷中心
2. 交通便利，便于设备运输
3. 避开地质灾害区域
4. 预留扩建空间

第三章 线路路径选择
1. 路径最短，减少线损
2. 避开人口密集区
3. 考虑环境影响
4. 便于施工和维护

第四章 设备选型
1. 优先选择节能设备
2. 设备容量留有余量
3. 考虑设备互换性
4. 符合国家标准

第五章 投资估算
1. 110kV变电站单位造价：3-5万元/kVA
2. 220kV变电站单位造价：2-4万元/kVA
3. 110kV线路单位造价：60-80万元/km
4. 220kV线路单位造价：100-150万元/km
""",
                'type': 'manual'
            },
            {
                'filename': '地方电网规划政策.txt',
                'content': """地方电网规划政策

第一条 规划目标
到2030年，全市电网供电能力达到2000万千瓦，供电可靠率达到99.99%。

第二条 优先发展区域
1. 经济开发区优先保障
2. 高新技术产业园区优先规划
3. 老旧城区电网改造优先实施

第三条 环保要求
1. 新建线路优先采用电缆
2. 变电站采用紧凑型布置
3. 减少电磁辐射影响

第四条 土地使用
1. 变电站用地纳入城市规划
2. 线路走廊预留保护
3. 地下管廊优先使用

第五条 投资政策
1. 政府补贴农村电网改造
2. 鼓励社会资本参与
3. 优化投资审批流程

第六条 技术政策
1. 推广智能电网技术
2. 提高设备自动化水平
3. 建设配电自动化系统
""",
                'type': 'policy'
            }
        ]

        for doc in sample_docs:
            file_path = os.path.join(self.documents_dir, doc['filename'])
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(doc['content'])
            self.documents.append({
                'path': file_path,
                'filename': doc['filename'],
                'content': doc['content'],
                'type': doc['type']
            })

    def create_embeddings(self):
        """创建文档嵌入（简化版，使用TF-IDF）"""
        from sklearn.feature_extraction.text import TfidfVectorizer

        if len(self.documents) == 0:
            self.load_documents()

        # 使用TF-IDF创建向量
        vectorizer = TfidfVectorizer(max_features=384)
        texts = [doc['content'] for doc in self.documents]
        self.embeddings = vectorizer.fit_transform(texts).toarray()

        # 保存向量化器
        self.vectorizer = vectorizer

    def build_index(self):
        """构建向量索引"""
        if len(self.embeddings) == 0:
            self.create_embeddings()

        # 简单的向量索引（实际应用中可以使用FAISS）
        self.index = {
            'embeddings': self.embeddings,
            'documents': self.documents
        }

        # 保存索引
        self.save_index()

    def save_index(self):
        """保存索引到文件"""
        with open(self.vector_db_path, 'wb') as f:
            pickle.dump({
                'index': self.index,
                'vectorizer': self.vectorizer
            }, f)

    def load_index(self):
        """加载索引"""
        if os.path.exists(self.vector_db_path):
            try:
                with open(self.vector_db_path, 'rb') as f:
                    data = pickle.load(f)
                    self.index = data['index']
                    self.vectorizer = data['vectorizer']
                    self.documents = self.index['documents']
                    self.embeddings = self.index['embeddings']
                return True
            except Exception as e:
                print(f"加载索引失败: {e}")
        return False

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            top_k: 返回前k个结果

        Returns:
            相关文档列表
        """
        if self.index is None:
            self.build_index()

        # 将查询转换为向量
        query_vector = self.vectorizer.transform([query]).toarray()[0]

        # 计算相似度
        similarities = np.dot(self.embeddings, query_vector)

        # 获取top_k结果
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            doc = self.documents[idx].copy()
            doc['score'] = float(similarities[idx])
            results.append(doc)

        return results

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """获取所有文档"""
        if len(self.documents) == 0:
            self.load_documents()
        return self.documents


# 初始化检索系统
from config import Config
retrieval_service = DocumentRetrieval(
    Config.DOCUMENTS_DIR,
    Config.VECTOR_DB_PATH
)
