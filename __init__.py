import importlib.util
import sys
import subprocess
import os
import traceback

# --- Tự động kiểm tra và cài đặt thư viện ---
def install_required_packages():
    """
    Đọc file requirements.txt và tự động cài đặt các gói còn thiếu.
    """
    print("--- DucK Nodes: Checking for missing package dependencies ---")
    
    # Lấy đường dẫn đến file requirements.txt trong cùng thư mục
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")

    if not os.path.exists(requirements_path):
        return

    # Lấy đường dẫn đến python.exe đang chạy ComfyUI
    python_executable = sys.executable
    
    # Đọc các thư viện cần thiết
    with open(requirements_path, 'r', encoding='utf-8') as f:
        required_packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Ánh xạ tên gói pip với tên module khi import (để kiểm tra)
    package_map = {
        'python-docx': 'docx',
        'pandas': 'pandas',
        'requests': 'requests',
        'openpyxl': 'openpyxl'
    }

    # Kiểm tra và cài đặt từng gói
    for package_name in required_packages:
        try:
            import_name = package_map.get(package_name, package_name)
            if importlib.util.find_spec(import_name) is None:
                print(f"Installing missing package: {package_name}")
                subprocess.run([python_executable, "-m", "pip", "install", package_name], check=True, capture_output=True, text=True)
                print(f"Successfully installed {package_name}.")
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to install '{package_name}'. Please install it manually. Pip output:\n{e.stdout}\n{e.stderr}")
        except Exception as e:
            print(f"An unexpected error occurred while trying to install {package_name}: {e}")

# Chạy hàm cài đặt khi node được tải
install_required_packages()

# --- Tải các node như bình thường ---
try:
    from .duck_nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    print(f"✅ Đã tải {len(NODE_CLASS_MAPPINGS)} nodes từ gói Duck Nodes.")

    # Import thêm hệ thống login
    from .password import *  # Đăng ký route /login, /logout và middleware
    print("🔒 Đã kích hoạt hệ thống đăng nhập cho Duck Nodes.")

    __all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
except Exception:
    print("❌ Lỗi khi tải các lớp node từ duck_nodes.py hoặc password.py")
    traceback.print_exc()
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
    __all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
