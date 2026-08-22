"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import json
import os
from datetime import datetime

# Resolve paths relative to vault root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(BASE_DIR, "04_Legal_and_IP", "sovereign_ledger.json")

TEMPLATES = {
    "1": {
        "name": "New Module PRD Generator",
        "template": (
            "SYSTEM: You are an expert system architect writing a PRD for an air-gapped system.\n"
            "TASK: Create a PRD for Module {module_num}: {module_name}.\n"
            "GOAL: {goal}\n"
            "STRICT RULES: Must run 100% offline, use relative paths, and output standard Python code without external third-party dependencies."
        )
    },
    "2": {
        "name": "Offline Code Security Audit",
        "template": (
            "SYSTEM: You are a strict cybersecurity and Python code auditor.\n"
            "TASK: Review the script '{script_name}' for security vulnerabilities, path traversal bugs, and error-handling gaps.\n"
            "FOCUS: Ensure no network requests are attempted and file operations use absolute/relative safe path resolution."
        )
    },
    "3": {
        "name": "Architecture & Logic Refactor",
        "template": (
            "SYSTEM: You are a lead software engineer optimizing offline Python architecture.\n"
            "TASK: Refactor script '{script_name}' to improve efficiency, modularity, and error handling while strictly preserving all existing logging and ledger interfaces."
        )
    }
}

def log_task_event(task_name, compiled_prompt):
    """Logs the prompt task request to sovereign_ledger.json."""
    os.makedirs(os.path.join(BASE_DIR, "04_Legal_and_IP"), exist_ok=True)
    ledger_data = []
    
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []
            
    payload = {
        "event": "AI_TASK_ROUTED",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "task_name": task_name,
        "prompt_length_chars": len(compiled_prompt)
    }
    
    ledger_data.append(payload)
    
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: LOCAL AI TASK ROUTER ===")
    print("\nSelect a Prompt Template:")
    for key, val in TEMPLATES.items():
        print(f" [{key}] {val['name']}")
        
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice in TEMPLATES:
        selected = TEMPLATES[choice]
        print(f"\n--- Selected: {selected['name']} ---")
        
        if choice == "1":
            mod_num = input("Enter Module Number (e.g., 08): ")
            mod_name = input("Enter Module Name: ")
            mod_goal = input("Enter Goal/Purpose: ")
            prompt_text = selected["template"].format(module_num=mod_num, module_name=mod_name, goal=mod_goal)
        elif choice in ["2", "3"]:
            s_name = input("Enter Script Name (e.g., storage_engine.py): ")
            prompt_text = selected["template"].format(script_name=s_name)
            
        print("\n================ COMPILED PROMPT FOR QWEN ================")
        print(prompt_text)
        print("==========================================================")
        
        log_task_event(selected["name"], prompt_text)
        print(f"\n[SUCCESS] Task event logged to sovereign_ledger.json")
    else:
        print("Invalid selection. Aborting.")
        
    print("\n--- Task Routing Complete ---")
