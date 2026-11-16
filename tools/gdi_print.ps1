# gdi_print.ps1 — PrintDocument GDI 打印 → unidrv 渲染 → out.prn
Add-Type -AssemblyName System.Drawing

$port = 'E:\Deepseek\lj2400woa\build\out.prn'
Remove-Item $port -ErrorAction SilentlyContinue

$pd = New-Object System.Drawing.Printing.PrintDocument
$pd.PrinterSettings.PrinterName = 'LJBi2'
$pd.DocumentName = 'Lenovo LJWoATest'

$font = New-Object System.Drawing.Font('Arial', 12)
$brush = [System.Drawing.Brushes]::Black
$script:page = 0
$handler = [System.Drawing.Printing.PrintPageEventHandler]{
    param($s, $e)
    $script:page++
    $e.Graphics.DrawString("Lenovo LJ2405D render test - page $script:page", $font, $brush, 50, 50)
    $e.Graphics.DrawString('Line 2 for raster command verification', $font, $brush, 50, 90)
    $e.HasMorePages = ($script:page -lt 2)
}
$pd.add_PrintPage($handler)
$pd.Print()
$pd.remove_PrintPage($handler)

Start-Sleep 5
if (Test-Path $port) {
    Write-Host ("out.prn: {0} 字节" -f (Get-Item $port).Length)
} else {
    Write-Host 'out.prn 未生成'
    Get-PrintJob -PrinterName 'LJBi2' -ErrorAction SilentlyContinue | Format-List Name,JobStatus,Size | Out-String
}
