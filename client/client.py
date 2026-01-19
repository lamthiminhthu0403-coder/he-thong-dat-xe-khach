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

# Import network handler (có thể chọn SSL hoặc non-SSL)
USE_SSL = os.getenv('USE_SSL', 'false').lower() == 'true'

if USE_SSL:
    from ssl_network import SSLNetworkHandler as NetworkHandler
    print("[Client] 🔒 Sử dụng SSL/TLS connection")
else:
    from network import NetworkHandler
    print("[Client] ⚠️ Sử dụng kết nối không mã hóa (non-SSL)")

# Khởi tạo Flask app
# static_folder phải là đường dẫn tuyệt đối hoặc tương đối từ client directory
client_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            static_folder=os.path.join(client_dir, 'static'),
            static_url_path='/static',
            template_folder='templates')
app.config['SECRET_KEY'] = 'bus-booking-secret-key'
# Cho phép serve files lớn
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
CORS(app)

print(f"[Flask] Static folder: {app.static_folder}")
print(f"[Flask] Static URL path: {app.static_url_path}")

# Khởi tạo Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Middleware để bỏ qua các request không hợp lệ (TLS handshake, etc.)
@app.before_request
def ignore_invalid_requests():
    """Bỏ qua các request không hợp lệ (TLS handshake, binary data, etc.)"""
    # Kiểm tra nếu request là binary data (TLS handshake)
    if request.data and len(request.data) > 0:
        # Nếu data bắt đầu bằng TLS handshake marker (0x16)
        if request.data[0] == 0x16 or (len(request.data) > 5 and request.data[:3] == b'\x16\x03\x01'):
            # Đây là TLS handshake, không phải HTTP request
            from flask import abort
            abort(400)  # Bad Request, nhưng không log chi tiết

# Custom error handler để không log các lỗi TLS handshake
@app.errorhandler(400)
def handle_bad_request(e):
    """Xử lý Bad Request - bỏ qua TLS handshake attempts"""
    # Kiểm tra nếu đây là TLS handshake
    if hasattr(request, 'data') and request.data and len(request.data) > 0:
        if request.data[0] == 0x16 or (len(request.data) > 5 and request.data[:3] == b'\x16\x03\x01'):
            # Không log TLS handshake attempts
            return '', 400
    
    # Log các lỗi 400 khác bình thường
    return 'Bad Request', 400

# Khởi tạo network handler
if USE_SSL:
    from client.config import SSL_CLIENT_CONFIG
    network = NetworkHandler(
        tcp_host='localhost', 
        tcp_port=55555, 
        udp_port=55556,
        verify_cert=SSL_CLIENT_CONFIG['verify_cert']
    )
else:
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


@app.route('/api/video/guide')
def stream_video():
    """Stream video hướng dẫn (nếu có file video)"""
    try:
        # Dùng đường dẫn tuyệt đối
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        video_path = os.path.join(current_dir, 'client', 'static', 'videos', 'guide.mp4')
        
        print(f"[Video] Đang tìm video tại: {video_path}")
        print(f"[Video] File exists: {os.path.exists(video_path)}")
        
        if os.path.exists(video_path):
            from flask import send_file, request, Response
            import mimetypes
            
            # Hỗ trợ range requests cho video streaming
            range_header = request.headers.get('Range', None)
            if range_header:
                # Partial content support for video streaming
                stat = os.stat(video_path)
                file_size = stat.st_size
                
                range_match = range_header.replace('bytes=', '').split('-')
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else file_size - 1
                length = end - start + 1
                
                with open(video_path, 'rb') as f:
                    f.seek(start)
                    data = f.read(length)
                
                response = Response(
                    data,
                    206,
                    mimetype='video/mp4',
                    direct_passthrough=True,
                )
                response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
                response.headers.add('Accept-Ranges', 'bytes')
                response.headers.add('Content-Length', str(length))
                return response
            else:
                # Full file request
                return send_file(video_path, mimetype='video/mp4', conditional=True)
        else:
            print(f"[Video] ❌ Không tìm thấy file video tại: {video_path}")
            return jsonify({'error': 'Video không tồn tại', 'path': video_path}), 404
    except Exception as e:
        print(f"[Video] ❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# Route để serve video với hỗ trợ range requests
@app.route('/static/videos/<path:filename>')
def serve_video(filename):
    """Serve video files với hỗ trợ range requests cho video streaming"""
    try:
        # Dùng đường dẫn từ Flask's static folder
        video_path = os.path.join(app.static_folder, 'videos', filename)
        
        print(f"[Video] Serve video: {filename}")
        print(f"[Video] Static folder: {app.static_folder}")
        print(f"[Video] Video path: {video_path}")
        print(f"[Video] File exists: {os.path.exists(video_path)}")
        
        if os.path.exists(video_path):
            from flask import request, Response
            
            # Hỗ trợ range requests cho video streaming (quan trọng!)
            range_header = request.headers.get('Range', None)
            if range_header:
                stat = os.stat(video_path)
                file_size = stat.st_size
                
                # Parse range header
                range_match = range_header.replace('bytes=', '').split('-')
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else file_size - 1
                length = end - start + 1
                
                with open(video_path, 'rb') as f:
                    f.seek(start)
                    data = f.read(length)
                
                response = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
                response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
                response.headers.add('Accept-Ranges', 'bytes')
                response.headers.add('Content-Length', str(length))
                response.headers.add('Content-Type', 'video/mp4')
                print(f"[Video] ✅ Trả về partial content: bytes {start}-{end}/{file_size}")
                return response
            
            # Full file request (nếu không có range header)
            print(f"[Video] ✅ Trả về full file")
            return send_file(video_path, mimetype='video/mp4', conditional=True)
        else:
            print(f"[Video] ❌ File không tồn tại: {video_path}")
            # List files để debug
            video_dir = os.path.join(app.static_folder, 'videos')
            if os.path.exists(video_dir):
                files = os.listdir(video_dir)
                print(f"[Video] Files trong video_dir: {files}")
            return jsonify({'error': f'Video {filename} không tồn tại', 'path': video_path}), 404
    except Exception as e:
        print(f"[Video] ❌ Lỗi serve video: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


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
        
        # Giảm log level để tránh spam TLS handshake errors
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)  # Chỉ log warnings và errors, không log 400 requests
        
        # Chạy Flask server
        socketio.run(app, host='0.0.0.0', port=3000, debug=False, log_output=False)
    else:
        print("\n[Lỗi] Không thể kết nối với server!")
        print("Hãy chắc chắn server đang chạy trên port 55555")
