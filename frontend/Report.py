import streamlit as st
import asyncio
import sys
import os
import time
from typing import List, Dict, Any
import json

# 添加项目根目录到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 导入报告生成器
from backend.agents.streaming import ReportGenerator

# 页面配置
st.set_page_config(
    page_title="报告生成器",
    page_icon="📊",
    layout="wide"
)

# 设置页面标题
st.title("📊 智能报告生成")

# 添加简短说明
st.write("这是一个智能报告生成工具，可以根据主题自动生成结构化报告。")
st.caption("系统会自动搜索相关信息并生成完整报告内容。")

# 侧边栏配置
with st.sidebar:
    st.header("报告设置")
    
    # 报告主题输入
    report_topic = st.text_input("报告主题", value="量子计算技术动态", help="输入你想生成报告的主题")
    
    # 高级设置
    with st.expander("高级设置"):
        max_sections = st.number_input("最大章节数", min_value=1, max_value=10, value=2, 
                                      help="限制报告生成的最大章节数")
        max_questions = st.number_input("每章节最大问题数", min_value=1, max_value=5, value=1, 
                                       help="每个章节处理的最大问题数量")
    
    # 生成报告按钮
    generate_button = st.button("生成报告", type="primary", use_container_width=True)
    
    # 取消生成按钮
    if "generating" in st.session_state and st.session_state.generating:
        if st.button("取消生成", type="secondary", use_container_width=True):
            st.session_state.generating = False
            st.rerun()
    
    # 清空报告按钮
    if "report_content" in st.session_state and st.session_state.report_content:
        if st.button("清空报告", use_container_width=True):
            st.session_state.report_content = ""
            st.session_state.report_structure = None
            st.session_state.current_section = None
            st.session_state.refined_doc = ""
            st.rerun()

# 初始化会话状态
if "report_content" not in st.session_state:
    st.session_state.report_content = ""
if "report_structure" not in st.session_state:
    st.session_state.report_structure = None
if "current_section" not in st.session_state:
    st.session_state.current_section = None
if "refined_doc" not in st.session_state:
    st.session_state.refined_doc = ""
if "generating" not in st.session_state:
    st.session_state.generating = False
if "live_sections" not in st.session_state:
    st.session_state.live_sections = []

# 创建两列布局
col1, col2 = st.columns([3, 2])

# 左侧：报告生成过程
with col1:
    st.subheader("生成过程")
    process_container = st.container(height=600, border=True)
    
    # 显示生成过程
    if st.session_state.report_content:
        with process_container:
            st.markdown(st.session_state.report_content)

# 右侧：报告结构和当前内容
with col2:
    # 报告结构
    st.subheader("报告结构")
    structure_container = st.container(height=200, border=True)
    with structure_container:
        if st.session_state.report_structure:
            st.json(st.session_state.report_structure)
        else:
            st.info("报告结构将在生成过程中显示")
    
    # 当前章节内容
    st.subheader("当前章节内容")
    content_container = st.container(height=350, border=True)
    with content_container:
        if st.session_state.refined_doc:
            st.markdown(st.session_state.refined_doc)
        else:
            st.info("章节内容将在生成过程中更新")

# 处理报告生成
if generate_button:
    # 重置状态
    st.session_state.report_content = ""
    st.session_state.report_structure = None
    st.session_state.current_section = None
    st.session_state.refined_doc = ""
    st.session_state.generating = True
    
    # 创建报告生成器
    generator = ReportGenerator()
    
    # 使用st.empty()创建可更新的容器
    process_placeholder = process_container.empty()
    structure_placeholder = structure_container.empty()
    content_placeholder = content_container.empty()
    
    try:
        # 生成报告
        for chunk in generator.generate_full_report(
            topic=report_topic,
            max_questions=max_questions,
            max_sections=max_sections
        ):
            # 检查是否取消生成
            if not st.session_state.generating:
                process_placeholder.markdown(st.session_state.report_content + "\n\n**报告生成已取消**")
                break
                
            
            
            # 检查是否包含报告结构信息
            if "报告结构已生成" in chunk and st.session_state.report_structure is None:
                    # 提取结构信息
                structure_text = chunk.split("报告结构已生成：")[1].strip()
                    # 尝试找到JSON对象的开始和结束位置
                    
                st.session_state.report_structure = structure_text
                structure_placeholder.json(st.session_state.report_structure)
            # 更新生成过程
            else:
                st.session_state.report_content += chunk
                process_placeholder.markdown(st.session_state.report_content)
            # 检查是否是新章节开始
            if "开始生成章节:" in chunk:
                section_title = chunk.split("开始生成章节:")[1].strip()
                st.session_state.current_section = section_title
                st.session_state.refined_doc = ""  # 重置当前章节内容
            
            # 检查是否包含章节内容更新
            if "当前章节内容更新：" in chunk:
                st.session_state.refined_doc = chunk.split("当前章节内容更新：\n")[1].strip()
                content_placeholder.markdown(st.session_state.refined_doc)
            
            # 添加一点延迟，让UI有时间更新
            time.sleep(0.01)
        
        # 生成完成
        st.session_state.generating = False
        
    except Exception as e:
        st.error(f"报告生成出错: {str(e)}")
        st.session_state.generating = False

# 添加页脚
st.markdown("---")
st.caption("开发者：Momo & Ly | 版本：1.0.0")
