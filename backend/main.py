import os
import subprocess
import asyncio
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from bot_manager import BotManager

app = FastAPI(title="ToolFace Automation V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot_manager = BotManager()

class StartBotPayload(BaseModel):
    mode: str
    resolution: str
    min_sleep: float = 3.0
    max_sleep: float = 8.0

@app.get("/api/devices")
def get_devices():
    try:
        output = subprocess.check_output("adb devices", shell=True).decode('utf-8')
        lines = output.strip().split('\n')[1:] 
        devices = []
        for line in lines:
            if 'device' in line and 'offline' not in line:
                devices.append(line.split('\t')[0].strip())
        return {"status": "success", "devices": devices}
    except Exception as e:
        return {"status": "error", "message": str(e), "devices": []}

@app.post("/api/bot/{device_id}/start")
def start_bot(device_id: str, payload: StartBotPayload):
    result = bot_manager.start_bot(
        device_id=device_id,
        mode=payload.mode,
        resolution=payload.resolution,
        min_sleep=payload.min_sleep,
        max_sleep=payload.max_sleep
    )
    if result.get("success"):
        return {"status": "success", "message": f"Bot {device_id} started."}
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))

@app.post("/api/bot/{device_id}/stop")
def stop_bot(device_id: str):
    result = bot_manager.stop_bot(device_id)
    if result.get("success"):
        return {"status": "success", "message": f"Bot {device_id} stopped."}
    else:
        raise HTTPException(status_code=400, detail=result.get("error"))

@app.get("/api/bot/status")
def get_bot_status():
    return {"status": "success", "data": bot_manager.get_running_status()}

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    bot_manager.add_websocket(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except Exception:
        bot_manager.remove_websocket(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
