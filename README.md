# 🦆 Duck Nodes for ComfyUI

**Duck Nodes** là một bộ mở rộng (extension) dành cho **ComfyUI**, cung cấp nhiều node tiện ích để tải dữ liệu từ nhiều nguồn khác nhau (Google Sheets, Google Docs, Excel, Word, file TXT, v.v.) và tích hợp **hệ thống đăng nhập bảo mật** cho ComfyUI.

---

## ✨ Tính năng chính

### 📂 Nodes xử lý dữ liệu
  Lấy dòng dữ liệu từ các tệp dữ liệu lớn, mỗi hàng được hiểu là một prompt.

- **Duck - Load Google Sheet Row**  
  Lấy dòng dữ liệu từ Google Sheet (công khai).
  
- **Duck - Load Google Doc Line**  
  Lấy dòng văn bản từ Google Docs (công khai).

- **Duck - Load Excel Row**  
  Lấy dòng từ file Excel (.xlsx) lưu trên máy.

- **Duck - Load Word Line**  
  Lấy dòng từ file Word (.docx) lưu trên máy.

- **Duck - Load Prompt From File**  
  Lấy dòng từ file `.txt` lưu trên máy.

### 🔒 Hệ thống đăng nhập bảo mật
- Trang login đẹp, hỗ trợ **username + password**.
- Mã hóa mật khẩu bằng **bcrypt**.
- Hỗ trợ xác thực bằng **Bearer Token** hoặc query `?token=...`.
- Session bảo mật bằng **EncryptedCookieStorage**.
- Middleware kiểm tra quyền truy cập trước khi vào ComfyUI.

---

## 📦 Cài đặt

### 1. Tải và đặt extension
Clone repository này vào thư mục `custom_nodes` của ComfyUI:
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/duckmartians/duck-nodes.git
```

### 2. Cài đặt dependencies
Bộ node này tự động kiểm tra và cài đặt thư viện cần thiết khi khởi động ComfyUI.  
Tuy nhiên, bạn có thể cài thủ công:
```bash
pip install -r requirements.txt
```

**`requirements.txt` gồm:**
```txt
pandas
requests
openpyxl
python-docx
aiohttp_session
bcrypt
Jinja2
```

---

## 🚀 Sử dụng

### 1. Khởi động ComfyUI
Chạy ComfyUI như bình thường, extension sẽ được tự động tải.
Khi lần đầu truy cập ComfyUI, bạn sẽ được yêu cầu **tạo username và password**.
<img width="822" height="636" alt="image" src="https://github.com/user-attachments/assets/00f3240f-cfa9-47db-92c2-1c5218395c15" />


### 2. Truy cập trang đăng nhập
Mở trình duyệt:
```
http://127.0.0.1:8188/login
```
- Nhập **username** và **password** để đăng nhập.
- Nếu muốn gọi API trực tiếp, có thể dùng **token** (lấy từ file `login/PASSWORD` trong thư mục cài ComfyUI).

### 3. Sử dụng các node Duck
Trong ComfyUI, tìm trong **Category: Duck Nodes/** để thấy các node mới:
- Duck - Load Google Sheet Row
- Duck - Load Google Doc Line
- Duck - Load Excel Row
- Duck - Load Word Line
- Duck - Load Prompt From File

---

## 🛡️ Bảo mật

- **Mật khẩu** được lưu dưới dạng **hash bcrypt**, không lưu plaintext.  
- **Token API** là chuỗi hash của mật khẩu.  
- **Session cookie** được mã hóa bằng key ngẫu nhiên khi server khởi động.

---

## 📁 Cấu trúc thư mục

```
duck-nodes/
│
├── duck_nodes.py       # Định nghĩa các node xử lý dữ liệu
├── password.py         # Hệ thống login & middleware bảo mật
├── __init__.py         # Khởi tạo, auto-install dependencies
├── login.html          # Giao diện trang đăng nhập
├── requirements.txt    # Danh sách thư viện cần thiết
└── README.md           # Tài liệu hướng dẫn (file này)
```

---

## 🖼️ Giao diện đăng nhập
<img width="882" height="512" alt="image" src="https://github.com/user-attachments/assets/b12cb978-8a5a-4c06-87b7-1211eb1ddeda" />

---

## 📝 Giấy phép

MIT License © 2025 Duck VN

Bạn được phép sử dụng, sửa đổi và phân phối phần mềm này cho mục đích cá nhân hoặc thương mại, miễn là giữ lại thông tin bản quyền.

---
