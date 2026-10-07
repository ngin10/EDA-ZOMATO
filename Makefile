.PHONY: install lint format test demo run clean

install:        ## Install the package with dev tools
	pip install -e ".[dev]"

lint:           ## Static checks
	ruff check .
	ruff format --check .

format:         ## Auto-format
	ruff format .
	ruff check --fix .

test:           ## Unit + integration tests with coverage
	pytest --cov=zomato_analytics --cov-report=term-missing

demo:           ## Full pipeline on synthetic data (no download needed)
	zomato-analytics demo --out reports

run:            ## Full pipeline on the real Kaggle file in data/raw/zomato.csv
	zomato-analytics run --input data/raw/zomato.csv --out reports

clean:
	rm -rf reports/* data/raw/zomato_sample.csv .pytest_cache .ruff_cache .coverage
	touch reports/.gitkeep
