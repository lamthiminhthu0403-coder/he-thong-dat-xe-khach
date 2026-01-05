# 🚌 Hệ Thống Đặt Vé Xe Khách

**Môn học:** Lập trình Mạng  
**Giao thức:** TCP (thao tác chính) + UDP (realtime sync ghế)

---

## � Cài đặt & Chạy

### 1. Tạo Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Cài thư viện
```bash
pip install flask flask-socketio flask-cors
```

### 3. Chạy Server (Terminal 1)
```bash
python server/server.py
```

### 4. Chạy Client (Terminal 2)
```bash
python client/client.py
```

### 5. Mở trình duyệt
```
http://localhost:3000
```