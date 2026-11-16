# v3api_install.ps1 — 自家未签名 v3 包: AddPrinterDriverEx flags 0x8000 + AddPrinter
$pkg = 'E:\Deepseek\lj2400woa\build\v3pkg'
$x3 = 'C:\Windows\System32\spool\drivers\x64\3'

# 补齐 unidrv 组件(从 x64\3 拷)
foreach ($f in 'UNIDRV.DLL', 'UNIDRVUI.DLL', 'UNIDRV.HLP', 'STDNAMES.GPD', 'LOCALE.GPD', 'MSXPSINC.GPD', 'TTFSUB.GPD') {
    if (Test-Path "$x3\$f") { Copy-Item "$x3\$f" "$pkg\$f" -Force }
}
Copy-Item "$pkg\LJ2655DN.gpd" "$pkg\LJ2655DN.gpd" -Force -ErrorAction SilentlyContinue
Get-ChildItem $pkg | Select-Object Name, Length | Out-String

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class PrintDrv {
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
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool AddPrinterDriverEx(string pName, uint Level, ref DRIVER_INFO_3 pInfo, uint dwFlags);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern IntPtr AddPrinterW(string pName, uint Level, byte[] pPrinter);
    [DllImport("kernel32.dll")]
    public static extern uint GetLastError();
}
"@

$pkgEsc = $pkg.Replace('\', '\\')
$code = @"
using System;
using System.Runtime.InteropServices;
public class PrnAdd {
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct PRINTER_INFO_2 {
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
    public static extern IntPtr AddPrinterW(string pName, uint Level, ref PRINTER_INFO_2 pPrinter);
    [DllImport("winspool.drv", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool AddPrinterDriverExW(string pName, uint Level, ref IntPtr pInfo, uint dwFlags);
}
"@
if (-not ('PrnAdd' -as [type])) { Add-Type -TypeDefinition $code }

# DRIVER_INFO_3: level 3
$di = New-Object PrintDrv+DRIVER_INFO_3
$di.cVersion = 3
$di.pName = 'Lenovo LJ2655DN'
$di.pEnvironment = $null    # null = 本机环境
$di.pDriverPath = "$pkg\UNIDRV.DLL"
$di.pDataFile = "$pkg\LJ2655DN.gpd"
$di.pConfigFile = "$pkg\UNIDRVUI.DLL"
# multi-sz: 双 \0 结尾
$dep = "UNIDRVUI.DLL`0UNIDRV.HLP`0STDNAMES.GPD`0LOCALE.GPD`0MSXPSINC.GPD`0TTFSUB.GPD`0`0"
$depPtr = [System.Runtime.InteropServices.Marshal]::StringToHGlobalUni($dep)
$di.pDependentFiles = $depPtr
$di.pMonitorName = [IntPtr]::Zero
$dtPtr = [System.Runtime.InteropServices.Marshal]::StringToHGlobalUni("RAW`0")
$di.pDefaultDataType = $dtPtr

$APD_INSTALL_WARNED_DRIVER = 0x8000
$ok = [PrintDrv]::AddPrinterDriverEx($null, 3, [ref]$di, $APD_INSTALL_WARNED_DRIVER)
$err = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
Write-Host ("AddPrinterDriverEx level3 flags=0x8000: ok=$ok err=0x{0:X}" -f $err)
if ($ok) {
    $pi = New-Object PrnAdd+PRINTER_INFO_2
    $pi.pPrinterName = 'LJWoAV3Test'
    $pi.pPortName = 'E:\Deepseek\lj2400woa\build\outv3.prn'
    $pi.pDriverName = 'Lenovo LJ2655DN'
    $pi.pPrintProcessor = 'winprint'
    $pi.pDatatype = 'RAW'
    $h = [PrnAdd]::AddPrinterW($null, 2, [ref]$pi)
    $err2 = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
    if ($h -ne [IntPtr]::Zero) { Write-Host 'AddPrinter: OK' } else { Write-Host ("AddPrinter FAIL err=0x{0:X}" -f $err2) }
}
Get-PrinterDriver -Name 'Lenovo LJ2655DN' -ErrorAction SilentlyContinue | Select-Object Name | Out-String
Get-Printer -Name 'LJWoAV3Test' -ErrorAction SilentlyContinue | Select-Object Name,DriverName | Out-String
