# cleanup_test.ps1 — 测试环境清理（保守：删我们建的队列/键，恢复 GENIBM9 原版，保留 out.prn artifact）
$keep = 'Microsoft PDF Document Writer', 'Microsoft XPS Document Writer', 'Microsoft Print to PDF', 'Microsoft Software Printer Driver', 'Microsoft enhanced Point and Print compatibility driver', 'Fax', 'SamsungCtrl'

Get-Printer | Where-Object { $keep -notcontains $_.Name -and $_.Name -notmatch '^Samsung' } | ForEach-Object {
    Write-Host ("删队列: " + $_.Name)
    Remove-Printer -Name $_.Name -ErrorAction SilentlyContinue
}

$vr = 'HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3'
Get-ChildItem $vr | Where-Object { $_.PSChildName -notmatch '^Samsung' -and $_.PSChildName -ne 'Generic IBM Graphics 9pin' } | ForEach-Object {
    Write-Host ("删驱动键: " + $_.PSChildName)
    Remove-Item $_.PSPath -Recurse -Force -ErrorAction SilentlyContinue
}

# GENIBM9 恢复原版（DriverStore + x64\3 + BUD 重建）
$dsGpd = 'C:\Windows\System32\DriverStore\FileRepository\prnge001.inf_amd64_5df0a87c00b7bd58\Amd64\GENIBM9.GPD'
$x3Gpd = 'C:\Windows\System32\spool\drivers\x64\3\GENIBM9.GPD'
Copy-Item 'E:\Deepseek\lj2400woa\build\GENIBM9.GPD.orig.bak' $dsGpd -Force
Copy-Item 'E:\Deepseek\lj2400woa\build\GENIBM9.GPD.orig.bak' $x3Gpd -Force
Remove-Item 'C:\Windows\System32\spool\drivers\x64\3\GENIBM9.BUD' -Force -ErrorAction SilentlyContinue

# x64\3 测试 GPD 清理
Get-ChildItem 'C:\Windows\System32\spool\drivers\x64\3' -Filter '*.gpd' -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch '^(unishare|STDNAMES|MSXPSINC|TTFSUB|LOCALE|PJL|PCLXL|P6DISP|TTY)\.gpd$|^(GENIBM9|MSGENCOL|MSGENBW|GBKCHS|GBKTRA|ARABIC|ANSIISO|FINNISH|FRENCH|GERMAN|GREEK|HEBREW|ITALIAN|NORWEG|POLAND|PORTUGE|RUSSIAN|SPANISH|SWEDISH|TURKISH)\.GPD$' } | ForEach-Object {
    Write-Host ("删测试GPD: " + $_.Name)
    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
}
Get-ChildItem 'C:\Windows\System32\spool\drivers\x64\3' -Filter '*.BUD' -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch '^(GENIBM9|unishare|TTY|MSGENCOL|MSGENBW)\.' } | ForEach-Object {
    Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
}

Restart-Service Spooler -Force
Start-Sleep 3
Write-Host '清理完成'
Get-Printer | Select-Object Name | Out-String
