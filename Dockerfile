FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
       --default-timeout=200 \
       --retries 10 \
       -r /app/requirements.txt

COPY . /app

EXPOSE 5000

CMD ["python", "app.py"]
