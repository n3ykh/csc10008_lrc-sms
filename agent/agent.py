import threading
import time
import json
import asyncio
import websockets
import tkinter as tk
from tkinter import messagebox
import psutil
import cv2
from PIL import ImageGrab
import io
import base64
import gc
import win32gui
from pynput import keyboard
import os
import socket
import subprocess

# ==========================================================
# TỰ ĐỘNG LẤY TÊN MÁY THỰC TẾ & KHỞI TẠO ĐƯỜNG DẪN GATEWAY
# ==========================================================
DEVICE_NAME = socket.gethostname() 
GATEWAY_URL = f"ws://127.0.0.1:8000/ws/agent/{DEVICE_NAME}"

print(f"=========================================")
print(f"[*] TÊN THIẾT BỊ PHÁT HIỆN ĐƯỢC: {DEVICE_NAME}")
print(f"[*] URL KẾT NỐI GATEWAY: {GATEWAY_URL}")
print(f"=========================================")

# ==========================================================
# 1. ĐỊNH NGHĨA CLASS BẢO MẬT & POPUP TRỰC QUAN (XIN QUYỀN)
# ==========================================================
class AgentSecurityAlert:
    def __init__(self):
        self.webcam_active = False

    def show_consent_popup(self, module_name):
        """Hiển thị Popup xin quyền người dùng trước khi giám sát"""
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        response = messagebox.askyesno(
            "CẢNH BÁO AN NINH SYSTEM",
            f"Quản trị viên yêu cầu giám sát: [{module_name.upper()}].\nBạn có đồng ý cấp quyền không?"
        )
        root.destroy()
        return response

    def _render_red_dot_widget(self):
        """Hiển thị chấm đỏ nhấp nháy cảnh báo Webcam đang hoạt động"""
        window = tk.Tk()
        window.title("WEBCAM_ALERT")
        window.overrideredirect(True)
        window.geometry("120x40+10+10")
        window.attributes("-topmost", True)
        window.configure(bg='black')
        label = tk.Label(window, text="● WEBCAM LIVE", fg="red", bg="black", font=("Arial", 10, "bold"))
        label.pack(expand=True)
        
        def flash():
            if self.webcam_active:
                current_fg = label.cget("fg")
                label.configure(fg="black" if current_fg == "red" else "red")
                window.after(500, flash)
            else:
                window.quit()  # BẢO MẬT: Dùng quit() thay vì destroy() để thoát vòng lặp an toàn
                
        flash()
        window.mainloop()
        
        try:
            window.destroy() # Dọn dẹp cửa sổ ở bên ngoài vòng lặp
        except:
            pass
        window.mainloop()

    def start_visual_alert(self):
        self.webcam_active = True
        threading.Thread(target=self._render_red_dot_widget, daemon=True).start()

    def stop_visual_alert(self):
        self.webcam_active = False

# Khởi tạo đối tượng bảo mật toàn cục
security = AgentSecurityAlert()

# Khởi tạo thư mục Sandbox an toàn phục vụ quản lý File
SANDBOX_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "sandbox_folder"))
if not os.path.exists(SANDBOX_DIR):
    os.makedirs(SANDBOX_DIR)

# ==========================================================
# 2. QUẢN LÝ TIẾN TRÌNH HỆ THỐNG (PROCESS MANAGER)
# ==========================================================
class ProcessManager:
    """Xử lý nghiệp vụ đọc dữ liệu hệ thống Windows và can thiệp Tiến trình"""
    
    @staticmethod
    def get_all_processes():
        process_list = []
        # Lấy tổng số luồng (nhân logic) của CPU máy trạm
        cpu_cores = psutil.cpu_count(logical=True) or 1
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                pinfo = proc.info
                ram_mb = (pinfo['memory_info'].rss / (1024 * 1024)) if pinfo['memory_info'] else 0
                
                # CHUẨN HÓA CPU: Chia cho số lượng nhân để quy về thang 0-100%
                raw_cpu = pinfo['cpu_percent'] or 0
                real_cpu = round(raw_cpu / cpu_cores, 1)

                process_list.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'] or "Unknown",
                    "cpu": real_cpu,
                    "ram": round(ram_mb, 2)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception as e:
                continue
        return process_list

    @staticmethod
    def kill_process(pid):
        try:
            psutil.Process(pid).kill()
            return True
        except:
            return False

