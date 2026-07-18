<#
.SYNOPSIS
  Create backend project skeleton for "芯语智问：EDA 全链路智能学习与实验平台"

.DESCRIPTION
  在当前目录下创建名为 "backend" 的目录结构与占位文件（__init__.py、main.py、README.md 等）。
  保持与之前提供的架构完全一致（包含所有子目录与文件名），并在占位文件中保留 owner 注释 (A/B/C)。

.NOTES
  运行示例:
    powershell -ExecutionPolicy Bypass -File .\create_structure.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = "backend"
Write-Host "Creating project skeleton under .\$root ..."

$dirs = @(
  "$root",
  "$root\alembic\versions",
  "$root\infra\k8s",
  "$root\infra\helm",
  "$root\infra\terraform",
  "$root\infra\deploy",
  "$root\scripts",
  "$root\ci",
  "$root\app",
  "$root\app\config",
  "$root\app\core",
  "$root\app\api",
  "$root\app\api\routers",
  "$root\app\api\openapi",
  "$root\app\domain",
  "$root\app\domain\entities",
  "$root\app\domain\value_objects",
  "$root\app\schemas",
  "$root\app\schemas\pydantic",
  "$root\app\use_cases",
  "$root\app\use_cases\users",
  "$root\app\use_cases\chapters",
  "$root\app\use_cases\progress",
  "$root\app\use_cases\questions",
  "$root\app\use_cases\submissions",
  "$root\app\use_cases\learning_profile",
  "$root\app\use_cases\eda",
  "$root\app\use_cases\rag",
  "$root\app\ports",
  "$root\app\ports\repositories",
  "$root\app\ports\external_services",
  "$root\app\adapters",
  "$root\app\adapters\db",
  "$root\app\adapters\db\mysql",
  "$root\app\adapters\db\redis",
  "$root\app\adapters\repositories",
  "$root\app\adapters\external",
  "$root\app\adapters\external\eda_tool_wrappers",
  "$root\app\services",
  "$root\app\workers",
  "$root\app\tasks",
  "$root\app\utils",
  "$root\tests\unit",
  "$root\tests\integration",
  "$root\tests\e2e",
  "$root\migrations",
  "$root\data\eda_images",
  "$root\data\sample_datasets",
  "$root\docs\api_docs",
  "$root\third_party\llm_playground",
  "$root\third_party\rag_index_store"
)

