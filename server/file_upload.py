"""File Upload Handler - Xử lý upload nhiều file

Chức năng:
- Nhận file qua TCP socket
- Lưu file vào thư mục uploads
- Hỗ trợ nhiều file cùng lúc
"""

import os
import hashlib
from typing import Dict
from image_processor import ImageProcessor
from config import MULTIMEDIA_CONFIG


class FileUploadHandler:
    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir
        self.ensure_upload_dir()
    
    def ensure_upload_dir(self):
        """Tạo thư mục upload nếu chưa tồn tại"""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
            print(f"[FileUpload] Đã tạo thư mục: {self.upload_dir}")
    
    def save_file(self, filename: str, file_data: bytes, booking_id: str = None, 
                  compress_image: bool = True) -> Dict:
        """Lưu file vào thư mục uploads
        
        Args:
            filename: Tên file gốc
            file_data: Dữ liệu binary của file
            booking_id: ID đặt vé (tùy chọn)
        
        Returns:
            {'success': bool, 'filepath': str, 'message': str}
        """
        try:
            # Kiểm tra kích thước file
            max_size = MULTIMEDIA_CONFIG['max_file_size']
            if len(file_data) > max_size:
                return {
                    'success': False,
                    'filepath': None,
                    'message': f'File quá lớn. Kích thước tối đa: {max_size // 1024 // 1024}MB'
                }
            
            # Xử lý ảnh: compress nếu là ảnh
            original_size = len(file_data)
            base_name, ext = os.path.splitext(filename)
            
            if compress_image and ext.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                # Kiểm tra xem có phải ảnh hợp lệ không
                if ImageProcessor.validate_image(file_data):
                    compressed = ImageProcessor.compress_image(file_data)
                    if compressed:
                        file_data = compressed
                        print(f"[FileUpload] Đã nén ảnh: {original_size} → {len(file_data)} bytes")
            
            # Tạo tên file duy nhất (thêm hash để tránh trùng)
            file_hash = hashlib.md5(file_data).hexdigest()[:8]
            
            if booking_id:
                unique_filename = f"{booking_id}_{base_name}_{file_hash}{ext}"
            else:
                unique_filename = f"{base_name}_{file_hash}{ext}"
            
            filepath = os.path.join(self.upload_dir, unique_filename)
            
            # Lưu file
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            print(f"[FileUpload] Đã lưu file: {unique_filename} ({len(file_data)} bytes)")
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': unique_filename,
                'message': 'Upload thành công'
            }
        
        except Exception as e:
            print(f"[FileUpload] Lỗi lưu file: {e}")
            return {
                'success': False,
                'filepath': None,
                'message': f'Lỗi: {str(e)}'
            }
    
    def save_multiple_files(self, files: list, booking_id: str = None) -> Dict:
        """Lưu nhiều file cùng lúc
        
        Args:
            files: List of {'filename': str, 'data': bytes}
            booking_id: ID đặt vé
        
        Returns:
            {'success': bool, 'files': list, 'message': str}
        """
        saved_files = []
        failed_files = []
        
        for file_info in files:
            result = self.save_file(
                file_info['filename'],
                file_info['data'],
                booking_id
            )
            
            if result['success']:
                saved_files.append(result['filename'])
            else:
                failed_files.append(file_info['filename'])
        
        if failed_files:
            return {
                'success': False,
                'files': saved_files,
                'message': f'Một số file lỗi: {failed_files}'
            }
        
        return {
            'success': True,
            'files': saved_files,
            'message': f'Đã upload {len(saved_files)} file'
        }
