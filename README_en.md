# 🤖 J.A.R.V.I.S. - Personal Virtual Assistant
*Leer en español: [🇪🇸 Español](README.md)*

A desktop virtual assistant inspired by Iron Man, created in Python. It features a holographic interface, long-term memory, and uses **Ollama** to process artificial intelligence locally.

## ✨ Key Features

* **Holographic Interface:** Translucent panel (Glassmorphism) with rounded edges.
* **Local Brain:** Connected to Ollama for fast and private AI.
* **Persistent Memory:** JARVIS remembers past conversations by saving data on your PC.
* **Realistic & Bilingual Voice:** Text-to-speech engine powered by Piper. Understands voice commands in both Spanish and English.
* **PC Automation:** Control your music (Spotify), launch Steam games, and send Discord messages.
* **Clap Activation:** "Double-clap" detection system to wake up the *Welcome Home* protocol.
* **Living Profile:** JARVIS knows who you are and what you like thanks to a local configuration file.
* **Vision (Drag & Drop):** Drag images into the window and JARVIS will analyze them.

## 🛠️ Requirements and Installation

### 1. Python Libraries
First, install the necessary dependencies with this command in your terminal:

`pip install PyQt6 ollama requests pyautogui send2trash pillow SpeechRecognition sounddevice soundfile numpy pyaudio pystray plyer pyttsx3`

### 2. The Brain (Ollama)
For JARVIS to think, you need to have [Ollama](https://ollama.com/) installed. Once installed, you must download an AI model (whichever you prefer). Here are the most recommended ones:

* **Llama 3 (Recommended):** The most balanced and powerful.
  `ollama run llama3`
* **Mistral:** Very fast and efficient.
  `ollama run mistral`
* **Phi-3:** Ideal if your computer is not very powerful.
  `ollama run phi3`
* **Qwen 2.5 Coder (NEW):** Ideal for coding tasks.
  `ollama run qwen2.5-coder:7b`
* **LLaVA (NEW):** Required for JARVIS to see and analyze images.
  `ollama run llava`

## 🚀 How to use it

1. Download these files to your computer.
2. Make sure you have Ollama open with one of the models above.
3. Run the main file:

`python jarvis.pyw`

**Privacy Note:** The first time you open it, the `archivos_jarvis` folder will be created. Your configuration and the assistant's memory are saved here 100% locally.

## 🧠 Customize your JARVIS (System Profile)
To give the AI its own personality and teach it who you are from the very first moment:

1. In the project folder, you will find a file named `system_profile_template.txt`.
2. Make a copy of that file and rename it to **`system_profile.txt`**.
3. Open it and fill in your data (your name, interests, how you want it to talk to you).
4. Save the file. JARVIS will read it upon startup!

*(Note: Your `system_profile.txt` file is protected by the `.gitignore` file. Your personal data will never be uploaded to GitHub).*