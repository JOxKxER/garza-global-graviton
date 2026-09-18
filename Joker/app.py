"""Joker: an offline local AI chat application backed by Ollama."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from config import SETTINGS
from engine import ChatMessage, JokerEngine, JokerEngineError


class JokerApp(tk.Tk):
    def __init__(self, engine: JokerEngine) -> None:
        super().__init__()
        self.engine = engine
        self.messages: list[ChatMessage] = [
            ChatMessage("system", SETTINGS.system_prompt)
        ]
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.generating = False

        self.title("Joker | Offline Local AI")
        self.geometry("900x680")
        self.minsize(620, 460)
        self._build_ui()
        self.after(50, self._drain_events)
        self._append_text(
            "Joker", "Offline local engine ready.\n", "assistant"
        )

    def _build_ui(self) -> None:
        self.configure(bg="#14181f")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", padding=8)
        style.configure(
            "Header.TLabel", background="#14181f", foreground="#7ee787"
        )
        style.configure(
            "Status.TLabel", background="#14181f", foreground="#9da7b3"
        )

        header = ttk.Frame(self, padding=(16, 14, 16, 8))
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="JOKER",
            style="Header.TLabel",
            font=("Segoe UI", 18, "bold"),
        ).pack(side=tk.LEFT)
        self.status = ttk.Label(
            header,
            text=f"Offline | Ollama {SETTINGS.ollama_host} | {SETTINGS.model}",
            style="Status.TLabel",
        )
        self.status.pack(side=tk.RIGHT)

        self.transcript = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#20252d",
            fg="#e6edf3",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=16,
            font=("Segoe UI", 11),
        )
        self.transcript.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))
        self.transcript.tag_configure("assistant", foreground="#7ee787")
        self.transcript.tag_configure("user", foreground="#79c0ff")
        self.transcript.tag_configure("error", foreground="#ff7b72")

        composer = ttk.Frame(self, padding=(16, 0, 16, 16))
        composer.pack(fill=tk.X)
        self.input = tk.Text(
            composer, height=4, wrap=tk.WORD, font=("Segoe UI", 11)
        )
        self.input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input.bind("<Control-Return>", self._send_event)
        ttk.Button(composer, text="Send", command=self.send_message).pack(
            side=tk.RIGHT, fill=tk.Y, padx=(10, 0)
        )

    def _send_event(self, _event: tk.Event) -> str:
        self.send_message()
        return "break"

    def send_message(self) -> None:
        if self.generating:
            return
        text = self.input.get("1.0", tk.END).strip()
        if not text:
            return
        self.input.delete("1.0", tk.END)
        self._append_text("You", f"{text}\n", "user")
        self.messages.append(ChatMessage("user", text))
        self.generating = True
        self.status.configure(text="Generating locally...")
        threading.Thread(target=self._generate, daemon=True).start()

    def _generate(self) -> None:
        try:
            self.events.put(("start", ""))
            response_parts: list[str] = []
            for chunk in self.engine.stream_chat(self.messages):
                response_parts.append(chunk)
                self.events.put(("chunk", chunk))
            self.events.put(("complete", "".join(response_parts)))
        except (JokerEngineError, ValueError) as error:
            self.events.put(("error", str(error)))

    def _drain_events(self) -> None:
        while True:
            try:
                event, content = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "start":
                self._append_text("Joker", "", "assistant")
            elif event == "chunk":
                self._append_text("", content, "assistant")
            elif event == "complete":
                self.messages.append(ChatMessage("assistant", content))
                self.generating = False
                self.status.configure(text=f"Offline | {SETTINGS.model}")
            elif event == "error":
                self._append_text("Error", f"{content}\n", "error")
                self.generating = False
                self.status.configure(text="Ollama unavailable")
                messagebox.showerror("Joker", content)
        self.after(50, self._drain_events)

    def _append_text(self, speaker: str, content: str, tag: str) -> None:
        self.transcript.configure(state=tk.NORMAL)
        if speaker:
            self.transcript.insert(tk.END, f"{speaker}: ", tag)
        self.transcript.insert(tk.END, content, tag)
        self.transcript.configure(state=tk.DISABLED)
        self.transcript.see(tk.END)


def main() -> None:
    JokerApp(JokerEngine(SETTINGS)).mainloop()


if __name__ == "__main__":
    main()
