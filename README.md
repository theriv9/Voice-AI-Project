# Voice Coach AI

A professional Windows background agent that refines your text using Gemini AI.

## Features
- **Global Hotkey**: Trigger refinement anywhere with `Ctrl + Alt + F11`.
- **Pro Popup Menu**: Choose between **Professional Refinement** and **Friendly Tone**.
- **Context Aware**: Highlighting text and triggering the coach replaces it instantly with the AI's improved version.
- **OneNote Optimized**: Specialized logic to handle focus and keyboard simulation in sensitive applications.

## Versions
- `voice_coach_pro.pyw`: The latest version with a PyQt6 GUI popup menu.
- `voice_coach.pyw`: The lightweight background-only version.

## Setup
1. Install dependencies:
   ```bash
   pip install pynput pyperclip google-genai python-dotenv PyQt6
   ```
2. Create a `.env` file with your Gemini API key:
   ```
   GEMINI_API_KEY=your_key_here
   ```
3. Run the pro version:
   ```bash
   python voice_coach_pro.pyw
   ```
