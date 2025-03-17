from langchain.chat_models import init_chat_model
from typing import Dict, List
import requests
from bs4 import BeautifulSoup
from langchain.tools import BaseTool
from langchain.agents import Tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from tools import WebTools, GetFullText

class Search_Agent:
    def __init__(self, user_input_template: str = "{question}", user_context_template: str = "{context}"):
        #TODO 适配更多模型
        self.model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)
        self.user_input_template = user_input_template
        self.user_context_template = user_context_template
        
        # 新增搜索工具
        self.search_tool = WebTools.get_search_tool()
        self.get_full_text = GetFullText()

    def forward(
        self,
        question: str,
        topic: str,
        history: List[dict] = None,
    ):
        # 构建提示模板
        prompt = f"""
        请根据以下问题生成响应。如果需要搜索，请使用以下格式：
        <工具>{{"名称":"检索", "query":"搜索关键词"}}</工具>
        
        问题：{question}
        主题：{topic}
        """
        
        # 获取模型响应
        response = self.model.predict(prompt)
        
        # 解析工具调用
        if "<工具>" in response and "</工具>" in response:
            import re
            import json
            
            try:
                # 提取工具参数
                tool_pattern = r'<工具>(.*?)</工具>'
                tool_json = re.search(tool_pattern, response, re.DOTALL).group(1)
                tool_args = json.loads(tool_json)
                
                if tool_args["名称"] == "检索":
                    # 调用搜索工具
                    search_result = self.search_tool.run(tool_args["query"])
                    return f"搜索结果：{search_result}"
                    
            except Exception as e:
                return f"工具调用失败：{str(e)}"
        
        return response


if __name__ == "__main__":
    # 创建工具
    agent = Search_Agent()
    print(agent.forward("量子计算技术动态", "量子计算"))
    # tool = Get_full_text()
    # print(tool.run("https://www.baidu.com"))