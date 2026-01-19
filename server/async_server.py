"""Async TCP Server - Phiên bản asyncio của TCP server

Chức năng:
- Xử lý TCP connections với asyncio (hiệu quả hơn threading)
- Giữ nguyên message framing protocol
- Tích hợp với các manager hiện có
"""

import asyncio
import struct
import json
import time
import os
import sys

# Thêm thư mục hiện tại vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from route_manager import RouteManager
from trip_manager import TripManager
from seat_manager import SeatManager
from booking_manager import BookingManager
from file_upload import FileUploadHandler
from email_service import EmailService
from config import SERVER_CONFIG, EMAIL_CONFIG


class AsyncBusBookingServer:
    """Async TCP Server với asyncio"""
    
    def __init__(self, tcp_port=None, udp_port=None):
        self.tcp_port = tcp_port or SERVER_CONFIG['tcp_port']
        self.udp_port = udp_port or SERVER_CONFIG['udp_port']
        self.host = SERVER_CONFIG['host']
        
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
        
        self.running = False
        self.clients = {}
        
        print("="*60)
        print("HỆ THỐNG ĐẶT VÉ XE KHÁCH (ASYNC MODE)")
        print("="*60)
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connection với asyncio"""
        client_addr = writer.get_extra_info('peername')
        connection_id = f"{client_addr[0]}:{client_addr[1]}"
        self.clients[connection_id] = writer
        
        print(f"[Async TCP] Client connected: {connection_id}")
        
        try:
            while self.running:
                # 1. Đọc header (4 bytes độ dài)
                try:
                    length_data = await reader.readexactly(4)
                except asyncio.IncompleteReadError:
                    break
                
                length = struct.unpack('!I', length_data)[0]
                
                # 2. Đọc body (JSON payload)
                try:
                    body_data = await reader.readexactly(length)
                except asyncio.IncompleteReadError:
                    break
                
                try:
                    request = json.loads(body_data.decode('utf-8'))
                    command = request.get('command')
                    
                    session_id = request.get('session_id')
                    if session_id:
                        client_id = session_id
                    else:
                        client_id = connection_id
                        print(f"[Async TCP] ⚠️ Client {connection_id} missing SessionID")
                    
                    print(f"[Async TCP] {client_id} -> {command}")
                    
                    # Xử lý command (async)
                    response = await self.process_command_async(command, request, client_id)
                    
                    # 3. Gửi response (Header + Body)
                    resp_bytes = json.dumps(response).encode('utf-8')
                    header = struct.pack('!I', len(resp_bytes))
                    
                    writer.write(header + resp_bytes)
                    await writer.drain()
                    
                except json.JSONDecodeError:
                    print(f"[Async TCP] Lỗi JSON từ {connection_id}")
                    continue
                    
        except Exception as e:
            print(f"[Async TCP] Lỗi {connection_id}: {e}")
        finally:
            if connection_id in self.clients:
                del self.clients[connection_id]
            writer.close()
            await writer.wait_closed()
            print(f"[Async TCP] Ngắt kết nối: {connection_id}")
    
    async def process_command_async(self, command: str, request: dict, client_id: str) -> dict:
        """Process commands với async support"""
        # Chạy các operations I/O-bound trong thread pool để không block event loop
        loop = asyncio.get_event_loop()
        
        if command == 'GET_CITIES':
            return await loop.run_in_executor(None, self.route_manager.get_all_cities)
        
        elif command == 'SEARCH_ROUTES':
            result = await loop.run_in_executor(
                None,
                self.route_manager.search_routes,
                request.get('from_city'),
                request.get('to_city')
            )
            return {'routes': result}
        
        elif command == 'GET_DATES':
            result = await loop.run_in_executor(
                None,
                self.trip_manager.get_available_dates,
                request.get('route_id')
            )
            return {'dates': result}
        
        elif command == 'SEARCH_TRIPS':
            trips = await loop.run_in_executor(
                None,
                self.trip_manager.search_trips,
                request.get('route_id'),
                request.get('date')
            )
            # Process available seats
            for trip in trips:
                if trip['id'] in self.seat_manager.seats_data:
                    trip['available_seats'] = await loop.run_in_executor(
                        None,
                        self.seat_manager.get_available_seats_count,
                        trip['id']
                    )
                else:
                    trip['available_seats'] = trip.get('total_seats', 40)
            return {'trips': trips}
        
        elif command == 'GET_SEATS':
            result = await loop.run_in_executor(
                None,
                self.seat_manager.get_trip_seats,
                request.get('trip_id')
            )
            return {'seats': result}
        
        elif command == 'SELECT_SEAT':
            return await loop.run_in_executor(
                None,
                self.seat_manager.select_seat,
                request.get('trip_id'),
                request.get('seat_id'),
                client_id
            )
        
        elif command == 'UNSELECT_SEAT':
            return await loop.run_in_executor(
                None,
                self.seat_manager.unselect_seat,
                request.get('trip_id'),
                request.get('seat_id'),
                client_id
            )
        
        elif command == 'BOOK_SEATS':
            t_start = time.time()
            seat_res = await loop.run_in_executor(
                None,
                self.seat_manager.book_seats,
                request.get('trip_id'),
                request.get('seat_ids', []),
                client_id
            )
            
            if seat_res['success']:
                if seat_res.get('action') == 'existing':
                    print(f"[Profiling] Book Existing took {time.time()-t_start:.4f}s")
                    return seat_res
                
                trip_id = request.get('trip_id')
                trip_info = await loop.run_in_executor(None, self.trip_manager.get_trip_by_id, trip_id)
                route_info = None
                if trip_info:
                    route_info = await loop.run_in_executor(
                        None,
                        self.route_manager.get_route_by_id,
                        trip_info.get('route_id')
                    )
                
                booking_res = await loop.run_in_executor(
                    None,
                    self.booking_manager.create_booking,
                    trip_id,
                    request.get('seat_ids'),
                    request.get('customer_info'),
                    None,  # uploaded_files
                    trip_info,
                    route_info
                )
                print(f"[Profiling] Book New took {time.time()-t_start:.4f}s")
                return booking_res
                
            return seat_res
        
        elif command == 'UPLOAD_FILE':
            return await loop.run_in_executor(
                None,
                self.file_handler.save_file,
                request.get('filename'),
                bytes.fromhex(request.get('file_data')),
                request.get('booking_id')
            )
        elif command == 'GET_TRIP_INFO':
            trip_info = await loop.run_in_executor(
                None,
                self.trip_manager.get_trip_by_id,
                request.get('trip_id')
            )
            if trip_info:
                return {'success': True, 'trip': trip_info}
            return {'success': False, 'error': 'Trip not found'}
        
        return {'error': f'Unknown command: {command}'}
    
    async def start(self):
        """Start async TCP server"""
        self.running = True
        
        # Start UDP broadcaster
        asyncio.create_task(self.udp_broadcast_loop())
        
        # Start cleanup loop
        asyncio.create_task(self.cleanup_loop())
        
        # Start TCP server
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.tcp_port
        )
        
        print(f"[Async TCP Server] Lắng nghe trên {self.host}:{self.tcp_port}")
        print("\n[Async Server] Sẵn sàng phục vụ!\n")
        
        async with server:
            await server.serve_forever()
    
    async def udp_broadcast_loop(self):
        """Async UDP broadcast loop"""
        sock = None
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setblocking(False)
            
            loop = asyncio.get_event_loop()
            
            while self.running:
                try:
                    all_seats = self.seat_manager.seats_data
                    if all_seats:
                        limited = dict(list(all_seats.items())[:50])
                        msg = {
                            'type': 'SEAT_UPDATE',
                            'timestamp': time.time(),
                            'seats_data': limited
                        }
                        data = json.dumps(msg).encode('utf-8')
                        if len(data) < 64000:
                            await loop.sock_sendto(
                                sock,
                                data,
                                ('<broadcast>', self.udp_port)
                            )
                    await asyncio.sleep(2)
                except Exception as e:
                    print(f"[Async UDP] Lỗi broadcast: {e}")
                    await asyncio.sleep(2)
        except Exception as e:
            print(f"[Async UDP] Lỗi khởi tạo: {e}")
        finally:
            if sock:
                sock.close()
    
    async def cleanup_loop(self):
        """Async cleanup loop"""
        while self.running:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.seat_manager.cleanup_expired_locks,
                300
            )
            await asyncio.sleep(60)
    
    def stop(self):
        """Stop server"""
        self.running = False


async def main():
    """Main async function"""
    server = AsyncBusBookingServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n[Async Server] Đang dừng...")
        server.stop()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Async Server] Đã dừng")

