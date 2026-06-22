import os
import sys
import time
import traceback
import certifi
import whisper
from openai import OpenAI
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QTabWidget, QLabel, QPushButton,
                               QRadioButton, QButtonGroup, QTextEdit, QLineEdit,
                               QFileDialog, QMessageBox, QGroupBox, QFormLayout,
                               QProgressBar, QCheckBox)
from PySide6.QtCore import QThread, Signal, Qt, QTimer

# =======================================================
# 🔧 PATCH KHUSUS MAC .APP (PYINSTALLER WINDOWED MODE)
# =======================================================
# 1. Cegah error stat: NoneType karena aplikasi GUI ga punya Terminal
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# 2. Tambahin Homebrew PATH biar Whisper dapet FFmpeg-nya
os.environ["PATH"] += os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin"

# 3. Bantu httpx/OpenAI nemuin sertifikat SSL
os.environ["SSL_CERT_FILE"] = certifi.where()
# =======================================================


# =======================================================
# 🧠 1. CLASSES (TRANSCRIBER & AI AGENT)
# =======================================================
class AudioTranscriber:
    def __init__(self, mode, config):
        self.mode = mode
        self.config = config
        if self.mode == "Cloud":
            self.cloud_client = OpenAI(
                api_key=self.config["cloud_stt_key"], 
                base_url=self.config["cloud_stt_url"]
            )

    def transcribe(self, audio_path):
        if self.mode == "Local":
            model_name = self.config["local_stt_model"]
            local_whisper_client = whisper.load_model(model_name)
            result = local_whisper_client.transcribe(audio_path, language="id")
            return result["text"]
        elif self.mode == "Cloud":
            with open(audio_path, "rb") as audio_file:
                transcription = self.cloud_client.audio.transcriptions.create(
                    model=self.config["cloud_stt_model"],
                    file=audio_file,
                    language="id"
                )
            return transcription.text

class AIAgent:
    def __init__(self, mode, config):
        self.mode = mode
        self.config = config
        if self.mode == "Local":
            self.client = OpenAI(
                api_key=self.config["local_llm_key"], 
                base_url=self.config["local_llm_url"]
            )
            self.model_name = self.config["local_llm_model"]
        elif self.mode == "Cloud":
            self.client = OpenAI(
                api_key=self.config["cloud_llm_key"], 
                base_url=self.config["cloud_llm_url"]
            )
            self.model_name = self.config["cloud_llm_model"]

    def generate_summary(self, text, system_prompt, user_prompt):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f"{user_prompt}\n\n{text}"}
            ]
        )
        return response.choices[0].message.content.strip()

# =======================================================
# 🧵 2. WORKER THREADS (Biar GUI gak nge-freeze)
# =======================================================
class STTWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, transcriber, audio_path):
        super().__init__()
        self.transcriber = transcriber
        self.audio_path = audio_path

    def run(self):
        try:
            result = self.transcriber.transcribe(self.audio_path)
            self.finished.emit(result)
        except Exception as e:
            # Pake traceback biar errornya detail dari baris ke berapa
            self.error.emit(traceback.format_exc())

class LLMWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, agent, text, sys_prompt, usr_prompt):
        super().__init__()
        self.agent = agent
        self.text = text
        self.sys_prompt = sys_prompt
        self.usr_prompt = usr_prompt

    def run(self):
        try:
            result = self.agent.generate_summary(self.text, self.sys_prompt, self.usr_prompt)
            self.finished.emit(result)
        except Exception as e:
            # Pake traceback biar errornya detail
            self.error.emit(traceback.format_exc())

