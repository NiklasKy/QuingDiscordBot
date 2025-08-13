FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies (no Tesseract/OCR needed)
RUN apt-get update && apt-get install -y \
    gcc \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a non-root user
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

# Start the modular bot
CMD ["python", "-m", "src.bot_modular"]