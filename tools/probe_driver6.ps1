# probe_driver6.ps1 — dump 系统 MXDW 的 DRIVER_INFO_6W 原生布局, 校准 P/Invoke 结构
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnProbe {
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool OpenPrinter(string pPrinterName, out IntPtr hPrinter, IntPtr pDefault);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool GetPrinterDriver(IntPtr hPrinter, string pEnvironment, uint Level, IntPtr pDriverInfo, uint cbBuf, out uint pcbNeeded);
    [DllImport("winspool.drv", SetLastError=true)]
    public static extern bool ClosePrinter(IntPtr hPrinter);
}
'@
Add-Type -TypeDefinition $code

$h = [IntPtr]::Zero
if (-not [PrnProbe]::OpenPrinter('Microsoft Print To PDF', [ref]$h, [IntPtr]::Zero)) {
    throw "OpenPrinter 失败: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
}
$cb = 0
[void][PrnProbe]::GetPrinterDriver($h, 'Windows x64', 6, [IntPtr]::Zero, 0, [ref]$cb)
$buf = [Runtime.InteropServices.Marshal]::AllocHGlobal([int]$cb + 256)
$need = 0
if (-not [PrnProbe]::GetPrinterDriver($h, 'Windows x64', 6, $buf, $cb, [ref]$need)) {
    throw "GetPrinterDriver 失败: $([Runtime.InteropServices.Marshal]::GetLastWin32Error()) (cb=$cb need=$need)"
}
Write-Host "cb=$cb need=$need"
for ($i = 0; $i -lt 14; $i++) {
    $v = [Runtime.InteropServices.Marshal]::ReadInt64($buf, $i * 8)
    Write-Host ("off {0,3}: 0x{1:X16}" -f ($i * 8), $v)
}
Write-Host "--- 字符串槽 ---"
foreach ($off in 8,16,24,32,40,56,64,72,80,104) {
    $p = [Runtime.InteropServices.Marshal]::ReadIntPtr($buf, $off)
    if ($p -ne [IntPtr]::Zero) {
        $s = [Runtime.InteropServices.Marshal]::PtrToStringUni($p)
        Write-Host ("off {0,3} -> '{1}'" -f $off, $s)
    } else {
        Write-Host ("off {0,3} -> NULL" -f $off)
    }
}
$year = [Runtime.InteropServices.Marshal]::ReadInt16($buf, 88)
$month = [Runtime.InteropServices.Marshal]::ReadInt16($buf, 90)
$day = [Runtime.InteropServices.Marshal]::ReadInt16($buf, 92)
Write-Host "SYSTEMTIME@88 = $year-$month-$day"
Write-Host "总字节数 cb=$cb (x64 结构预期 112)"
[void][PrnProbe]::ClosePrinter($h)
