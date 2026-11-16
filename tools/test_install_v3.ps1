# test_install_v3.ps1 — v3 Unidrv 数据驱动运行期验证
# AddPrinterDriverEx(level3, cVersion=3) 无签名直装 → Add-Printer → 测试页 → out.prn 抓流
$gpd = 'E:\Deepseek\lj2400woa\build\v3\LJ2405D.gpd'
$d3 = 'C:\Windows\System32\spool\drivers\x64\3'
$model = 'LJ2405D'
$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'

foreach ($n in 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIDRV.HLP', 'UNIRES.DLL', 'STDNAMES.GPD', 'MSXPSINC.GPD') {
    if (-not (Test-Path "$d3\$n")) { throw "x64\3 缺 $n" }
}
Copy-Item $gpd "$d3\$model.gpd" -Force
Write-Host "[1] LJ2405D.gpd 已放 $d3 (unidrv 组件全在)"

$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnV3 {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct DRIVER_INFO_3W {
        public uint cVersion;
        public string pName;
        public string pEnvironment;
        public string pDriverPath;
        public string pDataFile;
        public string pConfigFile;
        public string pHelpFile;
        public string pDependentFiles;
        public string pDefaultDataType;
        public string pszzMonitorName;
    }
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool AddPrinterDriverEx(string pName, uint Level, IntPtr pDriverInfo, uint dwFlags);
}
'@
Add-Type -TypeDefinition $code

$null = New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports' -Name $outprn -Value '' -PropertyType String -Force
Restart-Service Spooler -Force
Start-Sleep 2
Remove-Item $outprn -ErrorAction SilentlyContinue

$info = New-Object PrnV3+DRIVER_INFO_3W
$info.cVersion = 3
$info.pName = "Lenovo $model"
$info.pEnvironment = 'Windows x64'   # 环境名; 相对名由 spooler 从目标目录 x64\3 解析
$info.pDriverPath = 'C:\Windows\System32\spool\drivers\x64\3\UNIDRV.DLL'    # 相对名, spooler 从 pEnvironment 目录复制
$info.pDataFile = 'C:\Windows\System32\spool\drivers\x64\3\LJ2405D.gpd'
$info.pConfigFile = 'C:\Windows\System32\spool\drivers\x64\3\UNIDRVUI.DLL'
$info.pHelpFile = 'C:\Windows\System32\spool\drivers\x64\3\UNIDRV.HLP'
$d3 = "C:\Windows\System32\spool\drivers\x64\3"; $info.pDependentFiles = "$d3\LJ2405D.gpd`0$d3\UNIDRV.DLL`0$d3\UNIDRVUI.DLL`0$d3\UNIRES.DLL`0$d3\UNIDRV.HLP`0$d3\STDNAMES.GPD`0"
$info.pDefaultDataType = $null
$info.pszzMonitorName = $null

$size = [Runtime.InteropServices.Marshal]::SizeOf([type][PrnV3+DRIVER_INFO_3W])
$ptr = [Runtime.InteropServices.Marshal]::AllocHGlobal($size + 256)
[Runtime.InteropServices.Marshal]::StructureToPtr($info, $ptr, $false)
$flags = 0x00000008    # APD_INSTALL_WARNED_DRIVER
$ok = [PrnV3]::AddPrinterDriverEx($null, 3, $ptr, $flags)
$err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
[Runtime.InteropServices.Marshal]::FreeHGlobal($ptr)
if (-not $ok) {
    $e = [System.ComponentModel.Win32Exception]::new($err)
    Write-Host "[2] AddPrinterDriverEx FAILED: $($e.Message) (0x$('{0:X8}' -f $err))"
    exit 1
}
Write-Host "[2] AddPrinterDriverEx OK: v3 驱动 Lenovo $model 已注册"

if (Get-PrinterDriver -Name "Lenovo $model" -ErrorAction SilentlyContinue) {
    Get-PrinterDriver -Name "Lenovo $model" | Format-List Name,DriverPath,DataFile,ConfigFile | Out-String
}
if (Get-Printer -Name 'LJWoATest' -ErrorAction SilentlyContinue) { Remove-Printer 'LJWoATest'; Start-Sleep 1 }
try {
    Add-Printer -Name 'LJWoATest' -DriverName "Lenovo $model" -PortName $outprn -ErrorAction Stop
    Write-Host "[3] Add-Printer OK (v3 数据驱动解析 GPD 通过)"
} catch {
    Write-Host "[3] Add-Printer FAILED: $_"
    exit 2
}
Start-Sleep 1
Write-Host "[4] 打印测试页"
& rundll32 printui.dll,PrintUIEntry /k /n 'LJWoATest'
Start-Sleep 6
if (Test-Path $outprn) {
    Write-Host "[5] out.prn 已生成: $((Get-Item $outprn).Length) 字节"
} else {
    Write-Host "[5] out.prn 未生成"
    Get-PrintJob -PrinterName 'LJWoATest' -ErrorAction SilentlyContinue | Format-List | Out-String
}
