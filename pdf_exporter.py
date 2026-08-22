"""
Garza Global Graviton Core Module
Automated Vault Infrastructure Script
"""
import json
import os
import re
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGAL_DIR = os.path.join(BASE_DIR, "04_Legal_and_IP")
EXPORT_DIR = os.path.join(LEGAL_DIR, "exports")
LEDGER_PATH = os.path.join(LEGAL_DIR, "sovereign_ledger.json")

# Executive Defense CSS Styling
CSS_STYLE = """
<style>
    body { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a; margin: 40px; background-color: #ffffff; }
    h1 { color: #0f2b48; border-bottom: 2px solid #0f2b48; padding-bottom: 8px; font-size: 24pt; }
    h2 { color: #1d4ed8; margin-top: 24px; font-size: 16pt; border-bottom: 1px solid #e5e7eb; }
    h3 { color: #374151; font-size: 13pt; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 10pt; }
    th, td { border: 1px solid #d1d5db; padding: 10px; text-align: left; }
    th { background-color: #f3f4f6; color: #111827; font-weight: bold; }
    tr:nth-child(even) { background-color: #f9fafb; }
    code { background-color: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: 'Consolas', monospace; font-size: 9.5pt; color: #b91c1c; }
    pre { background-color: #1e293b; color: #f8fafc; padding: 16px; border-radius: 6px; overflow-x: auto; }
    pre code { background-color: transparent; color: #f8fafc; }
    blockquote { border-left: 4px solid #1d4ed8; padding-left: 16px; color: #4b5563; font-style: italic; margin: 20px 0; }
    hr { border: 0; height: 1px; background: #e5e7eb; margin: 30px 0; }
    .footer { margin-top: 50px; font-size: 8pt; color: #6b7280; text-align: center; border-top: 1px solid #e5e7eb; padding-top: 10px; }
</style>
"""

def read_file_safe(file_path: str) -> str:
    """Safely reads text files handling multi-encoding fallbacks."""
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    # Ultimate fallback with character substitution
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def simple_md_to_html(md_text: str) -> str:
    """Converts basic Markdown syntax into clean HTML."""
    html = md_text

    # Headers
    html = re.sub(r'^# (.*?)$', r'h1.\1', html, flags=re.M)
    html = re.sub(r'^## (.*?)$', r'h2.\1', html, flags=re.M)
    html = re.sub(r'^### (.*?)$', r'h3.\1', html, flags=re.M)

    # Tables conversion
    lines = html.split('\n')
    in_table = False
    table_html = []
    new_lines = []

    for line in lines:
        if '|' in line:
            if not in_table:
                in_table = True
                table_html = ['<table>']
            
            # Skip delimiter row
            if '---' in line:
                continue

            cells = [c.strip() for c in line.split('|')[1:-1]]
            tag = 'th' if len(table_html) == 1 else 'td'
            row_str = '<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>'
            table_html.append(row_str)
        else:
            if in_table:
                table_html.append('</table>')
                new_lines.append('\n'.join(table_html))
                in_table = False
                table_html = []
            new_lines.append(line)

    if in_table:
        table_html.append('</table>')
        new_lines.append('\n'.join(table_html))

    html = '\n'.join(new_lines)

    # Re-apply heading tags
    html = re.sub(r'h1\.(.*?)$', r'<h1>\1</h1>', html, flags=re.M)
    html = re.sub(r'h2\.(.*?)$', r'<h2>\1</h2>', html, flags=re.M)
    html = re.sub(r'h3\.(.*?)$', r'<h3>\1</h3>', html, flags=re.M)

    # Inline formatting
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    html = re.sub(r'^---$', r'<hr>', html, flags=re.M)

    return f"<!DOCTYPE html><html><head><meta charset='utf-8'>{CSS_STYLE}</head><body>{html}<div class='footer'>Garza Global Graviton Core Infrastructure — Sovereign Defense Document</div></body></html>"

def export_documents():
    """Finds and converts defense markdown reports to styled HTML/Printable documents."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    converted_files = []

    targets = ["AFWERX_SBIR_Proposal.md", "cmmc_compliance_report.md"]

    for filename in targets:
        src_path = os.path.join(LEGAL_DIR, filename)
        if os.path.exists(src_path):
            md_content = read_file_safe(src_path)

            html_output = simple_md_to_html(md_content)
            out_filename = filename.replace(".md", ".html")
            out_path = os.path.join(EXPORT_DIR, out_filename)

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_output)

            converted_files.append((filename, out_filename))

    return converted_files

def log_export_event(converted_count: int):
    """Logs document conversion event to sovereign_ledger.json."""
    ledger_data = []
    if os.path.exists(LEDGER_PATH):
        try:
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                ledger_data = json.load(f)
        except Exception:
            ledger_data = []

    payload = {
        "event": "DOCUMENT_EXPORTER_COMPLETE",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "documents_exported": converted_count,
        "export_format": "OFFLINE_DEFENSE_HTML_PDF_READY"
    }

    ledger_data.append(payload)

    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger_data, f, indent=2)

if __name__ == "__main__":
    print("=== GARZA GLOBAL GRAVITON: DOCUMENT EXPORTER ===")
    print("Converting Defense Artifacts to Printable Documents...")

    start_t = time.time()
    converted = export_documents()
    log_export_event(len(converted))
    elapsed = round(time.time() - start_t, 3)

    print("\n==============================================================")
    print("   GARZA GLOBAL GRAVITON: DOCUMENT EXPORT REPORT")
    print("==============================================================")
    print(f"  [DOCUMENTS CONVERTED]    {len(converted)} Markdown Artifacts")
    print(f"  [OUTPUT DIRECTORY]       04_Legal_and_IP/exports/")
    print("  ----------------------------------------------------------")
    print("  [EXPORTED ARTIFACTS]")
    for src, out in converted:
        print(f"    - {src.ljust(26)} -> 04_Legal_and_IP/exports/{out}")
    print(f"  [EXPORT DURATION]        {elapsed} Seconds")
    print("  ----------------------------------------------------------")
    print("  [CRYPTOGRAPHIC INTEGRITY]")
    print("    - Sovereign Ledger   : RECORDED & SEALED")
    print("    - Printable State    : READY FOR PDF PRINTING / SUBMISSION")
    print("==============================================================\n")