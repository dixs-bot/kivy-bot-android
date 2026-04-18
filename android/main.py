import json, os, threading, time
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ColorProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton

C = {
    'bg': (0.024, 0.043, 0.094, 1), 'bg_card': (0.067, 0.102, 0.180, 1),
    'border': (0.102, 0.153, 0.267, 1), 'border_l': (0.141, 0.200, 0.337, 1),
    'accent': (0.000, 0.898, 0.627, 1), 'accent_dim': (0.102, 0.239, 0.200, 1),
    'error': (1.000, 0.278, 0.341, 1), 'error_dim': (0.165, 0.051, 0.078, 1),
    'warning': (1.000, 0.647, 0.008, 1), 'warning_dim': (0.165, 0.102, 0.008, 1),
    'info': (0.561, 0.643, 0.788, 1), 'info_dim': (0.051, 0.102, 0.165, 1),
    'text': (0.910, 0.929, 0.961, 1), 'muted': (0.420, 0.478, 0.600, 1),
    'white': (1, 1, 1, 1), 'fb': (0.357, 0.498, 0.843, 1),
    'ig': (0.910, 0.376, 0.541, 1), 'wa': (0.145, 0.820, 0.400, 1),
    'success_bg': (0.051, 0.165, 0.122, 1)
}

class DataStore:
    def __init__(self):
        self.products = []
        self.history = []
        self.accounts = [{"id": 1, "label": "Akun Utama", "platform": "all", "active": True}]
        self.next_account_id = 2
    def set_products(self, p): self.products = p
    def add_history(self, e):
        self.history.append(e)
        if len(self.history) > 200: self.history = self.history[-200:]
store = DataStore()

class ToastManager:
    @mainthread
    def show(self, message, toast_type="info"):
        app = App.get_running_app()
        if not app or not app.root: return
        colors = {'success': C['accent'], 'error': C['error'], 'warning': C['warning'], 'info': C['info']}
        try:
            toast = BoxLayout(size_hint=(0.9, None), height=dp(48), pos_hint={'center_x': 0.5, 'top': 0.95})
            lbl = Label(text=message, font_size=sp(12), color=colors.get(toast_type, C['info']))
            toast.add_widget(lbl)
            app.root.add_widget(toast)
            Clock.schedule_once(lambda dt: app.root.remove_widget(toast) if toast.parent else None, 3.0)
        except: pass
toast_mgr = ToastManager()

