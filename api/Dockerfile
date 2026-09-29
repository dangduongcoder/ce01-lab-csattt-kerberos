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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY config/krb5.conf /etc/krb5.conf
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./api/app/
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
