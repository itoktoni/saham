@echo off
setlocal
echo Menghapus shortcut "Screener Saham"...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item ([Environment]::GetFolderPath('Desktop')+'\Screener Saham.lnk') -ErrorAction SilentlyContinue; Remove-Item ([Environment]::GetFolderPath('StartMenu')+'\Programs\Screener Saham.lnk') -ErrorAction SilentlyContinue; Write-Host '[v] Shortcut dihapus'"
echo.
pause
