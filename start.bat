@echo off
echo ========================================
echo    HỆ THỐNG ĐẶT VÉ XE KHÁCH
echo ========================================
echo.

REM Kiểm tra venv
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Không tìm thấy virtual environment!
    echo Hãy tạo venv trước: python -m venv venv
    pause
    exit /b 1
)

REM Activate venv
call venv\Scripts\activate.bat

echo [1/2] Đang khởi động Server...
start "Bus Booking Server" cmd /k "python server\server.py"

REM Đợi server khởi động
timeout /t 3 /nobreak > nul

echo [2/2] Đang khởi động Client...
start "Bus Booking Client" cmd /k "python client\client.py"

echo.
echo ========================================
echo    ✅ Server và Client đã khởi động!
echo ========================================
echo.
echo - Server: http://localhost:55555 (TCP/UDP)
echo - Client: http://localhost:3000
echo.
echo Nhấn phím bất kỳ để đóng cửa sổ này (server và client vẫn chạy)...
pause > nul

