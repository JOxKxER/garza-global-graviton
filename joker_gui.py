import tkinter as tk
from tkinter import scrolledtext, font
requests = None
try:
    import requests
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "requests"])
    import requests

API_URL = "http://127.0.0.1:8011/v1/chat/completions"
MODEL_NAME = "ggml-org/Qwen2.5-Coder-3B-Instruct-Q8_0-GGUF"
SYSTEM_MESSAGE = (
    "You are a specialized local AI business partner and coding assistant "
    "built for Joel Garza's workspace."
)

def query_joker(prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        "stream": False
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"Error: Status code {response.status_code}"
    except Exception as e:
        return f"Connection Error: Is llama.cpp running? ({e})"

def send_message(event=None):
    user_text = entry.get().strip()
    if not user_text:
        return
    
    chat_log.config(state=tk.NORMAL)
    chat_log.insert(tk.END, f"\n[You]: {user_text}\n")
    chat_log.config(state=tk.DISABLED)
    entry.delete(0, tk.END)
    
    # Query local model
    response_text = query_joker(user_text)
    
    chat_log.config(state=tk.NORMAL)
    chat_log.insert(tk.END, f"[Joker]: {response_text}\n")
    chat_log.config(state=tk.DISABLED)
    chat_log.see(tk.END)

# GUI Setup
root = tk.Tk()
root.title("Joker - Local AI Business Partner")
root.geometry("600x500")
root.configure(bg="#1e1e1e")

custom_font = font.Font(family="Consolas", size=10)

chat_log = scrolledtext.ScrolledText(root, wrap=tk.WORD, bg="#252526", fg="#dcdccc", font=custom_font)
chat_log.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
chat_log.config(state=tk.DISABLED)

bottom_frame = tk.Frame(root, bg="#1e1e1e")
bottom_frame.pack(padx=10, pady=10, fill=tk.X)

entry = tk.Entry(bottom_frame, bg="#333333", fg="#ffffff", insertbackground="white", font=custom_font)
entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
entry.bind("<Return>", send_message)

send_button = tk.Button(bottom_frame, text="Send", command=send_message, bg="#007acc", fg="#ffffff", relief=tk.FLAT)
send_button.pack(side=tk.RIGHT)

# Initial Greeting
chat_log.config(state=tk.NORMAL)
chat_log.insert(tk.END, "[Joker]: Online. Local mesh connected. Ready for business.\n")
chat_log.config(state=tk.DISABLED)

root.mainloop()