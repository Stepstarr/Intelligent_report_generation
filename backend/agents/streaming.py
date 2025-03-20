import asyncio
import time
from typing import Dict, List, Generator, Any
import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.agents.Structure_Agent import Structure_Agent
from backend.agents.Graph_Agent import GraphAgent


# 移除了循环导入: from backend.agents.streaming import stream_text

# 添加stream_text函数定义
async def stream_text(text: str, delay: float = 0.01):
    """
    流式输出文本
    
    Args:
        text: 要输出的文本
        delay: 每个字符之间的延迟（秒）
    """
    for char in text:
        print(char, end="", flush=True)
        await asyncio.sleep(delay)
    print()

class ReportGenerator:
    """
    报告生成器：协调Structure_Agent和Graph_Agent生成完整报告
    """
    def __init__(self):
        """
        初始化报告生成器
        """
        self.logger = logging.getLogger(__name__)

        self.structure_agent = Structure_Agent()
        self.graph_agent = GraphAgent()
        
    def generate_report_structure(self, topic: str) :
        """
        生成报告结构
        
        Args:
            topic: 报告主题
            
        Returns:
            报告结构字典
        """
        self.structure_agent.user_input_topic = topic
        yield "正在生成报告结构...\n"
        report_structure = self.structure_agent.forward()
        yield f"报告结构已生成：\n{report_structure}\n"
        return report_structure
        
    def generate_section_content(self, topic: str, section: str, max_questions: int = 1) -> Generator[str, None, None]:
        """
        生成报告章节内容
        
        Args:
            topic: 报告主题
            section: 章节名称
            max_questions: 最多处理的问题数量，None表示处理所有问题
            
        Yields:
            生成过程和内容
        """
        # 生成检索问题
        yield f"正在为章节 '{section}' 生成检索问题...\n"
        questions, think_processes = self.graph_agent.generate_initial_questions(topic, section)
        
        if think_processes:
            yield f"\n思考过程：\n"
            for i, process in enumerate(think_processes):
                yield f"{process}\n"
        
        # 输出思考过程
        yield f"为章节 '{section}' 生成的检索问题：\n"
        for i, question in enumerate(questions):
            yield f"{i+1}. {question}\n"

        # 如果设置了最大问题数，则限制问题数量
        if max_questions is not None and max_questions > 0:
            questions = questions[:max_questions]
            yield f"\n将处理前 {max_questions} 个问题\n"
        
        # 初始化精炼文档
        refined_doc = None
        
        # 对每个问题进行搜索和内容精炼
        for i, question in enumerate(questions):
            yield f"\n正在处理问题 {i+1}/{len(questions)}: {question}\n"
            
            # 搜索网络
            yield f"正在搜索相关信息...\n"
            search_results = self.graph_agent.search_web(question)
            
            if not search_results:
                yield f"未找到与问题 '{question}' 相关的搜索结果\n"
                continue
                
            yield f"找到 {len(search_results)} 条相关结果\n"
            
            # 精炼文档
            yield f"正在整合信息...\n"
            refined_doc = self.graph_agent.refine_documents(search_results, topic, section, refined_doc)
            
            # 流式输出当前精炼结果
            yield f"\n当前章节内容更新：\n"
            for char in refined_doc:
                yield char
                time.sleep(0.01)  # 减慢输出速度，便于阅读
            
        return refined_doc
        
    def generate_full_report(self, topic: str, max_questions: int = None, max_sections: int =1) -> Generator[str, None, None]:
        """
        生成完整报告
        
        Args:
            topic: 报告主题
            max_questions: 每个章节最多处理的问题数量，None表示处理所有问题
            max_sections: 最多处理的章节数量，None表示处理所有章节
            
        Yields:
            生成过程和内容
        """
        # 生成报告结构
        yield "开始生成报告...\n\n"
        
        # 直接调用方法获取报告结构，而不是使用生成器
        structure = self.structure_agent.forward()
        yield f"报告结构已生成：{structure}"
        
        # 生成每个章节的内容
        full_report = {"title": topic, "sections": []}
        
        # 如果设置了最大章节数，则限制章节数量
        sections_to_process = structure["structure"]
        if max_sections is not None and max_sections > 0:
            sections_to_process = structure["structure"][:max_sections]
            # yield f"将只处理前 {max_sections} 个章节\n"
        
        for section_info in sections_to_process:
            section_title = section_info["subtitle"]
            yield f"\n\n开始生成章节: {section_title}\n"
            yield f"{'='*50}\n"
            
            section_content = ""
            for chunk in self.generate_section_content(topic, section_title, max_questions):
                yield chunk
                if isinstance(chunk, str) and not chunk.startswith("正在") and not chunk.startswith("找到") and not chunk.startswith("为章节"):
                    section_content += chunk
            
            full_report["sections"].append({
                "title": section_title,
                "content": section_content
            })
            
            yield f"\n{'='*50}\n"
            yield f"章节 '{section_title}' 生成完成\n"
            
        yield "\n报告生成完成！\n"
        return full_report

if __name__ == "__main__":
    generator = ReportGenerator()
    topic = "量子计算技术动态"
    
    for chunk in generator.generate_full_report(topic, max_questions=1, max_sections=1):
        print(chunk, end="", flush=True)
