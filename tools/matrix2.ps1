# matrix2.ps1 — 对照实验: 现成系统 v3 数据 GPD(GENIBM9/TTY) 走同一管线
$code = @'
using System;
using System.Runtime.InteropServices;
public class PrnMx2 {
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
$prn = 'C:\Windows\System32\DriverStore\FileRepository\prnge001.inf_amd64_5df0a87c00b7bd58\Amd64'
Copy-Item "$prn\GENIBM9.GPD" $d3 -Force -ErrorAction SilentlyContinue
Copy-Item "$prn\TTY.GPD" $d3 -Force -ErrorAction SilentlyContinue

$cases = @(
    @{ tag='E: GENIBM9.GPD(系统成品)'; gpd='GENIBM9.GPD' },
    @{ tag='F: TTY.GPD(系统成品)';     gpd='TTY.GPD' }
)
$seq = 5
foreach ($c in $cases) {
    $seq++
    $name = "MxT$seq $($c.gpd)"
    [void][PrnMx2]::DeletePrinterDriverEx($null, 'Windows x64', $name, 0x1, 0)

    $info = New-Object PrnMx2+DRIVER_INFO_3W
    $info.cVersion = 3
    $info.pName = $name
    $info.pEnvironment = 'Windows x64'
    $info.pDriverPath = 'UNIDRV.DLL'
    $info.pDataFile = $c.gpd
    $info.pConfigFile = 'UNIDRVUI.DLL'
    $info.pHelpFile = 'UNIDRV.HLP'
    $info.pDependentFiles = "$($c.gpd)`0UNIDRV.DLL`0UNIDRVUI.DLL`0UNIRES.DLL`0UNIDRV.HLP`0"
    $info.pDefaultDataType = $null
    $info.pszzMonitorName = $null

    $ptr = [Runtime.InteropServices.Marshal]::AllocHGlobal(1024)
    [Runtime.InteropServices.Marshal]::StructureToPtr($info, $ptr, $false)
    $ok = [PrnMx2]::AddPrinterDriverEx($null, 3, $ptr, 9)   # COPY_ALL | WARNED_DRIVER
    $err = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    [Runtime.InteropServices.Marshal]::FreeHGlobal($ptr)
    if ($ok) { Write-Host ("[{0}] RESULT=SUCCESS" -f $c.tag) }
    else {
        $e = [System.ComponentModel.Win32Exception]::new($err)
        Write-Host ("[{0}] FAIL 0x{1:X8} {2}" -f $c.tag, $err, $e.Message)
    }
}
Get-WinEvent -LogName 'Microsoft-Windows-PrintService/Admin' -MaxEvents 8 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -like '*MxT*' } |
    ForEach-Object { Write-Host ("LOG {0} #{1}: {2}" -f $_.TimeCreated, $_.Id, ($_.Message -replace "`r`n", ' ')) }
