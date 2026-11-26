PY ?= python

.PHONY: help setup data-real data-demo etl analytics load insights train train-late pipeline test lint docker

help:
	@echo "make setup      - install all dependencies"
	@echo "make data-real  - download the real Olist dataset (needs Kaggle token)"
	@echo "make data-demo  - generate the synthetic demo dataset"
	@echo "make etl        - clean data and build analytical tables"
	@echo "make analytics  - KPI, RFM and cohort outputs"
	@echo "make load       - load processed tables into PostgreSQL"
	@echo "make insights   - auto-generate key findings from raw data"
	@echo "make train      - train repeat-purchase model (XGBoost + SHAP + MLflow)"
	@echo "make pipeline   - etl + analytics + insights + train"
	@echo "make test       - run pytest"
	@echo "make lint       - run ruff"
	@echo "make docker     - run the full stack with Docker Compose"

setup:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt -r requirements-ml.txt -r requirements-dev.txt

data-real:
	$(PY) scripts/download_olist.py

data-demo:
	$(PY) -m src.generate_data

etl:
	$(PY) -m src.etl

analytics:
	$(PY) -m src.analytics

load:
	$(PY) -m src.load_postgres

insights:
	$(PY) -m src.insights

train:
	$(PY) -m src.ml.train

train-late:
	$(PY) -m src.ml.late_delivery

pipeline: etl analytics insights train train-late

test:
	$(PY) -m pytest -q

lint:
	ruff check .

docker:
	docker compose up --build
