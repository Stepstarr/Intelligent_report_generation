import streamlit as st
import random
import time
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# 导入 ChatSearchAgent
from backend.agents.Chat_Search_Agent import ChatSearchAgent
from langchain.chat_models import init_chat_model

# 页面配置
st.set_page_config(
    page_title="聊天界面",
    page_icon="💭",
    layout="wide"  # 使用宽屏布局
)

# 设置页面标题
st.title("情报检索助手 💬")

# 添加简短说明
st.write("这是一个情报检索助手，可以回答问题并进行网络搜索。")
st.caption("支持知识库检索和网络搜索功能。")

# 初始化 ChatSearchAgent
@st.cache_resource
def get_agent():
    llm = init_chat_model("deepseek-chat", model_provider="deepseek", temperature=0)
    return ChatSearchAgent(llm=llm)

agent = get_agent()

# 初始化聊天历史
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "你好！我是 AI 助手，让我们开始聊天吧！ 👋", "citation": ""}]

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("citation") and message["role"] == "assistant":
            st.markdown(f"<div style='font-size: 0.8em; color: gray;'>{message['citation']}</div>", unsafe_allow_html=True)

# 接收用户输入
if prompt := st.chat_input("请输入你的问题..."):
    # 添加用户消息到聊天历史
    st.session_state.messages.append({"role": "user", "content": prompt})
    # 显示用户消息
    with st.chat_message("user"):
        st.markdown(prompt)

    # 显示助手回复
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        citation_placeholder = st.empty()
        
        # 获取侧边栏中的搜索模式设置
        search_mode = st.session_state.get("search_mode", "auto")
        
        # 显示思考中的提示
        message_placeholder.markdown("正在思考中...")
        
        # 调用 ChatSearchAgent 处理查询
        result = agent.process_query(query=prompt, search_mode=search_mode)
        
        full_response = result["answer"]
        citation = result["citation"]
        
        # 直接显示完整回答，不使用打字效果
        message_placeholder.markdown(full_response)
        
        # 显示引用信息（如果有）
        if citation:
            citation_placeholder.markdown(f"<div style='font-size: 0.8em; color: gray;'>{citation}</div>", unsafe_allow_html=True)
        
    # 将助手回复添加到聊天历史
    st.session_state.messages.append({"role": "assistant", "content": full_response, "citation": citation})

# 添加侧边栏配置选项
with st.sidebar:
    st.header("聊天设置")
    
    # 添加搜索模式选择
    st.selectbox(
        "搜索模式",
        ["自动判断", "强制网络搜索", "仅使用知识库"],
        index=0,
        key="search_mode_display",
        help="自动判断：AI 决定是否需要搜索；强制网络搜索：总是使用网络搜索；仅使用知识库：不使用网络搜索"
    )
    
    # 将显示值转换为 API 所需的值
    mode_mapping = {
        "自动判断": "auto",
        "强制网络搜索": "web",
        "仅使用知识库": "knowledge_base"
    }
    st.session_state.search_mode = mode_mapping[st.session_state.search_mode_display]
    
    # 添加聊天风格选择
    st.selectbox(
        "选择聊天风格",
        ["专业", "友好", "简洁"],
        key="chat_style"
    )
    
    # 添加清除聊天按钮
    if st.button("清除聊天历史"):
        st.session_state.messages = [{"role": "assistant", "content": "聊天历史已清除。让我们重新开始！ 👋", "citation": ""}]
        st.rerun()

# 添加页脚
st.markdown("---")
st.caption("开发者：Momo & Ly | 版本：1.0.0")