from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse # Thêm dòng này để trả file HTML
from typing import List, Dict
import json
import os

app = FastAPI(title="LRC-SMS Gateway Server")

# ==========================================
# ENDPOINT TRẢ GIAO DIỆN WEB CHO ADMIN
# ==========================================
@app.get("/")
async def get_dashboard():
    """Hàm này sẽ đọc file index.html trên máy 10 và phát ra trình duyệt cho máy 11"""
    # Đảm bảo file index.html nằm cùng thư mục với main.py (thư mục /webapp)
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ... (Giữ nguyên toàn bộ phần class ConnectionManager và các endpoint @app.websocket ở dưới) ...

class ConnectionManager:
    """Quản lý vòng đời kết nối WebSocket của Admin và Agent"""
    def __init__(self):
        # Lưu trữ danh sách các Admin đang mở Dashboard
        self.active_admins: List[WebSocket] = []
        # Lưu trữ danh sách Agent đang chạy ngầm (Dict với key là IP/ID của Agent)
        self.active_agents: Dict[str, WebSocket] = {}

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.active_admins.append(websocket)

    def disconnect_admin(self, websocket: WebSocket):
        if websocket in self.active_admins:
            self.active_admins.remove(websocket)

    async def connect_agent(self, websocket: WebSocket, agent_id: str):
        await websocket.accept()
        self.active_agents[agent_id] = websocket

    def disconnect_agent(self, agent_id: str):
        if agent_id in self.active_agents:
            del self.active_agents[agent_id]

    async def broadcast_to_admins(self, message: str):
        """Đẩy dữ liệu từ Agent (Màn hình, Thông số...) lên tất cả màn hình Admin"""
        for admin in self.active_admins:
            await admin.send_text(message)

    async def send_to_agent(self, agent_id: str, message: str):
        """Chuyển tiếp lệnh từ Admin xuống đúng máy Agent mục tiêu"""
        if agent_id in self.active_agents:
            await self.active_agents[agent_id].send_text(message)

# Khởi tạo bộ quản lý kết nối
manager = ConnectionManager()

# ==========================================
# ENDPOINT 1: DÀNH CHO ADMIN (Trình duyệt)
# ==========================================
@app.websocket("/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket):
    await manager.connect_admin(websocket)
    try:
        # Gửi thông báo bắt tay thành công ngay khi kết nối
        await websocket.send_text(json.dumps({
            "type": "system_status",
            "message": "Gateway Handshake Successful",
            "connected_agents": list(manager.active_agents.keys())
        }))
        
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                target_agent = payload.get("target")
                
                # -> SỬA LẠI ĐOẠN ĐỊNH TUYẾN NÀY CHO THÔNG MINH HƠN:
                if target_agent == "BROADCAST" or not target_agent:
                    # Nếu gửi broadcast hoặc chưa chỉ định đích, gửi cho TOÀN BỘ agent đang online
                    for agent_id in list(manager.active_agents.keys()):
                        await manager.send_to_agent(agent_id, data)
                elif target_agent in manager.active_agents:
                    # Nếu chỉ định đúng tên Agent, gửi đích danh
                    await manager.send_to_agent(target_agent, data)
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)

# ==========================================
# ENDPOINT 2: DÀNH CHO AGENT (Máy trạm Win 10)
# ==========================================
@app.websocket("/ws/agent/{agent_id}")
async def websocket_agent_endpoint(websocket: WebSocket, agent_id: str):
    await manager.connect_agent(websocket, agent_id)
    
    # Bắn tín hiệu cho Admin biết có Agent mới online
    await manager.broadcast_to_admins(json.dumps({
        "type": "agent_connected",
        "agent_id": agent_id
    }))
    
    try:
        while True:
            # Nhận dữ liệu stream từ Agent (Hình ảnh, PID, RAM...) và đẩy thẳng lên Admin
            data = await websocket.receive_text()
            await manager.broadcast_to_admins(data)
            
    except WebSocketDisconnect:
        manager.disconnect_agent(agent_id)
        # Báo cáo Admin khi Agent sập hoặc ngắt kết nối
        await manager.broadcast_to_admins(json.dumps({
            "type": "agent_disconnected",
            "agent_id": agent_id
        }))