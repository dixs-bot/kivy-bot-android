<<<<<<< HEAD
"""
Multi Platform Auto Posting System - Backend Server
FastAPI + WebSocket + asyncio + Scheduler
"""

import asyncio
import csv
import json
import logging
import os
import random
import shutil
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

import schedule as schedule_lib
from fastapi import (
    FastAPI, File, Form, HTTPException, UploadFile, WebSocket,
    WebSocketDisconnect, Header, Depends
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ============================================================
# KONFIGURASI
# ============================================================
API_KEY = "mpaps-2024-secret-key-change-me"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
IMAGES_DIR = os.path.join(DATA_DIR, "images")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Setup logging ke file
file_logger = logging.getLogger("file_logger")
file_logger.setLevel(logging.INFO)
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
file_logger.addHandler(fh)


# ============================================================
# MODEL PYDANTIC
# ============================================================
class SettingsModel(BaseModel):
    delay_min: int = 5
    delay_max: int = 15
    platform_facebook: bool = True
    platform_instagram: bool = True
    platform_whatsapp: bool = True
    retry_max: int = 3
    api_key_fb: str = ""
    api_key_ig: str = ""
    api_key_wa: str = ""


class ScheduleModel(BaseModel):
    enabled: bool = False
    hour: int = 9
    minute: int = 0
    days: List[str] = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]


class BotResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# PENYIMPANAN LOG (IN-MEMORY + FILE)
# ============================================================
class LogStore:
    def __init__(self, max_logs: int = 500):
        self.logs: List[Dict] = []
        self.max_logs = max_logs
        self._lock = threading.Lock()

    def add(self, level: str, message: str, platform: str = "system"):
        entry = {
            "id": len(self.logs) + 1,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": level.lower(),
            "message": message,
            "platform": platform.lower()
        }
        with self._lock:
            self.logs.append(entry)
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
        file_logger.info(f"[{platform.upper()}] {message}")
        return entry

    def get_recent(self, count: int = 100) -> List[Dict]:
        with self._lock:
            return self.logs[-count:]

    def clear(self):
        with self._lock:
            self.logs.clear()


log_store = LogStore()


# ============================================================
# PENGELOLA PRODUK (CSV)
# ============================================================
class ProductManager:
    def __init__(self):
        self.products: List[Dict] = []
        self.csv_file: Optional[str] = None

    def load_from_csv(self, filepath: str) -> int:
        self.products.clear()
        self.csv_file = filepath
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.products.append({
                        "nama": row.get("nama", "").strip(),
                        "harga": row.get("harga", "").strip(),
                        "deskripsi": row.get("deskripsi", "").strip(),
                        "gambar": row.get("gambar", "").strip()
                    })
            return len(self.products)
        except Exception as e:
            log_store.add("error", f"Gagal baca CSV: {str(e)}")
            raise

    def get_products(self) -> List[Dict]:
        return self.products

    def clear(self):
        self.products.clear()
        self.csv_file = None


product_manager = ProductManager()


