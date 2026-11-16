# loadtest.ps1 — 逐个 LoadLibrary unidrv 组件, 定位加载失败点
$code = @'
using System;
using System.Runtime.InteropServices;
public class Ld {
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern IntPtr LoadLibrary(string lpFileName);
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern IntPtr LoadLibraryEx(string lpFileName, IntPtr hFile, uint dwFlags);
}
'@
Add-Type -TypeDefinition $code

$d3 = 'C:\Windows\System32\spool\drivers\x64\3'
foreach ($n in 'UNIRES.DLL', 'UNIDRVUI.DLL', 'UNIDRV.DLL', 'SSCMD.DLL', 'TTFSUB.DLL') {
    $p = "$d3\$n"
    if (-not (Test-Path $p)) { Write-Host ("{0}: 不存在" -f $n); continue }
    $h = [Ld]::LoadLibrary($p)
    if ($h -eq [IntPtr]::Zero) {
        $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
        Write-Host ("{0}: LoadLibrary FAIL err={1}" -f $n, $err)
        # LOAD_WITH_ALTERED_SEARCH_PATH 重试
        $h2 = [Ld]::LoadLibraryEx($p, [IntPtr]::Zero, 0x8)
        if ($h2 -eq [IntPtr]::Zero) {
            $err2 = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
            Write-Host ("{0}: LoadLibraryEx(altered) FAIL err={1}" -f $n, $err2)
        } else { Write-Host ("{0}: LoadLibraryEx(altered) OK" -f $n) }
    } else {
        Write-Host ("{0}: LoadLibrary OK" -f $n)
    }
}
