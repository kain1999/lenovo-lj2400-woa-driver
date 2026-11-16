# gdi_ladder.ps1 — 三梯度 GDI 打印定位断层
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnL {
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
Add-Type -AssemblyName System.Drawing

$d3 = 'C:\Windows\System32\spool\drivers\x64\3'
$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'
$null = New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports' -Name $outprn -Value '' -PropertyType String -Force

$font = New-Object System.Drawing.Font('Arial', 12)
$brush = [System.Drawing.Brushes]::Black

function Make-Driver {
    param([string]$name, [string]$gpdfile)
    Copy-Item $gpdfile "$d3\$name.gpd" -Force
    $key = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\$name"
    if (Test-Path $key) { Remove-Item $key -Recurse -Force }
    New-Item $key -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Dependent Files' -Value @("$name.gpd", 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIRES.DLL', 'STDNAMES.GPD') -PropertyType MultiString -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Configuration File' -Value 'UNIDRVUI.DLL' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Data File' -Value "$name.gpd" -PropertyType String -Force | Out-Null
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
}

function Make-Queue {
    param([string]$queue, [string]$driver)
    if (Get-Printer -Name $queue -ErrorAction SilentlyContinue) { Remove-Printer $queue; Start-Sleep 1 }
    $inf2 = New-Object PrnL+PRINTER_INFO_2W
    $inf2.pPrinterName = $queue
    $inf2.pPortName = $outprn
    $inf2.pDriverName = $driver
    $inf2.pPrintProcessor = 'winprint'
    $inf2.pDatatype = 'RAW'
    $inf2.Attributes = 4
    $h = [PrnL]::AddPrinter($null, 2, [ref]$inf2)
    if ($h -eq [IntPtr]::Zero) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Write-Host ("[{0}] AddPrinter FAIL 0x{1:X8}" -f $queue, $err)
        return $false
    }
    [void][PrnL]::ClosePrinter($h)
    Write-Host ("[{0}] AddPrinter OK" -f $queue)
    return $true
}

function Try-Print {
    param([string]$queue)
    Remove-Item $outprn -ErrorAction SilentlyContinue
    $pd = New-Object System.Drawing.Printing.PrintDocument
    $pd.PrinterSettings.PrinterName = $queue
    $pd.DocumentName = 'grad test'
    $h = [System.Drawing.Printing.PrintPageEventHandler]{ param($s, $e) $e.Graphics.DrawString('grad', $font, $brush, 50, 50) }
    $pd.add_PrintPage($h)
    try {
        $pd.Print()
        Start-Sleep 4
        if (Test-Path $outprn) {
            Write-Host ("[{0}] GDI OK, out.prn={1} 字节" -f $queue, (Get-Item $outprn).Length)
        } else {
            Write-Host ("[{0}] GDI OK 但 out.prn 未生成" -f $queue)
        }
    } catch {
        Write-Host ("[{0}] GDI FAIL: {1}" -f $queue, $_.Exception.InnerException.Message)
    }
    $pd.remove_PrintPage($h)
}

Restart-Service Spooler -Force
Start-Sleep 2

# 梯度 1: unishare 原文
Make-Driver -name 'Ush1' -gpdfile "$d3\unishare.gpd"
if (Make-Queue -queue 'G1Ush' -driver 'Ush1') { Try-Print 'G1Ush' }

# 梯度 2: A3a (unishare+我们的Resolution+PJL命令)
Make-Driver -name 'B3a' -gpdfile 'E:\Deepseek\lj2400woa\build\inc2\A3a_enname.gpd'
if (Make-Queue -queue 'G2A3a' -driver 'B3a') { Try-Print 'G2A3a' }

# 梯度 3: A14b (全量拼装)
Make-Driver -name 'B14' -gpdfile 'E:\Deepseek\lj2400woa\build\allen\A7_allen.gpd'
if (Make-Queue -queue 'G3A14' -driver 'B14') { Try-Print 'G3A14' }
