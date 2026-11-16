# fix_mint.ps1 — 修 MINT.gpd 的 %% 转义重测 + unishare.gpd 已知好品对照
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnQ7 {
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

# 1. 修 MINT.gpd: 单 % -> %% (GPD 字面 % 转义)
$t = [System.IO.File]::ReadAllText("$d3\MINT.gpd", [System.Text.Encoding]::Unicode)
$n = ([regex]::Matches($t, '<1B>%-12345X')).Count
$t = $t.Replace('<1B>%-12345X', '<1B>%%-12345X')
[System.IO.File]::WriteAllText("$d3\MINT.gpd", $t, [System.Text.Encoding]::Unicode)
Write-Host "[1] MINT.gpd 修复 $n 处 %-12345X -> %%-12345X"

# 2. 重测 Vx1 Test (键已在, Data File=MINT.gpd)
Restart-Service Spooler -Force
Start-Sleep 2
$inf2 = New-Object PrnQ7+PRINTER_INFO_2W
$inf2.pPrinterName = 'LJBiFix'
$inf2.pPortName = $outprn
$inf2.pDriverName = 'Vx1 Test'
$inf2.pPrintProcessor = 'winprint'
$inf2.pDatatype = 'RAW'
$inf2.Attributes = 4
$h = [PrnQ7]::AddPrinter($null, 2, [ref]$inf2)
if ($h -eq [IntPtr]::Zero) {
    $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $e = [System.ComponentModel.Win32Exception]::new($err)
    Write-Host ("[2] MINT修复版 FAIL 0x{0:X8} {1}" -f $err, $e.Message)
} else {
    [void][PrnQ7]::ClosePrinter($h)
    Write-Host "[2] MINT修复版 AddPrinter OK — 根因=%%转义丢失"
}

# 3. unishare.gpd 已知好品对照 (新键 MxUsh)
$key = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\MxUsh"
if (Test-Path $key) { Remove-Item $key -Recurse -Force }
New-Item $key -Force | Out-Null
New-ItemProperty -Path $key -Name 'Dependent Files' -Value @('unishare.gpd', 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIRES.DLL', 'STDNAMES.GPD') -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Configuration File' -Value 'UNIDRVUI.DLL' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Data File' -Value 'unishare.gpd' -PropertyType String -Force | Out-Null
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
Restart-Service Spooler -Force
Start-Sleep 2
$inf3 = New-Object PrnQ7+PRINTER_INFO_2W
$inf3.pPrinterName = 'LJUsh'
$inf3.pPortName = $outprn
$inf3.pDriverName = 'MxUsh'
$inf3.pPrintProcessor = 'winprint'
$inf3.pDatatype = 'RAW'
$inf3.Attributes = 4
$h = [PrnQ7]::AddPrinter($null, 2, [ref]$inf3)
if ($h -eq [IntPtr]::Zero) {
    $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $e = [System.ComponentModel.Win32Exception]::new($err)
    Write-Host ("[3] unishare对照 FAIL 0x{0:X8} {1}" -f $err, $e.Message)
} else {
    [void][PrnQ7]::ClosePrinter($h)
    Write-Host "[3] unishare.gpd 对照 AddPrinter OK — 管线+unidrv 数据驱动注册方式全通"
}
