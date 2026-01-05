"""Route Manager - Quản lý tuyến đường

Chức năng:
- Load danh sách tuyến từ routes.json
- Tìm kiếm tuyến theo điểm đi, điểm đến
- Lấy thông tin tuyến theo ID
"""

import json
import os
from typing import List, Dict, Optional


class RouteManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.routes_file = os.path.join(data_dir, 'routes.json')
        self.routes: List[Dict] = []
        self.load_routes()
    
    def load_routes(self):
        """Load danh sách tuyến từ file JSON"""
        try:
            with open(self.routes_file, 'r', encoding='utf-8') as f:
                self.routes = json.load(f)
            print(f"[RouteManager] Đã load {len(self.routes)} tuyến")
        except FileNotFoundError:
            print(f"[RouteManager] Không tìm thấy file {self.routes_file}")
            self.routes = []
        except json.JSONDecodeError as e:
            print(f"[RouteManager] Lỗi đọc file JSON: {e}")
            self.routes = []
    
    def get_all_routes(self) -> List[Dict]:
        """Lấy tất cả tuyến"""
        return self.routes
    
    def get_route_by_id(self, route_id: str) -> Optional[Dict]:
        """Tìm tuyến theo ID"""
        for route in self.routes:
            if route['id'] == route_id:
                return route
        return None
    
    def search_routes(self, from_city: str = None, to_city: str = None) -> List[Dict]:
        """Tìm kiếm tuyến theo điểm đi và điểm đến"""
        results = self.routes
        
        if from_city:
            results = [r for r in results if r['from_city'].lower() == from_city.lower()]
        
        if to_city:
            results = [r for r in results if r['to_city'].lower() == to_city.lower()]
        
        return results
    
    def get_all_cities(self) -> Dict[str, List[str]]:
        """Lấy danh sách tất cả thành phố (from và to)"""
        from_cities = set()
        to_cities = set()
        
        for route in self.routes:
            from_cities.add(route['from_city'])
            to_cities.add(route['to_city'])
        
        return {
            'from_cities': sorted(list(from_cities)),
            'to_cities': sorted(list(to_cities))
        }