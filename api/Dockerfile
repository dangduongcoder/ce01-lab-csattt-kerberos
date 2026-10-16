FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    krb5-user \
    libkrb5-dev \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY config/krb5.conf /etc/krb5.conf
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./api/app/
COPY entrypoint.sh /entrypoint.sh

# Sanitize line endings and make executable (solves Windows CRLF exec issues)
RUN dos2unix /entrypoint.sh /etc/krb5.conf && \
    sed -i 's/\r$//' /entrypoint.sh /etc/krb5.conf && \
    chmod +x /entrypoint.sh

EXPOSE 8000

# Use /bin/bash explicitly so Linux kernel does not rely on shebang interpreter lookup
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
