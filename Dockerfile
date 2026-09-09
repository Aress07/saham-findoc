# FinDoc AI — container image
FROM python:3.12-slim

WORKDIR /app

# Install system deps (CA certs for SEC downloads + curl for health checks)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["./entrypoint.sh"]