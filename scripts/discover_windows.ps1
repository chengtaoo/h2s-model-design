$ErrorActionPreference = 'SilentlyContinue'
$found = @()
foreach ($app in @('blender', 'bambu-studio', 'BambuStudio', 'openscad', 'python', 'py')) {
    $found += Get-Command $app | ForEach-Object { [pscustomobject]@{source='PATH'; name=$_.Name; path=$_.Source} }
}
$found += Get-Process | Where-Object { $_.ProcessName -match 'bambu|blender|openscad' } | ForEach-Object { [pscustomobject]@{source='process'; name=$_.ProcessName; path=$_.Path} }
foreach ($root in @('HKLM:/Software/Microsoft/Windows/CurrentVersion/Uninstall/*','HKLM:/Software/WOW6432Node/Microsoft/Windows/CurrentVersion/Uninstall/*','HKCU:/Software/Microsoft/Windows/CurrentVersion/Uninstall/*')) {
    $found += Get-ItemProperty $root | Where-Object { $_.DisplayName -match 'Bambu|Blender|OpenSCAD' } | ForEach-Object { [pscustomobject]@{source='registry'; name=$_.DisplayName; path=$_.InstallLocation; icon=$_.DisplayIcon} }
}
foreach ($pattern in @("$env:ProgramFiles/Bambu Studio/bambu-studio.exe", "$env:ProgramFiles/Blender Foundation/Blender*/blender.exe", "$env:LOCALAPPDATA/Programs/Bambu Studio/bambu-studio.exe")) {
    $found += Get-Item $pattern | ForEach-Object { [pscustomobject]@{source='common-path'; name=$_.Name; path=$_.FullName} }
}
ConvertTo-Json -InputObject @($found) -Depth 4
