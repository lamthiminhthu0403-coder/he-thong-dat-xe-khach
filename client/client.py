"""Client - Web-based UI với Flask

Kiến trúc:
- Flask server để serve web UI và API endpoints
- Socket.IO cho realtime updates
- Network handler để giao tiếp với bus booking server
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import sys

# Thêm thư mục hiện tại vào sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from network import NetworkHandler

# Khởi tạo Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.config['SECRET_KEY'] = 'bus-booking-secret-key'
CORS(app)

# Khởi tạo Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Khởi tạo network handler
network = NetworkHandler(tcp_host='localhost', tcp_port=55555, udp_port=55556)

# Biến toàn cục lưu trạng thái
current_selection = {
    'trip_id': None,
    'selected_seats': []  # Danh sách ghế đang chọn
}


@app.route('/')
def index():
    """Trang chủ"""
    return render_template('index.html')


@app.route('/api/cities', methods=['GET'])
def get_cities():
    """Lấy danh sách thành phố"""
    response = network.send_request('GET_CITIES')
    return jsonify(response or {'error': 'Không kết nối được server'})


@app.route('/api/routes', methods=['POST'])
def search_routes():
    """Tìm kiếm tuyến"""
    data = request.json
    response = network.send_request(
        'SEARCH_ROUTES',
        from_city=data.get('from_city'),
        to_city=data.get('to_city')
    )
    return jsonify(response or {'error': 'Không kết nối được server'})


@app.route('/api/dates/<route_id>', methods=['GET'])
def get_dates(route_id):
    """Lấy ngày có chuyến"""
    response = network.send_request('GET_DATES', route_id=route_id)
    return jsonify(response or {'error': 'Không kết nối được server'})


@app.route('/api/trips', methods=['POST'])
def search_trips():
    """Tìm kiếm chuyến xe"""
    data = request.json
    response = network.send_request(
        'SEARCH_TRIPS',
        route_id=data.get('route_id'),
        date=data.get('date')
    )
    return jsonify(response or {'error': 'Không kết nối được server'})


@app.route('/api/seats/<trip_id>', methods=['GET'])
def get_seats(trip_id):
    """Lấy trạng thái ghế"""
    response = network.send_request('GET_SEATS', trip_id=trip_id)
    return jsonify(response or {'error': 'Không kết nối được server'})


@app.route('/api/select-seat', methods=['POST'])
def select_seat():
    """Chọn ghế"""
    data = request.json
    trip_id = data.get('trip_id')
    seat_id = data.get('seat_id')
    
    response = network.send_request(
        'SELECT_SEAT',
        trip_id=trip_id,
        seat_id=seat_id
    )
    
    # Lưu vào selection hiện tại
    if response and response.get('success'):
        current_selection['trip_id'] = trip_id
        if seat_id not in current_selection['selected_seats']:
            current_selection['selected_seats'].append(seat_id)
    
    return jsonify(response or {'success': False, 'message': 'Lỗi kết nối'})


@app.route('/api/unselect-seat', methods=['POST'])
def unselect_seat():
    """Bỏ chọn ghế"""
    data = request.json
    trip_id = data.get('trip_id')
    seat_id = data.get('seat_id')
    
    response = network.send_request(
        'UNSELECT_SEAT',
        trip_id=trip_id,
        seat_id=seat_id
    )
    
    # Xóa khỏi selection
    if response and response.get('success'):
        if seat_id in current_selection['selected_seats']:
            current_selection['selected_seats'].remove(seat_id)
    
    return jsonify(response or {'success': False, 'message': 'Lỗi kết nối'})


@app.route('/api/book', methods=['POST'])
def book_seats():
    """Xác nhận đặt vé"""
    data = request.json
    
    response = network.send_request(
        'BOOK_SEATS',
        trip_id=data.get('trip_id'),
        seat_ids=data.get('seat_ids'),
        customer_info=data.get('customer_info')
    )
    
    # Reset selection sau khi đặt thành công
    if response and response.get('success'):
        current_selection['trip_id'] = None
        current_selection['selected_seats'] = []
    
    return jsonify(response or {'success': False, 'message': 'Lỗi kết nối'})


@app.route('/api/trip-info/<trip_id>', methods=['GET'])
def get_trip_info(trip_id):
    """Lấy thông tin chuyến"""
    response = network.send_request('GET_TRIP_INFO', trip_id=trip_id)
    return jsonify(response or {'error': 'Không kết nối được server'})


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file qua TCP"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Không có file'})
    
    file = request.files['file']
    booking_id = request.form.get('booking_id', '')
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Chưa chọn file'})
    
    # Đọc nội dung file
    file_data = file.read()
    
    # Gửi qua TCP (convert bytes to hex string để JSON serialize)
    response = network.send_request(
        'UPLOAD_FILE',
        filename=file.filename,
        file_data=file_data.hex(),
        booking_id=booking_id
    )
    
    return jsonify(response or {'success': False, 'message': 'Lỗi upload'})


def handle_udp_broadcast(message):
    """Xử lý UDP broadcast - gửi realtime update cho clients"""
    if message.get('type') == 'SEAT_UPDATE':
        # Broadcast đến tất cả web clients qua Socket.IO
        socketio.emit('seat_update', message)


if __name__ == '__main__':
    print("="*60)
    print("CLIENT - HỆ THỐNG ĐẶT VÉ XE KHÁCH")
    print("="*60)
    
    # Kết nối TCP với server
    if network.connect():
        # Bắt đầu lắng nghe UDP
        network.start_udp_listener(handle_udp_broadcast)
        
        print("\n[Client] Mở trình duyệt và truy cập: http://localhost:3000")
        print("="*60)
        print()
        
        # Chạy Flask server
        socketio.run(app, host='0.0.0.0', port=3000, debug=False)
    else:
        print("\n[Lỗi] Không thể kết nối với server!")
        print("Hãy chắc chắn server đang chạy trên port 55555")