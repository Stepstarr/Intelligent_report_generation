# Intelligent_report_generation

本项目构建情报分析报告智能生成模型，利用大语言模型辅助完成情报的收集、筛选、信息提取及报告撰写等关键环节。通过该模型，能够大幅减少人工操作，提高情报处理的速度和准确性，使信息获取更加全面、系统，并确保输出格式规范统一。

### 技术栈

* LangChain:构建智能代理和工作流
* Streamlit:构建Web界面

* ChromaDB:向量数据库存储
* OpenAI/DeepSeek:大语言模型支持

### 配置

* Python 3.10+
* Poetry（依赖管理工具）

在项目文件新建.env，添加必要的API密钥

```
DEEPSEEK_API_KEY = 
OPENAI_API_KEY=
```

### 运行应用

```
PYTHONPATH=$PYTHONPATH:$(pwd) streamlit run frontend/Report.py
```

### Record

[duckduckgo](https://blog.csdn.net/gitblog_01234/article/details/143042489)
