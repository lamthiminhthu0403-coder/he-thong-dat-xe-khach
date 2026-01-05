"""TCP + UDP Server cho hệ thống đặt vé xe khách (Protocol v2: Message Framing)"""

import socket
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


class BusBookingServer:
    def __init__(self, tcp_port=55555, udp_port=55556):
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.host = '0.0.0.0'
        
        self.data_dir = os.path.join(current_dir, 'data')
        self.upload_dir = os.path.join(current_dir, 'uploads')
        
        self.route_manager = RouteManager(self.data_dir)
        self.trip_manager = TripManager(self.data_dir)
        self.seat_manager = SeatManager(self.data_dir)
        self.booking_manager = BookingManager(self.data_dir)
        self.file_handler = FileUploadHandler(self.upload_dir)
        
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        self.running = False
        self.clients = []
        
        print("="*60)
        print("HỆ THỐNG ĐẶT VÉ XE KHÁCH (IO FRAMING ENABLED)")
        print("="*60)
    
    def start(self):
        self.running = True
        self.tcp_socket.bind((self.host, self.tcp_port))
        self.tcp_socket.listen(5)
        print(f"[TCP Server] Lắng nghe trên {self.host}:{self.tcp_port}")
        
        threading.Thread(target=self.udp_broadcast_loop, daemon=True).start()
        threading.Thread(target=self.cleanup_loop, daemon=True).start()
        print("\n[Server] Sẵn sàng phục vụ!\n")
        
        while self.running:
            try:
                client_socket, addr = self.tcp_socket.accept()
                print(f"[TCP] Kết nối: {addr}")
                threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                print(f"[Server] Lỗi accept: {e}")

    def _recv_n_bytes(self, sock, n):
        """Đọc chính xác n bytes từ socket"""
        data = b''
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk: return None
                data += chunk
            except Exception:
                return None
        return data

    def handle_client(self, client_socket, client_address):
        connection_id = f"{client_address[0]}:{client_address[1]}"
        self.clients.append(connection_id)
        
        try:
            client_socket.settimeout(300.0)
            while self.running:
                # 1. Đọc header (4 bytes độ dài)
                length_data = self._recv_n_bytes(client_socket, 4)
                if not length_data: break
                
                length = struct.unpack('!I', length_data)[0]
                
                # 2. Đọc body (JSON payload)
                body_data = self._recv_n_bytes(client_socket, length)
                if not body_data: break
                
                try:
                    request = json.loads(body_data.decode('utf-8'))
                    command = request.get('command')
                    
                    # FIX: Session ID Priority
                    session_id = request.get('session_id')
                    if session_id:
                        client_id = session_id
                    else:
                        client_id = connection_id
                        print(f"[TCP] ⚠️ Client {connection_id} missing SessionID (Old Client?)")

                    print(f"[TCP] {client_id} -> {command}")
                    
                    # Gọi process_command với client_id chuẩn
                    response = self.process_command(command, request, client_id)
                    
                    # 3. Gửi response (Header + Body)
                    resp_bytes = json.dumps(response).encode('utf-8')
                    header = struct.pack('!I', len(resp_bytes))
                    
                    client_socket.sendall(header)
                    client_socket.sendall(resp_bytes)
                    
                except json.JSONDecodeError:
                    print(f"[TCP] Lỗi JSON từ {connection_id}")
                    continue
                    
        except Exception as e:
            print(f"[TCP] Lỗi {connection_id}: {e}")
        finally:
            if connection_id in self.clients: self.clients.remove(connection_id)
            client_socket.close()
            print(f"[TCP] Ngắt kết nối: {connection_id}")
    
    def process_command(self, command: str, request: dict, client_id: str) -> dict:
        if command == 'GET_CITIES':
            return self.route_manager.get_all_cities()
        elif command == 'SEARCH_ROUTES':
            return {'routes': self.route_manager.search_routes(request.get('from_city'), request.get('to_city'))}
        elif command == 'GET_DATES':
            return {'dates': self.trip_manager.get_available_dates(request.get('route_id'))}
        elif command == 'SEARCH_TRIPS':
            trips = self.trip_manager.search_trips(request.get('route_id'), request.get('date'))
            for trip in trips:
                # OPTIMIZATION: Không init ghế ở đây để tránh IO disk chậm
                # Nếu chưa init -> coi như còn trống tất cả
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
                # Idempotency check
                if seat_res.get('action') == 'existing':
                    print(f"[Profiling] Book Existing took {time.time()-t_start:.4f}s")
                    return seat_res

                booking_res = self.booking_manager.create_booking(request.get('trip_id'), request.get('seat_ids'), request.get('customer_info'))
                print(f"[Profiling] Book New took {time.time()-t_start:.4f}s")
                return booking_res
                
            return seat_res
        elif command == 'UPLOAD_FILE':
            return self.file_handler.save_file(request.get('filename'), bytes.fromhex(request.get('file_data')), request.get('booking_id'))
        return {'error': f'Unknown command: {command}'}
    
    def udp_broadcast_loop(self):
        while self.running:
            try:
                all_seats = self.seat_manager.seats_data
                if all_seats:
                    # Giới hạn 50 chuyến
                    limited = dict(list(all_seats.items())[:50])
                    msg = {'type': 'SEAT_UPDATE', 'timestamp': time.time(), 'seats_data': limited}
                    data = json.dumps(msg).encode('utf-8')
                    if len(data) < 64000:
                        self.udp_socket.sendto(data, ('<broadcast>', self.udp_port))
                time.sleep(2)
            except: pass
    
    def cleanup_loop(self):
        while self.running:
            self.seat_manager.cleanup_expired_locks(300)
            time.sleep(60)

    def stop(self):
        self.running = False
        try: self.tcp_socket.close()
        except: pass
        try: self.udp_socket.close()
        except: pass

if __name__ == '__main__':
    server = BusBookingServer()
    try: server.start()
    except KeyboardInterrupt: server.stop()