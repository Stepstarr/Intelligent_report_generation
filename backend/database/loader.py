from typing import List, Dict, Optional
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredURLLoader,
    TextLoader
)
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from langchain.text_splitter import RecursiveCharacterTextSplitter
from backend.database.chroma_manager import ChromaManager

class DocumentLoader:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.collection = ChromaManager.get_collection(persist_directory=persist_directory)
        
    def process_document(self, file_path: str, doc_type: str, title: Optional[str] = None, 
                        notes: Optional[str] = None, summary: Optional[str] = None):
        """处理不同类型的文档并存入ChromaDB
        
        Args:
            file_path: 文档路径或URL
            doc_type: 文档类型 ('pdf', 'docx', 'url' 或 'txt')
            title: 可选的文档标题
            notes: 可选的文档备注
            summary: 可选的文档摘要
        """
        # 根据文档类型选择合适的加载器
        if doc_type == "pdf":
            loader = PyPDFLoader(file_path)
        elif doc_type == "docx":
            loader = Docx2txtLoader(file_path)
        elif doc_type == "url":
            loader = UnstructuredURLLoader([file_path])
        elif doc_type == "txt":
            loader = TextLoader(file_path)
        else:
            raise ValueError(f"Unsupported document type: {doc_type}")
            
        # 加载文档
        documents = loader.load()
        
        # 文本分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(documents)
        
        # 准备数据
        texts = [split.page_content for split in splits]
        metadatas = [{
            "source": file_path,
            "title": title or file_path,
            "doc_type": doc_type,
            "page": split.metadata.get("page", 0),
            "notes": notes or "",  # 添加备注字段
            "summary": summary or "",  # 添加摘要字段
        } for split in splits]
        current_count = len(self.collection.get()["ids"])
        
        # 生成唯一ID
        ids = [f"doc_{current_count + i}" for i in range(len(texts))]
        
        # 添加到ChromaDB
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
    def search_documents(self, query: str, n_results: int = 5) -> List[Dict]:
        """搜索相关文档并返回结果及其来源文档信息"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["metadatas", "documents", "distances"]
            )
            
            # 格式化返回结果
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'chunk_id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i],
                    'notes': results['metadatas'][0][i]['notes'],
                    'summary': results['metadatas'][0][i]['summary']
                })
            
            return formatted_results
        except ConnectionError as e:
            print(f"连接错误: {str(e)}")
            return []
        except Exception as e:
            print(f"搜索文档时发生错误: {str(e)}")
            return []

    def get_all_documents(self) -> List[Dict]:
        """获取数据库中的所有文档"""
        try:
            results = self.collection.get()
            formatted_results = []
            for i in range(len(results['ids'])):
                formatted_results.append({
                    'chunk_id': results['ids'][i],
                    'content': results['documents'][i],
                    'metadata': results['metadatas'][i]
                })
            return formatted_results
        except Exception as e:
            print(f"获取文档时发生错误: {str(e)}")
            return []

    def clear_collection(self):
        """清除当前collection中的所有数据"""
        try:
            ChromaManager.delete_collection()
            self.collection = ChromaManager.get_collection()
            return True
        except Exception as e:
            print(f"清除数据时发生错误: {str(e)}")
            return False

if __name__ == "__main__":
    loader = DocumentLoader()
    loader.clear_collection()  # 清除所有数据
    loader.process_document("/Users/stepstar/program/Intelligent_report_generation/database/docs/01一周要闻_事关量子科技，工信部最新发声.docx", doc_type="docx",
    title="量子计算研究报告",
    summary="本文详细介绍了量子计算的最新发展...")
    results = loader.search_documents("量子信息技术工信部")
    for result in results:
        print(f"\n文档来源: {result['metadata']['title']}")
        print(f"页码: {result['metadata']['page']}")
        print(f"相似度距离: {result['distance']}")
        print(f"内容片段: {result['content'][:100]}...")
        print(f"备注: {result['notes']}")
        print(f"摘要: {result['summary']}")
    
