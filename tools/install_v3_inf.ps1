# install_v3_inf.ps1 — printui /if + v3 INF + 未签名弹窗 SendKeys 自动确认
$inf = 'E:\Deepseek\lj2400woa\build\v3\LJ2405V3.INF'
$port = 'E:\Deepseek\lj2400woa\build\out.prn'
$model = 'Lenovo LJ2405D v3'

$null = New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports' -Name $port -Value '' -PropertyType String -Force
Restart-Service Spooler -Force
Start-Sleep 2
Remove-Item 'E:\Deepseek\lj2400woa\build\out.prn' -ErrorAction SilentlyContinue

if (Get-Printer -Name 'LJWoATestV3' -ErrorAction SilentlyContinue) { Remove-Printer 'LJWoATestV3'; Start-Sleep 1 }

Add-Type -AssemblyName System.Windows.Forms
$p = Start-Process rundll32 -ArgumentList @('printui.dll,PrintUIEntry', '/if', '/b', 'LJWoATestV3',
        '/f', $inf, '/r', $port, '/m', $model) -PassThru
Write-Host "[1] printui 已启动 pid=$($p.Id)"

$ws = New-Object -ComObject WScript.Shell
for ($i = 0; $i -lt 14; $i++) {
    Start-Sleep -Milliseconds 800
    if ($p.HasExited) { Write-Host "[2] printui 已退出 (第 $i 轮)"; break }
    foreach ($t in 'Windows 安全中心', '打印机安装', '打印驱动程序', '无法验证', '安装打印机') {
        if ($ws.AppActivate($t)) {
            $ws.SendKeys('{ENTER}')
            Write-Host "[2] 确认弹窗: $t (第 $i 轮)"
            Start-Sleep -Milliseconds 400
            break
        }
    }
}
if (-not $p.HasExited) { $p.WaitForExit(90000) | Out-Null }
Write-Host "[3] printui 退出=$($p.HasExited) 退出码=$($p.ExitCode)"

$drv = Get-PrinterDriver -Name $model -ErrorAction SilentlyContinue
if ($drv) {
    $drv | Format-List Name,DriverPath,DataFile,ConfigFile | Out-String
    if (Get-Printer -Name 'LJWoATestV3' -ErrorAction SilentlyContinue) {
        Write-Host "[4] 打印测试页"
        & rundll32 printui.dll,PrintUIEntry /k /n 'LJWoATestV3'
        Start-Sleep 6
        if (Test-Path $port) { Write-Host "[5] out.prn 已生成: $((Get-Item $port).Length) 字节" }
        else {
            Write-Host "[5] out.prn 未生成"
            Get-PrintJob -PrinterName 'LJWoATestV3' -ErrorAction SilentlyContinue | Format-List | Out-String
        }
    }
} else {
    Write-Host "[4] 驱动未注册"
    Get-WinEvent -LogName 'Microsoft-Windows-PrintService/Admin' -MaxEvents 5 -ErrorAction SilentlyContinue |
        ForEach-Object { Write-Host ("LOG {0} #{1}: {2}" -f $_.TimeCreated, $_.Id, ($_.Message -replace "`r`n", ' ')) }
}
