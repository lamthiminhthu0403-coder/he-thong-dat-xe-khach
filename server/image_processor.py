"""Image Processor - Xử lý và nén ảnh

Chức năng:
- Compress images trước khi lưu
- Resize images theo kích thước tối đa
- Hỗ trợ nhiều format: JPEG, PNG, GIF
"""

from PIL import Image
import io
from typing import Optional, Tuple
from config import MULTIMEDIA_CONFIG


class ImageProcessor:
    """Xử lý và nén ảnh"""
    
    @staticmethod
    def compress_image(image_data: bytes, max_size: Tuple[int, int] = None, 
                      quality: int = None) -> Optional[bytes]:
        """
        Compress image trước khi lưu
        
        Args:
            image_data: Dữ liệu binary của ảnh
            max_size: Kích thước tối đa (width, height). Default từ config
            quality: Chất lượng JPEG (1-100). Default từ config
            
        Returns:
            Compressed image data hoặc None nếu có lỗi
        """
        try:
            if not MULTIMEDIA_CONFIG['image_compression']['enabled']:
                return image_data
            
            max_size = max_size or MULTIMEDIA_CONFIG['image_compression']['max_size']
            quality = quality or MULTIMEDIA_CONFIG['image_compression']['quality']
            
            # Mở ảnh
            img = Image.open(io.BytesIO(image_data))
            
            # Convert RGBA sang RGB nếu cần (để save JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Resize nếu cần
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Compress và save
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            
            compressed_data = output.getvalue()
            
            # Kiểm tra xem có thực sự nhỏ hơn không
            if len(compressed_data) < len(image_data):
                print(f"[ImageProcessor] ✅ Đã nén ảnh: {len(image_data)} → {len(compressed_data)} bytes")
                return compressed_data
            else:
                print(f"[ImageProcessor] ⚠️ Ảnh không nhỏ hơn sau khi nén, giữ nguyên")
                return image_data
                
        except Exception as e:
            print(f"[ImageProcessor] ❌ Lỗi xử lý ảnh: {e}")
            return image_data  # Trả về ảnh gốc nếu có lỗi
    
    @staticmethod
    def validate_image(image_data: bytes) -> bool:
        """Kiểm tra xem file có phải là ảnh hợp lệ không"""
        try:
            img = Image.open(io.BytesIO(image_data))
            img.verify()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_image_info(image_data: bytes) -> Optional[dict]:
        """Lấy thông tin ảnh (kích thước, format, etc.)"""
        try:
            img = Image.open(io.BytesIO(image_data))
            return {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height
            }
        except Exception as e:
            print(f"[ImageProcessor] Lỗi đọc thông tin ảnh: {e}")
            return None