# =======================================================
# 🎨 3. GUI UTAMA PYSIDE6
# =======================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎙️ Audio AI Agent")
        self.resize(1000, 750)

        self.config = {
            "local_stt_model": "base",
            "local_llm_model": "llama3",
            "local_llm_url": "http://localhost:11434/v1",
            "local_llm_key": "ollama",
            "cloud_stt_model": "qwen3-omni-30b-a3b-captioner",
            "cloud_stt_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "cloud_stt_key": "sk-ws-H.IIYEMM.xnhX.MEQCIBqfPDq3OlEfrvgtSjbEBHW9YaLmP9QH_LKXkrWudN-kAiBq3wxhFNVFraIazchQ19n9CthJ6Si3eATGcHrxTvJdBw",
            "cloud_llm_model": "qwen3.7-plus",
            "cloud_llm_url": "https://ws-er74w5iv56y4n38m.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
            "cloud_llm_key": "sk-ws-H.IIYEMM.xnhX.MEQCIBqfPDq3OlEfrvgtSjbEBHW9YaLmP9QH_LKXkrWudN-kAiBq3wxhFNVFraIazchQ19n9CthJ6Si3eATGcHrxTvJdBw"
        }

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.setup_transkripsi_tab()
        self.setup_notulen_tab()
        self.setup_pengaturan_tab()

    # ---------------------------------------------------
    # TAB 1: TRANSKRIPSI
    # ---------------------------------------------------
    def setup_transkripsi_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode STT:"))
        self.stt_bg = QButtonGroup(self)
        self.rb_stt_local = QRadioButton("Local")
        self.rb_stt_cloud = QRadioButton("Cloud")
        self.rb_stt_cloud.setChecked(True)
        self.stt_bg.addButton(self.rb_stt_local)
        self.stt_bg.addButton(self.rb_stt_cloud)
        mode_layout.addWidget(self.rb_stt_local)
        mode_layout.addWidget(self.rb_stt_cloud)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        self.lbl_file_audio = QLabel("Belum ada file audio yang dipilih.")
        layout.addWidget(self.lbl_file_audio)

        self.btn_pilih_audio = QPushButton("📂 Pilih File Audio")
        self.btn_pilih_audio.clicked.connect(self.pilih_file_audio)
        layout.addWidget(self.btn_pilih_audio)

        self.btn_proses_stt = QPushButton("🚀 Mulai Transkripsi")
        self.btn_proses_stt.setStyleSheet("background-color: #2E8B57; color: white; font-weight: bold; padding: 10px;")
        self.btn_proses_stt.clicked.connect(self.mulai_transkripsi)
        layout.addWidget(self.btn_proses_stt)

        stt_prog_layout = QHBoxLayout()
        self.stt_progress = QProgressBar()
        self.stt_progress.setValue(0)
        self.stt_progress.setVisible(False)
        stt_prog_layout.addWidget(self.stt_progress)

        self.lbl_waktu_stt = QLabel("Waktu: 00:00")
        self.lbl_waktu_stt.setVisible(False)
        self.lbl_waktu_stt.setStyleSheet("font-weight: bold;")
        stt_prog_layout.addWidget(self.lbl_waktu_stt)
        
        layout.addLayout(stt_prog_layout)

        self.stt_timer = QTimer()
        self.stt_timer.timeout.connect(self.update_stt_progress)
        self.stt_progress_val = 0
        self.stt_start_time = 0

        self.txt_hasil_stt = QTextEdit()
        self.txt_hasil_stt.setPlaceholderText("Hasil transkripsi akan muncul di sini...")
        layout.addWidget(self.txt_hasil_stt)

        self.btn_simpan_stt = QPushButton("💾 Simpan Hasil Transkrip ke File (.txt)")
        self.btn_simpan_stt.setStyleSheet("font-weight: bold; padding: 8px;")
        self.btn_simpan_stt.clicked.connect(self.simpan_transkrip)
        layout.addWidget(self.btn_simpan_stt)

        self.tabs.addTab(tab, "🎙️ Transkripsi")
        self.audio_path = None

    def pilih_file_audio(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Pilih File Audio", "", "Audio Files (*.mp3 *.wav *.m4a *.ogg)")
        if filepath:
            self.audio_path = filepath
            self.lbl_file_audio.setText(f"File: {os.path.basename(filepath)}")

    def update_stt_progress(self):
        if self.stt_progress_val < 95:
            self.stt_progress_val += 1
            self.stt_progress.setValue(self.stt_progress_val)
        
        elapsed_seconds = int(time.time() - self.stt_start_time)
        days, rem = divmod(elapsed_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)
        
        if days > 0:
            time_str = f"{days} Hari, {hours:02d}:{mins:02d}:{secs:02d}"
        elif hours > 0:
            time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
        else:
            time_str = f"{mins:02d}:{secs:02d}"
            
        self.lbl_waktu_stt.setText(f"Waktu: {time_str}")

    def mulai_transkripsi(self):
        if not self.audio_path:
            QMessageBox.warning(self, "Peringatan", "Pilih file audio dulu, bro!")
            return

        self.btn_proses_stt.setEnabled(False)
        self.btn_proses_stt.setText("⏳ Sedang Memproses...")
        self.txt_hasil_stt.clear()
        
        self.stt_progress.setVisible(True)
        self.lbl_waktu_stt.setVisible(True)
        self.stt_progress_val = 0
        self.stt_progress.setValue(0)
        self.stt_start_time = time.time()
        self.lbl_waktu_stt.setText("Waktu: 00:00")
        
        self.stt_timer.start(500) 

        mode = "Local" if self.rb_stt_local.isChecked() else "Cloud"
        transcriber = AudioTranscriber(mode, self.config)
        
        self.stt_worker = STTWorker(transcriber, self.audio_path)
        self.stt_worker.finished.connect(self.stt_selesai)
        self.stt_worker.error.connect(self.stt_error)
        self.stt_worker.start()

    def stt_selesai(self, hasil):
        self.stt_timer.stop()
        self.stt_progress.setValue(100)
        self.txt_hasil_stt.setText(hasil)
        self.reset_stt_button()

    def stt_error(self, err):
        self.stt_timer.stop()
        self.stt_progress.setValue(0)
        self.stt_progress.setVisible(False)
        self.txt_hasil_stt.setText(f"❌ Error Detail:\n{err}")
        self.reset_stt_button()

    def reset_stt_button(self):
        self.btn_proses_stt.setEnabled(True)
        self.btn_proses_stt.setText("🚀 Mulai Transkripsi")

    def simpan_transkrip(self):
        teks = self.txt_hasil_stt.toPlainText()
        if not teks.strip(): 
            QMessageBox.warning(self, "Peringatan", "Belum ada hasil yang bisa disimpan!")
            return
        filepath, _ = QFileDialog.getSaveFileName(self, "Simpan Transkrip", "hasil_transkrip.txt", "Text Files (*.txt)")
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(teks)
            QMessageBox.information(self, "Sukses", "File berhasil disimpan!")

    # ---------------------------------------------------
    # TAB 2: NOTULEN LLM
    # ---------------------------------------------------
    def setup_notulen_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode AI:"))
        self.llm_bg = QButtonGroup(self)
        self.rb_llm_local = QRadioButton("Local")
        self.rb_llm_cloud = QRadioButton("Cloud")
        self.rb_llm_cloud.setChecked(True)
        self.llm_bg.addButton(self.rb_llm_local)
        self.llm_bg.addButton(self.rb_llm_cloud)
        mode_layout.addWidget(self.rb_llm_local)
        mode_layout.addWidget(self.rb_llm_cloud)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        prompt_group = QGroupBox("Pengaturan Prompt")
        prompt_layout = QHBoxLayout(prompt_group)
        
        sys_layout = QVBoxLayout()
        sys_layout.addWidget(QLabel("System Prompt:"))
        self.txt_system = QTextEdit()
        self.txt_system.setMaximumHeight(80)
        self.txt_system.setText("Kamu adalah asisten AI cerdas yang bertugas sebagai notulen rapat. Buat ringkasan yang profesional dan rapi berisi Poin Penting dan Action Items.")
        sys_layout.addWidget(self.txt_system)
        
        usr_layout = QVBoxLayout()
        usr_layout.addWidget(QLabel("User Prompt:"))
        self.txt_user = QTextEdit()
        self.txt_user.setMaximumHeight(80)
        self.txt_user.setText("Tolong buatkan notulen rapat dari transkrip berikut:")
        usr_layout.addWidget(self.txt_user)

        prompt_layout.addLayout(sys_layout)
        prompt_layout.addLayout(usr_layout)
        layout.addWidget(prompt_group)

        upload_layout = QHBoxLayout()
        upload_layout.addWidget(QLabel("Masukkan Teks Transkrip (Atau Upload File):"))
        upload_layout.addStretch()
        
        self.btn_upload_txt = QPushButton("📂 Upload File .txt")
        self.btn_upload_txt.clicked.connect(self.upload_file_txt)
        upload_layout.addWidget(self.btn_upload_txt)
        layout.addLayout(upload_layout)

        self.txt_input_llm = QTextEdit()
        self.txt_input_llm.setMaximumHeight(100)
        layout.addWidget(self.txt_input_llm)

        self.btn_proses_llm = QPushButton("✨ Buat Notulen Sekarang")
        self.btn_proses_llm.setStyleSheet("background-color: #6A0DAD; color: white; font-weight: bold; padding: 10px;")
        self.btn_proses_llm.clicked.connect(self.mulai_llm)
        layout.addWidget(self.btn_proses_llm)

        llm_prog_layout = QHBoxLayout()
        self.llm_progress = QProgressBar()
        self.llm_progress.setValue(0)
        self.llm_progress.setVisible(False)
        llm_prog_layout.addWidget(self.llm_progress)
        
        self.lbl_waktu_llm = QLabel("Waktu: 00:00")
        self.lbl_waktu_llm.setVisible(False)
        self.lbl_waktu_llm.setStyleSheet("font-weight: bold;")
        llm_prog_layout.addWidget(self.lbl_waktu_llm)

        layout.addLayout(llm_prog_layout)

        self.llm_timer = QTimer()
        self.llm_timer.timeout.connect(self.update_llm_progress)
        self.llm_progress_val = 0
        self.llm_start_time = 0

        self.txt_hasil_llm = QTextEdit()
        self.txt_hasil_llm.setPlaceholderText("Hasil Notulen akan muncul di sini...")
        layout.addWidget(self.txt_hasil_llm)

        self.btn_simpan_llm = QPushButton("💾 Simpan Notulen (.md)")
        self.btn_simpan_llm.clicked.connect(self.simpan_notulen)
        layout.addWidget(self.btn_simpan_llm)

        self.tabs.addTab(tab, "📝 Notulen")

    def upload_file_txt(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Pilih File Transkrip", "", "Text Files (*.txt)")
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    teks = f.read()
                self.txt_input_llm.setText(teks)
                QMessageBox.information(self, "Sukses", f"Berhasil membaca file: {os.path.basename(filepath)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal membaca file: {str(e)}")

    def update_llm_progress(self):
        if self.llm_progress_val < 95:
            self.llm_progress_val += 1
            self.llm_progress.setValue(self.llm_progress_val)
        
        elapsed_seconds = int(time.time() - self.llm_start_time)
        days, rem = divmod(elapsed_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)
        
        if days > 0:
            time_str = f"{days} Hari, {hours:02d}:{mins:02d}:{secs:02d}"
        elif hours > 0:
            time_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
        else:
            time_str = f"{mins:02d}:{secs:02d}"
            
        self.lbl_waktu_llm.setText(f"Waktu: {time_str}")

    def mulai_llm(self):
        teks = self.txt_input_llm.toPlainText()
        if not teks.strip():
            QMessageBox.warning(self, "Peringatan", "Isi teks transkripnya dulu bro!")
            return

        self.btn_proses_llm.setEnabled(False)
        self.btn_proses_llm.setText("⏳ AI Sedang Berpikir...")
        self.txt_hasil_llm.clear()

        self.llm_progress.setVisible(True)
        self.lbl_waktu_llm.setVisible(True)
        self.llm_progress_val = 0
        self.llm_progress.setValue(0)
        self.llm_start_time = time.time()
        self.lbl_waktu_llm.setText("Waktu: 00:00")

        self.llm_timer.start(300)

        mode = "Local" if self.rb_llm_local.isChecked() else "Cloud"
        sys_prompt = self.txt_system.toPlainText()
        usr_prompt = self.txt_user.toPlainText()
        
        agent = AIAgent(mode, self.config)
        self.llm_worker = LLMWorker(agent, teks, sys_prompt, usr_prompt)
        self.llm_worker.finished.connect(self.llm_selesai)
        self.llm_worker.error.connect(self.llm_error)
        self.llm_worker.start()

    def llm_selesai(self, hasil):
        self.llm_timer.stop()
        self.llm_progress.setValue(100)
        self.txt_hasil_llm.setText(hasil)
        self.reset_llm_button()

    def llm_error(self, err):
        self.llm_timer.stop()
        self.llm_progress.setValue(0)
        self.llm_progress.setVisible(False)
        self.txt_hasil_llm.setText(f"❌ Error Detail:\n{err}")
        self.reset_llm_button()

    def reset_llm_button(self):
        self.btn_proses_llm.setEnabled(True)
        self.btn_proses_llm.setText("✨ Buat Notulen Sekarang")

    def simpan_notulen(self):
        teks = self.txt_hasil_llm.toPlainText()
        if not teks.strip(): return
        filepath, _ = QFileDialog.getSaveFileName(self, "Simpan Notulen", "Notulen_Rapat.md", "Markdown Files (*.md);;All Files (*)")
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(teks)
            QMessageBox.information(self, "Sukses", "Notulen berhasil disimpan!")

    # ---------------------------------------------------
    # TAB 3: PENGATURAN 
    # ---------------------------------------------------
    def setup_pengaturan_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.entries = {}

        kategori_tabs = QTabWidget()

        # 1. KATEGORI: LOCAL AI
        tab_local = QWidget()
        layout_local = QVBoxLayout(tab_local)
        subtab_local = QTabWidget()

        # Local -> STT
        tab_local_stt = QWidget()
        form_local_stt = QFormLayout(tab_local_stt)
        self.buat_baris_setting(form_local_stt, "local_stt_model", "Model Audio AI")
        subtab_local.addTab(tab_local_stt, "🎙️ Audio-to-Text")

        # Local -> LLM
        tab_local_llm = QWidget()
        form_local_llm = QFormLayout(tab_local_llm)
        self.buat_baris_setting(form_local_llm, "local_llm_model", "Model AI")
        self.buat_baris_setting(form_local_llm, "local_llm_url", "API URL")
        self.buat_baris_setting(form_local_llm, "local_llm_key", "API Key", is_password=True)
        subtab_local.addTab(tab_local_llm, "📝 LLM")

        layout_local.addWidget(subtab_local)
        kategori_tabs.addTab(tab_local, "💻 Local AI")

        # 2. KATEGORI: CLOUD AI
        tab_cloud = QWidget()
        layout_cloud = QVBoxLayout(tab_cloud)
        subtab_cloud = QTabWidget()

        # Cloud -> STT
        tab_cloud_stt = QWidget()
        form_cloud_stt = QFormLayout(tab_cloud_stt)
        self.buat_baris_setting(form_cloud_stt, "cloud_stt_model", "Model Audio AI")
        self.buat_baris_setting(form_cloud_stt, "cloud_stt_url", "API URL")
        self.buat_baris_setting(form_cloud_stt, "cloud_stt_key", "API Key", is_password=True)
        subtab_cloud.addTab(tab_cloud_stt, "🎙️ Audio-to-Text")

        # Cloud -> LLM
        tab_cloud_llm = QWidget()
        form_cloud_llm = QFormLayout(tab_cloud_llm)
        self.buat_baris_setting(form_cloud_llm, "cloud_llm_model", "Model AI")
        self.buat_baris_setting(form_cloud_llm, "cloud_llm_url", "API URL")
        self.buat_baris_setting(form_cloud_llm, "cloud_llm_key", "API Key", is_password=True)
        subtab_cloud.addTab(tab_cloud_llm, "📝 LLM")

        layout_cloud.addWidget(subtab_cloud)
        kategori_tabs.addTab(tab_cloud, "☁️ Cloud AI")

        layout.addWidget(kategori_tabs)
        layout.addStretch()

        btn_simpan_cfg = QPushButton("💾 Simpan Pengaturan")
        btn_simpan_cfg.setStyleSheet("background-color: #4682B4; color: white; padding: 10px; font-weight: bold;")
        btn_simpan_cfg.clicked.connect(self.simpan_pengaturan)
        layout.addWidget(btn_simpan_cfg)

        self.tabs.addTab(tab, "⚙️ Pengaturan")

    def buat_baris_setting(self, layout, key, label_text, is_password=False):
        entry = QLineEdit(self.config[key])
        self.entries[key] = entry

        if is_password:
            entry.setEchoMode(QLineEdit.EchoMode.Password)
            cb_tampilkan = QCheckBox("Tampilkan")
            cb_tampilkan.stateChanged.connect(lambda state, e=entry: self.toggle_password(state, e))

            row_layout = QHBoxLayout()
            row_layout.addWidget(entry)
            row_layout.addWidget(cb_tampilkan)
            layout.addRow(label_text + ":", row_layout)
        else:
            layout.addRow(label_text + ":", entry)

    def toggle_password(self, state, entry):
        if state == Qt.CheckState.Checked.value:
            entry.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            entry.setEchoMode(QLineEdit.EchoMode.Password)

    def simpan_pengaturan(self):
        for key, entry in self.entries.items():
            self.config[key] = entry.text()
        QMessageBox.information(self, "Sukses", "Pengaturan berhasil diperbarui di memori!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 

    window = MainWindow()
    window.show()
    sys.exit(app.exec())