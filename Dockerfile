FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY coint ./coint
COPY prompts ./prompts
RUN useradd -r -u 10001 coint && mkdir -p /data && chown coint /data
USER coint
ENV COINT_DB_PATH=/data/coint.sqlite3
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/healthz')" || exit 1
CMD ["python", "-m", "coint", "serve", "--port", "8080"]
