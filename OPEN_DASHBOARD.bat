@echo off
cd /d "%~dp0"
echo Open http://127.0.0.1:8088/ in your browser. Stop with Ctrl+C.
where py >nul 2>nul
if %errorlevel% equ 0 (
 py -m http.server 8088 --directory website --bind 127.0.0.1
) else (
 python -m http.server 8088 --directory website --bind 127.0.0.1
)
echo If port 8088 is busy, use 8090. See docs\DEPLOYMENT.md.
pause
