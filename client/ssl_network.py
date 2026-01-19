"""SSL/TLS Network Handler - Client với SSL encryption

Chức năng:
- Kết nối TCP với SSL/TLS encryption
- Giữ nguyên protocol message framing
- Hỗ trợ self-signed certificates
"""

import socket
import ssl
import json
import threading
import time
import struct
import uuid
from typing import Optional, Callable
from config import SSL_CONFIG


class SSLNetworkHandler:
    """Network handler với SSL/TLS support"""
    
    def __init__(self, tcp_host: str = 'localhost', tcp_port: int = 55555, 
                 udp_port: int = 55556, verify_cert: bool = False):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.verify_cert = verify_cert  # False cho self-signed certs trong dev
        self.tcp_socket = None
        self.udp_socket = None
        self.connected = False
        self.udp_callback = None
        self.session_id = str(uuid.uuid4())
    
    def connect(self) -> bool:
        """Kết nối TCP với SSL/TLS"""
        try:
            if self.tcp_socket:
                try:
                    self.tcp_socket.close()
                except:
                    pass
            
            # Tạo SSL context
            context = ssl.create_default_context()
            
            # Cấu hình SSL
            if not self.verify_cert:
                # Không verify certificate (cho self-signed certs)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                print("[SSL Client] ⚠️ Certificate verification đã tắt (chế độ development)")
            else:
                # Verify certificate (production)
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
                print("[SSL Client] ✅ Certificate verification đã bật")
            
            # Tạo socket và wrap với SSL
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket = context.wrap_socket(sock, server_hostname=self.tcp_host)
            
            # Kết nối
            self.tcp_socket.connect((self.tcp_host, self.tcp_port))
            self.tcp_socket.settimeout(30.0)
            self.connected = True
            
            # Hiển thị thông tin SSL
            cipher = self.tcp_socket.cipher()
            if cipher:
                print(f"[SSL Client] ✅ Kết nối SSL OK: {self.tcp_host}:{self.tcp_port}")
                print(f"[SSL Client] Cipher: {cipher[0]}, Version: {cipher[1]}")
            else:
                print(f"[SSL Client] ✅ Kết nối OK: {self.tcp_host}:{self.tcp_port}")
            
            return True
            
        except ssl.SSLError as e:
            print(f"[SSL Client] ❌ Lỗi SSL: {e}")
            self.connected = False
            return False
        except Exception as e:
            print(f"[SSL Client] ❌ Lỗi kết nối: {e}")
            self.connected = False
            return False
    
    def _recv_n_bytes(self, n):
        """Đọc chính xác n bytes từ socket"""
        data = b''
        while len(data) < n:
            chunk = self.tcp_socket.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Closed")
            data += chunk
        return data
    
    def send_request(self, command: str, max_retries: int = 0, **kwargs) -> Optional[dict]:
        """Gửi request qua SSL connection"""
        for attempt in range(max_retries + 1):
            if not self.connected:
                if not self.connect():
                    if attempt == max_retries:
                        return None
                    time.sleep(0.5)
                    continue
            
            try:
                payload_dict = {'command': command, 'session_id': self.session_id, **kwargs}
                req_body = json.dumps(payload_dict).encode('utf-8')
                req_header = struct.pack('!I', len(req_body))
                
                self.tcp_socket.sendall(req_header)
                self.tcp_socket.sendall(req_body)
                
                length_data = self._recv_n_bytes(4)
                length = struct.unpack('!I', length_data)[0]
                
                body_data = self._recv_n_bytes(length)
                return json.loads(body_data.decode('utf-8'))
            
            except Exception as e:
                print(f"[SSL Client] Lỗi IO (lần {attempt+1}): {e}")
                self.connected = False
                if attempt < max_retries:
                    time.sleep(0.5)
        
        return None
    
    def start_udp_listener(self, callback: Callable):
        """Start UDP listener (không thay đổi)"""
        self.udp_callback = callback
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('', self.udp_port))
        threading.Thread(target=self._udp_listen_loop, daemon=True).start()
        print(f"[UDP] Listening on {self.udp_port}")
    
    def _udp_listen_loop(self):
        """UDP listen loop (không thay đổi)"""
        while True:
            try:
                data, _ = self.udp_socket.recvfrom(65535)
                msg = json.loads(data.decode('utf-8'))
                if self.udp_callback:
                    self.udp_callback(msg)
            except:
                pass

