# install_registry.ps1 — 注册表直写注册 v3 Unidrv 数据驱动(绕过 API 校验), 对照 Samsung v3 模板
$gpd = 'E:\Deepseek\lj2400woa\build\v3\LJ2405D.gpd'
$d3 = 'C:\Windows\System32\spool\drivers\x64\3'
$model = 'Lenovo LJ2405D'
$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'
$inf = 'E:\Deepseek\lj2400woa\build\v3\LJ2405V3.INF'

foreach ($n in 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIDRV.HLP', 'UNIRES.DLL', 'STDNAMES.GPD') {
    if (-not (Test-Path "$d3\$n")) { throw "x64\3 缺 $n" }
}
Copy-Item $gpd "$d3\$model.gpd" -Force
Write-Host "[1] LJ2405D.gpd 已就位 $d3"

$key = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\$model"
if (Test-Path $key) { Remove-Item $key -Recurse -Force }
New-Item $key -Force | Out-Null
New-ItemProperty -Path $key -Name 'Dependent Files'      -Value @("$model.gpd", 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIRES.DLL', 'UNIDRV.HLP', 'STDNAMES.GPD') -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Configuration File'   -Value 'UNIDRVUI.DLL'  -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Data File'            -Value "$model.gpd"    -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Driver'               -Value 'UNIDRV.DLL'    -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Help File'            -Value 'UNIDRV.HLP'    -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Monitor'              -Value ''              -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Datatype'             -Value ''              -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Previous Names'       -Value @()             -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Version'              -Value 3               -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'TempDir'              -Value 0               -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'Attributes'           -Value 2               -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'Manufacturer'         -Value 'Lenovo'        -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'OEM URL'              -Value ''              -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'HardwareID'           -Value ''              -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Provider'             -Value 'Lenovo (WoA port)' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Print Processor'      -Value 'winprint'      -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'VendorSetup'          -Value ''              -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'ColorProfiles'        -Value @()             -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Base Driver'          -Value ''              -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'PrinterDriverID'      -Value ''              -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'App Registration'     -Value @()             -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'InfPath'              -Value $inf            -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'PrinterDriverAttributes' -Value 5            -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'LastServicedBuild'    -Value 19045           -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'CoreDependencies'     -Value @()             -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'DriverDate'           -Value '01/01/2025'    -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'DriverVersion'        -Value '1.0.0.0'       -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'MinInboxDriverVerDate'    -Value '01/01/1601' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'MinInboxDriverVerVersion' -Value '0.0.0.0'    -PropertyType String -Force | Out-Null
Write-Host "[2] 注册表键已写入: $key"

$null = New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports' -Name $outprn -Value '' -PropertyType String -Force
Restart-Service Spooler -Force
Start-Sleep 2
Remove-Item $outprn -ErrorAction SilentlyContinue

$drv = Get-PrinterDriver -Name $model -ErrorAction SilentlyContinue
if ($drv) {
    Write-Host "[3] spooler 已接受注册:"
    $drv | Format-List Name,DriverPath,DataFile,ConfigFile,MonitorName | Out-String
} else {
    Write-Host "[3] spooler 未接受 — 打印服务日志:"
    Get-WinEvent -LogName 'Microsoft-Windows-PrintService/Admin' -MaxEvents 4 -ErrorAction SilentlyContinue |
        ForEach-Object { Write-Host ("LOG {0} #{1}: {2}" -f $_.TimeCreated, $_.Id, ($_.Message -replace "`r`n", ' ')) }
    exit 1
}

if (Get-Printer -Name 'LJWoATest' -ErrorAction SilentlyContinue) { Remove-Printer 'LJWoATest'; Start-Sleep 1 }
try {
    Add-Printer -Name 'LJWoATest' -DriverName $model -PortName $outprn -ErrorAction Stop
    Write-Host "[4] Add-Printer OK (GPD 已被 spooler 解析接受)"
} catch {
    Write-Host "[4] Add-Printer FAILED: $_"
    exit 2
}
Start-Sleep 1
Write-Host "[5] 打印测试页"
& rundll32 printui.dll,PrintUIEntry /k /n 'LJWoATest'
Start-Sleep 6
if (Test-Path $outprn) {
    Write-Host "[6] out.prn 已生成: $((Get-Item $outprn).Length) 字节 — 抓流验证开始"
} else {
    Write-Host "[6] out.prn 未生成"
    Get-PrintJob -PrinterName 'LJWoATest' -ErrorAction SilentlyContinue | Format-List | Out-String
}