# ============================================================
# PENGELOLA PLATFORM (STUB - SIMULASI POSTING)
# ============================================================
class PlatformPoster:
    """
    Stub untuk masing-masing platform.
    Ganti implementasi dengan automation yang sesuai:
    - Facebook: Gunakan playwright/selenium untuk Marketplace,
      atau Graph API untuk Page
    - Instagram: Graph API (Business Account)
    - WhatsApp: WhatsApp Business API / Baileys (Node) / pywhatkit
    """

    @staticmethod
    async def post_facebook_marketplace(product: Dict) -> bool:
        """Simulasi post ke Facebook Marketplace"""
        log_store.add("info", f"Posting '{product['nama']}' ke FB Marketplace...", "facebook")
        await asyncio.sleep(random.uniform(2, 5))
        # Simulasi: 85% chance sukses
        if random.random() < 0.85:
            log_store.add("success", f"Berhasil post '{product['nama']}' ke FB Marketplace", "facebook")
            return True
        else:
            log_store.add("error", f"Gagal post '{product['nama']}' ke FB Marketplace", "facebook")
            return False

    @staticmethod
    async def post_facebook_page(product: Dict) -> bool:
        """Simulasi post ke Facebook Page via Graph API"""
        log_store.add("info", f"Posting '{product['nama']}' ke FB Page...", "facebook")
        await asyncio.sleep(random.uniform(1.5, 3))
        if random.random() < 0.90:
            log_store.add("success", f"Berhasil post '{product['nama']}' ke FB Page", "facebook")
            return True
        else:
            log_store.add("error", f"Gagal post '{product['nama']}' ke FB Page", "facebook")
            return False

    @staticmethod
    async def post_instagram(product: Dict) -> bool:
        """Simulasi post ke Instagram via Graph API"""
        log_store.add("info", f"Posting '{product['nama']}' ke Instagram...", "instagram")
        await asyncio.sleep(random.uniform(2, 4))
        if random.random() < 0.80:
            log_store.add("success", f"Berhasil post '{product['nama']}' ke Instagram", "instagram")
            return True
        else:
            log_store.add("error", f"Gagal post '{product['nama']}' ke Instagram", "instagram")
            return False

    @staticmethod
    async def post_whatsapp(product: Dict) -> bool:
        """Simulasi kirim ke WhatsApp"""
        log_store.add("info", f"Mengirim '{product['nama']}' via WhatsApp...", "whatsapp")
        await asyncio.sleep(random.uniform(1, 3))
        if random.random() < 0.92:
            log_store.add("success", f"Berhasil kirim '{product['nama']}' via WhatsApp", "whatsapp")
            return True
        else:
            log_store.add("error", f"Gagal kirim '{product['nama']}' via WhatsApp", "whatsapp")
            return False


poster = PlatformPoster()


# ============================================================
# PENGELOLA BOT UTAMA
# ============================================================
class BotManager:
    def __init__(self):
        self.is_running: bool = False
        self.current_index: int = 0
        self.total_posted: int = 0
        self.total_failed: int = 0
        self.task: Optional[asyncio.Task] = None
        self.stop_event: asyncio.Event = asyncio.Event()
        self.start_time: Optional[str] = None

    def get_status(self) -> Dict:
        return {
            "running": self.is_running,
            "current_index": self.current_index,
            "total_products": len(product_manager.products),
            "total_posted": self.total_posted,
            "total_failed": self.total_failed,
            "start_time": self.start_time,
            "uptime": self._calc_uptime() if self.start_time else "00:00:00"
        }

    def _calc_uptime(self) -> str:
        if not self.start_time:
            return "00:00:00"
        try:
            start = datetime.strptime(self.start_time, "%H:%M:%S")
            now = datetime.now()
            today_start = now.replace(hour=start.hour, minute=start.minute, second=start.second)
            if today_start > now:
                today_start = today_start.replace(day=today_start.day - 1)
            diff = now - today_start
            h, rem = divmod(int(diff.total_seconds()), 3600)
            m, s = divmod(rem, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            return "00:00:00"

    async def start(self):
        if self.is_running:
            return {"success": False, "message": "Bot sudah berjalan"}
        if not product_manager.products:
            return {"success": False, "message": "Tidak ada produk. Upload CSV dulu."}

        self.is_running = True
        self.current_index = 0
        self.total_posted = 0
        self.total_failed = 0
        self.stop_event.clear()
        self.start_time = datetime.now().strftime("%H:%M:%S")

        log_store.add("info", f"Bot dimulai. Total {len(product_manager.products)} produk.", "system")
        self.task = asyncio.create_task(self._run_loop())
        return {"success": True, "message": "Bot berhasil dimulai"}

    async def stop(self):
        if not self.is_running:
            return {"success": False, "message": "Bot tidak sedang berjalan"}
        self.stop_event.set()
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        log_store.add("warning", "Bot dihentikan oleh user.", "system")
        return {"success": True, "message": "Bot berhasil dihentikan"}

    async def _run_loop(self):
        settings = get_settings()
        products = product_manager.products

        for i, product in enumerate(products):
            if self.stop_event.is_set():
                break

            self.current_index = i
            log_store.add("info", f"[{i+1}/{len(products)}] Memproses: {product['nama']}", "system")

            # Posting ke setiap platform yang aktif
            if settings["platform_facebook"]:
                for attempt in range(settings["retry_max"]):
                    if self.stop_event.is_set():
                        break
                    success = await poster.post_facebook_marketplace(product)
                    if success:
                        self.total_posted += 1
                        break
                    if attempt < settings["retry_max"] - 1:
                        log_store.add("warning", f"Retry FB Marketplace ({attempt+2}/{settings['retry_max']})", "facebook")
                        await asyncio.sleep(3)
                else:
                    self.total_failed += 1

            if self.stop_event.is_set():
                break

            if settings["platform_instagram"]:
                for attempt in range(settings["retry_max"]):
                    if self.stop_event.is_set():
                        break
                    success = await poster.post_instagram(product)
                    if success:
                        self.total_posted += 1
                        break
                    if attempt < settings["retry_max"] - 1:
                        log_store.add("warning", f"Retry Instagram ({attempt+2}/{settings['retry_max']})", "instagram")
                        await asyncio.sleep(3)
                else:
                    self.total_failed += 1

            if self.stop_event.is_set():
                break

            if settings["platform_whatsapp"]:
                for attempt in range(settings["retry_max"]):
                    if self.stop_event.is_set():
                        break
                    success = await poster.post_whatsapp(product)
                    if success:
                        self.total_posted += 1
                        break
                    if attempt < settings["retry_max"] - 1:
                        log_store.add("warning", f"Retry WhatsApp ({attempt+2}/{settings['retry_max']})", "whatsapp")
                        await asyncio.sleep(3)
                else:
                    self.total_failed += 1

            # Delay antar produk
            if i < len(products) - 1 and not self.stop_event.is_set():
                delay = random.randint(settings["delay_min"], settings["delay_max"])
                log_store.add("info", f"Delay {delay} detik sebelum produk berikutnya...", "system")
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=delay)
                    break  # stop_event was set
                except asyncio.TimeoutError:
                    pass  # normal delay completed

        self.is_running = False
        log_store.add("info", f"Bot selesai. Posted: {self.total_posted}, Failed: {self.total_failed}", "system")


