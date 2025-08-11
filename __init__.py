import importlib.util
import sys
import subprocess
import os
import traceback

def install_required_packages():
    print("--- Duck Nodes: Checking for missing package dependencies ---")
    requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(requirements_path):
        return
    python_executable = sys.executable
    with open(requirements_path, 'r', encoding='utf-8') as f:
        required_packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    package_map = {
        'python-docx': 'docx',
        'pandas': 'pandas',
        'requests': 'requests',
        'openpyxl': 'openpyxl',
        'aiohttp_session': 'aiohttp_session',
        'bcrypt': 'bcrypt',
        'Jinja2': 'jinja2' 
    }

    for package_name in required_packages:
        try:
            import_name = package_map.get(package_name, package_name)
            if importlib.util.find_spec(import_name) is None:
                print(f"Installing missing package: {package_name}")
                subprocess.run([python_executable, "-m", "pip", "install", package_name], check=True, capture_output=True, text=True)
                print(f"Successfully installed {package_name}.")
        except Exception as e:
            print(f"ERROR: Failed to install '{package_name}'. Please install it manually. Details: {e}")

install_required_packages()

try:
    from .duck_nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    
    print(f"✅ Đã tải {len(NODE_CLASS_MAPPINGS)} nodes từ gói Duck Nodes.")
    print("🔒 Hệ thống đăng nhập đã được tích hợp và kích hoạt.")

    __all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

except Exception:
    print("❌ Lỗi nghiêm trọng khi tải Duck Nodes. Vui lòng kiểm tra lại file duck_nodes.py.")
    traceback.print_exc()
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
    __all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']