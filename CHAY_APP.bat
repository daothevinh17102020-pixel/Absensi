@echo off
setlocal
chcp 65001 >nul
title Absensi Face Recognition

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay Python trong .venv.
    echo Hay tao moi truong va cai dependency truoc khi chay app.
    echo.
    pause
    exit /b 1
)

echo ================================================
echo   DANG KHOI DONG HE THONG DIEM DANH
echo ================================================
echo Thu muc: %CD%
echo Trinh duyet se mo tai http://127.0.0.1:5000
echo De dung app, nhan Ctrl+C trong cua so nay.
if "%CONFIDENCE_THRESHOLD%"=="" set "CONFIDENCE_THRESHOLD=45"
if "%RECOGNITION_REQUIRED_FRAMES%"=="" set "RECOGNITION_REQUIRED_FRAMES=3"
if "%FACE_MATCH_THRESHOLD%"=="" set "FACE_MATCH_THRESHOLD=0.51"
echo ArcFace can duoc hieu chuan bang FACE_MATCH_THRESHOLD truoc khi tu dong diem danh.
echo.

if /I not "%AUTO_OPEN_BROWSER%"=="0" (
    start "" /b powershell.exe -NoProfile -WindowStyle Hidden -Command ^
        "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:5000'"
)

".venv\Scripts\python.exe" app.py

echo.
echo App da dung. Nhan phim bat ky de dong cua so.
pause >nul
endlocal
