# test_install.ps1 — v4 数据驱动安装验证(AddPrinterDriverEx level6)
# 结构布局以 probe_driver6.ps1 对系统 MXDW 的运行时 dump 为准(x64 144 字节):
#   0 cVersion | 8 pName | 16 pEnvironment | 24 pDriverPath | 32 pDataFile | 40 pConfigFile
#   48 pHelpFile | 56 pDependentFiles(multi-sz) | 64 pDefaultDataType | 72 pszzMonitorName
#   80 dDriverVersion | 88 ftDriverDate(16B) | 104 pszMfgName | 112 pszOEMUrl
#   120 pszHardwareID | 128 pszProvider | 136 pszzPreviousNames
# 封送: IntPtr + StructureToPtr(规避 PSReference 对含 string 结构的 AccessViolation)
# v4 相对名目录不存在(x64\4 是版本戳文件); AddPrinterDriverEx 按 pDataFile 同目录校验 manifest
# RequiredFiles(MXDW 回放实验实证), 故建独立驱动目录, 包文件与全部系统支持件凑齐
$src = 'E:\Deepseek\lj2400woa\driver'
$dst = 'C:\Windows\System32\spool\drivers\LenovoWoA'
$model = 'LJ2405D'
$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'

New-Item $dst -ItemType Directory -Force | Out-Null
$files = @("$src\$model.gpd", "$src\$model-manifest.ini", "$src\$model-pipelineconfig.xml")
foreach ($f in $files) {
    if (-not (Test-Path $f)) { throw "缺文件: $f" }
    Copy-Item $f $dst -Force
}
$support = 'C:\Windows\System32\spool\drivers\x64\3'
foreach ($n in 'UNIRES.DLL', 'STDNAMES.GPD', 'MSXPSINC.GPD', 'STDDTYPE.GDL', 'STDSCHEM.GDL', 'STDSCHMX.GDL', 'TTFSUB.GPD') {
    if (Test-Path "$support\$n") { Copy-Item "$support\$n" $dst -Force }
}
Write-Host "[1] 驱动目录 $dst : $((Get-ChildItem $dst -File | Measure-Object).Count) 个文件"

$printconfig = Get-ChildItem 'C:\Windows\System32\DriverStore\FileRepository\prnms003.inf_amd64_*\Amd64\PrintConfig.dll' | Select-Object -First 1 -ExpandProperty FullName
$unires = 'C:\Windows\System32\spool\drivers\x64\3\UNIRES.DLL'
if (-not (Test-Path $unires)) { throw 'UNIRES.DLL 未找到' }

$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnInst {
    [StructLayout(LayoutKind.Sequential)]
    public struct SYSTEMTIME {
        public ushort wYear, wMonth, wDayOfWeek, wDay, wHour, wMinute, wSecond, wMilliseconds;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode, Pack=8)]
    public struct DRV6 {
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
        public uint dDriverVersion;
        public SYSTEMTIME ftDriverDate;
        public string pszMfgName;
        public string pszOEMUrl;
        public string pszHardwareID;
        public string pszProvider;
        public string pszzPreviousNames;
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

$info = New-Object PrnInst+DRV6
$info.cVersion = 4
$info.pName = "Lenovo $model"
$info.pEnvironment = 'Windows x64'
$info.pDriverPath = "$dst\UNIRES.DLL"
$info.pDataFile = "$dst\$model.gpd"
$info.pConfigFile = $printconfig
$info.pHelpFile = $null
$info.pDependentFiles = "$dst\$model-manifest.ini`0$dst\$model-pipelineconfig.xml`0"
$info.pDefaultDataType = $null
$info.pszzMonitorName = $null
# 80 槽必须为 0: spooler v4 输入路径把它当指针槽解引用, 非 0 即 AV(MXDW 实测该槽=0)
$info.dDriverVersion = 0
$info.ftDriverDate.wYear = 2025
$info.ftDriverDate.wMonth = 1
$info.ftDriverDate.wDay = 1
$info.pszMfgName = 'Lenovo'
$info.pszOEMUrl = $null
$info.pszHardwareID = $null
$info.pszProvider = 'Lenovo (WoA port)'
$info.pszzPreviousNames = $null

$size = [Runtime.InteropServices.Marshal]::SizeOf([type][PrnInst+DRV6])
Write-Host "[*] 结构大小=$size (dump 校准目标 144)"
$ptr = [Runtime.InteropServices.Marshal]::AllocHGlobal($size + 64)
[Runtime.InteropServices.Marshal]::StructureToPtr($info, $ptr, $false)

$flags = 0x00000008    # APD_INSTALL_WARNED_DRIVER
$ok = [PrnInst]::AddPrinterDriverEx($null, 6, $ptr, $flags)
$err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
[Runtime.InteropServices.Marshal]::FreeHGlobal($ptr)
if (-not $ok) {
    $e = [System.ComponentModel.Win32Exception]::new($err)
    Write-Host "[2] AddPrinterDriverEx FAILED: $($e.Message) (0x$('{0:X8}' -f $err))"
    exit 1
}
Write-Host "[2] AddPrinterDriverEx OK: Lenovo $model 已注册"

$existing = Get-Printer -Name 'LJWoATest' -ErrorAction SilentlyContinue
if ($existing) { Remove-Printer 'LJWoATest'; Start-Sleep 1 }
try {
    Add-Printer -Name 'LJWoATest' -DriverName "Lenovo $model" -PortName $outprn -ErrorAction Stop
    Write-Host "[3] Add-Printer OK"
} catch {
    Write-Host "[3] Add-Printer FAILED: $_"
    exit 2
}
Start-Sleep 1
Write-Host "[4] 打印测试页"
& rundll32 printui.dll,PrintUIEntry /k /n 'LJWoATest'
Start-Sleep 5
if (Test-Path $outprn) {
    Write-Host "[5] out.prn 已生成: $((Get-Item $outprn).Length) 字节"
} else {
    Write-Host "[5] out.prn 未生成"
    Get-PrintJob -PrinterName 'LJWoATest' -ErrorAction SilentlyContinue | Format-List | Out-String
}
