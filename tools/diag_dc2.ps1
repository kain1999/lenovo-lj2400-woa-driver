# diag_dc2.ps1 — CreateDC 阶梯诊断(gdi32 CreateDCW)
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnDiag2 {
    [DllImport("gdi32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern IntPtr CreateDCW(string lpszDriver, string lpszDevice, string lpszOutput, IntPtr lpInitData);
    [DllImport("gdi32.dll", SetLastError=true)]
    public static extern bool DeleteDC(IntPtr hdc);
}
'@
Add-Type -TypeDefinition $code

foreach ($q in 'SamsungCtrl', 'G1Ush', 'LJBi2') {
    $dc = [PrnDiag2]::CreateDCW('WINSPOOL', $q, $null, [IntPtr]::Zero)
    if ($dc -eq [IntPtr]::Zero) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Write-Host ("[{0}] CreateDC FAIL 0x{1:X8}" -f $q, $err)
    } else {
        Write-Host ("[{0}] CreateDC OK" -f $q)
        [void][PrnDiag2]::DeleteDC($dc)
    }
}