# ==========================================================
# 3. QUẢN LÝ TỆP TIN VÀ KHÓA ĐƯỜNG DẪN (FILE MANAGER)
# ==========================================================
class FileManager:
    """Quản lý tệp tin an toàn với cơ chế Sandboxing chống Path Traversal"""
    @staticmethod
    def is_safe_path(path):
        return os.path.abspath(path).startswith(SANDBOX_DIR)

    @staticmethod
    def list_files():
        files = []
        for f in os.listdir(SANDBOX_DIR):
            full_path = os.path.join(SANDBOX_DIR, f)
            if os.path.isfile(full_path):
                size_kb = os.path.getsize(full_path) / 1024
                files.append({"name": f, "size": round(size_kb, 2)})
        return files

    @staticmethod
    def read_file(filename):
        path = os.path.join(SANDBOX_DIR, filename)
        if FileManager.is_safe_path(path) and os.path.exists(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        return None

    @staticmethod
    def save_file(filename, base64_data):
        path = os.path.join(SANDBOX_DIR, filename)
        if FileManager.is_safe_path(path):
            with open(path, "wb") as f:
                f.write(base64.b64decode(base64_data))
            return True
        return False

# ==========================================================
# 4. QUẢN TRỊ NGUỒN ĐIỆN HỆ THỐNG (POWER MANAGER)
# ==========================================================
class PowerManager:
    """Quản lý Nguồn điện máy trạm (Yêu cầu chạy Terminal với quyền Run as Administrator)"""
    @staticmethod
    def shutdown():
        try:
            # Thêm cờ /f để ép đóng ứng dụng kẹt, /t 10 để đếm ngược 10 giây
            res = subprocess.run(["shutdown", "/s", "/f", "/t", "10"], capture_output=True, text=True, shell=True)
            if res.returncode == 0 or "1190" in res.stderr or "1115" in res.stderr:
                return True, "Hệ thống sẽ TẮT NGUỒN sau 10 giây! (Mẹo: Mở CMD gõ 'shutdown /a' để hủy nếu đang test)"
            else:
                err_msg = res.stderr or res.stdout or "Thiếu quyền Administrator!"
                return False, f"Lỗi Windows (Code {res.returncode}): {err_msg.strip()}"
        except Exception as e:
            return False, f"Lỗi thực thi lệnh Tắt máy: {str(e)}"

    @staticmethod
    def restart():
        try:
            # Thêm cờ /f để ép khởi động lại sau 10 giây
            res = subprocess.run(["shutdown", "/r", "/f", "/t", "10"], capture_output=True, text=True, shell=True)
            if res.returncode == 0 or "1190" in res.stderr or "1115" in res.stderr:
                return True, "Hệ thống sẽ KHỞI ĐỘNG LẠI sau 10 giây! (Mẹo: Mở CMD gõ 'shutdown /a' để hủy nếu đang test)"
            else:
                err_msg = res.stderr or res.stdout or "Thiếu quyền Administrator!"
                return False, f"Lỗi Windows (Code {res.returncode}): {err_msg.strip()}"
        except Exception as e:
            return False, f"Lỗi thực thi lệnh Khởi động lại: {str(e)}"

    @staticmethod
    def sleep():
        try:
            # Dùng PowerShell gọi .NET System.Windows.Forms đảm bảo nhạy 100% trên Win 10/11
            cmd = 'powershell -command "Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState(\'Suspend\', $false, $false)"'
            res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if res.returncode == 0:
                return True, "Đã gửi lệnh đưa máy vào chế độ Ngủ (Sleep Mode)!"
            else:
                # Phương án dự phòng nếu PowerShell bị khóa
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                return True, "Đã thực thi lệnh Sleep bằng chế độ dự phòng rundll32!"
        except Exception as e:
            return False, f"Lỗi thực thi lệnh Sleep: {str(e)}"

# ==========================================================
# 5. ĐỊNH NGHĨA CÁC LUỒNG STREAMING DỮ LIỆU THỜI GIAN THỰC
# ==========================================================
streaming_state = {"webcam": False, "screen": False, "keylogger": False}
key_buffer = []

async def stream_webcam(websocket):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        await websocket.send(json.dumps({"type": "stream_status", "msg": "LỖI: Máy trạm không có thiết bị Webcam!"}))
        streaming_state["webcam"] = False
        cap.release()
        security.stop_visual_alert()
        return
    try:
        while streaming_state["webcam"]:
            ret, frame = cap.read()
            if ret:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                await websocket.send(json.dumps({"type": "video_stream", "source": "webcam", "data": jpg_as_text}))
            await asyncio.sleep(0.05)
    finally:
        cap.release()
        gc.collect()  # Kích hoạt dọn dẹp bộ nhớ chống rò rỉ RAM

async def stream_screen(websocket):
    try:
        while streaming_state["screen"]:
            screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format="JPEG", quality=40)
            jpg_as_text = base64.b64encode(buffer.getvalue()).decode('utf-8')
            await websocket.send(json.dumps({"type": "video_stream", "source": "screen", "data": jpg_as_text}))
            await asyncio.sleep(0.1)
    finally:
        gc.collect()  # Kích hoạt giải phóng bộ nhớ khi dừng stream

