from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredURLLoader,
    TextLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import chromadb
import os
import dotenv
from chromadb.api.models.Collection import Collection
dotenv.load_dotenv()

class ChromaManager:
    @staticmethod
    def get_collection(persist_directory="./chroma_db", collection_name="documents"):
        client = chromadb.PersistentClient(path=persist_directory)
        embedding_model = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model="text-embedding-ada-002"
        )
        
        # 创建符合新接口的embedding函数
        class OpenAIEmbeddingFunction:
            def __init__(self, embedding_model):
                self.embedding_model = embedding_model
                
            def __call__(self, input):
                if isinstance(input, str):
                    input = [input]
                return self.embedding_model.embed_documents(input)

        embedding_function = OpenAIEmbeddingFunction(embedding_model)

        # 使用 get_or_create_collection 替代 get_collection
        return client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )

    @staticmethod
    def delete_collection(persist_directory="./chroma_db", collection_name="documents"):
        """删除指定的collection"""
        try:
            client = chromadb.PersistentClient(path=persist_directory)
            client.delete_collection(name=collection_name)
            return True
        except Exception as e:
            print(f"删除collection时发生错误: {str(e)}")
            return False