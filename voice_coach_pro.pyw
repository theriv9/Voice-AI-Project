import os
import time
import sys
import pyperclip
from pynput import keyboard
from google import genai
from dotenv import load_dotenv

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QObject
from PyQt6.QtGui import QCursor, QFont

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-2.5-flash"

class Communicate(QObject):
    # Signals for thread-safe communication
    show_menu_signal = pyqtSignal()
    option_selected = pyqtSignal(str)

class PopupMenu(QWidget):
    def __init__(self, comm):
        super().__init__()
        self.comm = comm
        self.initUI()

    def initUI(self):
        # Frameless, Stay on Top, No Taskbar icon
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        options = [
            ("✨ Refine (Professional)", "professional"),
            ("📝 Summarize", "summarize"),
            ("✂️ Shorten", "shorten"),
            ("😊 Friendly Tone", "friendly")
        ]

        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: #2c2c2c;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                text-align: left;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(2)

        for text, mode in options:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, m=mode: self.handle_click(m))
            container_layout.addWidget(btn)

        layout.addWidget(self.container)
        self.setLayout(layout)

    def handle_click(self, mode):
        # Emit signal and hide immediately
        self.comm.option_selected.emit(mode)
        self.hide()

    def show_at_cursor(self):
        pos = QCursor.pos()
        # Ensure it fits on screen (simple offset)
        self.move(pos.x() - 20, pos.y() - 10)
        self.show()
        self.raise_()
        self.activateWindow()

class VoiceCoachPro:
    def __init__(self):
        self.client = genai.Client(api_key=API_KEY)
        self.controller = keyboard.Controller()
        self.app = QApplication(sys.argv)
        
        # Communication object to safely bridge pynput and Qt
        self.comm = Communicate()
        self.comm.show_menu_signal.connect(self.trigger_ui)
        self.comm.option_selected.connect(self.process_selection)

        self.menu = PopupMenu(self.comm)
        self.captured_text = ""

    def get_prompt(self, mode):
        base_instr = "You are a professional voice and grammar coach. "
        if mode == "professional":
            return base_instr + "Take this raw transcription, remove all filler words (ums, ahs, likes), fix grammar, and make the tone professional yet friendly. Return ONLY the refined text."
        elif mode == "summarize":
            return base_instr + "Summarize the following text into concise bullet points. Return ONLY the summary."
        elif mode == "shorten":
            return base_instr + "Shorten the following text significantly while keeping the core meaning. Return ONLY the shortened version."
        elif mode == "friendly":
            return base_instr + "Rewrite the following text to have a warm, friendly, and approachable tone. Return ONLY the rewritten text."
        return base_instr

    def robust_copy(self):
        # Clear clipboard
        pyperclip.copy("")
        time.sleep(0.1)
        
        for attempt in range(4):
            print(f"[DEBUG] Copy attempt {attempt + 1}...", flush=True)
            self.controller.release(keyboard.Key.ctrl_l)
            self.controller.release(keyboard.Key.alt_l)
            self.controller.release(keyboard.Key.f11)
            time.sleep(0.2) # Wait for release
            
            with self.controller.pressed(keyboard.Key.ctrl_l):
                time.sleep(0.1)
                self.controller.tap('c')
                time.sleep(0.1)
            
            time.sleep(0.8) # Wait for clipboard
            text = pyperclip.paste().strip()
            if text and len(text) > 1 and text.lower() not in ['c', 'v', 'a']:
                return text
            print(f"[DEBUG] Failed to capture on attempt {attempt + 1}", flush=True)
            time.sleep(0.5)
        return ""

    def process_selection(self, mode):
        print(f"[DEBUG] Processing mode: {mode}", flush=True)
        # Sequence Delay
        time.sleep(0.25) # Allow focus to return to original app
        
        if not self.captured_text:
            print("[DEBUG] ERROR: No text captured.", flush=True)
            return

        print(f"[DEBUG] Contacting Gemini for {mode}...", flush=True)
        try:
            response = self.client.models.generate_content(
                model=MODEL_ID,
                contents=self.captured_text,
                config={'system_instruction': self.get_prompt(mode)}
            )
            refined_text = response.text.strip()
            
            print("[DEBUG] Updating clipboard and pasting...", flush=True)
            pyperclip.copy(refined_text)
            time.sleep(0.3)
            
            with self.controller.pressed(keyboard.Key.ctrl_l):
                self.controller.tap('v')
            
            print("[DEBUG] SUCCESS!", flush=True)
        except Exception as e:
            print(f"[DEBUG] GEMINI ERROR: {e}", flush=True)

    def on_hotkey(self):
        # This is called from the pynput thread
        print("\n[DEBUG] --- Hotkey triggered! ---", flush=True)
        
        # Give the user a moment to lift their fingers
        time.sleep(0.3)
        
        # Grab text
        self.captured_text = self.robust_copy()
        if not self.captured_text:
            print("[DEBUG] Failed to capture text from selection.", flush=True)
            return
            
        # Signal the main thread to show the menu
        self.comm.show_menu_signal.emit()

    def trigger_ui(self):
        # This runs in the main thread (Qt)
        print("[DEBUG] Showing Popup Menu at cursor...", flush=True)
        self.menu.show_at_cursor()

    def run(self):
        # Start the hotkey listener in the background
        listener = keyboard.GlobalHotKeys({'<ctrl>+<alt>+<f11>': self.on_hotkey})
        listener.start()
        
        print("Voice Coach Pro is ACTIVE. Highlight text and press Ctrl+Alt+F11.", flush=True)
        print("(Note: GUI is running in the main thread for stability)", flush=True)
        
        # Main Qt Event Loop
        self.app.exec()

if __name__ == "__main__":
    if not API_KEY:
        print("CRITICAL ERROR: GEMINI_API_KEY NOT FOUND.", flush=True)
        sys.exit(1)
        
    coach = VoiceCoachPro()
    coach.run()