class ApiClient:
    def __init__(self):
        self.base_url = 'http://192.168.1.100:8000'
        self.api_key = 'mpaps-2024-secret-key-change-me'
    def _req(self, method, path, data=None, files=None):
        import urllib.request, urllib.error
        url = self.base_url.rstrip('/') + path
        hdrs = {'X-API-Key': self.api_key}
        rd = None
        if files:
            b = '----MPAPS' + str(int(time.time()*1000))
            body = bytearray()
            for fn,(fn2,fb) in files.items():
                body.extend(f'--{b}\r\nContent-Disposition: form-data; name="{fn}"; filename="{fn2}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
                body.extend(fb if isinstance(fb,bytes) else fb.encode()); body.extend(b'\r\n')
            body.extend(f'--{b}--\r\n'.encode())
            hdrs['Content-Type']=f'multipart/form-data; boundary={b}'; rd=bytes(body)
        elif data is not None:
            rd=json.dumps(data).encode('utf-8'); hdrs['Content-Type']='application/json'
        req = urllib.request.Request(url, data=rd, headers=hdrs, method=method)
        try:
            return json.loads(urllib.request.urlopen(req, timeout=12).read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try: return json.loads(e.read().decode('utf-8'))
            except: return {'success':False,'detail':f'HTTP {e.code}'}
        except Exception as e: return {'success':False,'detail':str(e)}
    def get(self, p): return self._req('GET', p)
    def post(self, p, d=None): return self._req('POST', p, d)
    def delete(self, p): return self._req('DELETE', p)
    def upload_csv(self, fp):
        with open(fp,'rb') as f: fb=f.read()
        return self._req('POST','/api/upload-csv',files={'file':(os.path.basename(fp),fb)})
    def health_check(self): return self.get('/api/health').get('status')=='ok'
api = ApiClient()

class WSClient:
    def __init__(self):
        self.connected=False; self._running=False; self._ws=None
        self.on_log=self.on_status=self.on_connect=self.on_disconnect=None; self._using_polling=False
    def connect(self, url):
        self.disconnect(); self._running=True
        threading.Thread(target=self._run, args=(url,), daemon=True).start()
    def disconnect(self):
        self._running=False; self.connected=False
        if self._ws:
            try: self._ws.close()
            except: pass
            self._ws=None
    def _run(self, url):
        try:
            import websocket; self._run_ws(url)
        except ImportError: self._run_polling()
    def _run_ws(self, url):
        import websocket
        while self._running:
            try:
                self._ws=websocket.WebSocket(); self._ws.settimeout(5); self._ws.connect(url)
                self.connected=True; self._using_polling=False
                if self.on_connect: Clock.schedule_once(lambda dt: self.on_connect(), 0)
                while self._running:
                    try:
                        d=self._ws.recv()
                        if not d: break
                        m=json.loads(d)
                        t=m.get('type')
                        if t=='log' and self.on_log: Clock.schedule_once(lambda dt, mm=m.get('data',{}): self.on_log(mm), 0)
                        elif t=='status' and self.on_status: Clock.schedule_once(lambda dt, mm=m.get('data',{}): self.on_status(mm), 0)
                        elif t=='logs_init' and self.on_log:
                            for e in m.get('data',[]): Clock.schedule_once(lambda dt, ee=e: self.on_log(ee), 0)
                    except websocket.WebSocketTimeoutException:
                        try: self._ws.ping()
                        except: break
                    except: break
            except: pass
            self.connected=False
            if self.on_disconnect: Clock.schedule_once(lambda dt: self.on_disconnect(), 0)
            if not self._running: break
            time.sleep(3)
        if self._running: self._run_polling()
    def _run_polling(self):
        self.connected=False; self._using_polling=True
        if self.on_disconnect: Clock.schedule_once(lambda dt: self.on_disconnect(), 0)
        lc=-1
        while self._running:
            try:
                r=api.get('/api/logs?count=30')
                if r and 'logs' in r and len(r['logs'])!=lc:
                    lc=len(r['logs'])
                    for e in r['logs'][-5:]:
                        if self.on_log: Clock.schedule_once(lambda dt, ee=e: self.on_log(ee), 0)
                s=api.get('/api/status')
                if s and self.on_status: Clock.schedule_once(lambda dt, ss=s: self.on_status(ss), 0)
            except: pass
            time.sleep(3)
ws_client = WSClient()

# ============================================================
# KV LAYOUT (SUPER STERIL - TANPA POS MANUAL YANG CRASH)
# ============================================================
KV = '''
<NavButton@ButtonBehavior+BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: '56dp'
    padding: ('4dp', '6dp')
    spacing: '3dp'
    canvas.before:
        Color: rgba: (0,0,0,0)
        Rectangle: pos: self.pos; size: self.size
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
        Color: rgba: self.background_color
        RoundedRectangle: pos: self.pos; size: self.size; radius: [12]

<DangerButton@Button>:
    background_color: C['error']
    color: C['white']
    font_size: '14sp'
    bold: True
    size_hint_y: None
    height: '50dp'
    canvas.before:
        Color: rgba: self.background_color
        RoundedRectangle: pos: self.pos; size: self.size; radius: [12]

<GhostButton@Button>:
    background_color: (0,0,0,0)
    color: C['text']
    font_size: '13sp'
    size_hint_y: None
    height: '42dp'
    canvas.before:
        Color: rgba: C['border']
        RoundedRectangle: pos: self.pos; size: self.size; radius: [10]

<CardBox@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.minimum_height
    padding: '16dp'
    spacing: '10dp'
    canvas.before:
        Color: rgba: C['bg_card']
        RoundedRectangle: pos: self.pos; size: self.size; radius: [12]

<SectionTitle@Label>:
    color: C['muted']
    font_size: '11sp'
    size_hint_y: None
    height: '16dp'

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
        Color: rgba: C['border']
        RoundedRectangle: pos: self.pos; size: self.size; radius: [10]

# AMAN: Menggunakan pos_hint alih-alih hitungan manual parent.pos
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
            Color: rgba: C['accent'] if root.active else C['border_l']
            RoundedRectangle: pos: self.pos; size: self.size; radius: [12]
        BoxLayout:
            size_hint_x: None
            width: '30dp'
            height: '30dp'
            pos_hint: {'center_x': 0.6 if root.active else 0.4, 'center_y': 0.5}
            canvas.before:
                Color: rgba: C['white']
                RoundedRectangle: pos: self.pos; size: self.size; radius: [8]

<PlatformChip@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '44dp'
    padding: ('12dp', '8dp')
    spacing: '12dp'
    canvas.before:
        Color: rgba: C['bg_card']
        RoundedRectangle: pos: self.pos; size: self.size; radius: [10]
    Label: text: root.icon; font_size: '18sp'; color: root.chip_color; size_hint_x: None; width: '28dp'
    Label: text: root.name; font_size: '13sp'; color: C['text']; valign: 'middle'
    Label: text: '\\u25CF'; font_size: '12sp'; color: C['accent'] if root.is_on else C['error']; size_hint_x: None; width: '20dp'; halign: 'right'

<LogLine@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '22dp'
    padding: ('0dp', '1dp')
    spacing: '6dp'
    Label: text: root.time_str; font_size: '10sp'; font_name: 'Roboto'; color: C['muted']; size_hint_x: None; width: '55dp'
    Label: text: root.level_str; font_size: '9sp'; bold: True; color: root.level_color; size_hint_x: None; width: '55dp'
    Label: text: root.platform_str; font_size: '9sp'; color: root.platform_color; size_hint_x: None; width: '70dp'
    Label: text: root.message; font_size: '10sp'; font_name: 'Roboto'; color: C['text']; halign: 'left'; valign: 'middle'; shorten_from: 'right'

<ProductRow@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: '72dp'
    padding: ('14dp', '10dp')
    spacing: '4dp'
    canvas.before:
        Color: rgba: C['bg_card']
        RoundedRectangle: pos: self.pos; size: self.size; radius: [10]
    Label: text: root.nama; font_size: '14sp'; bold: True; color: C['text']; size_hint_y: None; height: '20dp'; shorten_from: 'right'
    Label: text: root.harga_str; font_size: '13sp'; font_name: 'Roboto'; color: C['accent']; size_hint_y: None; height: '18dp'
    Label: text: root.desc_preview; font_size: '11sp'; color: C['muted']; size_hint_y: None; height: '16dp'; shorten_from: 'right'

<AccountRow@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '52dp'
    padding: ('14dp', '8dp')
    spacing: '10dp'
    canvas.before:
        Color: rgba: C['bg_card']
        RoundedRectangle: pos: self.pos; size: self.size; radius: [10]
    Label: text: root.label; font_size: '13sp'; color: C['text']; valign: 'middle'
    Label: text: root.platform; font_size: '10sp'; color: C['muted']; valign: 'middle'
    Label: text: 'AKTIF' if root.active else 'OFF'; font_size: '9sp'; bold: True; color: C['accent'] if root.active else C['error']; size_hint_x: None; width: '60dp'; halign: 'right'

<HistoryRow@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '50dp'
    padding: ('14dp', '6dp')
    spacing: '8dp'
    canvas.before:
        Color: rgba: C['bg_card']
        RoundedRectangle: pos: self.pos; size: self.size; radius: [10]
    Label: text: root.time_str; font_size: '10sp'; font_name: 'Roboto'; color: C['muted']; size_hint_x: None; width: '50dp'; valign: 'middle'
    Label: text: root.product; font_size: '12sp'; color: C['text']; valign: 'middle'
    Label: text: root.result; font_size: '9sp'; bold: True; color: C['accent'] if root.success else C['error']; size_hint_x: None; width: '50dp'; halign: 'right'

<BottomNav@BoxLayout>:
    orientation: 'horizontal'
    size_hint_y: None
    height: '68dp'
    padding: ['6dp', '4dp']
    spacing: '2dp'
    canvas.before:
        Color: rgba: (0.055, 0.078, 0.133, 1)
        Rectangle: pos: self.pos; size: self.size
        Color: rgba: C['border']
        Rectangle: pos: (self.pos[0], self.pos[1]); size: (self.size[0], 1)
    NavButton:
        id: nav_dash
        icon: '\\u26A1'
        label: 'Dashboard'
        on_press: app.switch_screen('dashboard')
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

<DashboardScreen>:
    orientation: 'vertical'; padding: '16dp'; spacing: '12dp'
    BoxLayout:
        size_hint_y: None; height: '44dp'
        Label: text: 'MPAPS Controller'; font_size: '20sp'; bold: True; color: C['text']
        BoxLayout: orientation: 'horizontal'; size_hint_x: None; width: '120dp'; spacing: '6dp'
            Label: text: '\\u25CF'; font_size: '10sp'; color: C['accent'] if root.connected else C['error']
            Label: text: root.ws_label; font_size: '10sp'; color: C['accent'] if root.connected else C['error']
    CardBox:
        height: '80dp'
        SectionTitle: text: 'STATUS BOT'
        BoxLayout:
            size_hint_y: None; height: '44dp'; spacing: '12dp'
            Label: text: '\\u25CF'; font_size: '28sp'; color: C['accent'] if root.bot_running else C['error']; size_hint_x: None; width: '40dp'
            Label: text: 'RUNNING' if root.bot_running else 'STOPPED'; font_size: '24sp'; bold: True; font_name: 'Roboto'; color: C['accent'] if root.bot_running else C['error']
    BoxLayout:
        size_hint_y: None; height: '115dp'; spacing: '10dp'
        CardBox:
            height: '115dp'; SectionTitle: text: 'DIPROSES'; BigValue: text: str(root.stat_processed); SmallInfo: text: f'dari {root.stat_total} produk'
        CardBox:
            height: '115dp'; SectionTitle: text: 'BERHASIL'; BigValue: text: str(root.stat_success); color: C['accent']
        CardBox:
            height: '115dp'; SectionTitle: text: 'GAGAL'; BigValue: text: str(root.stat_failed); color: C['error']
    CardBox:
        height: '68dp'
        SectionTitle: text: 'PROGRESS'
        BoxLayout:
            size_hint_y: None; height: '10dp'
            canvas.before:
                Color: rgba: C['border']; RoundedRectangle: pos: self.pos; size: self.size; radius: [5]
            BoxLayout:
                size_hint_x: root.progress / 100.0 if root.progress > 0 else 0
                canvas.before:
                    Color: rgba: C['accent']; RoundedRectangle: pos: self.pos; size: self.size; radius: [5]
        Label: text: f'{root.progress}%  |  {root.stat_processed}/{root.stat_total}'; font_size: '11sp'; font_name: 'Roboto'; color: C['muted']; size_hint_y: None; height: '18dp'
    SectionTitle: text: 'PLATFORM AKTIF'
    BoxLayout:
        size_hint_y: None; height: '48dp'; spacing: '8dp'
        PlatformChip: icon: 'f'; name: 'Facebook'; chip_color: C['fb']; is_on: root.plat_fb
        PlatformChip: icon: 'i'; name: 'Instagram'; chip_color: C['ig']; is_on: root.plat_ig
        PlatformChip: icon: 'w'; name: 'WhatsApp'; chip_color: C['wa']; is_on: root.plat_wa
    BoxLayout:
        size_hint_y: None; height: '54dp'; spacing: '12dp'
        PrimaryButton: text: '\\u25B6  MULAI BOT'; disabled: root.bot_running; on_press: root.start_bot()
        DangerButton: text: '\\u25A0  HENTIKAN'; disabled: not root.bot_running; on_press: root.stop_bot()
    Label: text: f'Uptime: {root.uptime}'; font_size: '11sp'; font_name: 'Roboto'; color: C['muted']; halign: 'center'; size_hint_y: None; height: '18dp'

<UploadScreen>:
    orientation: 'vertical'; padding: '16dp'; spacing: '12dp'
    Label: text: 'Upload CSV'; font_size: '20sp'; bold: True; color: C['text']; size_hint_y: None; height: '44dp'
    CardBox:
        height: '170dp'; spacing: '12dp'
        Label: text: 'Pilih file CSV berisi data produk'; font_size: '14sp'; color: C['muted']; size_hint_y: None; height: '22dp'
        Label: text: 'Format: nama, harga, deskripsi, gambar'; font_size: '11sp'; color: C['muted']; size_hint_y: None; height: '18dp'
        Label: text: root.file_label; font_size: '12sp'; color: C['accent'] if 'Terpilih' in root.file_label else C['muted']; size_hint_y: None; height: '18dp'
        PrimaryButton: text: 'PILIH FILE CSV'; size_hint_y: None; height: '46dp'; on_press: root.show_file_chooser()
    Label: text: root.upload_result; font_size: '13sp'; color: root.result_color; halign: 'center'; size_hint_y: None; height: '22dp'
    SectionTitle: text: f'PREVIEW DATA ({root.preview_count} produk)'
    ScrollView:
        CardBox:
            id: preview_container; height: self.minimum_height; spacing: '4dp'
    PrimaryButton: text: 'UPLOAD KE SERVER'; disabled: not root.has_file; on_press: root.do_upload()

<LogsScreen>:
    orientation: 'vertical'; padding: '16dp'; spacing: '10dp'
    BoxLayout:
        size_hint_y: None; height: '44dp'
        Label: text: 'Log Viewer'; font_size: '20sp'; bold: True; color: C['text']
        Label: text: f'{root.log_count} entri'; font_size: '11sp'; font_name: 'Roboto'; color: C['muted']; halign: 'right'
    BoxLayout:
        size_hint_y: None; height: '36dp'; spacing: '6dp'
        GhostButton: text: 'Semua'; size_hint_y: None; height: '34dp'; font_size: '11sp'; on_press: root.set_filter('all')
        GhostButton: text: 'Sukses'; size_hint_y: None; height: '34dp'; font_size: '11sp'; on_press: root.set_filter('success')
        GhostButton: text: 'Error'; size_hint_y: None; height: '34dp'; font_size: '11sp'; on_press: root.set_filter('error')
    ScrollView:
        id: log_scroll; do_scroll_x: False
        BoxLayout:
            id: log_list; orientation: 'vertical'; size_hint_y: None; height: self.minimum_height; spacing: '1dp'
    BoxLayout:
        size_hint_y: None; height: '44dp'; spacing: '10dp'
        GhostButton: text: 'Refresh'; size_hint_y: None; height: '40dp'; on_press: root.refresh_logs()
        GhostButton: text: 'Clear'; size_hint_y: None; height: '40dp'; color: C['error']; on_press: root.clear_logs()

<MoreMenuScreen>:
    orientation: 'vertical'; padding: '16dp'; spacing: '10dp'
    Label: text: 'Menu Lainnya'; font_size: '20sp'; bold: True; color: C['text']; size_hint_y: None; height: '44dp'
    CardBox:
        height: '54dp'
        canvas.before:
            Color: rgba: C['bg_card']; RoundedRectangle: pos: self.pos; size: self.size; radius: [12]
        BoxLayout:
            size_hint_y: None; height: '54dp'; padding: ('16dp', '8dp'); spacing: '14dp'
            Label: text: '\\u2699'; font_size: '20sp'; color: C['accent']
            Label: text: 'Pengaturan Bot'; font_size: '14sp'; color: C['text']
            Label: text: '\\u203A'; font_size: '20sp'; color: C['muted']; size_hint_x: None; width: '24dp'; halign: 'right'
    BoxLayout:
        size_hint_y: None; height: '40dp'
        Label: text: root.connection_info; font_size: '11sp'; color: C['muted']; halign: 'center'

<SettingsScreen>:
    orientation: 'vertical'; padding: '16dp'; spacing: '12dp'
    BoxLayout:
        size_hint_y: None; height: '44dp'
        Label: text: 'Pengaturan'; font_size: '20sp'; bold: True; color: C['text']
        Button: text: 'Kembali'; background_color: (0,0,0,0); color: C['accent']; font_size: '13sp'; size_hint_x: None; width: '70dp'; on_press: app.switch_screen('more_menu')
    CardBox:
        height: '130dp'
        SectionTitle: text: 'KONEKSI SERVER'
        FormInput: id: server_url; text: 'http://192.168.1.100:8000'; hint_text: 'http://IP:8000'
        FormInput: id: api_key; text: 'mpaps-2024-secret-key-change-me'; hint_text: 'API Key'
    CardBox:
        height: '130dp'
        SectionTitle: text: 'DELAY POSTING (DETIK)'
        BoxLayout:
            size_hint_y: None; height: '50dp'; spacing: '10dp'
            FormInput: id: delay_min; text: '5'; hint_text: 'Min'; input_type: 'number'
            FormInput: id: delay_max; text: '15'; hint_text: 'Max'; input_type: 'number'
        FormInput: id: retry_max; text: '3'; hint_text: 'Max Retry'; input_type: 'number'
    CardBox:
        height: '164dp'
        SectionTitle: text: 'PLATFORM'
        ToggleRow: id: tog_fb; text: 'Facebook'; active: True; on_press: self.active = not self.active
        ToggleRow: id: tog_ig; text: 'Instagram'; active: True; on_press: self.active = not self.active
        ToggleRow: id: tog_wa; text: 'WhatsApp'; active: True; on_press: self.active = not self.active
    PrimaryButton: text: 'SIMPAN & HUBUNGKAN'; on_press: root.save_and_connect()
    Label: text: root.status_msg; font_size: '12sp'; color: root.status_color; halign: 'center'; size_hint_y: None; height: '20dp'

<SchedulerScreen>:
    orientation: 'vertical'; padding: '16dp'; spacing: '12dp'
    BoxLayout:
        size_hint_y: None; height: '44dp'
        Label: text: 'Scheduler'; font_size: '20sp'; bold: True; color: C['text']
        Button: text: 'Kembali'; background_color: (0,0,0,0); color: C['accent']; font_size: '13sp'; size_hint_x: None; width: '70dp'; on_press: app.switch_screen('more_menu')
    CardBox: height: '64dp'; SectionTitle: text: 'AKTIFKAN SCHEDULER'; ToggleRow: id: sched_toggle; text: 'Jalankan bot otomatis'; active: False; on_press: self.active = not self.active
    CardBox:
        height: '110dp'
        SectionTitle: text: 'WAKTU EKSEKUSI'
        BoxLayout:
            size_hint_y: None; height: '50dp'; spacing: '8dp'
            FormInput: id: sched_hour; text: '9'; hint_text: 'Jam'; input_type: 'number'
            Label: text: ':'; font_size: '24sp'; color: C['muted']; size_hint_x: None; width: '20dp'; halign: 'center'
            FormInput: id: sched_minute; text: '0'; hint_text: 'Menit'; input_type: 'number'
    CardBox: height: '100dp'; SectionTitle: text: 'HARI AKTIF'; BoxLayout: id: day_buttons; size_hint_y: None; height: '44dp'; spacing: '6dp'
    PrimaryButton: text: 'SIMPAN JADWAL'; on_press: root.save_schedule()
    Label: text: root.status_msg; font_size: '12sp'; color: root.status_color; halign: 'center'; size_hint_y: None; height: '20dp'

<ProductListScreen>:
    orientation: 'vertical'; padding: '16dp'; spacing: '10dp'
    BoxLayout:
        size_hint_y: None; height: '44dp'
        Label: text: 'Daftar Produk'; font_size: '20sp'; bold: True; color: C['text']
        Button: text: 'Kembali'; background_color: (0,0,0,0); color: C['accent']; font_size: '13sp'; size_hint_x: None; width: '70dp'; on_press: app.switch_screen('more_menu')
    Label: text: f'Total: {root.product_count} produk'; font_size: '12sp'; color: C['muted']; size_hint_y: None; height: '20dp'
    ScrollView: id: product_scroll; do_scroll_x: False
        BoxLayout: id: product_list; orientation: 'vertical'; size_hint_y: None; height: self.minimum_height; spacing: '6dp'
    GhostButton: text: 'Refresh dari Server'; on_press: root.refresh_products()

<AccountScreen>:
    orientation: 'vertical'; padding: '16dp'; spacing: '10dp'
    BoxLayout:
        size_hint_y: None; height: '44dp'
        Label: text: 'Multi Akun'; font_size: '20sp'; bold: True; color: C['text']
        Button: text: 'Kembali'; background_color: (0,0,0,0); color: C['accent']; font_size: '13sp'; size_hint_x: None; width: '70dp'; on_press: app.switch_screen('more_menu')
    ScrollView: id: account_scroll; do_scroll_x: False
        BoxLayout: id: account_list; orientation: 'vertical'; size_hint_y: None; height: self.minimum_height; spacing: '6dp'
    PrimaryButton: text: '+ TAMBAH AKUN'; on_press: root.show_add_dialog()

<HistoryScreen>:
    orientation: 'vertical'; padding: '16dp'; spacing: '10dp'
    BoxLayout:
        size_hint_y: None; height: '44dp'
        Label: text: 'Riwayat Posting'; font_size: '20sp'; bold: True; color: C['text']
        Button: text: 'Kembali'; background_color: (0,0,0,0); color: C['accent']; font_size: '13sp'; size_hint_x: None; width: '70dp'; on_press: app.switch_screen('more_menu')
    BoxLayout:
        size_hint_y: None; height: '60dp'; spacing: '10dp'
        CardBox: height: '60dp'; SectionTitle: text: 'TOTAL'; Label: text: str(root.total_entries); font_size: '20sp'; font_name: 'Roboto'; color: C['text']; size_hint_y: None; height: '28dp'
        CardBox: height: '60dp'; SectionTitle: text: 'SUKSES'; Label: text: str(root.total_success); font_size: '20sp'; font_name: 'Roboto'; color: C['accent']; size_hint_y: None; height: '28dp'
        CardBox: height: '60dp'; SectionTitle: text: 'GAGAL'; Label: text: str(root.total_failed); font_size: '20sp'; font_name: 'Roboto'; color: C['error']; size_hint_y: None; height: '28dp'
    ScrollView: id: history_scroll; do_scroll_x: False
        BoxLayout: id: history_list; orientation: 'vertical'; size_hint_y: None; height: self.minimum_height; spacing: '4dp'
    GhostButton: text: 'Refresh'; on_press: root.refresh_history()
'''

# ============================================================
# SCREEN IMPLEMENTATIONS
# ============================================================
class DashboardScreen(Screen):
    bot_running=BooleanProperty(False); connected=BooleanProperty(False); ws_label=StringProperty('Terputus')
    stat_processed=NumericProperty(0); stat_success=NumericProperty(0); stat_failed=NumericProperty(0); stat_total=NumericProperty(0); progress=NumericProperty(0); uptime=StringProperty('00:00:00')
    plat_fb=BooleanProperty(True); plat_ig=BooleanProperty(True); plat_wa=BooleanProperty(True)
    def __init__(self, **kw):
        super().__init__(**kw)
        ws_client.on_status=self._on_status; ws_client.on_connect=self._on_c; ws_client.on_disconnect=self._on_d
    def _on_c(self): self.connected=True; self.ws_label='WebSocket' if not ws_client._using_polling else 'Polling'
    def _on_d(self): self.connected=False; self.ws_label='Terputus'
    def _on_status(self, d):
        self.bot_running=d.get('running',False); self.stat_processed=d.get('current_index',0); self.stat_success=d.get('total_posted',0); self.stat_failed=d.get('total_failed',0); self.stat_total=d.get('total_products',0); self.uptime=d.get('uptime','00:00:00')
        t=max(self.stat_total,1); self.progress=round((self.stat_processed/t)*100) if self.bot_running else (100 if self.stat_success>0 else 0)
    def start_bot(self):
        def do():
            r=api.post('/api/start-bot')
            if r:
                s=api.get('/api/status')
                if s: Clock.schedule_once(lambda dt: self._on_status(s), 0)
                Clock.schedule_once(lambda dt: toast_mgr.show(r.get('message',''),'success' if r.get('success') else 'warning'), 0)
        threading.Thread(target=do, daemon=True).start()
    def stop_bot(self):
        def do():
            r=api.post('/api/stop-bot')
            if r:
                s=api.get('/api/status')
                if s: Clock.schedule_once(lambda dt: self._on_status(s), 0)
                Clock.schedule_once(lambda dt: toast_mgr.show(r.get('message',''),'success' if r.get('success') else 'warning'), 0)
        threading.Thread(target=do, daemon=True).start()
    def on_enter(self):
        def ref():
            s=api.get('/api/status')
            if s: Clock.schedule_once(lambda dt: self._on_status(s), 0)
        threading.Thread(target=ref, daemon=True).start()

class UploadScreen(Screen):
    file_label=StringProperty('Belum ada file dipilih'); upload_result=StringProperty(''); result_color=ColorProperty(C['muted']); preview_count=NumericProperty(0); has_file=BooleanProperty(False)
    _filepath=None; _local_rows=[]
    def show_file_chooser(self):
        popup=Popup(title='Pilih File CSV', size_hint=(0.95,0.6))
        layout=BoxLayout(orientation='vertical', spacing='8dp')
        fc=FileChooserListView(filters=['*.csv'], path='/storage/emulated/0/Download')
        def on_sel(inst, sel, *a):
            if sel and sel[0].endswith('.csv'):
                self._filepath=sel[0]; self.file_label='Terpilih: '+os.path.basename(self._filepath); self.has_file=True; self._parse(self._filepath); popup.dismiss()
        fc.on_selection=on_sel
        layout.add_widget(fc); layout.add_widget(Button(text='Batal', background_color=(0,0,0,0), color=C['muted'], size_hint_y=None, height='44dp', on_press=popup.dismiss))
        popup.add_widget(layout); popup.open()
    def _parse(self, fp):
        self._local_rows=[]
        try:
            with open(fp,'r',encoding='utf-8') as f: lines=f.readlines()
            for l in lines[1:]:
                l=l.strip()
                if not l: continue
                p,c,q=[], '', False
                for ch in l:
                    if ch=='"': q=not q
                    elif ch==',' and not q: p.append(c.strip()); c=''
                    else: c+=ch
                p.append(c.strip())
                if len(p)>=2: self._local_rows.append({'nama':p[0],'harga':p[1],'deskripsi':p[2] if len(p)>2 else '','gambar':p[3] if len(p)>3 else ''})
            self.preview_count=len(self._local_rows)
            ct=self.ids.preview_container; ct.clear_widgets()
            for pr in self._local_rows[:20]: ct.add_widget(ProductRow(nama=pr.get('nama','-'), harga_str='Rp '+pr.get("harga","0"), desc_preview=pr.get('deskripsi','-')[:50]))
            self.upload_result=''
        except Exception as e: self.upload_result='Error: '+str(e); self.result_color=C['error']
    def do_upload(self):
        if not self._filepath: return
        self.upload_result='Mengupload...'; self.result_color=C['info']
        def do():
            r=api.upload_csv(self._filepath)
            if r and r.get('success'): Clock.schedule_once(lambda dt: (setattr(self,'upload_result','Berhasil'), setattr(self,'result_color',C['accent']), toast_mgr.show('Diupload','success')),0)
            else: Clock.schedule_once(lambda dt: (setattr(self,'upload_result','Gagal'), setattr(self,'result_color',C['error'])),0)
        threading.Thread(target=do, daemon=True).start()

class LogsScreen(Screen):
    log_count=NumericProperty(0); _cur_filt='all'; _all_logs=[]; _orig=None
    def on_enter(self):
        self._orig=ws_client.on_log; ws_client.on_log=self._on_log; self.refresh_logs()
    def on_leave(self):
        if self._orig: ws_client.on_log=self._orig
    def _on_log(self, e):
        self._all_logs.append(e)
        if len(self._all_logs)>300: self._all_logs=self._all_logs[-300:]
        if e.get('level') in ('success','error'):
            m=e.get('message',''); pn=m
            for k in ["'",'"']:
                s,ee=m.find(k),m.find(k,m.find(k)+1)
                if s>=0 and ee>s: pn=m[s+1:ee]; break
            store.add_history({'time':e.get('timestamp',''),'product':pn,'success':e.get('level')=='success'})
        self._render_entry(e); self.log_count=len(self._all_logs)
    def _render_entry(self, e):
        lv=e.get('level','info')
        if self._cur_filt!='all' and lv!=self._cur_filt: return
        cm={'success':C['accent'],'error':C['error'],'warning':C['warning'],'info':C['info']}
        pcm={'facebook':C['fb'],'instagram':C['ig'],'whatsapp':C['wa'],'system':C['muted']}
        ll=LogLine(time_str=e.get('timestamp','--:--:--'),level_str=lv.upper(),level_color=cm.get(lv,C['muted']),platform_str=e.get('platform','sys').upper(),platform_color=pcm.get(e.get('platform',''),C['muted']),message=e.get('message',''))
        self.ids.log_list.add_widget(ll)
        while len(self.ids.log_list.children)>150: self.ids.log_list.remove_widget(self.ids.log_list.children[0])
    def set_filter(self, f): self._cur_filt=f; self._render_all()
    def _render_all(self):
        self.ids.log_list.clear_widgets()
        cm={'success':C['accent'],'error':C['error'],'warning':C['warning'],'info':C['info']}
        pcm={'facebook':C['fb'],'instagram':C['ig'],'whatsapp':C['wa'],'system':C['muted']}
        fl=self._all_logs if self._cur_filt=='all' else [l for l in self._all_logs if l.get('level')==self._cur_filt]
        for e in fl[-100:]:
            lv=e.get('level','info')
            self.ids.log_list.add_widget(LogLine(time_str=e.get('timestamp','--:--:--'),level_str=lv.upper(),level_color=cm.get(lv,C['muted']),platform_str=e.get('platform','sys').upper(),platform_color=pcm.get(e.get('platform',''),C['muted']),message=e.get('message','')))
    def refresh_logs(self):
        def do():
            r=api.get('/api/logs?count=100')
            if r and 'logs' in r: self._all_logs=r['logs']; Clock.schedule_once(lambda dt: self._render_all(),0)
        threading.Thread(target=do, daemon=True).start()
    def clear_logs(self):
        def do():
            api.delete('/api/logs')
            Clock.schedule_once(lambda dt: (self._all_logs.clear(), self.ids.log_list.clear_widgets(), setattr(self,'log_count',0)),0)
        threading.Thread(target=do, daemon=True).start()

class MoreMenuScreen(Screen):
    product_count=NumericProperty(0); connection_info=StringProperty('')
    def on_enter(self):
        self.product_count=len(store.products)
        m='WebSocket' if ws_client.connected and not ws_client._using_polling else ('Polling' if ws_client._using_polling else 'Terputus')
        self.connection_info=api.base_url+' | '+m

class SettingsScreen(Screen):
    status_msg=StringProperty(''); status_color=ColorProperty(C['muted'])
    def save_and_connect(self):
        url=self.ids.server_url.text.rstrip('/')
        if not url.startswith('http'): return
        api.base_url=url; api.api_key=self.ids.api_key.text; self.status_msg='Menghubungkan...'; self.status_color=C['info']
        def do():
            if not api.health_check(): Clock.schedule_once(lambda dt: (setattr(self,'status_msg','Gagal'),setattr(self,'status_color',C['error'])),0); return
            api.post('/api/settings',{'delay_min':int(self.ids.delay_min.text or '5'),'delay_max':int(self.ids.delay_max.text or '15'),'retry_max':int(self.ids.retry_max.text or '3'),'platform_facebook':self.ids.tog_fb.active,'platform_instagram':self.ids.tog_ig.active,'platform_whatsapp':self.ids.tog_wa.active})
            ws_client.disconnect(); time.sleep(0.5); ws_client.connect(url.replace('http','ws')+'/ws/logs')
            Clock.schedule_once(lambda dt: (setattr(self,'status_msg','Terhubung!'),setattr(self,'status_color',C['accent'])),0)
        threading.Thread(target=do, daemon=True).start()
    def on_enter(self):
        self.ids.server_url.text=api.base_url; self.ids.api_key.text=api.api_key

class SchedulerScreen(Screen):
    status_msg=StringProperty(''); status_color=ColorProperty(C['muted']); _days=['senin','selasa','rabu','kamis','jumat','sabtu','minggu']; _sel_days=set()
    def on_enter(self):
        self._sel_days=set(); ct=self.ids.day_buttons; ct.clear_widgets()
        for d,l in zip(self._days,['S','S','R','K','J','S','M']):
            b=ToggleButton(text=l,font_size='12sp',bold=True,background_color=(0,0,0,0),color=C['muted'],border_normal=C['border'],size_hint_y=None,height='42dp',state='down',group='sd')
            b.day_name=d
            def mb(bb,dd):
                def os(inst,v):
                    if v=='down': bb.color=(0.02,0.04,0.09,1); bb.background_color=C['accent']; self._sel_days.add(dd)
                    else: bb.color=C['muted']; bb.background_color=(0,0,0,0); self._sel_days.discard(dd)
                return os
            b.bind(state=mb(b,d)); ct.add_widget(b)
    def save_schedule(self):
        if not self._sel_days: return
        def do():
            r=api.post('/api/schedule',{'enabled':self.ids.sched_toggle.active,'hour':int(self.ids.sched_hour.text or '9'),'minute':int(self.ids.sched_minute.text or '0'),'days':list(self._sel_days)})
            if r and r.get('success'): Clock.schedule_once(lambda dt: (setattr(self,'status_msg','Tersimpan'),setattr(self,'status_color',C['accent'])),0)
        threading.Thread(target=do, daemon=True).start()

class ProductListScreen(Screen):
    product_count=NumericProperty(0)
    def on_enter(self): self.refresh_products()
    def refresh_products(self):
        def do():
            r=api.get('/api/products')
            if r and 'products' in r: store.set_products(r['products']); Clock.schedule_once(lambda dt: self._render(r['products']),0)
        threading.Thread(target=do, daemon=True).start()
    def _render(self, p):
        self.product_count=len(p); ct=self.ids.product_list; ct.clear_widgets()
        if not p: ct.add_widget(Label(text='Kosong',font_size='13sp',color=C['muted'],halign='center',size_hint_y=None,height='60dp')); return
        for pr in p: ct.add_widget(ProductRow(nama=pr.get('nama','-'),harga_str='Rp '+pr.get("harga","0"),desc_preview=(pr.get('deskripsi','-') or '-')[:60]))

class AccountScreen(Screen):
    def on_enter(self): self._render()
    def _render(self):
        ct=self.ids.account_list; ct.clear_widgets()
        if not store.accounts: ct.add_widget(Label(text='Kosong',font_size='13sp',color=C['muted'],halign='center',size_hint_y=None,height='60dp')); return
        for a in store.accounts: ct.add_widget(AccountRow(label=a.get('label','-'),platform=a.get('platform','all').upper(),active=a.get('active',True)))
    def show_add_dialog(self):
        popup=Popup(title='Tambah Akun',size_hint=(0.9,0.45))
        layout=BoxLayout(orientation='vertical',padding='16dp',spacing='12dp')
        inp=TextInput(hint_text='Nama Akun',foreground_color=C['text'],hint_text_color=C['muted'],font_size='14sp',padding=['14dp','10dp'],size_hint_y=None,height='48dp',background_color=C['bg_card'],multiline=False)
        def add(inst):
            if inp.text.strip(): store.add_account(inp.text.strip(),'all'); self._render(); popup.dismiss()
        layout.add_widget(inp); layout.add_widget(PrimaryButton(text='TAMBAH',on_press=add)); layout.add_widget(GhostButton(text='Batal',on_press=popup.dismiss))
        popup.add_widget(layout); popup.open()

class HistoryScreen(Screen):
    total_entries=NumericProperty(0); total_success=NumericProperty(0); total_failed=NumericProperty(0)
    def on_enter(self): self._render()
    def _render(self):
        ct=self.ids.history_list; ct.clear_widgets(); h=store.history
        self.total_entries=len(h); self.total_success=sum(1 for x in h if x.get('success')); self.total_failed=sum(1 for x in h if not x.get('success'))
        if not h: ct.add_widget(Label(text='Kosong',font_size='13sp',color=C['muted'],halign='center',size_hint_y=None,height='60dp')); return
        for e in reversed(h[-100:]): ct.add_widget(HistoryRow(time_str=e.get('time','--:--'),product=e.get('product','-')[:30],result='OK' if e.get('success') else 'FAIL',success=e.get('success',False)))
    def refresh_history(self):
        def do():
            r=api.get('/api/logs?count=200')
            if r and 'logs' in r:
                nh=[]
                for e in r['logs']:
                    if e.get('level') in ('success','error'):
                        m=e.get('message',''); pn=m
                        for k in ["'",'"']:
                            s,ee=m.find(k),m.find(k,m.find(k)+1)
                            if s>=0 and ee>s: pn=m[s+1:ee]; break
                        nh.append({'time':e.get('timestamp',''),'product':pn,'success':e.get('level')=='success'})
                store.history=nh; Clock.schedule_once(lambda dt: self._render(),0)
        threading.Thread(target=do, daemon=True).start()

# ============================================================
# MAIN APP CLASS
# ============================================================
class MPAPSApp(App):
    def build(self):
        Window.clearcolor = C['bg']
        Builder.load_string(KV)
        self.sm = ScreenManager(transition=FadeTransition(duration=0.2))
        for n, c in [('dashboard',DashboardScreen),('upload',UploadScreen),('logs',LogsScreen),('more_menu',MoreMenuScreen),('settings',SettingsScreen),('scheduler',SchedulerScreen),('product_list',ProductListScreen),('account',AccountScreen),('history',HistoryScreen)]:
            self.sm.add_widget(c(name=n))
        self.root = BoxLayout(orientation='vertical')
        self.root.add_widget(self.sm)
        self.root.add_widget(BottomNav())
        Window.bind(on_keyboard=self._kb)
        return self.root
    def _kb(self, i, k, kc, t, m):
        if kc in (27, 1001):
            c = self.sm.current
            if c in ['settings','scheduler','product_list','account','history']: self.switch_screen('more_menu'); return True
            if c in ['upload','logs','more_menu']: self.switch_screen('dashboard'); return True
        return False
    def switch_screen(self, name):
        p = self.sm.current_screen
        if hasattr(p, 'on_leave'): p.on_leave()
        self.sm.current = name
        nm = {'dashboard':'nav_dash','upload':'nav_upload','logs':'nav_logs','more_menu':'nav_more'}
        for sn, nid in nm.items():
            nav = self.root.ids.get(nid)
            if nav: nav.text_color = C['accent'] if sn == name else C['muted']
        n = self.sm.current_screen
        if hasattr(n, 'on_enter'): n.on_enter()
    def on_pause(self): return True
    def on_resume(self):
        if not ws_client.connected and api.base_url: ws_client.connect(api.base_url.replace('http','ws')+'/ws/logs')

if __name__ == '__main__':
    MPAPSApp().run()