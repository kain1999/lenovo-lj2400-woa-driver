# samsung_ctrl.ps1 — 干净对照: 已注册 Samsung 驱动直接 AddPrinter
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnQ4 {
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

$outprn = 'E:\Deepseek\lj2400woa\build\samsung_ctrl.prn'
$null = New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Ports' -Name $outprn -Value '' -PropertyType String -Force
Restart-Service Spooler -Force
Start-Sleep 2

Get-PrinterDriver | Select-Object Name,DriverPath | Out-String

$inf2 = New-Object PrnQ4+PRINTER_INFO_2W
$inf2.pPrinterName = 'SamsungCtrl'
$inf2.pPortName = $outprn
$inf2.pDriverName = 'Samsung M332x 382x 402x Series'
$inf2.pPrintProcessor = 'winprint'
$inf2.pDatatype = 'RAW'
$inf2.Attributes = 4
$h = [PrnQ4]::AddPrinter($null, 2, [ref]$inf2)
if ($h -eq [IntPtr]::Zero) {
    $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $e = [System.ComponentModel.Win32Exception]::new($err)
    Write-Host ("Samsung AddPrinter FAIL 0x{0:X8} {1}" -f $err, $e.Message)
} else {
    [void][PrnQ4]::ClosePrinter($h)
    Write-Host "Samsung AddPrinter OK — AddPrinter 层可用, 0x3EB 是我们驱动键/组件的问题"
}
