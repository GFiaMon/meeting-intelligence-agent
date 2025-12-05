# Use Python 3.10 slim as base image
FROM python:3.10-slim

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
# - ffmpeg: Required for Whisper audio processing
# - git: Required for installing some git-based pip packages (if any)
# - curl: Required to download Node.js setup
# - nodejs: Required for running MCP servers (like Notion) via npx
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the Gradio port
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]
