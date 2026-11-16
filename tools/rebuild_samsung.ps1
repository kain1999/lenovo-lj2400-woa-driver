# rebuild_samsung.ps1 — 重建被误删的 Samsung v3 驱动注册键(全值来自之前 reg.exe dump)
$key = 'HKLM:\SYSTEM\CurrentControlSet\Control\Print\Environments\Windows x64\Drivers\Version-3\Samsung M332x 382x 402x Series'
$dep = @(
    'ssi5muc.dll','ssi5mur.dll','ssi5mf.xml','ssi5mlf.dll','ssi5mum.dll','ssi5mcu.dll','ssi5msc.cts','ssi5msc.dll',
    'ssi5mm1.bmp','ssi5mm2.bmp','ssi5mm3.bmp','ssi5msm.exe','ssi5mlpc.exe','ssi5mpi.exe','ssi5mc.xml','ssi5mp.xml',
    'ssi5mpp.ver','ssi5mimg.cab','ssi5mn.dll','ssi5man.dll','ssi5mei.exe','ssi5meu.exe','ssi5mec.dll','ssi5med.dll',
    'ssi5meu.exe.config','ssi5mstr.cab','ssi5mchm.cab','ssi5mech.cab','ssi5mam.exe','ssi5mDR.exe','ssi5mUA.dll'
)
New-Item $key -Force | Out-Null
New-ItemProperty -Path $key -Name 'Dependent Files'  -Value $dep -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Configuration File' -Value 'ssi5mdu.dll' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Data File' -Value 'ssi5mpp.dll' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Driver' -Value 'ssi5m.dll' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Help File' -Value 'ssi5men.chm' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Monitor' -Value 'ssi5m Langmon' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Datatype' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Previous Names' -Value @() -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Version' -Value 3 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'TempDir' -Value 0 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'Attributes' -Value 2 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'Manufacturer' -Value 'Samsung' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'OEM URL' -Value 'http://www.hp.com/go/samsung' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'HardwareID' -Value 'lptenum\samsungm332x_382x_405e02' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Provider' -Value 'Samsung' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'Print Processor' -Value 'ssi5mPC' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'VendorSetup' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'ColorProfiles' -Value @() -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'Base Driver' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'PrinterDriverID' -Value '' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'App Registration' -Value @() -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'InfPath' -Value 'C:\Windows\System32\DriverStore\FileRepository\ssi5m.inf_amd64_8fd91b25cfab35f5\ssi5m.inf' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'PrinterDriverAttributes' -Value 5 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'LastServicedBuild' -Value 19045 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $key -Name 'CoreDependencies' -Value @() -PropertyType MultiString -Force | Out-Null
New-ItemProperty -Path $key -Name 'DriverDate' -Value '01/29/2022' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'DriverVersion' -Value '3.13.13.0' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'MinInboxDriverVerDate' -Value '01/01/1601' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name 'MinInboxDriverVerVersion' -Value '0.0.0.0' -PropertyType String -Force | Out-Null
Write-Host "[1] Samsung 键已重建"
Restart-Service Spooler -Force
Start-Sleep 2
Get-PrinterDriver | Select-Object Name | Out-String
