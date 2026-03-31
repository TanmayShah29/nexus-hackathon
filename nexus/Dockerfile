FROM python:3.11-slim

WORKDIR /app

# System deps for aiohttp, beautifulsoup4, grpcio
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (cache layer)
COPY nexus/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy full repo structure so `nexus` resolves as a package
COPY . .

EXPOSE 8080

# FIX: The server lives at nexus/main.py and `nexus` is a Python package.
# Uvicorn must be launched from /app with the dotted module path.
# PYTHONPATH is not needed because /app is the CWD and `nexus/` is a package
# (it has __init__ files). We also tell uvicorn to look for the `app` object
# inside nexus.main.
CMD ["uvicorn", "nexus.main:app", "--host", "0.0.0.0", "--port", "8080"]
