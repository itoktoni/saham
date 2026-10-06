@echo off
setlocal
set "HERE=%~dp0"
echo ============================================
echo   Instalasi Screener Saham (portable)
echo ============================================
echo.
where python >nul 2>&1
if errorlevel 1 (
  echo [i] Python tidak terdeteksi di PATH.
  echo     - Pakai "Screener Saham.exe" bila ada ^(tanpa Python^), atau
  echo     - pasang Python 3.8+ lalu jalankan installer ini lagi.
) else (
  echo [v] Python ditemukan.
)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; $t=Join-Path '%HERE%' 'Jalankan Screener.vbs'; $i='%SystemRoot%\System32\shell32.dll,167'; $d=[Environment]::GetFolderPath('Desktop')+'\Screener Saham.lnk'; $s=$w.CreateShortcut($d); $s.TargetPath=$t; $s.WorkingDirectory='%HERE%'; $s.IconLocation=$i; $s.Save(); $sm=[Environment]::GetFolderPath('StartMenu')+'\Programs\Screener Saham.lnk'; $s2=$w.CreateShortcut($sm); $s2.TargetPath=$t; $s2.WorkingDirectory='%HERE%'; $s2.IconLocation=$i; $s2.Save(); Write-Host '[v] Shortcut dibuat: Desktop + Start Menu'"
echo.
echo Selesai. Klik "Screener Saham" di Desktop untuk menjalankan.
echo.
pause
