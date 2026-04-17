# kivy-bot-android

```markdown
# Multi Platform Auto Posting System (MPAPS)

Sistem otomasi posting produk multi-platform (Facebook, Instagram, WhatsApp) yang dikontrol melalui Web Dashboard dan Aplikasi Android (APK).

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green?logo=fastapi)
![Kivy](https://img.shields.io/badge/Kivy-2.3.0-orange?logo=kivy)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📑 Daftar Isi
1. [Arsitektur Sistem](#-arsitektur-sistem)
2. [Aplikasi yang Digunakan (Wajib)](#-aplikasi-yang-digunakan-wajib)
3. [Aplikasi Pendukung (Opsional tapi Disarankan)](#-aplikasi-pendukung-opsional-tapi-disarankan)
4. [Step 1: Menyiapkan Folder Project](#-step-1-menyiapkan-folder-project)
5. [Step 2: Instalasi & Menjalankan Backend](#-step-2-instalasi--menjalankan-backend)
6. [Step 3: Membuka Web Dashboard](#-step-3-membuka-web-dashboard)
7. [Step 4: Menjalankan APK di PC (Testing)](#-step-4-menjalankan-apk-di-pc-testing)
8. [Step 5: Build APK Android (.apk)](#-step-5-build-apk-android-apk)
9. [Step 6: Cara Connect Semuanya (Jaringan)](#-step-6-cara-connect-semuanya-jaringan)
10. [Alur Penggunaan Sistem](#-alur-penggunaan-sistem)
11. [Customisasi Automation (Penting!)](#-customisasi-automation-penting)
12. [Troubleshooting](#-troubleshooting)

---

## 🏗️ Arsitektur Sistem

```text
[ HP Android (APK) ]        [ Laptop/PC (Browser) ]
         │                           │
         └───────────┬───────────────┘
                     │ REST API + WebSocket
                     ▼
           [ Backend Server (Python) ]
           (FastAPI di Port 8000)
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Facebook     Instagram     WhatsApp
```

---

## 🛠️ Aplikasi yang Digunakan (Wajib)

| Aplikasi | Versi | Fungsi | Link Download |
|----------|-------|--------|---------------|
| **Python** | 3.8+ | Bahasa pemrograman utama (Backend & APK) | [python.org/downloads](https://www.python.org/downloads/) |
| **FastAPI** | 0.100+ | Framework Backend API | Install via `pip` |
| **Uvicorn** | Latest | Server ASGI untuk menjalankan FastAPI | Install via `pip` |
| **Kivy** | 2.3.0 | Framework UI untuk membuat APK Android | Install via `pip` |
| **Buildozer** | Latest | Tool untuk mengkompilasi Python ke APK | Install via `pip` |
| **WSL 2** (Windows) | Latest | Subsystem Linux wajib untuk build APK di Windows | Install via Command Prompt |

> **⚠️ Catatan untuk Build APK:** Anda **tidak bisa** langsung build APK di Windows/Mac murni. Anda **wajib** menggunakan sistem Linux (Ubuntu/Debian). Jika pakai Windows, gunakan **WSL 2 (Windows Subsystem for Linux)**.

---

## 📦 Aplikasi Pendukung (Opsional tapi Disarankan)

| Aplikasi | Fungsi |
|----------|--------|
| **Visual Studio Code (VS Code)** | Text editor terbaik untuk menulis kode. |
| **Extension: Live Server** (di VS Code) | Untuk menjalankan Web Dashboard (`index.html`) dengan auto-refresh. |
| **Extension: Python** (di VS Code) | Untuk auto-complete dan debug Python. |
| **Google Chrome / Firefox** | Browser untuk membuka Web Dashboard dan API Docs. |
| **Postman** | Untuk testing manual Endpoint API (`/api/status`, dll). |
| **Git** | Untuk version control (opsional). |

---

## 📁 Step 1: Menyiapkan Folder Project

Buat struktur folder persis seperti ini di komputer kamu:

```bash
mpaps-project/
│
├── backend/
│   └── main.py              # (Copy kode backend dari jawaban sebelumnya)
│
├── web/
│   └── index.html           # (Copy kode web dashboard dari jawaban sebelumnya)
│
├── android/
│   └── main.py              # (Copy kode Kivy APK dari jawaban sebelumnya)
│
├── data/
│   ├── products.csv         # (Copy kode CSV dari jawaban sebelumnya)
│   ├── uploads/             # (Buat folder kosong ini)
│   └── images/              # (Buat folder kosong ini)
│
├── buildozer.spec           # (Copy kode buildozer dari jawaban sebelumnya)
│
└── README.md                # (File ini)
```

---

## 🚀 Step 2: Instalasi & Menjalankan Backend

Backend adalah *otak* dari seluruh sistem. Tanpa ini, Web dan APK tidak bisa berfungsi.

### 2.1. Buat Virtual Environment
Buka terminal (Command Prompt / PowerShell / Terminal), arahkan ke folder project:

```bash
cd mpaps-project
python -m venv venv
```

### 2.2. Aktifkan Virtual Environment
**Windows:**
```bash
venv\Scripts\activate
```
**Linux/Mac/WSL:**
```bash
source venv/bin/activate
```
*Jika berhasil, di ujung prompt kamu akan muncul tulisan `(venv)`.*

### 2.3. Install Dependencies Python
```bash
pip install fastapi uvicorn python-multipart schedule
```

### 2.4. Jalankan Backend Server
```bash
cd backend
python main.py
```

**Output yang harus muncul:**
```text
============================================================
  Multi Platform Auto Posting System
  Backend Server
  API Key: mpaps-2024-secret-key-change-me
