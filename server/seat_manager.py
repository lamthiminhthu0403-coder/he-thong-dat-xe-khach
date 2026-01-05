"""SeatManager - Quản lý ghế ngồi (Optimized Storage v2)

Chức năng:
- Quản lý trạng thái ghế
- Tối ưu I/O: 
  + Lưu trữ mỗi chuyến xe ra 1 file JSON riêng biệt.
  + Async Disk Write: Ghi file trong background thread, không block response.
"""

import json
import os
import time
import glob
from typing import List, Dict, Optional
from threading import Lock, Thread
from queue import Queue
from concurrent.futures import ThreadPoolExecutor


class SeatManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.seats_file = os.path.join(data_dir, 'seats.json') # Legacy file
        self.seats_dir = os.path.join(data_dir, 'seats')       # New storage dir
        
        self.seats_data: Dict = {}  # Cache in Memory
        self.lock = Lock()
        
        # OPTIMIZATION: Async Disk Write
        self._write_executor = ThreadPoolExecutor(max_workers=2)
        self._pending_writes: Dict[str, dict] = {}  # Debounce: chỉ lưu version cuối
        
        self.init_storage()
        self.load_seats()
    
    def init_storage(self):
        """Khởi tạo thư mục và migrate dữ liệu cũ nếu có"""
        if not os.path.exists(self.seats_dir):
            os.makedirs(self.seats_dir)
            
            # Migration
            if os.path.exists(self.seats_file):
                print("[SeatManager] Đang chuyển đổi dữ liệu sang định dạng mới...")
                try:
                    with open(self.seats_file, 'r', encoding='utf-8') as f:
                        old_data = json.load(f)
                    
                    for trip_id, data in old_data.items():
                        self._sync_save_trip_data(trip_id, data)
                    
                    os.rename(self.seats_file, self.seats_file + '.bak')
                    print(f"[SeatManager] Đã migrate thành công.")
                except Exception as e:
                    print(f"[SeatManager] Lỗi Migration: {e}")

    def load_seats(self):
        """Load toàn bộ dữ liệu từ thư mục seats/ vào RAM"""
        self.seats_data = {}
        files = glob.glob(os.path.join(self.seats_dir, "*.json"))
        
        print(f"[SeatManager] Đang load {len(files)} file dữ liệu...")
        for filepath in files:
            try:
                trip_id = os.path.splitext(os.path.basename(filepath))[0]
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.seats_data[trip_id] = json.load(f)
            except Exception:
                pass

    def _sync_save_trip_data(self, trip_id: str, data: dict):
        """Ghi đồng bộ - dùng cho migration"""
        filepath = os.path.join(self.seats_dir, f"{trip_id}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SeatManager] Lỗi lưu chuyến {trip_id}: {e}")

    def _async_write_task(self, trip_id: str, data: dict):
        """Background task để ghi disk"""
        try:
            filepath = os.path.join(self.seats_dir, f"{trip_id}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SeatManager] Async write error for {trip_id}: {e}")

    def save_trip_data(self, trip_id: str, data: dict):
        """OPTIMIZED: Ghi async - return ngay, disk write trong background"""
        # Deep copy để tránh race condition
        import copy
        data_copy = copy.deepcopy(data)
        self._write_executor.submit(self._async_write_task, trip_id, data_copy)

    def initialize_trip_seats(self, trip_id: str, total_seats: int = 40):
        if trip_id in self.seats_data: return
        
        with self.lock:
            seats = {}
            for i in range(1, 21):
                seats[f"T1-A{i:02d}"] = {'status': 'available', 'locked_by': None, 'locked_at': None}
            for i in range(1, 21):
                seats[f"T2-B{i:02d}"] = {'status': 'available', 'locked_by': None, 'locked_at': None}
            
            self.seats_data[trip_id] = seats
            # Lazy init (No Save)

    def get_trip_seats(self, trip_id: str) -> Dict:
        if trip_id not in self.seats_data:
            self.initialize_trip_seats(trip_id)
        return self.seats_data.get(trip_id, {})

    def select_seat(self, trip_id: str, seat_id: str, client_id: str) -> Dict:
        with self.lock:
            if trip_id not in self.seats_data: return {'success': False, 'message': 'Chuyến không tồn tại'}
            if seat_id not in self.seats_data[trip_id]: return {'success': False, 'message': 'Ghế không tồn tại'}
            
            seat = self.seats_data[trip_id][seat_id]
            if seat['status'] != 'available':
                return {'success': False, 'message': f'Ghế đang {seat["status"]}'}
            
            seat['status'] = 'selecting'
            seat['locked_by'] = client_id
            seat['locked_at'] = time.time()
            
            self.save_trip_data(trip_id, self.seats_data[trip_id])
            return {'success': True, 'message': 'Chọn ghế thành công'}

    def unselect_seat(self, trip_id: str, seat_id: str, client_id: str) -> Dict:
        with self.lock:
            if trip_id not in self.seats_data or seat_id not in self.seats_data[trip_id]:
                return {'success': False, 'message': 'Lỗi dữ liệu'}
            
            seat = self.seats_data[trip_id][seat_id]
            if seat['locked_by'] != client_id:
                return {'success': False, 'message': 'Không chính chủ'}
            
            seat['status'] = 'available'
            seat['locked_by'] = None
            seat['locked_at'] = None
            
            self.save_trip_data(trip_id, self.seats_data[trip_id])
            return {'success': True, 'message': 'Đã bỏ chọn'}

    def book_seats(self, trip_id: str, seat_ids: List[str], client_id: str) -> Dict:
        with self.lock:
            if trip_id not in self.seats_data: return {'success': False, 'message': 'Lỗi trip'}
            
            for sid in seat_ids:
                if sid not in self.seats_data[trip_id]: return {'success': False, 'message': 'Lỗi seat'}
                s = self.seats_data[trip_id][sid]
                
                # Check Lock Ownership
                if s['status'] != 'selecting' or s['locked_by'] != client_id:
                    # Idempotency: Nếu đã book rồi -> Báo thành công (để Client không lỗi)
                    # Và báo action='existing' để Server không tạo Booking trùng
                    if s['status'] == 'booked' and s['locked_by'] == client_id:
                         return {'success': True, 'message': 'Vé đã được đặt thành công!', 'action': 'existing'}
                         
                    print(f"[Debug] BOOK FAIL: Seat={sid}, Status={s['status']}, LockedBy={s['locked_by']}, ReqClient={client_id}")
                    if s['status'] == 'booked' and s['locked_by'] == client_id:
                        return {'success': True, 'message': 'Vé đã được đặt thành công!', 'action': 'existing'}
                    return {'success': False, 'message': f'Ghế {sid} lỗi trạng thái'}
            
            # Commit Booking
            for sid in seat_ids:
                s = self.seats_data[trip_id][sid]
                s['status'] = 'booked'
                s['locked_at'] = time.time()
            
            self.save_trip_data(trip_id, self.seats_data[trip_id])
            return {'success': True, 'message': 'Đặt vé thành công'}

    def cleanup_expired_locks(self, timeout: int = 300):
        current_time = time.time()
        modified_trips = set()
        
        with self.lock:
            for trip_id, seats in self.seats_data.items():
                for seat in seats.values():
                    if seat['status'] == 'selecting' and seat['locked_at'] and (current_time - seat['locked_at'] > timeout):
                        seat['status'] = 'available'
                        seat['locked_by'] = None
                        seat['locked_at'] = None
                        modified_trips.add(trip_id)
            
            for trip_id in modified_trips:
                self.save_trip_data(trip_id, self.seats_data[trip_id])

    def get_available_seats_count(self, trip_id: str) -> int:
        if trip_id not in self.seats_data: return 0
        return sum(1 for s in self.seats_data[trip_id].values() if s['status'] == 'available')