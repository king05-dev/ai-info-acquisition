FROM python:3.12-slim

WORKDIR /app

COPY crawler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps

COPY crawler/ ./crawler/
COPY ui/ ./ui/

WORKDIR /app/crawler

EXPOSE 8000

CMD ["python", "main.py"]
