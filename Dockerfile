# Alternativa caso Nixpacks não funcione
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    firefox-esr \
    xvfb \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install geckodriver
RUN wget -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz \
    && tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/geckodriver \
    && rm /tmp/geckodriver.tar.gz

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements-railway.txt .
RUN pip install --no-cache-dir -r requirements-railway.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p static/css static/js

# Set environment variables
ENV DISPLAY=:99
ENV RAILWAY_ENVIRONMENT=production

# Expose port
EXPOSE $PORT

# Start command
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 main:app"]