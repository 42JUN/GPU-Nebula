from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json
from datetime import datetime

from ..models.gpu import GPUMetrics
from ..models.topology import Topology

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

metrics_manager = ConnectionManager()
topology_manager = ConnectionManager()

@router.websocket("/metrics")
async def websocket_metrics_endpoint(websocket: WebSocket):
    await metrics_manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive, or handle incoming messages if needed
            # For now, just waiting for disconnect
            await websocket.receive_text() 
    except WebSocketDisconnect:
        metrics_manager.disconnect(websocket)
        print(f"Metrics WebSocket disconnected: {websocket.client}")

@router.websocket("/topology")
async def websocket_topology_endpoint(websocket: WebSocket):
    await topology_manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive, or handle incoming messages if needed
            # For now, just waiting for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        topology_manager.disconnect(websocket)
        print(f"Topology WebSocket disconnected: {websocket.client}")

# Example functions to broadcast data (these would be called from services)
async def broadcast_gpu_metrics(metrics: GPUMetrics):
    await metrics_manager.broadcast(json.dumps(metrics.dict(), default=str))

async def broadcast_topology_update(topology: Topology):
    await topology_manager.broadcast(json.dumps(topology.dict(), default=str))
