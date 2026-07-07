@echo off
title LRC-SMS Automation Launcher
cls

echo =========================================================
echo       HE THONG KICH HOAT TU DONG DO AN LRC-SMS
echo =========================================================
echo.

:: Kiem tra dac quyen Administrator (Bat buoc phai co)
net session >nul 2>&1
if %errorLevel% == 0 goto :isAdmin

:: Neu chua co quyen, yeu cau UAC Bypass
echo [CANH BAO] Thieu dac quyen Administrator he thong!
echo Dang yeu cau Windows tu dong leo thang quyen (UAC Bypass)...
powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:isAdmin
echo [OK] Da ghi nhan quyen cuong che Administrator hien tai.

:: 1. Khoi dong Gateway Server (FastAPI + Uvicorn) trong mot cua so rieng biet
echo [*] Dang khoi dong can cu dieu phoi: Gateway Server (Port 8000)...
start "LRC-SMS Gateway Server" cmd /k "cd /d ""%~dp0webapp"" && uvicorn main:app --host 0.0.0.0 --port 8000"

:: Tre he thong 3 giay dam bao FastAPI da chiem dung thanh con cong 8000
echo [*] Cho dong bo mang luoi trong 3 giay...
timeout /t 3 /nobreak >nul

:: 2. Khoi dong Agent Engine (Chay duoi quyen Administrator ke thua tu file bat)
echo [*] Dang bat luong giam sat ngam: Agent Engine...
start "LRC-SMS Agent Engine" cmd /k "cd /d ""%~dp0agent"" && python agent.py"

echo.
echo =========================================================
echo [THANH CONG] Ca 2 phan he hien dang tu dong tuong tac!
echo [*] Huong dan nghiem thu:
echo   1. Sang may Windows 11 (Admin), mo Chrome/Edge.
echo   2. Truy cap dia chi: http://192.168.1.10:8000
echo   3. Thu nghiem lai luong lenh Sleep/Restart/Shutdown.
echo.
echo [!] De dung toan bo he thong, hay dong cac cua so CMD phu vua bat len.
echo =========================================================
pause