# install_via_printui.ps1 — 用 printui.dll /if 走微软安装逻辑(等价于手动"从磁盘安装"),
# 未签名驱动警告弹窗用 SendKeys 自动确认(默认按钮=仍安装)。
$inf = 'E:\Deepseek\lj2400woa\driver\LJ2400WOA.INF'
$port = 'E:\Deepseek\lj2400woa\build\out.prn'
$model = 'Lenovo LJ2405D'

$null = New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports' -Name $port -Value '' -PropertyType String -Force
Restart-Service Spooler -Force
Start-Sleep 2
Remove-Item 'E:\Deepseek\lj2400woa\build\out.prn' -ErrorAction SilentlyContinue

# 清残留队列
if (Get-Printer -Name 'LJWoATest' -ErrorAction SilentlyContinue) { Remove-Printer 'LJWoATest'; Start-Sleep 1 }

$p = Start-Process rundll32 -ArgumentList @('printui.dll,PrintUIEntry', '/if', '/b', 'LJWoATest',
        '/f', $inf, '/r', $port, '/m', $model) -PassThru
Write-Host "[1] printui 已启动 pid=$($p.Id) — 等待可能的未签名警告弹窗"

Add-Type -AssemblyName System.Windows.Forms
$confirmed = $false
for ($i = 0; $i -lt 12; $i++) {
    Start-Sleep -Milliseconds 900
    if ($p.HasExited) { break }
    # 尝试激活安装相关弹窗并发送 ENTER(默认按钮=仍安装此驱动程序软件)
    foreach ($t in 'Windows 安全中心', '打印驱动程序', '打印机安装', '无法验证') {
        if ([System.Windows.Forms.SendKeys]::SendWait('{ENTER}')) { }
    }
    $ws = New-Object -ComObject WScript.Shell
    foreach ($t in 'Windows 安全中心', '打印驱动程序', '打印机安装', '警告') {
        if ($ws.AppActivate($t)) {
            $ws.SendKeys('{ENTER}')
            $confirmed = $true
            Write-Host "[2] 已自动确认弹窗: $t"
            break
        }
    }
}
Write-Host "[3] 弹窗确认发送完成 (confirmed=$confirmed), printui 退出=$($p.HasExited)"
if (-not $p.HasExited) { $p.WaitForExit(60000) | Out-Null }

Start-Sleep 2
$drv = Get-PrinterDriver -Name $model -ErrorAction SilentlyContinue
if ($drv) {
    Write-Host "[4] 驱动已注册:"
    $drv | Format-List Name,DriverPath,DataFile,ConfigFile,MonitorName | Out-String
} else {
    Write-Host "[4] 驱动未注册 — 打印机状态:"
    Get-Printer -Name 'LJWoATest' -ErrorAction SilentlyContinue | Format-List Name,DriverName,PortName,PrinterStatus | Out-String
}

if (Get-Printer -Name 'LJWoATest' -ErrorAction SilentlyContinue) {
    Write-Host "[5] 打印测试页"
    & rundll32 printui.dll,PrintUIEntry /k /n 'LJWoATest'
    Start-Sleep 5
    if (Test-Path $port) {
        Write-Host "[6] out.prn 已生成: $((Get-Item $port).Length) 字节"
    } else {
        Write-Host "[6] out.prn 未生成"
        Get-PrintJob -PrinterName 'LJWoATest' -ErrorAction SilentlyContinue | Format-List | Out-String
    }
} else {
    Write-Host "[5] 队列未建立"
}
