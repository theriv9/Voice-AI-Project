import os
import time
import sys
import pyperclip
import ollama
from pynput import keyboard
from dotenv import load_dotenv

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QCursor, QFont

# Load environment variables (kept for consistency, though API keys may not be needed for local)
load_dotenv()

# We'll use Llama 3.1 as the local backend
LOCAL_MODEL_ID = "llama3.1"

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
            ("✨ Local Refine (Pro)", "professional"),
            ("😊 Local Friendly Tone", "friendly")
        ]

        self.container = QWidget()
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            QWidget#container {
                background-color: #1a1a1a;
                border: 2px solid #0078d4;
                border-radius: 10px;
            }
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                padding: 12px 24px;
                text-align: left;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #333;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.setSpacing(4)

        for text, mode in options:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, m=mode: self.handle_click(m))
            container_layout.addWidget(btn)

        layout.addWidget(self.container)
        self.setLayout(layout)

    def handle_click(self, mode):
        # Hide immediately and process events to ensure focus shifts back
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

class VoiceCoachLocal:
    def __init__(self):
        self.controller = keyboard.Controller()
        self.app = QApplication(sys.argv)
        
        self.comm = Communicate()
        self.comm.show_menu_signal.connect(self.trigger_ui)
        self.comm.option_selected.connect(self.process_selection)

        self.menu = PopupMenu(self.comm)
        self.captured_text = ""

    def get_prompt_messages(self, mode, user_text):
        # Hyper-Clinical transformation prompts.
        # We tell the model it is a "Text Rewriting Engine" to move away from "Assistant" personas.
        
        if mode == "professional":
            system_content = (
                "You are a Text Transformation Engine. Your EXCLUSIVE task is to take the provided input "
                "and output a grammatically correct, professional version of that EXACT content. \n"
                "RULES:\n"
                "1. NEVER answer a question. If the input is a question, you must REWRITE the question.\n"
                "2. Do NOT provide help, do NOT search for information, and do NOT be an assistant.\n"
                "3. Output ONLY the transformed text. Zero conversational filler."
            )
            examples = [
                {'role': 'user', 'content': "umm what is the best time that works for your schedule to grab a coffee?"},
                {'role': 'assistant', 'content': "When are you available to meet over a coffee?"},
                {'role': 'user', 'content': "uh I think we should like maybe send the email now"},
                {'role': 'assistant', 'content': "I believe we should send the email immediately."}
            ]
        else: # friendly
            system_content = (
                "You are a Text Transformation Engine. Your EXCLUSIVE task is to take the provided input "
                "and output a warm, friendly version of that EXACT content.\n"
                "RULES:\n"
                "1. NEVER answer a question. If the input is a question, you must REWRITE the question.\n"
                "2. Do NOT provide help, do NOT search for information, and do NOT be an assistant.\n"
                "3. Output ONLY the transformed text. Zero conversational filler."
            )
            examples = [
                {'role': 'user', 'content': "What time can you meet for coffee?"},
                {'role': 'assistant', 'content': "Hey! Do you happen to know what time works best for you to grab a coffee together?"},
                {'role': 'user', 'content': "The report is done. Read it."},
                {'role': 'assistant', 'content': "Hi there! Just a heads up that the report is all ready for you to take a look whenever you have some time."}
            ]

        messages = [{'role': 'system', 'content': system_content}]
        messages.extend(examples)
        messages.append({'role': 'user', 'content': user_text})
        return messages

    def robust_copy(self):
        pyperclip.copy("")
        time.sleep(0.05)
        
        for attempt in range(4):
            print(f"[DEBUG] Local Copy attempt {attempt + 1}...", flush=True)
            self.controller.release(keyboard.Key.ctrl_l)
            self.controller.release(keyboard.Key.alt_l)
            self.controller.release(keyboard.Key.f11)
            time.sleep(0.05)
            
            with self.controller.pressed(keyboard.Key.ctrl_l):
                self.controller.tap('c')
            
            time.sleep(0.4) 
            text = pyperclip.paste().strip()
            if text and len(text) > 1 and text.lower() not in ['c', 'v', 'a']:
                return text
            time.sleep(0.3)
        return ""

    def process_selection(self, mode):
        print(f"[DEBUG] Local processing mode: {mode}", flush=True)
        time.sleep(0.2) 
        
        if not self.captured_text:
            print("[DEBUG] ERROR: No text captured.", flush=True)
            return

        print(f"[DEBUG] Contacting local Ollama ({LOCAL_MODEL_ID}) for {mode}...", flush=True)
        try:
            # Use strict few-shot messages
            response = ollama.chat(
                model=LOCAL_MODEL_ID, 
                messages=self.get_prompt_messages(mode, self.captured_text),
                options={
                    'temperature': 0, 
                }
            )
            
            refined_text = response['message']['content'].strip()
            
            # Remove any accidental wrapping quotes if the model adds them
            if refined_text.startswith('"') and refined_text.endswith('"'):
                refined_text = refined_text[1:-1]
            
            print("[DEBUG] Updating clipboard...", flush=True)
            pyperclip.copy(refined_text)
            time.sleep(0.15)
            
            print("[DEBUG] Performing Fast Paste...", flush=True)
            self.controller.release(keyboard.Key.ctrl_l)
            time.sleep(0.05)
            
            with self.controller.pressed(keyboard.Key.ctrl_l):
                self.controller.tap('v')
            
            print("[DEBUG] SUCCESS (Local)!", flush=True)
        except Exception as e:
            print(f"[DEBUG] OLLAMA ERROR: {e}", flush=True)

    def on_hotkey(self):
        time.sleep(0.1)
        self.captured_text = self.robust_copy()
        if not self.captured_text:
            print("[DEBUG] Failed to capture text locally.", flush=True)
            return
        self.comm.show_menu_signal.emit()

    def trigger_ui(self):
        print("[DEBUG] Showing Local Popup Menu...", flush=True)
        self.menu.show_at_cursor()

    def run(self):
        listener = keyboard.GlobalHotKeys({'<ctrl>+<alt>+<f11>': self.on_hotkey})
        listener.start()
        
        print(f"Voice Coach LOCAL is ACTIVE. Model: {LOCAL_MODEL_ID}. Hotkey: Ctrl+Alt+F11.", flush=True)
        self.app.exec()

if __name__ == "__main__":
    # Check if ollama is reachable (optional)
    try:
        coach = VoiceCoachLocal()
        coach.run()
    except Exception as e:
        print(f"FAILED to start Local Voice Coach: {e}", flush=True)
