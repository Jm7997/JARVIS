# 🤖 J.A.R.V.I.S. - Asistente Virtual Personal

Un asistente virtual de escritorio inspirado en Iron Man, creado en Python. Cuenta con una interfaz holográfica, memoria a largo plazo y utiliza **Ollama** para procesar la inteligencia artificial de forma local.

## ✨ Características Principales

* **Interfaz Holográfica:** Panel translúcido (Glassmorphism) con bordes redondeados.
* **Cerebro Local:** Conectado a Ollama para una IA rápida y privada.
* **Memoria Persistente:** JARVIS recuerda conversaciones pasadas guardando los datos en tu PC.
* **Voz Realista:** Motor de texto a voz impulsado por Piper.

## 🛠️ Requisitos e Instalación

### 1. Librerías de Python
Primero, instala las dependencias necesarias con este comando en tu terminal:

`pip install PyQt6 ollama requests`

### 2. El Cerebro (Ollama)
Para que JARVIS piense, necesitas tener instalado [Ollama](https://ollama.com/). Una vez instalado, debes descargar un modelo de IA (el que tú prefieras). Aquí tienes los más recomendados:

* **Llama 3 (Recomendado):** El más equilibrado y potente.
  `ollama run llama3`
* **Mistral:** Muy rápido y eficiente.
  `ollama run mistral`
* **Phi-3:** Ideal si tu ordenador no es muy potente.
  `ollama run phi3`

## 🚀 Cómo usarlo

1. Descarga estos archivos en tu ordenador.
2. Asegúrate de tener Ollama abierto con uno de los modelos anteriores.
3. Ejecuta el archivo principal:

`python jarvis.pyw`

**Nota sobre privacidad:** La primera vez que lo abras, se creará la carpeta `archivos_jarvis`. Aquí se guarda tu configuración y la memoria del asistente de forma 100% local.