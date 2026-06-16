# 公网部署说明

目标：生成一个不依赖本机、随时随地可访问的公网 HTTPS 地址。

## 推荐方式：Render Web Service

选择付费的 Web Service 计划。免费计划可能休眠，不适合“随时随地都能打开”的要求。

### 需要准备

- 一个 GitHub 仓库，仓库内容为本 `ai_interviewer` 项目
- Render 账号
- 你的 API 配置：
  - `API_BASE_URL=https://guaihub.com/v1`
  - `API_KEY=你的完整 sk 密钥`
  - `API_MODEL=gpt-5.4-mini`

### 部署步骤

1. 把 `ai_interviewer` 文件夹上传到 GitHub 仓库。
2. 在 Render 创建 `New Web Service`。
3. 连接刚才的 GitHub 仓库。
4. 如果 Render 没有自动识别，手动填写：

```text
Build Command: python ingest.py
Start Command: python web.py
```

5. 在 Environment 里添加：

```text
WEB_HOST=0.0.0.0
API_BASE_URL=https://guaihub.com/v1
API_KEY=你的完整 sk 密钥
API_MODEL=gpt-5.4-mini
API_CHAT_PATH=/chat/completions
API_KEY_HEADER=Authorization
API_KEY_PREFIX=Bearer
API_TIMEOUT=90
API_TEMPERATURE=0.2
API_MAX_TOKENS=1200
RAG_TOP_K=4
RAG_MIN_SCORE=0.03
```

6. 点击部署，成功后 Render 会给出类似下面的公网地址：

```text
https://ai-interviewer-xxxx.onrender.com
```

这个地址就是可以提交到群里的公网网址。

## 云服务器方式

如果你有阿里云、腾讯云、华为云或其他 Linux 服务器，也可以用 Docker：

```bash
docker build -t ai-interviewer .
docker run -d \
  --name ai-interviewer \
  -p 80:8000 \
  -e WEB_HOST=0.0.0.0 \
  -e API_BASE_URL=https://guaihub.com/v1 \
  -e API_KEY=你的完整sk密钥 \
  -e API_MODEL=gpt-5.4-mini \
  ai-interviewer
```

然后访问：

```text
http://服务器公网IP
```

若要 HTTPS 和域名，需要再配置域名解析和 Nginx/Caddy 反向代理。

