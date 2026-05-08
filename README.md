# 🤖 J.A.R.V.I.S. - Asistente Virtual Personal
*Read this in English: [🇬🇧 English](README_en.md)*

Un asistente virtual de escritorio inspirado en Iron Man, creado en Python. Cuenta con una interfaz holográfica, memoria a largo plazo y utiliza **Ollama** para procesar la inteligencia artificial de forma local.

## ✨ Características Principales

* **Interfaz Holográfica:** Panel translúcido (Glassmorphism) con bordes redondeados.
* **Cerebro Local:** Conectado a Ollama para una IA rápida y privada.
* **Memoria Persistente:** JARVIS recuerda conversaciones pasadas guardando los datos en tu PC.
* **Voz Realista y Bilingüe:** Motor de texto a voz impulsado por Piper. Entiende comandos de voz tanto en Español como en Inglés.
* **Automatización del PC:** Controla la música (Spotify), lanza juegos de Steam y envía mensajes por Discord.
* **Activación por Palmada:** Sistema de "doble palmada" para despertar el protocolo *Welcome Home*.
* **Perfil Vivo (System Profile):** JARVIS sabe quién eres y qué te gusta gracias a un archivo de configuración local.
* **Visión (Drag & Drop):** Arrastra imágenes a la ventana y JARVIS las analizará.
* **Memoria SQLite:** Adiós a los archivos JSON. El historial y los recuerdos ahora se guardan en una base de datos relacional (`jarvis_memory.db`) ultrarrápida.
* **Sistema de Plugins:** Arquitectura modular. Añade nuevas capacidades (domótica, luces, etc.) simplemente arrastrando archivos `.py` a la carpeta `/plugins`.
* **Visualizador de Audio:** Nuevo ecualizador holográfico cian que reacciona de forma fluida mientras el asistente habla.
* **Localización Dinámica (i18n):** La interfaz y los saludos de J.A.R.V.I.S. se adaptan automáticamente al Español o al Inglés dependiendo del modelo de voz de Piper TTS que estés usando.
* **Autoconciencia de Modelos:** El sistema sabe exactamente qué "cerebro" está usando (Mistral, Qwen, LLaVA) eliminando alucinaciones.


## 🛠️ Requisitos e Instalación

### 1. Librerías de Python
Primero, instala las dependencias necesarias con este comando en tu terminal:

`pip install PyQt6 ollama requests pyautogui send2trash pillow SpeechRecognition sounddevice soundfile numpy pyaudio pystray plyer pyttsx3`

### 2. El Cerebro (Ollama)
Para que JARVIS piense, necesitas tener instalado [Ollama](https://ollama.com/). Una vez instalado, debes descargar un modelo de IA (el que tú prefieras). Aquí tienes los más recomendados:

* **Llama 3 (Recomendado):** El más equilibrado y potente.
  `ollama run llama3`
* **Mistral:** Muy rápido y eficiente.
  `ollama run mistral`
* **Phi-3:** Ideal si tu ordenador no es muy potente.
  `ollama run phi3`
* **Qwen 2.5 Coder (NUEVO):** Ideal para pedirle código o programar.
  `ollama run qwen2.5-coder:7b`
* **LLaVA (NUEVO):** Necesario para que JARVIS pueda ver y analizar imágenes.
  `ollama run llava`

## 🚀 Cómo usarlo

1. Descarga estos archivos en tu ordenador.
2. Asegúrate de tener Ollama abierto con uno de los modelos anteriores.
3. Ejecuta el archivo principal:

`python jarvis.pyw`

**Nota sobre privacidad:** La primera vez que lo abras, se creará la carpeta `archivos_jarvis`. Aquí se guarda tu configuración y la memoria del asistente de forma 100% local.

## 🧠 Personaliza a tu JARVIS (System Profile)
Para que la IA tenga su propia personalidad y sepa quién eres desde el primer momento:

1. En la carpeta del proyecto encontrarás un archivo llamado `system_profile_template.txt`.
2. Haz una copia de ese archivo y renómbralo a **`system_profile.txt`**.
3. Ábrelo y rellena tus datos (tu nombre, gustos, cómo quieres que te hable).
4. Guarda el archivo. ¡JARVIS lo leerá al iniciarse!
