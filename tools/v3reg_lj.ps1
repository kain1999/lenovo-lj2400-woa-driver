# v3reg_lj.ps1 — 直写注册自家 v3 驱动(ASCII GPD 全能力版) + AddPrinter + 打印
param([string]$Variant = 'P1')

$pkg = 'E:\Deepseek\lj2400woa\build\v3pkg'
$x3 = 'C:\Windows\System32\spool\drivers\x64\3'
$vr = 'HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\Lenovo LJ2655DN'
$drvName = 'Lenovo LJ2655DN'
$queue = "LJWoAV3$Variant"
$gpd = if ($Variant -eq 'P2') { 'LJ2655DN_600.gpd' } else { 'LJ2655DN.gpd' }

# 1. 文件就位(x64\3)
foreach ($f in 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIDRV.HLP', 'STDNAMES.GPD', 'LOCALE.GPD', 'MSXPSINC.GPD', 'TTFSUB.GPD', $gpd) {
    Copy-Item "$pkg\$f" "$x3\$f" -Force
}

# 2. 注册表键(带空格形态 = spooler 读取名)
New-Item -Path $vr -Force | Out-Null
Set-ItemProperty -Path $vr -Type String -Name 'Configuration File' -Value 'UNIDRVUI.DLL'
Set-ItemProperty -Path $vr -Type String -Name 'Data File' -Value $gpd
Set-ItemProperty -Path $vr -Type String -Name 'Driver' -Value 'UNIDRV.DLL'
Set-ItemProperty -Path $vr -Type String -Name 'Help File' -Value 'UNIDRV.HLP'
Set-ItemProperty -Path $vr -Type MultiString -Name 'Dependent Files' -Value @('UNIDRVUI.DLL', 'UNIDRV.HLP', 'STDNAMES.GPD', 'LOCALE.GPD', 'MSXPSINC.GPD', 'TTFSUB.GPD')
Set-ItemProperty -Path $vr -Type String -Name 'Datatype' -Value 'RAW'
Set-ItemProperty -Path $vr -Type String -Name 'Monitor' -Value ''
Set-ItemProperty -Path $vr -Type String -Name 'Provider' -Value 'Lenovo WoA Port'
Set-ItemProperty -Path $vr -Type DWord -Name 'Version' -Value 3

Stop-Service Spooler -Force
Start-Sleep 1
Start-Service Spooler
Start-Sleep 3

# 3. AddPrinter
$code = @"
using System;
using System.Runtime.InteropServices;
public class PrnAdd3 {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct PRINTER_INFO_2 {
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
    public static extern IntPtr AddPrinterW(string pName, uint Level, ref PRINTER_INFO_2 pPrinter);
}
"@
if (-not ('PrnAdd3' -as [type])) { Add-Type -TypeDefinition $code }
$pi = New-Object PrnAdd3+PRINTER_INFO_2
$pi.pPrinterName = $queue
$pi.pPortName = 'E:\Deepseek\lj2400woa\build\outv3.prn'
$pi.pDriverName = $drvName
$pi.pPrintProcessor = 'winprint'
$pi.pDatatype = 'RAW'
$h = [PrnAdd3]::AddPrinterW($null, 2, [ref]$pi)
$e = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
if ($h -ne [IntPtr]::Zero) { Write-Host "AddPrinter $queue OK" } else { Write-Host ("AddPrinter FAIL err=0x{0:X} ({1})" -f $e, $e); exit 1 }

Start-Sleep 2
$out = 'E:\Deepseek\lj2400woa\build\outv3.prn'
Remove-Item $out -ErrorAction SilentlyContinue
$r = powershell -NoProfile -STA -Command "Add-Type -AssemblyName System.Drawing; `$pd = New-Object System.Drawing.Printing.PrintDocument; `$pd.PrinterSettings.PrinterName = '$queue'; `$pd.DocumentName = '$Variant'; `$h = [System.Drawing.Printing.PrintPageEventHandler]{ param(`$s, `$e) `$e.Graphics.DrawString('v3 direct-reg render', (New-Object System.Drawing.Font('Arial',14)), [System.Drawing.Brushes]::Black, 60, 60); `$e.Graphics.DrawLine([System.Drawing.Pens]::Black, 60, 120, 500, 120) }; `$pd.add_PrintPage(`$h); try { `$pd.Print(); 'PrintOK' } catch { 'FAIL: ' + `$_.Exception.InnerException.Message }; `$pd.remove_PrintPage(`$h)" 2>&1 | Out-String
Start-Sleep 5
if (Test-Path $out) {
    Write-Host ("[$Variant] OK outv3.prn={0} 字节" -f (Get-Item $out).Length)
} else {
    Write-Host ("[$Variant] FAIL {0}" -f (($r -replace "`r`n", ' ').Trim()))
}
Copy-Item $out "E:\Deepseek\lj2400woa\build\$Variant.prn" -Force -ErrorAction SilentlyContinue
