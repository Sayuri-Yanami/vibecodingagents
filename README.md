# AI 面试官：自有 API + 本地 RAG

这是根据《AI 面试官系统智能体实训方案》落地的自建版本。项目不绑定智谱清言、腾讯元器、DeepSeek 或其他固定厂商；模型接口、模型名和密钥均由你自行配置。

核心功能：

- 本地知识库：支持 TXT、Markdown、CSV、JSON；可选支持 PDF、DOCX。
- 中文检索：使用本地 TF-IDF 与中文字符组合检索，不下载大型向量模型。
- 自有 API：兼容 OpenAI `chat/completions` 请求格式。
- 两种使用方式：命令行问答和浏览器聊天界面。
- 来源引用：每次回答展示检索到的本地文件和相关度。
- 多轮对话：保留最近几轮上下文。

## 第 1 步：准备环境

需要 Python 3.10 或更高版本。进入项目目录：

```powershell
cd C:\Users\icYanami\Desktop\智能体\ai_interviewer
python --version
```

核心功能没有第三方依赖，可以直接运行。

如果知识库中需要放 PDF 或 DOCX，再安装可选依赖：

```powershell
python -m pip install pypdf python-docx
```

## 第 2 步：配置自己的 API

项目已经准备好本地 `.env` 文件。打开它，至少填写：

```dotenv
API_BASE_URL=https://你的接口地址/v1
API_KEY=你的API密钥
API_MODEL=你的模型名称
```

默认最终请求地址是：

```text
API_BASE_URL + /chat/completions
```

如果服务商给的是完整地址，例如 `https://example.com/v1/chat/completions`，可直接把完整地址填入 `API_BASE_URL`。

非标准鉴权也可以配置：

```dotenv
API_KEY_HEADER=X-API-Key
API_KEY_PREFIX=
API_EXTRA_HEADERS_JSON={"X-App-Id":"your-app-id"}
```

真实 API Key 只能放在 `.env` 或系统环境变量中。`.env` 已被 `.gitignore` 忽略。

填写后先单独检查 API：

```powershell
python check_api.py
```

## 第 3 步：准备知识库

把资料放到 `docs/`。目前已经附带 Python、Java/JVM、算法、操作系统、网络、数据库、Git 和 STAR 行为面试示例。

建议每个问题使用下面的 Markdown 结构：

```markdown
## 什么是 TCP 三次握手？

这里填写准确、完整的参考答案。
```

修改、增加或删除知识库文件后，都需要重新运行入库脚本。

## 第 4 步：建立本地索引

```powershell
python ingest.py
```

成功后会生成 `data/rag_index.json`。这个文件可随时重新生成，不包含 API Key。

可调整切分参数：

```powershell
python ingest.py --chunk-size 700 --chunk-overlap 100
```

## 第 5 步：运行

浏览器版本：

```powershell
python web.py
```

打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

也可以执行一键脚本，它会先重建索引再启动网页：

```powershell
.\start.ps1
```

命令行版本：

```powershell
python query.py
```

## 第 6 步：测试

测试不会调用真实 API：

```powershell
python -m unittest discover -s tests -v
```

## 常见问题

### API 返回 401 或 403

检查 `API_KEY`、鉴权头和前缀。大多数兼容接口使用：

```dotenv
API_KEY_HEADER=Authorization
API_KEY_PREFIX=Bearer
```

### API 返回 404

检查最终地址是否正确。默认会在 `API_BASE_URL` 后追加 `/chat/completions`。

### 提示响应格式不兼容

项目默认读取：

```json
{"choices":[{"message":{"content":"回答内容"}}]}
```

如果你的 API 使用其他响应结构，需要在 `app/api_client.py` 的 `_extract_content` 中增加适配。

### 检索结果不准确

先补充更完整的知识库内容，再尝试增大 `RAG_TOP_K`。每次修改文档后记得重新执行 `python ingest.py`。

## 项目结构

```text
ai_interviewer/
├── app/                 核心配置、检索、API 和问答逻辑
├── docs/                本地知识库
├── tests/               离线自动化测试
├── web/                 浏览器界面
├── ingest.py            构建知识库索引
├── check_api.py         检查自有 API 连通性
├── query.py             命令行问答
├── web.py               网页服务
├── start.ps1            Windows 一键启动
└── .env.example         API 配置模板
```
