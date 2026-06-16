# 长期公网部署说明

这个项目已经准备好部署到 Render、Railway、Fly.io 等长期托管平台。

关键点：

- `.env` 不会上传，API Key 必须填到云平台的 Environment Variables。
- 云平台会提供 `PORT`，项目已支持自动读取。
- 构建阶段执行 `python ingest.py`，自动生成本地知识库索引。
- 启动阶段执行 `python web.py`。

## Render 推荐配置

连接 GitHub 仓库后，Render 会读取 `render.yaml`。

必须在 Render 环境变量中填写：

```dotenv
API_BASE_URL=https://你的接口地址/v1
API_KEY=你的API密钥
API_MODEL=你的模型名称
```

其他变量已经在 `render.yaml` 中给出默认值，可按需修改。

Build Command:

```bash
python ingest.py
```

Start Command:

```bash
python web.py
```

## Railway 推荐配置

Railway 会读取 `railway.json` 和 `nixpacks.toml`。

必须在 Railway Variables 中填写：

```dotenv
API_BASE_URL=https://你的接口地址/v1
API_KEY=你的API密钥
API_MODEL=你的模型名称
```

部署后在 Settings 或 Networking 中生成 Public Domain。

## 永久在线提醒

免费套餐通常会休眠，但公网网址仍然存在；首次访问可能需要等待冷启动。
如果要求真正 24 小时秒开，需要选择付费 Always On 服务或云服务器。
