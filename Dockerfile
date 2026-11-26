FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libgomp is required by xgboost
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-linux.txt requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements-linux.txt -r requirements-ml.txt

COPY . .

CMD ["python", "-m", "src.etl"]
