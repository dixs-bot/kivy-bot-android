"""
Multi Platform Auto Posting System - Android APK Controller
Versi lengkap: Dashboard, Upload, Logs, Settings, Scheduler,
Product List, History, Multi-Account, Toast, Reconnection
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import (
    BooleanProperty, ColorProperty, ListProperty,
    NumericProperty, ObjectProperty, StringProperty
)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.utils import get_color_from_hex

# ============================================================
# KONFIGURASI WARNA
# ============================================================
C = {
    'bg':           (0.024, 0.043, 0.094, 1),     # #060b18
    'bg_card':      (0.067, 0.102, 0.180, 1),     # #111a2e
    'bg_card_h':    (0.086, 0.125, 0.251, 1),     # #162040
    'border':       (0.102, 0.153, 0.267, 1),     # #1a2744
    'border_l':     (0.141, 0.200, 0.337, 1),     # #243356
    'accent':       (0.000, 0.898, 0.627, 1),     # #00e5a0
    'accent_dim':   (0.102, 0.239, 0.200, 1),     # #1a3d33
    'accent_glow':  (0.200, 1.000, 0.761, 1),     # #33ffc2
    'error':        (1.000, 0.278, 0.341, 1),     # #ff4757
    'error_dim':    (0.165, 0.051, 0.078, 1),     # #2a0d14
    'warning':      (1.000, 0.647, 0.008, 1),     # #ffa502
    'warning_dim':  (0.165, 0.102, 0.008, 1),     # #2a1a02
    'info':         (0.561, 0.643, 0.788, 1),     # #8fa4d0
    'info_dim':     (0.051, 0.102, 0.165, 1),     # #0d1a2a
    'text':         (0.910, 0.929, 0.961, 1),     # #e8edf5
    'muted':        (0.420, 0.478, 0.600, 1),     # #6b7a99
    'white':        (1, 1, 1, 1),
    'fb':           (0.357, 0.498, 0.843, 1),     # #5b7fd6
    'ig':           (0.910, 0.376, 0.541, 1),     # #e8608a
    'wa':           (0.145, 0.820, 0.400, 1),     # #25d366
    'success_bg':   (0.051, 0.165, 0.122, 1),     # #0d2a1f
}

Window.clearcolor = C['bg']
Window.softinput_mode = 'pan'

# ============================================================
# DATA STORE (shared antar screen)
# ============================================================
class DataStore:
    """Penyimpanan data global yang bisa diakses semua screen"""
    def __init__(self):
        self.products: List[Dict] = []
        self.history: List[Dict] = []
        self.accounts: List[Dict] = [
            {"id": 1, "label": "Akun Utama", "platform": "all", "active": True},
        ]
        self.next_account_id = 2

    def clear_products(self):
        self.products.clear()

    def set_products(self, products: List[Dict]):
        self.products = products

    def add_account(self, label: str, platform: str = "all") -> Dict:
        acc = {"id": self.next_account_id, "label": label, "platform": platform, "active": True}
        self.accounts.append(acc)
        self.next_account_id += 1
        return acc

    def remove_account(self, acc_id: int):
        self.accounts = [a for a in self.accounts if a["id"] != acc_id]

    def toggle_account(self, acc_id: int):
        for a in self.accounts:
            if a["id"] == acc_id:
                a["active"] = not a["active"]
                break

    def add_history(self, entry: Dict):
        self.history.append(entry)
        if len(self.history) > 200:
            self.history = self.history[-200:]

store = DataStore()


# ============================================================
# TOAST NOTIFICATION MANAGER
# ============================================================
class ToastManager:
    """Menampilkan toast notification di atas layar"""
    def __init__(self):
        self._queue = []
        self._showing = False

    @mainthread
    def show(self, message: str, toast_type: str = "info"):
        colors = {
            'success': (C['accent'], C['success_bg']),
            'error':   (C['error'], C['error_dim']),
            'warning': (C['warning'], C['warning_dim']),
            'info':    (C['info'], C['info_dim']),
        }
        text_color, bg_color = colors.get(toast_type, colors['info'])

        # Cari toast container atau buat baru
        app = App.get_running_app()
        root = app.root
        if not root:
            return

        toast = BoxLayout(
            size_hint=(0.9, None),
            height= dp(52),
            pos_hint={'center_x': 0.5, 'top': 0.96},
            padding=(dp(16), dp(12)),
            spacing= dp(10),
        )
        toast.canvas.before.add(
            Builder.load_string(f'''
<BoxLayout>:
    canvas.before:
        Color:
            rgba: {bg_color}
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12]
        Color:
            rgba: {text_color}
            a: 0.3
        Line:
            width: 1
            rounded_rectangle: [self.x, self.y, self.width, self.height, 12]
''')[0].canvas.before.children[1]  # border
        )

        icon_map = {'success': '✓', 'error': '✗', 'warning': '⚠', 'info': 'ℹ'}
        lbl_icon = Label(
            text=icon_map.get(toast_type, 'ℹ'),
            font_size= sp(18),
            color= text_color,
            size_hint_x= None,
            width= dp(24),
        )
        lbl_msg = Label(
            text= message,
            font_size= sp(13),
            color= text_color,
            halign= 'left',
            valign= 'middle',
        )
        toast.add_widget(lbl_icon)
        toast.add_widget(lbl_msg)

        # Tambahkan ke root overlay
        root.add_widget(toast)

        # Animasi fade-out setelah 3 detik
        def remove_toast(dt):
            if toast.parent:
                root.remove_widget(toast)

        Clock.schedule_once(remove_toast, 3.5)

toast_mgr = ToastManager()


# ============================================================
# API CLIENT
# ============================================================
class ApiClient:
    """HTTP client menggunakan urllib (tanpa requests dependency)"""
    def __init__(self):
        self.base_url = 'http://192.168.1.100:8000'
        self.api_key = 'mpaps-2024-secret-key-change-me'
        self.timeout = 12

    @property
    def headers(self):
        return {'X-API-Key': self.api_key}

    def _request(self, method: str, path: str,
                 data: dict = None, files: dict = None) -> dict:
        import urllib.request
        import urllib.error
        import io

        url = self.base_url.rstrip('/') + path
        hdrs = dict(self.headers)

        req_data = None

        if files:
            boundary = '----MPAPSBoundary' + str(int(time.time() * 1000))
            body = bytearray()
            for field_name, (filename, file_bytes) in files.items():
                body.extend(f'--{boundary}\r\n'.encode())
                body.extend(
                    f'Content-Disposition: form-data; name="{field_name}"; '
                    f'filename="{filename}"\r\n'.encode()
                )
                body.extend(b'Content-Type: application/octet-stream\r\n\r\n')
                body.extend(file_bytes if isinstance(file_bytes, bytes) else file_bytes.encode())
                body.extend(b'\r\n')
            body.extend(f'--{boundary}--\r\n'.encode())
            hdrs['Content-Type'] = f'multipart/form-data; boundary={boundary}'
            req_data = bytes(body)
        elif data is not None:
            body = json.dumps(data).encode('utf-8')
            hdrs['Content-Type'] = 'application/json'
            req_data = body

        req = urllib.request.Request(url, data=req_data, headers=hdrs, method=method)

        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout)
            return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode('utf-8')
                return json.loads(err_body)
            except Exception:
                return {'success': False, 'detail': f'HTTP {e.code}: {e.reason}'}
        except Exception as e:
            return {'success': False, 'detail': str(e)}

    def get(self, path: str) -> dict:
        return self._request('GET', path)

    def post(self, path: str, data: dict = None) -> dict:
        return self._request('POST', path, data=data)

    def delete(self, path: str) -> dict:
        return self._request('DELETE', path)

    def upload_csv(self, filepath: str) -> dict:
        with open(filepath, 'rb') as f:
            file_bytes = f.read()
        filename = os.path.basename(filepath)
        return self._request('POST', '/api/upload-csv', files={'file': (filename, file_bytes)})

    def health_check(self) -> bool:
        result = self.get('/api/health')
        return result.get('status') == 'ok'


api = ApiClient()


# ============================================================
# WEBSOCKET CLIENT
# ============================================================
class WSClient:
    """
    WebSocket client dengan auto-reconnect.
    Jika library websocket-client tidak tersedia, fallback ke polling.
    """
    def __init__(self):
        self.connected = False
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._ws = None
        self._reconnect_delay = 2
        self._max_reconnect_delay = 30

        # Callbacks (dipanggil dari main thread via Clock)
        self.on_log: Optional[Callable] = None
        self.on_status: Optional[Callable] = None
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None

        # Flag fallback
        self._using_polling = False

    def connect(self, url: str):
        self.disconnect()
        self._running = True
        self._reconnect_delay = 2
        self._thread = threading.Thread(target=self._run, args=(url,), daemon=True)
        self._thread.start()

    def disconnect(self):
        self._running = False
        self.connected = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    def _run(self, url: str):
        ws_available = False
        try:
            import websocket
            ws_available = True
        except ImportError:
            pass

        if ws_available:
            self._run_ws(url)
        else:
            self._using_polling = True
            self._run_polling()

    def _run_ws(self, url: str):
        """Koneksi WebSocket sesungguhnya"""
        import websocket

        while self._running:
            try:
                self._ws = websocket.WebSocket()
                self._ws.settimeout(5)
                self._ws.connect(url)

                self.connected = True
                self._using_polling = False
                self._reconnect_delay = 2
                if self.on_connect:
                    Clock.schedule_once(lambda dt: self.on_connect(), 0)

                while self._running:
                    try:
                        data = self._ws.recv()
                        if not data:
                            break
                        msg = json.loads(data)
                        self._handle_message(msg)
                    except websocket.WebSocketTimeoutException:
                        # Ping/keep alive
                        try:
                            self._ws.ping()
                        except Exception:
                            break
                    except Exception:
                        break

            except Exception as e:
                pass

            self.connected = False
            if self.on_disconnect:
                Clock.schedule_once(lambda dt: self.on_disconnect(), 0)

            if not self._running:
                break

            # Reconnect delay dengan exponential backoff
            if self.on_disconnect:
                Clock.schedule_once(
                    lambda dt: toast_mgr.show(
                        f'Reconnect dalam {self._reconnect_delay}d...', 'warning'
                    ), 0
                )
            time.sleep(self._reconnect_delay)
            self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

        # Jika keluar loop karena error terus, fallback ke polling
        if self._running:
            self._using_polling = True
            self._run_polling()

    def _run_polling(self):
        """Fallback: polling REST API setiap 3 detik"""
        self.connected = False
        self._using_polling = True
        if self.on_disconnect:
            Clock.schedule_once(lambda dt: self.on_disconnect(), 0)

        Clock.schedule_once(
            lambda dt: toast_mgr.show('WebSocket tidak tersedia, menggunakan polling', 'warning'), 0
        )

        last_log_count = -1
        while self._running:
            try:
                # Poll logs
                result = api.get('/api/logs?count=30')
                if result and 'logs' in result:
                    logs = result['logs']
                    if len(logs) != last_log_count:
                        last_log_count = len(logs)
                        # Kirim hanya log baru
                        for entry in logs[-5:]:
                            if self.on_log:
                                Clock.schedule_once(lambda dt, e=entry: self.on_log(e), 0)

                # Poll status
                status = api.get('/api/status')
                if status and self.on_status:
                    Clock.schedule_once(lambda dt, s=status: self.on_status(s), 0)

            except Exception:
                pass

            time.sleep(3)

    def _handle_message(self, msg: dict):
        mtype = msg.get('type')
        if mtype == 'log' and self.on_log:
            entry = msg.get('data', {})
            Clock.schedule_once(lambda dt, e=entry: self.on_log(e), 0)
        elif mtype == 'status' and self.on_status:
            data = msg.get('data', {})
            Clock.schedule_once(lambda dt, d=data: self.on_status(d), 0)
        elif mtype == 'logs_init' and self.on_log:
            for entry in msg.get('data', []):
                Clock.schedule_once(lambda dt, e=entry: self.on_log(e), 0)


ws_client = WSClient()


# ============================================================
# HELPER: BUAT CARD BACKGROUND OTOMATIS
# ============================================================
def card_background(color=C['bg_card'], radius=12):
    """Return string KV untuk canvas.before pada card"""
    return f'''
canvas.before:
    Color:
        rgba: {color}
    RoundedRectangle:
        pos: self.pos
        size: self.size
        radius: [{radius}]
'''


def rounded_rect_border(border_color=C['border'], radius=12):
    """Return string KV untuk border rounded rectangle"""
    return f'''
canvas.after:
    Color:
        rgba: {border_color}
    Line:
        width: 1
        rounded_rectangle: [self.x+0.5, self.y+0.5, self.width-1, self.height-1, {radius}]
'''


# ============================================================
# KV LAYOUT STRING
# ============================================================
KV = '''

# ============================================================
# BASE WIDGETS
# ============================================================

<NavButton@ButtonBehavior+BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: '56dp'
    padding: ('4dp', '6dp')
    spacing: '3dp'
    canvas.before:
        Color:
            rgba: (0,0,0,0)
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: root.icon
        font_name: 'Roboto'
        font_size: '20sp'
        color: root.text_color
        halign: 'center'
    Label:
        text: root.label
        font_size: '10sp'
        color: root.text_color
        halign: 'center'
    text_color: C['muted']

<PrimaryButton@Button>:
    background_color: C['accent']
    color: (0.02, 0.04, 0.09, 1)
    font_size: '14sp'
    bold: True
    size_hint_y: None
    height: '50dp'
    canvas.before:
        Color:
            rgba: self.background_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12]

<DangerButton@Button>:
    background_color: C['error']
    color: C['white']
    font_size: '14sp'
    bold: True
    size_hint_y: None
    height: '50dp'
    canvas.before:
        Color:
            rgba: self.background_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12]

<GhostButton@Button>:
    background_color: (0,0,0,0)
    color: C['text']
    font_size: '13sp'
    size_hint_y: None
    height: '42dp'
    canvas.before:
        Color:
            rgba: C['border']
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10]

<CardBox@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.minimum_height
    padding: '16dp'
    spacing: '10dp'
    canvas.before:
        Color:
            rgba: C['bg_card']
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12]

<SectionTitle@Label>:
    color: C['muted']
    font_size: '11sp'
    size_hint_y: None
    height: '16dp'
    text_size: (None, None)

<BigValue@Label>:
    color: C['text']
    font_size: '30sp'
    font_name: 'Roboto'
    size_hint_y: None
    height: '42dp'

<SmallInfo@Label>:
    color: C['muted']
    font_size: '11sp'
    size_hint_y: None
    height: '18dp'
    halign: 'left'

<FormInput@TextInput>:
    foreground_color: C['text']
    hint_text_color: C['muted']
    font_size: '14sp'
    padding: ['14dp', '12dp']
    size_hint_y: None
    height: '50dp'
    multiline: False
    background_color: C['bg_card']
    canvas.before:
        Color:
            rgba: C['border']
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10]

<ToggleRow@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '48dp'
    padding: ('0dp', '4dp')
    Label:
        text: root.text
        font_size: '14sp'
        color: C['text']
        valign: 'middle'
    BoxLayout:
        size_hint_x: None
        width: '50dp'
        pos_hint: {'center_y': 0.5}
        canvas.before:
            Color:
                rgba: C['accent'] if root.active else C['border_l']
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [12]
        BoxLayout:
            size_hint_x: None
            width: '42dp'
            height: '42dp'
            pos: self.parent.pos if self.parent else (0,0)
            x: self.parent.x + (8 if root.active else 0) if self.parent else 0
            y: self.parent.y + 4 if self.parent else 0
            canvas.before:
                Color:
                    rgba: C['white']
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [10]

<PlatformChip@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '44dp'
    padding: ('12dp', '8dp')
    spacing: '12dp'
    canvas.before:
        Color:
            rgba: C['bg_card']
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10]
    Label:
        text: root.icon
        font_size: '18sp'
        color: root.chip_color
        size_hint_x: None
        width: '28dp'
    Label:
        text: root.name
        font_size: '13sp'
        color: C['text']
        valign: 'middle'
    Label:
        text: '●'
        font_size: '12sp'
        color: C['accent'] if root.is_on else C['error']
        size_hint_x: None
        width: '20dp'
        halign: 'right'

# ============================================================
# LOG LINE (per baris log)
# ============================================================
<LogLine@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '22dp'
    padding: ('0dp', '1dp')
    spacing: '6dp'
    Label:
        text: root.time_str
        font_size: '10sp'
        font_name: 'Roboto'
        color: C['muted']
        size_hint_x: None
        width: '55dp'
    Label:
        text: root.level_str
        font_size: '9sp'
        bold: True
        color: root.level_color
        size_hint_x: None
        width: '55dp'
    Label:
        text: root.platform_str
        font_size: '9sp'
        color: root.platform_color
        size_hint_x: None
        width: '70dp'
    Label:
        text: root.message
        font_size: '10sp'
        font_name: 'Roboto'
        color: C['text']
        text_size: (None, None)
        halign: 'left'
        valign: 'middle'
        shorten_from: 'right'

# ============================================================
# PRODUCT ROW
# ============================================================
<ProductRow@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: '72dp'
    padding: ('14dp', '10dp')
    spacing: '4dp'
    canvas.before:
        Color:
            rgba: C['bg_card']
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10]
    Label:
        text: root.nama
        font_size: '14sp'
        bold: True
        color: C['text']
        size_hint_y: None
        height: '20dp'
        text_size: (None, None)
        halign: 'left'
        shorten_from: 'right'
    Label:
        text: root.harga_str
        font_size: '13sp'
        font_name: 'Roboto'
        color: C['accent']
        size_hint_y: None
        height: '18dp'
    Label:
        text: root.desc_preview
        font_size: '11sp'
        color: C['muted']
        size_hint_y: None
        height: '16dp'
        text_size: (None, None)
        halign: 'left'
        shorten_from: 'right'

# ============================================================
# ACCOUNT ROW
# ============================================================
<AccountRow@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '52dp'
    padding: ('14dp', '8dp')
    spacing: '10dp'
    canvas.before:
        Color:
            rgba: C['bg_card']
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10]
    Label:
        text: root.label
        font_size: '13sp'
        color: C['text']
        valign: 'middle'
    Label:
        text: root.platform
        font_size: '10sp'
        color: C['muted']
        valign: 'middle'
    Label:
        text: 'AKTIF' if root.active else 'NONAKTIF'
        font_size: '9sp'
        bold: True
        color: C['accent'] if root.active else C['error']
        size_hint_x: None
        width: '60dp'
        halign: 'right'
        valign: 'middle'

# ============================================================
# HISTORY ROW
# ============================================================
<HistoryRow@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '50dp'
    padding: ('14dp', '6dp')
    spacing: '8dp'
    canvas.before:
        Color:
            rgba: C['bg_card']
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10]
    Label:
        text: root.time_str
        font_size: '10sp'
        font_name: 'Roboto'
        color: C['muted']
        size_hint_x: None
        width: '50dp'
        valign: 'middle'
    Label:
        text: root.product
        font_size: '12sp'
        color: C['text']
        valign: 'middle'
    Label:
        text: root.result
        font_size: '9sp'
        bold: True
        color: C['accent'] if root.success else C['error']
        size_hint_x: None
        width: '50dp'
        halign: 'right'
        valign: 'middle'

# ============================================================
# BOTTOM NAVIGATION BAR
# ============================================================
<BottomNav@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '68dp'
    padding: ['6dp', '4dp']
    spacing: '2dp'
    canvas.before:
        Color:
            rgba: (0.055, 0.078, 0.133, 1)
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: C['border']
        Rectangle:
            pos: (self.pos[0], self.pos[1])
            size: (self.size[0], 1)
    NavButton:
        id: nav_dash
        icon: '\\u26A1'
        label: 'Dashboard'
        on_press: app.switch_screen('dashboard'); nav_dash.text_color = C['accent']
        on_release: nav_dash.text_color = C['accent']
    NavButton:
        id: nav_upload
        icon: '\\u2B06'
        label: 'Upload'
        on_press: app.switch_screen('upload')
    NavButton:
        id: nav_logs
        icon: '\\u2318'
        label: 'Logs'
        on_press: app.switch_screen('logs')
    NavButton:
        id: nav_more
        icon: '\\u2699'
        label: 'Lainnya'
        on_press: app.switch_screen('more_menu')

# ============================================================
# SCREEN: DASHBOARD
# ============================================================
<DashboardScreen>:
    orientation: 'vertical'
    padding: '16dp'
    spacing: '12dp'

    # Header
    BoxLayout:
        size_hint_y: None
        height: '44dp'
        Label:
            text: 'MPAPS Controller'
            font_size: '20sp'
            bold: True
            color: C['text']
        BoxLayout:
            orientation: 'horizontal'
            size_hint_x: None
            width: '120dp'
            spacing: '6dp'
            Label:
                text: '\\u25CF'
                font_size: '10sp'
                color: C['accent'] if root.connected else C['error']
                valign: 'middle'
            Label:
                text: root.ws_label
                font_size: '10sp'
                color: C['accent'] if root.connected else C['error']
                valign: 'middle'

    # Status utama
    CardBox:
        height: '80dp'
        SectionTitle:
            text: 'STATUS BOT'
        BoxLayout:
            size_hint_y: None
            height: '44dp'
            spacing: '12dp'
            Label:
                text: '\\u25CF'
                font_size: '28sp'
                color: C['accent'] if root.bot_running else C['error']
                size_hint_x: None
                width: '40dp'
                valign: 'middle'
            Label:
                text: 'RUNNING' if root.bot_running else 'STOPPED'
                font_size: '24sp'
                bold: True
                font_name: 'Roboto'
                color: C['accent'] if root.bot_running else C['error']
                valign: 'middle'

    # Stats grid 3 kolom
    BoxLayout:
        size_hint_y: None
        height: '115dp'
        spacing: '10dp'
        CardBox:
            height: '115dp'
            SectionTitle:
                text: 'DIPROSES'
            BigValue:
                text: str(root.stat_processed)
            SmallInfo:
                text: f'dari {root.stat_total} produk'

        CardBox:
            height: '115dp'
            SectionTitle:
                text: 'BERHASIL'
            BigValue:
                text: str(root.stat_success)
                color: C['accent']

        CardBox:
            height: '115dp'
            SectionTitle:
                text: 'GAGAL'
            BigValue:
                text: str(root.stat_failed)
                color: C['error']

    # Progress bar
    CardBox:
        height: '68dp'
        SectionTitle:
            text: 'PROGRESS'
        BoxLayout:
            size_hint_y: None
            height: '10dp'
            canvas.before:
                Color:
                    rgba: C['border']
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [5]
            BoxLayout:
                size_hint_x: root.progress / 100.0 if root.progress > 0 else 0
                canvas.before:
                    Color:
                        rgba: C['accent']
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [5]
        Label:
            text: f'{root.progress}%  —  {root.stat_processed}/{root.stat_total} produk'
            font_size: '11sp'
            font_name: 'Roboto'
            color: C['muted']
            size_hint_y: None
            height: '18dp'

    # Platform chips
    SectionTitle:
        text: 'PLATFORM AKTIF'
    BoxLayout:
        size_hint_y: None
        height: '48dp'
        spacing: '8dp'
        PlatformChip:
            icon: 'f'
            name: 'Facebook'
            chip_color: C['fb']
            is_on: root.plat_fb
        PlatformChip:
            icon: 'i'
            name: 'Instagram'
            chip_color: C['ig']
            is_on: root.plat_ig
        PlatformChip:
            icon: 'w'
            name: 'WhatsApp'
            chip_color: C['wa']
            is_on: root.plat_wa

    # Tombol kontrol
    BoxLayout:
        size_hint_y: None
        height: '54dp'
        spacing: '12dp'
        PrimaryButton:
            text: '\\u25B6  MULAI BOT'
            disabled: root.bot_running
            on_press: root.start_bot()
        DangerButton:
            text: '\\u25A0  HENTIKAN'
            disabled: not root.bot_running
            on_press: root.stop_bot()

    # Uptime
    Label:
        text: f'Uptime: {root.uptime}'
        font_size: '11sp'
        font_name: 'Roboto'
        color: C['muted']
        halign: 'center'
        size_hint_y: None
        height: '18dp'


# ============================================================
# SCREEN: UPLOAD
# ============================================================
<UploadScreen>:
    orientation: 'vertical'
    padding: '16dp'
    spacing: '12dp'

    Label:
        text: 'Upload CSV'
        font_size: '20sp'
        bold: True
        color: C['text']
        size_hint_y: None
        height: '44dp'

    CardBox:
        height: '170dp'
        spacing: '12dp'
        Label:
            text: 'Pilih file CSV berisi data produk'
            font_size: '14sp'
            color: C['muted']
            size_hint_y: None
            height: '22dp'
        Label:
            text: 'Format: nama, harga, deskripsi, gambar'
            font_size: '11sp'
            color: C['muted']
            size_hint_y: None
            height: '18dp'
        Label:
            text: root.file_label
            font_size: '12sp'
            color: C['accent'] if 'Terpilih' in root.file_label else C['muted']
            size_hint_y: None
            height: '18dp'
        PrimaryButton:
            text: 'PILIH FILE CSV'
            size_hint_y: None
            height: '46dp'
            on_press: root.show_file_chooser()

    Label:
        text: root.upload_result
        font_size: '13sp'
        color: root.result_color
        halign: 'center'
        size_hint_y: None
        height: '22dp'

    # Preview produk
    SectionTitle:
        text: f'PREVIEW DATA ({root.preview_count} produk)'
    ScrollView:
        CardBox:
            id: preview_container
            height: self.minimum_height
            spacing: '4dp'

    # Tombol upload manual
    PrimaryButton:
        text: 'UPLOAD KE SERVER'
        disabled: not root.has_file
        on_press: root.do_upload()


# ============================================================
# SCREEN: LOGS
# ============================================================
<LogsScreen>:
    orientation: 'vertical'
    padding: '16dp'
    spacing: '10dp'

    BoxLayout:
        size_hint_y: None
        height: '44dp'
        Label:
            text: 'Log Viewer'
            font_size: '20sp'
            bold: True
            color: C['text']
        Label:
            text: f'{root.log_count} entri'
            font_size: '11sp'
            font_name: 'Roboto'
            color: C['muted']
            halign: 'right'
            valign: 'middle'

    # Filter chips
    BoxLayout:
        size_hint_y: None
        height: '36dp'
        spacing: '6dp'
        GhostButton:
            text: 'Semua'
            size_hint_y: None
            height: '34dp'
            font_size: '11sp'
            background_color: C['accent_dim'] if root.filter_all else (0,0,0,0)
            color: C['accent'] if root.filter_all else C['muted']
            on_press: root.set_filter('all')
        GhostButton:
            text: 'Sukses'
            size_hint_y: None
            height: '34dp'
            font_size: '11sp'
            background_color: C['success_bg'] if root.filter_success else (0,0,0,0)
            color: C['accent'] if root.filter_success else C['muted']
            on_press: root.set_filter('success')
        GhostButton:
            text: 'Error'
            size_hint_y: None
            height: '34dp'
            font_size: '11sp'
            background_color: C['error_dim'] if root.filter_error else (0,0,0,0)
            color: C['error'] if root.filter_error else C['muted']
            on_press: root.set_filter('error')
        GhostButton:
            text: 'Warning'
            size_hint_y: None
            height: '34dp'
            font_size: '11sp'
            background_color: C['warning_dim'] if root.filter_warning else (0,0,0,0)
            color: C['warning'] if root.filter_warning else C['muted']
            on_press: root.set_filter('warning')

    # Log list
    ScrollView:
        id: log_scroll
        do_scroll_x: False
        BoxLayout:
            id: log_list
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: '1dp'

    # Bottom actions
    BoxLayout:
        size_hint_y: None
        height: '44dp'
        spacing: '10dp'
        GhostButton:
            text: 'Refresh'
            size_hint_y: None
            height: '40dp'
            on_press: root.refresh_logs()
        GhostButton:
            text: 'Clear'
            size_hint_y: None
            height: '40dp'
            color: C['error']
            on_press: root.clear_logs()


# ============================================================
# SCREEN: MORE MENU (Settings / Scheduler / Accounts / History)
# ============================================================
<MoreMenuScreen>:
    orientation: 'vertical'
    padding: '16dp'
    spacing: '10dp'

    Label:
        text: 'Menu Lainnya'
        font_size: '20sp'
        bold: True
        color: C['text']
        size_hint_y: None
        height: '44dp'

    # Menu items
    CardBox:
        height: '54dp'
        canvas.before:
            Color:
                rgba: C['bg_card']
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [12]
        BoxLayout:
            size_hint_y: None
            height: '54dp'
            padding: ('16dp', '8dp')
            spacing: '14dp'
            Label:
                text: '\\u2699'
                font_size: '20sp'
                color: C['accent']
                valign: 'middle'
            Label:
                text: 'Pengaturan Bot'
                font_size: '14sp'
                color: C['text']
                valign: 'middle'
            Label:
                text: '\\u203A'
                font_size: '20sp'
                color: C['muted']
                size_hint_x: None
                width: '24dp'
                halign: 'right'
                valign: 'middle'

    CardBox:
        height: '54dp'
        canvas.before:
            Color:
                rgba: C['bg_card']
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [12]
        BoxLayout:
            size_hint_y: None
            height: '54dp'
            padding: ('16dp', '8dp')
            spacing: '14dp'
            Label:
                text: '\\u23F0'
                font_size: '20sp'
                color: C['warning']
                valign: 'middle'
            Label:
                text: 'Scheduler / Jadwal'
                font_size: '14sp'
                color: C['text']
                valign: 'middle'
            Label:
                text: '\\u203A'
                font_size: '20sp'
                color: C['muted']
                size_hint_x: None
                width: '24dp'
                halign: 'right'
                valign: 'middle'

    CardBox:
        height: '54dp'
        canvas.before:
            Color:
                rgba: C['bg_card']
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [12]
        BoxLayout:
            size_hint_y: None
            height: '54dp'
            padding: ('16dp', '8dp')
            spacing: '14dp'
            Label:
                text: '\\u1F4CB'
                font_size: '20sp'
                color: C['info']
                valign: 'middle'
            Label:
                text: 'Daftar Produk'
                font_size: '14sp'
                color: C['text']
                valign: 'middle'
            Label:
                text: f'{root.product_count}'
                font_size: '12sp'
                font_name: 'Roboto'
                color: C['muted']
                size_hint_x: None
                width: '30dp'
                halign: 'right'
                valign: 'middle'
            Label:
                text: '\\u203A'
                font_size: '20sp'
                color: C['muted']
                size_hint_x: None
                width: '24dp'
                halign: 'right'
                valign: 'middle'

    CardBox:
        height: '54dp'
        canvas.before:
            Color:
                rgba: C['bg_card']
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [12]
        BoxLayout:
            size_hint_y: None
            height: '54dp'
            padding: ('16dp', '8dp')
            spacing: '14dp'
            Label:
                text: '\\u1F465'
                font_size: '20sp'
                color: C['ig']
                valign: 'middle'
            Label:
                text: 'Multi Akun'
                font_size: '14sp'
                color: C['text']
                valign: 'middle'
            Label:
                text: f'{root.account_count}'
                font_size: '12sp'
                font_name: 'Roboto'
                color: C['muted']
                size_hint_x: None
                width: '30dp'
                halign: 'right'
                valign: 'middle'
            Label:
                text: '\\u203A'
                font_size: '20sp'
                color: C['muted']
                size_hint_x: None
                width: '24dp'
                halign: 'right'
                valign: 'middle'

    CardBox:
        height: '54dp'
        canvas.before:
            Color:
                rgba: C['bg_card']
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [12]
        BoxLayout:
            size_hint_y: None
            height: '54dp'
            padding: ('16dp', '8dp')
            spacing: '14dp'
            Label:
                text: '\\u1F4CA'
                font_size: '20sp'
                color: C['fb']
                valign: 'middle'
            Label:
                text: 'Riwayat Posting'
                font_size: '14sp'
                color: C['text']
                valign: 'middle'
            Label:
                text: f'{root.history_count}'
                font_size: '12sp'
                font_name: 'Roboto'
                color: C['muted']
                size_hint_x: None
                width: '30dp'
                halign: 'right'
                valign: 'middle'
            Label:
                text: '\\u203A'
                font_size: '20sp'
                color: C['muted']
                size_hint_x: None
                width: '24dp'
                halign: 'right'
                valign: 'middle'

    # Info koneksi
    BoxLayout:
        size_hint_y: None
        height: '40dp'
        Label:
            text: root.connection_info
            font_size: '11sp'
            color: C['muted']
            halign: 'center'


# ============================================================
# SCREEN: SETTINGS
# ============================================================
<SettingsScreen>:
    orientation: 'vertical'
    padding: '16dp'
    spacing: '12dp'

    BoxLayout:
        size_hint_y: None
        height: '44dp'
        Label:
            text: 'Pengaturan'
            font_size: '20sp'
            bold: True
            color: C['text']
        Button:
            text: 'Kembali'
            background_color: (0,0,0,0)
            color: C['accent']
            font_size: '13sp'
            size_hint_x: None
            width: '70dp'
            on_press: app.switch_screen('more_menu')

    # Koneksi
    CardBox:
        height: '130dp'
        SectionTitle:
            text: 'KONEKSI SERVER'
        FormInput:
            id: server_url
            text: 'http://192.168.1.100:8000'
            hint_text: 'http://IP_SERVER:8000'
        FormInput:
            id: api_key
            text: 'mpaps-2024-secret-key-change-me'
            hint_text: 'API Key'

    # Delay
    CardBox:
        height: '130dp'
        SectionTitle:
            text: 'DELAY POSTING (DETIK)'
        BoxLayout:
            size_hint_y: None
            height: '50dp'
            spacing: '10dp'
            FormInput:
                id: delay_min
                text: '5'
                hint_text: 'Min'
                input_type: 'number'
            FormInput:
                id: delay_max
                text: '15'
                hint_text: 'Max'
                input_type: 'number'
        FormInput:
            id: retry_max
            text: '3'
            hint_text: 'Max Retry per platform'
            input_type: 'number'

    # Platform toggles
    CardBox:
        height: '164dp'
        SectionTitle:
            text: 'PLATFORM'
        ToggleRow:
            id: tog_fb
            text: 'Facebook (Marketplace + Page)'
            active: True
            on_press: self.active = not self.active
        ToggleRow:
            id: tog_ig
            text: 'Instagram'
            active: True
            on_press: self.active = not self.active
        ToggleRow:
            id: tog_wa
            text: 'WhatsApp'
            active: True
            on_press: self.active = not self.active

    PrimaryButton:
        text: 'SIMPAN & HUBUNGKAN'
        on_press: root.save_and_connect()

    Label:
        text: root.status_msg
        font_size: '12sp'
        color: root.status_color
        halign: 'center'
        size_hint_y: None
        height: '20dp'


# ============================================================
# SCREEN: SCHEDULER
# ============================================================
<SchedulerScreen>:
    orientation: 'vertical'
    padding: '16dp'
    spacing: '12dp'

    BoxLayout:
        size_hint_y: None
        height: '44dp'
        Label:
            text: 'Scheduler'
            font_size: '20sp'
            bold: True
            color: C['text']
        Button:
            text: 'Kembali'
            background_color: (0,0,0,0)
            color: C['accent']
            font_size: '13sp'
            size_hint_x: None
            width: '70dp'
            on_press: app.switch_screen('more_menu')

    CardBox:
        height: '64dp'
        SectionTitle:
            text: 'AKTIFKAN SCHEDULER'
        ToggleRow:
            id: sched_toggle
            text: 'Jalankan bot secara otomatis'
            active: False
            on_press: self.active = not self.active

    CardBox:
        height: '110dp'
        SectionTitle:
            text: 'WAKTU EKSEKUSI'
        BoxLayout:
            size_hint_y: None
            height: '50dp'
            spacing: '8dp'
            FormInput:
                id: sched_hour
                text: '9'
                hint_text: 'Jam'
                input_type: 'number'
            Label:
                text: ':'
                font_size: '24sp'
                color: C['muted']
                size_hint_x: None
                width: '20dp'
                halign: 'center'
                valign: 'middle'
            FormInput:
                id: sched_minute
                text: '0'
                hint_text: 'Menit'
                input_type: 'number'

    CardBox:
        height: '100dp'
        SectionTitle:
            text: 'HARI AKTIF'
        BoxLayout:
            size_hint_y: None
            height: '44dp'
            spacing: '6dp'
            id: day_buttons

    PrimaryButton:
        text: 'SIMPAN JADWAL'
        on_press: root.save_schedule()

    Label:
        text: root.status_msg
        font_size: '12sp'
        color: root.status_color
        halign: 'center'
        size_hint_y: None
        height: '20dp'


# ============================================================
# SCREEN: PRODUCT LIST
# ============================================================
<ProductListScreen>:
    orientation: 'vertical'
    padding: '16dp'
    spacing: '10dp'

    BoxLayout:
        size_hint_y: None
        height: '44dp'
        Label:
            text: 'Daftar Produk'
            font_size: '20sp'
            bold: True
            color: C['text']
        Button:
            text: 'Kembali'
            background_color: (0,0,0,0)
            color: C['accent']
            font_size: '13sp'
            size_hint_x: None
            width: '70dp'
            on_press: app.switch_screen('more_menu')

    Label:
        text: f'Total: {root.product_count} produk'
        font_size: '12sp'
        color: C['muted']
        size_hint_y: None
        height: '20dp'

    ScrollView:
        id: product_scroll
        do_scroll_x: False
        BoxLayout:
            id: product_list
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: '6dp'

    GhostButton:
        text: 'Refresh dari Server'
        on_press: root.refresh_products()


# ============================================================
# SCREEN: MULTI ACCOUNT
# ============================================================
<AccountScreen>:
    orientation: 'vertical'
    padding: '16dp'
    spacing: '10dp'

    BoxLayout:
        size_hint_y: None
        height: '44dp'
        Label:
            text: 'Multi Akun'
            font_size: '20sp'
            bold: True
            color: C['text']
        Button:
            text: 'Kembali'
            background_color: (0,0,0,0)
            color: C['accent']
            font_size: '13sp'
            size_hint_x: None
            width: '70dp'
            on_press: app.switch_screen('more_menu')

    Label:
        text: 'Kelola akun platform untuk posting multi-akun'
        font_size: '12sp'
        color: C['muted']
        size_hint_y: None
        height: '20dp'

    ScrollView:
        id: account_scroll
        do_scroll_x: False
        BoxLayout:
            id: account_list
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: '6dp'

    PrimaryButton:
        text: '+ TAMBAH AKUN'
        on_press: root.show_add_dialog()


# ============================================================
# SCREEN: HISTORY
# ============================================================
<HistoryScreen>:
    orientation: 'vertical'
    padding: '16dp'
    spacing: '10dp'

    BoxLayout:
        size_hint_y: None
        height: '44dp'
        Label:
            text: 'Riwayat Posting'
            font_size: '20sp'
            bold: True
            color: C['text']
        Button:
            text: 'Kembali'
            background_color: (0,0,0,0)
            color: C['accent']
            font_size: '13sp'
            size_hint_x: None
            width: '70dp'
            on_press: app.switch_screen('more_menu')

    # Summary
    BoxLayout:
        size_hint_y: None
        height: '60dp'
        spacing: '10dp'
        CardBox:
            height: '60dp'
            SectionTitle:
                text: 'TOTAL'
            Label:
                text: str(root.total_entries)
                font_size: '20sp'
                font_name: 'Roboto'
                color: C['text']
                size_hint_y: None
                height: '28dp'
        CardBox:
            height: '60dp'
            SectionTitle:
                text: 'SUKSES'
            Label:
                text: str(root.total_success)
                font_size: '20sp'
                font_name: 'Roboto'
                color: C['accent']
                size_hint_y: None
                height: '28dp'
        CardBox:
            height: '60dp'
            SectionTitle:
                text: 'GAGAL'
            Label:
                text: str(root.total_failed)
                font_size: '20sp'
                font_name: 'Roboto'
                color: C['error']
                size_hint_y: None
                height: '28dp'

    ScrollView:
        id: history_scroll
        do_scroll_x: False
        BoxLayout:
            id: history_list
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: '4dp'

    GhostButton:
        text: 'Refresh'
        on_press: root.refresh_history()

'''


# ============================================================
# SCREEN IMPLEMENTATIONS
# ============================================================

class DashboardScreen(Screen):
    """Screen utama: status bot, stats, kontrol"""
    bot_running = BooleanProperty(False)
    connected = BooleanProperty(False)
    ws_label = StringProperty('Terputus')
    stat_processed = NumericProperty(0)
    stat_success = NumericProperty(0)
    stat_failed = NumericProperty(0)
    stat_total = NumericProperty(0)
    progress = NumericProperty(0)
    uptime = StringProperty('00:00:00')
    plat_fb = BooleanProperty(True)
    plat_ig = BooleanProperty(True)
    plat_wa = BooleanProperty(True)

    def __init__(self, **kw):
        super().__init__(**kw)
        ws_client.on_status = self._on_status
        ws_client.on_connect = self._on_ws_connect
        ws_client.on_disconnect = self._on_ws_disconnect

    def _on_ws_connect(self):
        self.connected = True
        mode = 'WebSocket' if not ws_client._using_polling else 'Polling'
        self.ws_label = f'Terhubung ({mode})'

    def _on_ws_disconnect(self):
        self.connected = False
        self.ws_label = 'Terputus'

    def _on_status(self, data: dict):
        self.bot_running = data.get('running', False)
        self.stat_processed = data.get('current_index', 0)
        self.stat_success = data.get('total_posted', 0)
        self.stat_failed = data.get('total_failed', 0)
        self.stat_total = data.get('total_products', 0)
        self.uptime = data.get('uptime', '00:00:00')

        total = max(self.stat_total, 1)
        if self.bot_running:
            self.progress = round((self.stat_processed / total) * 100)
        elif self.stat_success > 0:
            self.progress = 100
        else:
            self.progress = 0

        # Update platform status dari settings
        def load_plats(dt):
            s = api.get('/api/settings')
            if s:
                self.plat_fb = s.get('platform_facebook', True)
                self.plat_ig = s.get('platform_instagram', True)
                self.plat_wa = s.get('platform_whatsapp', True)
        Clock.schedule_once(load_plats, 0.5)

    def start_bot(self):
        def do():
            r = api.post('/api/start-bot')
            if r:
                s = api.get('/api/status')
                if s:
                    Clock.schedule_once(lambda dt: self._on_status(s), 0)
                msg = r.get('message', '')
                ok = r.get('success', False)
                Clock.schedule_once(lambda dt: toast_mgr.show(msg, 'success' if ok else 'warning'), 0)
            else:
                Clock.schedule_once(lambda dt: toast_mgr.show('Gagal menghubungi server', 'error'), 0)
        threading.Thread(target=do, daemon=True).start()

    def stop_bot(self):
        def do():
            r = api.post('/api/stop-bot')
            if r:
                s = api.get('/api/status')
                if s:
                    Clock.schedule_once(lambda dt: self._on_status(s), 0)
                msg = r.get('message', '')
                ok = r.get('success', False)
                Clock.schedule_once(lambda dt: toast_mgr.show(msg, 'success' if ok else 'warning'), 0)
            else:
                Clock.schedule_once(lambda dt: toast_mgr.show('Gagal menghubungi server', 'error'), 0)
        threading.Thread(target=do, daemon=True).start()

    def on_enter(self):
        """Dipanggil saat screen ditampilkan"""
        def refresh():
            s = api.get('/api/status')
            if s:
                Clock.schedule_once(lambda dt: self._on_status(s), 0)
        threading.Thread(target=refresh, daemon=True).start()


class UploadScreen(Screen):
    """Screen upload CSV"""
    file_label = StringProperty('Belum ada file dipilih')
    upload_result = StringProperty('')
    result_color = ColorProperty(C['muted'])
    preview_count = NumericProperty(0)
    has_file = BooleanProperty(False)
    _filepath = None
    _local_rows = []

    def show_file_chooser(self):
        popup = Popup(
            title='Pilih File CSV',
            size_hint=(0.95, 0.6),
            separator_color=C['border'],
        )
        layout = BoxLayout(orientation='vertical', spacing='8dp')
        fc = FileChooserListView(
            filters=['*.csv'],
            path='/storage/emulated/0/Download',
            dirselect=False,
        )

        def on_select(instance, selection, *args):
            if selection:
                fp = selection[0]
                if fp.endswith('.csv'):
                    self._filepath = fp
                    self.file_label = f'Terpilih: {os.path.basename(fp)}'
                    self.has_file = True
                    self._parse_local(fp)
                    popup.dismiss()

        fc.on_selection = on_select

        btn_close = Button(
            text='Batal',
            background_color=(0, 0, 0, 0),
            color=C['muted'],
            size_hint_y=None,
            height='44dp',
        )
        btn_close.bind(on_press=popup.dismiss)

        layout.add_widget(fc)
        layout.add_widget(btn_close)
        popup.add_widget(layout)
        popup.open()

    def _parse_local(self, filepath: str):
        """Parse CSV secara lokal untuk preview"""
        self._local_rows = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                self.upload_result = 'File CSV kosong'
                self.result_color = C['error']
                return

            # Skip header
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                # Parsing sederhana
                parts = []
                current = ''
                in_q = False
                for ch in line:
                    if ch == '"':
                        in_q = not in_q
                    elif ch == ',' and not in_q:
                        parts.append(current.strip())
                        current = ''
                    else:
                        current += ch
                parts.append(current.strip())

                if len(parts) >= 2:
                    self._local_rows.append({
                        'nama': parts[0] if len(parts) > 0 else '',
                        'harga': parts[1] if len(parts) > 1 else '',
                        'deskripsi': parts[2] if len(parts) > 2 else '',
                        'gambar': parts[3] if len(parts) > 3 else '',
                    })

            self.preview_count = len(self._local_rows)
            self._render_preview()
            self.upload_result = ''

        except Exception as e:
            self.upload_result = f'Error: {str(e)}'
            self.result_color = C['error']

    def _render_preview(self):
        """Render preview produk di dalam CardBox"""
        container = self.ids.preview_container
        container.clear_widgets()

        for i, p in enumerate(self._local_rows[:20]):  # Max 20 preview
            row = ProductRow(
                nama=p.get('nama', '-'),
                harga_str=f'Rp {p.get("harga", "0")}',
                desc_preview=p.get('deskripsi', '-')[:50],
            )
            container.add_widget(row)

        if len(self._local_rows) > 20:
            lbl = Label(
                text=f'... dan {len(self._local_rows) - 20} produk lainnya',
                font_size='11sp',
                color=C['muted'],
                size_hint_y=None,
                height='20dp',
            )
            container.add_widget(lbl)

    def do_upload(self):
        """Upload file CSV ke server"""
        if not self._filepath:
            toast_mgr.show('Pilih file terlebih dahulu', 'warning')
            return

        self.upload_result = 'Mengupload...'
        self.result_color = C['info']

        def do():
            result = api.upload_csv(self._filepath)
            if result and result.get('success'):
                msg = result.get('message', 'Upload berhasil')
                count = result.get('count', 0)
                Clock.schedule_once(lambda dt: self._upload_ok(msg, count), 0)
            else:
                detail = result.get('detail', 'Gagal upload') if result else 'Tidak bisa hubungi server'
                Clock.schedule_once(lambda dt: self._upload_fail(detail), 0)

        threading.Thread(target=do, daemon=True).start()

    def _upload_ok(self, msg: str, count: int):
        self.upload_result = f'Berhasil: {msg}'
        self.result_color = C['accent']
        toast_mgr.show(f'{count} produk berhasil diupload', 'success')

        # Update store
        store.set_products(self._local_rows)

        # Refresh product list screen jika ada
        app = App.get_running_app()
        sm = app.root.children[0] if app.root else None
        if sm and hasattr(sm, 'get_screen'):
            pl = sm.get_screen('product_list')
            if pl:
                pl.product_count = count

    def _upload_fail(self, detail: str):
        self.upload_result = f'Gagal: {detail[:60]}'
        self.result_color = C['error']
        toast_mgr.show('Upload gagal', 'error')


class LogsScreen(Screen):
    """Screen log viewer real-time"""
    log_count = NumericProperty(0)
    filter_all = BooleanProperty(True)
    filter_success = BooleanProperty(False)
    filter_error = BooleanProperty(False)
    filter_warning = BooleanProperty(False)
    _current_filter = 'all'
    _all_logs: list = []  # Semua log yang masuk
    _max_logs = 300

    def __init__(self, **kw):
        super().__init__(**kw)
        # Tidak override on_log di sini, karena dashboard juga butuh
        # Gunakan pattern: subscribe di on_enter
        self._orig_on_log = None

    def on_enter(self):
        """Subscribe ke log events saat screen ditampilkan"""
        self._orig_on_log = ws_client.on_log
        ws_client.on_log = self._on_log
        # Load existing logs
        self.refresh_logs()

    def on_leave(self):
        """Unsubscribe saat screen ditinggalkan"""
        if self._orig_on_log:
            ws_client.on_log = self._orig_on_log
            self._orig_on_log = None

    def _on_log(self, entry: dict):
        """Callback saat log baru masuk via WebSocket"""
        self._all_logs.append(entry)
        if len(self._all_logs) > self._max_logs:
            self._all_logs = self._all_logs[-self._max_logs:]

        # Track history dari log success/error
        if entry.get('level') in ('success', 'error'):
            platform = entry.get('platform', 'system')
            msg = entry.get('message', '')
            # Coba extract nama produk dari message
            product_name = msg
            for keyword in ["'", '"']:
                start = msg.find(keyword)
                if start >= 0:
                    end = msg.find(keyword, start + 1)
                    if end > start:
                        product_name = msg[start + 1:end]
                        break

            store.add_history({
                'time': entry.get('timestamp', ''),
                'product': product_name,
                'platform': platform,
                'success': entry.get('level') == 'success',
                'message': msg,
            })

        # Render jika sesuai filter
        self._render_entry(entry)
        self.log_count = len(self._all_logs)

    def _render_entry(self, entry: dict):
        """Tambahkan satu baris log ke UI"""
        level = entry.get('level', 'info')
        if self._current_filter != 'all' and level != self._current_filter:
            return

        color_map = {
            'success': C['accent'],
            'error': C['error'],
            'warning': C['warning'],
            'info': C['info'],
        }
        plat_color_map = {
            'facebook': C['fb'],
            'instagram': C['ig'],
            'whatsapp': C['wa'],
            'system': C['muted'],
        }

        line = LogLine(
            time_str=entry.get('timestamp', '--:--:--'),
            level_str=entry.get('level', 'info').upper(),
            level_color=color_map.get(level, C['muted']),
            platform_str=entry.get('platform', 'system').upper(),
            platform_color=plat_color_map.get(entry.get('platform', ''), C['muted']),
            message=entry.get('message', ''),
        )
        log_list = self.ids.log_list
        log_list.add_widget(line)

        # Batasi widget di UI (performance)
        while len(log_list.children) > 150:
            log_list.remove_widget(log_list.children[0])

        # Auto scroll
        scroll = self.ids.log_scroll
        Clock.schedule_once(lambda dt: scroll.scroll_to(line), 0.05)

    def set_filter(self, filt: str):
        """Set filter log"""
        self._current_filter = filt
        # Update boolean properties
        self.filter_all = filt == 'all'
        self.filter_success = filt == 'success'
        self.filter_error = filt == 'error'
        self.filter_warning = filt == 'warning'
        # Re-render
        self._render_all()

    def _render_all(self):
        """Render ulang semua log sesuai filter"""
        log_list = self.ids.log_list
        log_list.clear_widgets()

        color_map = {
            'success': C['accent'], 'error': C['error'],
            'warning': C['warning'], 'info': C['info'],
        }
        plat_color_map = {
            'facebook': C['fb'], 'instagram': C['ig'],
            'whatsapp': C['wa'], 'system': C['muted'],
        }

        filtered = self._all_logs if self._current_filter == 'all' else \
            [l for l in self._all_logs if l.get('level') == self._current_filter]

        for entry in filtered[-100:]:
            level = entry.get('level', 'info')
            line = LogLine(
                time_str=entry.get('timestamp', '--:--:--'),
                level_str=level.upper(),
                level_color=color_map.get(level, C['muted']),
                platform_str=entry.get('platform', 'system').upper(),
                platform_color=plat_color_map.get(entry.get('platform', ''), C['muted']),
                message=entry.get('message', ''),
            )
            log_list.add_widget(line)

    def refresh_logs(self):
        """Fetch log dari server"""
        def do():
            result = api.get('/api/logs?count=100')
            if result and 'logs' in result:
                self._all_logs = result['logs']
                Clock.schedule_once(lambda dt: self._render_all(), 0)
                Clock.schedule_once(lambda dt: setattr(self, 'log_count', len(self._all_logs)), 0)
            else:
                Clock.schedule_once(lambda dt: toast_mgr.show('Gagal memuat log', 'error'), 0)
        threading.Thread(target=do, daemon=True).start()

    def clear_logs(self):
        """Hapus log di server dan lokal"""
        def do():
            api.delete('/api/logs')
            Clock.schedule_once(lambda dt: self._clear_local(), 0)
        threading.Thread(target=do, daemon=True).start()

    def _clear_local(self):
        self._all_logs.clear()
        self.ids.log_list.clear_widgets()
        self.log_count = 0
        toast_mgr.show('Log dibersihkan', 'success')


class MoreMenuScreen(Screen):
    """Screen menu lainnya: settings, scheduler, products, accounts, history"""
    product_count = NumericProperty(0)
    account_count = NumericProperty(0)
    history_count = NumericProperty(0)
    connection_info = StringProperty('')

    def on_enter(self):
        self.product_count = len(store.products)
        self.account_count = len(store.accounts)
        self.history_count = len(store.history)
        mode = 'WebSocket' if ws_client.connected and not ws_client._using_polling else \
               'Polling' if ws_client._using_polling else 'Terputus'
        self.connection_info = f'{api.base_url} | {mode}'


class SettingsScreen(Screen):
    """Screen pengaturan: koneksi, delay, platform toggle"""
    status_msg = StringProperty('')
    status_color = ColorProperty(C['muted'])

    def save_and_connect(self):
        url = self.ids.server_url.text.rstrip('/')
        key = self.ids.api_key.text

        if not url.startswith('http'):
            self.status_msg = 'URL harus diawali http:// atau https://'
            self.status_color = C['error']
            return

        api.base_url = url
        api.api_key = key
        self.status_msg = 'Menghubungkan...'
        self.status_color = C['info']

        def do():
            # Health check
            ok = api.health_check()
            if not ok:
                Clock.schedule_once(
                    lambda dt: (
                        setattr(self, 'status_msg', 'Gagal: Server tidak ditemukan'),
                        setattr(self, 'status_color', C['error']),
                        toast_mgr.show('Server tidak ditemukan', 'error')
                    ), 0
                )
                return

            # Kirim settings
            settings = {
                'delay_min': int(self.ids.delay_min.text or '5'),
                'delay_max': int(self.ids.delay_max.text or '15'),
                'retry_max': int(self.ids.retry_max.text or '3'),
                'platform_facebook': self.ids.tog_fb.active,
                'platform_instagram': self.ids.tog_ig.active,
                'platform_whatsapp': self.ids.tog_wa.active,
                'api_key_fb': '', 'api_key_ig': '', 'api_key_wa': '',
            }
            api.post('/api/settings', settings)

            # Connect WebSocket
            ws_url = url.replace('http', 'ws') + '/ws/logs'
            ws_client.disconnect()
            time.sleep(0.5)
            ws_client.connect(ws_url)

            # Load products
            prod = api.get('/api/products')
            if prod and 'products' in prod:
                store.set_products(prod['products'])

            Clock.schedule_once(
                lambda dt: (
                    setattr(self, 'status_msg', 'Terhubung! Pengaturan disimpan.'),
                    setattr(self, 'status_color', C['accent']),
                    toast_mgr.show('Berhasil terhubung ke server', 'success')
                ), 0
            )

        threading.Thread(target=do, daemon=True).start()

    def on_enter(self):
        """Load settings dari server saat screen dibuka"""
        self.ids.server_url.text = api.base_url
        self.ids.api_key.text = api.api_key

        def load():
            s = api.get('/api/settings')
            if s:
                Clock.schedule_once(lambda dt: self._apply_settings(s), 0)
        threading.Thread(target=load, daemon=True).start()

    def _apply_settings(self, s: dict):
        self.ids.delay_min.text = str(s.get('delay_min', 5))
        self.ids.delay_max.text = str(s.get('delay_max', 15))
        self.ids.retry_max.text = str(s.get('retry_max', 3))
        self.ids.tog_fb.active = s.get('platform_facebook', True)
        self.ids.tog_ig.active = s.get('platform_instagram', True)
        self.ids.tog_wa.active = s.get('platform_whatsapp', True)


class SchedulerScreen(Screen):
    """Screen scheduler: atur jadwal otomatis"""
    status_msg = StringProperty('')
    status_color = ColorProperty(C['muted'])
    _days = ['senin', 'selasa', 'rabu', 'kamis', 'jumat', 'sabtu', 'minggu']
    _day_labels = ['S', 'S', 'R', 'K', 'J', 'S', 'M']
    _selected_days = set()

    def on_enter(self):
        """Buat tombol hari dan load jadwal dari server"""
        self._selected_days = set()
        container = self.ids.day_buttons
        container.clear_widgets()

        for i, (day, label) in enumerate(zip(self._days, self._day_labels)):
            btn = ToggleButton(
                text=label,
                font_size='12sp',
                bold=True,
                background_color=(0, 0, 0, 0),
                color=C['muted'],
                foreground_color=C['accent'],
                border_normal=C['border'],
                border_pressed=C['accent'],
                size_hint_y=None,
                height='42dp',
                state='down',  # Default aktif
                group='sched_days',
            )

            # Simpan ref hari
            btn.day_name = day

            # Override warna
            def make_bind(b, d):
                def on_state(instance, value):
                    if value == 'down':
                        instance.color = (0.02, 0.04, 0.09, 1)
                        instance.background_color = C['accent']
                        self._selected_days.add(d)
                    else:
                        instance.color = C['muted']
                        instance.background_color = (0, 0, 0, 0)
                        self._selected_days.discard(d)
                return on_state

            btn.bind(state=make_bind(btn, day))
            # Trigger initial
            btn.state = 'down'
            container.add_widget(btn)

        # Load dari server
        def load():
            s = api.get('/api/schedule')
            if s:
                Clock.schedule_once(lambda dt: self._apply_schedule(s), 0)
        threading.Thread(target=load, daemon=True).start()

    def _apply_schedule(self, s: dict):
        self.ids.sched_toggle.active = s.get('enabled', False)
        self.ids.sched_hour.text = str(s.get('hour', 9))
        self.ids.sched_minute.text = str(s.get('minute', 0))

        server_days = set(s.get('days', []))
        for child in self.ids.day_buttons.children:
            if hasattr(child, 'day_name'):
                if child.day_name in server_days:
                    child.state = 'down'
                else:
                    child.state = 'normal'

    def save_schedule(self):
        days_list = list(self._selected_days)
        if not days_list:
            toast_mgr.show('Pilih minimal 1 hari', 'warning')
            return

        payload = {
            'enabled': self.ids.sched_toggle.active,
            'hour': int(self.ids.sched_hour.text or '9'),
            'minute': int(self.ids.sched_minute.text or '0'),
            'days': days_list,
        }

        self.status_msg = 'Menyimpan...'
        self.status_color = C['info']

        def do():
            r = api.post('/api/schedule', payload)
            if r and r.get('success'):
                Clock.schedule_once(
                    lambda dt: (
                        setattr(self, 'status_msg', 'Jadwal berhasil disimpan'),
                        setattr(self, 'status_color', C['accent']),
                        toast_mgr.show('Jadwal tersimpan', 'success')
                    ), 0
                )
            else:
                Clock.schedule_once(
                    lambda dt: (
                        setattr(self, 'status_msg', 'Gagal menyimpan jadwal'),
                        setattr(self, 'status_color', C['error']),
                        toast_mgr.show('Gagal simpan jadwal', 'error')
                    ), 0
                )
        threading.Thread(target=do, daemon=True).start()


class ProductListScreen(Screen):
    """Screen daftar produk dari server"""
    product_count = NumericProperty(0)

    def on_enter(self):
        self.refresh_products()

    def refresh_products(self):
        def do():
            result = api.get('/api/products')
            if result and 'products' in result:
                products = result['products']
                store.set_products(products)
                Clock.schedule_once(lambda dt: self._render(products), 0)
            else:
                Clock.schedule_once(lambda dt: toast_mgr.show('Gagal memuat produk', 'error'), 0)
        threading.Thread(target=do, daemon=True).start()

    def _render(self, products: list):
        self.product_count = len(products)
        container = self.ids.product_list
        container.clear_widgets()

        if not products:
            lbl = Label(
                text='Belum ada produk. Upload CSV terlebih dahulu.',
                font_size='13sp',
                color=C['muted'],
                halign='center',
                size_hint_y=None,
                height='60dp',
            )
            container.add_widget(lbl)
            return

        for p in products:
            row = ProductRow(
                nama=p.get('nama', '-'),
                harga_str=f'Rp {p.get("harga", "0")}',
                desc_preview=(p.get('deskripsi', '-') or '-')[:60],
            )
            container.add_widget(row)


class AccountScreen(Screen):
    """Screen multi-akun management"""
    def on_enter(self):
        self._render_accounts()

    def _render_accounts(self):
        container = self.ids.account_list
        container.clear_widgets()

        if not store.accounts:
            lbl = Label(
                text='Belum ada akun. Tap "Tambah Akun" untuk menambah.',
                font_size='13sp',
                color=C['muted'],
                halign='center',
                size_hint_y=None,
                height='60dp',
            )
            container.add_widget(lbl)
            return

        for acc in store.accounts:
            row = AccountRow(
                label=acc.get('label', '-'),
                platform=acc.get('platform', 'all').upper(),
                active=acc.get('active', True),
            )
            # Tap untuk toggle
            def make_bind(a):
                def on_touch(instance, touch):
                    if instance.collide_point(*touch.pos):
                        store.toggle_account(a['id'])
                        self._render_accounts()
                        toast_mgr.show(
                            f'Akun "{a["label"]}" {"diaktifkan" if a["active"] else "dinonaktifkan"}',
                            'info'
                        )
                        return True
                    return False
                return on_touch
            row.bind(on_touch_down=make_bind(acc))

            # Long press untuk hapus
            def make_long_bind(a, r):
                def on_long(instance, touch):
                    store.remove_account(a['id'])
                    self._render_accounts()
                    toast_mgr.show(f'Akun "{a["label"]}" dihapus', 'warning')
                return on_long
            row.bind(on_long_press=make_long_bind(acc, row))

            container.add_widget(row)

    def show_add_dialog(self):
        """Popup untuk menambah akun baru"""
        popup = Popup(
            title='Tambah Akun',
            size_hint=(0.9, 0.45),
            separator_color=C['border'],
        )
        layout = BoxLayout(orientation='vertical', padding='16dp', spacing='12dp')

        lbl_name = Label(text='Nama Akun:', font_size='13sp', color=C['text'], size_hint_y=None, height='22dp')
        input_name = TextInput(
            hint_text='Contoh: Toko Jaya FB',
            foreground_color=C['text'],
            hint_text_color=C['muted'],
            font_size='14sp',
            padding=['14dp', '10dp'],
            size_hint_y=None,
            height='48dp',
            background_color=C['bg_card'],
            multiline=False,
        )

        lbl_plat = Label(text='Platform:', font_size='13sp', color=C['text'], size_hint_y=None, height='22dp')
        spinner_plat = Spinner(
            text='all (Semua Platform)',
            values=['all (Semua Platform)', 'facebook', 'instagram', 'whatsapp'],
            font_size='13sp',
            color=C['text'],
            background_color=C['bg_card'],
            size_hint_y=None,
            height='48dp',
        )

        btn_add = PrimaryButton(text='TAMBAH')
        btn_cancel = GhostButton(text='Batal')

        def do_add(instance):
            name = input_name.text.strip()
            if not name:
                toast_mgr.show('Nama akun tidak boleh kosong', 'warning')
                return
            plat_text = spinner_plat.text
            plat = 'all'
            if 'facebook' in plat_text.lower():
                plat = 'facebook'
            elif 'instagram' in plat_text.lower():
                plat = 'instagram'
            elif 'whatsapp' in plat_text.lower():
                plat = 'whatsapp'

            store.add_account(name, plat)
            self._render_accounts()
            popup.dismiss()
            toast_mgr.show(f'Akun "{name}" ditambahkan', 'success')

        btn_add.bind(on_press=do_add)
        btn_cancel.bind(on_press=popup.dismiss)

        layout.add_widget(lbl_name)
        layout.add_widget(input_name)
        layout.add_widget(lbl_plat)
        layout.add_widget(spinner_plat)
        layout.add_widget(btn_add)
        layout.add_widget(btn_cancel)
        popup.add_widget(layout)
        popup.open()


class HistoryScreen(Screen):
    """Screen riwayat posting"""
    total_entries = NumericProperty(0)
    total_success = NumericProperty(0)
    total_failed = NumericProperty(0)

    def on_enter(self):
        self._render_history()

    def _render_history(self):
        container = self.ids.history_list
        container.clear_widgets()

        history = store.history
        self.total_entries = len(history)
        self.total_success = sum(1 for h in history if h.get('success'))
        self.total_failed = sum(1 for h in history if not h.get('success'))

        if not history:
            lbl = Label(
                text='Belum ada riwayat. Mulai bot untuk melihat riwayat.',
                font_size='13sp',
                color=C['muted'],
                halign='center',
                size_hint_y=None,
                height='60dp',
            )
            container.add_widget(lbl)
            return

        # Tampilkan dari terbaru
        for entry in reversed(history[-100:]):
            row = HistoryRow(
                time_str=entry.get('time', '--:--'),
                product=entry.get('product', '-')[:30],
                result='OK' if entry.get('success') else 'FAIL',
                success=entry.get('success', False),
            )
            container.add_widget(row)

    def refresh_history(self):
        """Refresh dari server log (rebuild history)"""
        def do():
            result = api.get('/api/logs?count=200')
            if result and 'logs' in result:
                # Rebuild history dari logs
                new_history = []
                for entry in result['logs']:
                    if entry.get('level') in ('success', 'error'):
                        msg = entry.get('message', '')
                        product_name = msg
                        for kw in ["'", '"']:
                            start = msg.find(kw)
                            if start >= 0:
                                end = msg.find(kw, start + 1)
                                if end > start:
                                    product_name = msg[start + 1:end]
                                    break
                        new_history.append({
                            'time': entry.get('timestamp', ''),
                            'product': product_name,
                            'platform': entry.get('platform', ''),
                            'success': entry.get('level') == 'success',
                            'message': msg,
                        })
                store.history = new_history
                Clock.schedule_once(lambda dt: self._render_history(), 0)
            else:
                Clock.schedule_once(lambda dt: toast_mgr.show('Gagal memuat riwayat', 'error'), 0)
        threading.Thread(target=do, daemon=True).start()


# ============================================================
# MAIN APP CLASS
# ============================================================
class MPAPSApp(App):
    """App utama: mengelola screen manager dan navigasi"""

    def build(self):
        Builder.load_string(KV)

        self.sm = ScreenManager(transition=FadeTransition(duration=0.2))

        # Daftarkan semua screen
        self.sm.add_widget(DashboardScreen(name='dashboard'))
        self.sm.add_widget(UploadScreen(name='upload'))
        self.sm.add_widget(LogsScreen(name='logs'))
        self.sm.add_widget(MoreMenuScreen(name='more_menu'))
        self.sm.add_widget(SettingsScreen(name='settings'))
        self.sm.add_widget(SchedulerScreen(name='scheduler'))
        self.sm.add_widget(ProductListScreen(name='product_list'))
        self.sm.add_widget(AccountScreen(name='account'))
        self.sm.add_widget(HistoryScreen(name='history'))

        # Root layout: screen manager di atas, bottom nav di bawah
        self.root = BoxLayout(orientation='vertical')
        self.root.add_widget(self.sm)
        self.root.add_widget(BottomNav())

        # Handle Android back button
        Window.bind(on_keyboard=self._on_keyboard)

        return self.root

    def _on_keyboard(self, instance, keyboard, keycode, text, modifiers):
        """Handle back button Android"""
        if keycode in (27, 1001):  # ESC atau back button
            current = self.sm.current
            # Jika di sub-screen, kembali ke more_menu atau dashboard
            sub_screens = ['settings', 'scheduler', 'product_list', 'account', 'history']
            if current in sub_screens:
                self.switch_screen('more_menu')
                return True
            elif current in ('upload', 'logs', 'more_menu'):
                self.switch_screen('dashboard')
                return True
        return False

    def switch_screen(self, name: str):
        """Pindah screen dan update nav highlight"""
        # Leave event untuk screen sebelumnya
        prev = self.sm.current_screen
        if hasattr(prev, 'on_leave'):
            prev.on_leave()

        self.sm.current = name

        # Update nav highlight
        nav_map = {
            'dashboard': 'nav_dash',
            'upload': 'nav_upload',
            'logs': 'nav_logs',
            'more_menu': 'nav_more',
        }
        for screen_name, nav_id in nav_map.items():
            nav = self.root.ids.get(nav_id)
            if nav:
                nav.text_color = C['accent'] if screen_name == name else C['muted']

        # Enter event untuk screen baru
        new_screen = self.sm.current_screen
        if hasattr(new_screen, 'on_enter'):
            new_screen.on_enter()

    def on_pause(self):
        """Dipanggil saat app ke background (Android)"""
        return True  # Biarkan tetap berjalan di background

    def on_resume(self):
        """Dipanggil saat app kembali ke foreground"""
        # Reconnect WebSocket jika terputus
        if not ws_client.connected and api.base_url:
            ws_url = api.base_url.replace('http', 'ws') + '/ws/logs'
            ws_client.connect(ws_url)


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == '__main__':
    MPAPSApp().run()