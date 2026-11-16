# v3api_install2.ps1 — level2 精简 + level3 无依赖 双变体
$pkg = 'E:\Deepseek\lj2400woa\build\v3pkg'

$code = @"
using System;
using System.Runtime.InteropServices;
public class PrnDrv2 {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct DRIVER_INFO_2 {
        public uint cVersion;
        [MarshalAs(UnmanagedType.LPWStr)] public string pName;
        [MarshalAs(UnmanagedType.LPWStr)] public string pEnvironment;
        [MarshalAs(UnmanagedType.LPWStr)] public string pDriverPath;
        [MarshalAs(UnmanagedType.LPWStr)] public string pDataFile;
        [MarshalAs(UnmanagedType.LPWStr)] public string pConfigFile;
    }
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true, EntryPoint="AddPrinterDriverExW")]
    public static extern bool AddPrinterDriverEx2(string pName, uint Level, ref DRIVER_INFO_2 pInfo, uint dwFlags);
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct DRIVER_INFO_3 {
        public uint cVersion;
        [MarshalAs(UnmanagedType.LPWStr)] public string pName;
        [MarshalAs(UnmanagedType.LPWStr)] public string pEnvironment;
        [MarshalAs(UnmanagedType.LPWStr)] public string pDriverPath;
        [MarshalAs(UnmanagedType.LPWStr)] public string pDataFile;
        [MarshalAs(UnmanagedType.LPWStr)] public string pConfigFile;
        public IntPtr pDependentFiles;
        public IntPtr pMonitorName;
        public IntPtr pDefaultDataType;
    }
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true, EntryPoint="AddPrinterDriverExW")]
    public static extern bool AddPrinterDriverEx3(string pName, uint Level, ref DRIVER_INFO_3 pInfo, uint dwFlags);
}
"@
if (-not ('PrnDrv2' -as [type])) { Add-Type -TypeDefinition $code }

$f = 0x8000  # APD_INSTALL_WARNED_DRIVER

$d2 = New-Object PrnDrv2+DRIVER_INFO_2
$d2.cVersion = 3
$d2.pName = 'Lenovo LJ2655DN'
$d2.pEnvironment = $null
$d2.pDriverPath = "$pkg\UNIDRV.DLL"
$d2.pDataFile = "$pkg\LJ2655DN.gpd"
$d2.pConfigFile = "$pkg\UNIDRVUI.DLL"
$ok2 = [PrnDrv2]::AddPrinterDriverEx2($null, 2, [ref]$d2, $f)
$e2 = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
Write-Host ("level2 flags=0x8000: ok=$ok2 err=0x{0:X} ({1})" -f $e2, $e2)

$d3 = New-Object PrnDrv2+DRIVER_INFO_3
$d3.cVersion = 3
$d3.pName = 'Lenovo LJ2655DN'
$d3.pEnvironment = $null
$d3.pDriverPath = "$pkg\UNIDRV.DLL"
$d3.pDataFile = "$pkg\LJ2655DN.gpd"
$d3.pConfigFile = "$pkg\UNIDRVUI.DLL"
$d3.pDependentFiles = [IntPtr]::Zero
$d3.pMonitorName = [IntPtr]::Zero
$d3.pDefaultDataType = [IntPtr]::Zero
$ok3 = [PrnDrv2]::AddPrinterDriverEx3($null, 3, [ref]$d3, $f)
$e3 = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
Write-Host ("level3 nodep flags=0x8000: ok=$ok3 err=0x{0:X} ({1})" -f $e3, $e3)
Get-PrinterDriver -Name 'Lenovo LJ2655DN' -ErrorAction SilentlyContinue | Select-Object Name,DriverPath | Out-String
