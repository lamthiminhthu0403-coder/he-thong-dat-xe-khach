"""Script để generate Python code từ Protocol Buffers

Chạy script này để generate code từ proto files:
    python generate_proto.py
"""

import subprocess
import sys
import os

def generate_proto():
    """Generate Python code từ .proto files"""
    
    # Đường dẫn
    proto_file = "proto/bus_booking.proto"
    output_dir = "."
    
    # Kiểm tra proto file
    if not os.path.exists(proto_file):
        print(f"❌ Không tìm thấy file: {proto_file}")
        return False
    
    # Kiểm tra grpc_tools
    try:
        import grpc_tools.protoc
    except ImportError:
        print("❌ Chưa cài grpc_tools!")
        print("Cài đặt: pip install grpcio-tools")
        return False
    
    print("="*60)
    print("GENERATE PROTOCOL BUFFERS CODE")
    print("="*60)
    print(f"Proto file: {proto_file}")
    print(f"Output dir: {output_dir}")
    print()
    
    try:
        # Generate code
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"-I{os.path.dirname(proto_file)}",  # Include path
            f"--python_out={output_dir}",        # Python output
            f"--grpc_python_out={output_dir}",   # gRPC Python output
            proto_file                           # Proto file
        ]
        
        print("Đang chạy lệnh:", " ".join(cmd))
        print()
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Generate thành công!")
            print()
            print("Các file đã được tạo:")
            print("  - bus_booking_pb2.py")
            print("  - bus_booking_pb2_grpc.py")
            print()
            return True
        else:
            print("❌ Lỗi khi generate:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False


if __name__ == '__main__':
    success = generate_proto()
    sys.exit(0 if success else 1)

