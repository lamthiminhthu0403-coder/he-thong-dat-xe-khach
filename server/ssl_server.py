"""SSL/TLS TCP Server - Phiên bản bảo mật của TCP server

Chức năng:
- Wrap TCP socket với SSL/TLS encryption
- Hỗ trợ certificate authentication
- Giữ nguyên protocol message framing
"""

import socket
import ssl
import threading
import json
import time
import os
import sys
import struct

# Thêm thư mục hiện tại vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from route_manager import RouteManager
from trip_manager import TripManager
from seat_manager import SeatManager
from booking_manager import BookingManager
from file_upload import FileUploadHandler
from email_service import EmailService
from config import SSL_CONFIG, SERVER_CONFIG, EMAIL_CONFIG


class SSLBusBookingServer:
    """TCP Server với SSL/TLS encryption"""
    
    def __init__(self, tcp_port=None, udp_port=None, cert_file=None, key_file=None):
        self.tcp_port = tcp_port or SERVER_CONFIG['tcp_port']
        self.udp_port = udp_port or SERVER_CONFIG['udp_port']
        self.host = SERVER_CONFIG['host']
        
        # SSL Configuration
        self.cert_file = cert_file or SSL_CONFIG['cert_file']
        self.key_file = key_file or SSL_CONFIG['key_file']
        
        self.data_dir = os.path.join(current_dir, 'data')
        self.upload_dir = os.path.join(current_dir, 'uploads')
        
        self.route_manager = RouteManager(self.data_dir)
        self.trip_manager = TripManager(self.data_dir)
        self.seat_manager = SeatManager(self.data_dir)
        
        # Initialize Email Service với config từ environment variables
        self.email_service = EmailService(
            smtp_server=EMAIL_CONFIG['smtp_server'],
            smtp_port=EMAIL_CONFIG['smtp_port'],
            username=EMAIL_CONFIG['username'],
            password=EMAIL_CONFIG['password'],
            use_tls=EMAIL_CONFIG['use_tls']
        )
        self.booking_manager = BookingManager(self.data_dir, email_service=self.email_service)
        self.file_handler = FileUploadHandler(self.upload_dir)
        
        # SSL Context
        self.ssl_context = None
        self._setup_ssl_context()
        
        # TCP Socket (sẽ được wrap với SSL khi accept)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # UDP Socket (không cần SSL)
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        self.running = False
        self.clients = []
        
        print("="*60)
        print("HỆ THỐNG ĐẶT VÉ XE KHÁCH (SSL/TLS ENABLED)")
        print("="*60)
    
    def _setup_ssl_context(self):
        """Setup SSL context với certificate"""
        try:
            # Tạo SSL context cho server
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            
            # Load certificate và private key
            if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
                self.ssl_context.load_cert_chain(certfile=self.cert_file, keyfile=self.key_file)
                print(f"[SSL] ✅ Đã load certificate: {self.cert_file}")
            else:
                print(f"[SSL] ⚠️ Không tìm thấy certificate files")
                print(f"[SSL] Certificate: {self.cert_file}")
                print(f"[SSL] Key: {self.key_file}")
                print(f"[SSL] 💡 Tạo certificate bằng lệnh:")
                print(f"[SSL] openssl req -x509 -newkey rsa:4096 -nodes -out {self.cert_file} -keyout {self.key_file} -days 365")
                # Tạo context không có certificate (sẽ fail khi accept)
                self.ssl_context = None
                return
            
            # Chỉ cho phép TLS 1.2 trở lên (bảo mật hơn)
            try:
                self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
            except AttributeError:
                # Python < 3.7 không có TLSVersion
                self.ssl_context.options |= ssl.OP_NO_SSLv2
                self.ssl_context.options |= ssl.OP_NO_SSLv3
                self.ssl_context.options |= ssl.OP_NO_TLSv1
                self.ssl_context.options |= ssl.OP_NO_TLSv1_1
            
            print(f"[SSL] ✅ SSL/TLS context đã được khởi tạo")
            
        except Exception as e:
            print(f"[SSL] ❌ Lỗi setup SSL context: {e}")
            self.ssl_context = None
    
    def start(self):
        """Start SSL server"""
        if not self.ssl_context:
            print("[SSL] ❌ Không thể start server: thiếu SSL certificate")
            return
        
        self.running = True
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(5)
        print(f"[SSL TCP Server] Lắng nghe trên {self.host}:{self.tcp_port} (SSL/TLS enabled)")
        
        threading.Thread(target=self.udp_broadcast_loop, daemon=True).start()
        threading.Thread(target=self.cleanup_loop, daemon=True).start()
        print("\n[SSL Server] Sẵn sàng phục vụ!\n")
        
        while self.running:
            try:
                client_socket, addr = self.tcp_socket.accept()
                print(f"[SSL TCP] Kết nối từ: {addr}")
                
                # Wrap socket với SSL
                try:
                    ssl_socket = self.ssl_context.wrap_socket(client_socket, server_side=True)
                    print(f"[SSL TCP] ✅ SSL handshake thành công với {addr}")
                    
                    # Xử lý client trong thread riêng
                    threading.Thread(
                        target=self.handle_client,
                        args=(ssl_socket, addr),
                        daemon=True
                    ).start()
                except ssl.SSLError as e:
                    print(f"[SSL TCP] ❌ SSL handshake thất bại với {addr}: {e}")
                    client_socket.close()
                    
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                print(f"[SSL Server] Lỗi accept: {e}")
    
    def _recv_n_bytes(self, sock, n):
        """Đọc chính xác n bytes từ socket"""
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except Exception:
                return None
        return data
    
    def handle_client(self, ssl_socket, client_address):
        """Handle SSL client connection (giống như TCP server thông thường)"""
        connection_id = f"{client_address[0]}:{client_address[1]}"
        self.clients.append(connection_id)
        
        try:
            ssl_socket.settimeout(300.0)
            while self.running:
                # 1. Đọc header (4 bytes độ dài)
                length_data = self._recv_n_bytes(ssl_socket, 4)
                if not length_data:
                    break
                
                length = struct.unpack('!I', length_data)[0]
                
                # 2. Đọc body (JSON payload)
                body_data = self._recv_n_bytes(ssl_socket, length)
                if not body_data:
                    break
                
                try:
                    request = json.loads(body_data.decode('utf-8'))
                    command = request.get('command')
                    
                    session_id = request.get('session_id')
                    if session_id:
                        client_id = session_id
                    else:
                        client_id = connection_id
                    
                    print(f"[SSL TCP] {client_id} -> {command}")
                    
                    # Xử lý command
                    response = self.process_command(command, request, client_id)
                    
                    # 3. Gửi response (Header + Body)
                    resp_bytes = json.dumps(response).encode('utf-8')
                    header = struct.pack('!I', len(resp_bytes))
                    
                    ssl_socket.sendall(header)
                    ssl_socket.sendall(resp_bytes)
                    
                except json.JSONDecodeError:
                    print(f"[SSL TCP] Lỗi JSON từ {connection_id}")
                    continue
                    
        except Exception as e:
            print(f"[SSL TCP] Lỗi {connection_id}: {e}")
        finally:
            if connection_id in self.clients:
                self.clients.remove(connection_id)
            ssl_socket.close()
            print(f"[SSL TCP] Ngắt kết nối: {connection_id}")
    
    def process_command(self, command: str, request: dict, client_id: str) -> dict:
        """Process commands (giống như TCP server thông thường)"""
        if command == 'GET_CITIES':
            return self.route_manager.get_all_cities()
        elif command == 'SEARCH_ROUTES':
            return {'routes': self.route_manager.search_routes(request.get('from_city'), request.get('to_city'))}
        elif command == 'GET_DATES':
            return {'dates': self.trip_manager.get_available_dates(request.get('route_id'))}
        elif command == 'SEARCH_TRIPS':
            trips = self.trip_manager.search_trips(request.get('route_id'), request.get('date'))
            for trip in trips:
                if trip['id'] in self.seat_manager.seats_data:
                    trip['available_seats'] = self.seat_manager.get_available_seats_count(trip['id'])
                else:
                    trip['available_seats'] = trip.get('total_seats', 40)
            return {'trips': trips}
        elif command == 'GET_SEATS':
            return {'seats': self.seat_manager.get_trip_seats(request.get('trip_id'))}
        elif command == 'SELECT_SEAT':
            return self.seat_manager.select_seat(request.get('trip_id'), request.get('seat_id'), client_id)
        elif command == 'UNSELECT_SEAT':
            return self.seat_manager.unselect_seat(request.get('trip_id'), request.get('seat_id'), client_id)
        elif command == 'BOOK_SEATS':
            import time
            t_start = time.time()
            seat_res = self.seat_manager.book_seats(request.get('trip_id'), request.get('seat_ids', []), client_id)
            
            if seat_res['success']:
                if seat_res.get('action') == 'existing':
                    print(f"[Profiling] Book Existing took {time.time()-t_start:.4f}s")
                    return seat_res
                
                trip_id = request.get('trip_id')
                trip_info = self.trip_manager.get_trip_by_id(trip_id)
                route_info = None
                if trip_info:
                    route_info = self.route_manager.get_route_by_id(trip_info.get('route_id'))
                
                booking_res = self.booking_manager.create_booking(
                    trip_id,
                    request.get('seat_ids'),
                    request.get('customer_info'),
                    trip_info=trip_info,
                    route_info=route_info
                )
                print(f"[Profiling] Book New took {time.time()-t_start:.4f}s")
                return booking_res
                
            return seat_res
        elif command == 'UPLOAD_FILE':
            return self.file_handler.save_file(request.get('filename'), bytes.fromhex(request.get('file_data')), request.get('booking_id'))
        elif command == 'GET_TRIP_INFO':
            trip_info = self.trip_manager.get_trip_by_id(request.get('trip_id'))
            if trip_info:
                return {'success': True, 'trip': trip_info}
            return {'success': False, 'error': 'Trip not found'}
        return {'error': f'Unknown command: {command}'}
    
    def udp_broadcast_loop(self):
        """UDP broadcast loop (không thay đổi)"""
        while self.running:
            try:
                all_seats = self.seat_manager.seats_data
                if all_seats:
                    limited = dict(list(all_seats.items())[:50])
                    msg = {'type': 'SEAT_UPDATE', 'timestamp': time.time(), 'seats_data': limited}
                    data = json.dumps(msg).encode('utf-8')
                    if len(data) < 64000:
                        self.udp_socket.sendto(data, ('<broadcast>', self.udp_port))
                time.sleep(2)
            except:
                pass
    
    def cleanup_loop(self):
        """Cleanup loop (không thay đổi)"""
        while self.running:
            self.seat_manager.cleanup_expired_locks(300)
            time.sleep(60)
    
    def stop(self):
        """Stop server"""
        self.running = False
        try:
            self.tcp_socket.close()
        except:
            pass
        try:
            self.udp_socket.close()
        except:
            pass


if __name__ == '__main__':
    server = SSLBusBookingServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

