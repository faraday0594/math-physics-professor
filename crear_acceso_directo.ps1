$wshell = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop "Profesor MiniMax.lnk"
$shortcut = $wshell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "d:\math teacher\iniciar_profesor.bat"
$shortcut.WorkingDirectory = "d:\math teacher"
$shortcut.Description = "Iniciar Tutor IA de Matematicas y Fisica con MiniMax"
$shortcut.IconLocation = "shell32.dll,23"
$shortcut.Save()
Write-Host "Acceso directo creado en el Escritorio: $shortcutPath"
