"""Trip Manager - Quản lý chuyến xe

Chức năng:
- Load danh sách chuyến xe từ trips.json
- Tìm kiếm chuyến theo ngày, tuyến
- Lấy thông tin chuyến theo ID
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime


class TripManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.trips_file = os.path.join(data_dir, 'trips.json')
        self.trips: List[Dict] = []
        self.load_trips()
    
    def load_trips(self):
        """Load danh sách chuyến xe từ file JSON"""
        try:
            with open(self.trips_file, 'r', encoding='utf-8') as f:
                self.trips = json.load(f)
            print(f"[TripManager] Đã load {len(self.trips)} chuyến xe")
        except FileNotFoundError:
            print(f"[TripManager] Không tìm thấy file {self.trips_file}")
            self.trips = []
        except json.JSONDecodeError as e:
            print(f"[TripManager] Lỗi đọc file JSON: {e}")
            self.trips = []
    
    def get_all_trips(self) -> List[Dict]:
        """Lấy tất cả chuyến"""
        return self.trips
    
    def get_trip_by_id(self, trip_id: str) -> Optional[Dict]:
        """Tìm chuyến theo ID"""
        for trip in self.trips:
            if trip['id'] == trip_id:
                return trip
        return None
    
    def search_trips(self, route_id: str = None, date: str = None) -> List[Dict]:
        """Tìm kiếm chuyến theo tuyến và ngày"""
        results = self.trips
        
        if route_id:
            results = [t for t in results if t['route_id'] == route_id]
        
        if date:
            results = [t for t in results if t['date'] == date]
        
        # Sắp xếp theo giờ khởi hành
        results.sort(key=lambda x: x['departure_time'])
        
        return results
    
    def get_available_dates(self, route_id: str = None) -> List[str]:
        """Lấy danh sách ngày có chuyến"""
        trips = self.trips if not route_id else [t for t in self.trips if t['route_id'] == route_id]
        dates = sorted(list(set(t['date'] for t in trips)))
        return dates