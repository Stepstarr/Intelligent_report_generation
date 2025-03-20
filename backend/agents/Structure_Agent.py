from langchain.chat_models import init_chat_model
from typing import Dict, List
import requests
from bs4 import BeautifulSoup
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, Tool
from langchain_community.tools import DuckDuckGoSearchResults 
from langchain.agents import initialize_agent  # 新增初始化方法
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.agents.prompts import fewshot_structure_template,structure_template_cn
from langchain_core.output_parsers import JsonOutputParser  # 输出解析器

class Structure_Agent:
    def __init__(self, user_input_topic: str = "{topic}", user_context_template: str = "{context}"):
        #TODO 适配更多模型
        self.model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)
        self.user_input_topic = user_input_topic
        self.user_context_template = user_context_template
        # 添加搜索工具
        self.search_tool = DuckDuckGoSearchResults()
        '''
        self.tools = [
            Tool(
                name="网络检索",
                func=self.search_tool.run,
                description="使用此工具通过DuckDuckGo搜索引擎获取最新的网络信息"
            )
        ]
        '''
        # 替换Agent初始化方式
        # self.agent_executor = initialize_agent(
        #     tools=self.tools,
        #     llm=self.model,
        #     agent="structured-chat-zero-shot-react-description",  # 使用结构化agent类型
        #     verbose=True,
        #     handle_parsing_errors=True,
        #     return_intermediate_steps=True  # 允许中间步骤
        # )
        self.parser = JsonOutputParser()  # 初始化JSON解析器

    def forward(self):
        # 重构提示词结构
        structured_prompt = structure_template_cn.format(
            topic=self.user_input_topic,
        )# + "\n请使用以下格式响应：\nThought: 思考过程\nAction: 工具名称\nAction Input: 输入参数"
        
        raw_response = self.model.invoke(structured_prompt+fewshot_structure_template)
        return self.parser.parse(raw_response.content)  # 使用解析器直接处理原始内容

if __name__ == "__main__":
    agent = Structure_Agent()
    agent.user_input_topic = "量子计算技术动态"
    previous_conversation = [     
    ]
    result = agent.forward()
    print('-------------------------------------------------------------')
    print(result)
