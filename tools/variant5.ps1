# variant5.ps1 — V5/V6: 打印处理器变体 (ssi5mPC vs winprint) + 极简 PRINTER_INFO 变体(level 0)
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnQ6 {
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
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct PRINTER_INFO_0W {
        public string pPrinterName;
        public string pServerName;
        public uint Attributes;
        public uint Status;
        public uint cJobs;
        public uint cTotalJobs;
        public uint cTotalBytes;
        public uint cTotalPages;
        public uint cTotalPagesThrough;
        public uint AveragePPM;
    }
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern IntPtr AddPrinter(string pName, uint Level, ref PRINTER_INFO_2W pPrinter);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern IntPtr AddPrinter(string pName, uint Level, ref PRINTER_INFO_0W pPrinter);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool ClosePrinter(IntPtr hPrinter);
}
'@
Add-Type -TypeDefinition $code

$outprn = 'E:\Deepseek\lj2400woa\build\out.prn'
function Test-Add2 {
    param([string]$tag, [string]$driver, [string]$proc)
    $inf2 = New-Object PrnQ6+PRINTER_INFO_2W
    $inf2.pPrinterName = $tag
    $inf2.pPortName = $outprn
    $inf2.pDriverName = $driver
    $inf2.pPrintProcessor = $proc
    $inf2.pDatatype = 'RAW'
    $inf2.Attributes = 4
    $h = [PrnQ6]::AddPrinter($null, 2, [ref]$inf2)
    if ($h -eq [IntPtr]::Zero) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        $e = [System.ComponentModel.Win32Exception]::new($err)
        Write-Host ("[{0}] FAIL 0x{1:X8} {2}" -f $tag, $err, $e.Message)
    } else {
        [void][PrnQ6]::ClosePrinter($h)
        Write-Host ("[{0}] AddPrinter OK" -f $tag)
    }
}

# V5: 我们 v3 驱动 + Samsung 的打印处理器
Test-Add2 -tag 'LJV5' -driver 'Vx1 Test' -proc 'ssi5mPC'
# V6: Samsung 驱动 + winprint 处理器(反向验证 winprint 可用性)
Test-Add2 -tag 'LJV6' -driver 'Samsung M332x 382x 402x Series' -proc 'winprint'
# V7: Samsung 阱 + 驱动 Datatype RAW2?? 不试. V7: Samsung 队列 + ssi5mPC (再次确认基线)
Test-Add2 -tag 'LJV7' -driver 'Samsung M332x 382x 402x Series' -proc 'ssi5mPC'
