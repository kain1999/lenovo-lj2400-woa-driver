# diag_dc.ps1 — 原生 API 阶梯诊断 GDI handle invalid
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnDiag {
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool OpenPrinter(string pPrinterName, out IntPtr hPrinter, IntPtr pDefault);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool ClosePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern int DocumentProperties(IntPtr hWnd, IntPtr hPrinter, string pDeviceName, IntPtr pDevModeOutput, IntPtr pDevModeInput, int fMode);
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern IntPtr CreateDCW(string lpszDriver, string lpszDevice, string lpszOutput, IntPtr lpInitData);
    [DllImport("gdi32.dll", SetLastError=true)]
    public static extern bool DeleteDC(IntPtr hdc);
}
'@
Add-Type -TypeDefinition $code

function Diag-Queue {
    param([string]$q)
    Write-Host ("=== {0} ===" -f $q)
    $h = [IntPtr]::Zero
    $ok = [PrnDiag]::OpenPrinter($q, [ref]$h, [IntPtr]::Zero)
    if (-not $ok) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Write-Host ("  OpenPrinter FAIL 0x{0:X8}" -f $err)
        return
    }
    Write-Host "  OpenPrinter OK"
    $need = [PrnDiag]::DocumentProperties([IntPtr]::Zero, $h, $q, [IntPtr]::Zero, [IntPtr]::Zero, 0)
    if ($need -lt 0) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Write-Host ("  DocumentProperties(size) FAIL 0x{0:X8}" -f $err)
    } else {
        Write-Host ("  DocumentProperties(size) OK need={0}" -f $need)
    }
    [void][PrnDiag]::ClosePrinter($h)
    $dc = [PrnDiag]::CreateDCW('WINSPOOL', $q, $null, [IntPtr]::Zero)
    if ($dc -eq [IntPtr]::Zero) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Write-Host ("  CreateDC FAIL 0x{0:X8}" -f $err)
    } else {
        Write-Host "  CreateDC OK"
        [void][PrnDiag]::DeleteDC($dc)
    }
}

Diag-Queue 'SamsungCtrl'
Diag-Queue 'G1Ush'
Diag-Queue 'Microsoft Print to PDF'
