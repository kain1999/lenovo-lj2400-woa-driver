# bisect2_runner.ps1 — 6 变体一轮测完
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnQ9 {
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
$src = 'E:\Deepseek\lj2400woa\build\inc9'
$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'
$null = New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports' -Name $outprn -Value '' -PropertyType String -Force

$cases = @('A14c_replace')
$seq = 0
foreach ($c in $cases) {
    $seq++
    $gpd = "$c.gpd"
    $key = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\Bix$seq"
    if (Test-Path $key) { Remove-Item $key -Recurse -Force }
    New-Item $key -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Dependent Files' -Value @($gpd, 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIRES.DLL', 'STDNAMES.GPD') -PropertyType MultiString -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Configuration File' -Value 'UNIDRVUI.DLL' -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Data File' -Value $gpd -PropertyType String -Force | Out-Null
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
    Copy-Item "$src\$gpd" "$d3\$gpd" -Force
    if (Get-Printer -Name 'LJBi2' -ErrorAction SilentlyContinue) { Remove-Printer 'LJBi2'; Start-Sleep 1 }
    Restart-Service Spooler -Force
    Start-Sleep 2
    $inf2 = New-Object PrnQ9+PRINTER_INFO_2W
    $inf2.pPrinterName = 'LJBi2'
    $inf2.pPortName = $outprn
    $inf2.pDriverName = "Bix$seq"
    $inf2.pPrintProcessor = 'winprint'
    $inf2.pDatatype = 'RAW'
    $inf2.Attributes = 4
    $h = [PrnQ9]::AddPrinter($null, 2, [ref]$inf2)
    if ($h -eq [IntPtr]::Zero) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Write-Host ("[$c] FAIL 0x{0:X8}" -f $err)
    } else {
        [void][PrnQ9]::ClosePrinter($h)
        Write-Host ("[$c] OK")
    }
}
