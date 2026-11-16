# variant_runner.ps1 — M1 键 4 变体: 定位 0x3EB 的键值根因
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnQ5 {
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
$min = 'E:\Deepseek\lj2400woa\build\min'
$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'
$inf = 'E:\Deepseek\lj2400woa\build\v3\LJ2405V3.INF'
# V4 用: 含 "Vx1 Test" 模型行的 INF
$v4inf = 'E:\Deepseek\lj2400woa\build\min\M1INF.INF'
@'
[Version]
Signature="$Windows NT$"
Provider=%Lenovo%
ClassGUID={4D36E979-E325-11CE-BFC1-08002BE10318}
Class=Printer
DriverVer=01/01/2025,1.0.0.0

[Manufacturer]
%Lenovo%=Lenovo

[Lenovo]
"Vx1 Test" = M1.Install

[M1.Install]
CopyFiles=@MINT.gpd
DataFile=MINT.gpd
DataSection=UNIDRV_DATA
Include=ntprint.inf
Needs=UNIDRV.OEM

[DestinationDirs]
DefaultDestDir=66000

[Strings]
Lenovo="Lenovo"
'@ | Set-Content -Path $v4inf -Encoding Unicode

$null = New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports' -Name $outprn -Value '' -PropertyType String -Force
Copy-Item "$min\MINT.gpd" "$d3\MINT.gpd" -Force

function New-MxKey {
    param([string]$name, [bool]$withInf, [bool]$withMonitor, [string]$infPath)
    $key = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\$name"
    if (Test-Path $key) { Remove-Item $key -Recurse -Force }
    New-Item $key -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Dependent Files' -Value @('MINT.gpd', 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIRES.DLL', 'UNIDRV.HLP', 'STDNAMES.GPD') -PropertyType MultiString -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Configuration File' -Value 'UNIDRVUI.DLL' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Data File' -Value 'MINT.gpd' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Driver' -Value 'UNIDRV.DLL' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Help File' -Value 'UNIDRV.HLP' -PropertyType String -Force | Out-Null
    if ($withMonitor) { New-ItemProperty -Path $key -Name 'Monitor' -Value '' -PropertyType String -Force | Out-Null }
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
    if ($withInf) { New-ItemProperty -Path $key -Name 'InfPath' -Value $infPath -PropertyType String -Force | Out-Null }
    New-ItemProperty -Path $key -Name 'PrinterDriverAttributes' -Value 5 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $key -Name 'LastServicedBuild' -Value 19045 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $key -Name 'CoreDependencies' -Value @() -PropertyType MultiString -Force | Out-Null
    New-ItemProperty -Path $key -Name 'DriverDate' -Value '01/01/2025' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'DriverVersion' -Value '1.0.0.0' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'MinInboxDriverVerDate' -Value '01/01/1601' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'MinInboxDriverVerVersion' -Value '0.0.0.0' -PropertyType String -Force | Out-Null
}

function Test-Add {
    param([string]$tag, [string]$name)
    Restart-Service Spooler -Force
    Start-Sleep 2
    $inf2 = New-Object PrnQ5+PRINTER_INFO_2W
    $inf2.pPrinterName = 'LJBiTest'
    $inf2.pPortName = $outprn
    $inf2.pDriverName = $name
    $inf2.pPrintProcessor = 'winprint'
    $inf2.pDatatype = 'RAW'
    $inf2.Attributes = 4
    $h = [PrnQ5]::AddPrinter($null, 2, [ref]$inf2)
    if ($h -eq [IntPtr]::Zero) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        $e = [System.ComponentModel.Win32Exception]::new($err)
        Write-Host ("[{0}] FAIL 0x{1:X8} {2}" -f $tag, $err, $e.Message)
    } else {
        [void][PrnQ5]::ClosePrinter($h)
        Write-Host ("[{0}] AddPrinter OK" -f $tag)
    }
}

New-MxKey -name 'Vx1 Test' -withInf $false -withMonitor $false -infPath ''
Test-Add -tag 'V1: 无InfPath无Monitor' -name 'Vx1 Test'

New-MxKey -name 'Vx2 Test' -withInf $true -withMonitor $false -infPath $inf
Test-Add -tag 'V2: InfPath=原INF' -name 'Vx2 Test'

New-MxKey -name 'Vx3 Test' -withInf $false -withMonitor $true -infPath ''
Test-Add -tag 'V3: 无InfPath+空Monitor' -name 'Vx3 Test'

New-MxKey -name 'Vx4 Test' -withInf $true -withMonitor $false -infPath $v4inf
Test-Add -tag 'V4: InfPath=含模型行INF' -name 'Vx4 Test'
