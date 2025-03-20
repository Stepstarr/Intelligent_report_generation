from typing import List, Dict, Any, Optional, Union, Literal
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.llms.base import BaseLLM
import sys
import os
from langchain.chat_models import init_chat_model
# 添加项目根目录到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# 使用绝对导入替代相对导入
from backend.database.loader import DocumentLoader
from backend.agents.tools import WebTools, GetFullText

class ChatSearchAgent:
    """聊天搜索代理，可以根据问题生成响应，判断是否需要搜索，处理搜索结果"""
    
    def __init__(self, llm: BaseLLM, persist_directory: str = "./chroma_db"):
        self.llm = llm
        self.document_loader = DocumentLoader(persist_directory=persist_directory)
        self.web_tools = WebTools()  # 初始化WebTools
        self.search_tool = self.web_tools.get_search_tool()  # 获取搜索工具
        self.full_text_tool = GetFullText()  # 初始化获取全文工具
        
        # 初始化判断是否需要搜索的Chain
        self.need_search_prompt = PromptTemplate(
            input_variables=["query"],
            template="""
            用户问题: {query}
            
            请判断这个问题是否需要进行网络搜索来获取最新或特定信息。
            如果问题涉及最新事件、具体数据、特定事实或需要最新信息，应该进行搜索。
            如果是一般性问题、主观问题或不需要特定信息的问题，则不需要搜索。
            
            只回答"是"或"否"。
            """
        )
        self.need_search_chain = LLMChain(llm=llm, prompt=self.need_search_prompt)
        
        # 初始化判断是否需要获取全文的Chain
        self.need_full_text_prompt = PromptTemplate(
            input_variables=["query", "search_results"],
            template="""
            用户问题: {query}
            
            搜索结果摘要:
            {search_results}
            
            基于以上搜索结果摘要，请判断是否需要获取完整文章内容来更全面地回答用户问题。
            如果摘要已经包含足够信息，或问题只需要简单信息，则不需要获取全文。 
            如果问题需要深入分析、详细解释或摘要信息不足，则需要获取全文。
            
            只回答"是"或"否"。
            """
        )
        self.need_full_text_chain = LLMChain(llm=llm, prompt=self.need_full_text_prompt)
        
        # 初始化生成最终回答的Chain
        self.final_answer_prompt = PromptTemplate(
            input_variables=["query", "search_results", "knowledge_base_results", "full_text"],
            template="""
            用户问题: {query}
            
            搜索结果:
            {search_results}
            
            知识库检索结果:
            {knowledge_base_results}
            
            全文内容(如果有):
            {full_text}
            
            请根据以上信息，生成一个全面、准确的回答。回答应该:
            1. 直接回应用户问题，不要添加任何解释性文字
            2. 综合搜索结果和知识库信息
            3. 在回答中适当位置添加引用标记，如[1]、[2]等，表明信息来源。引用标记要和后面参考来源一一对应。
            4. 保持客观、准确，避免臆测
            5. 确保在回答中的每个关键信息点都有对应的引用标记
            6. 确保所有引用的来源在参考来源中都有对应条目
            """
        )
        self.final_answer_chain = LLMChain(llm=llm, prompt=self.final_answer_prompt)
        
        # 初始化生成引用索引的Chain
        self.citation_prompt = PromptTemplate(
            input_variables=["answer", "sources"],
            template="""
            回答内容: {answer}
            
            信息来源:
            {sources}
            
            请为上述回答生成适当的引用索引，并确保回答中已经包含了对应的引用标记。
            
            要求：
            1. 检查回答中是否已经包含了引用标记（如[1]、[2]等）
            2. 如果回答中缺少引用标记，请在适当位置添加，确保每个关键信息点都有引用
            3. 生成完整的参考来源列表，格式如下：
               [1] 来源标题, URL或文档名称
               [2] 来源标题, URL或文档名称
            4. 确保回答中的引用标记与参考来源列表一一对应
            5. 如果多处引用同一篇文章，使用相同的引用标号
            6. 所有引用必须来源于提供的知识库或网络搜索结果，不得编造引用
            
            请返回修改后的完整回答（包含引用标记）和参考来源列表。
            """
        )
        self.citation_chain = LLMChain(llm=llm, prompt=self.citation_prompt)
    
    def process_query(self, query: str, search_mode: Union[Literal["auto"], Literal["web"], Literal["knowledge_base"]] = "auto") -> Dict[str, Any]:
        """处理用户查询，返回完整的回答和相关信息
        
        Args:
            query: 用户查询
            search_mode: 搜索模式
                - "auto": 自动判断是否需要网络搜索
                - "web": 强制使用网络搜索
                - "knowledge_base": 只使用知识库搜索
        """
        need_search = False
        
        # 根据搜索模式决定是否进行网络搜索
        if search_mode == "auto":
            # 自动判断是否需要搜索
            need_search_response = self.need_search_chain.run(query=query).strip().lower()
            need_search = need_search_response == "是"
        elif search_mode == "web":
            # 强制使用网络搜索
            need_search = True
        # knowledge_base模式下不进行网络搜索
        
        search_results = []
        full_text = ""
        need_full_text = False
        
        # 如果需要搜索，执行搜索
        if need_search:
            # 使用search_tool进行搜索
            search_results_text = self.search_tool.run(query)
            
            # 解析搜索结果文本为结构化数据
            search_results = self._parse_search_results(search_results_text)
            
            # 判断是否需要获取全文
            need_full_text_response = self.need_full_text_chain.run(
                query=query, 
                search_results=search_results_text
            ).strip().lower()
            
            need_full_text = need_full_text_response == "是"
            
            # 如果需要获取全文，获取全文
            if need_full_text and search_results:
                # 获取第一个结果的全文
                first_url = search_results[0].get("url", "")
                if first_url:
                    full_text = self.full_text_tool.run(first_url)
        
        # 从知识库检索相关内容
        knowledge_base_results = self.document_loader.search_documents(query, n_results=3)
        knowledge_base_text = self._format_knowledge_base_results(knowledge_base_results)
        
        # 生成最终回答
        final_answer = self.final_answer_chain.run(
            query=query,
            search_results=self._format_search_results(search_results),
            knowledge_base_results=knowledge_base_text,
            full_text=full_text
        )
        
        # 准备信息来源
        sources = []
        if search_results:
            sources.extend([{"title": result.get("title", "未知"), "url": result.get("url", "未知")} 
                           for result in search_results])
        if knowledge_base_results:
            sources.extend([{"title": result.get("metadata", {}).get("title", "未知"), 
                            "url": result.get("metadata", {}).get("source", "未知"),
                            "content": result.get("content", "未知")}
                           for result in knowledge_base_results])
        
        # 去除重复的信息来源
        unique_sources = self._deduplicate_sources(sources)
        
        # 生成带有引用的回答和引用列表
        if unique_sources:
            formatted_sources = self._format_sources_for_citation(unique_sources)
            citation_result = self.citation_chain.run(
                answer=final_answer,
                sources=formatted_sources
            )
            
            # 解析结果，提取更新后的回答和引用
            updated_answer, citation = self._parse_citation_result(citation_result)
            if updated_answer:
                final_answer = updated_answer
        else:
            citation = ""
        
        # 返回结果
        return {
            "query": query,
            "answer": final_answer,
            "citation": citation,
            "search_results": search_results,
            "knowledge_base_results": knowledge_base_results,
            "full_text": full_text if full_text else None,
            "needed_search": need_search,
            "needed_full_text": need_full_text if need_search else False
        }
    
    def _format_search_results(self, results: List[Dict]) -> str:
        """格式化搜索结果为文本"""
        if not results:
            return "没有找到相关搜索结果。"
        
        formatted_text = ""
        for i, result in enumerate(results):
            formatted_text += f"结果 {i+1}:\n"
            formatted_text += f"标题: {result.get('title', '未知')}\n"
            formatted_text += f"摘要: {result.get('snippet', '无摘要')}\n"
            formatted_text += f"内容: {result.get('content', '无内容')}\n"
            formatted_text += f"URL: {result.get('url', '未知')}\n\n"
       
        
        return formatted_text
    
    def _format_knowledge_base_results(self, results: List[Dict]) -> str:
        """格式化知识库检索结果为文本"""
        if not results:
            return "知识库中没有找到相关信息。"
        
        formatted_text = ""
        for i, result in enumerate(results):
            formatted_text += f"知识库结果 {i+1}:\n"
            formatted_text += f"标题: {result.get('metadata', {}).get('title', '未知')}\n"
            formatted_text += f"内容: {result.get('content', '无内容')[:200]}...\n"
            formatted_text += f"来源: {result.get('metadata', {}).get('source', '未知')}\n"
            formatted_text += f"摘要: {result.get('summary', '无摘要')}\n\n"
        
        return formatted_text

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

    def _deduplicate_sources(self, sources: List[Dict]) -> List[Dict]:
        """去除重复的信息来源，基于URL或文档路径"""
        unique_sources = []
        seen_urls = set()
        
        for source in sources:
            url = source.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_sources.append(source)
        
        return unique_sources

    def _format_sources_for_citation(self, sources: List[Dict]) -> str:
        """格式化信息来源为引用生成所需的格式"""
        formatted_text = ""
        for i, source in enumerate(sources):
            formatted_text += f"来源 {i+1}:\n"
            formatted_text += f"标题: {source.get('title', '未知')}\n"
            formatted_text += f"URL: {source.get('url', '未知')}\n"
            if 'content' in source and source['content']:
                content_preview = source['content'][:100] + "..." if len(source['content']) > 100 else source['content']
                formatted_text += f"内容片段: {content_preview}\n"
            formatted_text += "\n"
        return formatted_text

    def _parse_citation_result(self, citation_result: str) -> tuple:
        """解析引用生成结果，提取更新后的回答和引用列表"""
        # 尝试分离回答和参考来源
        parts = citation_result.split("\n参考来源:", 1)
        
        if len(parts) == 2:
            # 成功分离
            updated_answer = parts[0].strip()
            citation = "\n参考来源:" + parts[1]
            return updated_answer, citation
        
        # 如果无法按预期分离，尝试其他可能的分隔符
        parts = citation_result.split("\n\n参考来源:", 1)
        if len(parts) == 2:
            updated_answer = parts[0].strip()
            citation = "\n参考来源:" + parts[1]
            return updated_answer, citation
            
        # 如果仍然无法分离，返回原始结果和空引用
        return citation_result, ""

if __name__ == "__main__":
    # 测试聊天搜索代理
    import os
    from langchain_openai import ChatOpenAI
    
    # 初始化LLM
    # llm = ChatOpenAI(
    #     model_name="gpt-4o",
    #     temperature=0.7,
    #     api_key=os.getenv("OPENAI_API_KEY")
    # )
    llm= init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)
    
    # 初始化聊天搜索代理
    agent = ChatSearchAgent(llm=llm)
    
    # 测试不同搜索模式
    test_queries = [
        {"query": "什么是量子计算？", "mode": "knowledge_base"},
        {"query": "最近的人工智能发展有哪些突破？", "mode": "web"},
        # {"query": "如何做红烧肉？", "mode": "auto"}
    ]
    
    for test in test_queries:
        print(f"\n\n测试查询: {test['query']}")
        print(f"搜索模式: {test['mode']}")
        print("-" * 50)
        
        result = agent.process_query(query=test["query"], search_mode=test["mode"])
        
        print(f"是否进行了网络搜索: {result['needed_search']}")
        print(f"是否获取了全文: {result['needed_full_text']}")
        print("\n回答:")
        print(result["answer"])
        
        if result["citation"]:
            print(result["citation"])
        
        print("=" * 80)
