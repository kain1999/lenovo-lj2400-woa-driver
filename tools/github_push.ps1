# GitHub 发布脚本（token 仅从环境变量读取，绝不落盘）
# 用法: powershell -File tools\github_push.ps1
# 前置: $env:GITHUB_TOKEN = "<PAT>"（发布后请立即撤销该 token）
param(
    [string]$RepoName = "lenovo-lj2400-woa-driver",
    [string]$RepoDesc = "Lenovo LJ24/LJ26/M74/M76 series printer driver for Windows on ARM (ARM64) + x64 - v4 GPD data driver, installer, printer manager, RE evidence"
)
$ErrorActionPreference = 'Stop'
if (-not $env:GITHUB_TOKEN) { Write-Error "GITHUB_TOKEN 环境变量未设置"; exit 1 }
$tok = $env:GITHUB_TOKEN
$h = @{ Authorization = "token $tok"; 'User-Agent' = 'lj2400-woa-publisher'; Accept = 'application/vnd.github+json' }

# 1. owner
$user = Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $h
$owner = $user.login
Write-Host "owner: $owner"

# 2. 建仓库（存在则跳过）
try {
    Invoke-RestMethod -Uri "https://api.github.com/repos/$owner/$RepoName" -Headers $h | Out-Null
    Write-Host "repo exists: $owner/$RepoName"
} catch {
    Invoke-RestMethod -Method Post -Uri 'https://api.github.com/user/repos' -Headers $h -Body (
        @{ name = $RepoName; description = $RepoDesc; private = $false; auto_init = $true } | ConvertTo-Json
    ) | Out-Null
    Write-Host "repo created: $owner/$RepoName"
}

# 3. 发布清单（WoA 优先的目录结构）
$base = 'E:\Deepseek\lj2400woa'
$files = @()
# 驱动包（WoA 本体）
$files += Get-ChildItem "$base\driver" -File | ForEach-Object { @{ src=$_.FullName; dst="driver/$($_.Name)" } }
# v3 附加包
$files += Get-ChildItem "$base\v3pkg" -File | ForEach-Object { @{ src=$_.FullName; dst="v3pkg-optional-x64/$($_.Name)" } }
# 安装器与管理工具（exe 成品 + 源码）
$files += Get-ChildItem "$base\installer\dist" -File | Where-Object { $_.Name -ne 'build_log.txt' } | ForEach-Object { @{ src=$_.FullName; dst="dist/$($_.Name)" } }
$files += @{ src="$base\installer\Setup\Program.cs"; dst="installer-src/Setup/Program.cs" }
$files += @{ src="$base\installer\Manager\Manager.cs"; dst="installer-src/Manager/Manager.cs" }
$files += @{ src="$base\installer\app.manifest"; dst="installer-src/app.manifest" }
# 工具与生成器
$files += Get-ChildItem "$base\tools" -File | ForEach-Object { @{ src=$_.FullName; dst="tools/$($_.Name)" } }
$files += Get-ChildItem "$base\installer\tools" -File | ForEach-Object { @{ src=$_.FullName; dst="tools/installer-tools/$($_.Name)" } }
# 逆向证据文档
foreach ($d in @("E:\Deepseek\lj2400lin\analysis\capability_matrix.md","E:\Deepseek\lj2400lin\analysis\ppd_extract.json","E:\Deepseek\lj2400lin\analysis\rawtobr3_strings.txt")) {
    if (Test-Path $d) { $n = Split-Path $d -Leaf; $files += @{ src=$d; dst="docs/linux-driver-analysis/$n" } }
}
foreach ($d in @("E:\Deepseek\lj2655win\analysis\capability_matrix.md","E:\Deepseek\lj2655win\analysis\command_tables.txt","E:\Deepseek\lj2655win\analysis\oid_table.txt")) {
    if (Test-Path $d) { $n = Split-Path $d -Leaf; $files += @{ src=$d; dst="docs/win-driver-analysis/$n" } }
}

# 4. 逐文件上传（base64，PUT contents）
$i = 0
foreach ($f in $files) {
    $i++
    if (-not (Test-Path $f.src)) { Write-Host "SKIP(missing): $($f.dst)"; continue }
    $b64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($f.src))
    $body = @{ message = "publish: $($f.dst)"; content = $b64; branch = 'main' } | ConvertTo-Json
    try {
        Invoke-RestMethod -Method Put -Uri "https://api.github.com/repos/$owner/$RepoName/contents/$($f.dst)" -Headers $h -Body $body | Out-Null
        Write-Host "[$i/$($files.Count)] OK: $($f.dst)"
    } catch {
        Write-Host "[$i] FAIL: $($f.dst) -> $($_.Exception.Message)"
    }
}
Write-Host "`n仓库地址: https://github.com/$owner/$RepoName"
Write-Host "安全提醒: 发布完成后请立即在 GitHub Settings -> Developer settings 撤销本次使用的 token。"
