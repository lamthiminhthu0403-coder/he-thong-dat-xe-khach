"""Email Service - Gửi email xác nhận đặt vé

Chức năng:
- Gửi email xác nhận khi đặt vé thành công
- HTML email với thông tin chi tiết vé
- Hỗ trợ SMTP với TLS/SSL
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
import os


class EmailService:
    def __init__(self, smtp_server: str = 'smtp.gmail.com', smtp_port: int = 587,
                 username: Optional[str] = None, password: Optional[str] = None,
                 use_tls: bool = True):
        """
        Khởi tạo Email Service
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port (587 cho TLS, 465 cho SSL)
            username: Email username
            password: Email password (hoặc App Password)
            use_tls: Sử dụng TLS (True) hay SSL (False)
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        
        # Lấy từ environment variables nếu không truyền vào
        if not self.username:
            self.username = os.getenv('EMAIL_USERNAME', 'lamthiminhthu.0403@gmail.com')
        if not self.password:
            self.password = os.getenv('EMAIL_PASSWORD', 'wwjx guyw cclw cgmv')
        
        self.enabled = bool(self.username and self.password)
        
        if not self.enabled:
            print("[EmailService] ⚠️ Email service không được kích hoạt (thiếu username/password)")
        else:
            print(f"[EmailService] ✅ Đã khởi tạo với SMTP: {smtp_server}:{smtp_port}")
    
    def send_booking_confirmation(self, to_email: str, booking_data: Dict) -> bool:
        """
        Gửi email xác nhận đặt vé
        
        Args:
            to_email: Email người nhận
            booking_data: Dictionary chứa thông tin đặt vé
            
        Returns:
            True nếu gửi thành công, False nếu có lỗi
        """
        if not self.enabled:
            print(f"[EmailService] ⚠️ Bỏ qua gửi email vì service chưa được cấu hình")
            return False
        
        if not to_email or '@' not in to_email:
            print(f"[EmailService] ⚠️ Email không hợp lệ: {to_email}")
            return False
        
        try:
            # Tạo message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = f'✅ Xác nhận đặt vé - Mã vé: {booking_data.get("booking_id", "N/A")}'
            
            # Tạo nội dung email HTML
            html_body = self._create_booking_email_html(booking_data)
            
            # Tạo nội dung text đơn giản
            text_body = self._create_booking_email_text(booking_data)
            
            # Attach cả hai (HTML và text)
            part1 = MIMEText(text_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Gửi email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            print(f"[EmailService] ✅ Đã gửi email xác nhận đến {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"[EmailService] ❌ Lỗi xác thực SMTP: {e}")
            print("[EmailService] 💡 Gợi ý: Kiểm tra lại username/password hoặc sử dụng App Password cho Gmail")
            return False
        except smtplib.SMTPException as e:
            print(f"[EmailService] ❌ Lỗi SMTP: {e}")
            return False
        except Exception as e:
            print(f"[EmailService] ❌ Lỗi gửi email: {e}")
            return False
    
    def _create_booking_email_html(self, booking_data: Dict) -> str:
        """Tạo nội dung email HTML"""
        booking_id = booking_data.get('booking_id', 'N/A')
        customer_name = booking_data.get('customer_name', 'Khách hàng')
        from_city = booking_data.get('from_city', 'N/A')
        to_city = booking_data.get('to_city', 'N/A')
        date = booking_data.get('date', 'N/A')
        departure_time = booking_data.get('departure_time', 'N/A')
        bus_code = booking_data.get('bus_code', 'N/A')
        bus_type = booking_data.get('bus_type', 'Giường nằm')
        seats = booking_data.get('seats', [])
        total_price = booking_data.get('total_price', 0)
        
        seats_str = ', '.join(seats) if isinstance(seats, list) else str(seats)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .booking-id {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #667eea;
                    margin: 20px 0;
                }}
                .info-box {{
                    background: white;
                    padding: 20px;
                    margin: 15px 0;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                }}
                .info-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                }}
                .info-row:last-child {{
                    border-bottom: none;
                }}
                .label {{
                    font-weight: bold;
                    color: #666;
                }}
                .value {{
                    color: #333;
                }}
                .total-price {{
                    font-size: 20px;
                    color: #22c55e;
                    font-weight: bold;
                    text-align: center;
                    margin-top: 20px;
                    padding: 15px;
                    background: #f0fdf4;
                    border-radius: 8px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>✅ Xác nhận đặt vé thành công!</h1>
            </div>
            
            <div class="content">
                <p>Xin chào <strong>{customer_name}</strong>,</p>
                <p>Cảm ơn bạn đã đặt vé tại hệ thống của chúng tôi. Đơn đặt vé của bạn đã được xác nhận.</p>
                
                <div class="booking-id">
                    Mã vé: {booking_id}
                </div>
                
                <div class="info-box">
                    <h3 style="margin-top: 0;">📋 Thông tin đặt vé</h3>
                    <div class="info-row">
                        <span class="label">Tuyến:</span>
                        <span class="value"><strong>{from_city}</strong> → <strong>{to_city}</strong></span>
                    </div>
                    <div class="info-row">
                        <span class="label">Ngày khởi hành:</span>
                        <span class="value">{date}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Giờ khởi hành:</span>
                        <span class="value">{departure_time}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Xe:</span>
                        <span class="value">{bus_code} ({bus_type})</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Ghế đã đặt:</span>
                        <span class="value"><strong>{seats_str}</strong></span>
                    </div>
                    <div class="info-row">
                        <span class="label">Số lượng ghế:</span>
                        <span class="value">{len(seats) if isinstance(seats, list) else 1} ghế</span>
                    </div>
                </div>
                
                <div class="total-price">
                    Tổng tiền: {total_price:,} VNĐ
                </div>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 20px;">
                    <strong>📌 Lưu ý:</strong>
                    <ul style="margin: 10px 0;">
                        <li>Vui lòng đến bến xe trước giờ khởi hành <strong>ít nhất 30 phút</strong></li>
                        <li>Mang theo <strong>CCCD/CMND</strong> để làm thủ tục</li>
                        <li>Mã vé: <strong>{booking_id}</strong> - Hãy lưu lại để tra cứu</li>
                    </ul>
                </div>
            </div>
            
            <div class="footer">
                <p>Trân trọng,<br><strong>Hệ thống đặt vé xe khách</strong></p>
                <p style="font-size: 12px; color: #999;">Đây là email tự động, vui lòng không trả lời email này.</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _create_booking_email_text(self, booking_data: Dict) -> str:
        """Tạo nội dung email dạng text đơn giản"""
        booking_id = booking_data.get('booking_id', 'N/A')
        customer_name = booking_data.get('customer_name', 'Khách hàng')
        from_city = booking_data.get('from_city', 'N/A')
        to_city = booking_data.get('to_city', 'N/A')
        date = booking_data.get('date', 'N/A')
        departure_time = booking_data.get('departure_time', 'N/A')
        bus_code = booking_data.get('bus_code', 'N/A')
        seats = booking_data.get('seats', [])
        total_price = booking_data.get('total_price', 0)
        
        seats_str = ', '.join(seats) if isinstance(seats, list) else str(seats)
        
        text = f"""
Xác nhận đặt vé thành công!

Xin chào {customer_name},

Cảm ơn bạn đã đặt vé tại hệ thống của chúng tôi.

Mã vé: {booking_id}

Thông tin đặt vé:
- Tuyến: {from_city} → {to_city}
- Ngày khởi hành: {date}
- Giờ khởi hành: {departure_time}
- Xe: {bus_code}
- Ghế đã đặt: {seats_str}
- Tổng tiền: {total_price:,} VNĐ

Lưu ý:
- Vui lòng đến bến xe trước giờ khởi hành ít nhất 30 phút
- Mang theo CCCD/CMND để làm thủ tục
- Mã vé: {booking_id} - Hãy lưu lại để tra cứu

Trân trọng,
Hệ thống đặt vé xe khách
        """
        return text.strip()

