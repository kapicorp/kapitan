all: clean package

.PHONY: pre-requisites
pre-requisites:
	@echo ----- Installing pre-requisites -----
	poetry install --with dev --with docs --with test

.PHONY: lint
lint:
	@echo ----- Running lint -----
	poetry run flake8 kapitan
	poetry run mypy kapitan
	poetry run pylint kapitan

.PHONY: install poetry with pipx
install_poetry:
	@echo ----- Installing poetry with pipx -----
	which poetry || pipx install poetry

.PHONY: test
test: pre-requisites lint test_python test_docker test_coverage test_formatting
	@echo ----- Running python tests -----
	poetry run pytest

.PHONY: test_docker
test_docker:
	@echo ----- Testing build of docker image -----
	docker build . --no-cache -t kapitan
	@echo ----- Testing run of docker image -----
	docker run -ti --rm kapitan --help
	docker run -ti --rm kapitan lint

.PHONY: test_coverage
test_coverage:
	@echo ----- Testing code coverage -----
	poetry run pytest tests/ \
		-n auto \
		--cov=kapitan \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-report=json:coverage.json \
		--cov-report=html:htmlcov \
		--cov-fail-under=65

.PHONY: test_formatting
test_formatting:
	@echo ----- Testing code formatting -----
	poetry run black --check .
	@echo

.PHONY: release
release:
ifeq ($(version),)
	@echo Please pass version to release e.g. make release version=0.16.5
else
	scripts/inc_version.sh $(version)
endif

.PHONY: package
package:
	python3 setup.py sdist bdist_wheel

.PHONY: clean
clean:
	rm -rf dist/ build/ kapitan.egg-info/ bindist/

.PHONY: format_codestyle
format_codestyle:
	poetry run black .
	@echo

.PHONY: local_serve_documentation
local_serve_documentation:
	poetry run mike serve

.PHONY: mkdocs_gh_deploy
mkdocs_gh_deploy:
	poetry run mike deploy --push dev master
