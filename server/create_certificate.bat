@echo off
REM Tạo SSL Certificate cho Development
REM Chạy file này để tạo self-signed certificate

echo ========================================
echo Creating SSL Certificate for Development
echo ========================================
echo.

REM Kiểm tra OpenSSL
where openssl >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: OpenSSL khong duoc tim thay!
    echo Vui long cai dat OpenSSL:
    echo 1. Download tu: https://slproweb.com/products/Win32OpenSSL.html
    echo 2. Hoac cai qua chocolatey: choco install openssl
    echo.
    pause
    exit /b 1
)

REM Kiểm tra certificate đã tồn tại
if exist server.crt (
    echo WARNING: server.crt da ton tai!
    echo Ban co muon ghi de? (Y/N)
    set /p OVERWRITE=
    if /i NOT "%OVERWRITE%"=="Y" (
        echo Huy tao certificate.
        pause
        exit /b 0
    )
)

echo Dang tao certificate...
echo.

openssl req -x509 -newkey rsa:4096 -nodes -out server.crt -keyout server.key -days 365 -subj "/CN=localhost"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Certificate da duoc tao thanh cong!
    echo ========================================
    echo Files:
    echo   - server.crt (Certificate)
    echo   - server.key (Private Key)
    echo.
    echo Luu y: Day la self-signed certificate chi dung cho development.
    echo.
) else (
    echo.
    echo ERROR: Khong the tao certificate!
    echo.
)

pause