bot_manager = BotManager()


# ============================================================
# PENGELOLA PENGATURAN
# ============================================================
_settings_store: Dict = {
    "delay_min": 5,
    "delay_max": 15,
    "platform_facebook": True,
    "platform_instagram": True,
    "platform_whatsapp": True,
    "retry_max": 3,
    "api_key_fb": "",
    "api_key_ig": "",
    "api_key_wa": ""
}

_schedule_store: Dict = {
    "enabled": False,
    "hour": 9,
    "minute": 0,
    "days": ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]
}


def get_settings() -> Dict:
    return _settings_store.copy()


def update_settings(data: Dict) -> Dict:
    for k, v in data.items():
        if k in _settings_store:
            _settings_store[k] = v
    log_store.add("info", "Pengaturan diperbarui.", "system")
    return _settings_store.copy()


def get_schedule() -> Dict:
    return _schedule_store.copy()


def update_schedule(data: Dict) -> Dict:
    for k, v in data.items():
        if k in _schedule_store:
            _schedule_store[k] = v
    _apply_schedule()
    log_store.add("info", "Scheduler diperbarui.", "system")
    return _schedule_store.copy()


# ============================================================
# SCHEDULER
# ============================================================
def _apply_schedule():
    """Terapkan jadwal ke schedule library"""
    schedule_lib.clear()

    if not _schedule_store["enabled"]:
        return

    day_map = {
        "senin": schedule_lib.every().monday,
        "selasa": schedule_lib.every().tuesday,
        "rabu": schedule_lib.every().wednesday,
        "kamis": schedule_lib.every().thursday,
        "jumat": schedule_lib.every().friday,
        "sabtu": schedule_lib.every().saturday,
        "minggu": schedule_lib.every().sunday
    }

    time_str = f"{_schedule_store['hour']:02d}:{_schedule_store['minute']:02d}"
    for day_name in _schedule_store.get("days", []):
        if day_name in day_map:
            day_map[day_name].at(time_str).do(_scheduled_start)
    log_store.add("info", f"Scheduler aktif: {time_str} hari {', '.join(_schedule_store['days'])}", "system")


