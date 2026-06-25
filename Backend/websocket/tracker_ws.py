from fastapi import WebSocket, APIRouter, Query, HTTPException
from utils.security import decode_token
from database import SessionLocal

ws_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, assignment_id: str, websocket: WebSocket):
        await websocket.accept()
        if assignment_id not in self.active_connections:
            self.active_connections[assignment_id] = []
        self.active_connections[assignment_id].append(websocket)

    def disconnect(self, assignment_id: str, websocket: WebSocket):
        if assignment_id in self.active_connections and websocket in self.active_connections[assignment_id]:
            self.active_connections[assignment_id].remove(websocket)

    async def broadcast(self, assignment_id: str, message: dict):
        if assignment_id in self.active_connections:
            dead = []
            for ws in self.active_connections[assignment_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.active_connections[assignment_id].remove(ws)

manager = ConnectionManager()

@ws_router.websocket("/api/v1/ws/tracker/{assignment_id}")
async def tracker_ws(assignment_id: str, websocket: WebSocket, token: str = Query(...)):
    from models.class_ import ClassMembership
    from models.assignment import Assignment
    db = SessionLocal()
    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=4001)
        db.close()
        return

    role = payload.get("role")
    user_id = payload.get("sub")

    if role not in ("ADMIN", "MENTOR"):
        await websocket.close(code=4003)
        db.close()
        return

    assignment = db.query(Assignment).filter_by(id=assignment_id).first()
    if not assignment:
        await websocket.close(code=4004)
        db.close()
        return

    if role == "MENTOR":
        membership = db.query(ClassMembership).filter(
            ClassMembership.class_id == assignment.class_id,
            ClassMembership.user_id == user_id,
            ClassMembership.member_role == "MENTOR",
            ClassMembership.status == "ACTIVE"
        ).first()
        if not membership:
            await websocket.close(code=4003)
            db.close()
            return
    db.close()

    await manager.connect(assignment_id, websocket)
    await websocket.send_json({"event": "connected", "assignment_id": assignment_id})

    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(assignment_id, websocket)
