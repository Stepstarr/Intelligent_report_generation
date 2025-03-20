import asyncio
from typing import List, Dict, Any
import logging
import re
from langchain.chat_models import init_chat_model
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.agents.tools import WebTools, GetFullText
from backend.agents.prompts import graph_template, fewshot_graph_template, initial_refine_template, refine_template

from backend.database.loader import DocumentLoader
import time
from backend.agents.Search_Agent import Search_Agent

class GraphAgent:
    """
    图检索代理：根据报告主题和部分内容生成检索问题，构建检索图
    """
    def __init__(self, search_agent: Search_Agent, persist_directory: str = "./chroma_db"):
        """
        初始化图检索代理
        
        Args:
            search_client: 搜索客户端，用于执行DuckDuckGo搜索
        """
        # self.search_client = search_client
        self.document_loader = DocumentLoader(persist_directory=persist_directory)
        self.logger = logging.getLogger(__name__)
        self.model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)
        self.web_tools = WebTools() 
        self.search_agent = search_agent
    
    def generate_initial_questions(self, topic: str, section: str) -> List[str]:
        """
        根据报告主题和部分内容生成初始检索问题
        
        Args:
            topic: 报告主题
            section: 报告部分
            
        Returns:
            初始检索问题列表
        """
        # 使用LLM生成问题
        prompt = graph_template.format(topic=topic, section=section) + fewshot_graph_template
        
        try:
            response = self.model.invoke(prompt).content
            
            
            # 解析思考过程
            think_processes = []
            think_pattern = r'<\|think_start\|>(.*?)<\|think_end\|>'
            think_matches = re.findall(think_pattern, response, re.DOTALL)
            for match in think_matches:
                think_processes.append(match.strip())
            
            # 解析问题
            questions = []
            question_pattern = r'<\|question_start\|>(.*?)<\|question_end\|>'
            question_matches = re.findall(question_pattern, response, re.DOTALL)
            for match in question_matches:
                questions.append(match.strip())
            # 如果LLM没有生成足够的问题，添加一些默认问题
            if len(questions) < 3:
                default_questions = [
                    f"{topic} {section} 概述",
                    f"{topic} {section} 关键点",
                    f"{topic} {section} 最新研究",
                    f"{topic} {section} 数据统计"
                ]
                questions.extend(default_questions[:5-len(questions)])
                
            # 记录思考过程
            if think_processes:
                self.logger.info(f"LLM思考过程: {think_processes}")
            print(questions[:5])
            return questions[:5] , think_processes  # 限制最多返回5个问题
            
        except Exception as e:
            self.logger.error(f"使用LLM生成问题时出错: {str(e)}")
            # 出错时返回默认问题
            return [
                f"{topic} {section} 概述",
                f"{topic} {section} 关键点",
                f"{topic} {section} 最新研究",
                f"{topic} {section} 数据统计"
            ]
        
    # TODO：以下要整合Search_Agent Search_Agent可以有chat mode 和 search mode 
    def search_web(self, question: str) -> List[str]:
        """
        根据问题搜索网络和知识库
        
        Args:
            question: 搜索问题  
        
        Returns:
            搜索结果列表
        """
        # 使用DuckDuckGo搜索
        search_results_text = self.web_tools.get_search_tool().run(question,max_results=4)
        time.sleep(1)
        # 解析搜索结果文本为结构化数据
        web_results = self._parse_search_results(search_results_text)
        
        # 从知识库中搜索
        kb_results = self._search_knowledge_base(question)
        
        # 合并结果
        combined_results = web_results + kb_results
            
        return combined_results
    
    def _parse_search_results(self, search_results_text: str) -> List[Dict]:
        """将搜索工具返回的文本解析为结构化数据"""
        results = []
        if not search_results_text or "没有找到相关搜索结果" in search_results_text:
            return results
            
        # 按分隔符分割不同的搜索结果
        result_blocks = search_results_text.split("\n---\n")
        
        for block in result_blocks:
            if not block.strip():
                continue
                
            result = {}
            lines = block.strip().split("\n")
            
            for line in lines:
                if line.startswith("标题:"):
                    result["title"] = line[3:].strip()
                elif line.startswith("链接:"):
                    result["url"] = line[3:].strip()
                elif line.startswith("摘要:"):
                    result["snippet"] = line[3:].strip()
            
            if result:  # 只有当解析出结果时才添加
                results.append(result)              
        return results
    
    def _search_knowledge_base(self, question: str, n_results: int = 3) -> List[Dict]:
        """
        从知识库中搜索相关内容
        
        Args:
            question: 搜索问题
            n_results: 返回结果数量
            
        Returns:
            知识库搜索结果列表
        """
       
            # 初始化知识库加载器
        kb_results = self.document_loader.search_documents(question, n_results=n_results)
            # 转换为与网络搜索结果相同的格式
        formatted_results = []
        for result in kb_results:
            formatted_results.append({
                    "title": result['metadata'].get('title', '知识库文档'),
                    "url": f"知识库链接:{result['metadata'].get('title', '未知文档')}",
                    "snippet": result['content'][:200] + "..." if len(result['content']) > 200 else result['content'],
                    "full_text": result['content'],
                    "source": "knowledge_base",
                    "distance": result.get('distance', 0)
                })
        print(formatted_results)
        return formatted_results
            

    
    # TODO：refine链要解耦
    def refine_documents(self, search_results: List[Dict], topic: str, section: str,refine_document=None) -> str:
        """
        根据搜索结果优化文档，构建一个文档链，每个文档依次进入链条进行提炼
        
        Args:
            search_results: 搜索结果列表
            topic: 报告主题
            section: 报告部分
            
        Returns:
            提炼后的文档内容
        """
        if not search_results:
            self.logger.warning("没有搜索结果可供提炼")
            return f"未找到关于{topic}的{section}相关信息。"
            
        # 初始文档
        refined_doc = ""
        
        # 提炼提示词模板
        initial_prompt_template = initial_refine_template
        
        refine_prompt_template = refine_template
        try:
            if refine_document:
                refined_doc = refine_document
                for i in range(0, len(search_results)):
                    print(i)
                    if "full_text" in search_results[i]:
                        doc = search_results[i]["full_text"]+"\n"+"url:"+search_results[i]["url"]
                        refine_prompt = refine_prompt_template.format(
                        topic=topic,
                        section=section,
                        existing_content=refined_doc,
                        document=doc
                    )
                        refined_doc = self.model.invoke(refine_prompt).content
                    
                return refined_doc
                

            # 处理第一个文档
            if search_results and "full_text" in search_results[0]:
                first_doc = search_results[0]["full_text"]+"\n"+"url:"+search_results[0]["url"]
                initial_prompt = initial_prompt_template.format(
                    topic=topic,
                    section=section,
                    document=first_doc
                )
                refined_doc = self.model.invoke(initial_prompt).content
                
            # 依次处理剩余文档
            for i in range(1, len(search_results)):
                print(i)
                if "full_text" in search_results[i]:
                    doc = search_results[i]["full_text"]+"\n"+"url:"+search_results[i]["url"]
                    refine_prompt = refine_prompt_template.format(
                        topic=topic,
                        section=section,
                        existing_content=refined_doc,
                        document=doc
                    )
                    refined_doc = self.model.invoke(refine_prompt).content
                    
            return refined_doc
            
        except Exception as e:
            self.logger.error(f"提炼文档时出错: {str(e)}")
            return f"处理{topic}的{section}信息时遇到错误。"
    
    # TODO：以下均需要修改
if __name__ == "__main__":
    graph_agent = GraphAgent(Search_Agent())
    topic = "量子计算技术动态"
    section = "政策和战略"
    questions, _ = graph_agent.generate_initial_questions(topic, section)
    refined_doc = None
    for question in questions:
        search_results = graph_agent.search_web(question)
        refined_doc = graph_agent.refine_documents(search_results, topic, section,refined_doc)
        print('---------------------------------------------------------------------------')
        print(refined_doc)
        print('---------------------------------------------------------------------------')