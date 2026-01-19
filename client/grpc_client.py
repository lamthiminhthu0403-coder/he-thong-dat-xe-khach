"""gRPC Client - Client handler cho gRPC API

Chức năng:
- Kết nối với gRPC server
- Gọi các RPC methods
- Streaming support
"""

import grpc
import uuid
from typing import Optional, Dict, List, Callable
import threading

# Import generated gRPC code
try:
    import bus_booking_pb2
    import bus_booking_pb2_grpc
except ImportError:
    # Try to import from proto directory
    import sys
    import os
    proto_path = os.path.join(os.path.dirname(__file__), '..', 'proto')
    if os.path.exists(proto_path):
        sys.path.insert(0, proto_path)
    try:
        import bus_booking_pb2
        import bus_booking_pb2_grpc
    except ImportError:
        print("[gRPC Client] ⚠️ Chưa generate proto files!")
        print("[gRPC Client] Chạy: python generate_proto.py")
        bus_booking_pb2 = None
        bus_booking_pb2_grpc = None


class gRPCClient:
    """gRPC Client cho Bus Booking System"""
    
    def __init__(self, server_address: str = 'localhost:50051'):
        """
        Khởi tạo gRPC client
        
        Args:
            server_address: Địa chỉ gRPC server (host:port)
        """
        if not bus_booking_pb2 or not bus_booking_pb2_grpc:
            raise ImportError("gRPC proto files chưa được generate. Chạy: python generate_proto.py")
        
        self.server_address = server_address
        self.channel = grpc.insecure_channel(server_address)
        self.stub = bus_booking_pb2_grpc.BusBookingServiceStub(self.channel)
        self.session_id = str(uuid.uuid4())
        
        print(f"[gRPC Client] ✅ Đã kết nối với {server_address}")
    
    def get_cities(self) -> Optional[Dict]:
        """Lấy danh sách thành phố"""
        try:
            request = bus_booking_pb2.Empty()
            response = self.stub.GetCities(request)
            return {
                'from_cities': list(response.from_cities),
                'to_cities': list(response.to_cities)
            }
        except Exception as e:
            print(f"[gRPC Client] Lỗi GetCities: {e}")
            return None
    
    def search_routes(self, from_city: str = None, to_city: str = None) -> Optional[List[Dict]]:
        """Tìm kiếm tuyến đường"""
        try:
            request = bus_booking_pb2.SearchRoutesRequest(
                from_city=from_city or '',
                to_city=to_city or ''
            )
            response = self.stub.SearchRoutes(request)
            
            routes = []
            for route in response.routes:
                routes.append({
                    'id': route.id,
                    'from_city': route.from_city,
                    'to_city': route.to_city,
                    'distance_km': route.distance_km,
                    'base_price': route.base_price
                })
            
            return routes
        except Exception as e:
            print(f"[gRPC Client] Lỗi SearchRoutes: {e}")
            return None
    
    def get_dates(self, route_id: str) -> Optional[List[str]]:
        """Lấy ngày có chuyến"""
        try:
            request = bus_booking_pb2.GetDatesRequest(route_id=route_id)
            response = self.stub.GetDates(request)
            return list(response.dates)
        except Exception as e:
            print(f"[gRPC Client] Lỗi GetDates: {e}")
            return None
    
    def search_trips(self, route_id: str, date: str) -> Optional[List[Dict]]:
        """Tìm kiếm chuyến xe"""
        try:
            request = bus_booking_pb2.SearchTripsRequest(
                route_id=route_id,
                date=date
            )
            response = self.stub.SearchTrips(request)
            
            trips = []
            for trip in response.trips:
                trips.append({
                    'id': trip.id,
                    'route_id': trip.route_id,
                    'date': trip.date,
                    'departure_time': trip.departure_time,
                    'bus_code': trip.bus_code,
                    'bus_type': trip.bus_type,
                    'total_seats': trip.total_seats,
                    'available_seats': trip.available_seats
                })
            
            return trips
        except Exception as e:
            print(f"[gRPC Client] Lỗi SearchTrips: {e}")
            return None
    
    def get_seats(self, trip_id: str) -> Optional[Dict]:
        """Lấy trạng thái ghế"""
        try:
            request = bus_booking_pb2.GetSeatsRequest(trip_id=trip_id)
            response = self.stub.GetSeats(request)
            
            seats = {}
            for seat_id, seat_status in response.seats.items():
                seats[seat_id] = {
                    'status': seat_status.status,
                    'locked_by': seat_status.locked_by,
                    'locked_until': seat_status.locked_until
                }
            
            return seats
        except Exception as e:
            print(f"[gRPC Client] Lỗi GetSeats: {e}")
            return None
    
    def select_seat(self, trip_id: str, seat_id: str) -> Optional[Dict]:
        """Chọn ghế"""
        try:
            request = bus_booking_pb2.SelectSeatRequest(
                trip_id=trip_id,
                seat_id=seat_id,
                session_id=self.session_id
            )
            response = self.stub.SelectSeat(request)
            return {
                'success': response.success,
                'message': response.message
            }
        except Exception as e:
            print(f"[gRPC Client] Lỗi SelectSeat: {e}")
            return None
    
    def unselect_seat(self, trip_id: str, seat_id: str) -> Optional[Dict]:
        """Bỏ chọn ghế"""
        try:
            request = bus_booking_pb2.UnselectSeatRequest(
                trip_id=trip_id,
                seat_id=seat_id,
                session_id=self.session_id
            )
            response = self.stub.UnselectSeat(request)
            return {
                'success': response.success,
                'message': response.message
            }
        except Exception as e:
            print(f"[gRPC Client] Lỗi UnselectSeat: {e}")
            return None
    
    def book_seats(self, trip_id: str, seat_ids: List[str], customer_info: Dict) -> Optional[Dict]:
        """Đặt vé"""
        try:
            request = bus_booking_pb2.BookSeatsRequest(
                trip_id=trip_id,
                seat_ids=seat_ids,
                customer_info=bus_booking_pb2.CustomerInfo(
                    name=customer_info['name'],
                    phone=customer_info['phone'],
                    cccd=customer_info['cccd'],
                    email=customer_info.get('email', '')
                ),
                session_id=self.session_id
            )
            response = self.stub.BookSeats(request)
            return {
                'success': response.success,
                'booking_id': response.booking_id,
                'message': response.message
            }
        except Exception as e:
            print(f"[gRPC Client] Lỗi BookSeats: {e}")
            return None
    
    def upload_file(self, filename: str, file_data: bytes, booking_id: str = None) -> Optional[Dict]:
        """Upload file"""
        try:
            request = bus_booking_pb2.UploadFileRequest(
                filename=filename,
                file_data=file_data,
                booking_id=booking_id or ''
            )
            response = self.stub.UploadFile(request)
            return {
                'success': response.success,
                'filepath': response.filepath,
                'message': response.message
            }
        except Exception as e:
            print(f"[gRPC Client] Lỗi UploadFile: {e}")
            return None
    
    def stream_seat_updates(self, trip_ids: List[str] = None, callback: Callable = None):
        """
        Stream realtime seat updates
        
        Args:
            trip_ids: List trip IDs để filter (None = tất cả)
            callback: Function được gọi khi nhận update (trip_id, seats_dict)
        """
        def stream_thread():
            try:
                request = bus_booking_pb2.StreamRequest(
                    trip_ids=trip_ids or []
                )
                
                for update in self.stub.StreamSeatUpdates(request):
                    seats = {}
                    for seat_id, seat_status in update.seats.items():
                        seats[seat_id] = {
                            'status': seat_status.status,
                            'locked_by': seat_status.locked_by,
                            'locked_until': seat_status.locked_until
                        }
                    
                    if callback:
                        callback(update.trip_id, seats, update.timestamp)
                    
            except Exception as e:
                print(f"[gRPC Client] Lỗi stream: {e}")
        
        thread = threading.Thread(target=stream_thread, daemon=True)
        thread.start()
        return thread
    
    def close(self):
        """Đóng kết nối"""
        if self.channel:
            self.channel.close()

