import threading
import json
import asyncio
from typing import Dict, List
import sys
import os

# Add parent directory to path to import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bot_runner import BotWorker

class BotManager:
    def __init__(self):
        self.workers: Dict[str, BotWorker] = {}
        self.active_websockets: List = []
        self.loop = asyncio.get_event_loop()

    def add_websocket(self, ws):
        if ws not in self.active_websockets:
            self.active_websockets.append(ws)

    def remove_websocket(self, ws):
        if ws in self.active_websockets:
            self.active_websockets.remove(ws)

    def broadcast_log(self, device_id: str, message: str):
        payload = json.dumps({"device_id": device_id, "message": message})
        for ws in self.active_websockets:
            asyncio.run_coroutine_threadsafe(ws.send_text(payload), self.loop)

    def start_bot(self, device_id: str, mode: str, resolution: str, min_sleep: float, max_sleep: float) -> dict:
        if device_id in self.workers and self.workers[device_id].is_running:
            return {"success": False, "error": "Bot is already running for this device."}
        
        worker = BotWorker(
            device_id=device_id,
            mode=mode,
            resolution=resolution,
            min_sleep=min_sleep,
            max_sleep=max_sleep,
            log_callback=self.broadcast_log
        )
        self.workers[device_id] = worker
        worker.daemon = True
        worker.start()
        
        return {"success": True}

    def stop_bot(self, device_id: str) -> dict:
        if device_id not in self.workers or not self.workers[device_id].is_running:
            return {"success": False, "error": "Bot is not running for this device."}
        
        self.workers[device_id].stop()
        return {"success": True}

    def get_running_status(self) -> dict:
        status = {}
        for device_id, worker in self.workers.items():
            status[device_id] = {
                "is_running": worker.is_running,
                "mode": worker.mode,
                "resolution": worker.resolution
            }
        return status
