# v4bisect_runner.ps1 — v4 unishare 基座 GPD 变体测试
Add-Type -AssemblyName System.Drawing

$ds = 'C:\Windows\System32\DriverStore\FileRepository\prnms003.inf_amd64_1217c52be7f85bdd\Amd64\unishare.gpd'
$x3 = 'C:\Windows\System32\spool\drivers\x64\3\unishare.gpd'
$out4 = 'E:\Deepseek\lj2400woa\build\out4.prn'

foreach ($v in 'V18_note') {
    $src = "E:\Deepseek\lj2400woa\build\v4s\$v.gpd"
    Copy-Item $src $ds -Force
    Copy-Item $src $x3 -Force
    Stop-Service Spooler -Force
    Start-Sleep 1
    Start-Service Spooler
    Start-Sleep 3
    Remove-Item $out4 -ErrorAction SilentlyContinue
    $r = powershell -NoProfile -STA -Command "Add-Type -AssemblyName System.Drawing; `$pd = New-Object System.Drawing.Printing.PrintDocument; `$pd.PrinterSettings.PrinterName = 'LJWoAV4Test'; `$pd.DocumentName = '$v'; `$h = [System.Drawing.Printing.PrintPageEventHandler]{ param(`$s, `$e) `$e.Graphics.DrawString('t', (New-Object System.Drawing.Font('Arial',12)), [System.Drawing.Brushes]::Black, 50, 50) }; `$pd.add_PrintPage(`$h); try { `$pd.Print(); 'PrintOK' } catch { 'FAIL: ' + `$_.Exception.InnerException.Message }; `$pd.remove_PrintPage(`$h)" 2>&1 | Out-String
    Start-Sleep 5
    if (Test-Path $out4) {
        Write-Host ("[$v] OK out4.prn={0} 字节" -f (Get-Item $out4).Length)
    } else {
        $msg = ($r -replace "`r`n", ' ').Trim()
        Write-Host ("[$v] FAIL {0}" -f $msg.Substring(0, [Math]::Min(80, $msg.Length)))
    }
}
