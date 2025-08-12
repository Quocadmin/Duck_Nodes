# 🦆 Duck Nodes for ComfyUI

**Duck Nodes** là một bộ mở rộng (extension) dành cho **ComfyUI**, cung cấp nhiều node tiện ích để tải dữ liệu từ nhiều nguồn khác nhau, xử lý văn bản, hình ảnh và tích hợp **hệ thống đăng nhập bảo mật** cho ComfyUI.

-----

## ✨ Tính năng chính

### 📂 Nodes Tải Dữ Liệu

Lấy dòng dữ liệu từ các tệp tin, nơi mỗi hàng được hiểu là một prompt riêng biệt, giúp tự động hóa quy trình làm việc.

  - **Duck - Load Google Sheet Row**  
    Lấy dòng dữ liệu từ Google Sheet (yêu cầu quyền xem công khai).

  - **Duck - Load Google Doc Line**  
    Lấy dòng văn bản từ Google Docs (yêu cầu quyền xem công khai).

  - **Duck - Load Excel Row**  
    Lấy dòng từ file Excel (.xlsx) lưu trên máy.

  - **Duck - Load Word Line**  
    Lấy dòng từ file Word (.docx) lưu trên máy.

  - **Duck - Load Prompt From File**  
    Lấy dòng từ file `.txt` lưu trên máy.

-----

### 🛠️ Nodes Tiện Ích & Xử Lý Ảnh

Các công cụ giúp xử lý văn bản và hình ảnh một cách linh hoạt.

  - **Duck - Text Replacer** Tìm kiếm và thay thế một chuỗi ký tự trong văn bản đầu vào.

  - **Duck - Add Text Overlay** Thêm một dải văn bản tùy chỉnh lên trên hoặc dưới ảnh. Hỗ trợ tùy chỉnh toàn diện: vị trí dải nền (trên, giữa, dưới), căn lề văn bản (trái, giữa, phải), màu sắc, cỡ chữ, độ cao của dải nền và độ trong suốt.

-----

## 📦 Cài đặt

### 1\. Tải và đặt extension

Clone repository này vào thư mục `custom_nodes` của ComfyUI:

```bash
cd ComfyUI/custom_nodes
```

```bash
git clone https://github.com/duckmartians/Duck_Nodes.git
```

### 2\. Cài đặt dependencies

Bộ node này tự động kiểm tra và cài đặt thư viện cần thiết khi khởi động ComfyUI.  
Tuy nhiên, bạn có thể cài thủ công bằng lệnh sau trong môi trường của ComfyUI:

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

-----

## 🚀 Sử dụng

### 1\. Khởi động ComfyUI

Chạy ComfyUI như bình thường, extension sẽ được tự động tải.
Khi lần đầu truy cập ComfyUI, bạn sẽ được yêu cầu **tạo username và password** để bảo vệ giao diện làm việc.

### 2\. Giao diện đăng nhập & Các tiện ích

Hệ thống đăng nhập được thiết kế với sự chú trọng đến bảo mật và trải nghiệm người dùng:

  - **Thiết lập linh hoạt:**
      - Lần đầu sử dụng, bạn sẽ được yêu cầu tạo tài khoản và mật khẩu để bảo vệ ComfyUI.
      - Nếu không có nhu cầu bảo mật, bạn có thể chọn **"Skip (Disable Login)"** để tắt hoàn toàn tính năng này.
  - **Giao diện đa ngôn ngữ:** Dễ dàng chuyển đổi qua lại giữa **Tiếng Anh** và **Tiếng Việt** ngay trên màn hình đăng nhập.
  - **Quản lý tài khoản:** Sau khi đăng nhập, bạn có thể truy cập chức năng **"Change Password"** để thay đổi mật khẩu một cách an toàn.
  - **Trải nghiệm thân thiện:**
      - Giao diện sẽ gửi **lời chào theo thời gian thực** (Chào buổi sáng, chiều, tối).
      - Biểu tượng con mắt (👁️) tại ô mật khẩu cho phép **hiển thị/ẩn mật khẩu** đang gõ, giúp bạn nhập chính xác hơn.

<img width="599" height="550" alt="image" src="https://github.com/user-attachments/assets/84c4fb4c-d1b8-4b70-ad56-d91d2ccd8679" />
<img width="1055" height="551" alt="image" src="https://github.com/user-attachments/assets/5ce203b6-2a55-4226-b565-8b9329930cb7" />

-----

### 3\. Sử dụng các node Duck

Trong ComfyUI, tìm trong **Category: Duck Nodes/** để thấy các node mới:
  - Duck - Load Google Sheet Row
  - Duck - Load Google Doc Line
  - Duck - Load Excel Row
  - Duck - Load Word Line
  - Duck - Load Prompt From File
  - Duck - Text Replacer
  - Duck - Add Text Overlay

<img width="1028" height="830" alt="image" src="https://github.com/user-attachments/assets/a8a244bc-af51-456b-bb8f-633b41fe1cbf" />

📌 **Cách hoạt động của các node tải dữ liệu:**

  - Khi bạn bật chế độ "control\_after\_generate" (ví dụ: increment) cho đầu vào `seed`, ComfyUI sẽ nhớ vị trí dòng cuối cùng đã đọc.
  - Lần chạy tiếp theo, nó tự động tăng chỉ số `seed` lên 1, rồi đọc prompt ở dòng mới theo đúng thứ tự.
  - Khi tới dòng cuối cùng, nó sẽ quay về dòng đầu tiên (hoạt động theo vòng lặp).

-----

## 🛡️ Bảo mật

  - **Mật khẩu** được lưu dưới dạng **hash bcrypt**, không bao giờ lưu dưới dạng văn bản thuần.  
  - **Token API** được tạo ra từ chuỗi hash của mật khẩu để đảm bảo an toàn khi truy cập qua API.  
  - **Session cookie** được mã hóa bằng một khóa ngẫu nhiên mỗi khi server khởi động.

-----

## 📝 Giấy phép

MIT License © 2025 Duck Martians AI Labs

Bạn được phép sử dụng, sửa đổi và phân phối phần mềm này cho mục đích cá nhân hoặc thương mại, miễn là giữ lại thông tin bản quyền.

-----
