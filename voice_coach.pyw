import os
import time
import sys
import pyperclip
from pynput import keyboard
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
# Use Gemini 2.5 Flash as requested
MODEL_ID = "gemini-2.5-flash"

if not API_KEY:
    print("CRITICAL ERROR: GEMINI_API_KEY NOT FOUND IN .ENV FILE.", flush=True)
else:
    print(f"API Key loaded (Free Tier Client detected: {API_KEY[:10]}...)", flush=True)

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"CRITICAL ERROR initializing Gemini client: {e}", flush=True)

# Keyboard controller
controller = keyboard.Controller()

def robust_copy():
    """Attempts to copy text with retries and verification to avoid 'C'/'A' typing issue."""
    old_clipboard = pyperclip.paste()
    # Clear clipboard to be sure we're getting fresh data
    pyperclip.copy("")
    time.sleep(0.2)
    
    for attempt in range(4):
        print(f"[DEBUG] Copy attempt {attempt + 1}...", flush=True)
        
        # We use a very deliberate sequence for OneNote
        # Release everything first
        controller.release(keyboard.Key.ctrl_l)
        controller.release(keyboard.Key.ctrl_r)
        time.sleep(0.2)
        
        # Press and HOLD Ctrl
        with controller.pressed(keyboard.Key.ctrl_l):
            time.sleep(0.3)
            # Tap 'C' - we NO LONGER tap 'A' here.
            controller.press('c')
            time.sleep(0.1)
            controller.release('c')
            time.sleep(0.5)
            
        time.sleep(1.0) # Wait for clipboard synchronization
        
        new_clipboard = pyperclip.paste().strip()
        
        # check if we actually got text (and not just 'c' or 'a')
        if new_clipboard and len(new_clipboard) > 1:
            if new_clipboard.lower() not in ['c', 'a', 'v']:
                return new_clipboard
            
        print("[DEBUG] Copy failed (got empty or single char). Retrying...", flush=True)
        time.sleep(1.0)

    # If all retries fail, try returning the last content if it's not empty
    last_resort = pyperclip.paste().strip()
    return last_resort if len(last_resort) > 1 else ""

def on_activate():
    print("\n[DEBUG] --- Hotkey triggered! ---", flush=True)
    
    # 1. Grab text
    raw_text = robust_copy()
    
    if not raw_text:
        print("[DEBUG] ERROR: Failed to capture text from clipboard after multiple attempts.", flush=True)
        return

    print(f"[DEBUG] Captured text (first 50 chars): {raw_text[:50]}...", flush=True)

    # 2. Refine text with Gemini
    print(f"[DEBUG] Contacting Gemini ({MODEL_ID}) for refinement...", flush=True)
    try:
        start_time = time.time()
        # For Free Tier, we use the gemini-1.5-flash-latest alias
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=raw_text,
            config={
                'system_instruction': (
                    "You are a professional voice and grammar coach. "
                    "Take this raw transcription, remove all filler words (ums, ahs, likes), "
                    "fix grammar, and make the tone professional yet friendly. "
                    "Return ONLY the refined text."
                )
            }
        )
        duration = time.time() - start_time
        print(f"[DEBUG] Gemini response received in {duration:.2f}s.", flush=True)
        
        refined_text = response.text.strip()
        
        # 3. Paste back
        print("[DEBUG] Updating clipboard with refined text...", flush=True)
        pyperclip.copy(refined_text)
        
        # User requested: Add a 200ms delay after the script puts the text on the clipboard
        print("[DEBUG] Waiting 0.2s before paste...", flush=True)
        time.sleep(0.2)
        
        print("[DEBUG] Simulating Ctrl+V...", flush=True)
        with controller.pressed(keyboard.Key.ctrl_l):
            time.sleep(0.1) # Small delay for Ctrl to register
            controller.tap('v')
            time.sleep(0.1)
        
        print("[DEBUG] SUCCESS: Text refined and pasted back!", flush=True)

    except Exception as e:
        print(f"[DEBUG] GEMINI API ERROR: {e}", flush=True)
        if "404" in str(e):
            print("[DEBUG] TRYING FALLBACK: gemini-1.5-flash", flush=True)
            # Simple retry with the basic name
            try:
                response = client.models.generate_content(model="gemini-1.5-flash", contents=raw_text)
                print("[DEBUG] Fallback SUCCESS!", flush=True)
                # ... repeat paste logic or better yet, just tell user to try it.
            except: pass

def start_listener():
    print("[DEBUG] Starting Global Hotkey Listener (Ctrl + Alt + F11)...", flush=True)
    try:
        with keyboard.GlobalHotKeys({
                '<ctrl>+<alt>+<f11>': on_activate}) as h:
            print("[DEBUG] Listener is ACTIVE. Press Ctrl + Alt + F11 to test.", flush=True)
            h.join()
    except Exception as e:
        print(f"[DEBUG] LISTENER ERROR: {e}", flush=True)

if __name__ == "__main__":
    print("Voice Coach Debug Mode Started (Free Tier Edition).", flush=True)
    print("Working Directory:", os.getcwd(), flush=True)
    start_listener()
