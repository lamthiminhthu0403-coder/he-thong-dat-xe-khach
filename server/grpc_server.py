"""gRPC Server - gRPC API cho hệ thống đặt vé

Chức năng:
- Cung cấp gRPC API song song với TCP/UDP
- Protocol Buffers cho performance cao hơn
- Streaming support cho realtime updates
"""

import grpc
from concurrent import futures
import threading
import time
import json
import os
import sys

# Thêm thư mục hiện tại vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import generated gRPC code
try:
    import bus_booking_pb2
    import bus_booking_pb2_grpc
except ImportError:
    print("[gRPC] ⚠️ Chưa generate proto files!")
    print("[gRPC] Chạy: python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/bus_booking.proto")
    sys.exit(1)

from route_manager import RouteManager
from trip_manager import TripManager
from seat_manager import SeatManager
from booking_manager import BookingManager
from file_upload import FileUploadHandler
from email_service import EmailService
from config import SERVER_CONFIG


class BusBookingService(bus_booking_pb2_grpc.BusBookingServiceServicer):
    """gRPC Service Implementation"""
    
    def __init__(self, booking_server):
        self.server = booking_server
        self.stream_subscribers = {}  # {trip_id: [contexts]}
        self.stream_lock = threading.Lock()
    
    def GetCities(self, request, context):
        """Lấy danh sách thành phố"""
        try:
            cities = self.server.route_manager.get_all_cities()
            return bus_booking_pb2.CitiesResponse(
                from_cities=cities['from_cities'],
                to_cities=cities['to_cities']
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return bus_booking_pb2.CitiesResponse()
    
    def SearchRoutes(self, request, context):
        """Tìm kiếm tuyến đường"""
        try:
            routes = self.server.route_manager.search_routes(
                request.from_city if request.from_city else None,
                request.to_city if request.to_city else None
            )
            
            pb_routes = []
            for route in routes:
                pb_routes.append(bus_booking_pb2.Route(
                    id=route['id'],
                    from_city=route['from_city'],
                    to_city=route['to_city'],
                    distance_km=route['distance_km'],
                    base_price=route['base_price']
                ))
            
            return bus_booking_pb2.RoutesResponse(routes=pb_routes)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return bus_booking_pb2.RoutesResponse()
    
    def GetDates(self, request, context):
        """Lấy ngày có chuyến"""
        try:
            dates = self.server.trip_manager.get_available_dates(request.route_id)
            return bus_booking_pb2.DatesResponse(dates=dates)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return bus_booking_pb2.DatesResponse()
    
    def SearchTrips(self, request, context):
        """Tìm kiếm chuyến xe"""
        try:
            trips = self.server.trip_manager.search_trips(
                request.route_id,
                request.date
            )
            
            # Add available seats count
            for trip in trips:
                if trip['id'] in self.server.seat_manager.seats_data:
                    trip['available_seats'] = self.server.seat_manager.get_available_seats_count(trip['id'])
                else:
                    trip['available_seats'] = trip.get('total_seats', 40)
            
            pb_trips = []
            for trip in trips:
                pb_trips.append(bus_booking_pb2.Trip(
                    id=trip['id'],
                    route_id=trip['route_id'],
                    date=trip['date'],
                    departure_time=trip['departure_time'],
                    bus_code=trip['bus_code'],
                    bus_type=trip.get('bus_type', 'Giường nằm'),
                    total_seats=trip.get('total_seats', 40),
                    available_seats=trip.get('available_seats', 40)
                ))
            
            return bus_booking_pb2.TripsResponse(trips=pb_trips)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return bus_booking_pb2.TripsResponse()
    
    def GetSeats(self, request, context):
        """Lấy trạng thái ghế"""
        try:
            seats = self.server.seat_manager.get_trip_seats(request.trip_id)
            
            pb_seats = {}
            for seat_id, seat_info in seats.items():
                pb_seats[seat_id] = bus_booking_pb2.SeatStatus(
                    status=seat_info.get('status', 'available'),
                    locked_by=seat_info.get('locked_by', ''),
                    locked_until=int(seat_info.get('locked_until', 0))
                )
            
            response = bus_booking_pb2.SeatsResponse()
            response.seats.update(pb_seats)
            return response
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return bus_booking_pb2.SeatsResponse()
    
    def SelectSeat(self, request, context):
        """Chọn ghế"""
        try:
            result = self.server.seat_manager.select_seat(
                request.trip_id,
                request.seat_id,
                request.session_id
            )
            return bus_booking_pb2.SelectSeatResponse(
                success=result.get('success', False),
                message=result.get('message', '')
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return bus_booking_pb2.SelectSeatResponse(success=False, message=str(e))
    
    def UnselectSeat(self, request, context):
        """Bỏ chọn ghế"""
        try:
            result = self.server.seat_manager.unselect_seat(
                request.trip_id,
                request.seat_id,
                request.session_id
            )
            return bus_booking_pb2.SelectSeatResponse(
                success=result.get('success', False),
                message=result.get('message', '')
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return bus_booking_pb2.SelectSeatResponse(success=False, message=str(e))
    
    def BookSeats(self, request, context):
        """Đặt vé"""
        try:
            # Get trip and route info
            trip_info = self.server.trip_manager.get_trip_by_id(request.trip_id)
            route_info = None
            if trip_info:
                route_info = self.server.route_manager.get_route_by_id(trip_info.get('route_id'))
            
            customer_info = {
                'name': request.customer_info.name,
                'phone': request.customer_info.phone,
                'cccd': request.customer_info.cccd,
                'email': request.customer_info.email if request.customer_info.email else ''
            }
            
            result = self.server.booking_manager.create_booking(
                request.trip_id,
                list(request.seat_ids),
                customer_info,
                uploaded_files=None,
                trip_info=trip_info,
                route_info=route_info
            )
            
            return bus_booking_pb2.BookSeatsResponse(
                success=result.get('success', False),
                booking_id=result.get('booking_id', ''),
                message=result.get('message', '')
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return bus_booking_pb2.BookSeatsResponse(
                success=False,
                booking_id='',
                message=str(e)
            )
    
    def UploadFile(self, request, context):
        """Upload file"""
        try:
            result = self.server.file_handler.save_file(
                request.filename,
                request.file_data,
                request.booking_id if request.booking_id else None
            )
            return bus_booking_pb2.UploadFileResponse(
                success=result.get('success', False),
                filepath=result.get('filepath', ''),
                message=result.get('message', '')
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error: {str(e)}")
            return bus_booking_pb2.UploadFileResponse(
                success=False,
                filepath='',
                message=str(e)
            )
    
    def StreamSeatUpdates(self, request, context):
        """Stream realtime seat updates"""
        try:
            filter_trip_ids = set(request.trip_ids) if request.trip_ids else None
            
            last_seats_data = {}
            
            while context.is_active():
                try:
                    # Get current seats data
                    all_seats = self.server.seat_manager.seats_data
                    
                    # Filter by trip_ids if specified
                    if filter_trip_ids:
                        seats_data = {
                            trip_id: seats
                            for trip_id, seats in all_seats.items()
                            if trip_id in filter_trip_ids
                        }
                    else:
                        seats_data = dict(list(all_seats.items())[:50])  # Limit 50 trips
                    
                    # Send updates for changed trips
                    for trip_id, seats in seats_data.items():
                        if trip_id not in last_seats_data or seats != last_seats_data[trip_id]:
                            pb_seats = {}
                            for seat_id, seat_info in seats.items():
                                pb_seats[seat_id] = bus_booking_pb2.SeatStatus(
                                    status=seat_info.get('status', 'available'),
                                    locked_by=seat_info.get('locked_by', ''),
                                    locked_until=int(seat_info.get('locked_until', 0))
                                )
                            
                            update = bus_booking_pb2.SeatUpdate(
                                trip_id=trip_id,
                                timestamp=int(time.time()),
                            )
                            update.seats.update(pb_seats)
                            
                            context.write(update)
                            last_seats_data[trip_id] = seats
                    
                    # Wait before next update
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"[gRPC Stream] Lỗi: {e}")
                    break
            
        except Exception as e:
            print(f"[gRPC Stream] Lỗi stream: {e}")
        finally:
            print(f"[gRPC Stream] Client disconnected")


def serve_grpc(booking_server, port=None):
    """Start gRPC server"""
    port = port or SERVER_CONFIG['grpc_port']
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    bus_booking_pb2_grpc.add_BusBookingServiceServicer_to_server(
        BusBookingService(booking_server), server
    )
    
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    print(f"[gRPC] ✅ Server listening on port {port}")
    print(f"[gRPC] Endpoint: localhost:{port}")
    
    return server


if __name__ == '__main__':
    # Import main server để sử dụng managers
    from server import BusBookingServer
    
    main_server = BusBookingServer()
    grpc_server = serve_grpc(main_server)
    
    try:
        # Keep server running
        import time
        while True:
            time.sleep(86400)  # Run for 24 hours
    except KeyboardInterrupt:
        print("\n[gRPC] Đang dừng...")
        grpc_server.stop(0)
        print("[gRPC] Đã dừng")

