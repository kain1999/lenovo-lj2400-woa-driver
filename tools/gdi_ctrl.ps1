# gdi_ctrl.ps1 — GDI 打印对照: SamsungCtrl vs MXDW vs LJBi2
Add-Type -AssemblyName System.Drawing

$font = New-Object System.Drawing.Font('Arial', 12)
$brush = [System.Drawing.Brushes]::Black

function Try-Print {
    param([string]$queue)
    $pd = New-Object System.Drawing.Printing.PrintDocument
    $pd.PrinterSettings.PrinterName = $queue
    $pd.DocumentName = 'ctrl test'
    $h = [System.Drawing.Printing.PrintPageEventHandler]{ param($s, $e) $e.Graphics.DrawString('ctrl', $font, $brush, 50, 50) }
    $pd.add_PrintPage($h)
    try {
        $pd.Print()
        Write-Host ("[{0}] Print OK" -f $queue)
    } catch {
        Write-Host ("[{0}] FAIL: {1}" -f $queue, $_.Exception.InnerException.Message)
    }
    $pd.remove_PrintPage($h)
}

Try-Print 'SamsungCtrl'
Try-Print 'LJBi2'
