import os
import time
import sys
import pyperclip
import ollama
from pynput import keyboard
from google import genai
from dotenv import load_dotenv

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QHBoxLayout
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
    review_complete = pyqtSignal(str)

class ReviewWindow(QWidget):
    def __init__(self, comm):
        super().__init__()
        self.comm = comm
        self.pending_text = ""
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: #1a1a1a;
                border: 2px solid #0078d4;
                border-radius: 12px;
            }
            QLabel#title {
                color: #0078d4;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
                margin-bottom: 4px;
            }
            QTextEdit {
                background-color: #252525;
                color: #ffffff;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QPushButton#accept {
                background-color: #0078d4;
                color: white;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton#accept:hover {
                background-color: #0086f1;
            }
            QPushButton#decline {
                background-color: #333;
                color: #ccc;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        
        title = QLabel("Review AI Refinement")
        title.setObjectName("title")
        container_layout.addWidget(title)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(False)
        self.text_area.setMinimumHeight(150)
        self.text_area.setMinimumWidth(350)
        container_layout.addWidget(self.text_area)

        btn_layout = QHBoxLayout()
        btn_decline = QPushButton("❌ Decline")
        btn_decline.setObjectName("decline")
        btn_decline.clicked.connect(self.hide)
        
        btn_accept = QPushButton("✅ Accept & Paste")
        btn_accept.setObjectName("accept")
        btn_accept.clicked.connect(self.handle_accept)
        
        btn_layout.addWidget(btn_decline)
        btn_layout.addWidget(btn_accept)
        container_layout.addLayout(btn_layout)

        layout.addWidget(self.container)
        self.setLayout(layout)

    def handle_accept(self):
        # Capture the current (possibly edited) text from the text area
        final_text = self.text_area.toPlainText().strip()
        self.hide()
        QApplication.processEvents()
        self.comm.review_complete.emit(final_text)

    # Make frameless window draggable
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def show_review(self, text):
        self.pending_text = text
        self.text_area.setText(text)
        
        # Smart positioning: Ensure window stays on screen
        screen = QApplication.primaryScreen().geometry()
        pos = QCursor.pos()
        
        # Default offset
        x = pos.x() - 150
        y = pos.y() - 100
        
        # Constrain to screen boundaries
        w, h = 380, 250 # Approximate dimensions
        x = max(screen.left(), min(x, screen.right() - w))
        y = max(screen.top(), min(y, screen.bottom() - h))
        
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

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

        # Cloud Section
        header_cloud = QLabel("Cloud-Based")
        header_cloud.setObjectName("header")
        container_layout.addWidget(header_cloud)
        
        btn_gem_sum = QPushButton("Gemini Summarize")
        btn_gem_sum.clicked.connect(lambda: self.handle_click("gemini_summarize"))
        container_layout.addWidget(btn_gem_sum)

        # Local Section
        header_local = QLabel("Local-Based")
        header_local.setObjectName("header")
        container_layout.addWidget(header_local)
        
        btn_loc_sum = QPushButton("Ollama Summarize")
        btn_loc_sum.clicked.connect(lambda: self.handle_click("ollama_summarize"))
        container_layout.addWidget(btn_loc_sum)

        layout.addWidget(self.container)
        self.setLayout(layout)

    def handle_click(self, mode):
        self.hide()
        QApplication.processEvents()
        self.comm.option_selected.emit(mode)

    # Make frameless window draggable
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

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
        self.comm.review_complete.connect(self.finalize_paste)

        self.menu = PopupMenu(self.comm)
        self.review_window = ReviewWindow(self.comm)
        self.captured_text = ""

    def get_summary_prompt(self):
        return (
            "You are to receive text and your job is to summarize the sentiment of it to its entirety and improve spelling and grammar. "
            "CRITICAL RULES: "
            "1. **No Preface**: Do NOT include any introductory remarks or prefaces (like 'Here is a summarized version'). "
            "2. **No Quotes**: Do NOT wrap the summary in quotation marks. "
            "3. **Structure**: Use new lines and paragraphs to organize the summary if the content warrants it. "
            "4. **Tone**: Use a professional business tone that is friendly and human-like. "
            "Output ONLY the summarized text."
        )

    def get_local_messages(self, user_text):
        # Few-shot example with multi-line structure for clearer 1B model guidance
        example_in = (
            "Yeah so we had the meeting about the new office space. it was pretty good. "
            "Dave says we move in April. Oh and the budget for furniture is 10k. "
            "We also need to hire a new intern soon for the summer."
        )
        example_out = (
            "We have confirmed a move to the new office space in April.\n\n"
            "A budget of $10,000 has been allocated for new furniture. Additionally, "
            "recruitment for a summer intern will begin shortly."
        )
        
        return [
            {'role': 'system', 'content': self.get_summary_prompt()},
            {'role': 'user', 'content': example_in},
            {'role': 'assistant', 'content': example_out},
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
            if mode == "gemini_summarize":
                if not self.gemini_client:
                    print("[DEBUG] ERROR: Gemini API Key missing or client not initialized.", flush=True)
                    return
                print(f"[DEBUG] Calling Gemini ({GEMINI_MODEL})...", flush=True)
                response = self.gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=self.captured_text,
                    config={'system_instruction': self.get_summary_prompt()}
                )
                refined_text = response.text.strip()
            elif mode == "ollama_summarize":
                print(f"[DEBUG] Calling Ollama ({LOCAL_MODEL})...", flush=True)
                response = ollama.chat(
                    model=LOCAL_MODEL, 
                    messages=self.get_local_messages(self.captured_text),
                    options={'temperature': 0}
                )
                refined_text = response['message']['content'].strip()
            else:
                refined_text = "Unknown Mode"

            # Clean up and Paste
            if refined_text.startswith('"') and refined_text.endswith('"'):
                refined_text = refined_text[1:-1]
            
            # Instead of auto-pasting, show the review window
            print("[DEBUG] Showing Review Window...", flush=True)
            self.review_window.show_review(refined_text)

        except Exception as e:
            print(f"[DEBUG] ERROR: {e}", flush=True)

    def finalize_paste(self, text):
        print("[DEBUG] User accepted. Finalizing paste...", flush=True)
        time.sleep(0.2)
        pyperclip.copy(text)
        time.sleep(0.15)
        
        with self.controller.pressed(keyboard.Key.ctrl_l):
            self.controller.tap('v')
        print("[DEBUG] SUCCESS!", flush=True)

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
