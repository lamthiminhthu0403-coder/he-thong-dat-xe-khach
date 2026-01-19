#!/bin/bash
# Tạo SSL Certificate cho Development
# Chạy: bash create_certificate.sh

echo "========================================"
echo "Creating SSL Certificate for Development"
echo "========================================"
echo ""

# Kiểm tra OpenSSL
if ! command -v openssl &> /dev/null; then
    echo "ERROR: OpenSSL không được tìm thấy!"
    echo "Vui lòng cài đặt OpenSSL:"
    echo "  - Ubuntu/Debian: sudo apt-get install openssl"
    echo "  - MacOS: brew install openssl"
    echo ""
    exit 1
fi

# Kiểm tra certificate đã tồn tại
if [ -f "server.crt" ]; then
    echo "WARNING: server.crt đã tồn tại!"
    read -p "Bạn có muốn ghi đè? (y/N): " OVERWRITE
    if [[ ! $OVERWRITE =~ ^[Yy]$ ]]; then
        echo "Hủy tạo certificate."
        exit 0
    fi
fi

echo "Đang tạo certificate..."
echo ""

openssl req -x509 -newkey rsa:4096 -nodes -out server.crt -keyout server.key -days 365 -subj "/CN=localhost"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "Certificate đã được tạo thành công!"
    echo "========================================"
    echo "Files:"
    echo "  - server.crt (Certificate)"
    echo "  - server.key (Private Key)"
    echo ""
    echo "Lưu ý: Đây là self-signed certificate chỉ dùng cho development."
    echo ""
    
    # Set permissions (Linux/Mac)
    chmod 600 server.key
    chmod 644 server.crt
    
else
    echo ""
    echo "ERROR: Không thể tạo certificate!"
    echo ""
    exit 1
fi

