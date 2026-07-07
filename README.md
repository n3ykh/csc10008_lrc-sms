# LRC-SMS (LAN Remote Control - System Management Service)
**Dự án:** Giám sát và Điều khiển Máy tính từ xa qua Mạng LAN (Đồ án môn học MMT - HCMUS)

LRC-SMS là hệ thống quản trị mạng cục bộ (LAN) dựa trên kiến trúc Gateway - Agent sử dụng giao thức truyền thông thời gian thực WebSockets và FastAPI. Hệ thống cung cấp các luồng giám sát tài nguyên, hình ảnh và điều khiển nguồn điện an toàn với cơ chế bảo mật Zero-Trust (Bắt buộc xác nhận quyền từ người dùng vật lý).

---

## Cấu trúc Thư mục Dự án

Vui lòng đảm bảo mã nguồn được sắp xếp theo đúng cấu trúc sau trước khi khởi chạy:

LRC-SMS-Project/
 |-- agent/                 # Chứa phân hệ Agent chạy ngầm trên máy trạm
 |   |-- agent.py
 |-- webapp/                # Chứa phân hệ Gateway Server và Giao diện Web
 |   |-- main.py
 |   |-- index.html
 |-- requirements.txt       # Danh sách các thư viện Python cần thiết
 |-- run.bat                # Script tự động hóa khởi chạy hệ thống (1-click)
 |-- README.md              # Tài liệu hướng dẫn sử dụng

---

## Yêu cầu Hệ thống & Cài đặt

### 1. Yêu cầu môi trường
- Hệ điều hành: Microsoft Windows 10 hoặc Windows 11 (Máy trạm bắt buộc dùng Windows để tương tác API hệ thống).
- Python: Khuyến nghị cài đặt Python phiên bản 3.10 trở lên. (Lưu ý: Nhớ tích chọn "Add Python to PATH" trong quá trình cài đặt Python).

### 2. Cài đặt các gói thư viện (Dependencies)
Mở cửa sổ Command Prompt (CMD) hoặc PowerShell tại thư mục gốc của dự án và chạy câu lệnh sau để cài đặt toàn bộ các thư viện cần thiết:

pip install -r requirements.txt

(Nếu không dùng file requirements.txt, có thể cài đặt thủ công bằng lệnh sau):
pip install fastapi uvicorn websockets psutil opencv-python pillow pynput pywin32

---

## Hướng dẫn Sử dụng (Tutorial)

Hệ thống được thiết kế để tự động hóa tối đa. Thực hiện theo các bước sau để khởi chạy:

### Bước 1: Khởi động Hệ thống trên Máy trạm (Máy bị điều khiển)
1. Truy cập vào thư mục gốc của dự án.
2. Nháy đúp chuột vào tệp run_system.bat.
3. Cửa sổ User Account Control (UAC) của Windows sẽ hiện ra yêu cầu quyền quản trị, hãy nhấn YES.
4. Hệ thống sẽ tự động bật 2 cửa sổ Console:
   - Cửa sổ 1: Khởi chạy Gateway Server (mở cổng 8000).
   - Cửa sổ 2: Khởi chạy Agent Engine (kết nối ngầm vào Gateway).

### Bước 2: Truy cập Bảng điều khiển từ xa (Máy Quản trị viên)
1. Tại một máy tính khác trong cùng mạng LAN, mở trình duyệt web.
2. Gõ địa chỉ IP của Máy trạm kèm theo cổng 8000. 
   - Ví dụ: http://192.168.1.10:8000
3. Chờ 1 giây, nếu góc phải màn hình hiện nhãn Online màu xanh, bạn đã kết nối thành công.

---

## Các Phân hệ Chức năng Chính

1. Quản lý Tiến trình (Process Manager):
   - Quét và hiển thị mức độ tiêu thụ CPU, RAM của các ứng dụng đang chạy.
   - Nút KILL: Gửi lệnh cưỡng chế đóng phần mềm từ xa.

2. Giám sát Hình ảnh (Screen & Webcam Stream):
   - Bảo mật: Khi Admin nhấn xem, màn hình máy trạm sẽ hiện Popup xin quyền. Tính năng chỉ hoạt động khi người dùng trạm bấm Đồng ý.
   - Có đèn cảnh báo chấm đỏ chớp tắt trên máy trạm khi Camera đang được live stream.

3. Theo dõi Bàn phím (Keylogger):
   - Ghi nhận thao tác gõ phím theo thời gian thực (yêu cầu cấp quyền).
   - Tự động nhận diện và đính kèm tên cửa sổ ứng dụng mà người dùng đang gõ (VD: Notepad, Chrome).

4. Quản lý Tệp tin (File Sandbox):
   - Cho phép Upload và Download tệp tin giữa Admin và Máy trạm.
   - Bảo mật: Tệp tin bị giới hạn nghiêm ngặt bên trong thư mục sandbox_folder. Thuật toán chặn tuyệt đối các hành vi truy cập lùi thư mục (Path Traversal).

5. Quản trị Nguồn điện (Power Control):
   - Hỗ trợ các lệnh: Tắt máy (Shutdown), Khởi động lại (Restart), và Chế độ ngủ (Sleep).
   - Mẹo test: Khi gọi lệnh Shutdown, Windows sẽ đếm ngược 10 giây. Bạn có thể mở CMD trên máy trạm và gõ "shutdown /a" để hủy lệnh tắt máy nếu chỉ đang thử nghiệm.