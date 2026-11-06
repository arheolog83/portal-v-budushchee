# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    python -m pip install --no-cache-dir -r requirements.txt

# GigaChat uses the Russian Ministry of Digital Development trust root.
# The certificate is installed into the OS trust store; TLS verification stays enabled.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -fsSk --retry 3 \
       https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt \
       -o /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \
    && openssl x509 -in /usr/local/share/ca-certificates/russian_trusted_root_ca.crt -noout \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser main.py index.html ./

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
