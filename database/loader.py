from langchain_community.document_loaders import TextLoader, WebBaseLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import os

load_dotenv()

embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))

# 直接使用 OpenAIEmbeddings 来创建嵌入
texts = [
    "hi",
    "hello",
    "What's your name?",
    "my friends call me John",
    'hello, how are you?',
]

# 为多个文本创建嵌入
embedded_texts = embeddings.embed_documents(texts)


embedded_query = embeddings.embed_query("What's the name mentioned in the text?")
print(embedded_query[:5])

# 创建 Chroma 向量数据库
vectorstore = Chroma.from_texts(
    texts=texts,
    embedding=embeddings
)

# 使用查询向量搜索最相似的文本
query = "What's the name mentioned in the text?"
docs = vectorstore.similarity_search(query, k=2)  # k=2 表示返回最相似的2条结果

# 打印搜索结果
for doc in docs:
    print(doc.page_content)
