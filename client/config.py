"""Configuration file cho client"""

import os

CLIENT_CONFIG = {
    'host': os.getenv('CLIENT_HOST', '0.0.0.0'),
    'port': int(os.getenv('CLIENT_PORT', '3000')),
    'ssl_context': None  # Có thể set ('cert.pem', 'key.pem') để enable HTTPS
}

# SSL Client config
SSL_CLIENT_CONFIG = {
    'verify_cert': os.getenv('SSL_VERIFY_CERT', 'false').lower() == 'true'  # False cho dev với self-signed certs
}

