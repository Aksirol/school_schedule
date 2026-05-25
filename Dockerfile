FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Встановлення системних залежностей для компіляції psycopg2
RUN apt-get update \
    && apt-get install -y gcc libpq-dev fonts-dejavu-core \
    && apt-get clean

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]