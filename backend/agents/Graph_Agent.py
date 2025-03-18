import asyncio
from typing import List, Dict, Any
import logging
import re
from langchain.chat_models import init_chat_model
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.agents.prompts import graph_template, fewshot_graph_template
from backend.agents.Search_Agent import Search_Agent

class GraphAgent:
    """
    图检索代理：根据报告主题和部分内容生成检索问题，构建检索图
    """
    def __init__(self, search_client):
        """
        初始化图检索代理
        
        Args:
            search_client: 搜索客户端，用于执行DuckDuckGo搜索
        """
        self.search_client = search_client
        self.logger = logging.getLogger(__name__)
        self.model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)
    
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
                print(match.strip())
            
            # 解析问题
            questions = []
            question_pattern = r'<\|question_start\|>(.*?)<\|question_end\|>'
            question_matches = re.findall(question_pattern, response, re.DOTALL)
            for match in question_matches:
                questions.append(match.strip())
                print(match.strip())
            # 如果LLM没有生成足够的问题，添加一些默认问题
            if len(questions) < 3:
                default_questions = [
                    f"{topic} {section} 概述",
                    f"{topic} {section} 关键点",
                    f"{topic} {section} 最新研究",
                    f"{topic} {section} 数据统计"
                ]
                questions.extend(default_questions[:5-len(questions)])
                
            # 记录思考过程（可选）
            if think_processes:
                self.logger.info(f"LLM思考过程: {think_processes}")
                
            return questions[:5]  # 限制最多返回5个问题
            
        except Exception as e:
            self.logger.error(f"使用LLM生成问题时出错: {str(e)}")
            # 出错时返回默认问题
            return [
                f"{topic} {section} 概述",
                f"{topic} {section} 关键点",
                f"{topic} {section} 最新研究",
                f"{topic} {section} 数据统计"
            ]
   
    # TODO：以下均需要修改
    async def generate_follow_up_questions(self, topic: str, section: str, 
                                          search_results: List[Dict[str, Any]]) -> List[str]:
        """
        根据初始搜索结果生成后续检索问题
        
        Args:
            topic: 报告主题
            section: 报告部分
            search_results: 初始搜索结果
            
        Returns:
            后续检索问题列表
        """
        # 从搜索结果中提取关键信息，生成更具体的问题
        # 实际应用中应使用LLM分析搜索结果并生成问题
        follow_up_questions = []
        
        # 从搜索结果中提取关键词和概念
        keywords = self._extract_keywords_from_results(search_results)
        
        # 为每个关键词生成更具体的问题
        for keyword in keywords[:3]:  # 限制问题数量
            follow_up_questions.append(f"{topic} {section} {keyword} 详细分析")
            follow_up_questions.append(f"{keyword} 在{topic}中的应用")
        
        return follow_up_questions
    
    def _extract_keywords_from_results(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """
        从搜索结果中提取关键词
        
        Args:
            search_results: 搜索结果
            
        Returns:
            关键词列表
        """
        # 简化实现，实际应用中应使用NLP技术提取关键词
        keywords = []
        for result in search_results:
            if 'title' in result:
                # 简单地将标题分词并添加到关键词列表
                words = result['title'].split()
                keywords.extend([w for w in words if len(w) > 4])  # 简单过滤短词
        
        # 去重并返回
        return list(set(keywords))
    
    async def build_search_graph(self, topic: str, section: str) -> Dict[str, Any]:

        """
        构建检索图
        
        Args:
            topic: 报告主题
            section: 报告部分
            
        Returns:
            检索图，包含问题和对应的搜索结果
        """
        search_graph = {
            "topic": topic,
            "section": section,
            "nodes": []
        }
        
        # 生成初始问题
        initial_questions = await self.generate_initial_questions(topic, section)
        
        # 执行初始搜索
        initial_results = {}
        initial_search_tasks = []
        
        for question in initial_questions:
            task = asyncio.create_task(self.search_client.search(question))
            initial_search_tasks.append((question, task))
        
        # 等待所有初始搜索完成
        for question, task in initial_search_tasks:
            try:
                results = await task
                initial_results[question] = results
                search_graph["nodes"].append({
                    "question": question,
                    "results": results,
                    "follow_up_questions": []
                })
            except Exception as e:
                self.logger.error(f"搜索问题 '{question}' 时出错: {str(e)}")
        
        # 为每个初始问题生成后续问题
        for i, node in enumerate(search_graph["nodes"]):
            question = node["question"]
            results = node["results"]
            
            # 生成后续问题
            follow_up_questions = await self.generate_follow_up_questions(topic, section, results)
            
            # 执行后续搜索
            follow_up_search_tasks = []
            for follow_up_question in follow_up_questions:
                task = asyncio.create_task(self.search_client.search(follow_up_question))
                follow_up_search_tasks.append((follow_up_question, task))
            
            # 等待所有后续搜索完成
            for follow_up_question, task in follow_up_search_tasks:
                try:
                    follow_up_results = await task
                    search_graph["nodes"][i]["follow_up_questions"].append({
                        "question": follow_up_question,
                        "results": follow_up_results
                    })
                except Exception as e:
                    self.logger.error(f"搜索后续问题 '{follow_up_question}' 时出错: {str(e)}")
        
        return search_graph

if __name__ == "__main__":
    graph_agent = GraphAgent(Search_Agent())
    topic = "量子计算技术动态"
    section = "政策和战略"
    questions = graph_agent.generate_initial_questions(topic, section)
    print(questions)
