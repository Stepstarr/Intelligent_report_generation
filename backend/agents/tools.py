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
        """获取增强版搜索工具"""
        search = DuckDuckGoSearchAPIWrapper()
        
        def enhanced_search(query: str,max_results: int = 4) -> str:
            results = search.results(query, max_results)
            formatted_results = []
            
            for result in results:
                formatted_results.append(
                    f"标题: {result['title']}\n"
                    f"链接: {result['link']}\n"
                    f"摘要: {result['snippet']}\n"
                )
            
            return "\n---\n".join(formatted_results)
            
        return Tool(
            name="网络搜索",
            func=enhanced_search,
            description="进行网络搜索并返回带URL的结果"
        )

class GetFullText(BaseTool):
    """获取网页全文内容的工具"""
    name: str = "获取网页全文内容"
    description: str = "获取网页全文内容"
 
    def _run(self, url: str) -> str:
        print('开始获取网页内容...')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15'
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # 检查响应状态
            response.encoding = response.apparent_encoding  # 自动检测编码
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取所有文本内容，不仅仅是 p 标签
            text_content = []
            for element in soup.find_all(['p', 'article', 'div.article-content']):
                text = element.get_text().strip()
                if text:
                    text_content.append(text)
            
            if not text_content:
                return "未能找到文章内容"
                
            return '\n'.join(text_content)
            
        except requests.exceptions.RequestException as e:
            return f"网络请求错误：{str(e)}"
        except Exception as e:
            return f"处理内容时出错：{str(e)}"

# test tools
if __name__ == "__main__":
    tool = WebTools()
    print(tool.get_search_tool().run("量子计算相关政策"))