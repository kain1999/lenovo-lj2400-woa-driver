# bisect_runner.ps1 — M1-M5 逐版注册+AddPrinter, 定位 0x3EB 根因
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnQ3 {
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

$null = New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports' -Name $outprn -Value '' -PropertyType String -Force

$cases = @(
    @{ tag='M1 极简';      gpd='MINT.gpd'; key='Mx1 Test' },
    @{ tag='M2 全纸型';    gpd='M2.gpd';   key='Mx2 Test' },
    @{ tag='M3 中文Name';  gpd='M3.gpd';   key='Mx3 Test' },
    @{ tag='M4 全feature'; gpd='M4.gpd';   key='Mx4 Test' },
    @{ tag='M5 +MSXPSINC'; gpd='M5.gpd';   key='Mx5 Test' }
)

foreach ($c in $cases) {
    $model = $c.key
    Copy-Item "$min\$($c.gpd)" "$d3\$($c.gpd)" -Force
    $key = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\$model"
    if (Test-Path $key) { Remove-Item $key -Recurse -Force }
    New-Item $key -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Dependent Files' -Value @("$($c.gpd)", 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIRES.DLL', 'UNIDRV.HLP', 'STDNAMES.GPD') -PropertyType MultiString -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Configuration File' -Value 'UNIDRVUI.DLL' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Data File' -Value "$($c.gpd)" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Driver' -Value 'UNIDRV.DLL' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Help File' -Value 'UNIDRV.HLP' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Monitor' -Value '' -PropertyType String -Force | Out-Null
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
    New-ItemProperty -Path $key -Name 'InfPath' -Value $inf -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'PrinterDriverAttributes' -Value 5 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $key -Name 'LastServicedBuild' -Value 19045 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $key -Name 'CoreDependencies' -Value @() -PropertyType MultiString -Force | Out-Null
    New-ItemProperty -Path $key -Name 'DriverDate' -Value '01/01/2025' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'DriverVersion' -Value '1.0.0.0' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'MinInboxDriverVerDate' -Value '01/01/1601' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'MinInboxDriverVerVersion' -Value '0.0.0.0' -PropertyType String -Force | Out-Null
    Restart-Service Spooler -Force
    Start-Sleep 2
    if (Get-Printer -Name 'LJBiTest' -ErrorAction SilentlyContinue) { Remove-Printer 'LJBiTest'; Start-Sleep 1 }
    $inf2 = New-Object PrnQ3+PRINTER_INFO_2W
    $inf2.pPrinterName = 'LJBiTest'
    $inf2.pPortName = $outprn
    $inf2.pDriverName = $model
    $inf2.pPrintProcessor = 'winprint'
    $inf2.pDatatype = 'RAW'
    $inf2.Attributes = 4
    $h = [PrnQ3]::AddPrinter($null, 2, [ref]$inf2)
    if ($h -eq [IntPtr]::Zero) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        $e = [System.ComponentModel.Win32Exception]::new($err)
        Write-Host ("[{0}] AddPrinter FAIL 0x{1:X8} {2}" -f $c.tag, $err, $e.Message)
    } else {
        [void][PrnQ3]::ClosePrinter($h)
        Write-Host ("[{0}] AddPrinter OK" -f $c.tag)
    }
}
Write-Host '--- 打印服务日志(最近 8 条) ---'
Get-WinEvent -LogName 'Microsoft-Windows-PrintService/Admin' -MaxEvents 8 -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Host ("LOG {0} #{1}: {2}" -f $_.TimeCreated, $_.Id, ($_.Message -replace "`r`n", ' ')) }
