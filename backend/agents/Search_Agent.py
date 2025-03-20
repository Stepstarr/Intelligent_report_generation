from langchain.chat_models import init_chat_model
from langchain.chains import LLMChain
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from typing import Dict, List
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from backend.agents.tools import WebTools, GetFullText

class Search_Agent:
    def __init__(self, user_input_template: str = "{question}", user_context_template: str = "{context}"):
        # 初始化模型
        self.model = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)
        self.user_input_template = user_input_template
        self.user_context_template = user_context_template
        
        # 初始化工具
        self.search_tool = WebTools.get_search_tool()
        self.get_full_text_tool = GetFullText()
        
        # 创建工具列表
        self.tools = [
            Tool(
                name="检索",
                func=self.search_tool.run,
                description="用于搜索网络信息，输入应为搜索关键词"
            ),
            Tool(
                name="获取全文",
                func=self.get_full_text_tool.run,
                description="用于获取网页的完整内容，输入应为网页URL"
            )
        ]
        
        # 创建Agent
        self.agent_prompt = PromptTemplate.from_template(
            """你是一个信息检索助手。
            
            你有以下工具可以使用:
            {tools}
            
            工具名称: {tool_names}
            
            请按照以下格式回答:
            
            Thought: 你的思考过程
            Action: 工具名称
            Action Input: 工具的输入
            Observation: 工具的输出
            ... (这个思考/行动/观察可以重复多次)
            Thought: 我现在知道最终答案
            Final Answer: 对用户问题的最终回答
            
            重要提示：
            1. 不要重复执行相同的操作
            2. 在获取搜索结果后，如果发现有价值的网页链接，应该使用"获取全文"工具获取更详细的信息
            3. 在获取足够信息后，直接提供最终答案
            
            请按照以下步骤处理用户问题:
            1. 如果需要搜索信息，使用"检索"工具
            2. 分析搜索结果，如果需要获取某个网页的完整内容，使用"获取全文"工具
            3. 基于所有收集到的信息，提供完整、准确的回答
            
            问题: {question}
            主题: {topic}
            
            {agent_scratchpad}
            """
        )
        
        self.agent = create_react_agent(
            llm=self.model,
            tools=self.tools,
            prompt=self.agent_prompt
        )
        
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True
        )

    def forward(
        self,
        question: str,
        topic: str,
        history: List[dict] = None,
    ):
        try:
            # 执行Agent
            result = self.agent_executor.invoke({
                "question": question,
                "topic": topic
            })
            
            return result["output"]
        except Exception as e:
            return f"处理过程中出现错误: {str(e)}"


if __name__ == "__main__":
    # 创建Agent
    agent = Search_Agent()
    print(agent.forward("量子计算技术动态", "量子计算"))