foreach ($d in $dirs) {
    if (-not (Test-Path -Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        Write-Host "Created directory: $d"
    } else {
        Write-Host "Exists: $d"
    }
}

function New-TextFile($path, $content) {
    $dir = Split-Path -Path $path -Parent
    if (-not (Test-Path -Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    # Use UTF8 without BOM
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
    [System.IO.File]::WriteAllBytes((Resolve-Path $path).Path, $bytes)
    Write-Host "Created file: $path"
}

# Top-level files
New-TextFile "$root\.gitignore" "# Add ignores"
New-TextFile "$root\README.md" @'
# 芯语智问：EDA 全链路智能学习与实验平台 (backend)
Owner mapping:
- A: 用户/章节/进度/认证
- B: 题库/判题/动态出题/学习画像
- C: EDA 工具链/RAG/部署/infra
'@

New-TextFile "$root\Dockerfile" "# Dockerfile placeholder"
New-TextFile "$root\docker-compose.yml" "# docker-compose placeholder"
New-TextFile "$root\requirements.txt" "# requirements placeholder"
New-TextFile "$root\.env.example" "# .env.example placeholder"
New-TextFile "$root\pyproject.toml" "[tool.poetry]\nname = \"eda-platform-backend\"\nversion = \"0.1.0\""

# alembic placeholder
New-TextFile "$root\alembic\env.py" @'
# Alembic env placeholder (owner: C)
'@

# scripts
New-TextFile "$root\scripts\eda_sandbox_prepare.sh" @'
#!/usr/bin/env bash
# EDA sandbox init (owner: C)
echo "Prepare EDA sandbox"
'@

New-TextFile "$root\scripts\ingest_resources.sh" @'
#!/usr/bin/env bash
# Resource ingest script (owner: C)
echo "Ingest resources"
'@

# ci
New-TextFile "$root\ci\github-actions.yml" "# CI workflows (owner: C)"

# app main and common files
New-TextFile "$root\app\main.py" @'
# FastAPI app entrypoint (owner: C)
from fastapi import FastAPI

app = FastAPI(title="EDA Learning Platform")

@app.get("/health")
def health():
    return {"status": "ok"}
'@

# package __init__.py placeholders
$packagePlaces = @(
  "$root\app",
  "$root\app\config",
  "$root\app\core",
  "$root\app\api",
  "$root\app\api\routers",
  "$root\app\domain",
  "$root\app\domain\entities",
  "$root\app\schemas",
  "$root\app\schemas\pydantic",
  "$root\app\use_cases",
  "$root\app\use_cases\users",
  "$root\app\use_cases\chapters",
  "$root\app\use_cases\progress",
  "$root\app\use_cases\questions",
  "$root\app\use_cases\submissions",
  "$root\app\use_cases\learning_profile",
  "$root\app\use_cases\eda",
  "$root\app\use_cases\rag",
  "$root\app\ports",
  "$root\app\ports\repositories",
  "$root\app\ports\external_services",
  "$root\app\adapters",
  "$root\app\adapters\db",
  "$root\app\adapters\db\mysql",
  "$root\app\adapters\db\redis",
  "$root\app\adapters\repositories",
  "$root\app\adapters\external",
  "$root\app\adapters\external\eda_tool_wrappers",
  "$root\app\services",
  "$root\app\workers",
  "$root\app\tasks",
  "$root\app\utils"
)

foreach ($p in $packagePlaces) {
    $initPath = Join-Path $p "__init__.py"
    if (-not (Test-Path -Path $initPath)) {
        New-TextFile $initPath ("# package: $p - add code here. Owner mapping in README.")
    } else {
        Write-Host "Exists file: $initPath"
    }
}

# create example router files with owner tag
New-TextFile "$root\app\api\routers\auth.py" @'
# owner: A - auth endpoints placeholder
from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
def login():
    return {"msg": "login placeholder"}
'@

New-TextFile "$root\app\api\routers\chapters.py" @'
# owner: A - chapters endpoints placeholder
from fastapi import APIRouter

router = APIRouter()
'@

New-TextFile "$root\app\api\routers\questions.py" @'
# owner: B - questions endpoints placeholder
from fastapi import APIRouter

router = APIRouter()
'@

New-TextFile "$root\app\adapters\external\eda_tool_wrappers\yosys_runner.py" @'
# owner: C - wrapper to run yosys (placeholder)
def run_yosys(job):
    return {"result": "ok"}
'@

# create README per top module with owner
New-TextFile "$root\app\api\README.md" @'
API Routers
- owner: A/B/C per submodule
- location: app/api/routers
- purpose: HTTP endpoints; register routers in app/main.py
'@

New-TextFile "$root\app\adapters\README.md" @'
Adapters implement ports and integrate with infra (MySQL, Redis, external services)
- owner: C (infra), A/B implement their repo adapters
'@

# create placeholder tests
New-TextFile "$root\tests\unit\test_placeholder.py" @'
def test_placeholder():
    assert True
'@

Write-Host ""
Write-Host "Skeleton created under .\$root"
Write-Host ""
Write-Host "How to run:"
Write-Host " 1) Open PowerShell in this directory."
Write-Host " 2) If needed, allow script execution for this run:"
Write-Host "      powershell -ExecutionPolicy Bypass -File .\create_structure.ps1"
Write-Host ""
Write-Host "Notes:"
Write-Host " - The script creates .sh files (script placeholders) as plain text so they remain consistent with the original architecture."
Write-Host " - Adjust file contents to real implementations and add licensing/CI secrets as needed."