def _scheduled_start():
    """Dijalankan oleh thread scheduler"""
    if not bot_manager.is_running and product_manager.products:
        log_store.add("info", "Scheduler memulai bot secara otomatis...", "system")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(bot_manager.start())
            else:
                loop.run_until_complete(bot_manager.start())
        except Exception as e:
            log_store.add("error", f"Scheduler error: {str(e)}", "system")


def _run_scheduler():
    """Thread terpisah untuk scheduler"""
    while True:
        schedule_lib.run_pending()
        time.sleep(1)


scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
scheduler_thread.start()


# ============================================================
# WEBSOCKET MANAGER
# ============================================================
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: Dict):
        disconnected = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_log(self, entry: Dict):
        await self.broadcast({"type": "log", "data": entry})

    async def broadcast_status(self):
        await self.broadcast({"type": "status", "data": bot_manager.get_status()})


ws_manager = ConnectionManager()


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(title="Multi Platform Auto Posting System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Middleware API Key ---
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key and x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="API Key tidak valid")
    return True


# ============================================================
# ENDPOINTS API
# ============================================================

@app.get("/api/status")
async def get_status():
    return bot_manager.get_status()


@app.post("/api/start-bot", response_model=BotResponse)
async def start_bot(auth: bool = Depends(verify_api_key)):
    result = await bot_manager.start()
    await ws_manager.broadcast_status()
    return BotResponse(success=result["success"], message=result["message"])


