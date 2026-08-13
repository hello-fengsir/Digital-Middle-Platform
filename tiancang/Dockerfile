FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app.py /app/tiancang_app.py
COPY static /app/static
COPY pdfjs /app/pdfjs
RUN chmod -R a+rX /app && mkdir -p /data/pdfs && useradd --system --uid 10001 --home /nonexistent --shell /usr/sbin/nologin tiancang && chown -R tiancang:tiancang /data/pdfs
USER tiancang
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=20 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["uvicorn","tiancang_app:app","--host","0.0.0.0","--port","8000"]
