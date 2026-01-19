"""Configuration file cho hệ thống đặt vé xe khách

Cấu hình cho các service:
- Email Service
- SSL/TLS
- Server ports
"""

import os

# ============================
# EMAIL CONFIGURATION
# ============================
EMAIL_CONFIG = {
    'smtp_server': os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', '587')),
    'username': os.getenv('EMAIL_USERNAME', 'lamthiminhthu.0403@gmail.com'),  # Hoặc set trực tiếp: 'your-email@gmail.com'
    'password': os.getenv('EMAIL_PASSWORD', 'wwjx guyw cclw cgmv'),  # Hoặc set trực tiếp: 'your-app-password'
    'use_tls': os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
}

# ============================
# SSL/TLS CONFIGURATION
# ============================
SSL_CONFIG = {
    'enabled': os.getenv('SSL_ENABLED', 'false').lower() == 'true',
    'cert_file': os.getenv('SSL_CERT_FILE', 'server/server.crt'),
    'key_file': os.getenv('SSL_KEY_FILE', 'server/server.key'),
    'client_cert_required': os.getenv('SSL_CLIENT_CERT_REQUIRED', 'false').lower() == 'true'
}

# ============================
# SERVER CONFIGURATION
# ============================
SERVER_CONFIG = {
    'tcp_port': int(os.getenv('TCP_PORT', '55555')),
    'udp_port': int(os.getenv('UDP_PORT', '55556')),
    'grpc_port': int(os.getenv('GRPC_PORT', '50051')),
    'host': os.getenv('SERVER_HOST', '0.0.0.0')
}

# ============================
# CLIENT CONFIGURATION
# ============================
CLIENT_CONFIG = {
    'host': os.getenv('CLIENT_HOST', '0.0.0.0'),
    'port': int(os.getenv('CLIENT_PORT', '3000')),
    'ssl_context': None  # Có thể set ('cert.pem', 'key.pem') để enable HTTPS
}

# ============================
# MULTIMEDIA CONFIGURATION
# ============================
MULTIMEDIA_CONFIG = {
    'upload_dir': os.getenv('UPLOAD_DIR', 'server/uploads'),
    'max_file_size': int(os.getenv('MAX_FILE_SIZE', '5242880')),  # 5MB default
    'allowed_image_types': ['image/jpeg', 'image/png', 'image/gif'],
    'allowed_document_types': ['application/pdf'],
    'image_compression': {
        'enabled': True,
        'max_size': (800, 600),
        'quality': 85
    }
}

# ============================
# NOTES
# ============================
"""
Cách sử dụng:

1. Email Configuration:
   - Set environment variables: EMAIL_USERNAME, EMAIL_PASSWORD
   - Hoặc chỉnh sửa trực tiếp trong file này
   - Gmail yêu cầu App Password (không dùng password thường)

2. SSL/TLS:
   - Tạo certificate: openssl req -x509 -newkey rsa:4096 -nodes -out server.crt -keyout server.key -days 365
   - Set SSL_ENABLED=true để bật SSL

3. Environment Variables:
   - Tạo file .env hoặc export variables trong shell
   - Ví dụ: export EMAIL_USERNAME="your-email@gmail.com"
"""

