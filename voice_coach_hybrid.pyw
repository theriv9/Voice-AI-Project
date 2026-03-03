import os
import time
import sys
import pyperclip
import ollama
from pynput import keyboard
from google import genai
from dotenv import load_dotenv

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QCursor, QFont

# Load environment variables
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"
LOCAL_MODEL = "llama3.2:1b"

class Communicate(QObject):
    show_menu_signal = pyqtSignal()
    option_selected = pyqtSignal(str)

class PopupMenu(QWidget):
    def __init__(self, comm):
        super().__init__()
        self.comm = comm
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: #1a1a1a;
                border: 2px solid #5a5a5a;
                border-radius: 12px;
            }
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                padding: 12px 20px;
                text-align: left;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #333;
            }
            QLabel#header {
                color: #888;
                font-size: 10px;
                font-weight: bold;
                padding-left: 12px;
                padding-top: 8px;
                text-transform: uppercase;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.setSpacing(2)

        # Gemini Section
        header_gemini = QLabel("Cloud (Gemini)")
        header_gemini.setObjectName("header")
        container_layout.addWidget(header_gemini)
        
        btn_gem_pro = QPushButton("✨ Professional Refine")
        btn_gem_pro.clicked.connect(lambda: self.handle_click("gemini_professional"))
        container_layout.addWidget(btn_gem_pro)

        # Local Section
        header_local = QLabel("Local (Llama)")
        header_local.setObjectName("header")
        container_layout.addWidget(header_local)
        
        btn_loc_friendly = QPushButton("😊 Friendly Rewrite")
        btn_loc_friendly.clicked.connect(lambda: self.handle_click("local_friendly"))
        container_layout.addWidget(btn_loc_friendly)

        layout.addWidget(self.container)
        self.setLayout(layout)

    def handle_click(self, mode):
        self.hide()
        QApplication.processEvents()
        self.comm.option_selected.emit(mode)

    def show_at_cursor(self):
        pos = QCursor.pos()
        self.move(pos.x() - 20, pos.y() - 10)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def focusOutEvent(self, event):
        QTimer.singleShot(150, self.check_focus_and_close)
        super().focusOutEvent(event)

    def check_focus_and_close(self):
        if self.isVisible() and not self.isActiveWindow():
            self.hide()

class VoiceCoachHybrid:
    def __init__(self):
        self.gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
        self.controller = keyboard.Controller()
        self.app = QApplication(sys.argv)
        
        self.comm = Communicate()
        self.comm.show_menu_signal.connect(self.trigger_ui)
        self.comm.option_selected.connect(self.process_selection)

        self.menu = PopupMenu(self.comm)
        self.captured_text = ""

    def get_local_messages(self, user_text):
        # Professional Editor persona with strict "Sentiment Preservation" rules.
        system_content = (
            "You are a professional editor. Your task is to rewrite the input to be warm and friendly. "
            "CRITICAL: Keep the original sentiment, context, and all specific details exactly the same. "
            "Simply improve the flow and tone without cutting out any of the user's original points. "
            "Output ONLY the rewritten text. Do NOT include any 'Here is your text' or introductory remarks. "
            "If the input is a question, rewrite the question itself, do not answer it."
        )
        return [
            {'role': 'system', 'content': system_content},
            {'role': 'user', 'content': "What time can you meet for coffee?"},
            {'role': 'assistant', 'content': "Hey! Do you happen to know what time works best for you to grab a coffee together?"},
            {'role': 'user', 'content': user_text}
        ]

    def robust_copy(self):
        pyperclip.copy("")
        time.sleep(0.05)
        for attempt in range(3):
            self.controller.release(keyboard.Key.ctrl_l)
            self.controller.release(keyboard.Key.alt_l)
            self.controller.release(keyboard.Key.f11)
            time.sleep(0.05)
            with self.controller.pressed(keyboard.Key.ctrl_l):
                self.controller.tap('c')
            time.sleep(0.3)
            text = pyperclip.paste().strip()
            if text and len(text) > 1 and text.lower() not in ['c', 'v', 'a']:
                return text
            time.sleep(0.2)
        return ""

    def process_selection(self, mode):
        print(f"[DEBUG] Selection: {mode}", flush=True)
        time.sleep(0.2) # Focus recovery
        
        if not self.captured_text: return

        try:
            if mode == "gemini_professional":
                print(f"[DEBUG] Calling Gemini ({GEMINI_MODEL})...", flush=True)
                instr = "Take this raw transcription, fix grammar, and make it professional yet friendly. Return ONLY refined text."
                response = self.gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=self.captured_text,
                    config={'system_instruction': instr}
                )
                refined_text = response.text.strip()
            else:
                print(f"[DEBUG] Calling Local ({LOCAL_MODEL})...", flush=True)
                response = ollama.chat(
                    model=LOCAL_MODEL, 
                    messages=self.get_local_messages(self.captured_text),
                    options={'temperature': 0}
                )
                refined_text = response['message']['content'].strip()

            # Clean up and Paste
            if refined_text.startswith('"') and refined_text.endswith('"'):
                refined_text = refined_text[1:-1]
            
            pyperclip.copy(refined_text)
            time.sleep(0.15)
            
            with self.controller.pressed(keyboard.Key.ctrl_l):
                self.controller.tap('v')
            print("[DEBUG] SUCCESS!", flush=True)

        except Exception as e:
            print(f"[DEBUG] ERROR: {e}", flush=True)

    def on_hotkey(self):
        time.sleep(0.1)
        self.captured_text = self.robust_copy()
        if self.captured_text:
            self.comm.show_menu_signal.emit()

    def trigger_ui(self):
        self.menu.show_at_cursor()

    def run(self):
        listener = keyboard.GlobalHotKeys({'<ctrl>+<alt>+<f11>': self.on_hotkey})
        listener.start()
        print(f"Hybrid Voice Coach ACTIVE. Gemini: {GEMINI_MODEL}, Local: {LOCAL_MODEL}", flush=True)
        self.app.exec()

if __name__ == "__main__":
    coach = VoiceCoachHybrid()
    coach.run()