@app.post("/api/stop-bot", response_model=BotResponse)
async def stop_bot(auth: bool = Depends(verify_api_key)):
    result = await bot_manager.stop()
    await ws_manager.broadcast_status()
    return BotResponse(success=result["success"], message=result["message"])


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...), auth: bool = Depends(verify_api_key)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Hanya file CSV yang diperbolehkan")

    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        count = product_manager.load_from_csv(filepath)
        log_store.add("success", f"CSV loaded: {count} produk dari {file.filename}", "system")
        await ws_manager.broadcast_status()
        return {"success": True, "message": f"{count} produk berhasil dimuat", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products")
async def get_products():
    return {"products": product_manager.get_products(), "count": len(product_manager.products)}


@app.get("/api/logs")
async def get_logs(count: int = 100):
    return {"logs": log_store.get_recent(count)}


@app.delete("/api/logs")
async def clear_logs(auth: bool = Depends(verify_api_key)):
    log_store.clear()
    return {"success": True, "message": "Log berhasil dihapus"}


@app.get("/api/settings")
async def api_get_settings():
    return get_settings()


@app.post("/api/settings")
async def api_update_settings(settings: SettingsModel, auth: bool = Depends(verify_api_key)):
    updated = update_settings(settings.dict())
    return {"success": True, "settings": updated}


@app.get("/api/schedule")
async def api_get_schedule():
    return get_schedule()


@app.post("/api/schedule")
async def api_update_schedule(sched: ScheduleModel, auth: bool = Depends(verify_api_key)):
    updated = update_schedule(sched.dict())
    return {"success": True, "schedule": updated}


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================
@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        # Kirim status awal
        await ws.send_json({"type": "status", "data": bot_manager.get_status()})
        # Kirim log terakhir
        await ws.send_json({"type": "logs_init", "data": log_store.get_recent(50)})
        # Keep alive
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ============================================================
# EVENT: BROADCAST LOG BARU SECARA OTOMATIS
# ============================================================
# Patch log_store.add agar auto-broadcast via WebSocket
_original_add = log_store.add


def _patched_add(level, message, platform="system"):
    entry = _original_add(level, message, platform)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(ws_manager.broadcast_log(entry))
            asyncio.create_task(ws_manager.broadcast_status())
    except RuntimeError:
        pass
    return entry


log_store.add = _patched_add


# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Multi Platform Auto Posting System")
    print("  Backend Server")
    print(f"  API Key: {API_KEY}")
    print("=" * 60)
=======
"""
Multi Platform Auto Posting System - Backend Server
FastAPI + WebSocket + asyncio + Scheduler
"""

import asyncio
import csv
import json
import logging
import os
import random
import shutil
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

import schedule as schedule_lib
from fastapi import (
    FastAPI, File, Form, HTTPException, UploadFile, WebSocket,
    WebSocketDisconnect, Header, Depends
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ============================================================
# KONFIGURASI
# ============================================================
API_KEY = "mpaps-2024-secret-key-change-me"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
IMAGES_DIR = os.path.join(DATA_DIR, "images")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Setup logging ke file
file_logger = logging.getLogger("file_logger")
file_logger.setLevel(logging.INFO)
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
file_logger.addHandler(fh)


# ============================================================
# MODEL PYDANTIC
# ============================================================
class SettingsModel(BaseModel):
    delay_min: int = 5
    delay_max: int = 15
    platform_facebook: bool = True
    platform_instagram: bool = True
    platform_whatsapp: bool = True
    retry_max: int = 3
    api_key_fb: str = ""
    api_key_ig: str = ""
    api_key_wa: str = ""


class ScheduleModel(BaseModel):
    enabled: bool = False
    hour: int = 9
    minute: int = 0
    days: List[str] = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]


class BotResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# PENYIMPANAN LOG (IN-MEMORY + FILE)
# ============================================================
class LogStore:
    def __init__(self, max_logs: int = 500):
        self.logs: List[Dict] = []
        self.max_logs = max_logs
        self._lock = threading.Lock()

    def add(self, level: str, message: str, platform: str = "system"):
        entry = {
            "id": len(self.logs) + 1,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": level.lower(),
            "message": message,
            "platform": platform.lower()
        }
        with self._lock:
            self.logs.append(entry)
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
        file_logger.info(f"[{platform.upper()}] {message}")
        return entry

    def get_recent(self, count: int = 100) -> List[Dict]:
        with self._lock:
            return self.logs[-count:]

    def clear(self):
        with self._lock:
            self.logs.clear()


log_store = LogStore()


# ============================================================
# PENGELOLA PRODUK (CSV)
# ============================================================
class ProductManager:
    def __init__(self):
        self.products: List[Dict] = []
        self.csv_file: Optional[str] = None

    def load_from_csv(self, filepath: str) -> int:
        self.products.clear()
        self.csv_file = filepath
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.products.append({
                        "nama": row.get("nama", "").strip(),
                        "harga": row.get("harga", "").strip(),
                        "deskripsi": row.get("deskripsi", "").strip(),
                        "gambar": row.get("gambar", "").strip()
                    })
            return len(self.products)
        except Exception as e:
            log_store.add("error", f"Gagal baca CSV: {str(e)}")
            raise

    def get_products(self) -> List[Dict]:
        return self.products

    def clear(self):
        self.products.clear()
        self.csv_file = None


product_manager = ProductManager()


# ============================================================
# PENGELOLA PLATFORM (STUB - SIMULASI POSTING)
# ============================================================
class PlatformPoster:
    """
    Stub untuk masing-masing platform.
    Ganti implementasi dengan automation yang sesuai:
    - Facebook: Gunakan playwright/selenium untuk Marketplace,
      atau Graph API untuk Page
    - Instagram: Graph API (Business Account)
    - WhatsApp: WhatsApp Business API / Baileys (Node) / pywhatkit
    """

    @staticmethod
    async def post_facebook_marketplace(product: Dict) -> bool:
        """Simulasi post ke Facebook Marketplace"""
        log_store.add("info", f"Posting '{product['nama']}' ke FB Marketplace...", "facebook")
        await asyncio.sleep(random.uniform(2, 5))
        # Simulasi: 85% chance sukses
        if random.random() < 0.85:
            log_store.add("success", f"Berhasil post '{product['nama']}' ke FB Marketplace", "facebook")
            return True
        else:
            log_store.add("error", f"Gagal post '{product['nama']}' ke FB Marketplace", "facebook")
            return False

    @staticmethod
    async def post_facebook_page(product: Dict) -> bool:
        """Simulasi post ke Facebook Page via Graph API"""
        log_store.add("info", f"Posting '{product['nama']}' ke FB Page...", "facebook")
        await asyncio.sleep(random.uniform(1.5, 3))
        if random.random() < 0.90:
            log_store.add("success", f"Berhasil post '{product['nama']}' ke FB Page", "facebook")
            return True
        else:
            log_store.add("error", f"Gagal post '{product['nama']}' ke FB Page", "facebook")
            return False

    @staticmethod
    async def post_instagram(product: Dict) -> bool:
        """Simulasi post ke Instagram via Graph API"""
        log_store.add("info", f"Posting '{product['nama']}' ke Instagram...", "instagram")
        await asyncio.sleep(random.uniform(2, 4))
        if random.random() < 0.80:
            log_store.add("success", f"Berhasil post '{product['nama']}' ke Instagram", "instagram")
            return True
        else:
            log_store.add("error", f"Gagal post '{product['nama']}' ke Instagram", "instagram")
            return False

    @staticmethod
    async def post_whatsapp(product: Dict) -> bool:
        """Simulasi kirim ke WhatsApp"""
        log_store.add("info", f"Mengirim '{product['nama']}' via WhatsApp...", "whatsapp")
        await asyncio.sleep(random.uniform(1, 3))
        if random.random() < 0.92:
            log_store.add("success", f"Berhasil kirim '{product['nama']}' via WhatsApp", "whatsapp")
            return True
        else:
            log_store.add("error", f"Gagal kirim '{product['nama']}' via WhatsApp", "whatsapp")
            return False


poster = PlatformPoster()


# ============================================================
# PENGELOLA BOT UTAMA
# ============================================================
class BotManager:
    def __init__(self):
        self.is_running: bool = False
        self.current_index: int = 0
        self.total_posted: int = 0
        self.total_failed: int = 0
        self.task: Optional[asyncio.Task] = None
        self.stop_event: asyncio.Event = asyncio.Event()
        self.start_time: Optional[str] = None

    def get_status(self) -> Dict:
        return {
            "running": self.is_running,
            "current_index": self.current_index,
            "total_products": len(product_manager.products),
            "total_posted": self.total_posted,
            "total_failed": self.total_failed,
            "start_time": self.start_time,
            "uptime": self._calc_uptime() if self.start_time else "00:00:00"
        }

    def _calc_uptime(self) -> str:
        if not self.start_time:
            return "00:00:00"
        try:
            start = datetime.strptime(self.start_time, "%H:%M:%S")
            now = datetime.now()
            today_start = now.replace(hour=start.hour, minute=start.minute, second=start.second)
            if today_start > now:
                today_start = today_start.replace(day=today_start.day - 1)
            diff = now - today_start
            h, rem = divmod(int(diff.total_seconds()), 3600)
            m, s = divmod(rem, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            return "00:00:00"

    async def start(self):
        if self.is_running:
            return {"success": False, "message": "Bot sudah berjalan"}
        if not product_manager.products:
            return {"success": False, "message": "Tidak ada produk. Upload CSV dulu."}

        self.is_running = True
        self.current_index = 0
        self.total_posted = 0
        self.total_failed = 0
        self.stop_event.clear()
        self.start_time = datetime.now().strftime("%H:%M:%S")

        log_store.add("info", f"Bot dimulai. Total {len(product_manager.products)} produk.", "system")
        self.task = asyncio.create_task(self._run_loop())
        return {"success": True, "message": "Bot berhasil dimulai"}

    async def stop(self):
        if not self.is_running:
            return {"success": False, "message": "Bot tidak sedang berjalan"}
        self.stop_event.set()
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        log_store.add("warning", "Bot dihentikan oleh user.", "system")
        return {"success": True, "message": "Bot berhasil dihentikan"}

    async def _run_loop(self):
        settings = get_settings()
        products = product_manager.products

        for i, product in enumerate(products):
            if self.stop_event.is_set():
                break

            self.current_index = i
            log_store.add("info", f"[{i+1}/{len(products)}] Memproses: {product['nama']}", "system")

            # Posting ke setiap platform yang aktif
            if settings["platform_facebook"]:
                for attempt in range(settings["retry_max"]):
                    if self.stop_event.is_set():
                        break
                    success = await poster.post_facebook_marketplace(product)
                    if success:
                        self.total_posted += 1
                        break
                    if attempt < settings["retry_max"] - 1:
                        log_store.add("warning", f"Retry FB Marketplace ({attempt+2}/{settings['retry_max']})", "facebook")
                        await asyncio.sleep(3)
                else:
                    self.total_failed += 1

            if self.stop_event.is_set():
                break

            if settings["platform_instagram"]:
                for attempt in range(settings["retry_max"]):
                    if self.stop_event.is_set():
                        break
                    success = await poster.post_instagram(product)
                    if success:
                        self.total_posted += 1
                        break
                    if attempt < settings["retry_max"] - 1:
                        log_store.add("warning", f"Retry Instagram ({attempt+2}/{settings['retry_max']})", "instagram")
                        await asyncio.sleep(3)
                else:
                    self.total_failed += 1

            if self.stop_event.is_set():
                break

            if settings["platform_whatsapp"]:
                for attempt in range(settings["retry_max"]):
                    if self.stop_event.is_set():
                        break
                    success = await poster.post_whatsapp(product)
                    if success:
                        self.total_posted += 1
                        break
                    if attempt < settings["retry_max"] - 1:
                        log_store.add("warning", f"Retry WhatsApp ({attempt+2}/{settings['retry_max']})", "whatsapp")
                        await asyncio.sleep(3)
                else:
                    self.total_failed += 1

            # Delay antar produk
            if i < len(products) - 1 and not self.stop_event.is_set():
                delay = random.randint(settings["delay_min"], settings["delay_max"])
                log_store.add("info", f"Delay {delay} detik sebelum produk berikutnya...", "system")
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=delay)
                    break  # stop_event was set
                except asyncio.TimeoutError:
                    pass  # normal delay completed

        self.is_running = False
        log_store.add("info", f"Bot selesai. Posted: {self.total_posted}, Failed: {self.total_failed}", "system")


bot_manager = BotManager()


# ============================================================
# PENGELOLA PENGATURAN
# ============================================================
_settings_store: Dict = {
    "delay_min": 5,
    "delay_max": 15,
    "platform_facebook": True,
    "platform_instagram": True,
    "platform_whatsapp": True,
    "retry_max": 3,
    "api_key_fb": "",
    "api_key_ig": "",
    "api_key_wa": ""
}

_schedule_store: Dict = {
    "enabled": False,
    "hour": 9,
    "minute": 0,
    "days": ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]
}


