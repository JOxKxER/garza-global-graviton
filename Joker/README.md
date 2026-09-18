# Joker

Joker is an offline local AI chat application. It communicates only with an Ollama daemon bound to the loopback address `localhost:11434` and does not contain cloud APIs, telemetry, analytics, or tracking.

## Setup

From PowerShell:

```powershell
cd V:\03_Source_Code\Joker
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull llama3.1
```

On Windows, Ollama normally runs as a background service and listens on
`localhost:11434`; you do not need to run `ollama serve` manually. If the
service is not running, start Ollama from the Start menu, then pull the model.

Open a second PowerShell window and run:

```powershell
cd V:\03_Source_Code\Joker
..\.venv\Scripts\python.exe app.py
```

The default model is `llama3.1`. To use another model already installed locally:

```powershell
$env:OLLAMA_MODEL = "gemma3"
..\.venv\Scripts\python.exe app.py
```

`Ctrl+Enter` sends a message. Responses stream into the window as Ollama produces them.

## Configuration

Supported environment variables:

- `OLLAMA_HOST`: loopback URL only; defaults to `http://127.0.0.1:11434`
- `OLLAMA_MODEL`: local model name; defaults to `llama3.1`

Temperature is fixed at `0.0` for deterministic behavior, and the context window is `8192` tokens. The application intentionally rejects non-loopback Ollama URLs.
