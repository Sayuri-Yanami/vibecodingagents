$ErrorActionPreference = "Stop"

Write-Host "步骤 1/2：构建本地客服知识库索引"
python ingest.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "步骤 2/2：启动网页 AI 客服"
python web.py