def get_settings() -> Dict:
    return _settings_store.copy()


def update_settings(data: Dict) -> Dict:
    for k, v in data.items():
        if k in _settings_store:
            _settings_store[k] = v
    log_store.add("info", "Pengaturan diperbarui.", "system")
    return _settings_store.copy()


def get_schedule() -> Dict:
    return _schedule_store.copy()


def update_schedule(data: Dict) -> Dict:
    for k, v in data.items():
        if k in _schedule_store:
            _schedule_store[k] = v
    _apply_schedule()
    log_store.add("info", "Scheduler diperbarui.", "system")
    return _schedule_store.copy()


# ============================================================
# SCHEDULER
# ============================================================
def _apply_schedule():
    """Terapkan jadwal ke schedule library"""
    schedule_lib.clear()

    if not _schedule_store["enabled"]:
        return

    day_map = {
        "senin": schedule_lib.every().monday,
        "selasa": schedule_lib.every().tuesday,
        "rabu": schedule_lib.every().wednesday,
        "kamis": schedule_lib.every().thursday,
        "jumat": schedule_lib.every().friday,
        "sabtu": schedule_lib.every().saturday,
        "minggu": schedule_lib.every().sunday
    }

    time_str = f"{_schedule_store['hour']:02d}:{_schedule_store['minute']:02d}"
    for day_name in _schedule_store.get("days", []):
        if day_name in day_map:
            day_map[day_name].at(time_str).do(_scheduled_start)
    log_store.add("info", f"Scheduler aktif: {time_str} hari {', '.join(_schedule_store['days'])}", "system")


