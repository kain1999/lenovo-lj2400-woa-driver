# ============================================================================
# build.ps1 —— LJ2400Setup.exe / LJ2400Manager.exe 编译与打包
# 唯一编译器：C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe（C#5 语法）
# 目标：AnyCPU（WoA/ARM64 与 x64 通用），纯 .NET Framework WinForms，零第三方依赖
# 用法：powershell -ExecutionPolicy Bypass -File tools\build.ps1
# ============================================================================
$ErrorActionPreference = "Stop"

$installerRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)  # ...\lj2400woa\installer
$woaRoot       = Split-Path -Parent $installerRoot                                     # ...\lj2400woa
$dist          = Join-Path $installerRoot "dist"
$manifest      = Join-Path $installerRoot "app.manifest"
$srcSetup      = Join-Path $installerRoot "Setup\Program.cs"
$srcManager    = Join-Path $installerRoot "Manager\Manager.cs"
$driverDir     = Join-Path $woaRoot "driver"
$logPath       = Join-Path $dist "build_log.txt"

# csc.exe 定位（Framework64 优先，Framework 兜底）
$csc = Join-Path $env:SystemRoot "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { $csc = Join-Path $env:SystemRoot "Microsoft.NET\Framework\v4.0.30319\csc.exe" }
if (-not (Test-Path $csc)) { throw "未找到 csc.exe（需要 .NET Framework 4.x）" }

New-Item -ItemType Directory -Force -Path $dist | Out-Null
"==== LJ2400WoA 构建日志 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====" | Out-File -FilePath $logPath -Encoding utf8

function Invoke-Csc {
    param([string]$Out, [string[]]$SourceFiles, [bool]$UseManifest)
    $cscArgs = @("/nologo", "/target:winexe", "/platform:anycpu", "/optimize+", "/out:$Out")
    if ($UseManifest) { $cscArgs += "/win32manifest:$script:manifest" }
    $cscArgs += $SourceFiles
    (& $script:csc @cscArgs 2>&1) | Out-File -FilePath $script:logPath -Append -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw "csc 编译失败（$Out），详见 $script:logPath" }
    "OK -> $Out" | Out-File -FilePath $script:logPath -Append -Encoding utf8
}

try {
    # 1) 编译 Setup（requireAdministrator 清单）与 Manager（默认 asInvoker 清单）
    Invoke-Csc -Out (Join-Path $dist "LJ2400Setup.exe")   -SourceFiles @($srcSetup)   -UseManifest $true
    Invoke-Csc -Out (Join-Path $dist "LJ2400Manager.exe") -SourceFiles @($srcManager) -UseManifest $false

    # 2) 驱动包产物存在（目录里有文件）时一并打包 dist\LJ2400-WoA-bundle.zip；否则跳过并提示「待生成器产出」
    $driverHasFiles = (Test-Path $driverDir) -and ((Get-ChildItem -Path $driverDir -Recurse -File | Measure-Object).Count -gt 0)
    if ($driverHasFiles) {
        $zip = Join-Path $dist "LJ2400-WoA-bundle.zip"
        if (Test-Path $zip) { Remove-Item $zip -Force }
        Compress-Archive -Path (Join-Path $driverDir "*") `
            -DestinationPath $zip -Force
        Compress-Archive -Path (Join-Path $dist "LJ2400Setup.exe"), `
                                 (Join-Path $dist "LJ2400Manager.exe"), `
                                 (Join-Path $dist "README.md") `
            -DestinationPath $zip -Update
        $msg = "打包完成：$zip"
        $msg | Out-File -FilePath $logPath -Append -Encoding utf8
        Write-Host $msg
    }
    else {
        $msg = "驱动包 $driverDir 为空或不存在，跳过打包（待生成器产出）"
        $msg | Out-File -FilePath $logPath -Append -Encoding utf8
        Write-Host $msg
    }

    Write-Host "构建完成：$dist"
    exit 0
}
catch {
    $_.ToString() | Out-File -FilePath $logPath -Append -Encoding utf8
    Write-Host "构建失败：$_"
    exit 1
}
