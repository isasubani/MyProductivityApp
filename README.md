# 👨🏻‍💻 My Productivity Tools

Aplikasi desktop berbasis **GUI (PySide6)** yang memfasilitasi transkripsi audio ke teks dan pembuatan notulen rapat pintar secara hybrid menggunakan AI (Lokal dan Cloud).

Aplikasi ini mendukung alur kerja otomatisasi rapat (meeting automation), mulai dari rekaman suara hingga menjadi rangkuman/notulen rapi yang siap dibagikan.

---

## ✨ Fitur Utama

1. **🎙️ Transkripsi Audio (Hybrid STT)**
   - **Lokal**: Menggunakan model **OpenAI Whisper** secara lokal langsung di komputer Anda.
   - **Cloud**: Menggunakan model **Qwen STT / ASR** melalui API Alibaba Cloud (DashScope/MaaS) untuk pemrosesan super cepat.
   - Mendukung format file audio: `.mp3`, `.wav`, `.m4a`, `.ogg`.
   - Progress bar dinamis disertai estimasi durasi proses.

2. **📝 AI Notulen Rapat (Hybrid LLM)**
   - Meringkas transkrip rapat secara profesional menjadi ringkasan umum, poin penting, dan *Action Items*.
   - **Lokal**: Terintegrasi dengan **Ollama** (default: `llama3`).
   - **Cloud**: Terintegrasi dengan **Qwen LLM** (default: `qwen3.7-plus`).
   - Kustomisasi System Prompt & User Prompt langsung dari aplikasi.

3. **⚙️ Manajemen Pengaturan yang Mudah**
   - Pengaturan API Key, URL, dan model untuk Lokal & Cloud tersimpan dalam memori.
   - input password/key terlindungi dengan fitur tampil/sembunyikan (toggle visibility).

4. **💾 Ekspor Hasil Praktis**
   - Simpan hasil transkripsi sebagai file teks (`.txt`).
   - Simpan hasil notulen rapat terformat dalam format Markdown (`.md`).

---

## 🛠️ Persyaratan Sistem

- Python 3.9 atau versi yang lebih baru.
- Virtual Environment (venv) sangat direkomendasikan.
- FFmpeg (dibutuhkan oleh library `whisper` untuk pemrosesan audio lokal).
- Akun Alibaba Cloud/MaaS (jika menggunakan fitur Cloud).
- Ollama terinstall & berjalan di lokal (jika menggunakan fitur Lokal LLM).

---

## 🚀 Cara Memulai

### 1. Kloning & Persiapan Repositori
```bash
git clone <repository_url>
cd MyProductivityApp
```

### 2. Konfigurasi Environment Variables
Salin file template `.env.example` menjadi `.env` lalu lengkapi API Key Anda:
```bash
cp .env.example .env
```
Isi variabel di dalam `.env`:
```env
LOCAL_STT_MODEL=base
LOCAL_LLM_MODEL=llama3
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_KEY=ollama

CLOUD_STT_MODEL=qwen3-omni-30b-a3b-captioner
CLOUD_STT_URL=https://ws-er74w5iv56y4n38m.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
CLOUD_STT_KEY=masukkan_api_key_alibaba_stt_disini

CLOUD_LLM_MODEL=qwen3.7-plus
CLOUD_LLM_URL=https://ws-er74w5iv56y4n38m.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
CLOUD_LLM_KEY=masukkan_api_key_alibaba_llm_disini
```

### 3. Instalasi Dependencies
Aktifkan virtual environment Anda dan install semua library yang dibutuhkan:
```bash
# Untuk macOS / Linux
source venv/bin/activate

# Untuk Windows
venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 4. Jalankan Aplikasi
Jalankan aplikasi utama dengan perintah berikut:
```bash
python app.py
```

---

## 📓 Eksperimen & Prototyping (Jupyter Notebook)

Jika Anda ingin melakukan uji coba alur pemrosesan data secara manual lewat kode/notebook, Anda bisa menggunakan file **`TranskripKita.ipynb`**. Notebook ini memiliki alur kerja yang sama dengan aplikasi GUI tetapi disajikan dalam bentuk notebook interaktif untuk ekstraksi JSON notulen rapat.

---

## 📦 Build Menjadi Aplikasi Standalone (.app / .exe)

Untuk memaketkan kode Python ini menjadi aplikasi executable mandiri menggunakan **PyInstaller**, gunakan perintah berikut:

```bash
pyinstaller --windowed --name "MyProductivityTools" --icon="icon.ico" app.py
```

Hasil build akan berada di direktori `dist/MyProductivityTools.app` (untuk macOS) atau `dist/MyProductivityTools.exe` (untuk Windows).
