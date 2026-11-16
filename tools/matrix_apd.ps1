# matrix_apd.ps1 — AddPrinterDriverEx 参数组合实验, 收集错误码定位 0x2 来源
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnMx {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct DRIVER_INFO_3W {
        public uint cVersion;
        public string pName;
        public string pEnvironment;
        public string pDriverPath;
        public string pDataFile;
        public string pConfigFile;
        public string pHelpFile;
        public string pDependentFiles;
        public string pDefaultDataType;
        public string pszzMonitorName;
    }
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool AddPrinterDriverEx(string pName, uint Level, IntPtr pDriverInfo, uint dwFlags);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool DeletePrinterDriverEx(string pName, string pEnvironment, string pDriverName, uint dwDeleteFlag, uint dwVersionNum);
}
'@
Add-Type -TypeDefinition $code

$d3 = 'C:\Windows\System32\spool\drivers\x64\3'
if (-not (Test-Path "$d3\UNIDRV.DLL")) { throw 'UNIDRV.DLL 缺' }
if (-not (Test-Path "$d3\LJ2405D.gpd")) { throw 'LJ2405D.gpd 缺' }

$combos = @(
    @{ tag='A: 绝对路径 env=x64 flags=9(COPY_ALL|WARNED)'; abs=$true; env='Windows x64'; flags=(1 -bor 8) },
    @{ tag='B: 相对名 env=null flags=9';                   abs=$false; env=$null;        flags=(1 -bor 8) },
    @{ tag='C: 相对名 env=x64 flags=3(COPY_ALL|FROMDIR)';  abs=$false; env='Windows x64'; flags=(1 -bor 2 -bor 8) },
    @{ tag='D: 相对名 env=x64 flags=8(WARNED)';            abs=$false; env='Windows x64'; flags=8 }
)

$seq = 0
foreach ($c in $combos) {
    $seq++
    $name = "MxT$seq LJ2405D"
    [void][PrnMx]::DeletePrinterDriverEx($null, $c.env, $name, 0x1, 0)   # 清理残留(忽略失败)

    $info = New-Object PrnMx+DRIVER_INFO_3W
    $info.cVersion = 3
    $info.pName = $name
    $info.pEnvironment = $c.env
    if ($c.abs) {
        $info.pDriverPath = "$d3\UNIDRV.DLL"
        $info.pDataFile = "$d3\LJ2405D.gpd"
        $info.pConfigFile = "$d3\UNIDRVUI.DLL"
        $info.pHelpFile = "$d3\UNIDRV.HLP"
        $info.pDependentFiles = "$d3\LJ2405D.gpd`0$d3\UNIDRV.DLL`0$d3\UNIDRVUI.DLL`0$d3\UNIRES.DLL`0$d3\UNIDRV.HLP`0"
    } else {
        $info.pDriverPath = 'UNIDRV.DLL'
        $info.pDataFile = 'LJ2405D.gpd'
        $info.pConfigFile = 'UNIDRVUI.DLL'
        $info.pHelpFile = 'UNIDRV.HLP'
        $info.pDependentFiles = 'LJ2405D.gpd`0UNIDRV.DLL`0UNIDRVUI.DLL`0UNIRES.DLL`0UNIDRV.HLP`0'
    }
    $info.pDefaultDataType = $null
    $info.pszzMonitorName = $null

    $ptr = [Runtime.InteropServices.Marshal]::AllocHGlobal(1024)
    [Runtime.InteropServices.Marshal]::StructureToPtr($info, $ptr, $false)
    $ok = [PrnMx]::AddPrinterDriverEx($null, 3, $ptr, $c.flags)
    $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    [Runtime.InteropServices.Marshal]::FreeHGlobal($ptr)
    if ($ok) { Write-Host ("[{0}] RESULT=SUCCESS" -f $c.tag) }
    else {
        $e = [System.ComponentModel.Win32Exception]::new($err)
        Write-Host ("[{0}] FAIL 0x{1:X8} {2}" -f $c.tag, $err, $e.Message)
    }
}
Get-WinEvent -LogName 'Microsoft-Windows-PrintService/Admin' -MaxEvents 6 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -like '*MxT*' } |
    ForEach-Object { Write-Host ("LOG {0} #{1}: {2}" -f $_.TimeCreated, $_.Id, ($_.Message -replace "`r`n", ' ')) }
