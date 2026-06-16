# Vibecoding Agents

这个仓库包含两个可运行的 AI 智能体项目：

1. **AI 面试官系统**
   - 位置：仓库根目录
   - 用途：技术面试问答、模拟追问、项目深挖、简历与行为面试训练
   - 本地端口：`8000`

2. **AI 客服系统**
   - 位置：`customer_service_agent/`
   - 用途：电商售后 FAQ、物流、退换货、优惠券、投诉与人工服务引导
   - 本地端口：`8001`

两个项目都使用：

- 本地知识库 RAG
- OpenAI `chat/completions` 兼容 API
- 自有 API Key 配置
- 浏览器聊天界面
- 命令行问答
- 离线测试

真实密钥不要提交到 GitHub。`.env` 已被 `.gitignore` 忽略。

## 项目结构

```text
vibecodingagents/
├── app/                         AI 面试官后端逻辑
├── docs/                        AI 面试官知识库
├── tests/                       AI 面试官测试
├── web/                         AI 面试官网页界面
├── ingest.py                    AI 面试官知识库入库
├── web.py                       AI 面试官网页服务
├── query.py                     AI 面试官命令行
├── check_api.py                 AI 面试官 API 检查
├── render.yaml                  AI 面试官 Render 部署配置
├── Dockerfile                   AI 面试官 Docker 部署配置
└── customer_service_agent/
    ├── app/                     AI 客服后端逻辑
    ├── docs/                    AI 客服知识库
    ├── tests/                   AI 客服测试
    ├── web/                     AI 客服网页界面
    ├── ingest.py                AI 客服知识库入库
    ├── web.py                   AI 客服网页服务
    ├── query.py                 AI 客服命令行
    ├── check_api.py             AI 客服 API 检查
    ├── render.yaml              AI 客服 Render 部署配置
    ├── railway.json             AI 客服 Railway 部署配置
    └── Procfile                 AI 客服通用部署入口
```

## API 配置

两个项目都需要配置自己的模型 API。

面试官项目复制根目录的模板：

```powershell
Copy-Item .env.example .env
```

客服项目复制子目录模板：

```powershell
cd customer_service_agent
Copy-Item .env.example .env
```

至少填写：

```dotenv
API_BASE_URL=https://guaihub.com/v1
API_KEY=你的完整sk密钥
API_MODEL=gpt-5.4-mini
API_CHAT_PATH=/chat/completions
API_KEY_HEADER=Authorization
API_KEY_PREFIX=Bearer
```

配置完成后可检查 API：

```powershell
python check_api.py
```

## 运行 AI 面试官

在仓库根目录执行：

```powershell
python ingest.py
python web.py
```

打开：

```text
http://127.0.0.1:8000
```

也可以使用命令行：

```powershell
python query.py
```

## 运行 AI 客服

进入客服项目目录：

```powershell
cd customer_service_agent
python ingest.py
python web.py
```

打开：

```text
http://127.0.0.1:8001
```

也可以使用命令行：

```powershell
python query.py
```

## 公网部署

### 部署面试官

在 Render 创建 Web Service，选择本仓库根目录。

```text
Build Command: python ingest.py
Start Command: python web.py
```

环境变量：

```text
WEB_HOST=0.0.0.0
API_BASE_URL=https://guaihub.com/v1
API_KEY=你的完整sk密钥
API_MODEL=gpt-5.4-mini
API_CHAT_PATH=/chat/completions
API_KEY_HEADER=Authorization
API_KEY_PREFIX=Bearer
```

### 部署客服

在 Render 创建另一个 Web Service，并设置 Root Directory：

```text
customer_service_agent
```

然后填写：

```text
Build Command: python ingest.py
Start Command: python web.py
```

环境变量同上。客服项目还可以额外配置：

```text
STORE_NAME=你的店铺名称
HUMAN_SERVICE_TEXT=你的人工客服说明
```

## 测试

面试官测试：

```powershell
python -m unittest discover -s tests -v
```

客服测试：

```powershell
cd customer_service_agent
python -m unittest discover -s tests -v
```

测试使用本地模拟 API，不会消耗真实模型额度。

## 两个项目怎么区分

| 项目 | 位置 | 主要用途 | 默认端口 |
| --- | --- | --- | --- |
| AI 面试官 | 根目录 | 技术面试、项目深挖、简历与行为面试 | `8000` |
| AI 客服 | `customer_service_agent/` | 电商售后客服 FAQ 与人工服务引导 | `8001` |

如果只需要提交一个公网网址，部署对应项目即可；如果两个都要展示，需要在 Render 创建两个 Web Service。

