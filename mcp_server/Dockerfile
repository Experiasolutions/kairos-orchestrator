FROM python:3.11-slim

WORKDIR /app

# Install pg_dump for backup functionality
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create backup directory
RUN mkdir -p /backups

EXPOSE 3001

CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "3001", "--log-level", "info"]
