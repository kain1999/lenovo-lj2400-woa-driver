# v3reg_full.ps1 — 全套键值 + CreateDC 诊断
$vr = 'HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\Lenovo LJ2655DN'
$pkg = 'E:\Deepseek\lj2400woa\build\v3pkg'
$x3 = 'C:\Windows\System32\spool\drivers\x64\3'

Copy-Item "$pkg\LJ2655DN.gpd" "$x3\LJ2655DN.gpd" -Force

# 全套值(Samsung 形态)
Set-ItemProperty -Path $vr -Type DWord -Name 'TempDir' -Value 0
Set-ItemProperty -Path $vr -Type DWord -Name 'Attributes' -Value 0x81
Set-ItemProperty -Path $vr -Type String -Name 'Manufacturer' -Value 'Lenovo'
Set-ItemProperty -Path $vr -Type String -Name 'OEM URL' -Value ''
Set-ItemProperty -Path $vr -Type String -Name 'HardwareID' -Value ''
Set-ItemProperty -Path $vr -Type String -Name 'Print Processor' -Value 'winprint'
Set-ItemProperty -Path $vr -Type MultiString -Name 'ColorProfiles' -Value @()
Set-ItemProperty -Path $vr -Type String -Name 'PrinterDriverID' -Value '{7B41A9F0-2655-4C10-9E44-88AB1F3D0001}'
Set-ItemProperty -Path $vr -Type String -Name 'DriverDate' -Value '11|16|2026'
Set-ItemProperty -Path $vr -Type String -Name 'DriverVersion' -Value '1.0.0.1'
Set-ItemProperty -Path $vr -Type DWord -Name 'PrinterDriverAttributes' -Value 0

Stop-Service Spooler -Force
Start-Sleep 1
Start-Service Spooler
Start-Sleep 3

# CreateDC 诊断 P/Invoke
$code = @"
using System;
using System.Runtime.InteropServices;
public class DCdiag {
    [DllImport("gdi32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern IntPtr CreateDCW(string lpszDriver, string lpszDevice, string lpszOutput, IntPtr lpInitData);
    [DllImport("kernel32.dll")]
    public static extern uint GetLastError();
}
"@
if (-not ('DCdiag' -as [type])) { Add-Type -TypeDefinition $code }
$h = [DCdiag]::CreateDCW('WINSPOOL', 'LJWoAV3P1', $null, [IntPtr]::Zero)
$e = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
if ($h -ne [IntPtr]::Zero) { Write-Host "CreateDC OK handle=$h" } else { Write-Host ("CreateDC FAIL err=0x{0:X} ({1})" -f $e, $e) }

# 驱动信息核对
$r = Get-PrinterDriver -Name 'Lenovo LJ2655DN' -ErrorAction SilentlyContinue
if ($r) { $r | Select-Object Name, DriverPath, DataFile, ConfigFile | Format-List | Out-String } else { 'GetPrinterDriver: 未注册' }
