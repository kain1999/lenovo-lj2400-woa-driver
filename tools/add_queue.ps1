# add_queue.ps1 — Win32 AddPrinter 直建 v3 队列(绕过 cmdlet 封装校验)
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnQ {
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
}
'@
Add-Type -TypeDefinition $code

$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'
$model = 'Lenovo LJ2405D'

if (Get-Printer -Name 'LJWoATest' -ErrorAction SilentlyContinue) { Remove-Printer 'LJWoATest'; Start-Sleep 1 }

$inf2 = New-Object PrnQ+PRINTER_INFO_2W
$inf2.pPrinterName = 'LJWoATest'
$inf2.pPortName = $outprn
$inf2.pDriverName = $model
$inf2.pPrintProcessor = 'winprint'
$inf2.pDatatype = 'RAW'
$inf2.Attributes = 0x00000004   # PRINTER_ATTRIBUTE_LOCAL
$inf2.Priority = 0
$inf2.DefaultPriority = 0

$h = [PrnQ]::AddPrinter($null, 2, [ref]$inf2)
if ($h -eq [IntPtr]::Zero) {
    $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    $e = [System.ComponentModel.Win32Exception]::new($err)
    Write-Host "AddPrinter FAILED: $($e.Message) (0x$('{0:X8}' -f $err))"
    exit 1
}
[void][Runtime.InteropServices.Marshal]::FreeHGlobal([IntPtr]::Zero)
Write-Host "AddPrinter OK"
Get-Printer -Name 'LJWoATest' | Format-List Name,DriverName,PortName,Type | Out-String
