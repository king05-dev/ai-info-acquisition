FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY crawler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY crawler/ ./crawler/
COPY ui/ ./ui/

WORKDIR /app/crawler

EXPOSE 8000

CMD ["python", "main.py"]
