FROM python:3.11-slim

# Prevent Python from creating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Make Python output appear immediately
ENV PYTHONUNBUFFERED=1

# Working directory inside container
WORKDIR /app

# Install Python dependencies first
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/db.py ./src/db.py
COPY src/features.py ./src/features.py
COPY src/train_experts.py ./src/train_experts.py

# Create model directory
RUN mkdir -p /app/models

# Start expert training
CMD ["python", "src/train_experts.py"]
