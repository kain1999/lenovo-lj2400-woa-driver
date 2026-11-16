# gdi_gen9.ps1 — LJGen9 GDI 打印（替换后 GPD）
Add-Type -AssemblyName System.Drawing

$port = 'E:\Deepseek\lj2400woa\build\out.prn'
Remove-Item $port -ErrorAction SilentlyContinue

$pd = New-Object System.Drawing.Printing.PrintDocument
$pd.PrinterSettings.PrinterName = 'LJGen9'
$pd.DocumentName = 'Lenovo LJWoATest'

$font = New-Object System.Drawing.Font('Arial', 12)
$brush = [System.Drawing.Brushes]::Black
$n = 0
$h = [System.Drawing.Printing.PrintPageEventHandler]{
    param($s, $e)
    $n++
    $e.Graphics.DrawString("Lenovo LJ2405D render test page $n", $font, $brush, 50, 50)
    $e.Graphics.DrawString('Second line for raster verification', $font, $brush, 50, 90)
    $e.HasMorePages = $false
}
$pd.add_PrintPage($h)
$pd.Print()
$pd.remove_PrintPage($h)

Start-Sleep 5
if (Test-Path $port) {
    Write-Host ("out.prn: {0} 字节" -f (Get-Item $port).Length)
} else {
    Write-Host 'out.prn 未生成'
}
