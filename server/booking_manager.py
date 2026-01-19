"""Booking Manager - Quản lý đặt vé (Optimized Storage v2 - Async Write)

Chức năng:
- Lưu thông tin đặt vé (Tách file Booking theo chuyến)
- Lưu thông tin khách hàng (Append-Only Log)
- Tạo mã vé
- OPTIMIZED: Async Disk Write để không block API response
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
import copy
import threading


class BookingManager:
    def __init__(self, data_dir: str, email_service=None):
        self.data_dir = data_dir
        self.bookings_dir = os.path.join(data_dir, 'bookings')
        self.clients_file = os.path.join(data_dir, 'clients.json') # Optimized to JSONL
        
        self.clients: List[Dict] = []
        self.lock = Lock()
        
        # OPTIMIZATION: Async Disk Write
        self._write_executor = ThreadPoolExecutor(max_workers=2)
        
        # Email service (optional)
        self.email_service = email_service
        
        self.init_storage()
        self.load_clients()
    
    def init_storage(self):
        if not os.path.exists(self.bookings_dir):
            os.makedirs(self.bookings_dir)
            
    def load_clients(self):
        """Load clients từ file .jsonl"""
        self.clients = []
        try:
            if os.path.exists(self.clients_file):
                with open(self.clients_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                self.clients.append(json.loads(line))
                            except: pass
            print(f"[BookingManager] Đã load {len(self.clients)} khách hàng")
        except Exception as e:
            print(f"[BookingManager] Lỗi load clients: {e}")

    def get_trip_bookings(self, trip_id: str) -> List[Dict]:
        filepath = os.path.join(self.bookings_dir, f"{trip_id}.json")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _async_save_booking(self, filepath: str, booking: Dict):
        """Background task để ghi booking vào disk"""
        try:
            bookings = []
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    bookings = json.load(f)
            
            bookings.append(booking)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(bookings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[BookingManager] Async save booking error: {e}")

    def save_trip_booking(self, trip_id: str, booking: Dict):
        """OPTIMIZED: Async write - return ngay, disk write trong background"""
        filepath = os.path.join(self.bookings_dir, f"{trip_id}.json")
        booking_copy = copy.deepcopy(booking)
        self._write_executor.submit(self._async_save_booking, filepath, booking_copy)

    def _async_save_customer(self, info: Dict):
        """Background task để ghi customer vào disk"""
        try:
            with open(self.clients_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(info, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[BookingManager] Async save client error: {e}")

    def save_customer(self, info: Dict):
        """OPTIMIZED: Check duplicate in RAM -> Async Append to Disk"""
        # Validate input
        if not isinstance(info, dict):
            print(f"[BookingManager] Warning: info is not dict, got {type(info)}")
            return
            
        with self.lock:
            # Check duplicate
            phone = info.get('phone')
            if not phone:
                return
            
            for c in self.clients:
                if isinstance(c, dict) and c.get('phone') == phone:
                    return # Đã tồn tại, không lưu lại
            
            self.clients.append(info)
        
        # Async write (outside lock to avoid blocking)
        info_copy = copy.deepcopy(info)
        self._write_executor.submit(self._async_save_customer, info_copy)

    def create_booking(self, trip_id: str, seat_ids: List[str], 
                      customer_info: Dict, uploaded_files: List[str] = None,
                      trip_info: Dict = None, route_info: Dict = None) -> Dict:
        """Tạo đơn đặt vé mới - OPTIMIZED với async disk write"""
        # Validate customer_info
        if not isinstance(customer_info, dict):
            return {'success': False, 'message': f'Dữ liệu khách hàng không hợp lệ (got {type(customer_info).__name__})'}
        
        required_fields = ['name', 'phone', 'cccd']
        for field in required_fields:
            if field not in customer_info:
                return {'success': False, 'message': f'Thiếu thông tin: {field}'}
        
        booking_id = f"BK{uuid.uuid4().hex[:8].upper()}"
        
        booking = {
            'id': booking_id,
            'trip_id': trip_id,
            'seat_ids': seat_ids,
            'customer_name': customer_info['name'],
            'customer_phone': customer_info['phone'],
            'customer_cccd': customer_info['cccd'],
            'uploaded_files': uploaded_files or [],
            'booking_time': datetime.now().isoformat(),
            'status': 'confirmed'
        }
        
        # 1. Save Booking (Async - không block)
        self.save_trip_booking(trip_id, booking)
        
        # 2. Save Customer (Async - không block)
        self.save_customer(customer_info)
        
        # 3. Gửi email xác nhận (nếu có email và email_service)
        if self.email_service and customer_info.get('email'):
            self._send_confirmation_email(booking_id, customer_info, seat_ids, trip_info, route_info)
        
        print(f"[Booking] Đã tạo đơn {booking_id} cho chuyến {trip_id}")
        
        return {
            'success': True,
            'booking_id': booking_id,
            'message': 'Đặt vé thành công'
        }
    
    def _send_confirmation_email(self, booking_id: str, customer_info: Dict, 
                                 seat_ids: List[str], trip_info: Dict = None, 
                                 route_info: Dict = None):
        """Gửi email xác nhận trong background thread"""
        def send_email():
            try:
                # Tính tổng tiền (giá mỗi ghế * số ghế)
                total_price = 0
                if route_info and 'base_price' in route_info:
                    total_price = route_info['base_price'] * len(seat_ids)
                
                email_data = {
                    'booking_id': booking_id,
                    'customer_name': customer_info['name'],
                    'from_city': route_info.get('from_city', 'N/A') if route_info else 'N/A',
                    'to_city': route_info.get('to_city', 'N/A') if route_info else 'N/A',
                    'date': trip_info.get('date', 'N/A') if trip_info else 'N/A',
                    'departure_time': trip_info.get('departure_time', 'N/A') if trip_info else 'N/A',
                    'bus_code': trip_info.get('bus_code', 'N/A') if trip_info else 'N/A',
                    'bus_type': trip_info.get('bus_type', 'Giường nằm') if trip_info else 'Giường nằm',
                    'seats': seat_ids,
                    'total_price': total_price
                }
                
                self.email_service.send_booking_confirmation(customer_info['email'], email_data)
            except Exception as e:
                print(f"[BookingManager] Lỗi gửi email: {e}")
        
        # Gửi trong thread riêng để không block
        threading.Thread(target=send_email, daemon=True).start()
