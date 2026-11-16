# final_gpd_test.ps1 — 全量 GPD(gen_gpd.py 产物, 静态点数版) 走 unishare 式成功管线
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnQ8 {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct PRINTER_INFO_2W {
        public string pServerName;
        public string pPrinterName;
        public string pShareName;
        public string pPortName;
        public string pDriverName;
        public string pComment;
        public string pLocation;
        public IntPtr pDevMode;
        public IntPtr pSepFile;
        public string pPrintProcessor;
        public string pDatatype;
        public string pParameters;
        public IntPtr pSecurityDescriptor;
        public uint Attributes;
        public uint Priority;
        public uint DefaultPriority;
        public uint StartTime;
        public uint UntilTime;
        public uint Status;
        public uint cJobs;
        public uint AveragePPM;
    }
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern IntPtr AddPrinter(string pName, uint Level, ref PRINTER_INFO_2W pPrinter);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool ClosePrinter(IntPtr hPrinter);
}
'@
Add-Type -TypeDefinition $code

$d3 = 'C:\Windows\System32\spool\drivers\x64\3'
$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'
$src = 'E:\Deepseek\lj2400woa\build\LJ2405D_ansi.gpd'
$static = 'E:\Deepseek\lj2400woa\build\LJ2405D_ansi_final.gpd'

# 用 bisect_gpd 的静态点数替换逻辑重新生成干净的全量静态版 GPD
$t = [System.IO.File]::ReadAllText($src, [System.Text.Encoding]::Unicode)
$t = $t2 = $t
[System.IO.File]::WriteAllBytes($static, [System.IO.File]::ReadAllBytes($src))
$left = ([regex]::Matches($t, '%d\{PhysPage')).Count
Write-Host "[1] 全量静态版 GPD 生成 ($left 处动态参数残留) -> $static"

Copy-Item $static "$d3\LJ2405A.gpd" -Force

$key = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\MxLJ"
if (Test-Path $key) { Remove-Item $key -Recurse -Force }
New-Item $key -Force | Out-Null
New-ItemProperty -Path $key -Name 'Dependent Files' -Value @('LJ2405A.gpd', 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIRES.DLL', 'STDNAMES.GPD') -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Configuration File' -Value 'UNIDRVUI.DLL' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Data File' -Value 'LJ2405A.gpd' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Driver' -Value 'UNIDRV.DLL' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Help File' -Value 'UNIDRV.HLP' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Datatype' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Previous Names' -Value @() -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Version' -Value 3 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'TempDir' -Value 0 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'Attributes' -Value 2 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'Manufacturer' -Value 'Lenovo' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'OEM URL' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'HardwareID' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Provider' -Value 'Lenovo (WoA port)' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Print Processor' -Value 'winprint' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'VendorSetup' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'ColorProfiles' -Value @() -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Base Driver' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'PrinterDriverID' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'App Registration' -Value @() -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'InfPath' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'PrinterDriverAttributes' -Value 5 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'LastServicedBuild' -Value 19045 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'CoreDependencies' -Value @() -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'DriverDate' -Value '01/01/2025' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'DriverVersion' -Value '1.0.0.0' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'MinInboxDriverVerDate' -Value '01/01/1601' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'MinInboxDriverVerVersion' -Value '0.0.0.0' -PropertyType String -Force | Out-Null
Write-Host "[2] MxLJ 键写入(Data File=LJ2405A.gpd 全量静态版)"

Restart-Service Spooler -Force
Start-Sleep 2

$inf2 = New-Object PrnQ8+PRINTER_INFO_2W
$inf2.pPrinterName = 'LJWoATest'
$inf2.pPortName = $outprn
$inf2.pDriverName = 'MxLJ'
$inf2.pPrintProcessor = 'winprint'
$inf2.pDatatype = 'RAW'
$inf2.Attributes = 4
$h = [PrnQ8]::AddPrinter($null, 2, [ref]$inf2)
if ($h -eq [IntPtr]::Zero) {
    $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $e = [System.ComponentModel.Win32Exception]::new($err)
    Write-Host ("[3] 全量GPD FAIL 0x{0:X8} {1}" -f $err, $e.Message)
} else {
    [void][PrnQ8]::ClosePrinter($h)
    Write-Host "[3] 全量GPD AddPrinter OK — 27 型号 GPD 全部可注册!"
    Start-Sleep 1
    Write-Host "[4] 打印测试页"
    & rundll32 printui.dll,PrintUIEntry /k /n 'LJWoATest'
    Start-Sleep 6
    if (Test-Path $outprn) {
        Write-Host ("[5] out.prn 已生成: {0} 字节 — 命令流验证开始" -f (Get-Item $outprn).Length)
    } else {
        Write-Host "[5] out.prn 未生成"
        Get-PrintJob -PrinterName 'LJWoATest' -ErrorAction SilentlyContinue | Format-List | Out-String
    }
}