def _scheduled_start():
    """Dijalankan oleh thread scheduler"""
    if not bot_manager.is_running and product_manager.products:
        log_store.add("info", "Scheduler memulai bot secara otomatis...", "system")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(bot_manager.start())
            else:
                loop.run_until_complete(bot_manager.start())
        except Exception as e:
            log_store.add("error", f"Scheduler error: {str(e)}", "system")


def _run_scheduler():
    """Thread terpisah untuk scheduler"""
    while True:
        schedule_lib.run_pending()
        time.sleep(1)


scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
scheduler_thread.start()


# ============================================================
# WEBSOCKET MANAGER
# ============================================================
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: Dict):
        disconnected = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_log(self, entry: Dict):
        await self.broadcast({"type": "log", "data": entry})

    async def broadcast_status(self):
        await self.broadcast({"type": "status", "data": bot_manager.get_status()})


ws_manager = ConnectionManager()


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(title="Multi Platform Auto Posting System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Middleware API Key ---
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key and x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="API Key tidak valid")
    return True


# ============================================================
# ENDPOINTS API
# ============================================================

@app.get("/api/status")
async def get_status():
    return bot_manager.get_status()


@app.post("/api/start-bot", response_model=BotResponse)
async def start_bot(auth: bool = Depends(verify_api_key)):
    result = await bot_manager.start()
    await ws_manager.broadcast_status()
    return BotResponse(success=result["success"], message=result["message"])


