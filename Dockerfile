FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Node.js for persistent Pi Agent runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies for Pi Agent
COPY pi_agent/package*.json /opt/pi_agent/
RUN cd /opt/pi_agent && npm install --omit=dev --no-audit --no-fund

# Copy application source
COPY backend/ /app/
COPY pi_agent/ /opt/pi_agent/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8000 8001

CMD ["/bin/sh", "/app/start.sh"]