def on_press(key):
    if streaming_state.get("keylogger"):
        try:
            active_win = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            k = key.char if hasattr(key, 'char') and key.char else f"[{key.name}]"
            key_buffer.append(f"[{active_win}] : {k}")
        except Exception:
            pass

async def stream_keylogger(websocket):
    global key_buffer
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    try:
        while streaming_state["keylogger"]:
            if key_buffer:
                data_to_send = list(key_buffer)
                key_buffer.clear()
                await websocket.send(json.dumps({"type": "keylogger_data", "data": data_to_send}))
            await asyncio.sleep(0.5)
    finally:
        listener.stop()

# ==========================================================
# 6. VÒNG LẶP KẾT NỐI CHÍNH & ĐỊNH TUYẾN LỆNH TỪ WEB DASHBOARD
# ==========================================================
async def connect_to_gateway():
    print(f"[Agent - {DEVICE_NAME}] Đang chờ kết nối tới Gateway...")
    while True:
        try:
            async with websockets.connect(GATEWAY_URL) as websocket:
                print("[Agent] Kết nối Gateway thành công!")
                
                # Đồng bộ danh sách file trong Sandbox lên màn hình Admin ngay khi vừa kết nối
                await websocket.send(json.dumps({
                    "type": "file_list", "data": FileManager.list_files()
                }))
                
                while True:
                    data = await websocket.recv()
                    command = json.loads(data)
                    action = command.get("action")
                    
                    # --- PHÂN HỆ GIÁM SÁT MÀN HÌNH ---
                    if action == "START_STREAM":
                        if not streaming_state["screen"]:
                            if security.show_consent_popup("Giám sát Màn hình"):
                                print("[Agent] Bắt đầu Stream Màn hình...")
                                streaming_state["screen"] = True
                                asyncio.create_task(stream_screen(websocket))
                            else:
                                print("[Agent] Người dùng từ chối quyền Giám sát Màn hình.")
                                await websocket.send(json.dumps({"type": "stream_status", "msg": "[PERMISSION DENIED] Máy trạm từ chối cấp quyền Màn hình!"}))
                                
                    elif action == "STOP_STREAM":
                        print("[Agent] Nhận lệnh dừng Stream Màn hình.")
                        streaming_state["screen"] = False
                        await websocket.send(json.dumps({
                            "type": "stream_status", 
                            "msg": "[STREAM STOPPED] Đã dừng phát luồng giám sát màn hình."
                        }))
                        
                    # --- PHÂN HỆ WEBCAM ---
                    elif action == "START_CAM":
                        if not streaming_state["webcam"]:
                            if security.show_consent_popup("Webcam"):
                                print("[Agent] Bắt đầu Stream Webcam...")
                                streaming_state["webcam"] = True
                                security.start_visual_alert()
                                asyncio.create_task(stream_webcam(websocket))
                            else:
                                print("[Agent] Người dùng từ chối quyền Webcam.")
                                await websocket.send(json.dumps({"type": "stream_status", "msg": "[PERMISSION DENIED] Máy trạm từ chối cấp quyền Webcam!"}))
                                
                    elif action == "STOP_CAM":
                        print("[Agent] Nhận lệnh dừng Webcam.")
                        streaming_state["webcam"] = False
                        security.stop_visual_alert()
                        await websocket.send(json.dumps({
                            "type": "stream_status", 
                            "msg": "[WEBCAM STOPPED] Đã tắt Webcam và thu hồi driver thành công."
                        }))
                        
                    # --- PHÂN HỆ KEYLOGGER ---
                    elif action == "START_KEYLOG":
                        if not streaming_state["keylogger"]:
                            if security.show_consent_popup("Keylogger"):
                                print("[Agent] Bắt đầu Keylogger...")
                                streaming_state["keylogger"] = True
                                asyncio.create_task(stream_keylogger(websocket))
                            else:
                                print("[Agent] Người dùng từ chối quyền Keylogger.")
                                await websocket.send(json.dumps({"type": "stream_status", "msg": "[PERMISSION DENIED] Máy trạm từ chối cấp quyền Keylogger!"}))
                                
                    elif action == "STOP_KEYLOG":
                        print("[Agent] Nhận lệnh dừng Keylogger.")
                        streaming_state["keylogger"] = False
                        await websocket.send(json.dumps({
                            "type": "stream_status", 
                            "msg": "[KEYLOG STOPPED] Đã gỡ bỏ Hook lắng nghe bàn phím."
                        }))
                        
                    # --- PHÂN HỆ QUẢN LÝ TIẾN TRÌNH ---
                    elif action == "GET_PROCESSES":
                        print("[DEBUG] Đã nhận lệnh GET_PROCESSES từ Admin!")
                        processes = ProcessManager.get_all_processes()
                        print(f"[DEBUG] Quét được {len(processes)} tiến trình.")
                        await websocket.send(json.dumps({
                            "type": "process_list",
                            "data": processes
                        }))
                        
                    elif action == "KILL_PROCESS":
                        pid = command.get("pid")
                        print(f"[Agent] Nhận lệnh hạ tiến trình PID: {pid}")
                        if ProcessManager.kill_process(pid):
                            await websocket.send(json.dumps({"type": "stream_status", "msg": f"[PROCESS KILLED] Đã hạ tiến trình PID {pid} thành công!"}))
                            processes = ProcessManager.get_all_processes()
                            await websocket.send(json.dumps({"type": "process_list", "data": processes}))
                        else:
                            await websocket.send(json.dumps({"type": "stream_status", "msg": f"[PROCESS ERROR] Không thể hạ tiến trình PID {pid} (Quyền hạn hoặc đã tắt)!"}))
                            
                    # --- PHÂN HỆ QUẢN LÝ TỆP TIN (UPLOAD / DOWNLOAD) ---
                    elif action == "LIST_FILES":
                        print("[Agent] Nhận lệnh làm mới danh sách Sandbox...")
                        await websocket.send(json.dumps({
                            "type": "file_list", "data": FileManager.list_files()
                        }))
                        
                    elif action == "UPLOAD_FILE":
                        filename = command.get("filename")
                        file_data = command.get("data")
                        print(f"[Agent] Đang nhận file upload: {filename}")
                        if FileManager.save_file(filename, file_data):
                            await websocket.send(json.dumps({
                                "type": "stream_status", 
                                "msg": f"[FILE SUCCESS] Tệp [{filename}] đã lưu an toàn vào Sandbox!"
                            }))
                            await websocket.send(json.dumps({
                                "type": "file_list", "data": FileManager.list_files()
                            }))
                        else:
                            await websocket.send(json.dumps({
                                "type": "stream_status", 
                                "msg": f"[SECURITY BLOCKED] Tệp [{filename}] bị từ chối do nghi ngờ Path Traversal!"
                            }))
                            
                    elif action == "DOWNLOAD_FILE":
                        filename = command.get("filename")
                        print(f"[Agent] Đang chuẩn bị dữ liệu gửi file: {filename}")
                        encoded_data = FileManager.read_file(filename)
                        if encoded_data:
                            await websocket.send(json.dumps({
                                "type": "download_response",
                                "filename": filename,
                                "data": encoded_data
                            }))
                            await websocket.send(json.dumps({
                                "type": "stream_status", 
                                "msg": f"[FILE SUCCESS] Máy Admin đã lấy tệp [{filename}] về máy!"
                            }))
                        else:
                            await websocket.send(json.dumps({
                                "type": "stream_status",
                                "msg": f"[FILE ERROR] Tệp [{filename}] không tồn tại hoặc bị từ chối truy cập!"
                            }))
                            
                    # --- PHÂN HỆ QUẢN TRỊ NGUỒN ---
                    elif action == "SHUTDOWN":
                        print("[Agent] Nhận lệnh SHUTDOWN từ Admin.")
                        success, msg = PowerManager.shutdown()
                        await websocket.send(json.dumps({
                            "type": "stream_status", 
                            "msg": f"[POWER] {msg}"
                        }))
                        
                    elif action == "RESTART":
                        print("[Agent] Nhận lệnh RESTART từ Admin.")
                        success, msg = PowerManager.restart()
                        await websocket.send(json.dumps({
                            "type": "stream_status", 
                            "msg": f"[POWER] {msg}"
                        }))
                        
                    elif action == "SLEEP":
                        print("[Agent] Nhận lệnh SLEEP từ Admin.")
                        success, msg = PowerManager.sleep()
                        await websocket.send(json.dumps({
                            "type": "stream_status", 
                            "msg": f"[POWER] {msg}"
                        }))

        except Exception as e:
            print(f"[Agent] Lỗi kết nối: {e}. Thử lại sau 3s...")
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(connect_to_gateway())