============================================================
INFO:     Started server process [xxxxx]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

> **✅ Backend berhasil berjalan di Port 8000. JANGAN TUTUP terminal ini.**
> 
> *Bonus:* Buka browser baru, akses `http://localhost:8000/docs`. Ini adalah Swagger UI (dokumentasi API otomatis dari FastAPI) yang sangat berguna untuk testing.

---

## 🌐 Step 3: Membuka Web Dashboard

### Cara 1: Double Click (Paling Mudah)
Cukup buka file `web/index.html` langsung di browser (Chrome/Firefox/Edge).

### Cara 2: Menggunakan VS Code Live Server (Disarankan)
1. Buka folder `mpaps-project` di VS Code.
2. Klik kanan pada file `web/index.html`.
3. Pilih **"Open with Live Server"**.
4. Dashboard akan terbuka otomatis di `http://127.0.0.1:5500`.

### Cara Connect ke Backend
1. Di bagian **atas kanan** dashboard, ada kolom "Server URL".
2. Pastikan isinya: `http://localhost:8000`
3. Kolom "API Key" isi: `mpaps-2024-secret-key-change-me`
4. Klik tombol **"Hubungkan"**.
5. Jika berhasil, akan muncul notifikasi hijau "Berhasil terhubung ke server!" dan indikator WebSocket di kiri bawah berwarna hijau.

---

## 📱 Step 4: Menjalankan APK di PC (Testing)

Sebelum di-build jadi APK, sebaiknya test dulu di komputer untuk memastikan tidak ada error.

### 4.1. Install Kivy (di luar venv atau di venv baru khusus)
```bash
# Pastikan venv aktif
pip install kivy
```

### 4.2. Jalankan Aplikasi Kivy
```bash
cd android
python main.py
```
*Akan muncul window baru berisi tampilan HP Android.*

### 4.3. Test Koneksi dari Kivy App
1. Klik menu **"Lainnya"** (pojok kanan bawah).
2. Klik **"Pengaturan"**.
3. Isi Server URL: `http://localhost:8000`
4. Isi API Key: `mpaps-2024-secret-key-change-me`
5. Klik **"SIMPAN & HUBUNGKAN"**.
6. Kembali ke Dashboard, status harus berubah menjadi "Terhubung".

---

## 📲 Step 5: Build APK Android (.apk)

*Proses ini membutuhkan waktu sekitar 15-30 menit pada build pertama karena mendownload NDK dan SDK Android.*

### 5.1. Persiapan WSL (Jika Kamu Pakai Windows)
Jika kamu sudah pakai Linux native, lewati langkah ini.
1. Buka **Command Prompt (Admin)** di Windows.
2. Ketik: `wsl --install`
3. Restart komputer.
4. Setelah restart, buka aplikasi **Ubuntu** yang baru terinstall.
5. Buat username dan password baru.

### 5.2. Install Dependencies Buildozer di Linux/WSL
Buka terminal Linux/WSL, ketik perintah ini satu per satu:
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev libltdl-dev
```

### 5.3. Install Python & Buildozer di WSL
```bash
sudo apt install python3 python3-pip python3-venv
pip3 install --upgrade pip
pip3 install buildozer cython
```

### 5.4. Pindahkan Project ke WSL
Karena WSL tidak bisa langsung akses drive C:, kamu perlu copy project ke folder home WSL.
```bash
# Di dalam terminal WSL:
cd ~
mkdir mpaps-project
```
*Copy seluruh isi folder `mpaps-project` dari Windows Explorer ke folder `\\wsl$\Ubuntu\home\username\mpaps-project\`*

### 5.5. Mulai Build APK
```bash
cd ~/mpaps-project
buildozer android debug
```

*(Pada build pertama, buildozer akan otomatis mendownload Android NDK (~1GB) dan SDK (~500MB). Pastikan koneksi internet stabil).*

### 5.6. Ambil File APK
Jika build berhasil (muncul tulisan `Android packaging done!`), file APK ada di:
```bash
~/mpaps-project/bin/MPAPS-1.0.0-debug.apk
```

### 5.7. Install APK ke HP
1. Copy file `.apk` ke HP Android kamu (via kabel USB, Google Drive, atau Telegram).
2. Buka file `.apk` di HP.
3. Izinkan install dari sumber tidak dikenal (*Unknown Sources*).
4. Install dan buka aplikasi.

---

## 🌐 Step 6: Cara Connect Semuanya (Jaringan)

Web Dashboard dan APK Android **hanya bisa mengontrol bot jika terhubung ke IP yang sama dengan Backend.**

### Koneksi di 1 Komputer yang Sama (Localhost)
- Web Dashboard: `http://localhost:8000`
- APK (jalan di PC): `http://localhost:8000`

