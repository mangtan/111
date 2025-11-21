"""
LLM服务 - 阿里通义千问Qwen集成
"""
import requests
import json
from typing import List, Dict, Any, Optional
from config import Config


class QwenLLMService:
    """通义千问LLM服务"""

    def __init__(self):
        self.api_key = Config.QWEN_API_KEY
        self.api_base = Config.QWEN_API_BASE
        self.model = Config.QWEN_MODEL

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        调用Qwen聊天完成API

        Args:
            messages: 消息列表 [{"role": "user/assistant/system", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式输出

        Returns:
            API响应
        """
        url = f"{self.api_base}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"LLM API调用错误: {e}")
            raise

    def extract_text(self, response: Dict[str, Any]) -> str:
        """从API响应中提取文本"""
        try:
            return response['choices'][0]['message']['content']
        except (KeyError, IndexError) as e:
            print(f"解析响应错误: {e}")
            return ""

    def parse_constraints(self, document_text: str) -> Dict[str, Any]:
        """
        使用LLM解析文档中的约束条件

        Args:
            document_text: 文档文本

        Returns:
            结构化的约束信息
        """
        system_prompt = """你是一个电网规划专家。请从给定的文档中提取所有技术约束和规划标准。

输出格式应为JSON，包含以下字段：
- voltage_constraints: 电压约束
- capacity_constraints: 容量约束
- distance_constraints: 距离约束
- topology_rules: 拓扑规则
- safety_requirements: 安全要求
- explanations: 每个约束的解释

确保输出是有效的JSON格式。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下文档并提取约束条件：\n\n{document_text[:3000]}"}
        ]

        response = self.chat_completion(messages, temperature=0.3)
        text = self.extract_text(response)

        try:
            # 尝试解析JSON
            constraints = json.loads(text)
            return constraints
        except json.JSONDecodeError:
            # 如果不是有效的JSON，返回原始文本
            return {
                "raw_text": text,
                "parsed": False
            }

    def evaluate_candidate(
        self,
        candidate: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用LLM评估候选方案是否满足约束

        Args:
            candidate: 候选方案
            constraints: 约束条件

        Returns:
            评估结果
        """
        system_prompt = """你是一个电网规划专家。请评估给定的规划方案是否满足所有约束条件。

输出格式应为JSON，包含以下字段：
- compliant: true/false (是否符合要求)
- violations: [] (违反的约束列表)
- score: 0-100 (合规分数)
- recommendations: [] (改进建议)"""

        user_prompt = f"""候选方案：
{json.dumps(candidate, ensure_ascii=False, indent=2)}

约束条件：
{json.dumps(constraints, ensure_ascii=False, indent=2)}

请评估该方案是否满足约束条件。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self.chat_completion(messages, temperature=0.3)
        text = self.extract_text(response)

        try:
            evaluation = json.loads(text)
            return evaluation
        except json.JSONDecodeError:
            return {
                "raw_text": text,
                "parsed": False
            }

    def generate_planning_suggestions(
        self,
        gis_data: Dict[str, Any],
        load_forecast: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        基于GIS数据、负载预测和约束条件生成规划建议

        Args:
            gis_data: GIS数据
            load_forecast: 负载预测
            constraints: 约束条件

        Returns:
            规划建议列表
        """
        system_prompt = """你是一个电网规划专家。基于GIS数据、负载预测和技术约束，生成合理的电网加固和扩展方案。

输出格式应为JSON数组，每个方案包含：
- type: "reinforcement" 或 "expansion"
- location: 位置描述
- equipment: 设备类型
- capacity: 容量
- priority: 优先级(1-5)
- reasoning: 理由"""

        user_prompt = f"""GIS数据摘要：
{json.dumps(gis_data, ensure_ascii=False, indent=2)[:1000]}

负载预测：
{json.dumps(load_forecast, ensure_ascii=False, indent=2)[:1000]}

约束条件：
{json.dumps(constraints, ensure_ascii=False, indent=2)[:1000]}

请生成3-5个规划方案建议。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self.chat_completion(messages, temperature=0.7, max_tokens=3000)
        text = self.extract_text(response)

        try:
            suggestions = json.loads(text)
            if isinstance(suggestions, list):
                return suggestions
            else:
                return [suggestions]
        except json.JSONDecodeError:
            return [{
                "raw_text": text,
                "parsed": False
            }]


# 全局实例
llm_service = QwenLLMService()
