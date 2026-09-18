import os
import pathlib
import webull

sdk_path = pathlib.Path(webull.__file__).parent
print("Searching SDK for instrument_type choices...")
results = []
for p in sdk_path.rglob("*.py"):
    try:
        text = p.read_text(encoding="utf-8")
        if "instrument_type" in text or "EQUITY" in text or "CS" in text:
            for line in text.splitlines():
                if any(k in line for k in ["STOCK", "EQUITY", "instrument_type", "ETF"]):
                    results.append(f"{p.name}: {line.strip()}")
    except Exception:
        pass
for r in results[:30]:
    print(r)
