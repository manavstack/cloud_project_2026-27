FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY database ./database
CMD ["python", "-c", "from src.db import apply_migrations; apply_migrations()"]