@app.post("/api/stop-bot", response_model=BotResponse)
async def stop_bot(auth: bool = Depends(verify_api_key)):
    result = await bot_manager.stop()
    await ws_manager.broadcast_status()
    return BotResponse(success=result["success"], message=result["message"])


@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...), auth: bool = Depends(verify_api_key)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Hanya file CSV yang diperbolehkan")

    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        count = product_manager.load_from_csv(filepath)
        log_store.add("success", f"CSV loaded: {count} produk dari {file.filename}", "system")
        await ws_manager.broadcast_status()
        return {"success": True, "message": f"{count} produk berhasil dimuat", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products")
async def get_products():
    return {"products": product_manager.get_products(), "count": len(product_manager.products)}


@app.get("/api/logs")
async def get_logs(count: int = 100):
    return {"logs": log_store.get_recent(count)}


@app.delete("/api/logs")
async def clear_logs(auth: bool = Depends(verify_api_key)):
    log_store.clear()
    return {"success": True, "message": "Log berhasil dihapus"}


@app.get("/api/settings")
async def api_get_settings():
    return get_settings()


@app.post("/api/settings")
async def api_update_settings(settings: SettingsModel, auth: bool = Depends(verify_api_key)):
    updated = update_settings(settings.dict())
    return {"success": True, "settings": updated}


@app.get("/api/schedule")
async def api_get_schedule():
    return get_schedule()


@app.post("/api/schedule")
async def api_update_schedule(sched: ScheduleModel, auth: bool = Depends(verify_api_key)):
    updated = update_schedule(sched.dict())
    return {"success": True, "schedule": updated}


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ============================================================
# WEBSOCKET ENDPOINT
# ============================================================
@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        # Kirim status awal
        await ws.send_json({"type": "status", "data": bot_manager.get_status()})
        # Kirim log terakhir
        await ws.send_json({"type": "logs_init", "data": log_store.get_recent(50)})
        # Keep alive
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ============================================================
# EVENT: BROADCAST LOG BARU SECARA OTOMATIS
# ============================================================
# Patch log_store.add agar auto-broadcast via WebSocket
_original_add = log_store.add


def _patched_add(level, message, platform="system"):
    entry = _original_add(level, message, platform)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(ws_manager.broadcast_log(entry))
            asyncio.create_task(ws_manager.broadcast_status())
    except RuntimeError:
        pass
    return entry


log_store.add = _patched_add


# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  Multi Platform Auto Posting System")
    print("  Backend Server")
    print(f"  API Key: {API_KEY}")
    print("=" * 60)
>>>>>>> 0051939bdfc4db26b4371397e7b9cfc434853ab3
    uvicorn.run(app, host="0.0.0.0", port=8000)