# bisect_gpd.ps1 — GPD 内容二分: 把 %d{PhysPage*} 动态参数替换为静态点数后重试 AddPrinter
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnQ2 {
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
    public static extern bool DeletePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool ClosePrinter(IntPtr hPrinter);
}
'@
Add-Type -TypeDefinition $code

$d3 = 'C:\Windows\System32\spool\drivers\x64\3'
$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'
$model = 'Lenovo LJ2405D'

$gpdPath = "$d3\$model.gpd"
$t = [System.IO.File]::ReadAllText($gpdPath, [System.Text.Encoding]::Unicode)
$before = ([regex]::Matches($t, '%d\{PhysPage')).Count
# 4 处动态维度(CUSTOM1/2/3 + CustomMediaSize) → 静态 600dpi 点数(A4 上限占位 4960x7016):
$t = $t.Replace('" %d{PhysPageWidth}"X<1B>*c" %d{PhysPageHeight}"Y<1B>*c0P"', '4960X<1B>*c7016Y<1B>*c0P"')

[System.IO.File]::WriteAllText($gpdPath, $t, [System.Text.Encoding]::Unicode)
$after = ([regex]::Matches($t, '%d\{PhysPage')).Count
Write-Host "[1] PhysPage 动态参数: $before -> $after (替换为静态点数)"
# GPD 编码: v3 目录下 GPD 是 UTF-16 LE BOM, PowerShell Unicode 编码 = UTF-16 LE 带 BOM ✓

Restart-Service Spooler -Force
Start-Sleep 2

if (Get-Printer -Name 'LJWoATest' -ErrorAction SilentlyContinue) { Remove-Printer 'LJWoATest'; Start-Sleep 1 }
$inf2 = New-Object PrnQ2+PRINTER_INFO_2W
$inf2.pPrinterName = 'LJWoATest'
$inf2.pPortName = $outprn
$inf2.pDriverName = $model
$inf2.pPrintProcessor = 'winprint'
$inf2.pDatatype = 'RAW'
$inf2.Attributes = 4
$h = [PrnQ2]::AddPrinter($null, 2, [ref]$inf2)
if ($h -eq [IntPtr]::Zero) {
    $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $e = [System.ComponentModel.Win32Exception]::new($err)
    Write-Host "AddPrinter FAILED: $($e.Message) (0x$('{0:X8}' -f $err))"
} else {
    [void][PrnQ2]::ClosePrinter($h)
    Write-Host "AddPrinter OK — GPD 解析通过!"
    Get-Printer -Name 'LJWoATest' | Format-List Name,DriverName,PortName | Out-String
}
