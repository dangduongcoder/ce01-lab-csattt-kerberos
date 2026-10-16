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

COPY client.py demo_normal.py inspect_ticket.py ./

RUN dos2unix *.py /etc/krb5.conf && \
    sed -i 's/\r$//' *.py /etc/krb5.conf

CMD ["tail", "-f", "/dev/null"]
