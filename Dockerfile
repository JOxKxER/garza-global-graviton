FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install core system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source application
COPY . .

# Render supplies PORT at runtime; 8000 remains the local fallback.
EXPOSE 8000

# Use a lightweight exec-form launcher that reads Render's PORT at runtime.
CMD ["python", "-m", "src.serve"]
