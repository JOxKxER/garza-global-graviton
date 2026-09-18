"""Standalone desktop chat client for a local llama.cpp model server.

Package with PyInstaller, for example:
    python -m PyInstaller --onefile --windowed --name JokerChat
        --distpath "V:\03_Source_Code\build_output" desktop_chat.py
"""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "http://127.0.0.1:8011/v1/chat/completions"
MODEL_NAME = "ggml-org/Qwen2.5-Coder-3B-Instruct-Q8_0-GGUF"
REQUEST_TIMEOUT_SECONDS = 120


class DesktopChat(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Joker Local Chat")
        self.geometry("820x620")
        self.minsize(560, 420)
        self.configure(bg="#1e1e1e")

        self.messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are Joker, a concise and helpful local coding "
                    "assistant."
                ),
            }
        ]
        self.response_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.response_parts: list[str] = []
        self.is_generating = False

        self._build_window()
        self._append_message(
            "Joker",
            "Connected to the local chat client. What are we building?",
        )
        self.after(50, self._drain_response_queue)

    def _build_window(self) -> None:
        self.chat_history = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#252526",
            fg="#e8e8e8",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            borderwidth=0,
            font=("Segoe UI", 11),
            padx=14,
            pady=14,
        )
        self.chat_history.pack(
            fill=tk.BOTH, expand=True, padx=12, pady=(12, 8)
        )
        self.chat_history.tag_configure(
            "user", foreground="#79c0ff", font=("Segoe UI", 11, "bold")
        )
        self.chat_history.tag_configure(
            "joker", foreground="#7ee787", font=("Segoe UI", 11, "bold")
        )
        self.chat_history.tag_configure("error", foreground="#ff7b72")

        input_frame = tk.Frame(self, bg="#1e1e1e")
        input_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        self.message_input = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            bg="#333333",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            borderwidth=0,
            font=("Segoe UI", 11),
            padx=10,
            pady=8,
        )
        self.message_input.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8)
        )
        self.message_input.bind("<Return>", self._send_message)
        self.message_input.focus_set()

        self.send_button = tk.Button(
            input_frame,
            text="Send",
            command=self._send_message,
            bg="#238636",
            activebackground="#2ea043",
            fg="#ffffff",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=12,
        )
        self.send_button.pack(side=tk.RIGHT, fill=tk.Y)

    def _append_message(
        self, sender: str, text: str, tag: str | None = None
    ) -> None:
        self.chat_history.configure(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"{sender}: ", tag)
        self.chat_history.insert(tk.END, f"{text}\n\n")
        self.chat_history.configure(state=tk.DISABLED)
        self.chat_history.see(tk.END)

    def _send_message(self, _event: tk.Event | None = None) -> str | None:
        if self.is_generating:
            return "break"

        message = self.message_input.get("1.0", tk.END).strip()
        if not message:
            return "break"

        self.message_input.delete("1.0", tk.END)
        self._append_message("You", message, "user")
        self.messages.append({"role": "user", "content": message})
        self._start_joker_response()
        return "break"

    def _start_joker_response(self) -> None:
        self.is_generating = True
        self.response_parts = []
        self.send_button.configure(state=tk.DISABLED, text="Thinking...")
        self.message_input.configure(state=tk.DISABLED)
        self._append_message("Joker", "", "joker")
        threading.Thread(target=self._stream_response, daemon=True).start()

    def _stream_response(self) -> None:
        payload = json.dumps(
            {"model": MODEL_NAME, "messages": self.messages, "stream": True}
        ).encode("utf-8")
        request = Request(
            API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue
                    event_data = line[6:]
                    if event_data == "[DONE]":
                        break
                    choice = json.loads(event_data).get("choices", [{}])[0]
                    text = choice.get("delta", {}).get("content", "")
                    if text:
                        self.response_queue.put(("chunk", text))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            message = (
                f"Local model server returned HTTP {error.code}: {detail}"
            )
            self.response_queue.put(("error", message))
        except (
            URLError, TimeoutError, OSError, json.JSONDecodeError
        ) as error:
            message = f"Cannot reach local model server at {API_URL}: {error}"
            self.response_queue.put(("error", message))
        finally:
            self.response_queue.put(("complete", ""))

    def _drain_response_queue(self) -> None:
        while True:
            try:
                event, content = self.response_queue.get_nowait()
            except queue.Empty:
                break

            if event == "chunk":
                self.response_parts.append(content)
                self._append_stream_chunk(content)
            elif event == "error":
                self._append_stream_chunk(f"\n{content}", "error")
            elif event == "complete":
                if self.response_parts:
                    self.messages.append(
                        {
                            "role": "assistant",
                            "content": "".join(self.response_parts),
                        }
                    )
                self.is_generating = False
                self.send_button.configure(state=tk.NORMAL, text="Send")
                self.message_input.configure(state=tk.NORMAL)
                self.message_input.focus_set()

        self.after(50, self._drain_response_queue)

    def _append_stream_chunk(self, text: str, tag: str | None = None) -> None:
        self.chat_history.configure(state=tk.NORMAL)
        self.chat_history.insert(tk.END, text, tag)
        self.chat_history.configure(state=tk.DISABLED)
        self.chat_history.see(tk.END)


if __name__ == "__main__":
    DesktopChat().mainloop()
