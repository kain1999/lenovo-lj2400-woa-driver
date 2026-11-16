# debug_apd.ps1 — 一锤定音实验: MXDW level6 buffer 原样回放 AddPrinterDriverEx
# 期望: 3019(已安装) 或其他错误码 => 调用封装/结构布局正确; AV => 封装本身有错
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnDbg {
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool OpenPrinter(string pPrinterName, out IntPtr hPrinter, IntPtr pDefault);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool GetPrinterDriver(IntPtr hPrinter, string pEnvironment, uint Level, IntPtr pDriverInfo, uint cbBuf, out uint pcbNeeded);
    [DllImport("winspool.drv", SetLastError=true)]
    public static extern bool ClosePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool AddPrinterDriverEx(string pName, uint Level, IntPtr pDriverInfo, uint dwFlags);
}
'@
Add-Type -TypeDefinition $code

$h = [IntPtr]::Zero
[void][PrnDbg]::OpenPrinter('Microsoft Print To PDF', [ref]$h, [IntPtr]::Zero)
$cb = 0
[void][PrnDbg]::GetPrinterDriver($h, 'Windows x64', 6, [IntPtr]::Zero, 0, [ref]$cb)
$buf = [Runtime.InteropServices.Marshal]::AllocHGlobal([int]$cb)
$need = 0
[void][PrnDbg]::GetPrinterDriver($h, 'Windows x64', 6, $buf, $cb, [ref]$need)
[void][PrnDbg]::ClosePrinter($h)
Write-Host "MXDW level6 buffer: $need 字节 (结构 144 + 字符串区)"

$flags = 0x00000008
$ok = [PrnDbg]::AddPrinterDriverEx($null, 6, $buf, $flags)
$err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
if ($ok) {
    Write-Host "RESULT: OK (真装了一个 MXDW 副本?)"
} else {
    $e = [System.ComponentModel.Win32Exception]::new($err)
    Write-Host ("RESULT: FAIL {0} (0x{1:X8})" -f $e.Message, $err)
}
