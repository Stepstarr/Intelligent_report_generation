import streamlit as st
import pandas as pd
from pathlib import Path
import os
from datetime import datetime
import sys
sys.path.append("../../")  
from backend.database.loader import DocumentLoader
import tempfile

# 页面配置
st.set_page_config(
    page_title="知识库",
    page_icon="📚",
    layout="wide"
)

# 初始化 session state
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []
if "knowledge_base" not in st.session_state:
    st.session_state.knowledge_base = {}

# 初始化 DocumentLoader 并加载现有文档
if "document_loader" not in st.session_state:
    st.session_state.document_loader = DocumentLoader() 
    # 从数据库加载现有文档
    existing_docs = st.session_state.document_loader.get_all_documents()
    for doc in existing_docs:
        metadata = doc['metadata']
        st.session_state.knowledge_base[metadata['source']] = {
            "details": {
                "文件名": os.path.basename(metadata['source']),
                "文件类型": metadata['doc_type'],
                "文件大小": "N/A"  # 由于文件已在数据库中，无法获取原始大小
            },
            "title": metadata['title'],
            "summary": metadata['summary'],
            "notes": metadata['notes'],
            "upload_time": "已存在"  # 对于已存在的文档，显示"已存在"
        }

# 添加当前时间的辅助函数
def get_current_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 主标题
st.title("📚 知识库管理")

# 创建上半部分的两列布局
top_col1, top_col2 = st.columns(2)

# 左侧：上传部分
with top_col1:
    st.subheader("文档上传")
    uploaded_file = st.file_uploader(
        "上传文档",
        type=["txt", "pdf", "doc", "docx"],
        help="支持 txt、pdf、doc、docx 格式的文件"
    )

    if uploaded_file is not None and "submitted" not in st.session_state:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        # 保存文件信息
        file_details = {
            "文件名": uploaded_file.name,
            "文件类型": uploaded_file.type,
            "文件大小": f"{uploaded_file.size / 1024:.2f} KB"
        }
        
        # 添加文件元信息表单
        with st.form("file_metadata_form"):
            file_title = st.text_input("文件标题", value=uploaded_file.name.split('.')[0])
            file_summary = st.text_area("文件摘要", placeholder="请输入文件摘要...")
            file_notes = st.text_area("备注", placeholder="请输入备注信息...")
            submit_button = st.form_submit_button("添加到知识库")
            
            if submit_button:
                if uploaded_file.name not in st.session_state.knowledge_base:
                    try:
                        # 处理文档并存入数据库
                        
                        doc_type = uploaded_file.name.split('.')[-1].lower()
                        print(doc_type)
                        st.session_state.document_loader.process_document(
                            file_path=tmp_file_path,
                            doc_type=doc_type,
                            title=file_title,
                            notes=file_notes,
                            summary=file_summary
                        )
                        
                        # 更新session state
                        st.session_state.knowledge_base[uploaded_file.name] = {
                            "details": file_details,
                            "title": file_title,
                            "summary": file_summary,
                            "notes": file_notes,
                            "upload_time": get_current_time()
                        }
                        st.session_state.submitted = True
                        st.success(f"文件 {uploaded_file.name} 已添加到知识库！")
                        
                        # 删除临时文件
                        os.unlink(tmp_file_path)
                        st.rerun()
                    except Exception as e:
                        st.error(f"文件处理失败：{str(e)}")
                else:
                    st.warning("该文件已存在于知识库中！")

# 右侧：知识检索
with top_col2:
    st.subheader("知识检索")
    search_query = st.text_input("输入搜索关键词", placeholder="请输入要搜索的内容...")
    
    if search_query:
        results = st.session_state.document_loader.search_documents(search_query)
        for result in results:
            with st.expander(f"来自：{result['metadata']['title']} (相似度：{1-result['distance']:.2f})"):
                st.markdown(result['content'])
                st.caption(f"摘要：{result['metadata']['summary']}")
                if result['metadata']['notes']:
                    st.caption(f"备注：{result['metadata']['notes']}")

# 侧边栏配置
with st.sidebar:
    st.header("知识库设置")
    
    # 文件类型过滤
    selected_types = st.multiselect(
        "文件类型过滤",
        ["txt", "pdf", "doc", "docx"],
        default=["txt", "pdf", "doc", "docx"]
    )
    
    # 文件排序方式
    sort_method = st.selectbox(
        "文件排序方式",
        ["按名称升序", "按名称降序", "按大小升序", "按大小降序", "按上传时间降序", "按上传时间升序"]
    )
    
    # 显示统计信息
    st.subheader("统计信息")
    st.write(f"文件总数：{len(st.session_state.knowledge_base)}")
    
    # 清空知识库按钮
    if st.button("清空知识库"):
        st.session_state.knowledge_base = {}
        st.session_state.document_loader.clear_collection()
        st.rerun()

# 知识库文件列表部分
st.markdown("---")
st.subheader("知识库文件列表")
if st.session_state.knowledge_base:
    # 创建数据表格
    files_data = []
    for filename, file_info in st.session_state.knowledge_base.items():
        # 获取文件扩展名
        file_ext = filename.split('.')[-1].lower()
        # 只添加选中类型的文件
        if file_ext in selected_types:
            # 将文件大小转换为数字以便排序
            size_str = file_info["details"]["文件大小"]
            if size_str != "N/A":
                size_num = float(size_str.split()[0])  # 提取数字部分
            else:
                size_num = 0

            files_data.append({
                "文件名": filename,
                "标题": file_info["title"],
                "上传时间": file_info["upload_time"],
                "文件大小": file_info["details"]["文件大小"],
                "文件大小数值": size_num,  # 添加用于排序的数值列
                "摘要": file_info["summary"],
                "备注": file_info["notes"]
            })
    
    if files_data:  # 只在有数据时创建和排序 DataFrame
        df = pd.DataFrame(files_data)
        
        # 根据侧边栏的排序方式进行排序
        if sort_method == "按名称升序":
            df = df.sort_values(by="文件名")
        elif sort_method == "按名称降序":
            df = df.sort_values(by="文件名", ascending=False)
        elif sort_method == "按大小升序":
            df = df.sort_values(by="文件大小数值")
        elif sort_method == "按大小降序":
            df = df.sort_values(by="文件大小数值", ascending=False)
        elif sort_method == "按上传时间降序":
            df = df.sort_values(by="上传时间", ascending=False)
        elif sort_method == "按上传时间升序":
            df = df.sort_values(by="上传时间")
        
        # 删除用于排序的数值列，显示结果
        df = df.drop(columns=["文件大小数值"])
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("没有找到符合所选文件类型的文件")

    # 在数据表下方添加删除操作
    col1, col2 = st.columns([3, 1])
    with col1:
        file_to_delete = st.selectbox(
            "选择要删除的文件",
            options=list(st.session_state.knowledge_base.keys()),
            key="delete_selector"
        )
    with col2:
        if st.button("删除", key="delete_button", use_container_width=True):
            if file_to_delete in st.session_state.knowledge_base:
                del st.session_state.knowledge_base[file_to_delete]
                # 清空并重建数据库
                st.session_state.document_loader.clear_collection()
                st.success(f"已删除文件：{file_to_delete}")
                st.rerun()

else:
    st.info("知识库暂无文件")

# 页脚
st.markdown("---")
st.caption("人类的智慧在于等待与希望")
st.caption("开发者：Momo & Ly | 版本：1.0.0")