PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements.txt

check:
	$(PYTHON) scripts/check.py

run:
	$(PYTHON) main.py

mysql:
	docker compose up -d mysql

up:
	docker compose up -d --build

down:
	docker compose down