### Koneksi dari HP Android ke Komputer (WiFi)
Jika backend berjalan di PC/Laptop, dan APK berjalan di HP:

1. **Cari IP Komputer:**
   - **Windows:** Buka CMD, ketik `ipconfig`. Cari *IPv4 Address* (contoh: `192.168.1.5`).
   - **Linux/Mac:** Buka terminal, ketik `ip a` atau `ifconfig`.
2. **Pastikan 1 Jaringan WiFi:** HP dan Komputer harus terhubung ke WiFi yang sama.
3. **Buka Firewall Port 8000 (Windows):**
   - Buka *Windows Defender Firewall with Advanced Security*.
   - Klik *Inbound Rules* -> *New Rule* -> *Port* -> *TCP*, Specific local port: `8000`.
   - Pilih *Allow the connection* -> Finish.
4. **Isi di APK / Web Dashboard:**
   - Ganti `http://localhost:8000` menjadi `http://192.168.1.5:8000` (sesuaikan IP kamu).

---

## 🔄 Alur Penggunaan Sistem

1. **Nyalakan Backend:** Jalankan `python main.py` di terminal. Biarkan menyala.
2. **Buka Web / APK:** Hubungkan ke IP server.
3. **Upload Data:** Masuk ke menu *Upload CSV*, pilih file `products.csv`.
4. **Cek Preview:** Pastikan data produk muncul dengan benar.
5. **Atur Pengaturan (Opsional):** Sesuaikan delay, retry, dan platform yang aktif di menu *Settings*.
6. **Mulai Bot:** Klik tombol **"MULAI BOT"**.
7. **Monitor:** Pantau prosesnya di menu **Logs**. Log akan muncul real-time via WebSocket.
8. **Stop:** Klik **"HENTIKAN"** kapan saja untuk menghentikan proses.

---

## 🔧 Customisasi Automation (Penting!)

Saat ini, sistem ini berjalan dalam **mode SIMULASI (Stub)**. Artinya, bot tidak benar-benar memposting ke Facebook/Instagram/WhatsApp (hanya menunggu beberapa detik dan menghasilkan log palsu).

Untuk membuatnya **benar-benar memposting**, kamu harus mengedit class `PlatformPoster` di dalam file `backend/main.py`.

### Contoh Integrasi Nyata:
1. **Facebook Page:** Gunakan [Facebook Graph API](https://developers.facebook.com/docs/graph-api/). Ganti fungsi `post_facebook_page()` dengan request HTTP ke endpoint Graph API menggunakan token akses halaman.
2. **Instagram:** Gunakan Instagram Graph API (memerlukan akun Instagram yang dihubungkan ke Facebook Page sebagai Business Account).
3. **WhatsApp:**
   - *Gratis/Tanpa API Resmi:* Gunakan library `pywhatkit` atau `whatsapp-web.js` (Node.js).
   - *Resmi/Berbayar:* Gunakan [WhatsApp Business Cloud API](https://business.whatsapp.com/developers/developer-hub).
4. **Facebook Marketplace:** Tidak ada API resmi. Gunakan library browser automation seperti `Playwright` atau `Selenium` untuk mengontrol browser secara otomatis.

---

## 🐛 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: No module named 'fastapi'` | Kamu lupa mengaktifkan virtual environment. Ketik `venv\Scripts\activate` (Windows) lalu install ulang `pip install fastapi uvicorn...` |
| Web Dashboard tidak bisa connect | Pastikan backend sudah berjalan. Cek URL di topbar (harus `http://...` bukan `https://...`). Cek API Key. |
| APK di HP tidak bisa connect ke PC | Pastikan HP dan PC 1 WiFi. Cek IP PC (`ipconfig`). Buka Port 8000 di Firewall Windows. |
| Buildozer gagal (error NDK/SDK) | Hapus folder `.buildozer` di home directory WSL, lalu jalankan ulang `buildozer android debug --download-ndk --download-sdk`. |
| Buildozer gagal (error Cython) | Jalankan `pip3 install --upgrade cython` di WSL, lalu coba build lagi. |
| Port 8000 sudah dipakai | Kill proses yang pakai port 8000. Windows: `netstat -ano | findstr :8000`, lalu `taskkill /PID <nomor_pid> /F`. Linux: `lsof -i :8000`, lalu `kill -9 <nomor_pid>`. |
| WebSocket di APK selalu "Terputus (Polling)" | Normal jika library `websocket-client` gagal di-compile saat build APK. Sistem akan otomatis fallback ke polling (meminta data setiap 3 detik). Fitur tetap berjalan normal. |

---

## 📄 Lisensi
Proyek ini dibuat untuk keperluan edukasi dan otomasi personal. Gunakan dengan bertanggung jawab dan patuhi Terms of Service platform terkait.
```
