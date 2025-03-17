from langchain.tools import Tool, BaseTool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
import requests
from bs4 import BeautifulSoup
from typing import Dict, List
'''
存了一些工具
'''
class WebTools:
    @staticmethod
    def get_search_tool() -> Tool:
        """获取 DuckDuckGo 搜索工具"""
        return Tool(
            name="DuckDuckGo 搜索",
            func=DuckDuckGoSearchAPIWrapper().run,
            description="使用 DuckDuckGo 进行网络搜索"
        )

class GetFullText(BaseTool):
    """获取网页全文内容的工具"""
    name: str = "获取网页全文内容"
    description: str = "获取网页全文内容"
 
    def _run(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            return ' '.join(p.get_text().strip() for p in soup.find_all('p'))
        except Exception as e:
            return f"无法获取全文内容：{str(e)}"