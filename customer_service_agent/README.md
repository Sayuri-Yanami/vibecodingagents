# AI 客服系统智能体：自有 API + 本地 RAG

本项目根据《AI 客服系统智能体实训方案》中的“电商售后客服”示例落地。它不绑定智谱清言、腾讯元器、DeepSeek 或其他固定厂商，直接使用你自己的 OpenAI `chat/completions` 兼容 API。

已实现：

- 五类本地客服知识库：退换货、物流、产品使用与尺码、优惠券积分与发票、投诉与人工服务。
- 中文本地检索：使用轻量 TF-IDF 和中文字符组合，不下载大型向量模型。
- 自有 API：接口地址、模型、密钥、请求路径、鉴权头和附加参数均可配置。
- 客服约束：严格依据知识库，不编造政策、赔偿、时效或订单状态。
- 情绪识别：检测不满或着急表达，要求模型先同理再给解决步骤。
- 转人工逻辑：用户主动要求，或连续两次未检索到可靠资料时建议人工处理。
- 多轮对话：保留最近 4 轮问答。
- 浏览器界面：快捷问题、来源查看、情绪提示、隐私提醒和转人工按钮。
- 命令行界面：便于调试检索和 API。
- 离线测试：测试不会消耗真实 API。

## 第 0 步：确认知识库范围

PDF 建议电商售后客服至少覆盖：

1. 退换货政策
2. 物流查询
3. 产品使用问题
4. 优惠券和积分
5. 投诉与建议

项目已在 `docs/` 中提供 60 多个实训问答。它们是演示规则，不代表真实平台。正式使用前，请替换为你的店铺政策、商品说明和服务口径。

推荐的知识库格式：

```markdown
## 我收到的商品有破损怎么办？

请在签收后 48 小时内保留外包装并提交照片……
```

每个问题尽量只问一件事，答案控制在 200 字左右，文件统一使用 UTF-8 编码。

## 第 1 步：准备环境

需要 Python 3.10 或更高版本：

```powershell
cd C:\Users\icYanami\Desktop\智能体\customer_service_agent
python --version
```

核心功能只使用 Python 标准库，不需要安装依赖。

如需把 PDF 或 DOCX 放进知识库，可选安装：

```powershell
python -m pip install pypdf python-docx
```

## 第 2 步：配置你自己的 API

复制配置模板：

```powershell
Copy-Item .env.example .env
```

至少填写：

```dotenv
API_BASE_URL=https://你的接口地址/v1
API_KEY=你的API密钥
API_MODEL=你的模型名称
```

默认请求地址为：

```text
API_BASE_URL + /chat/completions
```

如果服务商给的是完整 `/chat/completions` 地址，可以直接填入 `API_BASE_URL`。非标准鉴权或请求参数可配置：

```dotenv
API_KEY_HEADER=X-API-Key
API_KEY_PREFIX=
API_EXTRA_HEADERS_JSON={"X-App-Id":"your-app-id"}
API_EXTRA_BODY_JSON={"top_p":0.9}
```

真实 API Key 只放在 `.env` 或系统环境变量中。`.env` 已被 `.gitignore` 忽略。

先测试 API：

```powershell
python check_api.py
```

## 第 3 步：调整客服业务信息

在 `.env` 中修改：

```dotenv
STORE_NAME=你的店铺名称
HUMAN_SERVICE_TEXT=你的人工客服时间和联系说明
```

不要在知识库或提示词中写无法兑现的赔偿承诺。

## 第 4 步：准备知识库

把 TXT、Markdown、CSV、JSON 文件放入 `docs/`。项目当前结构：

```text
docs/
├── 退换货政策.md
├── 物流查询.md
├── 产品使用与尺码.md
├── 优惠券积分与发票.md
└── 投诉建议与人工服务.md
```

修改、增加或移除知识库文件后，都要重新执行入库。

## 第 5 步：建立本地索引

```powershell
python ingest.py
```

成功后会生成 `data/rag_index.json`。可调整切分参数：

```powershell
python ingest.py --chunk-size 650 --chunk-overlap 80
```

## 第 6 步：运行客服系统

浏览器版本：

```powershell
python web.py
```

打开 [http://127.0.0.1:8001](http://127.0.0.1:8001)。

也可以执行一键脚本，它会先重建知识库再启动网页：

```powershell
.\start.ps1
```

命令行版本：

```powershell
python query.py
```

## 第 7 步：运行测试

测试使用本地假 API，不会请求真实模型：

```powershell
python -m unittest discover -s tests -v
```

## 客服专用逻辑

### 情绪识别

包含“投诉”“生气”“一直没收到”“怎么还没”等表达时，系统会标记用户情绪，并要求模型先表示理解，再给出最短处理路径。

### 转人工

- 用户输入“转人工客服”“找人工”等表达时立即提示人工渠道。
- 第一次没有检索到可靠知识时，要求用户补充信息。
- 连续第二次仍未命中时，自动建议人工处理。

### 多轮对话

前端和命令行默认保留最近 4 轮对话。可通过 `.env` 修改：

```dotenv
HISTORY_TURNS=4
```

### 数据边界

当前项目没有接入真实订单、物流或工单系统，因此不会声称订单已经退款、包裹已经催促或工单已经创建。接入业务系统时，应通过受控 API 查询，并对敏感字段做权限和脱敏处理。

## 常见问题

### API 返回 401 或 403

检查 `API_KEY`、鉴权头和前缀。常见配置：

```dotenv
API_KEY_HEADER=Authorization
API_KEY_PREFIX=Bearer
```

### API 返回 404

检查最终请求地址。默认会在 `API_BASE_URL` 后追加 `/chat/completions`。

### 回答格式不兼容

项目支持以下常见响应：

```json
{"choices":[{"message":{"content":"回答内容"}}]}
```

也支持 `choices[0].text` 和 `output_text`。其他结构可在 `app/api_client.py` 的 `_extract_content` 中适配。

### 检索结果不准确

先补充更具体的 FAQ，再调整：

```dotenv
RAG_TOP_K=4
RAG_MIN_SCORE=0.055
```

每次改动文档后都要重新运行 `python ingest.py`。

## 项目结构

```text
customer_service_agent/
├── app/                 配置、API、检索和客服逻辑
├── data/                自动生成的本地索引
├── docs/                客服 FAQ 知识库
├── tests/               离线自动化测试
├── web/                 浏览器界面
├── check_api.py         自有 API 连通性检查
├── ingest.py            构建知识库索引
├── query.py             命令行客服
├── web.py               网页服务
├── start.ps1            Windows 一键启动
└── .env.example         API 和业务配置模板
```
