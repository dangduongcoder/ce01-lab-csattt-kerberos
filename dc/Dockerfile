FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba \
    samba-ad-provision \
    samba-dsdb-modules \
    samba-vfs-modules \
    winbind \
    krb5-user \
    krb5-config \
    dnsutils \
    ldb-tools \
    procps \
    psmisc \
    curl \
    python3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /scripts /shared /var/lib/samba/private /etc/samba

COPY config/krb5.conf /etc/krb5.conf
COPY provision.sh /scripts/provision.sh
COPY rotate_krbtgt.sh /scripts/rotate_krbtgt.sh
COPY export_domain_info.py /scripts/export_domain_info.py
COPY entrypoint.sh /scripts/entrypoint.sh

RUN sed -i 's/\r$//' /scripts/*.sh /scripts/*.py /etc/krb5.conf && \
    chmod +x /scripts/*.sh /scripts/*.py

EXPOSE 53/tcp 53/udp 88/tcp 88/udp 135/tcp 138/udp 139/tcp 389/tcp 389/udp 445/tcp 464/tcp 464/udp 636/tcp

ENTRYPOINT ["/scripts/entrypoint.sh"]
