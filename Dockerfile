FROM node:22.19-bookworm-slim AS node

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Pi Agent packages require Node 22.19+. Copy the runtime from the official
# image instead of using the older Debian package.
COPY --from=node /usr/local /usr/local

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies for Pi Agent
COPY pi_agent/package*.json /opt/pi_agent/
RUN cd /opt/pi_agent && npm ci --omit=dev --no-audit --no-fund

# Copy application source
COPY backend/ /app/
COPY pi_agent/ /opt/pi_agent/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8000 8001

CMD ["/bin/sh", "/app/start.sh"]
